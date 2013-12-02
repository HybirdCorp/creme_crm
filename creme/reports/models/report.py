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
import logging

from django.contrib.auth.models import User
from django.db.models import (CharField, PositiveIntegerField,
        PositiveSmallIntegerField, BooleanField, ForeignKey)
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import CremeModel, CremeEntity, EntityFilter
from creme.creme_core.models.fields import EntityCTypeForeignKey


logger = logging.getLogger(__name__)


class Report(CremeEntity):
    name   = CharField(_(u'Name of the report'), max_length=100)
    ct     = EntityCTypeForeignKey(verbose_name=_(u'Entity type'))
    filter = ForeignKey(EntityFilter, verbose_name=_(u'Filter'), blank=True, null=True)

    creation_label = _('Add a report')
    _columns = None

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

    def _build_columns(self, allow_selected):
        """@param allow_selected Boolean, 'True' allows columns to be 'selected'
                                 (expanded sub-report)
        """
        self._columns = columns = []

        for rfield in self.fields.all():
            rfield.report = self #pre-cache

            if rfield.hand: #field is valid
                rfield._build_children(allow_selected)
                columns.append(rfield)

        return columns

    @property
    def columns(self):
        columns = self._columns

        if columns is None: #root report
            columns = self._build_columns(allow_selected=True)

        return columns

    def get_ascendants_reports(self):
        asc_reports = list(Report.objects.filter(pk__in=Field.objects.filter(sub_report=self.id)
                                                                     .values_list('report', flat=True)
                                                )
                          )

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

        fields = self.columns

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
        return chain.from_iterable(f.get_children_fields_flat() for f in self.columns)

    def _post_save_clone(self, source): #TODO: test
        for graph in source.reportgraph_set.all():
            new_graph = graph.clone()
            new_graph.report = self
            new_graph.save()

    #TODO: add a similar EntityCell type in creme_core (& so move this code in core)
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


class Field(CremeModel):
    report     = ForeignKey(Report, related_name='fields').set_tags(viewable=False)
    name       = CharField(_(u'Name of the column'), max_length=100).set_tags(viewable=False)
    order      = PositiveIntegerField().set_tags(viewable=False)
    type       = PositiveSmallIntegerField().set_tags(viewable=False) #==> see RFT_* in constants #Add in choices ?
    selected   = BooleanField(default=False).set_tags(viewable=False) #use this field to expand
    sub_report = ForeignKey(Report, blank=True, null=True).set_tags(viewable=False) #Sub report

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

    #def __eq__(self, other):
        #return (self.id == other.id and #todo id ??
                #self.name == other.name and
                ##self.title == other.title and
                #self.order == other.order and
                #self.type == other.type and
                #self.selected == other.selected and
                #self.sub_report_id == other.sub_report_id)

    def _build_children(self, allow_selected):
        """Force the tree to be built, and fix the 'selected' attributes.
        Only root fields (ie: deep==0), or children a selected root field,
        can be selected.
        """
        self.selected &= allow_selected

        sub_report = self.sub_report

        if sub_report:
            sub_report._build_columns(self.selected)

    @property
    def hand(self):
        from ..core.report import REPORT_HANDS_MAP, ReportHand #lazy loading

        hand = self._hand

        if hand is None:
            try:
                self._hand = hand = REPORT_HANDS_MAP[self.type](self)
            except (ReportHand.ValueError, KeyError) as e:
                logger.warn('Invalid column is deleted (%s)', e)
                self.delete()

        return hand

    def get_children_fields_flat(self):
        children = []

        if self.selected:
            for child in self.sub_report.columns:
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

    @property
    def model(self):
        return self.report.ct.model_class()

    @property
    def title(self):
        return self.hand.title
