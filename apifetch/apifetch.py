import requests
import cchardet
import urllib
import logging
import time
import math
from .request import RequestStrategy, SignalTimeout
from .log import LogStrategy, Timer
from .exceptions import RequestFailure, RequestTimeout

# Monkey-patch requests to have it use cchardet instead of chardet
# cf https://github.com/psf/requests/issues/2359#issuecomment-552736992
class ForceCchardet:
    @property
    def apparent_encoding(obj):
        return cchardet.detect(obj.content)["encoding"]


requests.Response.apparent_encoding = ForceCchardet.apparent_encoding

logger = logging.getLogger(__name__)


def get(url, **kwargs):
    return request_url("get", url, **kwargs)


def post(url, **kwargs):
    return request_url("post", url, **kwargs)


def request_url(method, url, strategy: RequestStrategy, log: LogStrategy, **kwargs):

    tries = 0
    start_ts = time.perf_counter()
    while tries < strategy.tries:

        # Exponential backoff sleep (need to explicitly skip it the first time, as otherwise x^0 = 1)
        if tries > 0:
            to_sleep = strategy.backoff_mul * strategy.backoff_exp ** tries
            # Quick check to ensure we won't already be timed out when finished sleeping
            if (
                strategy.total_time
                and strategy.total_time - (time.perf_counter() - start_ts) - to_sleep
                <= 0
            ):
                raise RequestFailure(
                    "Total timeout of {} seconds would get reached after exponential backoff".format(
                        strategy.total_time
                    )
                )
            logger.debug(
                "Try #{} failed, sleeping {} seconds before retry.".format(
                    tries, to_sleep
                )
            )
            time.sleep(to_sleep)

        tries += 1
        try:
            new_kill_timeout = strategy.kill_timeout
            if strategy.total_time:
                max_time_left = strategy.total_time - (time.perf_counter() - start_ts)
                if max_time_left <= 0:
                    raise RequestFailure(
                        "Total timeout of {} seconds reached".format(
                            strategy.total_time
                        )
                    )
                # set a kill timeout as the min between the explicit kill timeout (if any) and max time left (if any)
                new_kill_timeout = math.ceil(min(max_time_left, strategy.kill_timeout))

            logger.debug("Try #{} (of {} maximum)".format(tries, strategy.tries))
            r = _request_url_once(
                method,
                url,
                strategy,
                log,
                override_kill_timeout=new_kill_timeout,
                **kwargs
            )
        except RequestFailure:
            raise  # Game over, no time left
        except (RequestTimeout, requests.exceptions.RequestException) as e:
            logger.debug("Request exception (%s): %s", type(e).__name__, str(e))
            # Low level error, e.g. connection error, socket error, etc. --> retryable
            # Could also be a override_kill_timeout reached --> it will get intercepted when re-entering the loop
            continue  # retry

        if not isinstance(r, requests.Response) or not r.status_code:
            # TODO: log the case, as it is weird
            logger.info("Response has unexpected type {}".format(type(r).__name__))
            continue  # retry

        # If we are here, we have a response, but it could be an HTTP error (500, etc.)
        # 2 special cases:
        # * normal codes: codes in the 400..599 range that actually mean a success
        # * fatal codes: codes that should not be re-tried
        if (
            r.status_code >= 400
            and r.status_code < 600
            and str(r.status_code) not in strategy.normal_codes
        ):  # in the error range
            if (
                str(r.status_code) in strategy.fatal_codes
                or str(r.status_code)[0:2] + "x" in strategy.fatal_codes
                or str(r.status_code)[0:1] + "xx" in strategy.fatal_codes
            ):
                # Fatal, do not retry
                r.raise_for_status()
            else:
                continue  # retry

        # Success: we return the response for further processing
        return r

    # If we end up here, it means we reached the maximum number of tries
    raise RequestFailure("Request failed (total: {} tries)".format(strategy.tries))


def _request_url_once(  # allow to override the kill timeout (to fit in max total time)
    method,
    url,
    strategy: RequestStrategy,
    log: LogStrategy,
    override_kill_timeout=None,
    params=None,
    **kwargs
):
    is_logged = log is not None

    # In the query string, avoid spaces becoming "+" (want "%20" instead)
    if params:
        kwargs["params"] = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

    # Replicating defaults from https://github.com/psf/requests/blob/master/requests/api.py
    if method == "get" or method == "options":
        kwargs.setdefault("allow_redirects", True)
    elif method == "head":
        kwargs.setdefault("allow_redirects", False)

    kwargs["timeout"] = (
        strategy.connect_timeout,
        strategy.read_timeout,
    )

    # We will use a prepared request, to be able to log the raw request even if
    # we do not get a response (e.g. hard timeout or exception)

    # We need to split kwargs in 2, one for the prepared request, the rest for sending
    kwargs_req = {}
    for k, v in kwargs.items():
        # From https://github.com/psf/requests/blob/428f7a275914f60a8f1e76a7d69516d617433d30/requests/models.py#L254
        if k in [
            "method",
            "url",
            "headers",
            "files",
            "data",
            "json",
            "params",
            "auth",
            "cookies",
            "hooks",
        ]:
            kwargs_req.update({k: v})
    for k, v in kwargs_req.items():
        kwargs.pop(k, None)

    s = requests.Session()
    req = requests.Request(method.upper(), url, **kwargs_req)
    prepped = s.prepare_request(req)

    timed_out = True
    r = None
    kill_timeout = (
        override_kill_timeout
        if override_kill_timeout is not None
        else strategy.kill_timeout
    )
    try:
        with SignalTimeout(kill_timeout):
            if is_logged:
                timer = Timer()
                timer.start()

            r = s.send(prepped, **kwargs)

            # If we arrive here, it means we didn't reach the timeout.
            # We have to flag this fact explicitly
            timed_out = False

        if timed_out and r is None:
            raise RequestTimeout("Killed on timeout ({}s)".format(kill_timeout))

    except Exception as e:
        # If we are here, it means the request failed (no response), we log the request
        if is_logged:
            timer.stop()
            log.dump_failed(request=prepped, exception=e, timing=timer)
        raise

    if is_logged:
        timer.stop()
        log.dump(response=r, timing=timer)

    return r
