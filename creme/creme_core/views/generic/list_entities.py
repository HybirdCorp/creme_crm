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

#DEPRECATED


from logging import debug

from django.db.models import Q
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.conf import settings

from creme_core.models import EntityCredentials

#TODO: only used by documents.folders.... delete when not used any more....

def list_entities(request, model_entity, list_attribut, Q_filter=None, sorder=None):
    """
        @Permissions : Get objects that can Read / Update / Delete
    """
    try:
        entity_list = model_entity.objects.filter(Q(is_deleted__in=[False, None]) | Q(is_deleted__isnull=True))
    except:
        entity_list = model_entity.objects.all()

    if Q_filter is not None:
        entity_list = entity_list.filter(Q_filter)

    #entity_list = filter_RUD_objects(request, entity_list)
    entity_list = EntityCredentials.filter(request.user, entity_list)

    if sorder is not None :
        entity_list = entity_list.order_by(sorder)

    paginator = None
    page = 1

    if list_attribut is not None:
        if request.GET:
            tmp_page = request.GET.get('page')
            if tmp_page:
                page = tmp_page

    paginator = Paginator(entity_list, settings.PAGGING_SIZE)

    page_list_entities = None
    try:
        page_list_entities = paginator.page(page)
    except (EmptyPage, InvalidPage):
        page_list_entities = paginator.page(paginator.num_pages)

    return page_list_entities
