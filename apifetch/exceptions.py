class RequestTimeout(Exception):
    pass


class RequestFailure(Exception):
    pass


class InvalidResponse(ValueError):
    pass
