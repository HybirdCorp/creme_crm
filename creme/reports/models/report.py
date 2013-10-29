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

from itertools import chain
#import logging

from django.contrib.auth.models import User
from django.db.models import (CharField, PositiveIntegerField,
        PositiveSmallIntegerField, BooleanField, ManyToManyField, ForeignKey)
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import CremeModel, CremeEntity, EntityFilter
from creme.creme_core.models.fields import EntityCTypeForeignKey


#logger = logging.getLogger(__name__)


class Field(CremeModel):
    name       = CharField(_(u'Name of the column'), max_length=100).set_tags(viewable=False)
    title      = CharField(max_length=100).set_tags(viewable=False)
    order      = PositiveIntegerField().set_tags(viewable=False)
    type       = PositiveSmallIntegerField().set_tags(viewable=False) #==> {HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM, HFI_CALCULATED, HFI_RELATED}#Add in choices ?
    selected   = BooleanField(default=False).set_tags(viewable=False) #use this field to expand
    sub_report = ForeignKey("Report", blank=True, null=True).set_tags(viewable=False) #Sub report

    _hand = None

    class Meta:
        app_label = 'reports'
        verbose_name = _(u'Column of report')
        verbose_name_plural = _(u'Columns of report')
        ordering = ('order',)

    def __unicode__(self):
        return self.title

    #def __repr__(self):
        #return '<Field id=%s name=%s title=%s order=%s type=%s selected=%s report_id=%s>' % (
                    #self.id, self.name, self.title, self.order, self.type, self.selected, self.report_id,
                #)

    def __eq__(self, other):
        return (self.id == other.id and
                self.name == other.name and
                self.title == other.title and
                self.order == other.order and
                self.type == other.type and
                self.selected == other.selected and
                self.sub_report_id == other.sub_report_id)

    #@staticmethod
    #def get_instance_from_hf_item(hf_item):
        #"""
            #@returns : A Field instance built from an HeaderFilterItem instance
        #"""
        #if hf_item.type == HFI_RELATION:
            #return Field(name=hf_item.relation_predicat_id, title=hf_item.title, order=hf_item.order, type=hf_item.type)
        #else:
            #return Field(name=hf_item.name, title=hf_item.title, order=hf_item.order, type=hf_item.type)

    @property
    def hand(self):
        from ..core.report import REPORT_HANDS_MAP #lazy loading

        hand = self._hand

        if hand is None:
            #TODO: manage invalid type
            self._hand = hand = REPORT_HANDS_MAP[self.type](self)

        return hand

    def get_children_fields_flat(self):
        children = []

        if self.selected:
            for child in self.sub_report.fields:
                children.extend(child.get_children_fields_flat())
        else:
            children.append(self)

        return children

    def get_value(self, entity, user, scope):
        """Return the value of the cell for this entity.
        @param entity CremeEntity instance, or None.
        @param user User instance, used to check credentials.
        @scope QuerySet of CremeEntities (used to make correct aggregate).
        @return An unicode or a list (that correspond to an expanded column).
        """
        return self.hand.get_value(entity, user, scope)


class Report(CremeEntity):
    name    = CharField(_(u'Name of the report'), max_length=100)
    ct      = EntityCTypeForeignKey(verbose_name=_(u'Entity type'))
    columns = ManyToManyField(Field, verbose_name=_(u"Displayed columns"), 
                              related_name='report_columns_set', editable=False,
                             ) #TODO: use a One2Many instead....
    filter  = ForeignKey(EntityFilter, verbose_name=_(u'Filter'), blank=True, null=True)

    creation_label = _('Add a report')
    _report_fields_cache = None

    class Meta:
        app_label = 'reports'
        verbose_name = _(u'Report')
        verbose_name_plural = _(u'Reports')
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/reports/report/%s" % self.id

    def get_edit_absolute_url(self):
        return "/reports/report/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/reports/reports"

    @property
    def fields(self):
        fields = self._report_fields_cache

        if fields is None:
            self._report_fields_cache = fields = self.columns.all()

        return fields

    def get_ascendants_reports(self):
        fields = Field.objects.filter(sub_report=self.id)
        asc_reports = []

        for field in fields:
            asc_reports.extend(Report.objects.filter(columns__id=field.id))

        for report in asc_reports:
            asc_reports.extend(report.get_ascendants_reports())

        return set(asc_reports)

    def _fetch(self, limit_to=None, extra_q=None, user=None):
        user = user or User(is_superuser=True)
        entities = EntityCredentials.filter(user, self.ct.model_class().objects.filter(is_deleted=False))

        if self.filter is not None:
            entities = self.filter.filter(entities)

        if extra_q is not None:
            entities = entities.filter(extra_q)

        fields = self.fields

        return ([field.get_value(entity, scope=entities, user=user)
                    for field in fields
                ] for entity in entities[:limit_to]
               )

    #TODO: transform into generator (--> StreamResponse)
    def fetch_all_lines(self, limit_to=None, extra_q=None, user=None):
        from ..core.report import ExpandableLine #lazy loading

        lines = []

        for values in self._fetch(limit_to=limit_to, extra_q=extra_q, user=user):
            lines.extend(ExpandableLine(values).get_lines())

            if limit_to is not None and len(lines) >= limit_to:#Bof
                break #TODO: test

        return lines

    def get_children_fields_flat(self):
        return chain.from_iterable(f.get_children_fields_flat() for f in self.fields)

    def _post_save_clone(self, source): #TODO: test
        for graph in source.reportgraph_set.all():
            new_graph = graph.clone()
            new_graph.report = self
            new_graph.save()

    #TODO: add a similar HeaderFilterItem type in creme_core (& so move this code in core)
    @staticmethod
    def get_related_fields_choices(model):
        allowed_related_fields = model.allowed_related #TODO: can we just use the regular introspection (+ field tags ?) instead
        meta = model._meta
        related_fields = chain(meta.get_all_related_objects(),
                               meta.get_all_related_many_to_many_objects()
                              )

        return [(related_field.var_name, unicode(related_field.model._meta.verbose_name))
                    for related_field in related_fields
                        if related_field.var_name in allowed_related_fields
               ]
