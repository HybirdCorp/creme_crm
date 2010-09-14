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
from django.forms.fields import ChoiceField
from django.forms.widgets import Select
from django.utils.translation import ugettext_lazy as _

from creme_core.forms.base import CremeEntityForm
from creme_core.forms.widgets import DependentSelect
from creme_core.forms.fields import AjaxChoiceField
from creme_core.utils.meta import get_flds_with_fk_flds

from reports.report_aggregation_registry import field_aggregation_registry
from reports.models.graph import ReportGraph, RGT_FK, RGT_RANGE

authorized_aggregate_fields = field_aggregation_registry.authorized_fields
authorized_abscissa_types = [models.DateField, models.DateTimeField, models.ForeignKey]


class ReportGraphAddForm(CremeEntityForm):
    aggregates        = ChoiceField(label=_(u'Ordinate aggregate'), choices=[(aggregate.name, aggregate.title) for aggregate in field_aggregation_registry.itervalues()])
    aggregates_fields = ChoiceField(label=_(u'Ordinate aggregate field'), choices=())

    abscissa_fields   = ChoiceField(label=_(u'Abscissa field'), choices=(), widget=DependentSelect(target_id='id_abscissa_group_by', target_url='/reports/graph/get_available_types/'))
    abscissa_group_by = AjaxChoiceField(label=_(u'Abscissa : Group by'), choices=(), widget=Select(attrs={'id': 'id_abscissa_group_by'}))

    class Meta:
        model = ReportGraph
        exclude = CremeEntityForm.Meta.exclude + ('ordinate', 'abscissa', 'type')

    def __init__(self, report, data=None, *args, **kwargs):
        super(ReportGraphAddForm, self).__init__(data, *args,  **kwargs)
        self.report = report
        report_ct = report.ct
        model = report_ct.model_class()

        fields = self.fields
        fields['report'].choices = [(report.id, unicode(report))]
        fields['report'].initial = report.id

        fields['aggregates_fields'].choices = [(f.name, unicode(f.verbose_name)) for f in get_flds_with_fk_flds(model, deep=0) if f.__class__ in authorized_aggregate_fields]
        fields['abscissa_fields'].choices   = [(f.name, unicode(f.verbose_name)) for f in get_flds_with_fk_flds(model, deep=0) if f.__class__ in authorized_abscissa_types]
        fields['abscissa_fields'].widget.target_url += str(report_ct.id) #Bof but when DependentSelect will be refactored improve here too

        if data is not None:
            fields['abscissa_fields'].widget.set_source(data.get('abscissa_fields'))
            fields['abscissa_fields'].widget.set_target(data.get('abscissa_group_by'))

        instance = self.instance
        if instance.pk is not None and data is None:
            ordinate, sep, aggregate = instance.ordinate.rpartition('__')
            fields['aggregates'].initial        = aggregate
            fields['aggregates_fields'].initial = ordinate
            fields['abscissa_fields'].initial = instance.abscissa
            fields['abscissa_fields'].widget.set_source(instance.abscissa)
            fields['abscissa_fields'].widget.set_target(instance.type)

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data     = cleaned_data.get
        model = self.report.ct.model_class()

        try:
            abscissa_group_by = int(get_data('abscissa_group_by'))
        except: #TODO: better exception
            abscissa_group_by = None

        abscissa_fields = get_data('abscissa_fields')
        abscissa_field  = None

        #TODO: method instead ?
        val_err = ValidationError(self.fields['abscissa_group_by'].error_messages['invalid_choice'] % {'value': abscissa_fields})

        try:
            abscissa_field = model._meta.get_field(abscissa_fields)
        except FieldDoesNotExist:
            raise val_err

        if isinstance(abscissa_field, ForeignKey) and abscissa_group_by != RGT_FK:
            raise val_err
        if isinstance(abscissa_field, (DateField, DateTimeField)) and abscissa_group_by == RGT_FK:
            raise val_err

        if abscissa_group_by == RGT_RANGE and not cleaned_data.get('days'):
            raise ValidationError(_(u"You have to specify a day range if you use 'by X days'")) #TODO: ugettext instead of ugettext_lazy

        return cleaned_data

    def save(self):
        get_data = self.cleaned_data.get
        
        graph =  self.instance# or ReportGraph()
        graph.user     = get_data('user')
        graph.name     = get_data('name')
        graph.report   = self.report
        graph.abscissa = get_data('abscissa_fields')
        graph.ordinate = '%s__%s' % (get_data('aggregates_fields'), get_data('aggregates'))
        graph.type     = get_data('abscissa_group_by')
        graph.is_count = get_data('is_count')
        graph.days     = get_data('days')
        graph.save()
