"""outlook007 渠道注册成功后的自动后处理：join 空间 → 验证可对话 → 转 sub2api → 推送。

参考 E:\\TestProjects\\143\\regist.py（send_join / verify_chat_access / build_sub2api_account）。
由 openai_register.worker 在注册成功后调用；任何失败只记日志、绝不影响注册主流程。

双轨日志（遵循全局规范）：
- logger.debug 记全量细节（端点/join 报文/verify 原始 info/推送 body/sub2api 响应）。
- logger.info / warning 记关键节点摘要（start / join ok / pushed / failed）。
"""
from __future__ import annotations

import base64
import json
import threading
from typing import Any

from services.account_service import account_service
from services.config import DATA_DIR, config
from services.openai_backend_api import OpenAIBackendAPI
from services.sub2api_service import push_accounts_batch
from utils.log import logger

# 与账号 id_token 的 aud 一致；JWT 解不出 client_id 时兜底用它（与 regist.py 一致）
OAUTH_CLIENT_ID = "app_2SKx67EdpoN0G6j64rFvigXD"

# 拿不到的字段(model_mapping)照抄参考 sub2api-account 文件的默认值（与 regist.py 一致）
DEFAULT_MODEL_MAPPING = {
    "codex-auto-review": "codex-auto-review",
    "gpt-4o-audio-preview": "gpt-4o-audio-preview",
    "gpt-4o-realtime-preview": "gpt-4o-realtime-preview",
    "gpt-5*": "gpt-5.5",
    "gpt-5.2": "gpt-5.2",
    "gpt-5.2-2025-12-11": "gpt-5.2-2025-12-11",
    "gpt-5.2-chat-latest": "gpt-5.2-chat-latest",
    "gpt-5.2-pro": "gpt-5.2-pro",
    "gpt-5.2-pro-2025-12-11": "gpt-5.2-pro-2025-12-11",
    "gpt-5.3-codex": "gpt-5.3-codex",
    "gpt-5.3-codex-spark": "gpt-5.3-codex-spark",
    "gpt-5.4": "gpt-5.4",
    "gpt-5.4-2026-03-05": "gpt-5.4-2026-03-05",
    "gpt-5.4-mini": "gpt-5.4-mini",
    "gpt-5.5": "gpt-5.5",
    "gpt-image-1": "gpt-image-1",
    "gpt-image-1.5": "gpt-image-1.5",
    "gpt-image-2": "gpt-image-2",
}


def _jwt_payload(token: str) -> dict:
    """解 JWT payload(base64url 段)，失败返回 {}。"""
    try:
        part = token.split(".")[1]
        part += "=" * (4 - len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part))
    except Exception:
        return {}


def build_sub2api_account(account: dict, info: dict, group_ids: list[int], concurrency: int = 5,
                          workspace_id: str = "") -> dict:
    """把一个账号组装成 sub2api BatchCreate 结构（= 参考文件账号结构 + 顶层 group_ids）。

    account: 号池账号 dict（access_token / refresh_token / id_token / email / user_id ...）
    info: verify_workspace_access 结果（account_id / plan_type / organization_id），可为空
    group_ids: 归入的 sub2api 分组 id 列表（如 [2]）
    workspace_id: 非空时账号 name = email+workspace_id（一个号加入多空间时区分，避免 sub2api 重名覆盖）
    """
    access_token = str(account.get("access_token") or "")
    payload = _jwt_payload(access_token)
    auth_claim = payload.get("https://api.openai.com/auth")
    auth_claim = auth_claim if isinstance(auth_claim, dict) else {}
    profile_claim = payload.get("https://api.openai.com/profile")
    profile_claim = profile_claim if isinstance(profile_claim, dict) else {}

    email = str(account.get("email") or "").strip() or str(profile_claim.get("email") or "").strip()
    # account_id / plan / org 优先用 join 后 verify 拿到的 workspace 值，兜底用 JWT claim
    account_id = str(info.get("account_id") or "").strip() or str(auth_claim.get("chatgpt_account_id") or "").strip()
    plan_type = str(info.get("plan_type") or "").strip() or str(auth_claim.get("chatgpt_plan_type") or "").strip()
    organization_id = str(info.get("organization_id") or "").strip()

    sub_name = f"{email}+{workspace_id}" if workspace_id else email
    return {
        "name": sub_name,
        "platform": "openai",
        "type": "oauth",
        "credentials": {
            "access_token": access_token,
            "chatgpt_account_id": account_id,
            "chatgpt_user_id": str(auth_claim.get("user_id") or account.get("user_id") or ""),
            "client_id": str(payload.get("client_id") or OAUTH_CLIENT_ID),
            "email": email,
            "expires_at": payload.get("exp", 0),
            "id_token": str(account.get("id_token") or ""),
            "model_mapping": DEFAULT_MODEL_MAPPING,
            "organization_id": organization_id,
            "plan_type": plan_type,
            "refresh_token": str(account.get("refresh_token") or ""),
        },
        "extra": {
            "email": email,
            "openai_oauth_responses_websockets_v2_enabled": False,
            "openai_oauth_responses_websockets_v2_mode": "off",
            "privacy_mode": "training_off",
        },
        "concurrency": concurrency,
        "priority": 1,
        "rate_multiplier": 1,
        "auto_pause_on_expired": True,
        "group_ids": [int(gid) for gid in (group_ids or [])],
    }


