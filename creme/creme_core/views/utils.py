# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.utils.http import PROTOCOL_TO_PORT
from django.utils.six.moves.urllib.parse import urlparse


def build_cancel_path(request):
    url = request.META.get('HTTP_REFERER')

    if url is not None:
        parsed_url = urlparse(url)
        hostname, _sep, port = request.get_host().partition(':')

        if parsed_url.hostname == hostname and (
           (parsed_url.port or PROTOCOL_TO_PORT[parsed_url.scheme]) ==
           (int(port) if port else PROTOCOL_TO_PORT[request.scheme])):
            return parsed_url.path
