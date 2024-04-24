# Code derived from https://github.com/millerdev/WorQ/blob/master/worq/pool/process.py

################################################################################
#
# Copyright (c) 2012 Daniel Miller
# Copyright (c) 2016-2024 Hybird
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

from os import name as os_name
from subprocess import Popen
from sys import executable as PYTHON_BIN


def python_subprocess(script, python=PYTHON_BIN, start_new_session=False, **kwargs) -> Popen:
    kwargs['start_new_session'] = start_new_session

    return Popen([python, '-c', script], **kwargs)


# We import the following functions
# - enable_exit_handler
# - disable_exit_handler
# - is_exit_handler_enabled

if os_name == 'nt':
    from .nt import *  # NOQA
elif os_name == 'posix':
    from .posix import *  # NOQA
else:  # 'os2', 'ce', 'java', 'riscos', other ?
    import logging
    from sys import exit

    logger = logging.getLogger(__name__)
    logger.critical(
        'It seems your platform "%s" has not been tested for the sub-process feature ;'
        'so you may encounter some issues.', os_name
    )

    def enable_exit_handler(on_exit=lambda *args: exit()):
        pass

    def disable_exit_handler():
        pass

    def is_exit_handler_enabled():
        return False
