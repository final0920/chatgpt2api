"""账号巡检服务：巡检 sub2api 与 ChatGPT2API 账号并同步。

流程（针对 sub2api 分组 group_id，取自系统设置 register_postprocess.group_ids 首个，默认 2）：
1. 删除 sub2api 该分组内状态为 error 的账号。
2. 对该分组内状态非 error、且存在于 ChatGPT2API 号池(按 email)的账号：
   重新授权(更新 at/rt) → join 空间 → 转 sub2api 格式 → 推送到 sub2api。

照 register_service 的"任务+日志"骨架：daemon 线程跑，_logs buffer 供前端 SSE 拉取。
单账号失败隔离(不中断整轮)；双轨：主日志(buffer,前端可见)记节点，细节走 logger.debug。
"""
from __future__ import annotations

import threading
import uuid

from services.account_service import account_service
from services.config import config
from services import sub2api_service
from utils.log import logger
from utils.timezone import beijing_now_str as _now


class InspectService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._runner: threading.Thread | None = None
        self._enabled = False
        self._logs: list[dict] = []
        self._stats: dict = self._empty_stats()

    @staticmethod
    def _empty_stats() -> dict:
        return {
            "job_id": "", "running": False,
            "total": 0, "deleted": 0, "matched": 0,
            "synced": 0, "failed": 0, "skipped": 0,
            "started_at": "", "updated_at": "", "finished_at": "",
        }

    def get(self) -> dict:
        with self._lock:
            return {
                "enabled": self._enabled,
                "stats": dict(self._stats),
                "logs": self._logs[-300:],
            }

    def _append_log(self, text: str, level: str = "info") -> None:
        with self._lock:
            self._logs.append({"time": _now(), "text": str(text), "level": str(level or "info")})
            self._logs = self._logs[-300:]

    def _bump(self, **updates) -> None:
        with self._lock:
            self._stats.update(updates)
            self._stats["updated_at"] = _now()

    def start(self) -> dict:
        with self._lock:
            if self._runner and self._runner.is_alive():
                return self.get()
            self._enabled = True
            self._logs = []
            self._stats = self._empty_stats()
            self._stats["job_id"] = uuid.uuid4().hex
            self._stats["running"] = True
            self._stats["started_at"] = _now()
            self._stats["updated_at"] = _now()
            self._runner = threading.Thread(target=self._run, daemon=True, name="account-inspect")
            self._runner.start()
            return self.get()

    def stop(self) -> dict:
        with self._lock:
            self._enabled = False
            self._append_log("已请求停止巡检，正在结束当前账号处理", "yellow")
            return self.get()

    def _run(self) -> None:
        try:
            self._do_inspect()
        except Exception as exc:
            self._append_log(f"巡检异常终止: {type(exc).__name__}: {exc}", "red")
            logger.debug({"event": "inspect_run_error", "error": repr(exc)})
        finally:
            with self._lock:
                self._enabled = False
                self._stats["running"] = False
                self._stats["finished_at"] = _now()
                self._stats["updated_at"] = _now()

    def _build_local_email_index(self) -> dict[str, str]:
        """{email(lower): access_token}，用于判断 sub2api 账号是否在 ChatGPT2API 号池。"""
        index: dict[str, str] = {}
        for acc in account_service.list_accounts():
            email = str(acc.get("email") or "").strip().lower()
            token = str(acc.get("access_token") or "")
            if email and token:
                index.setdefault(email, token)
        return index

    def _do_inspect(self) -> None:
        # 延迟 import，避免潜在循环依赖
        from services.register import openai_register
        from services.openai_backend_api import OpenAIBackendAPI
        from services.register.postprocess import build_sub2api_account

        settings = config.get_register_postprocess_settings()
        base_url = str(settings.get("sub2api_base_url") or "").strip()
        api_key = str(settings.get("sub2api_api_key") or "").strip()
        workspace_id = str(settings.get("workspace_id") or "").strip()
        group_ids = settings.get("group_ids") or [2]
        do_verify = bool(settings.get("verify_chat_access", True))
        group_id = str(group_ids[0]) if group_ids else "2"

        if not base_url or not api_key:
            self._append_log("sub2api 未配置（请到 系统设置→注册入库 填地址/密钥），巡检中止", "red")
            return
        if not workspace_id:
            self._append_log("未配置空间 id，巡检中止", "red")
            return

        server = {"base_url": base_url, "api_key": api_key, "group_id": group_id}
        self._append_log(f"巡检开始：sub2api group={group_id}，空间={workspace_id}", "green")

        # 拉取该分组账号（巡检只需 status/email/id，不涉及 sub2api token）
        remote = sub2api_service.list_group_accounts(server)
        self._append_log(f"拉取 sub2api group {group_id} 账号：共 {len(remote)} 个", "info")
        self._bump(total=len(remote))

        # 阶段1：删除状态为 error 的账号
        err_accounts = [a for a in remote if str(a.get("status")) == "error"]
        self._append_log(f"[阶段1] 待删除错误账号：{len(err_accounts)} 个", "info")
        deleted = 0
        for a in err_accounts:
            if not self._enabled:
                self._append_log("已停止", "yellow")
                return
            label = a.get("email") or a.get("name") or a.get("id")
            try:
                sub2api_service.delete_account(server, str(a.get("id")))
                deleted += 1
                self._append_log(f"已删除错误账号：{label}", "info")
            except Exception as exc:
                self._append_log(f"删除失败 {label}：{exc}", "red")
                logger.debug({"event": "inspect_delete_error", "id": a.get("id"), "error": repr(exc)})
            self._bump(deleted=deleted)

        # 阶段2：非 error 账号，比对号池命中的走 重授权 → join → 推送
        ok_accounts = [a for a in remote if str(a.get("status")) != "error"]
        local_index = self._build_local_email_index()
        matched = [a for a in ok_accounts if str(a.get("email") or "").strip().lower() in local_index]
        skipped = len(ok_accounts) - len(matched)
        self._bump(matched=len(matched), skipped=skipped)
        self._append_log(
            f"[阶段2] 非错误账号 {len(ok_accounts)} 个：命中号池 {len(matched)} 个，跳过(不在号池) {skipped} 个",
            "info",
        )

        synced = 0
        failed = 0
        for a in matched:
            if not self._enabled:
                self._append_log("已停止", "yellow")
                return
            email = str(a.get("email") or "").strip()
            old_token = local_index.get(email.lower())
            if not old_token:
                continue
            try:
                self._append_log(f"重新授权：{email}", "info")
                logger.debug({"event": "inspect_reauth_start", "email": email})
                tokens = openai_register.reauthorize_login(email)
                updated = account_service.reauthorize_account(old_token, tokens, "inspect")
                new_token = str(updated.get("access_token") or "")
                client = OpenAIBackendAPI(new_token)
                client.request_workspace_invite(workspace_id)
                info = client.verify_workspace_access(workspace_id) if do_verify else {}
                logger.debug({"event": "inspect_verify", "email": email, "info": info})
                acct = build_sub2api_account(updated, info, group_ids)
                sub2api_service.push_accounts_batch(server, [acct])
                synced += 1
                self._append_log(f"已更新令牌 + join 空间 + 推送 sub2api：{email}", "green")
            except Exception as exc:
                failed += 1
                self._append_log(f"处理失败 {email}：{type(exc).__name__}: {exc}", "red")
                logger.debug({"event": "inspect_sync_error", "email": email, "error": repr(exc)})
            self._bump(synced=synced, failed=failed)

        self._append_log(
            f"巡检完成：删除 {deleted}，更新 {synced}，失败 {failed}，跳过 {skipped}",
            "green",
        )


inspect_service = InspectService()
