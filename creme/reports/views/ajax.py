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

#from logging import debug

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.simplejson import JSONEncoder
from django.utils.encoding import smart_str
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import Filter

from reports.models import Report, Field, Operation, FieldsOperations, Mtm_rp_fl


PREVIEW_MAX = 25

@login_required
def get_filters_for_ct(request):
    filters = Filter.objects.filter(model_ct__id=request.POST['ct']).values('id', 'name')

    return HttpResponse(JSONEncoder().encode(list(filters)), mimetype="text/javascript")

@login_required
def get_columns_for_ct(request):
    POST        = request.POST
    excluded    = set(POST.getlist('except_tab'))
    model_class = ContentType.objects.get(pk=POST['ct']).model_class()

    excluded |= set(getattr(model_class, 'excluded_fields_in_html_output', []))

    headers = [item.name for item in model_class._meta.fields if item.name not in excluded]

    return HttpResponse(JSONEncoder().encode(headers), mimetype="text/javascript")

@login_required
def get_preview(request):
    POST = request.POST
    model_class = ContentType.objects.get(pk=POST['ct']).model_class()
    filter_id   = int(POST['filter'])

    if filter_id:
        entities = model_class.objects.filter(Filter.objects.get(pk=filter_id).get_q()).distinct()
    else:
        entities = model_class.objects.all()

    fields   = set(field.name for field in model_class._meta.fields)
    headers  = [column for column in POST.getlist('column_tab') if column in fields]
    content  = [[smart_str(getattr(entity, column)) for column in headers] for entity in entities[:PREVIEW_MAX]]
    rendered = render_to_string('reports/preview.html', {'headers': headers, 'rows': content})

    return HttpResponse(JSONEncoder().encode(rendered), mimetype="text/javascript")

def save_report(request):
    post = request.POST
    report_name = post.get('name')
    fields_list = post.get('fields_list')
    filter_id = int(post.get('filter', 0))
    ct_id = int(post.get('ct', 0))
    U = User.objects.get(username=str(request.user))
    report_id = post.get('report_id')

    R = get_object_or_404(Report, pk=report_id) if report_id else Report()

    FieldsOperations.objects.filter(report=R).delete()
    Mtm_rp_fl.objects.filter(report=R).delete()

    R.name = report_name
    R.ct = ContentType.objects.get(pk=ct_id)
    if filter_id:
        R.filter = Filter.objects.get(pk=filter_id)
    R.user = U
    R.save()

    if fields_list:  #TODO: useful test ?? (can be None ???)
        for i, field in enumerate(fields_list.split(',')):
            try:
                F = Field.objects.get(ct=R.ct, name=field)
                R.addField(F, i) #TODO: can be factorised no ???
            except: #TODO: better exception....
                F = Field()
                F.ct = R.ct
                F.name = field
                F.save()
                R.addField(F, i)

    # Ici on parse les operations que souhaite le createur du rapport
    # Format = ( opérateur , column/column/... ) | ( ... )
    brut = post.get('operations_list')
    if brut: #TODO: useful test ?? (can be None ???)
        for item in brut.split('|'):
            if not item:
                continue
            couple_tab = item.split(',') #TODO: unpacking....
            for column in couple_tab[1].split('/'):
                try:
                    F = FieldsOperations()
                    F.report = R
                    F.field = Field.objects.get(ct=R.ct, name=column)
                    F.operation = Operation.objects.get(operator=couple_tab[0])
                    F.save()
                except Field.DoesNotExist, Operation.DoesNotExist:
                    pass

    return R

# Unused code. comment on 17/03/2010 

#def generate_CSV(request):
#    report = save_report(request)
#    return report.generateCSV()
#
#def generate_ODT(request):
#    report = save_report(request)
#    return report.generateODT()

#def generate_SIMPLE(request):
#    report = save_report(request)
#    return HttpResponseRedirect(report.get_absolute_url())
#    #return HttpResponseRedirect('/reports/reports')

@login_required
def save(request):
    report = save_report(request)
    return HttpResponseRedirect(report.get_absolute_url())

@login_required
def get_operable_columns(request):
    POST = request.POST
    fields_of_ct = dict((field.name, field) for field in ContentType.objects.get(pk=POST['ct']).model_class()._meta.fields)

    valid_columns = []
    accepted_field_types = frozenset(('PositiveIntegerField', 'IntegerField')) #static ??

    for wanted_column in POST.getlist('fields_list'):
        field = fields_of_ct.get(wanted_column)

        if field and field.get_internal_type() in accepted_field_types:
            valid_columns.append(wanted_column)

    return HttpResponse(JSONEncoder().encode(valid_columns), mimetype="text/javascript")
