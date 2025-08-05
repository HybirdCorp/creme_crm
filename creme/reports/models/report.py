################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from __future__ import annotations

import logging
# import warnings
from collections.abc import Iterator
from itertools import chain
from typing import TYPE_CHECKING, Type

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_filter import EF_REGULAR
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.models import (
    CremeEntity,
    CremeModel,
    EntityFilter,
    FieldsConfig,
)
from creme.creme_core.models.fields import EntityCTypeForeignKey

from ..constants import EF_REPORTS

if TYPE_CHECKING:
    from ..core.report import ReportHand

logger = logging.getLogger(__name__)


class AbstractReport(CremeEntity):
    name = models.CharField(_('Name of the report'), max_length=100)
    ct = EntityCTypeForeignKey(verbose_name=_('Entity type'))
    filter = models.ForeignKey(
        EntityFilter, verbose_name=_('Filter'),
        blank=True, null=True, on_delete=models.PROTECT,
        limit_choices_to={'filter_type__in': [EF_REGULAR, EF_REPORTS]},
    ).set_null_label(_('No filter'))

    creation_label = _('Create a report')
    save_label     = _('Save the report')

    _columns: list[Field] | None = None

    class Meta:
        abstract = True
        app_label = 'reports'
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('reports__view_report', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('reports__create_report')

    def get_edit_absolute_url(self):
        return reverse('reports__edit_report', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('reports__list_reports')

    def _build_columns(self, allow_selected: bool) -> list[Field]:
        """@param allow_selected: Boolean, 'True' allows columns to be 'selected'
                  (i.e. expanded sub-report).
        """
        self._columns = columns = []
        selected_found = False

        for rfield in self.fields.all():
            if rfield.hand:  # Field is valid
                if rfield.selected:
                    if selected_found:
                        logger.warning('Several expanded sub-reports -> we fix it')
                        rfield.selected = False
                        rfield.save()

                    selected_found = True

                rfield._build_children(allow_selected)
                columns.append(rfield)

        return columns

    @property
    def columns(self) -> list[Field]:
        columns = self._columns

        if columns is None:  # root report
            columns = self._build_columns(allow_selected=True)

        return columns

    @cached_property
    def _fields_configs(self) -> FieldsConfig.LocalCache:
        "Protected API. Useful for ReportHands/ReportGraphHand (in order to avoid queries)"
        return FieldsConfig.LocalCache()

    @cached_property
    def filtered_columns(self) -> list[Field]:
        # TODO: avoid case of hand which is None (RAII) => remove <if column.hand>
        return [column for column in self.columns if column.hand and not column.hand.hidden]

    def get_ascendants_reports(self) -> set[AbstractReport]:
        asc_reports = [
            *type(self).objects.filter(
                pk__in=Field.objects
                            .filter(sub_report=self.id)
                            .values_list('report', flat=True),
            ),
        ]

        for report in asc_reports:
            asc_reports.extend(report.get_ascendants_reports())

        return {*asc_reports}

    # TODO: move 'user' as first argument + no default value ?
    def _fetch(self,
               limit_to: int | None = None,
               extra_q: models.Q | None = None,
               user=None) -> Iterator[list]:
        user = user or get_user_model()(is_superuser=True)
        entities = EntityCredentials.filter(
            user,
            self.ct.get_all_objects_for_this_type(is_deleted=False),
        )

        if self.filter is not None:
            entities = self.filter.filter(entities)

        if extra_q is not None:
            entities = entities.filter(extra_q)

        if limit_to:
            entities = entities[:limit_to]

        fields = self.filtered_columns

        for entity in entities:
            yield [
                field.get_value(entity, scope=entities, user=user)
                for field in fields
            ]

    # TODO: transform into generator (--> StreamResponse)
    def fetch_all_lines(self,
                        limit_to: int | None = None,
                        extra_q: models.Q | None = None,
                        user=None) -> list[list[str]]:
        from ..core.report import ExpandableLine  # Lazy loading

        lines = []

        for values in self._fetch(limit_to=limit_to, extra_q=extra_q, user=user):
            lines.extend(ExpandableLine(values).get_lines())

            if limit_to is not None and len(lines) >= limit_to:  # Meh
                break  # TODO: test

        return lines

    def get_children_fields_flat(self) -> Iterator[Field]:
        return chain.from_iterable(
            f.get_children_fields_flat()
            for f in self.filtered_columns
        )

    # def _post_save_clone(self, source):
    #     warnings.warn(
    #         'The method Report._post_save_clone() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     for rfield in source.fields.all():
    #         rfield.clone(report=self)
    #
    #     for graph in source.reportgraph_set.all():
    #         new_graph = graph.clone()
    #         new_graph.linked_report = self
    #         new_graph.save()


class Report(AbstractReport):
    class Meta(AbstractReport.Meta):
        swappable = 'REPORTS_REPORT_MODEL'


class Field(CremeModel):
    report = models.ForeignKey(
        settings.REPORTS_REPORT_MODEL,
        related_name='fields',
        on_delete=models.CASCADE,
    ).set_tags(viewable=False)

    # TODO: choices ?
    # See RFT_* in constants
    type = models.PositiveSmallIntegerField().set_tags(viewable=False)
    # TODO: rename "value" ??
    name = models.CharField(max_length=100).set_tags(viewable=False)

    order = models.PositiveIntegerField().set_tags(viewable=False)

    # Use this field to expand
    selected = models.BooleanField(default=False).set_tags(viewable=False)
    sub_report = models.ForeignKey(
        settings.REPORTS_REPORT_MODEL,
        blank=True, null=True,
        on_delete=models.CASCADE,
    ).set_tags(viewable=False)

    _hand = None

    class Meta:
        app_label = 'reports'
        verbose_name = _('Column of report')
        verbose_name_plural = _('Columns of report')
        ordering = ('order',)

    def __str__(self):
        return self.title

    def _build_children(self, allow_selected: bool) -> None:
        """Force the tree to be built, and fix the 'selected' attributes.
        Only root fields (i.e. deep==0), or children a selected root field,
        can be selected.
        """
        self.selected &= allow_selected

        sub_report = self.sub_report

        if sub_report:
            sub_report._build_columns(self.selected)

    def clone(self, report: AbstractReport | None = None) -> Field:
        fields_kv = {}

        for field in self._meta.fields:
            if field.get_tag(FieldTag.CLONABLE):
                fname = field.name
                fields_kv[fname] = getattr(self, fname)

        if report is not None:
            fields_kv['report'] = report

        return Field.objects.create(**fields_kv)

    @property
    def hand(self) -> ReportHand | None:
        from ..core.report import REPORT_HANDS_MAP, ReportHand  # Lazy loading

        hand = self._hand

        if hand is None:
            try:
                self._hand = hand = REPORT_HANDS_MAP[self.type](self)
            except (ReportHand.ValueError, KeyError) as e:
                logger.warning('Invalid column is deleted (%s)', e)
                self.delete()

        return hand

    def get_children_fields_flat(self) -> list[Field]:
        children: list[Field] = []

        if self.selected:
            for child in self.sub_report.columns:
                children.extend(child.get_children_fields_flat())
        else:
            children.append(self)

        return children

    def get_value(self,
                  entity: CremeEntity | None,
                  user,
                  scope: models.QuerySet) -> str | list:
        """Return the value of the cell for this entity.
        @param entity: CremeEntity instance, or None.
        @param user: User instance, used to check credentials.
        @param scope: QuerySet of CremeEntities (used to make correct aggregate).
        @return A string or a list (that correspond to an expanded column).
        """
        hand = self.hand
        return hand.get_value(entity, user, scope) if hand else '??'

    @property
    def model(self) -> Type[CremeEntity]:
        return self.report.ct.model_class()

    @property
    def title(self) -> str:
        hand = self.hand
        return hand.title if hand else '??'
