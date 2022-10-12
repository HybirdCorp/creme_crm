################################################################################
#
# Copyright (c) 2017-2023 Hybird
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

import logging
import os
import subprocess
from functools import lru_cache

from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime

logger = logging.getLogger(__name__)


@lru_cache
def get_hg_info() -> dict:
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    info = {
        'date': '?',
        'id':   '?',
    }

    # from xml.etree.ElementTree import XMLParser
    #
    # hg_heads = subprocess.Popen('hg heads --style=xml',
    #                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    #                             shell=True, cwd=repo_dir,
    #                             universal_newlines=True,
    #                            )
    # xml = hg_heads.communicate()[0]
    #
    # parser = XMLParser()
    # parser.feed(xml)
    #
    # root = parser.close()
    # log_entry = root.find('.//logentry')
    # ...

    # NB: it seems the date format does not work on very old HG (ok with 3.7+ at least)
    hg_log = subprocess.Popen(
        """hg log -r tip --template '{date(date, "%Y-%m-%dT%H:%M%z")}#{node}'""",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=True, cwd=repo_dir,
        # universal_newlines=True,
        text=True,
    )

    raw_result, error = hg_log.communicate()

    if error:
        logger.warning('Error in creme_core.utils.version.get_hg_info(): %s', error)
    else:
        try:
            date_str, changeset_id = raw_result.split('#', 1)
        except ValueError:
            logger.warning(
                'Error in creme_core.utils.version.get_hg_info(): '
                'received: %s', raw_result,
            )
        else:
            info['id'] = changeset_id

            try:
                date_obj = parse_datetime(date_str)
            except ValueError as e:
                logger.warning(
                    'Error in creme_core.utils.version.get_hg_info(): '
                    'invalid date info (%s)', e
                )
            else:
                if date_obj is None:
                    logger.warning(
                        'Error in creme_core.utils.version.get_hg_info(): '
                        'date info is not well formatted (%s)', date_str,
                    )
                else:
                    info['date'] = localtime(date_obj)

    return info


# TODO: factorise ?
@lru_cache
def get_git_info() -> dict:
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    info = {
        'date': '?',
        'id':   '?',
    }

    git_log = subprocess.Popen(
        "git log -n 1 --format='%H#%cI'",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=True, cwd=repo_dir,
        # universal_newlines=True,
        text=True,
    )

    raw_result, error = git_log.communicate()

    if error:
        logger.warning('Error in creme_core.utils.version.get_hg_info(): %s', error)
    else:
        print(raw_result)
        try:
            changeset_id, date_str = raw_result.strip().split('#', 1)
        except ValueError:
            logger.warning(
                'Error in creme_core.utils.version.get_git_info(): '
                'received: %s', raw_result,
            )
        else:
            info['id'] = changeset_id

            try:
                date_obj = parse_datetime(date_str)
            except ValueError as e:
                logger.warning(
                    'Error in creme_core.utils.version.get_git_info(): '
                    'invalid date info (%s)', e
                )
            else:
                if date_obj is None:
                    logger.warning(
                        'Error in creme_core.utils.version.get_git_info(): '
                        'date info is not well formatted (%s)', date_str,
                    )
                else:
                    info['date'] = localtime(date_obj)

    return info
