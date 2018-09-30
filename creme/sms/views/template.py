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

from .. import get_messagetemplate_model
from ..constants import DEFAULT_HFILTER_MTEMPLATE
from ..forms import template as tpl_forms


MessageTemplate = get_messagetemplate_model()

# Function views --------------------------------------------------------------


def abstract_add_messagetemplate(request, form=tpl_forms.TemplateCreateForm,
                                 submit_label=MessageTemplate.save_label,
                                ):
    warnings.warn('sms.views.template.abstract_add_messagetemplate() is deprecated ; '
                  'use the class-based view MessageTemplateCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_entity(request, form,
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_messagetemplate(request, template_id, form=tpl_forms.TemplateEditForm):
    warnings.warn('sms.views.template.abstract_edit_messagetemplate() is deprecated ; '
                  'use the class-based view MessageTemplateEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, template_id, MessageTemplate, form)


def abstract_view_messagetemplate(request, template_id,
                                  template='sms/view_template.html',
                                 ):
    warnings.warn('sms.views.template.abstract_view_messagetemplate() is deprecated ; '
                  'use the class-based view MessageTemplateDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, template_id, MessageTemplate, template=template)


@login_required
@permission_required(('sms', cperm(MessageTemplate)))
def add(request):
    warnings.warn('sms.views.template.add() is deprecated.', DeprecationWarning)
    return abstract_add_messagetemplate(request)


@login_required
@permission_required('sms')
def edit(request, template_id):
    warnings.warn('sms.views.template.edit() is deprecated.', DeprecationWarning)
    return abstract_edit_messagetemplate(request, template_id)


@login_required
@permission_required('sms')
def detailview(request, template_id):
    warnings.warn('sms.views.template.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_messagetemplate(request, template_id)


@login_required
@permission_required('sms')
def listview(request):
    return generic.list_view(request, MessageTemplate, hf_pk=DEFAULT_HFILTER_MTEMPLATE)


# Class-based views  ----------------------------------------------------------

class MessageTemplateCreation(generic.EntityCreation):
    model = MessageTemplate
    form_class = tpl_forms.TemplateCreateForm


class MessageTemplateDetail(generic.detailview.EntityDetail):
    model = MessageTemplate
    template_name = 'sms/view_template.html'
    pk_url_kwarg = 'template_id'


class MessageTemplateEdition(generic.EntityEdition):
    model = MessageTemplate
    form_class = tpl_forms.TemplateEditForm
    pk_url_kwarg = 'template_id'
