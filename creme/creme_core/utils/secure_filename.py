# -*- coding: utf-8 -*-

#    This file comes from Werkzeug.
#
#    Werkzeug is the Swiss Army knife of Python web development.
#
#    It provides useful classes and functions for any WSGI application to make
#    the life of a python web developer much easier.  All of the provided
#    classes are independent from each other so you can mix it with any other
#    library.
#
#    Copyright: (c) 2010 by the Werkzeug Team
#                   2018-2020 Hybird
#    License: BSD
#    Website: http://werkzeug.pocoo.org/


import os
import re
from unicodedata import normalize

_windows_device_files = ('CON', 'AUX', 'COM1', 'COM2', 'COM3', 'COM4', 'LPT1',
                         'LPT2', 'LPT3', 'PRN', 'NUL')
_filename_ascii_strip_re = re.compile(r'[^A-Za-z0-9_.-]')


def secure_filename(filename: str) -> str:
    """Pass it a filename and it will return a secure version of it.
    This filename can then safely be stored on a regular file system and passed
    to :func:`os.path.join`.
    The filename returned is an ASCII only string for maximum portability.

    On windows system the function also makes sure that the file is not
    named after one of the special device files.

    >>> secure_filename("My cool movie.mov")
    'My_cool_movie.mov'
    >>> secure_filename("../../../etc/passwd")
    'etc_passwd'
    >>> secure_filename(u'i contain cool \xfcml\xe4uts.txt')
    'i_contain_cool_umlauts.txt'

    @param filename: the filename to secure (str).
    @return: A new string.
    """
    filename = normalize('NFKD', filename).encode('ascii', 'ignore').decode()

    for sep in (os.path.sep, os.path.altsep):
        if sep:
            filename = filename.replace(sep, ' ')

    filename = str(
        _filename_ascii_strip_re.sub('', '_'.join(filename.split()))
    ).strip('._')

    # On NT a couple of special files are present in each folder.
    #  We have to ensure that the target file is not such a filename.
    #  In this case we prepend an underline.
    if os.name == 'nt':
        if filename.split('.')[0].upper() in _windows_device_files:
            filename = '_' + filename

    return filename
