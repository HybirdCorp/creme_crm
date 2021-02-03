# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2021  Hybird
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

from django.http import response

from creme.creme_core.utils.serializers import CremeJSONEncoder


# The method HttpRequest.is_ajax() is deprecated since Django 3.1 because it relied
# on a way which was jQuery centric. As dropping jQuery is not planned at, we keep
# this technic at the moment.
# It could change if we use https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API
def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


class CremeJsonResponse(response.JsonResponse):
    def __init__(self, data, encoder=CremeJSONEncoder, *args, **kwargs):
        super().__init__(data=data, encoder=encoder, *args, **kwargs)
