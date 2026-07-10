import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

import ntplib
from zoneinfo import ZoneInfo


logger = logging.getLogger(__name__)


class SirimTime:
    """
    Provides Malaysia time synchronized with SIRIM NTP servers.

    The NTP server is not contacted every time sirim_now() is called.
    Instead, the time offset is cached and periodically refreshed.
    """

    _hosts = [
        "ntp1.sirim.my",
        "ntp2.sirim.my",
    ]

    _malaysia_timezone = ZoneInfo("Asia/Kuala_Lumpur")

    _offset = timedelta(0)
    _has_synced = False
    _last_synced_at: Optional[datetime] = None

    _lock = threading.Lock()

    # Re-sync after 30 minutes
    _sync_interval_seconds = 30 * 60

    # NTP request timeout
    _timeout_seconds = 3

    @classmethod
    def sync(cls, force: bool = False) -> bool:
        """
        Synchronize the backend time with a SIRIM NTP server.

        Args:
            force:
                True  = always contact the NTP server.
                False = use the cached offset when it is still valid.

        Returns:
            True when synchronization is available.
            False when all SIRIM servers fail.
        """

        with cls._lock:
            if not force and cls._is_sync_still_valid():
                return True

            client = ntplib.NTPClient()

            for host in cls._hosts:
                try:
                    response = client.request(
                        host,
                        version=3,
                        timeout=cls._timeout_seconds,
                    )

                    # response.offset is the difference between:
                    # NTP server time and this server's system time.
                    cls._offset = timedelta(seconds=response.offset)
                    cls._has_synced = True
                    cls._last_synced_at = datetime.now(
                        tz=cls._malaysia_timezone
                    )

                    logger.info(
                        "[SirimTime] Sync successful through %s. "
                        "Offset: %.3f ms",
                        host,
                        response.offset * 1000,
                    )

                    return True

                except Exception as error:
                    logger.warning(
                        "[SirimTime] Sync failed through %s: %s",
                        host,
                        error,
                    )

            # Keep the previous valid offset when synchronization later fails.
            if cls._has_synced:
                logger.warning(
                    "[SirimTime] Unable to refresh SIRIM time. "
                    "Using the previously synchronized offset."
                )
                return True

            logger.error(
                "[SirimTime] Unable to synchronize with all SIRIM servers. "
                "Using Malaysia system time as fallback."
            )

            return False

    @classmethod
    def now(cls) -> datetime:
        """
        Return the current Malaysia time adjusted using the SIRIM offset.

        This method automatically refreshes the SIRIM offset when required.
        """

        cls.sync()

        malaysia_system_time = datetime.now(
            tz=cls._malaysia_timezone
        )

        return malaysia_system_time + cls._offset

    @classmethod
    def now_naive(cls) -> datetime:
        """
        Return SIRIM Malaysia time without timezone information.

        Use this when the existing SQLAlchemy database columns use
        DATETIME without timezone support.
        """

        return cls.now().replace(tzinfo=None)

    @classmethod
    def has_synced(cls) -> bool:
        return cls._has_synced

    @classmethod
    def offset(cls) -> timedelta:
        return cls._offset

    @classmethod
    def last_synced_at(cls) -> Optional[datetime]:
        return cls._last_synced_at

    @classmethod
    def _is_sync_still_valid(cls) -> bool:
        if not cls._has_synced or cls._last_synced_at is None:
            return False

        current_time = datetime.now(
            tz=cls._malaysia_timezone
        )

        elapsed = (
            current_time - cls._last_synced_at
        ).total_seconds()

        return elapsed < cls._sync_interval_seconds


def sirim_now() -> datetime:
    """
    Shortcut for timezone-aware SIRIM Malaysia time.
    """

    return SirimTime.now()


def sirim_now_naive() -> datetime:
    """
    Shortcut for timezone-naive SIRIM Malaysia time.

    Recommended for existing MySQL DATETIME columns.
    """

    return SirimTime.now_naive()


def sync_sirim_time(force: bool = False) -> bool:
    """
    Manually synchronize with the SIRIM NTP servers.
    """

    return SirimTime.sync(force=force)