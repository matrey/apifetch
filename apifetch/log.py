# Derived from https://raw.githubusercontent.com/requests/toolbelt/22f424a6d336fb37a416926a6524aa3604bab64d/requests_toolbelt/utils/dump.py
# Copyright 2014 Ian Cordasco, Cory Benfield
# Licensed under the Apache License, Version 2.0

import base64
import time
from datetime import datetime
import secrets

from requests import compat


class Timer(object):
    def start(self):
        self._start_ts = time.perf_counter()
        self.start_date = datetime.utcnow()

    def stop(self):
        self.end_date = datetime.utcnow()
        self.total_time_s = time.perf_counter() - self._start_ts


class HeaderFilter(object):
    # TODO: cookie

    stack = []

    def mask_by_name(self, header_name, show_first_chars=None):
        def fn(name, value):
            return (
                name,
                value
                if name.lower() != header_name.lower()
                else (
                    "<<masked>>"
                    if show_first_chars is None
                    else "<<masked value={}...>>".format(value[0:show_first_chars])
                ),
            )

        self.stack.append(fn)

        return self

    def mask_authorization(self):
        def fn(name, value):
            cval = None
            if name.lower() == "authorization":
                parts = value.split(" ", 1)
                if len(parts) == 2:
                    type = parts[0].lower()
                    if type == "basic":
                        try:
                            basic = base64.b64decode(parts[1]).decode().split(":", 1)
                        except Exception:
                            basic = ("?",)
                        cval = "{} <<masked password, username={}>>".format(
                            parts[0], basic[0]
                        )
                    elif type == "bearer":
                        jwt = parts[1].split(".")
                        if (
                            len(jwt) == 3
                        ):  # We can be fairly confident it's a JWT, we remove the signature
                            try:
                                # Thanks https://gist.github.com/perrygeo/ee7c65bb1541ff6ac770 for the tip about padding (risk this exception otherwise: binascii.Error: Incorrect padding)
                                header = base64.urlsafe_b64decode(
                                    jwt[0] + "==="
                                ).decode()
                                body = base64.urlsafe_b64decode(jwt[1] + "===").decode()
                                jwtout = (
                                    header,
                                    body,
                                )
                            except Exception:
                                jwtout = (
                                    "?",
                                    "?",
                                )
                            cval = "{} <<masked JWT, header={}, body={}>>".format(
                                parts[0], jwtout[0], jwtout[1]
                            )
                        else:  # Other kind of token
                            cval = "{} <<masked opaque token>>".format(parts[0])
                    else:
                        cval = "{} <<masked>>".format(parts[0])

            return (
                name,
                value if cval is None else cval,
            )

        self.stack.append(fn)

        return self


class BodyFilter(object):
    # TODO: ability to mask some values
    pass


