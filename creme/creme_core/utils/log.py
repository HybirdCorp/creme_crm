################################################################################
#
# Copyright (c) 2017-2025 Hybird
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

import sys
import traceback
from collections.abc import Callable
from functools import wraps


def log_exceptions(printer: Callable[[str], None], limit: int = 10):
    """Decorator which prints (& re-raises) exceptions.
    Useful when a function is passed as a callback, and its exceptions are caught silently.

    @param printer: function which takes a string.
    @param limit: depth of printed stack-trace.

    >> import logging
    >> logger = logging.getLogger(__name__)
    >> @log_exceptions(logger.warn)
    >> def my_function(*args, **kwargs):
    >>     ...
    """
    def _decorator(function):
        @wraps(function)
        def _aux(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()

                printer(
                    'An exception occurred in <{}>.\n{}'.format(
                        function.__name__,
                        '\n'.join(
                            traceback.format_exception(
                                exc_type, exc_value, exc_traceback, limit=limit,
                            )
                        ),
                    )
                )
                raise

        return _aux

    return _decorator
