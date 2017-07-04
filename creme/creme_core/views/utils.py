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

from json import dumps as json_dump

from django.db.models.base import Model
from django.http.response import HttpResponse
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


# TODO : Find a better name
def json_update_from_widget_response(instance):
    """
    This function is designed for javascript selectors (listview or combobox) with creation forms and
    needs to be updated the on fly.

    Returns a dict that represents the changes to apply in a javascript widgets that supports collection "patch".
    {"value": id, "added": [[id, label]]} is returned (the js will add the choice and select it).
    """
    if isinstance(instance, Model):
        data = {
            'value': instance.id,
            'added': [(instance.id, unicode(instance))]
        }
    else:
        data = instance

    return HttpResponse(json_dump(data), content_type="application/json")
