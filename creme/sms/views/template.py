# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

# from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import add_entity, edit_entity, view_entity, list_view

from .. import get_messagetemplate_model
from ..constants import DEFAULT_HFILTER_MTEMPLATE
from ..forms.template import TemplateCreateForm, TemplateEditForm


MessageTemplate = get_messagetemplate_model()


def abstract_add_messagetemplate(request, form=TemplateCreateForm,
                                 # submit_label=_('Save the message template'),
                                 submit_label=MessageTemplate.save_label,
                                ):
    return add_entity(request, form,
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_edit_messagetemplate(request, template_id, form=TemplateEditForm):
    return edit_entity(request, template_id, MessageTemplate, form)


def abstract_view_messagetemplate(request, template_id,
                                  template='sms/view_template.html',
                                 ):
    return view_entity(request, template_id, MessageTemplate, template=template)


@login_required
@permission_required(('sms', cperm(MessageTemplate)))
def add(request):
    return abstract_add_messagetemplate(request)


@login_required
@permission_required('sms')
def edit(request, template_id):
    return abstract_edit_messagetemplate(request, template_id)


@login_required
@permission_required('sms')
def detailview(request, template_id):
    return abstract_view_messagetemplate(request, template_id)


@login_required
@permission_required('sms')
def listview(request):
    return list_view(request, MessageTemplate, hf_pk=DEFAULT_HFILTER_MTEMPLATE)
