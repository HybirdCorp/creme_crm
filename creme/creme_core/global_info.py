# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2009-2020 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
################################################################################

# See  middleware.global_info.GlobalInfoMiddleware

from collections import defaultdict
from functools import wraps
from typing import DefaultDict, Hashable

try:
    from threading import currentThread
except ImportError:
    from dummy_threading import currentThread  # type: ignore

_globals: DefaultDict = defaultdict(dict)


def get_global_info(key: Hashable):
    """Get a global value, safely because stored in a per-thread way.

    @param key: Hashable object (typically a string) as usual.
    @return The value corresponding to the key.
            <None> is returned if the key is not found.
    """
    thread_globals = _globals.get(currentThread())
    return thread_globals and thread_globals.get(key)


def set_global_info(**kwargs) -> None:
    """Set some global values, safely because stored in a per-thread way.

    @param kwargs: Each key-value are sored as global data.
    """
    _globals[currentThread()].update(kwargs)


def clear_global_info() -> None:
    # Don't use del _globals[currentThread()], it causes problems with dev server.
    _globals.pop(currentThread(), None)


def get_per_request_cache() -> dict:
    """Get a special global data, which is a dictionary used as a per-request cache.

    @return: A dictionary.
    """
    cache = get_global_info('per_request_cache')

    if cache is None:
        cache = {}
        set_global_info(per_request_cache=cache)

    return cache


def cached_per_request(cache_key: Hashable):
    """Decorator which caches the result in the per-request cache.
    (see get_per_request_cache().

    @param cache_key: The key used to identify the result.
    """
    def _decorator(function):
        @wraps(function)
        def _aux(*args, **kwargs):
            cache = get_per_request_cache()

            try:
                cached_value = cache[cache_key]
            except KeyError:
                cache[cache_key] = cached_value = function(*args, **kwargs)

            return cached_value

        return _aux

    return _decorator
