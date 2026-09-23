# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Monitor-specific `EspLog` subclass that preserves the legacy `--- ` style.

Use ``log.print(..., style='yellow')`` for primary monitor lines.
Use ``log.note`` for secondary FYI asides (e.g. configuration decisions, state toggles, side-channel progress).
Keep ``log.warn`` / ``log.err`` for problems; help/menu chrome may use ``style='red bold'``.
"""

import re

from esp_pylib.logger import EspLog

COMMON_PREFIX = '---'

# Opening Rich markup tag at the start of a one-line message, e.g. ``[bold yellow]``.
_RICH_OPEN_TAG = re.compile(r'^\[([^/\]][^[]*)\]')


def add_common_prefix(message: str) -> str:
    """Prepend ``COMMON_PREFIX`` to a one-line message, inside a leading Rich open tag.

    Idempotent: if the message already carries the marker it is returned
    unchanged
    """
    if not message.strip() or message == '.':
        return message
    first_line = message.splitlines()[0]
    if first_line.startswith(COMMON_PREFIX) or f'{COMMON_PREFIX} ' in first_line:
        return message
    match = _RICH_OPEN_TAG.match(message)
    if match:
        return f'{match.group(0)}{COMMON_PREFIX} {message[match.end() :]}'
    return ''.join([f'{COMMON_PREFIX} {line}' for line in message.splitlines(keepends=True)])


class MonitorLog(EspLog):
    """`EspLog` proxy subclass that emits the monitor's `--- ` style on stderr."""

    def __init__(self):
        super().__init__()
        self.set_console_options(soft_wrap=True)

    @property
    def stdout(self):
        """Route ordinary monitor output to stderr; stdout carries chip bytes."""
        return self.stderr

    def print(self, *args, **kwargs) -> None:
        """Add the common ``--- `` prefix to the message and print it."""
        # Join parts with Rich's default ``sep=' '`` so ``log.note`` / ``log.warn`` /
        # ``log.err`` keep a space after their ``NOTE:`` / ``WARNING:`` / ``ERROR:`` prefixes.
        sep = kwargs.pop('sep', ' ')
        super().print(add_common_prefix(sep.join(args)), **kwargs)

    def counter_line(self, prefix: str, suffix: str, *, final: bool = False) -> None:
        """Add the common ``--- `` prefix to live counter / progress lines."""
        message = add_common_prefix(f'{prefix}{suffix}')
        super().counter_line(message, '', final=final)


def install_monitor_log(force_color: bool = False) -> None:
    """Install (or re-install) `MonitorLog` as the global `esp_pylib` logger.

    ``MonitorLog`` inherits `EspLog`'s per-class singleton behaviour, so
    ``MonitorLog()`` always returns the same instance.
    """
    monitor_log = MonitorLog()
    monitor_log.set_console_options(soft_wrap=True, force_terminal=True if force_color else None)
    EspLog.set_logger(monitor_log)
