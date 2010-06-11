# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

import logging

from django.http import HttpResponse
from django.core.serializers.json import DjangoJSONEncoder

from products.models import Category, SubCategory


def _is_valid(category):
    if not category:
        return False

    return bool(Category.objects.filter(id=category).count())

def get_sub_cat_on_cat_change(request):
    logging.debug("GET_SUB_CAT_ON_CAT_CHANGE")

    category = request.POST.get('record_id', '')

    if _is_valid(category):
        #TODO: if it was {'id':..., 'name':..}, we could use values('id', 'name') directly....
        result = [{'id': id, 'text': name} for id, name in SubCategory.objects.filter(category=category).values_list('id', 'name')]
    else:
        result = [{'id': '', 'text': u'Choisissez une catégorie'}]

    return HttpResponse(DjangoJSONEncoder().encode({'result': result}), mimetype='application/javascript')
