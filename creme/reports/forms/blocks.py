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

from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import ugettext_lazy as _, ugettext
from django.forms import ChoiceField, CharField, ValidationError
from django.contrib.contenttypes.models import ContentType

from creme.creme_core.models import RelationType
from creme.creme_core.models.header_filter import HFI_FIELD, HFI_RELATION
from creme.creme_core.forms.base import CremeForm
from creme.creme_core.forms.widgets import Label
from creme.creme_core.utils import creme_entity_content_types

from ..models import  ReportGraph


class GraphInstanceBlockForm(CremeForm):
    graph           = CharField(label=_(u"Related graph"), widget=Label())
    volatile_column = ChoiceField(label=_(u'Volatile column'), choices=(), required=False)
#    volatile_column = AjaxChoiceField(label=_(u'Volatil column'), choices=(), required=False)

    def __init__(self, graph, *args, **kwargs):
        super(GraphInstanceBlockForm, self).__init__(*args, **kwargs)
        self.graph = graph
        report = graph.report
        fields = self.fields
        fields['volatile_column'].choices = self._get_volatile_columns(report, creme_entity_content_types())
        fields['graph'].initial = u"%s - %s" % (graph, report)

    def _get_volatile_columns(self, report, creme_entity_cts):
        report_model = report.ct.model_class()
        report_model_get_field = report_model._meta.get_field

        results = []
        targets = defaultdict(list)

        for column in report.columns.filter(type__in=[HFI_FIELD, HFI_RELATION]):
            targets[column.type].append(column)

        cts = list(creme_entity_cts) #TODO: frozenset ??
        ct_get = ContentType.objects.get_for_model

        for column in targets[HFI_FIELD]:
            field_name = column.name.split('__', 1)[0]

            try:
                field = report_model_get_field(field_name)
            except FieldDoesNotExist:
                continue

            if field.get_internal_type() == 'ForeignKey' and ct_get(field.rel.to) in cts:
                results.append((u"%s|%s" % (field_name, HFI_FIELD), column.title))

        self.rtypes = rtypes = RelationType.objects.in_bulk([c.name for c in targets[HFI_RELATION]])

        for column in targets[HFI_RELATION]:
            name = column.name

            if rtypes.get(name):
                results.append((u"%s|%s" % (name, HFI_RELATION), column.title))

        if not results:
            results = [("", ugettext(u"No available choice"))]
        else:
            results.insert(0, ("", _(u"None")))

        return results

    def clean(self):
        cleaned_data = self.cleaned_data
        volatile_column = cleaned_data.get('volatile_column')
        kwargs = {}

        if volatile_column:
            col_value, col_type = volatile_column.split('|')
            col_type = int(col_type)

            if col_type == HFI_FIELD:
                kwargs['volatile_field'] = col_value
            else:
                assert col_type == HFI_RELATION
                kwargs['volatile_rtype'] = self.rtypes[col_value]

        try:
            self.ibci = self.graph.create_instance_block_config_item(save=False, **kwargs)
        except ReportGraph.InstanceBlockConfigItemError as e:
            raise ValidationError(unicode(e))

        return cleaned_data

    def save(self):
        ibci = self.ibci
        ibci.save()

        return ibci