class LogStrategy(object):

    request_header_filter = None
    response_header_filter = None
    response_body_filter = None

    sampling = 1
    bytearr = None
    boundary = None

    save_func = None

    def __init__(self, sampling: int = 1):
        self.sampling = sampling  # TODO: use the sampling

        self.bytearr = bytearray()
        self.boundary = "rawtrace.{}.{}".format(int(time.time()), secrets.token_hex(16))

        self.bytearr.extend(
            self.coerce_to_bytes(
                'Content-Type: multipart/mixed; boundary="{}"'.format(self.boundary)
            )
            + b"\r\n"
            + b"\r\n"
        )

    def to_file(self, filepath):
        f = open(filepath, "wb")
        f.write(self.bytearr)
        f.close()

    def to_bytearray(self):
        return self.bytearr

    def with_request_header_filter(self, header_filter: HeaderFilter):
        self.request_header_filter = header_filter
        return self

    def with_response_header_filter(self, header_filter: HeaderFilter):
        self.response_header_filter = header_filter
        return self

    def with_response_body_filter(self, body_filter: BodyFilter):
        self.response_body_filter = body_filter
        return self

    def dump_failed(
        self,
        request,
        reason: str = None,
        exception: Exception = None,
        timing: Timer = None,
    ):
        self._dump_request_data(
            request, proxy_info=None,
        )
        self._write_boundary("response")
        self.bytearr.extend(
            b"<< "
            + self.coerce_to_bytes(
                'Exception "{}": {}'.format(type(exception).__name__, str(exception))
                if exception is not None
                else reason
            )
            + b" >>"
            + b"\r\n"
        )
        if timing:
            self._dump_timer(timing)

    def dump(self, response, timing: Timer = None):
        """Dump all requests and responses including redirects.

        This takes the response returned by requests and will dump all
        request-response pairs in the redirect history in order followed by the
        final request-response.
        """

        history = list(response.history[:])
        history.append(response)

        for response in history:
            self._dump_one(response,)
        if timing:
            self._dump_timer(timing)

    def _write_boundary(self, type=None):
        self.bytearr.extend(
            self.coerce_to_bytes("--%s\r\n" % self.boundary)
            + (
                self.coerce_to_bytes('X-Type: "%s"\r\n' % type)
                if type is not None
                else b""
            )
            + b"\r\n"
        )

    def _write_headers(self, headers, header_filter=None):
        for name, value in headers.items():
            if header_filter is not None:
                mname = name
                mvalue = value
                for mask in header_filter.stack:
                    mname, mvalue = mask(mname, mvalue)
                self.bytearr.extend(
                    self.coerce_to_bytes(mname)
                    + b": "
                    + self.coerce_to_bytes(mvalue)
                    + b"\r\n"
                )
            else:
                self.bytearr.extend(
                    self.coerce_to_bytes(name)
                    + b": "
                    + self.coerce_to_bytes(value)
                    + b"\r\n"
                )

    @classmethod
    def get_proxy_information(cls, response):
        if getattr(response.connection, "proxy_manager", False):
            proxy_info = {}
            request_url = response.request.url
            if request_url.startswith("https://"):
                proxy_info["method"] = "CONNECT"

            proxy_info["request_path"] = request_url
            return proxy_info
        return None

    @classmethod
    def build_request_path(cls, url, proxy_info):
        uri = compat.urlparse(url)
        proxy_url = proxy_info.get("request_path")
        if proxy_url is not None:
            request_path = cls.coerce_to_bytes(proxy_url)
            return request_path, uri

        request_path = cls.coerce_to_bytes(uri.path)
        if uri.query:
            request_path += b"?" + cls.coerce_to_bytes(uri.query)

        return request_path, uri

    @classmethod
    def coerce_to_bytes(cls, data):
        if not isinstance(data, bytes) and hasattr(data, "encode"):
            data = data.encode("utf-8")
        # Don't bail out with an exception if data is None
        return data if data is not None else b""

    def _dump_request_data(self, request, proxy_info=None):
        if proxy_info is None:
            proxy_info = {}

        method = self.coerce_to_bytes(proxy_info.pop("method", request.method))
        request_path, uri = self.build_request_path(request.url, proxy_info)

        self._write_boundary("request")
        # <prefix><METHOD> <request-path> HTTP/1.1
        self.bytearr.extend(method + b" " + request_path + b" HTTP/1.1\r\n")

        # <prefix>Host: <request-host> OR host header specified by user
        headers = request.headers.copy()
        host_header = self.coerce_to_bytes(headers.pop("Host", uri.netloc))
        self.bytearr.extend(b"Host: " + host_header + b"\r\n")

        # rest of HTTP headers
        self._write_headers(headers, self.request_header_filter)
        self.bytearr.extend(b"\r\n")

        if request.body:
            if isinstance(request.body, compat.basestring):
                self.bytearr.extend(self.coerce_to_bytes(request.body))
            else:
                # In the event that the body is a file-like object, let's not try
                # to read everything into memory.
                self.bytearr.extend(b"<< Request body is not a string-like type >>")
        self.bytearr.extend(b"\r\n")

    def _dump_response_data(self, response):
        # Let's interact almost entirely with urllib3's response
        raw = response.raw

        # Let's convert the version int from httplib to bytes
        HTTP_VERSIONS = {
            9: b"0.9",
            10: b"1.0",
            11: b"1.1",
        }
        version_str = HTTP_VERSIONS.get(raw.version, b"?")

        self._write_boundary("response")
        # <prefix>HTTP/<version_str> <status_code> <reason>
        self.bytearr.extend(
            b"HTTP/"
            + version_str
            + b" "
            + str(raw.status).encode("ascii")
            + b" "
            + self.coerce_to_bytes(response.reason)
            + b"\r\n"
        )

        self._write_headers(raw.headers, self.response_header_filter)
        self.bytearr.extend(b"\r\n")

        # Avoid logging binary body
        if (
            len(response.content) > 0
            and response.encoding is None
            and response.apparent_encoding is None
        ):
            self.bytearr.extend(b"<< Binary response body >>")
        else:
            # TODO: body filter
            self.bytearr.extend(response.content)
        self.bytearr.extend(b"\r\n")

    def _dump_one(self, response):
        """Dump a single request-response cycle's information.

        This will take a response object and dump only the data that requests can
        see for that single request-response cycle.

        """

        if not hasattr(response, "request"):
            raise ValueError("Response has no associated request")

        proxy_info = self.get_proxy_information(response)
        self._dump_request_data(
            response.request, proxy_info=proxy_info,
        )
        self._dump_response_data(response)

    def _dump_timer(self, timing: Timer):
        self._write_boundary("timing-hint")
        self.bytearr.extend(
            b"<< "
            + self.coerce_to_bytes(
                "Request sent at {} ; response received (or timed out) at {} ; time elapsed (s): {}".format(
                    timing.start_date, timing.end_date, timing.total_time_s
                )
            )
            + b" >>"
            + b"\r\n"
        )
