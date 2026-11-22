"""Keep signed test values independent of wall-clock adjustments."""

from time import monotonic, time
from unittest.mock import patch

from itsdangerous import TimestampSigner


def use_stable_signing_clock(test_case):
    started_at = monotonic()
    wall_time = time()

    def timestamp(_signer):
        return int(wall_time + (monotonic() - started_at))

    # Flask sessions and Flask-WTF tokens share this signer. Keep real signature
    # validation and expiration, and restore the original signer after each test.
    test_case.enterContext(patch.object(TimestampSigner, "get_timestamp", timestamp))
