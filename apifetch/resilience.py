import abc
import time
from typing import List, Tuple

from requests.models import Request, Response


"""
# Circuit breaker TBC

class RequestContext(object):
    hostname: str
    uri: str
    querystring: dict
    headers: dict

    def __init__(self, req: Request):
        self.hostname = ""
        self.uri = ""
        self.querystring = {}
        self.headers = {}


class ResponseContext(object):
    headers: dict
    # status = success, explicit failure, implicit failure (timeout, transport error, etc.)
    httpcode: str
    # exception: Exception
    total_time: float

    def __init__(
        self, res: Response = None, e: Exception = None, total_time: float = None
    ):
        self.headers = {}
        self.httpcode = ""
        # self.exception = None
        self.total_time = 0.0


class CircuitBreakerInterface(metaclass=abc.ABCMeta):

    STATUS_OPENED = 0
    STATUS_CLOSED = 1
    STATUS_HALF = -1

    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "is_closed")
            and callable(subclass.is_closed)
            and hasattr(subclass, "assess_transaction")
            and callable(subclass.assess_transaction)
            or NotImplemented
        )

    @abc.abstractmethod
    def is_closed(self, req: RequestContext = None) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def assess_transaction(self, req: RequestContext, res: ResponseContext) -> None:
        raise NotImplementedError
"""


class RateLimiterInterface(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "is_rejected")
            and callable(subclass.is_rejected)
            or NotImplemented
        )

    @abc.abstractmethod
    def is_rejected(self) -> Tuple[bool, float]:
        # If [0] is False, go ahead
        # If [0] is True, sleep for [1] seconds
        raise NotImplementedError


class LocalGCRA(RateLimiterInterface):

    limit: float
    emission_interval: float

    def __init__(self, emission_interval):
        # emission interval = period of time / rate
        # (e.g. 10 per minute = 60 / 10 = emission interval of 6s

        self.limit = None
        self.emission_interval = emission_interval

    def is_rejected(self) -> Tuple[bool, float]:

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
