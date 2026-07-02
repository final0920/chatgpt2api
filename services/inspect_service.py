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
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.account_service import account_service
from services.config import config
from services import sub2api_service
from utils.log import logger
from utils.timezone import beijing_now_str as _now

ROUND_INTERVAL_SECONDS = 10
MIN_THREADS = 1
MAX_THREADS = 10
DEFAULT_THREADS = 3


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
            "round": 0, "threads": DEFAULT_THREADS,
            "total": 0, "deleted": 0, "matched": 0, "synced": 0, "failed": 0, "skipped": 0,
            "rounds_done": 0, "total_deleted": 0, "total_synced": 0, "total_failed": 0,
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

    def start(self, threads: int = DEFAULT_THREADS) -> dict:
        with self._lock:
            if self._runner and self._runner.is_alive():
                return self.get()
            try:
                threads = int(threads)
            except (TypeError, ValueError):
                threads = DEFAULT_THREADS
            threads = max(MIN_THREADS, min(threads, MAX_THREADS))
            self._enabled = True
            self._logs = []
            self._stats = self._empty_stats()
            self._stats["job_id"] = uuid.uuid4().hex
            self._stats["running"] = True
            self._stats["threads"] = threads
            self._stats["started_at"] = _now()
            self._stats["updated_at"] = _now()
            self._runner = threading.Thread(
                target=self._run, args=(threads,), daemon=True, name="account-inspect")
            self._runner.start()
            return self.get()

    def stop(self) -> dict:
        with self._lock:
            self._enabled = False
            self._append_log("已请求停止巡检，正在结束当前账号处理", "yellow")
            return self.get()

    def _interruptible_sleep(self, secs: int) -> None:
        for _ in range(max(0, int(secs))):
            if not self._enabled:
                return
            time.sleep(1)

    def _reset_round(self, round_no: int) -> None:
        with self._lock:
            self._stats["round"] = round_no
            self._stats["total"] = 0
            self._stats["deleted"] = 0
            self._stats["matched"] = 0
            self._stats["synced"] = 0
            self._stats["failed"] = 0
            self._stats["skipped"] = 0
            self._stats["updated_at"] = _now()

    def _run(self, threads: int) -> None:
        round_no = 0
        try:
            while self._enabled:
                round_no += 1
                self._reset_round(round_no)
                self._append_log(
                    f"========== 第 {round_no} 轮巡检开始（线程 {threads}）==========", "green")
                self._do_inspect(threads)
                with self._lock:
                    self._stats["rounds_done"] = round_no
                    td = self._stats.get("total_deleted", 0)
                    ts = self._stats.get("total_synced", 0)
                    tf = self._stats.get("total_failed", 0)
                    self._stats["updated_at"] = _now()
                if not self._enabled:
                    break
                self._append_log(
                    f"第 {round_no} 轮结束（累计 删{td} 推{ts} 败{tf}），{ROUND_INTERVAL_SECONDS}s 后开始下一轮",
                    "info")
                self._interruptible_sleep(ROUND_INTERVAL_SECONDS)
        except Exception as exc:
            self._append_log(f"巡检异常终止: {type(exc).__name__}: {exc}", "red")
            logger.debug({"event": "inspect_run_error", "error": repr(exc)})
        finally:
            with self._lock:
                self._enabled = False
                self._stats["running"] = False
                self._stats["finished_at"] = _now()
                self._stats["updated_at"] = _now()
            self._append_log(f"巡检已停止（共完成 {round_no} 轮）", "yellow")

    def _do_inspect(self, threads: int) -> None:
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

        remote = sub2api_service.list_group_accounts(server)
        self._append_log(f"拉取 sub2api group {group_id} 账号：共 {len(remote)} 个", "info")
        self._bump(total=len(remote))

        err_accounts = [a for a in remote if str(a.get("status")) == "error"]
        self._append_log(f"[阶段1] 待删除错误账号：{len(err_accounts)} 个（线程 {threads}）", "info")
        self._run_stage1(server, err_accounts, threads)
        if not self._enabled:
            return

        ok_emails = {
            str(a.get("email") or "").strip().lower()
            for a in remote
            if str(a.get("status")) != "error" and str(a.get("email") or "").strip()
        }
        local_accounts = account_service.list_accounts()
        to_sync = []
        for acc in local_accounts:
            email = str(acc.get("email") or "").strip()
            token = str(acc.get("access_token") or "").strip()
            if not email or not token:
                continue
            if email.lower() in ok_emails:
                continue
            to_sync.append(acc)
        skipped = len(local_accounts) - len(to_sync)
        self._bump(matched=len(to_sync), skipped=skipped)
        self._append_log(
            f"[阶段2] ChatGPT2API 号池 {len(local_accounts)} 个：需补推 {len(to_sync)} 个，"
            f"跳过(sub2api 已有) {skipped} 个（线程 {threads}）",
            "info")
        self._run_stage2(server, to_sync, workspace_id, group_ids, do_verify, threads)

        with self._lock:
            deleted = self._stats.get("deleted", 0)
            synced = self._stats.get("synced", 0)
            failed = self._stats.get("failed", 0)
        self._append_log(
            f"本轮完成：删除 {deleted}，更新 {synced}，失败 {failed}，跳过 {skipped}", "green")

    def _run_stage1(self, server: dict, err_accounts: list, threads: int) -> None:
        if not err_accounts:
            return
        deleted = 0

        def _del_one(a: dict):
            if not self._enabled:
                return None
            label = a.get("email") or a.get("name") or a.get("id")
            try:
                sub2api_service.delete_account(server, str(a.get("id")))
                self._append_log(f"已删除错误账号：{label}", "info")
                return True
            except Exception as exc:
                self._append_log(f"删除失败 {label}：{exc}", "red")
                logger.debug({"event": "inspect_delete_error", "id": a.get("id"), "error": repr(exc)})
                return False

        with ThreadPoolExecutor(max_workers=threads) as ex:
            futs = [ex.submit(_del_one, a) for a in err_accounts]
            for fut in as_completed(futs):
                try:
                    ok = fut.result()
                except Exception:
                    ok = False
                if ok:
                    deleted += 1
                with self._lock:
                    self._stats["deleted"] = deleted
                    if ok:
                        self._stats["total_deleted"] = self._stats.get("total_deleted", 0) + 1
                    self._stats["updated_at"] = _now()

    def _run_stage2(self, server: dict, to_sync: list, workspace_id: str,
                    group_ids: list, do_verify: bool, threads: int) -> None:
        if not to_sync:
            return
        from services.register import openai_register
        from services.openai_backend_api import OpenAIBackendAPI
        from services.register.postprocess import build_sub2api_account

        synced = 0
        failed = 0

        def _sync_one(acc: dict):
            if not self._enabled:
                return None
            email = str(acc.get("email") or "").strip()
            old_token = str(acc.get("access_token") or "").strip()
            if not old_token:
                return None
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
                self._append_log(f"已更新令牌 + join 空间 + 推送 sub2api：{email}", "green")
                return True
            except Exception as exc:
                self._append_log(f"处理失败 {email}：{type(exc).__name__}: {exc}", "red")
                logger.debug({"event": "inspect_sync_error", "email": email, "error": repr(exc)})
                return False

        with ThreadPoolExecutor(max_workers=threads) as ex:
            futs = [ex.submit(_sync_one, acc) for acc in to_sync]
            for fut in as_completed(futs):
                try:
                    r = fut.result()
                except Exception:
                    r = False
                if r is True:
                    synced += 1
                elif r is False:
                    failed += 1
                with self._lock:
                    self._stats["synced"] = synced
                    self._stats["failed"] = failed
                    if r is True:
                        self._stats["total_synced"] = self._stats.get("total_synced", 0) + 1
                    elif r is False:
                        self._stats["total_failed"] = self._stats.get("total_failed", 0) + 1
                    self._stats["updated_at"] = _now()


inspect_service = InspectService()
