"""Push-to-talk keyboard session for the Mac voice client."""

from __future__ import annotations

import os
import queue
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
from pynput import keyboard

from emberforge.client.recording import record_while_active

DEFAULT_PTT_KEY = "space"

# macOS often delivers PTT keys as KeyCode(vk=...) while we configure Key.*.
_KEY_VK_ALIASES: dict[keyboard.Key, frozenset[int]] = {
    keyboard.Key.space: frozenset({49}),
    keyboard.Key.enter: frozenset({36, 76}),
    keyboard.Key.f5: frozenset({96}),
}

_LISTENING_INDICATOR = "\r\033[7m ● LISTENING \033[27m release when done\033[K"
_CLEAR_LISTENING_LINE = "\r\033[K"


class SessionEventType(str, Enum):
    AUDIO = "audio"
    COMMAND = "command"
    TYPING = "typing"
    STOP = "stop"


@dataclass(frozen=True)
class SessionEvent:
    type: SessionEventType
    audio: Optional[np.ndarray] = None


def resolve_ptt_key(name: str) -> keyboard.Key | keyboard.KeyCode:
    normalized = name.strip().lower()
    aliases = {
        "space": keyboard.Key.space,
        "spc": keyboard.Key.space,
        "enter": keyboard.Key.enter,
        "return": keyboard.Key.enter,
        "backtick": keyboard.KeyCode.from_char("`"),
        "`": keyboard.KeyCode.from_char("`"),
        "f5": keyboard.Key.f5,
    }
    if normalized in aliases:
        return aliases[normalized]
    if len(normalized) == 1:
        return keyboard.KeyCode.from_char(normalized)
    raise ValueError(f"Unsupported PTT key: {name}")


def keys_equal(
    observed: keyboard.Key | keyboard.KeyCode | None,
    expected: keyboard.Key | keyboard.KeyCode,
) -> bool:
    """Match keys across macOS press/release event shape differences."""
    if observed is None:
        return False
    if observed == expected:
        return True

    observed_vk = getattr(observed, "vk", None)
    expected_vk = getattr(expected, "vk", None)
    if observed_vk is not None and expected_vk is not None and observed_vk == expected_vk:
        return True

    if isinstance(expected, keyboard.Key):
        aliases = _KEY_VK_ALIASES.get(expected)
        if aliases and observed_vk in aliases:
            return True

    observed_char = getattr(observed, "char", None)
    expected_char = getattr(expected, "char", None)
    if observed_char and expected_char and observed_char == expected_char:
        return True

    return False


def is_typing_key(key: keyboard.Key | keyboard.KeyCode) -> bool:
    """True for printable characters the user might be typing at the prompt."""
    return isinstance(key, keyboard.KeyCode) and bool(key.char) and key.char.isprintable()


def ptt_key_virtual_codes(ptt_key: keyboard.Key | keyboard.KeyCode) -> frozenset[int]:
    """macOS virtual key codes for the configured PTT key."""
    if isinstance(ptt_key, keyboard.Key):
        aliases = _KEY_VK_ALIASES.get(ptt_key)
        if aliases:
            return aliases
    vk = getattr(ptt_key, "vk", None)
    if vk is not None:
        return frozenset({vk})
    return frozenset()


def should_suppress_ptt_vk(*, command_mode: bool, vk: int, ptt_vks: frozenset[int]) -> bool:
    """Return True when a key event should be swallowed before it reaches the terminal."""
    if command_mode:
        return False
    return vk in ptt_vks


def show_listening_indicator() -> None:
    """In-place listening hint on stderr (no terminal spaces)."""
    sys.stderr.write(_LISTENING_INDICATOR)
    sys.stderr.flush()


def clear_listening_indicator(suffix: str = "") -> None:
    """Clear the listening line; optional suffix (e.g. capture summary)."""
    sys.stderr.write(_CLEAR_LISTENING_LINE + suffix)
    if suffix:
        sys.stderr.write("\n")
    sys.stderr.flush()


