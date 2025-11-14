# src/c400g_ptz/ptz.py

import logging
import time
from typing import Optional, Any

from onvif import ONVIFCamera
from onvif.exceptions import ONVIFError


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _is_remote_disconnect_error(exc: Exception) -> bool:
    txt = repr(exc)
    return (
        "RemoteDisconnected" in txt
        or "Connection aborted" in txt
        or "MaxRetryError" in txt
    )


def _safe_onvif_call(func, params: dict, *, label: str) -> Optional[Any]:
    try:
        return func(params)
    except ONVIFError as exc:
        if _is_remote_disconnect_error(exc):
            logger.warning(
                "[C400GPTZ] %s: RemoteDisconnected/Connection aborted "
                "(command probably executed)",
                label,
            )
            return None
        raise


class C400GPTZ:
    def __init__(
        self,
        ip: str,
        port: int,
        user: str,
        password: str,
        *,
        profile_index: int = 0,
        default_step_time: float = 0.3,
        log: Optional[logging.Logger] = None,
    ) -> None:
        self.ip = ip
        self.port = port
        self.user = user
        self.profile_index = profile_index
        self.default_step_time = float(default_step_time)
        self._log = log or logger

        self._log.info("[C400GPTZ] connecting %s:%d", ip, port)
        self._camera = ONVIFCamera(
            ip, port, user, password,
            no_cache=True,
        )

        media = self._camera.create_media_service()
        profiles = media.GetProfiles()
        if not profiles:
            raise RuntimeError("no ONVIF media profiles")

        if profile_index < 0 or profile_index >= len(profiles):
            raise ValueError(
                f"profile_index={profile_index} out of range "
                f"(profiles={len(profiles)})"
            )

        profile = profiles[profile_index]
        self._profile = profile
        self._profile_token = profile.token

        self._log.info(
            "[C400GPTZ] using profile index=%d token=%s name=%s",
            profile_index,
            self._profile_token,
            getattr(profile, "Name", None),
        )

        self._ptz = self._camera.create_ptz_service()
        self._log.debug(
            "[C400GPTZ] ptz xaddr=%s",
            getattr(self._ptz, "xaddr", None),
        )

    @staticmethod
    def _direction_to_velocity(direction: str) -> tuple[float, float]:
        d = direction.lower()
        pan = 0.0
        tilt = 0.0

        if d == "left":
            pan = 1.0
        elif d == "right":
            pan = -1.0
        elif d == "up":
            tilt = 1.0
        elif d == "down":
            tilt = -1.0
        else:
            raise ValueError(f"invalid direction: {direction!r}")

        return pan, tilt

    def step(self, direction: str, *, duration: Optional[float] = None) -> None:
        if duration is None:
            duration = self.default_step_time
        duration = float(duration)
        if duration <= 0:
            raise ValueError("duration must be > 0")

        pan, tilt = self._direction_to_velocity(direction)

        vel = {"PanTilt": {"x": pan, "y": tilt}, "Zoom": {"x": 0.0}}
        params_move = {"ProfileToken": self._profile_token, "Velocity": vel}
        params_stop = {"ProfileToken": self._profile_token}

        self._log.info(
            "[C400GPTZ] step dir=%s dur=%.3fs pan=%.1f tilt=%.1f",
            direction,
            duration,
            pan,
            tilt,
        )

        _safe_onvif_call(self._ptz.ContinuousMove, params_move, label="ContinuousMove(step)")
        time.sleep(duration)
        _safe_onvif_call(self._ptz.Stop, params_stop, label="Stop(step)")

    def left(self, duration: Optional[float] = None) -> None:
        self.step("left", duration=duration)

    def right(self, duration: Optional[float] = None) -> None:
        self.step("right", duration=duration)

    def up(self, duration: Optional[float] = None) -> None:
        self.step("up", duration=duration)

    def down(self, duration: Optional[float] = None) -> None:
        self.step("down", duration=duration)

    def start_move(self, direction: str) -> None:
        pan, tilt = self._direction_to_velocity(direction)

        vel = {"PanTilt": {"x": pan, "y": tilt}, "Zoom": {"x": 0.0}}
        params_move = {"ProfileToken": self._profile_token, "Velocity": vel}

        self._log.info(
            "[C400GPTZ] start_move dir=%s pan=%.1f tilt=%.1f",
            direction,
            pan,
            tilt,
        )

        _safe_onvif_call(self._ptz.ContinuousMove, params_move, label="ContinuousMove(start_move)")

    def stop(self) -> None:
        params_stop = {"ProfileToken": self._profile_token}
        self._log.info("[C400GPTZ] stop")
        _safe_onvif_call(self._ptz.Stop, params_stop, label="Stop")
