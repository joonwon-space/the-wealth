"""backup_health.py 서비스 유닛 테스트.

_read_latest_backup_mtime() 함수의 파일시스템 경우와
get_last_backup_info() 의 DB 폴백 로직을 검증한다.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# _read_latest_backup_mtime — filesystem helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReadLatestBackupMtime:
    def test_returns_none_when_directory_missing(self) -> None:
        """존재하지 않는 디렉토리는 None 을 반환해야 한다."""
        with patch.dict(os.environ, {"BACKUP_DIR": "/nonexistent/path/xyz"}):
            # Re-import inside test so the env variable is picked up
            import importlib
            import app.services.backup_health as bh

            importlib.reload(bh)
            result = bh._read_latest_backup_mtime()

        assert result is None

    def test_returns_none_when_no_dump_files(self, tmp_path: Path) -> None:
        """daily/ 디렉토리에 .dump 파일이 없으면 None 을 반환해야 한다."""
        daily = tmp_path / "daily"
        daily.mkdir()

        with patch.dict(os.environ, {"BACKUP_DIR": str(tmp_path)}):
            import importlib
            import app.services.backup_health as bh

            importlib.reload(bh)
            result = bh._read_latest_backup_mtime()

        assert result is None

    def test_returns_mtime_of_newest_dump(self, tmp_path: Path) -> None:
        """여러 .dump 파일 중 가장 최신 파일의 mtime 을 반환해야 한다."""
        daily = tmp_path / "daily"
        daily.mkdir()

        older = daily / "backup_2026-03-19.dump"
        newer = daily / "backup_2026-03-20.dump"

        older.write_bytes(b"old")
        newer.write_bytes(b"new")

        # Force mtime difference
        os.utime(older, (time.time() - 7200, time.time() - 7200))
        os.utime(newer, (time.time() - 3600, time.time() - 3600))

        with patch.dict(os.environ, {"BACKUP_DIR": str(tmp_path)}):
            import importlib
            import app.services.backup_health as bh

            importlib.reload(bh)
            result = bh._read_latest_backup_mtime()

        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        # The newer file should be chosen (mtime closer to now)
        assert result >= datetime.fromtimestamp(
            newer.stat().st_mtime - 1, tz=timezone.utc
        )

    def test_returns_utc_datetime(self, tmp_path: Path) -> None:
        """반환 값은 UTC timezone-aware datetime 이어야 한다."""
        daily = tmp_path / "daily"
        daily.mkdir()
        dump = daily / "backup.dump"
        dump.write_bytes(b"data")

        with patch.dict(os.environ, {"BACKUP_DIR": str(tmp_path)}):
            import importlib
            import app.services.backup_health as bh

            importlib.reload(bh)
            result = bh._read_latest_backup_mtime()

        assert result is not None
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_returns_none_on_permission_error(self, tmp_path: Path) -> None:
        """PermissionError 발생 시 None 을 반환해야 한다."""
        daily = tmp_path / "daily"
        daily.mkdir()

        with patch("pathlib.Path.glob", side_effect=PermissionError("denied")):
            with patch.dict(os.environ, {"BACKUP_DIR": str(tmp_path)}):
                import importlib
                import app.services.backup_health as bh

                importlib.reload(bh)
                result = bh._read_latest_backup_mtime()

        assert result is None


# ---------------------------------------------------------------------------
# get_last_backup_info — integration / DB fallback
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetLastBackupInfo:
    async def test_returns_null_when_no_backup_anywhere(self) -> None:
        """파일시스템과 DB 모두 백업 없으면 null 반환."""
        import importlib
        import app.services.backup_health as bh

        importlib.reload(bh)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch.object(bh, "_read_latest_backup_mtime", return_value=None):
            result = await bh.get_last_backup_info(mock_db)

        assert result["last_backup_at"] is None
        assert result["backup_age_hours"] is None

    async def test_uses_filesystem_mtime_first(self) -> None:
        """파일시스템 mtime 이 있으면 DB 쿼리를 건너뛰어야 한다."""
        import importlib
        import app.services.backup_health as bh

        importlib.reload(bh)

        fake_dt = datetime(2026, 3, 20, 2, 0, 0, tzinfo=timezone.utc)
        mock_db = AsyncMock(spec=AsyncSession)

        with patch.object(bh, "_read_latest_backup_mtime", return_value=fake_dt):
            result = await bh.get_last_backup_info(mock_db)

        # DB should not have been called
        mock_db.execute.assert_not_called()
        assert result["last_backup_at"] is not None
        assert result["backup_age_hours"] is not None

    async def test_falls_back_to_db_when_no_filesystem(self) -> None:
        """파일시스템 백업 없을 때 DB 에서 조회해야 한다."""
        import importlib
        import app.services.backup_health as bh

        importlib.reload(bh)

        fake_dt = datetime(2026, 3, 19, 12, 0, 0, tzinfo=timezone.utc)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_dt
        mock_db.execute.return_value = mock_result

        with patch.object(bh, "_read_latest_backup_mtime", return_value=None):
            result = await bh.get_last_backup_info(mock_db)

        mock_db.execute.assert_called_once()
        assert result["last_backup_at"] is not None

    async def test_backup_age_hours_is_positive_float(self) -> None:
        """backup_age_hours 는 양의 float 값이어야 한다."""
        import importlib
        import app.services.backup_health as bh

        importlib.reload(bh)

        # 1 hour ago
        one_hour_ago = datetime.now(tz=timezone.utc).replace(
            second=0, microsecond=0
        )
        # Subtract 3600 seconds manually to avoid mutating datetime
        from datetime import timedelta

        one_hour_ago = one_hour_ago - timedelta(hours=1)

        mock_db = AsyncMock(spec=AsyncSession)

        with patch.object(
            bh, "_read_latest_backup_mtime", return_value=one_hour_ago
        ):
            result = await bh.get_last_backup_info(mock_db)

        age = result["backup_age_hours"]
        assert age is not None
        assert isinstance(age, float)
        assert 0.9 <= age <= 1.2  # Allow some clock skew tolerance

    async def test_backup_age_hours_rounded_to_2_decimals(self) -> None:
        """backup_age_hours 는 소수점 2자리로 반올림되어야 한다."""
        import importlib
        import app.services.backup_health as bh

        importlib.reload(bh)

        from datetime import timedelta

        fake_dt = datetime.now(tz=timezone.utc) - timedelta(seconds=5400)  # 1.5h

        mock_db = AsyncMock(spec=AsyncSession)

        with patch.object(bh, "_read_latest_backup_mtime", return_value=fake_dt):
            result = await bh.get_last_backup_info(mock_db)

        age = result["backup_age_hours"]
        assert age is not None
        assert age == round(age, 2)

    async def test_db_exception_returns_null(self) -> None:
        """DB 쿼리 예외 발생 시 null 을 반환해야 한다 (graceful degradation)."""
        import importlib
        import app.services.backup_health as bh

        importlib.reload(bh)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.side_effect = Exception("DB connection lost")

        with patch.object(bh, "_read_latest_backup_mtime", return_value=None):
            result = await bh.get_last_backup_info(mock_db)

        assert result["last_backup_at"] is None
        assert result["backup_age_hours"] is None
