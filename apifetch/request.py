import abc
import signal
import time
from typing import List


class RateLimiterInterface(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "is_rejected")
            and callable(subclass.is_rejected)
            or NotImplemented
        )

    @abc.abstractmethod
    def is_rejected(self):
        """Load in the data set"""
        raise NotImplementedError


class RequestStrategy(object):

    tries = 1
    total_time = None

    # In case you need to consider some code(s) between 400 and 599 as
    # "normal" (e.g. for API calls returning empty response as 404)
    normal_codes: List[str] = []

    # In case some codes should not be retried (e.g. a 401 or 403 is
    # unlikely to get better after a retry).
    # "DDx" and "Dxx" patterns (e.g. "4xx", "40x") are acceptable.
    fatal_codes: List[str] = []

    backoff_exp = 2
    backoff_mul = 0.5  # with exponent 2, gives: 1, 2, 4, 8, 16, etc.

    rate_limiter = None

    connect_timeout_s = 0.0
    read_timeout_s = 0.0
    kill_timeout_s = 0

    def __init__(self, connect_timeout: float, read_timeout: float, kill_timeout: int):
        self.connect_timeout_s = connect_timeout
        self.read_timeout_s = read_timeout
        self.kill_timeout_s = kill_timeout

    def connect_timeout(self, connect_timeout: float):
        self.connect_timeout_s = connect_timeout
        return self

    def read_timeout(self, read_timeout: float):
        self.read_timeout_s = read_timeout
        return self

    def kill_timeout(self, kill_timeout: int):
        self.kill_timeout_s = kill_timeout
        return self

    def max_tries(self, tries: int):
        self.tries = tries
        return self

    def max_total_time(self, total_time: float):
        self.total_time = total_time
        return self

    def normal_response_codes(self, response_codes: list):
        for code in response_codes:
            if not isinstance(code, str) or int(code) < 400 or int(code) >= 600:
                raise Exception('Invalid option "{}"'.format(code))
        self.normal_codes = response_codes
        return self

    def fatal_response_codes(self, response_codes: list):
        for code in response_codes:
            if not isinstance(code, str) or (code[0:1] != "4" and code[0:1] != "5"):
                raise Exception('Invalid option "{}"'.format(code))
        self.fatal_codes = response_codes
        return self

    def backoff_multiplier(self, multiplier: float):
        self.backoff_mul = multiplier
        return self

    def backoff_exponent(self, exponent: int):
        self.backoff_exp = exponent
        return self

    def rate_limit(self, limiter: RateLimiterInterface):
        self.rate_limiter = limiter
        return self


class LocalGCRA(RateLimiterInterface):
    def __init__(self, emission_interval):
        # emission interval = period of time / rate
        # (e.g. 10 per minute = 60 / 10 = emission interval of 6s

        self.limit = None
        self.emission_interval = emission_interval

    def is_rejected(self):

        ts = time.time()
        jan_1_2020 = 1577836800
        now = ts - jan_1_2020

        tat = self.limit
        if tat is None:
            tat = now

        allow_at = max(tat, now)
        new_tat = allow_at + self.emission_interval

        diff = now - allow_at

        if diff < 0:
            return (
                True,
                round(-1 * diff, 2),
            )
        else:
            self.limit = new_tat
            return (
                False,
                -1,
            )


class SignalTimeout:
    # Thanks to https://stackoverflow.com/a/22156618/8046487

    class SignalTimeoutException(Exception):
        pass

    @staticmethod
    def _timeout(signum, frame):
        raise SignalTimeout.SignalTimeoutException()

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        signal.signal(signal.SIGALRM, SignalTimeout._timeout)

    def __enter__(self):
        signal.alarm(self.timeout)

    def __exit__(self, exc_type, exc_value, traceback):
        signal.alarm(0)
        return exc_type is SignalTimeout.SignalTimeoutException
