################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2025  Hybird
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

from urllib.parse import urlparse

from django.db.models.base import Model

from creme.creme_core.http import CremeJsonResponse

PROTOCOL_TO_PORT = {
    'http': 80,
    'https': 443,
}


def build_cancel_path(request) -> str | None:
    url = request.META.get('HTTP_REFERER')

    if url is not None:
        parsed_url = urlparse(url)
        hostname, _sep, port = request.get_host().partition(':')

        if (
            parsed_url.hostname == hostname
            and (
                (
                    parsed_url.port or PROTOCOL_TO_PORT[parsed_url.scheme]
                ) == (
                    int(port) if port else PROTOCOL_TO_PORT[request.scheme]
                )
            )
        ):
            return parsed_url.path

    return None


# TODO: Find a better name
def json_update_from_widget_response(instance):
    """
    This function is designed for JavaScript selectors (list-view or combobox)
    with creation forms and needs to be updated the on fly.

    Returns a dict that represents the changes to apply in a javascript widget
    which supports collection "patch" :
       {"value": id, "added": [[id, label]]} is returned
       (the JS will add the choice and select it).
    """
    return CremeJsonResponse(
        data={
            'value': instance.id,
            'added': [(instance.id, str(instance))],
        } if isinstance(instance, Model) else instance,
    )
