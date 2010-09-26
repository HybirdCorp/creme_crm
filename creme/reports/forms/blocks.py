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

from django.contrib.contenttypes.models import ContentType
from collections import defaultdict

from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import ugettext_lazy as _, ugettext
from django.forms import ChoiceField, CharField, ValidationError

from creme_core.models.relation import RelationType
from creme_core.models.header_filter import HFI_FIELD, HFI_RELATION
from creme_core.models.block import InstanceBlockConfigItem
from creme_core.forms.base import CremeForm
from creme_core.forms.widgets import Label
from creme_core.utils import creme_entity_content_types
from creme_core.utils.meta import get_verbose_field_name

from reports.blocks import ReportGraphBlock

def _get_volatile_columns(report, creme_entity_cts):
    report_model = report.ct.model_class()
    report_model_get_field = report_model._meta.get_field

    results = []

    target_columns = report.columns.filter(type__in=[HFI_FIELD, HFI_RELATION])

    targets = defaultdict(list)
    for column in target_columns:
        targets[column.type].append(column)

    cts = list(creme_entity_cts)
    ct_get = ContentType.objects.get_for_model

    for col in targets[HFI_FIELD]:
        col_name = col.name.split('__')[0]

        try:
            field = report_model_get_field(col_name)
        except FieldDoesNotExist:
            continue

        if field.get_internal_type() == 'ForeignKey' and ct_get(field.rel.to) in cts:
            results.append((u"%s#%s" % (col_name, HFI_FIELD), col.title))

    rt_get = RelationType.objects.get
    for rel in targets[HFI_RELATION]:
        try:
            rt=rt_get(pk=rel.name)
        except RelationType.DoesNotExist:
            continue

        results.append((u"%s#%s" % (rel.name, HFI_RELATION), rel.title))

    if not results:
        results = [("", _(u"No availables choices"))]
    else:
        results.insert(0, ("", _(u"None")))

    return results

def _get_volatile_column_verbose(model, col):
    col = col.split('#')[0]
    verbose = get_verbose_field_name(model, col)
    if not verbose:
        try:
            verbose = unicode(RelationType.objects.get(pk=col))
        except RelationType.DoesNotExist:
            verbose = col
    return verbose

class GraphInstanceBlockForm(CremeForm):
    graph = CharField(label=_(u"Related graph"),  widget=Label())
#    volatil_column = AjaxChoiceField(label=_(u'Volatil column'), choices=(), required=False)
    volatil_column = ChoiceField(label=_(u'Volatil column'), choices=(), required=False)

    def __init__(self, graph, *args, **kwargs):
        super(GraphInstanceBlockForm, self).__init__(*args, **kwargs)
        self.graph = graph
        report = graph.report
        fields = self.fields
        fields['volatil_column'].choices = _get_volatile_columns(report, creme_entity_content_types())
        fields['graph'].initial = u"%s - %s" % (graph, report)

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data     = cleaned_data.get
        graph = self.graph
        volatil_column = get_data('volatil_column', '')

        try:
            InstanceBlockConfigItem.objects.get(block_id=ReportGraphBlock.generate_id('creme_config', u"%s_%s" % (graph.id, volatil_column)))
        except InstanceBlockConfigItem.DoesNotExist:
            return cleaned_data

        raise ValidationError(ugettext(u'The instance block for %s with %s already exists !') % (graph, volatil_column.split('#')[0] or _('None')))

    def save(self):
        cleaned_data = self.cleaned_data
        graph = self.graph
        report_model = graph.report.ct.model_class()
        volatil_column = cleaned_data.get('volatil_column', '')

        instance = InstanceBlockConfigItem()
        instance.entity = graph
        instance.block_id = ReportGraphBlock.generate_id('creme_config', u"%s_%s" % (graph.id, volatil_column))
        instance.data = volatil_column
        instance.verbose = u"%s - %s" % (graph, _get_volatile_column_verbose(report_model, volatil_column) or _(u'None'))
        instance.save()