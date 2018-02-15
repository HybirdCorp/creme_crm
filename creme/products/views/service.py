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

from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic

from .. import get_service_model
from ..constants import DEFAULT_HFILTER_SERVICE
from ..forms import service as service_forms
from ..forms.base import AddImagesForm


Service = get_service_model()


def abstract_add_service(request, form=service_forms.ServiceCreateForm,
                         submit_label=Service.save_label,
                        ):
    return generic.add_entity(request, form,
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_service(request, service_id, form=service_forms.ServiceEditForm):
    return generic.edit_entity(request, service_id, Service, form)


def abstract_view_service(request, service_id,
                          template='products/view_service.html',
                         ):
    return generic.view_entity(request, service_id, Service, template=template)


@login_required
@permission_required(('products', cperm(Service)))
def add(request):
    return abstract_add_service(request)


@login_required
@permission_required('products')
def edit(request, service_id):
    return abstract_edit_service(request, service_id)


@login_required
@permission_required('products')
def detailview(request, service_id):
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