# ---- 注册入库：本地导出（export_local=True）----
# 每行：登入账号----登入密码----会员类型----邮件接码地址，追加到 data/account.txt（多线程注册故加锁）。
ACCOUNT_TXT_SEP = "----"
ACCOUNT_TXT_FILE = DATA_DIR / "account.txt"
_account_txt_lock = threading.Lock()


def _export_account_to_local(result: dict, settings: dict) -> dict:
    """local 模式：把注册成功的账号按 登入账号----登入密码----会员类型----接码地址 追加写入 data/account.txt。"""
    email = str(result.get("email") or "").strip()
    password = str(result.get("password") or "").strip()
    membership = str(settings.get("local_membership_type") or "").strip() or "K12"
    code_api_url = str(result.get("code_api_url") or "").strip()
    line = ACCOUNT_TXT_SEP.join([email, password, membership, code_api_url])
    try:
        with _account_txt_lock:
            ACCOUNT_TXT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(ACCOUNT_TXT_FILE, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        logger.info(f"注册入库(本地导出): email={email} -> {ACCOUNT_TXT_FILE}")
        return {"ok": True, "exported": "local", "path": str(ACCOUNT_TXT_FILE)}
    except Exception as exc:
        logger.warning(f"注册入库(本地导出)失败: email={email}, error={type(exc).__name__}: {exc}")
        logger.debug({"event": "register_postprocess_local_export_error", "email": email, "error": repr(exc)})
        return {"ok": False, "reason": str(exc)}


def _push_to_sub2api(result: dict, settings: dict, email: str) -> dict:
    """sub2api 入库：多空间逐个 join + verify + 组装，再一次性 BatchCreate 推送。

    返回 {ok, skipped?, reason?, push_result?}；任何异常都被吞掉并记日志，绝不向上抛。
    """
    # 多空间：workspace_ids 逐个 join+推送；blocked_workspace_ids 里的空间跳过（不 join 不推送）
    workspace_ids = settings.get("workspace_ids") or []
    blocked = {str(w).strip() for w in (settings.get("blocked_workspace_ids") or []) if str(w).strip()}
    targets = [str(ws).strip() for ws in workspace_ids if str(ws).strip() and str(ws).strip() not in blocked]
    base_url = str(settings.get("sub2api_base_url") or "").strip()
    api_key = str(settings.get("sub2api_api_key") or "").strip()
    group_ids = settings.get("group_ids") or []
    do_verify = bool(settings.get("verify_chat_access", True))
    concurrency = int(settings.get("concurrency") or 5)

    if not targets:
        logger.warning(f"注册后处理跳过: email={email}, 原因=无可用空间(未配置或全部被屏蔽)")
        return {"ok": False, "skipped": True, "reason": "no_workspace_id"}
    if not base_url or not api_key:
        logger.warning(f"注册后处理跳过: email={email}, 原因=sub2api未配置(地址/密钥)")
        return {"ok": False, "skipped": True, "reason": "sub2api_not_configured"}

    logger.info(f"注册后处理开始: email={email}, 空间数={len(targets)}, 屏蔽={len(blocked)}")

    try:
        # ① 取当前有效 token（refresh_accounts 可能已轮换，不能用注册时旧值）
        current_token = account_service.resolve_access_token(str(result.get("access_token") or ""))
        account = account_service.get_account(current_token) or {}
        if not account:
            # 号池取不到就用 register 返回值兜底
            account = {
                "access_token": current_token or str(result.get("access_token") or ""),
                "refresh_token": str(result.get("refresh_token") or ""),
                "id_token": str(result.get("id_token") or ""),
                "email": email,
            }
        access_token = str(account.get("access_token") or "")
        if not access_token:
            raise RuntimeError("no access_token available")

        client = OpenAIBackendAPI(access_token)

        # ②③④ 逐个空间 join + verify(拿各自 account_id) + 组装(同 token / 各自 account_id / name=email+空间)
        # 单个空间失败只跳过该空间、不影响其它；屏蔽空间已在 targets 里排除
        sub2api_accounts: list[dict] = []
        for ws in targets:
            try:
                logger.debug({"event": "register_postprocess_join_request", "email": email, "workspace": ws})
                join_result = client.request_workspace_invite(ws)
                logger.debug({"event": "register_postprocess_join_response", "email": email, "workspace": ws, "result": join_result})
                info: dict[str, Any] = {}
                if do_verify:
                    info = client.verify_workspace_access(ws)
                    logger.debug({"event": "register_postprocess_verify", "email": email, "workspace": ws, "info": info})
                acct = build_sub2api_account(account, info, group_ids, concurrency, workspace_id=ws)
                sub2api_accounts.append(acct)
                logger.info(f"注册后处理 join+组装成功: email={email}, workspace={ws}")
            except Exception as ws_exc:
                logger.warning(f"注册后处理 空间处理失败(跳过该空间): email={email}, workspace={ws}, error={type(ws_exc).__name__}: {ws_exc}")
                logger.debug({"event": "register_postprocess_workspace_error", "email": email, "workspace": ws, "error": repr(ws_exc)})

        if not sub2api_accounts:
            logger.warning(f"注册后处理失败: email={email}, 所有空间 join/组装均失败，无推送")
            return {"ok": False, "reason": "all_workspaces_failed"}

        # ⑤ 一次推送所有空间账号到 sub2api（BatchCreate，共享 group_ids）
        server = {"base_url": base_url, "api_key": api_key}
        logger.debug({"event": "register_postprocess_push_request", "email": email, "count": len(sub2api_accounts), "group_ids": group_ids})
        push_result = push_accounts_batch(server, sub2api_accounts)
        logger.debug({"event": "register_postprocess_push_response", "email": email, "result": push_result})

        success = int(push_result.get("success") or 0) if isinstance(push_result, dict) else 0
        failed = int(push_result.get("failed") or 0) if isinstance(push_result, dict) else 0
        if failed and not success:
            logger.warning(f"注册后处理推送 sub2api 失败: email={email}, resp={push_result}")
            return {"ok": False, "reason": "push_failed", "push_result": push_result}

        logger.info(f"注册后处理已推送 sub2api: email={email}, 空间数={len(sub2api_accounts)}, group_ids={group_ids}")
        return {"ok": True, "push_result": push_result}
    except Exception as exc:
        logger.warning(f"注册后处理失败: email={email}, error={type(exc).__name__}: {exc}")
        logger.debug({"event": "register_postprocess_error", "email": email, "error": repr(exc)})
        return {"ok": False, "reason": str(exc)}


def run_postprocess(result: dict) -> dict:
    """注册成功后的后处理编排：本地导出 / 推送 sub2api，两者可同时进行、互不影响。

    result: register() 返回值（email / access_token / refresh_token / id_token / mail_provider ...）
    返回 {ok, skipped?, reason?, summary?, targets, local?, sub2api?}；任何异常都被吞掉并记日志，绝不向上抛。
    """
    email = str(result.get("email") or "").strip()
    settings = config.get_register_postprocess_settings()

    if not settings.get("enabled"):
        return {"ok": False, "skipped": True, "reason": "disabled"}

    export_local = bool(settings.get("export_local"))
    push_sub2api = bool(settings.get("push_sub2api", True))
    if not export_local and not push_sub2api:
        logger.warning(f"注册后处理跳过: email={email}, 原因=未选任何入库目标(本地/sub2api 都关)")
        return {"ok": False, "skipped": True, "reason": "no_storage_target"}

    out: dict[str, Any] = {"targets": []}
    attempted: list[bool] = []   # 各实际执行目标成功与否（被跳过的不计入）
    done: list[str] = []         # 成功目标的中文摘要
    reasons: list[str] = []      # 失败/跳过原因

    # ① 本地导出（可与 sub2api 并存，互不影响）
    if export_local:
        out["targets"].append("local")
        local_res = _export_account_to_local(result, settings)
        out["local"] = local_res
        if local_res.get("ok"):
            attempted.append(True)
            done.append("已导出到本地 account.txt")
        else:
            attempted.append(False)
            reasons.append(f"本地导出:{local_res.get('reason')}")

    # ② 推送 sub2api（原 join 空间 + 转 sub2api + 推送 流程）
    if push_sub2api:
        out["targets"].append("sub2api")
        push_res = _push_to_sub2api(result, settings, email)
        out["sub2api"] = push_res
        if push_res.get("ok"):
            attempted.append(True)
            done.append("已推送 sub2api")
        else:
            if not push_res.get("skipped"):
                attempted.append(False)  # 未配置等"跳过"不计入失败
            reasons.append(f"sub2api:{push_res.get('reason')}")

    # 全部目标都被跳过（未配置等）→ 整体视为跳过，保持安静（与原行为一致）
    if not attempted:
        return {"ok": False, "skipped": True, "targets": out["targets"],
                "reason": "; ".join(reasons) or "no_storage_target"}

    out["ok"] = all(attempted)
    out["summary"] = " + ".join(done)
    if reasons:
        out["reason"] = "; ".join(reasons)
    return out
