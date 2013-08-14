# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
import logging

from django.db.models.query_utils import Q
from django.forms.fields import MultipleChoiceField, ChoiceField
from django.forms import ValidationError
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType

from creme.creme_core.registry import export_backend_registry #creme_registry
from creme.creme_core.forms import CremeEntityForm, CremeForm
from creme.creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme.creme_core.forms.fields import AjaxMultipleChoiceField, AjaxModelChoiceField, CreatorEntityField, DateRangeField
from creme.creme_core.models import EntityFilter, RelationType, CustomField
from creme.creme_core.models.header_filter import (HeaderFilter, HFI_FIELD, HFI_RELATION,
                                                   HFI_CUSTOM, HFI_FUNCTION, HFI_CALCULATED, HFI_RELATED)
from creme.creme_core.utils.meta import (get_verbose_field_name, get_function_field_verbose_name,
                                         get_date_fields, get_related_field_verbose_name,
                                         ModelFieldEnumerator) #get_flds_with_fk_flds get_flds_with_fk_flds_str

from ..utils import encode_datetime
from ..models import Report, Field
from ..report_aggregation_registry import field_aggregation_registry


logger = logging.getLogger(__name__)


def _save_field(name, title, order, type):
    return Field.objects.create(name=name, title=title, order=order, type=type)

def save_hfi_field(model, column, order):
    return _save_field(column, get_verbose_field_name(model, column), order, HFI_FIELD)

def save_hfi_related_field(model, related_field_name, order):
    return _save_field(related_field_name, get_related_field_verbose_name(model, related_field_name), order, HFI_RELATED)

def save_hfi_cf(custom_field, order):
    return _save_field(custom_field.id, custom_field.name, order, HFI_CUSTOM)

def save_hfi_relation(relation, order):
    try:
        predicate_verbose = RelationType.objects.get(pk=relation)
    except RelationType.DoesNotExist:
        predicate_verbose = relation

    return _save_field(relation, predicate_verbose, order, HFI_RELATION)

def save_hfi_function(model, function_name, order):
    return _save_field(function_name, get_function_field_verbose_name(model, function_name), order, HFI_FUNCTION)

def save_hfi_calculated(calculated, title, order):
    return _save_field(calculated, title, order, HFI_CALCULATED)

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

def get_hfi_related_field_or_save(columns_get, model, column, order):
    try:
        f = _get_field(columns_get, column, HFI_RELATED, order)
    except Field.DoesNotExist:
        f = save_hfi_related_field(model, column, order)
    return f

def get_hfi_cf_or_save(columns_get, custom_field, order):
    try:
        f = _get_field(columns_get, custom_field.id, HFI_CUSTOM, order)
    except Field.DoesNotExist:
        f = save_hfi_cf(custom_field, order)
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

def _get_hfi_calculated_title(aggregate, calculated_column, model):
    field_name, sep, aggregate_name = calculated_column.rpartition('__')

    cfs_info = field_name.split('__')
    if cfs_info[0] == 'cf':
        cf_id   = cfs_info[1]
        try:
            cf_name = CustomField.objects.get(pk=cf_id).name
        except CustomField.DoesNotExist:
            cf_name = ""
        return u"%s - %s" % (unicode(aggregate.title), cf_name)

    return u"%s - %s" % (unicode(aggregate.title), get_verbose_field_name(model, field_name))


def get_hfi_calculated(columns_get, calculated_column, aggregate, model, order):
    try:
        f = _get_field(columns_get, calculated_column, HFI_CALCULATED, order)
    except Field.DoesNotExist:
        title = _get_hfi_calculated_title(aggregate, calculated_column, model)
        f = save_hfi_calculated(calculated_column, title, order)
    return f

def get_aggregate_custom_fields(model, aggregate_pattern): #TODO: generator expression...
    return [(u"cf__%s__%s" % (cf.field_type, aggregate_pattern % cf.id), cf.name)
            for cf in CustomField.objects.filter(content_type=ContentType.objects.get_for_model(model),
                                                 field_type__in=[CustomField.INT, CustomField.FLOAT])
            ]


def get_aggregate_fields(fields, model, initial_data=None): #TODO: move to AddFieldToReportForm ??
    authorized_fields = field_aggregation_registry.authorized_fields

    for aggregate in field_aggregation_registry.itervalues():
        aggregate_pattern = aggregate.pattern

        #choices = [(u"%s" % (aggregate_pattern % f.name), unicode(f.verbose_name)) for f in get_flds_with_fk_flds(model, deep=0) if f.__class__ in authorized_fields]
        choices = [(aggregate_pattern % f_name, f_vname)
                        for f_name, f_vname in ModelFieldEnumerator(model, deep=0)
                                                .filter((lambda f: isinstance(f, authorized_fields)), viewable=True)
                                                .choices()
                  ]

