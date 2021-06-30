from requests.exceptions import HTTPError


class RequestTimeout(Exception):
    pass


class RequestFailure(Exception):
    pass


class InvalidResponse(ValueError):
    pass


class RequestsHTTPError(HTTPError):
    pass
