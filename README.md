# apifetch

Extra features on top of Python `requests`:
 * hard timeout on total time
 * retries, with exponential backoff
 * rate limiting to spread load evenly (one implementation of GCRA algorithm included)
 * log raw request and response, mask confidential values
 * helpers to validate response payload format: JSON, XML, JPG, GIF
 * helpers around strings: fix Latin mojibake (e.g. "Ã©"), remove Unicode control chars
 
TODO:
 * [ ] dig encodings and charsets (no "apparent charset" magic)
 * [ ] rate limiting should be able to inspect responses (in case the server included relevant headers)
 * [ ] circuit breaker / bulkheading to avoid retrying on a dead service (maybe look at https://pypi.org/project/pybreaker/)


## Remarks on timeouts


### Requests' timeouts do not guarantee a total download time

Requests exposes 2 timeouts: one for establishing the connection, and another one
for receiving the HTTP response headers. But there is no timeout for total
download time.


See https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts:
> timeout is not a time limit on the entire response download; rather, an exception
> is raised if the server has not issued a response for timeout seconds (more precisely,
> if no bytes have been received on the underlying socket for timeout seconds).


So, we have to implement a hard timeout externally.

### How to implement the equivalent of `timeout -s KILL` in Python 3?

Previously I would have used `eventlet.Timeout`, e.g.

```
import eventlet
eventlet.monkey_patch(socket=True)

with eventlet.Timeout(...):
    ...

```

But it stopped working with Python 3.7 (raises a `RecursionError`,
or `TypeError: wrap_socket() got an unexpected keyword argument '_context'`).

You can track for instance this issue: https://github.com/eventlet/eventlet/issues/526 (apparently, installing `pyOpenSSL` might help)


Thanks to https://stackoverflow.com/a/22156618/8046487 a signal-based alternative
seems to be working well. Note the caveats though:

> * It is not threadsafe, signals are always delivered to the main thread, so you can't put this in any other thread.
> * There is a slight delay after the scheduling of the signal and the execution of the actual code.
> * One possible down side with [the] context manager approach is that you can't know if the code actually timed out or not.


The last point can be worked around. The `SignalTimeout.SignalTimeoutException`
exception raised stays internal to the process manager ; we have to manually
set a flag while still inside the process manager, after the call to `requests`, and
manually raise an exception if the flag is unset once we are out of the process manager.
