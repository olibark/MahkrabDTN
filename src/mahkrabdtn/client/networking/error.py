from urllib import error

class RelayClientError(Exception):
    pass

def is_retryable_http_error(httpError: error.HTTPError) -> bool:
    return httpError.code == 429 or 500 <= httpError.code < 600