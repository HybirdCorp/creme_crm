# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from creme.creme_core.views import generic

from .. import custom_forms, get_service_model
from ..constants import DEFAULT_HFILTER_SERVICE
from .base import ImagesAddingBase

Service = get_service_model()


class ServiceCreation(generic.EntityCreation):
    model = Service
    form_class = custom_forms.SERVICE_CREATION_CFORM


class ServiceDetail(generic.EntityDetail):
    model = Service
    template_name = 'products/view_service.html'
    pk_url_kwarg = 'service_id'


class ServiceEdition(generic.EntityEdition):
    model = Service
    form_class = custom_forms.SERVICE_EDITION_CFORM
    pk_url_kwarg = 'service_id'


class ServicesList(generic.EntitiesList):
    model = Service
    default_headerfilter_id = DEFAULT_HFILTER_SERVICE


class ImagesAdding(ImagesAddingBase):
    entity_id_url_kwarg = 'service_id'
    entity_classes = Service
