# -*- coding: utf-8 -*-

# Code derived from https://github.com/millerdev/WorQ/blob/master/worq/pool/process.py

################################################################################
#
# Copyright (c) 2012 Daniel Miller
# Copyright (c) 2016-2020 Hybird
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
# FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

import logging
from sys import exit, version_info

logger = logging.getLogger(__name__)


try:
    from win32api import SetConsoleCtrlHandler

    __win32_exit_handler = None

    def enable_exit_handler(handler=lambda *args: exit()):
        global __win32_exit_handler

        SetConsoleCtrlHandler(handler, True)
        __win32_exit_handler = handler

    def disable_exit_handler():
        global __win32_exit_handler

        if __win32_exit_handler is not None:
            SetConsoleCtrlHandler(__win32_exit_handler, False)
            __win32_exit_handler = None

    def is_exit_handler_enabled():
        return __win32_exit_handler is not None
except ImportError:
    def enable_exit_handler(*args, **kwargs):
        logger.critical('pywin32.SetConsoleCtrlHandler is not supported by your install')
        return False

    disable_exit_handler = enable_exit_handler
    is_exit_handler_enabled = enable_exit_handler

    version = '.'.join(map(str, version_info[:2]))
    logger.critical('pywin32 not installed for Python %s', version)
