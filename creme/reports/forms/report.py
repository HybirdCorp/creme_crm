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

from collections import defaultdict
from itertools import chain
from django.db.models.query_utils import Q
from django.forms.fields import MultipleChoiceField
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType

from creme_core.registry import creme_registry
from creme_core.forms import CremeEntityForm, CremeForm
from creme_core.forms.widgets import OrderedMultipleChoiceWidget, ListViewWidget
from creme_core.forms.fields import AjaxMultipleChoiceField, AjaxModelChoiceField, CremeEntityField
from creme_core.models import Filter, RelationType, CustomField
from creme_core.models.header_filter import HeaderFilter, HeaderFilterItem, HFI_FIELD, HFI_RELATION, HFI_CUSTOM, HFI_FUNCTION
from creme_core.utils.meta import get_verbose_field_name, get_function_field_verbose_name, get_flds_with_fk_flds_str

from reports.models import Report, Field

def _save_field(name, title, order, type):
    f = Field(name=name, title=title, order=order, type=type)
    f.save()
    return f

def save_hfi_field(model, column, order):
    return _save_field(column, get_verbose_field_name(model, column), order, HFI_FIELD)

def save_hfi_cf(name, title, order):
    return _save_field(name, title, order, HFI_CUSTOM)

def save_hfi_relation(relation, order):
    rel_type_get = RelationType.objects.get
    try:
        predicate_verbose = rel_type_get(pk=relation)
    except RelationType.DoesNotExist:
        predicate_verbose =  relation
    return _save_field(relation, predicate_verbose, order, HFI_RELATION)

def save_hfi_function(model, function_name, order):
    return _save_field(function_name, get_function_field_verbose_name(model, function_name), order, HFI_FUNCTION)

def _get_field(columns_get, column, type, order):
    f = columns_get(name=column, type=type)
    f.order = order
    f.save()
    return f

def get_hfi_field_or_save(columns_get, model, column, order):
    try:
        f = _get_field(columns_get, column, HFI_FIELD, order)
    except Field.DoesNotExist:
        f = save_hfi_field(model, column, order)
    return f

def get_hfi_cf_or_save(columns_get, column, order):
    try:
        f = _get_field(columns_get, column, HFI_CUSTOM, order)
    except Field.DoesNotExist:
        f = save_hfi_cf(column, column, order)
    return f

def get_hfi_relation_or_save(columns_get, relation, order):
    try:
        f = _get_field(columns_get, relation, HFI_RELATION, order)
    except Field.DoesNotExist:
        f = save_hfi_relation(relation, order)
    return f

def get_hfi_function_or_save(columns_get, model, function, order):
    try:
        f = _get_field(columns_get, function, HFI_FUNCTION, order)
    except Field.DoesNotExist:
        f = save_hfi_function(model, function, order)
    return f


