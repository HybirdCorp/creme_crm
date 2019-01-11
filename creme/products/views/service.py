# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import warnings

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic

from .. import get_service_model
from ..constants import DEFAULT_HFILTER_SERVICE
from ..forms import service as service_forms

from .base import ImagesAddingBase

Service = get_service_model()

# Function views --------------------------------------------------------------


def abstract_add_service(request, form=service_forms.ServiceCreateForm,
                         submit_label=Service.save_label,
                        ):
    warnings.warn('products.views.service.abstract_add_service() is deprecated ; '
                  'use the class-based view ServiceCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_entity(request, form,
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_service(request, service_id, form=service_forms.ServiceEditForm):
    warnings.warn('products.views.service.abstract_edit_service() is deprecated ; '
                  'use the class-based view ServiceEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, service_id, Service, form)


def abstract_view_service(request, service_id,
                          template='products/view_service.html',
                         ):
    warnings.warn('products.views.service.abstract_view_service() is deprecated ; '
                  'use the class-based view ServiceDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, service_id, Service, template=template)


@login_required
@permission_required(('products', cperm(Service)))
def add(request):
    warnings.warn('products.views.service.add() is deprecated.', DeprecationWarning)
    return abstract_add_service(request)


@login_required
@permission_required('products')
def edit(request, service_id):
    warnings.warn('products.views.service.edit() is deprecated.', DeprecationWarning)
    return abstract_edit_service(request, service_id)


@login_required
@permission_required('products')
def detailview(request, service_id):
    warnings.warn('products.views.service.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_service(request, service_id)


@login_required
@permission_required('products')
def listview(request):
    return generic.list_view(request, Service, hf_pk=DEFAULT_HFILTER_SERVICE)


# Class-based views  ----------------------------------------------------------


class ServiceCreation(generic.EntityCreation):
    model = Service
    form_class = service_forms.ServiceCreateForm


class ServiceDetail(generic.EntityDetail):
    model = Service
    template_name = 'products/view_service.html'
    pk_url_kwarg = 'service_id'


class ServiceEdition(generic.EntityEdition):
    model = Service
    form_class = service_forms.ServiceEditForm
    pk_url_kwarg = 'service_id'


class ImagesAdding(ImagesAddingBase):
    entity_id_url_kwarg = 'service_id'
    entity_classes = Service