class PushToTalkSession:
    """
    Hold-to-talk session aligned with future hardware button semantics.

    - Hold the PTT key (default: Space) to record
    - Start typing (or tap Enter) to enter a command or quoted prompt
    """

    def __init__(
        self,
        *,
        ptt_key: keyboard.Key | keyboard.KeyCode | None = None,
        can_record: Callable[[], bool] | None = None,
        on_listening: Callable[[], None] | None = None,
        on_finished: Callable[[float], None] | None = None,
    ) -> None:
        key_name = os.getenv("EMBER_PTT_KEY", DEFAULT_PTT_KEY)
        self._ptt_key = ptt_key or resolve_ptt_key(key_name)
        self._ptt_vks = ptt_key_virtual_codes(self._ptt_key)
        self._can_record = can_record or (lambda: True)
        self._on_listening = on_listening or show_listening_indicator
        self._on_finished = on_finished
        self._held = threading.Event()
        self._recording = False
        self._command_mode = False
        self._line_input_pending = False
        self._stop = False
        self._events: queue.Queue[SessionEvent] = queue.Queue()
        self._listener: keyboard.Listener | None = None
        self._record_lock = threading.Lock()

    @property
    def command_mode(self) -> bool:
        return self._command_mode

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def ptt_key_label(self) -> str:
        return describe_ptt_key(self._ptt_key)

    def enter_command_mode(self) -> None:
        self._command_mode = True

    def leave_command_mode(self) -> None:
        self._command_mode = False

    def clear_line_input_pending(self) -> None:
        self._line_input_pending = False

    def _begin_line_input(self) -> None:
        if self._line_input_pending:
            return
        self.enter_command_mode()
        self._line_input_pending = True
        self._events.put(SessionEvent(SessionEventType.TYPING))

    def request_stop(self) -> None:
        self._stop = True
        self._release_hold()

    def _release_hold(self) -> None:
        self._held.clear()

    def _start_recording(self) -> None:
        with self._record_lock:
            if self._recording or self._command_mode or self._stop:
                return
            self._recording = True

        def _run() -> None:
            try:
                audio = record_while_active(
                    self._held.is_set,
                    on_listening=self._on_listening,
                    on_finished=self._on_finished,
                )
                if audio is not None:
                    self._events.put(SessionEvent(SessionEventType.AUDIO, audio=audio))
                else:
                    clear_listening_indicator()
            finally:
                with self._record_lock:
                    self._recording = False
                # Reset hold state so a missed release event cannot wedge the session.
                self._release_hold()

        threading.Thread(target=_run, name="emberforge-ptt-record", daemon=True).start()

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if self._stop or self._command_mode:
            return

        if keys_equal(key, self._ptt_key):
            if not self._can_record():
                return
            if self._recording:
                return
            if not self._held.is_set():
                self._held.set()
                self._start_recording()
            return

        if keys_equal(key, keyboard.Key.enter):
            with self._record_lock:
                if not self._held.is_set() and not self._recording:
                    self._events.put(SessionEvent(SessionEventType.COMMAND))
            return

        if is_typing_key(key):
            with self._record_lock:
                if not self._held.is_set() and not self._recording:
                    self._begin_line_input()

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if keys_equal(key, self._ptt_key):
            self._release_hold()

    def _darwin_intercept(self, event_type, event):
        """Swallow PTT key events on macOS so Space does not print in the terminal."""
        from Quartz import (
            CGEventGetIntegerValueField,
            kCGEventKeyDown,
            kCGEventKeyUp,
            kCGKeyboardEventKeycode,
        )

        if event_type not in (kCGEventKeyDown, kCGEventKeyUp):
            return event

        vk = int(CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode))
        if should_suppress_ptt_vk(
            command_mode=self._command_mode,
            vk=vk,
            ptt_vks=self._ptt_vks,
        ):
            return None
        return event

    def _listener_kwargs(self) -> dict:
        if sys.platform == "darwin":
            return {"darwin_intercept": self._darwin_intercept}
        return {}

    def start(self) -> None:
        if self._listener is not None:
            return
        # Selective PTT suppression on macOS — global suppress wedges the keyboard.
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            **self._listener_kwargs(),
        )
        self._listener.start()

    def stop(self) -> None:
        self.request_stop()
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def wait_event(self, timeout: float = 0.1) -> SessionEvent | None:
        try:
            return self._events.get(timeout=timeout)
        except queue.Empty:
            return None


def describe_ptt_key(key: keyboard.Key | keyboard.KeyCode) -> str:
    if key == keyboard.Key.space:
        return "SPACE"
    if key == keyboard.Key.enter:
        return "ENTER"
    if isinstance(key, keyboard.KeyCode) and key.char:
        return key.char.upper()
    return str(key)