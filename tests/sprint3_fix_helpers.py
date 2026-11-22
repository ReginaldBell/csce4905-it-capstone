"""Shared helpers for the Sprint 3 patch regression tests. Not collected as a test module."""

import contextlib
import logging
import threading
from unittest import mock


class LogCapture(logging.Handler):
    """Keep formatted log text, including any traceback, for leak checks."""

    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []
        self.levels = []

    def emit(self, record):
        text = record.getMessage()
        if record.exc_info:
            text += logging.Formatter().formatException(record.exc_info)
        self.lines.append(text)
        self.levels.append(record.levelno)

    @property
    def text(self):
        return "\n".join(self.lines)

    @property
    def has_error(self):
        return any(level >= logging.ERROR for level in self.levels)


@contextlib.contextmanager
def captured_logs():
    handler = LogCapture()
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        yield handler
    finally:
        root.removeHandler(handler)


class FakeSMTP:
    """Stands in for smtplib.SMTP, so no test opens a socket.

    With hold=True a worker thread waits inside the connection until settle() runs, which
    models a slow mail server without a sleep. The main thread never waits, so code that
    still sends synchronously fails its assertion instead of stalling the suite.
    """

    WAIT_SECONDS = 5

    def __init__(self, error=None, hold=False):
        self.error = error
        self.hold = hold
        self.server = mock.MagicMock()
        self.server.__enter__.return_value = self.server
        self.server.__exit__.return_value = False
        self.threads = []
        self.release = threading.Event()
        self.before = set(threading.enumerate())

    def __call__(self, *args, **kwargs):
        current = threading.current_thread()
        self.threads.append(current)
        if self.hold and current is not threading.main_thread():
            self.release.wait(self.WAIT_SECONDS)
        if self.error is not None:
            raise self.error
        return self.server

    def settle(self):
        """Let held workers finish, then join every thread started since creation."""
        self.release.set()
        started = [t for t in threading.enumerate()
                   if t not in self.before and t is not threading.current_thread()]
        for thread in started:
            thread.join(self.WAIT_SECONDS)
        return [thread for thread in started if thread.is_alive()]

    @property
    def called(self):
        return bool(self.threads)

    @property
    def sent_messages(self):
        return [call.args[0] for call in self.server.send_message.call_args_list]
