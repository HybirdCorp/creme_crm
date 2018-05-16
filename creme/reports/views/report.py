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

import logging  # warnings

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.utils.db import reorder_instances
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import POST_only

from .. import get_report_model
from ..constants import DEFAULT_HFILTER_REPORT
from ..forms.report import (ReportCreateForm, ReportEditForm,
        LinkFieldToReportForm, ReportFieldsForm)
from ..models import Field


logger = logging.getLogger(__name__)
Report = get_report_model()


def abstract_add_report(request, form=ReportCreateForm,
                        # TODO: improve widgets & drop this template
                        template='reports/add_report.html',
                        submit_label=Report.save_label,
                       ):
    return generic.add_entity(request, form, template=template,
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_report(request, report_id, form=ReportEditForm):
    return generic.edit_entity(request, report_id, Report, form)


def abstract_view_report(request, report_id,
                         template='reports/view_report.html',
                        ):
    return generic.view_entity(request, report_id, Report, template=template)


@login_required
@permission_required(('reports', cperm(Report)))
def add(request):
    return abstract_add_report(request)


@login_required
@permission_required('reports')
def edit(request, report_id):
    return abstract_edit_report(request, report_id)


@login_required
@permission_required('reports')
def detailview(request, report_id):
    return abstract_view_report(request, report_id)


@login_required
@permission_required('reports')
def listview(request):
    return generic.list_view(request, Report, hf_pk=DEFAULT_HFILTER_REPORT)


@login_required
@permission_required('reports')
def unlink_report(request):
    field = get_object_or_404(Field, pk=get_from_POST_or_404(request.POST, 'field_id'))

    # TODO: odd credentials ?! (only edit on field.report ??)
    has_perm_or_die = request.user.has_perm_to_unlink_or_die
    has_perm_or_die(field.report)

    if field.sub_report is None:
        raise ConflictError('This field has no sub-report')

    has_perm_or_die(field.sub_report)

    field.sub_report = None
    field.selected = False
    field.save()

    return HttpResponse(content_type='text/javascript')


@login_required
@permission_required('reports')
def link_report(request, field_id):
    rfield = get_object_or_404(Field, pk=field_id)
    user = request.user

    user.has_perm_to_link_or_die(rfield.report)

    hand = rfield.hand

    if hand is None:
        raise ConflictError('This field is invalid')  # TODO: force block to reload

    ctypes = rfield.hand.get_linkable_ctypes()

    if ctypes is None:
        raise ConflictError('This field is not linkable')

    if request.method == 'POST':
        link_form = LinkFieldToReportForm(rfield, ctypes, user=user, data=request.POST)

        if link_form.is_valid():
            link_form.save()
    else:
        link_form = LinkFieldToReportForm(rfield, ctypes, user=user)

    return generic.inner_popup(request,
                               'creme_core/generics/blockform/link_popup.html',
                               {'form': link_form,
                                'title': ugettext(u'Link of the column «%s»') % rfield,
                                'submit_label': _(u'Link'),
                               },
                               is_valid=link_form.is_valid(),
                               reload=False,
                               delegate_reload=True,
                              )


@login_required
@permission_required('reports')
def edit_fields(request, report_id):
    return generic.add_to_entity(request, report_id, ReportFieldsForm,
                                 _(u'Edit columns of «%s»'),
                                 entity_class=Report,
                                 submit_label=_(u'Save the modifications'),
                                 template='creme_core/generics/blockform/edit_popup.html',
                                )
    # TODO: need to change the constructor of ReportFieldsForm (arg 'entity' => 'instance'
    # return generic.edit_model_with_popup(request,
    #                                      model=Report,
    #                                      query_dict={'id': report_id},
    #                                      form_class=ReportFieldsForm,
    #                                      title_format=_(u'Edit columns of «%s»'),
    #                                     )

# _order_direction = {
#     'up':   -1,
#     'down':  1,
# }
#
#
# @login_required
# @permission_required('reports')
# def change_field_order(request):
#     warnings.warn('reports.views.report.change_field_order() is deprecated ; use reorder_field() instead.',
#                   DeprecationWarning
#                  )
#
#     POST = request.POST
#     field = get_object_or_404(Field, pk=get_from_POST_or_404(POST, 'field_id'))
#     direction = POST.get('direction', 'up')
#     report = field.report
#
#     request.user.has_perm_to_change_or_die(report)
#
#     field.order += _order_direction[direction]  # todo: manage bad direction arg
#     try:
#         other_field = report.fields.get(order=field.order)
#     except Field.DoesNotExist:
#         return HttpResponse(status=403, content_type='text/javascript')
#
#     other_field.order -= _order_direction[direction]
#
#     field.save()
#     other_field.save()
#
#     return HttpResponse(status=200, content_type='text/javascript')


@POST_only
@login_required
@permission_required('reports')
def reorder_field(request, field_id):
    new_order = get_from_POST_or_404(request.POST, 'target', int)
    rfield = get_object_or_404(Field, pk=field_id)

    report = rfield.report
    request.user.has_perm_to_change_or_die(report)

    try:
        reorder_instances(moved_instance=rfield, new_order=new_order, queryset=report.fields)
    except Exception as e:
        return HttpResponse(e, status=409, content_type='text/javascript')

    return HttpResponse(content_type='text/javascript')


@login_required
@permission_required('reports')
def set_selected(request):
    POST   = request.POST
    rfield = get_object_or_404(Field, pk=get_from_POST_or_404(POST, 'field_id'))

    if not rfield.sub_report_id:
        raise ConflictError('This Field has no Report, so can no be (un)selected')

    report = rfield.report

    request.user.has_perm_to_change_or_die(report)

    try:
        checked = bool(int(POST.get('checked', 0)))
    except ValueError:
        checked = False

    if rfield.selected != checked:
        if checked:  # Only one Field should be selected
            report.fields.exclude(pk=rfield.pk).update(selected=False)

        rfield.selected = checked
        rfield.save()

    return HttpResponse(content_type='text/javascript')