class CreateForm(CremeEntityForm):
    hf     = AjaxModelChoiceField(queryset=HeaderFilter.objects.none(), required=False)
    filter = AjaxModelChoiceField(queryset=Filter.objects.none(), required=False)

    columns       = AjaxMultipleChoiceField(label=_(u'Regular fields'),required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    custom_fields = AjaxMultipleChoiceField(label=_(u'Custom fields'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    relations     = AjaxMultipleChoiceField(label=_(u'Relations'),     required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    functions     = AjaxMultipleChoiceField(label=_(u'Functions'),     required=False, choices=(), widget=OrderedMultipleChoiceWidget)

    class Meta:
        model = Report
        exclude = CremeEntityForm.Meta.exclude 

    def __init__(self, *args, **kwargs):
        super(CreateForm, self).__init__(*args, **kwargs)
        fields   = self.fields
        ct_get = ContentType.objects.get_for_model
        cts = [ct_get(model) for model in creme_registry.iter_entity_models()]
        cts.sort(key=lambda ct: ct.name)
        fields['ct'].choices = [(ct.id, ct.name) for ct in cts]

        #To hande a validation error get ct_id data to rebuild all ?

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data     = cleaned_data.get
        fields       = self.fields

        hf            = get_data('hf')
        columns       = get_data('columns')
        custom_fields = get_data('custom_fields')
        relations     = get_data('relations')
        functions     = get_data('functions')

        _fields_choices = [unicode(fields[f].label) for f in ['columns','custom_fields','relations', 'functions']]

        if not hf and not (columns or custom_fields or relations or functions):
            raise ValidationError(ugettext(u"You must select an existing view, or at least one field from : %s") % ", ".join(_fields_choices))

        return cleaned_data

    def save(self):
        get_data = self.cleaned_data.get

        user          = get_data('user')
        name          = get_data('name')
        ct            = get_data('ct')
        filter        = get_data('filter')
        hf            = get_data('hf')
        columns       = get_data('columns')
        custom_fields = get_data('custom_fields')
        relations     = get_data('relations')
        functions     = get_data('functions')

        model = ct.model_class()

        report = Report()
        report.user = user
        report.name = name
        report.ct = ct
        report.filter = filter
        report.save()
        self.instance = report

        report_fields = []

        if hf is not None:
            #Have to build from an existant header filter
            hf_items = HeaderFilterItem.objects.filter(header_filter=hf)
            field_get_instance_from_hf_item = Field.get_instance_from_hf_item
            for hf_item in hf_items:
                f = field_get_instance_from_hf_item(hf_item)
                f.save()
                report_fields.append(f)
        else:
            i = 1
            for column in columns:
                report_fields.append(save_hfi_field(model, column, i))
                i += 1

            for custom_field in custom_fields:
                report_fields.append(save_hfi_cf(custom_field, custom_field, i))
                i += 1

            for relation in relations:
                report_fields.append(save_hfi_relation(relation, i))
                i += 1

            for function in functions:
                report_fields.append(save_hfi_function(model, function, i))
                i += 1

        report.columns = report_fields
        report.save()


class EditForm(CremeEntityForm):
    class Meta:
        model = Report
        exclude = CremeEntityForm.Meta.exclude + ('ct', 'columns')

    def __init__(self, *args, **kwargs):
        super(EditForm, self).__init__(*args, **kwargs)
        instance = self.instance
        fields = self.fields

        base_filter = [('', ugettext(u'All'))]
        base_filter.extend(Filter.objects.filter(model_ct=instance.ct).values_list('id','name'))
        fields['filter'].choices = base_filter
        fields['filter'].initial = instance.ct.id

    def save(self):
        super(EditForm, self).save()


class LinkFieldToReportForm(CremeForm):
    report = CremeEntityField(label=_(u"Sub-report linked to the column"), model=Report, widget=ListViewWidget)

    def __init__(self, report, field, ct, *args, **kwargs):
        self.field = field
        self.ct = ct
        super(LinkFieldToReportForm, self).__init__(*args, **kwargs)

        self.fields['report'].widget.q_filter = {'ct__id' : ct.id, '~id__in' : [r.id for r in chain(report.get_ascendants_reports(),[report])]}

    def save(self):
        self.field.report = self.cleaned_data['report']
        self.field.save()


class AddFieldToReportForm(CremeForm):
    columns       = MultipleChoiceField(label=_(u'Regular fields'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    custom_fields = MultipleChoiceField(label=_(u'Custom fields'),  required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    relations     = MultipleChoiceField(label=_(u'Relations'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    functions     = MultipleChoiceField(label=_(u'Functions'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)

    def __init__(self, report, *args, **kwargs):
        self.report = report
        super(AddFieldToReportForm, self).__init__(*args, **kwargs)
        ct = report.ct
        model = ct.model_class()

        fields = self.fields

        fields['columns'].choices = get_flds_with_fk_flds_str(model, 1)
        fields['custom_fields'].choices = [(cf.name, cf.name) for cf in CustomField.objects.filter(content_type=ct)]
        fields['relations'].choices = [(r.id, r.predicate) for r in RelationType.objects.filter(Q(subject_ctypes=ct)|Q(subject_ctypes__isnull=True)).order_by('predicate')]
        fields['functions'].choices = [(f.name, f.verbose_name) for f in model.function_fields]

        initial_data = defaultdict(list)

        for f in report.columns.all():
            initial_data[f.type].append(f)

        fields['columns'].initial       = [f.name for f in initial_data[HFI_FIELD]]
        fields['custom_fields'].initial = [f.name for f in initial_data[HFI_CUSTOM]]
        fields['relations'].initial     = [f.name for f in initial_data[HFI_RELATION]]
        fields['functions'].initial     = [f.name for f in initial_data[HFI_FUNCTION]]


    def save(self):
        get_data = self.cleaned_data.get
        report = self.report
        ct = report.ct
        model = ct.model_class()
        report_columns = report.columns.all()

        columns       = get_data('columns')
        custom_fields = get_data('custom_fields')
        relations     = get_data('relations')
        functions     = get_data('functions')

        fields_to_keep = []

        columns_get = report.columns.get

        i = 1
        for column in columns:
            fields_to_keep.append(get_hfi_field_or_save(columns_get, model, column, i))
            i += 1

        for custom_field in custom_fields:
            fields_to_keep.append(get_hfi_cf_or_save(columns_get, custom_field, i))
            i += 1

        for relation in relations:
            fields_to_keep.append(get_hfi_relation_or_save(columns_get, relation, i))
            i += 1

        for function in functions:
            fields_to_keep.append(get_hfi_function_or_save(columns_get, model, function, i))
            i += 1

        for col in set(report_columns) - set(fields_to_keep):
            col.delete()

        report.columns = fields_to_keep
        report.save()

