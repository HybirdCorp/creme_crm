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

from django.http import Http404
from django.db.models.fields.related import ForeignKey
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponse

from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die, edit_view_or_die
from creme_core.views.generic import add_entity, view_entity_with_template, list_view, inner_popup
from creme_core.views.generic.edit import edit_entity
from creme_core.utils.meta import get_model_field_infos
from creme_core.utils import get_ct_or_404

#from reports2.blocks import report_fields_block
from reports2.models import Report2 as Report, report_prefix_url, report_template_dir, Field
from reports2.forms.report import CreateForm, EditForm, LinkFieldToReportForm, AddFieldToReportForm


report_app = Report._meta.app_label
report_ct  = ContentType.objects.get_for_model(Report)

@login_required
@get_view_or_die(report_app)
@add_view_or_die(report_ct, None, report_app)
def add(request):
    tpl_dict = {
        'help_messages' : [],
        'ct_posted' : request.POST.get('ct'),
    }
    return add_entity(request, CreateForm, template="%s/add_report.html" % report_template_dir, extra_template_dict=tpl_dict)

def edit(request, report_id):
    return edit_entity(request, report_id, Report, EditForm, report_app)

@login_required
@get_view_or_die('reports')
def detailview(request, report_id):
    """
        @Permissions : Acces or Admin to document app & Read on current Report object
    """
    return view_entity_with_template(request, report_id, Report,
                                     '%s/report' % report_prefix_url,
                                     '%s/view_report.html' % report_template_dir)

@login_required
@get_view_or_die(report_app)
def listview(request):
    return list_view(request, Report, extra_dict={'add_url':'%s/report/add' % report_prefix_url})

#@login_required
#@get_view_or_die(report_app)
#def reload_fields_block(request, report_id):
    #return report_fields_block.detailview_ajax(request, report_id)

@login_required
@get_view_or_die(report_app)
def unlink_report(request):
    field = get_object_or_404(Field, pk=request.POST.get('field_id'))
    field.report = None
    field.save()

    return HttpResponse("", mimetype="text/javascript")

def __link_report(request, report, field, ct):
    POST = request.POST
    if POST:
        link_form = LinkFieldToReportForm(report, field, ct, POST)

        if link_form.is_valid():
            link_form.save()
    else:
        link_form = LinkFieldToReportForm(report=report, field=field, ct=ct)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   link_form,
                        'title': 'Liaison de la colonne <%s>' % field,
                       },
                       is_valid=link_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
@get_view_or_die(report_app)
def link_report(request, report_id, field_id):
    field  = get_object_or_404(Field,  pk=field_id)
    report = get_object_or_404(Report, pk=report_id)

    fields = get_model_field_infos(report.ct.model_class(), field.name)

    model = None
    for f in fields:
        if(isinstance(f.get('field'), ForeignKey)):
            model = f.get('model')

    if model is None:
        raise Http404
    
    ct = ContentType.objects.get_for_model(model)

    #Really useful here ?
#    die_status = edit_object_or_die(request, field)
#    if die_status:
#        return die_status

    return __link_report(request, report, field, ct)

@login_required
@get_view_or_die(report_app)
def link_relation_report(request, report_id, field_id, ct_id):
    field  = get_object_or_404(Field,  pk=field_id)
    report = get_object_or_404(Report, pk=report_id)
    ct = get_ct_or_404(ct_id)
    
    return __link_report(request, report, field, ct)

@login_required
@get_view_or_die(report_app)
def add_field(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    POST = request.POST
    
    if POST:
        add_field_form = AddFieldToReportForm(report, POST)

        if add_field_form.is_valid():
            add_field_form.save()
    else:
        add_field_form = AddFieldToReportForm(report=report)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   add_field_form,
                        'title': 'Ajout de colonne à <%s>' % report,
                       },
                       is_valid=add_field_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

_order_direction = {
    'up': -1,
    'down':1
}
@login_required
@get_view_or_die(report_app)
def change_field_order(request):
    POST = request.POST
    report = get_object_or_404(Report, pk=POST.get('report_id'))
    field  = get_object_or_404(Field,  pk=POST.get('field_id'))
    direction = POST.get('direction', 'up')

    field.order =  field.order+_order_direction[direction]
    try:
        other_field = report.columns.get(order=field.order)
    except Field.DoesNotExist:
        return HttpResponse("", status=403, mimetype="text/javascript")

    other_field.order = other_field.order-_order_direction[direction]

    field.save()
    other_field.save()

    return HttpResponse("", status=200, mimetype="text/javascript")

@login_required
@get_view_or_die(report_app)
def preview(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    model = report.ct.model_class()

    results = report.fetch()
#    for field in report.columns.all().order_by('order'):


    return render_to_response("%s/preview_report.html" % report_template_dir,
                              {
                                'object'  : report,
                                'results' : results,
                                'entities' : model.objects.all(),
                              },
                              context_instance=RequestContext(request))



