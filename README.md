# apifetch

Extra features on top of requests:
 * hard timeout on total time
 * retries, with exponential backoff
 * log raw request and response, mask confidential values
 * validate payload format ==> TODO explicit charset for text (no "apparent charset" magic)
 * rate limiting, concurrency limiting --> just local GCRA for now (assume 1 worker)
 * redis-based circuit breaker / bulkheading ==> TODO, look at https://pypi.org/project/pybreaker/


## Remarks on timeouts

Requests exposes 2 timeouts: one for establishing the connection, and another one
for receiving the HTTP response headers. But there is no timeout for total
download time.
(see https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts:
"timeout is not a time limit on the entire response download; rather, an exception
is raised if the server has not issued a response for timeout seconds (more precisely,
if no bytes have been received on the underlying socket for timeout seconds).")

So, we have to implement a hard timeout externally.

Unfortunately, eventlet.Timeout stopped working with Python 3.7 (raises a "RecursionError",
or "TypeError: wrap_socket() got an unexpected keyword argument '_context'"")

Thanks to https://stackoverflow.com/a/22156618/8046487 a signal-based alternative
seems to be working well. Note the caveats though:
  * **it is not threadsafe**, signals are always delivered to the main thread,
so you can't put this in any other thread.
 * one possible down side with this context manager approach is that you can't
know if the code actually timed out or not (the SignalTimeout.SignalTimeoutException
exception raised stays internal to the process manager ; we have to manually
set a flag while still inside the process manager, after the call to requests, and
manually raise an exception if the flag is unset once out of the process manager)
