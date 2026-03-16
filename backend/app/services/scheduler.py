"""APScheduler 기반 자동 동기화 스케줄러.

FastAPI 앱 startup/shutdown 이벤트에 연결하여 사용합니다.

NOTE: 실제 동기화를 위해서는 사용자별 계좌번호가 필요합니다.
현재는 스케줄러 인프라만 구성하고, 계좌번호 관리 기능 추가 후 활성화하세요.
docs/plan/manual-tasks.md 참고.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _sync_all_accounts() -> None:
    """모든 사용자의 KIS 계좌를 순차 동기화 (추후 구현)."""
    logger.info("[Scheduler] Starting periodic KIS account sync")
    # TODO: 사용자별 계좌번호 저장 기능 추가 후 구현
    # users = await fetch_all_users_with_kis_credentials()
    # for user, portfolio, account_no in users:
    #     await sync_portfolio(user, portfolio, account_no)


def start_scheduler() -> None:
    scheduler.add_job(
        _sync_all_accounts,
        trigger="interval",
        hours=1,
        id="kis_sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[Scheduler] APScheduler started — KIS sync every 1 hour")


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("[Scheduler] APScheduler stopped")
