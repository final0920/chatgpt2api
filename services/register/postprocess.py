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
from typing import Any

from services.account_service import account_service
from services.config import config
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


def build_sub2api_account(account: dict, info: dict, group_ids: list[int], concurrency: int = 5) -> dict:
    """把一个账号组装成 sub2api BatchCreate 结构（= 参考文件账号结构 + 顶层 group_ids）。

    account: 号池账号 dict（access_token / refresh_token / id_token / email / user_id ...）
    info: verify_workspace_access 结果（account_id / plan_type / organization_id），可为空
    group_ids: 归入的 sub2api 分组 id 列表（如 [2]）
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

    return {
        "name": email,
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


def run_postprocess(result: dict) -> dict:
    """注册成功后的后处理编排。

    result: register() 返回值（email / access_token / refresh_token / id_token / mail_provider ...）
    返回 {ok, skipped?, reason?, push_result?}；任何异常都被吞掉并记日志，绝不向上抛。
    """
    email = str(result.get("email") or "").strip()
    settings = config.get_register_postprocess_settings()

    if not settings.get("enabled"):
        return {"ok": False, "skipped": True, "reason": "disabled"}

    workspace_id = str(settings.get("workspace_id") or "").strip()
    base_url = str(settings.get("sub2api_base_url") or "").strip()
    api_key = str(settings.get("sub2api_api_key") or "").strip()
    group_ids = settings.get("group_ids") or []
    do_verify = bool(settings.get("verify_chat_access", True))

    if not workspace_id:
        logger.warning(f"注册后处理跳过: email={email}, 原因=未配置空间id")
        return {"ok": False, "skipped": True, "reason": "no_workspace_id"}
    if not base_url or not api_key:
        logger.warning(f"注册后处理跳过: email={email}, 原因=sub2api未配置(地址/密钥)")
        return {"ok": False, "skipped": True, "reason": "sub2api_not_configured"}

    logger.info(f"注册后处理开始: email={email}, workspace={workspace_id}")

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

        # ② join 母号空间
        logger.debug({"event": "register_postprocess_join_request", "email": email, "workspace": workspace_id})
        join_result = client.request_workspace_invite(workspace_id)
        logger.debug({"event": "register_postprocess_join_response", "email": email, "result": join_result})
        logger.info(f"注册后处理 join 空间成功: email={email}")

        # ③ 验证可对话，拿 workspace 的 account_id / plan / org
        info: dict[str, Any] = {}
        if do_verify:
            info = client.verify_workspace_access(workspace_id)
            logger.debug({"event": "register_postprocess_verify", "email": email, "info": info})

        # ④ 组装 sub2api 结构（+ 顶层 group_ids）
        sub2api_account = build_sub2api_account(account, info, group_ids, int(settings.get("concurrency") or 5))
        logger.debug({
            "event": "register_postprocess_push_request",
            "email": email,
            "group_ids": group_ids,
            "chatgpt_account_id": sub2api_account["credentials"].get("chatgpt_account_id"),
            "plan_type": sub2api_account["credentials"].get("plan_type"),
        })

        # ⑤ 推送到 sub2api（BatchCreate）
        server = {"base_url": base_url, "api_key": api_key}
        push_result = push_accounts_batch(server, [sub2api_account])
        logger.debug({"event": "register_postprocess_push_response", "email": email, "result": push_result})

        success = int(push_result.get("success") or 0) if isinstance(push_result, dict) else 0
        failed = int(push_result.get("failed") or 0) if isinstance(push_result, dict) else 0
        if failed and not success:
            logger.warning(f"注册后处理推送 sub2api 失败: email={email}, resp={push_result}")
            return {"ok": False, "reason": "push_failed", "push_result": push_result}

        logger.info(f"注册后处理已推送 sub2api: email={email}, group_ids={group_ids}")
        return {"ok": True, "push_result": push_result}
    except Exception as exc:
        logger.warning(f"注册后处理失败: email={email}, error={type(exc).__name__}: {exc}")
        logger.debug({"event": "register_postprocess_error", "email": email, "error": repr(exc)})
        return {"ok": False, "reason": str(exc)}