#        cfs = CustomField.objects.filter(content_type=ContentType.objects.get_for_model(model), field_type__in=[CustomField.INT,CustomField.FLOAT])
#        for cf in cfs:
#            choices.extend([(u"cf__%s__%s" % (cf.field_type, aggregate_pattern % cf.id), cf.name)])
        choices.extend(get_aggregate_custom_fields(model, aggregate_pattern))

        fields[aggregate.name] = MultipleChoiceField(label=_(aggregate.title), required=False, choices=choices, widget=OrderedMultipleChoiceWidget)
        if initial_data is not None:
            fields[aggregate.name].initial = initial_data


class CreateForm(CremeEntityForm):
    hf     = AjaxModelChoiceField(label=_(u"Existing view"), queryset=HeaderFilter.objects.none(), required=False)
    filter = AjaxModelChoiceField(label=_(u"Filter"), queryset=EntityFilter.objects.none(), required=False)

    regular_fields = AjaxMultipleChoiceField(label=_(u'Regular fields'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    custom_fields  = AjaxMultipleChoiceField(label=_(u'Custom fields'),  required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    related_fields = AjaxMultipleChoiceField(label=_(u'Related fields'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    relations      = AjaxMultipleChoiceField(label=_(u'Relations'),      required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    functions      = AjaxMultipleChoiceField(label=_(u'Functions'),      required=False, choices=(), widget=OrderedMultipleChoiceWidget)

    blocks = CremeEntityForm.blocks.new(
        ('hf_block',         _(u'Select from a existing view : '), ['hf']),
        ('fields_block',     _(u'Or'), ['regular_fields', 'related_fields', 'custom_fields','relations', 'functions']),
        ('aggregates_block', _(u'Calculated values'), [aggregate.name for aggregate in field_aggregation_registry.itervalues()]),
    )

    class Meta(CremeEntityForm.Meta):
        model = Report

    def __init__(self, *args, **kwargs):
        super(CreateForm, self).__init__(*args, **kwargs)
        fields = self.fields

        #get_ct = ContentType.objects.get_for_model
        #cts    = [(ct.id, unicode(ct)) for ct in (get_ct(model) for model in creme_registry.iter_entity_models())]
        #cts.sort(key=lambda ct_tuple: ct_tuple[1]) #sort by alphabetical order
        #fields['ct'].choices = cts

        self.aggregates = list(field_aggregation_registry.itervalues())#Convert to list to reuse it in template

        for aggregate in self.aggregates:
            fields[aggregate.name] = AjaxMultipleChoiceField(label=_(aggregate.title), required=False, choices=(), widget=OrderedMultipleChoiceWidget)

        #To hande a validation error get ct_id data to rebuild all ?

    #TODO: clean_hf
    #TODO: clean_filter

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data     = cleaned_data.get
        fields       = self.fields

        hf             = get_data('hf')
        regular_fields = get_data('regular_fields')
        related_fields = get_data('related_fields')
        custom_fields  = get_data('custom_fields')
        relations      = get_data('relations')
        functions      = get_data('functions')

        aggregates = self.aggregates

        is_one_aggregate_selected = False
        for aggregate in aggregates:
            for data in get_data(aggregate.name):
                is_one_aggregate_selected |= bool(data)

        if not hf and not (regular_fields or related_fields or custom_fields or relations or functions or is_one_aggregate_selected):
            rfield_fields = ['regular_fields', 'related_fields', 'custom_fields', 'relations', 'functions']
            rfield_fields.extend(aggregate.name for aggregate in aggregates)
            raise ValidationError(ugettext(u"You must select an existing view, or at least one field from : %s") %
                                    u", ".join(unicode(fields[f].label) for f in rfield_fields)
                                 )

        #TODO: Do a real validation

        return cleaned_data

    def save(self, *args, **kwargs):
        report = super(CreateForm, self).save(*args, **kwargs)
        report_fields = []
        get_data = self.cleaned_data.get
        hf = get_data('hf')

        if hf is not None:
            #Have to build from an existant header filter
            field_get_instance_from_hf_item = Field.get_instance_from_hf_item

            for hf_item in hf.items:
                f = field_get_instance_from_hf_item(hf_item)
                f.save()
                report_fields.append(f)
        else:
            model = report.ct.model_class()
            i = 1

            for regular_field in get_data('regular_fields'):
                report_fields.append(save_hfi_field(model, regular_field, i))
                i += 1

            for related_field in get_data('related_fields'):
                report_fields.append(save_hfi_related_field(model, related_field, i))
                i += 1

            cf_ids = get_data('custom_fields')
            if cf_ids:
                cfields = CustomField.objects.filter(content_type=report.ct).in_bulk(cf_ids)

                for cf_id in cf_ids:
                    try:
                        cfield = cfields[int(cf_id)]
                    except (ValueError, KeyError):
                        logger.exception('CreateForm.save()')
                    else:
                        report_fields.append(save_hfi_cf(cfield, i))
                        i += 1

            for relation in get_data('relations'):
                report_fields.append(save_hfi_relation(relation, i))
                i += 1

            for function in get_data('functions'):
                report_fields.append(save_hfi_function(model, function, i))
                i += 1

            for aggregate in self.aggregates:
                for calculated_column in get_data(aggregate.name):
                    title = _get_hfi_calculated_title(aggregate, calculated_column, model)
                    report_fields.append(save_hfi_calculated(calculated_column, title, i))
                    i += 1

        report.columns = report_fields

        return report


class EditForm(CremeEntityForm):
    class Meta:
        model = Report
        #exclude = CremeEntityForm.Meta.exclude + ('ct', 'columns')
        exclude = CremeEntityForm.Meta.exclude + ('ct',)

    def __init__(self, *args, **kwargs):
        super(EditForm, self).__init__(*args, **kwargs)
        ct = self.instance.ct
        fields = self.fields

        base_filter = [('', ugettext(u'All'))]
        base_filter.extend(EntityFilter.objects.filter(entity_type=ct).values_list('id', 'name'))
        fields['filter'].choices = base_filter
        fields['filter'].initial = ct.id


class LinkFieldToReportForm(CremeForm):
    report = CreatorEntityField(label=_(u"Sub-report linked to the column"), model=Report)

    def __init__(self, report, field, ct, *args, **kwargs):
        super(LinkFieldToReportForm, self).__init__(*args, **kwargs)
        self.rfield = field
        self.fields['report'].q_filter = {
                'ct__id' :  ct.id,
                '~id__in' : [r.id for r in chain(report.get_ascendants_reports(), [report])]
            }

    def save(self):
        rfield = self.rfield
        rfield.report = self.cleaned_data['report']
        rfield.save()


class AddFieldToReportForm(CremeForm):
    regular_fields = MultipleChoiceField(label=_(u'Regular fields'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    related_fields = MultipleChoiceField(label=_(u'Related fields'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    custom_fields  = MultipleChoiceField(label=_(u'Custom fields'),  required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    relations      = MultipleChoiceField(label=_(u'Relations'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    functions      = MultipleChoiceField(label=_(u'Functions'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)

    blocks = CremeEntityForm.blocks.new(
        ('aggregates_block', _(u'Calculated values'), [aggregate.name for aggregate in field_aggregation_registry.itervalues()]),
    )

    def __init__(self, entity, *args, **kwargs):
        self.report = entity
        super(AddFieldToReportForm, self).__init__(*args, **kwargs)
        ct = entity.ct
        model = ct.model_class()

        fields = self.fields
        self.custom_fields = cfields = dict((cf.id, cf) for cf in CustomField.objects.filter(content_type=ct))

        #fields['columns'].choices        = get_flds_with_fk_flds_str(model, 1)
        fields['regular_fields'].choices = ModelFieldEnumerator(model, deep=1).filter(viewable=True).choices()
        fields['related_fields'].choices = Report.get_related_fields_choices(model)
        #fields['custom_fields'].choices  = [(cf.name, cf.name) for cf in CustomField.objects.filter(content_type=ct)]
        fields['custom_fields'].choices  = [(str(cf.id), cf.name) for cf in cfields.itervalues()]
        fields['relations'].choices      = [(r.id, r.predicate) for r in RelationType.objects.filter(Q(subject_ctypes=ct)|Q(subject_ctypes__isnull=True)).order_by('predicate')]
        fields['functions'].choices      = [(f.name, f.verbose_name) for f in model.function_fields]

        initial_data = defaultdict(list)

        for f in entity.columns.all(): #TODO: cache columns
            #initial_data[f.type].append(f)
            initial_data[f.type].append(f.name)

        #fields['columns'].initial        = [f.name for f in initial_data[HFI_FIELD]]
        #fields['related_fields'].initial = [f.name for f in initial_data[HFI_RELATED]]
        #fields['custom_fields'].initial  = [f.name for f in initial_data[HFI_CUSTOM]]
        #fields['relations'].initial      = [f.name for f in initial_data[HFI_RELATION]]
        #fields['functions'].initial      = [f.name for f in initial_data[HFI_FUNCTION]]
        fields['regular_fields'].initial = initial_data[HFI_FIELD]
        fields['related_fields'].initial = initial_data[HFI_RELATED]
        fields['custom_fields'].initial  = initial_data[HFI_CUSTOM]
        fields['relations'].initial      = initial_data[HFI_RELATION]
        fields['functions'].initial      = initial_data[HFI_FUNCTION]

        #get_aggregate_fields(fields, model, initial_data=[f.name for f in initial_data[HFI_CALCULATED]])
        get_aggregate_fields(fields, model, initial_data=initial_data[HFI_CALCULATED])

    def save(self):
        get_data = self.cleaned_data.get
        report = self.report
        ct = report.ct
        model = ct.model_class()
        report_columns = report.columns.all()

        regular_fields = get_data('regular_fields')
        related_fields = get_data('related_fields')
        custom_fields  = get_data('custom_fields')
        relations      = get_data('relations')
        functions      = get_data('functions')

        fields_to_keep = []

        columns_get = report.columns.get

        i = 1
        for regular_field in regular_fields:
            fields_to_keep.append(get_hfi_field_or_save(columns_get, model, regular_field, i))
            i += 1

        for related_field in related_fields:
            fields_to_keep.append(get_hfi_related_field_or_save(columns_get, model, related_field, i))
            i += 1

        for cf_id in custom_fields:
            fields_to_keep.append(get_hfi_cf_or_save(columns_get, self.custom_fields[int(cf_id)], i))
            i += 1

        for relation in relations:
            fields_to_keep.append(get_hfi_relation_or_save(columns_get, relation, i))
            i += 1

        for function in functions:
            fields_to_keep.append(get_hfi_function_or_save(columns_get, model, function, i))
            i += 1

        for aggregate in field_aggregation_registry.itervalues():
            for calculated_column in get_data(aggregate.name):
                fields_to_keep.append(get_hfi_calculated(columns_get, calculated_column, aggregate, model, i))
                i += 1

        for col in set(report_columns) - set(fields_to_keep):
            report.columns.remove(col)#Remove from the m2m before deleting it(postgresql)
            col.delete()

        report.columns = fields_to_keep
        report.save()


class DateReportFilterForm(CremeForm):
    doc_type    = ChoiceField(label=_(u'Extension'), required=False, choices=())
    date_field  = ChoiceField(label=_(u'Date field'), required=True, choices=())
    date_filter = DateRangeField(label=_(u'Date filter'))

    def __init__(self, report, *args, **kwargs):
        super(DateReportFilterForm, self).__init__(*args, **kwargs)
        fields = self.fields
        fields['date_field'].choices = [(field.name, field.verbose_name)
                                            for field in get_date_fields(report.ct.model_class())
                                       ]

        choices = [(backend.id, backend.verbose_name)
                        for backend in export_backend_registry.iterbackends()
                  ]
        if choices:
            doc_type = fields['doc_type']
            doc_type.choices = choices
            try:
                doc_type.initial = choices[0][0]
            except IndexError:
                pass

    def get_q_dict(self):
        cdata = self.cleaned_data
        if cdata:
            return cdata['date_filter'].get_q_dict(cdata['date_field'], now())
        return None

    def get_dates(self):
        cleaned_data = self.cleaned_data
        if cleaned_data:
            return cleaned_data['date_filter'].get_dates(now())
        return None, None

    @property
    def forge_url_data(self):
        cleaned_data = self.cleaned_data
        if cleaned_data:
            get_cdata = cleaned_data.get
            data = ['field=%s' % get_cdata('date_field'),
                    'range_name=%s' % get_cdata('date_filter').name
                   ]

            start, end = self.get_dates()
            if start is not None:
                data.append('start=%s' % encode_datetime(start))
            if end is not None:
                data.append('end=%s' % encode_datetime(end))

            return "&".join(data)

    #def save(self, *args, **kwargs):
        #return self.cleaned_data
