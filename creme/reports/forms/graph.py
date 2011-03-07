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


from django.db import models
from django.db.models.fields.related import ForeignKey
from django.db.models.fields import FieldDoesNotExist, DateTimeField, DateField
from django.forms.util import ValidationError
from django.forms.fields import ChoiceField, BooleanField, CharField
from django.forms.widgets import Select, CheckboxInput, HiddenInput
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.forms.base import CremeEntityForm
from creme_core.forms.widgets import DependentSelect, Label
from creme_core.forms.fields import AjaxChoiceField
from creme_core.utils.meta import get_flds_with_fk_flds

from reports.report_aggregation_registry import field_aggregation_registry
from reports.models.graph import ReportGraph, RGT_FK, RGT_RANGE

AUTHORIZED_AGGREGATE_FIELDS = field_aggregation_registry.authorized_fields
AUTHORIZED_ABSCISSA_TYPES = (models.DateField, models.DateTimeField, models.ForeignKey)

class ReportGraphAddForm(CremeEntityForm):
    report_lbl        = CharField(label=_(u'Report'), widget=Label)

    aggregates        = ChoiceField(label=_(u'Ordinate aggregate'), choices=[(aggregate.name, aggregate.title) for aggregate in field_aggregation_registry.itervalues()])
    aggregates_fields = ChoiceField(label=_(u'Ordinate aggregate field'), choices=())

    abscissa_fields   = ChoiceField(label=_(u'Abscissa field'), choices=(), widget=DependentSelect(target_id='id_abscissa_group_by', target_url='/reports/graph/get_available_types/'))
    abscissa_group_by = AjaxChoiceField(label=_(u'Abscissa : Group by'), choices=(), widget=Select(attrs={'id': 'id_abscissa_group_by'}))

    is_count = BooleanField(label=_(u'Entities count'), help_text=_(u'Make a count instead of aggregate ?'), required=False, widget=CheckboxInput(attrs={'onchange': "creme.reports.graphs.toggleDisableOthers(this, ['#id_aggregates', '#id_aggregates_fields']);"}))

    blocks = CremeEntityForm.blocks.new(
                ('abscissa', _(u'Abscissa informations'),  ['abscissa_fields', 'abscissa_group_by', 'days']),
                ('ordinate', _(u'Ordinates informations'), ['is_count', 'aggregates', 'aggregates_fields']),
            )

    class Meta:
        model = ReportGraph
        exclude = CremeEntityForm.Meta.exclude + ('ordinate', 'abscissa', 'type', 'report')

    def __init__(self, entity, *args, **kwargs):
        super(ReportGraphAddForm, self).__init__(*args,  **kwargs)
        self.report = entity
        report_ct = entity.ct
        model = report_ct.model_class()

        fields = self.fields
        
        fields['report_lbl'].initial = unicode(entity)
        aggregates_fields = fields['aggregates_fields']
        abscissa_fields   = fields['abscissa_fields']

        aggregates_fields.choices = [(f.name, unicode(f.verbose_name)) for f in get_flds_with_fk_flds(model, deep=0) if isinstance(f, AUTHORIZED_AGGREGATE_FIELDS)]
        if not aggregates_fields.choices:
             #NB: WTF !!?? this line is exactly the same than previous one (Commented on 9 december 2010)
             #aggregates_fields.choices = [(f.name, unicode(f.verbose_name)) for f in get_flds_with_fk_flds(model, deep=0) if isinstance(f, authorized_aggregate_fields)]
             aggregates_fields.required = False

        abscissa_fields.choices   = [(f.name, unicode(f.verbose_name)) for f in get_flds_with_fk_flds(model, deep=0) if isinstance(f, AUTHORIZED_ABSCISSA_TYPES)]
        abscissa_fields.widget.target_url += str(report_ct.id) #Bof but when DependentSelect will be refactored improve here too

        data = self.data

        if data:
            abscissa_fields.widget.set_source(data.get('abscissa_fields'))
            abscissa_fields.widget.set_target(data.get('abscissa_group_by'))

        instance = self.instance
        if (instance.pk is not None) and not data:
            ordinate, sep, aggregate     = instance.ordinate.rpartition('__')
            fields['aggregates'].initial = aggregate
            aggregates_fields.initial    = ordinate
            abscissa_fields.initial      = instance.abscissa
            
            abscissa_fields.widget.set_source(instance.abscissa)
            abscissa_fields.widget.set_target(instance.type)

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data     = cleaned_data.get
        model = self.report.ct.model_class() #TODO: want we several Report classes ?? If not, simply replace by 'Report'

        try:
            abscissa_group_by = int(get_data('abscissa_group_by'))
        except (ValueError, TypeError):
            abscissa_group_by = None

        abscissa_fields = get_data('abscissa_fields')
        abscissa_field  = None
        aggregates_fields = get_data('aggregates_fields')
        is_count = get_data('is_count')


        #TODO: method instead ?
        val_err = ValidationError(self.fields['abscissa_group_by'].error_messages['invalid_choice'] % {'value': abscissa_fields})

        try:
            abscissa_field = model._meta.get_field(abscissa_fields)
        except FieldDoesNotExist:
            raise val_err

        is_abscissa_group_by_is_RGT_FK = abscissa_group_by == RGT_FK

        if isinstance(abscissa_field, ForeignKey) and not is_abscissa_group_by_is_RGT_FK:
            raise val_err
        if isinstance(abscissa_field, (DateField, DateTimeField)) and is_abscissa_group_by_is_RGT_FK:
            raise val_err

        if abscissa_group_by == RGT_RANGE and not cleaned_data.get('days'):
            raise ValidationError(ugettext(u"You have to specify a day range if you use 'by X days'"))

        if not aggregates_fields and not is_count:
            raise ValidationError(ugettext(u"If you don't choose an ordinate field (or none available) you have to check 'Make a count instead of aggregate ?'"))

        return cleaned_data

    def save(self):
        get_data = self.cleaned_data.get

        graph =  self.instance# or ReportGraph()
        graph.user     = get_data('user')
        graph.name     = get_data('name')
        graph.report   = self.report
        graph.abscissa = get_data('abscissa_fields')

        aggregates_fields = get_data('aggregates_fields')

        if aggregates_fields:
            graph.ordinate = '%s__%s' % (aggregates_fields, get_data('aggregates'))
        else:
            graph.ordinate = u""

        graph.type     = get_data('abscissa_group_by')
        graph.is_count = get_data('is_count')
        graph.days     = get_data('days')
        graph.save()
