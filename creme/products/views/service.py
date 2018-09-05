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

from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic

from .. import get_service_model
from ..constants import DEFAULT_HFILTER_SERVICE
from ..forms import service as service_forms
from ..forms.base import AddImagesForm


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


@login_required
@permission_required('products')
def add_images(request, service_id):
    return generic.add_to_entity(request, service_id, AddImagesForm,
                                 ugettext(u'New images for «%s»'),
                                 entity_class=Service,
                                 submit_label=_(u'Link the images'),
                                 template='creme_core/generics/blockform/link_popup.html',
                                )

# Class-based views  ----------------------------------------------------------


class ServiceCreation(generic.add.EntityCreation):
    model = Service
    form_class = service_forms.ServiceCreateForm


class ServiceDetail(generic.detailview.EntityDetail):
    model = Service
    template_name = 'products/view_service.html'
    pk_url_kwarg = 'service_id'
