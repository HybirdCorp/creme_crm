################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2025  Hybird
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
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING
from uuid import UUID

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db.models import ForeignKey, ManyToManyField
from django.utils.formats import number_format
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.gui.field_printers import field_printer_registry
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import CremeEntity, CustomField, RelationType
from creme.creme_core.models.utils import model_verbose_name
from creme.creme_core.utils.meta import FieldInfo

from .. import constants
from ..report_aggregation_registry import (
    FieldAggregation,
    field_aggregation_registry,
)

if TYPE_CHECKING:
    from django.db.models import Field, Model, QuerySet
    from django.db.models.aggregates import Aggregate

    from ..models import Field as ReportField  # TODO: rename model ??

# TODO: use Window/Frame to compute aggregate ?

logger = logging.getLogger(__name__)


class ReportHand:
    "Class which computes values of a report column (ie reports.models.Field)."
    verbose_name = 'OVERLOADME'

    class ValueError(Exception):
        pass

    def __init__(self,
                 report_field: ReportField,
                 title: str = '??',
                 support_subreport: bool = False,
                 ):
        self._report_field = report_field
        self._title = title
        self._support_subreport = support_subreport

    def _generate_flattened_report(self, entities, user, scope: QuerySet) -> str:
        columns = self._report_field.sub_report.columns

        return ', '.join(
            '/'.join(
                f'{column.title}: {column.get_value(entity, user, scope)}'
                for column in columns
            ) for entity in entities
        )

    # TODO: scope ??
    def _get_related_instances(self, entity: CremeEntity, user) -> QuerySet:
        raise NotImplementedError

    def _get_filtered_related_entities(self, entity: CremeEntity, user) -> QuerySet:
        related_entities = EntityCredentials.filter(
            user=user,
            queryset=self._get_related_instances(entity, user),
        )
        report = self._report_field.sub_report

        if report.filter is not None:
            related_entities = report.filter.filter(related_entities)

        return related_entities

    def _get_value(self,
                   entity: CremeEntity,
                   user,
                   scope: QuerySet,
                   ):
        # NB: we are not building 'self._get_value' in __init__() because the
        #     value of 'report_field.selected' can change after the Hand building.
        if self._support_subreport:
            report_field = self._report_field

            if report_field.sub_report:
                get_value = (
                    self._get_value_extended_subreport
                    if report_field.selected else
                    self._get_value_flattened_subreport
                )
            else:
                get_value = self._get_value_no_subreport
        else:
            get_value = self._get_value_single

        # Cache
        self._get_value = get_value  # type: ignore

        return get_value(entity, user, scope)

    def _get_value_extended_subreport(self,
                                      entity: CremeEntity,
                                      user,
                                      scope: QuerySet,
                                      ) -> list[list[str]]:
        """Used as _get_value() method by subclasses which manage
        sub-reports (extended sub-report case).
        """
        related_entities = self._get_filtered_related_entities(entity, user)
        gen_values = self._handle_report_values

        # "(None,)" : even if sub-scope is empty, we must generate empty columns for this line
        return [gen_values(e, user, related_entities) for e in related_entities or (None,)]

    def _get_value_flattened_subreport(self,
                                       entity: CremeEntity,
                                       user,
                                       scope: QuerySet,
                                       ) -> str:
        """Used as _get_value() method by subclasses which manage
        sub-reports (flattened sub-report case).
        """
        return self._generate_flattened_report(
            self._get_filtered_related_entities(entity, user), user, scope,
        )

    def _get_value_no_subreport(self,
                                entity: CremeEntity,
                                user,
                                scope: QuerySet,
                                ) -> str:
        """Used as _get_value() method by subclasses which manage
        sub-reports (no sub-report case).
        """
        qs = self._get_related_instances(entity, user)
        extract = self._related_model_value_extractor

        if issubclass(qs.model, CremeEntity):
            qs = EntityCredentials.filter(user, qs)

        return ', '.join(str(extract(instance)) for instance in qs)

    def _get_value_single(self,
                          entity: CremeEntity,
                          user,
                          scope: QuerySet,
                          ) -> str:
        """Used as _get_value() method by subclasses which does not manage
        sub-reports.
        """
        return (
            self._get_value_single_on_allowed(entity, user, scope)
            if user.has_perm_to_view(entity) else
            settings.HIDDEN_VALUE
        )

    def _get_value_single_on_allowed(self,
                                     entity: CremeEntity,
                                     user,
                                     scope: QuerySet,
                                     ) -> str:
        """Overload this in sub-class when you compute the hand value (entity is viewable)."""
        raise NotImplementedError

    def _handle_report_values(self,
                              entity: CremeEntity | None,
                              user,
                              scope: QuerySet,
                              ) -> list[str]:
        """@param entity: CremeEntity instance, or None."""
        return [
            rfield.get_value(entity, user, scope)
            for rfield in self._report_field.sub_report.columns
        ]

    def _related_model_value_extractor(self, instance: Model):
        return instance

    # TODO: property ??
    def get_linkable_ctypes(self) -> Iterable[ContentType] | None:
        """Return the ContentTypes which are compatible, in order to link a sub-report.
        @return A sequence of ContentTypes instances, or None (that means "can not link") ;
                an empty sequence means "All kind of CremeEntities are linkable".
        """
        return None

    def get_value(self,
                  entity: CremeEntity | None,
                  user,
                  scope: QuerySet,
                  ) -> str | list:
        """Extract the value from entity for a Report cell.
        @param entity: CremeEntity instance, or None.
        @param user: User instance ; used to compute credentials.
        @param scope: 'QuerySet' where 'entity' it coming from ; used by aggregates.
        """
        value = None

        if entity is None:  # e.g. a FK column was NULL, or the instance did not pass a filter
            if self._report_field.selected:
                # selected=True => self._report_field.sub_report is not None
                value = [self._handle_report_values(None, user, scope)]
        else:
            value = self._get_value(entity, user, scope)

        return '' if value is None else value

    @property
    def hidden(self) -> bool:
        "Is the hand hidden ? (see FieldsConfig or deleted CustomFields)."
        return False

    @property
    def title(self) -> str:
        return self._title

    # def to_entity_cell(self):
    #     "@return An equivalent EntityCell"
    #     return None #todo: avoid None


class ReportHandRegistry:
    __slots__ = ('_hands', )

    def __init__(self) -> None:
        self._hands: dict[int, type[ReportHand]] = {}

    def __call__(self, hand_id: int):
        assert hand_id not in self._hands, 'ID collision'

        def _aux(cls):
            self._hands[hand_id] = cls
            cls.hand_id = hand_id
            return cls

        return _aux

    def __getitem__(self, i: int) -> type[ReportHand]:
        return self._hands[i]

    def __iter__(self) -> Iterator[int]:
        return iter(self._hands)

    def get(self, i: int) -> type[ReportHand] | None:
        return self._hands.get(i)


REPORT_HANDS_MAP = ReportHandRegistry()


@REPORT_HANDS_MAP(constants.RFT_FIELD)
class RHRegularField(ReportHand):
    verbose_name = _('Regular field')

    _field_info: FieldInfo

    def __new__(cls, report_field: ReportField):
        try:
            field_info = FieldInfo(report_field.model, report_field.name)
        except FieldDoesNotExist as e:
            raise ReportHand.ValueError(
                f'Invalid field: "{report_field.name}" (does not exist)'
            ) from e

        info_length = len(field_info)
        if info_length > 1:
            if info_length > 2:
                raise ReportHand.ValueError(
                    f'Invalid field: "{report_field.name}" (too deep)'
                )

            second_part = field_info[1]

            if (
                isinstance(second_part, ForeignKey | ManyToManyField)
                and issubclass(second_part.remote_field.model, CremeEntity)
            ):
                raise ReportHand.ValueError(
                    f'Invalid field: "{report_field.name}" (no entity at depth=1)'
                )

        first_part = field_info[0]
        klass = (
            RHForeignKey if isinstance(first_part, ForeignKey) else
            RHManyToManyField if isinstance(first_part, ManyToManyField) else
            RHRegularField
        )

        instance: RHRegularField = ReportHand.__new__(klass)
        instance._field_info = field_info

        return instance

    def __init__(self, report_field, support_subreport=False, title=None):
        model = report_field.model
        super().__init__(
            report_field,
            title=title or self._field_info.verbose_name,
            support_subreport=support_subreport,
        )

        # TODO: FieldInfo is used by build_field_printer do the same work: can we factorise this ??
        self._printer = field_printer_registry.build_field_printer(
            model=model,
            field_name=report_field.name,
            tag=ViewTag.TEXT_PLAIN,
        )

    def _get_value_single_on_allowed(self, entity, user, scope) -> str:
        return self._printer(entity, user)

    @property
    def field_info(self) -> FieldInfo:
        return self._field_info

    @cached_property
    def hidden(self):
        return self._report_field.report._fields_configs.is_fieldinfo_hidden(self._field_info)


class RHForeignKey(RHRegularField):
    def __init__(self, report_field) -> None:
        field_info = self._field_info
        fk_field = field_info[0]
        self._fk_attr_name: str = fk_field.get_attname()
        fk_model = fk_field.remote_field.model
        self._linked2entity: bool = issubclass(fk_model, CremeEntity)
        qs = fk_model.objects.all()
        sub_report = report_field.sub_report

        if sub_report:
            efilter = sub_report.filter
            if efilter:
                qs = efilter.filter(qs)
        else:
            # Small optimization: only used by _get_value_no_subreport()
            if len(field_info) > 1:
                self._value_extractor = field_printer_registry.build_field_printer(
                    model=field_info[0].remote_field.model,
                    field_name=field_info[1].name,
                    tag=ViewTag.TEXT_PLAIN,
                )
            else:
                self._value_extractor = lambda fk_instance, user: str(fk_instance)

        self._qs = qs
        super().__init__(
            report_field,
            support_subreport=True,
            title=str(fk_field.verbose_name) if sub_report else None,
        )

    # NB: cannot rename to _get_related_instances() because forbidden entities
    #     are filtered instead of outputting '??'
    def _get_fk_instance(self, entity: CremeEntity) -> CremeEntity | None:
        try:
            rel_entity = self._qs.get(pk=getattr(entity, self._fk_attr_name))
        except ObjectDoesNotExist:
            rel_entity = None

        return rel_entity

    def _get_value_flattened_subreport(self, entity, user, scope):
        fk_entity = self._get_fk_instance(entity)

        if fk_entity is not None:  # TODO: test
            return self._generate_flattened_report((fk_entity,), user, scope)

    def _get_value_extended_subreport(self, entity, user, scope):
        return [self._handle_report_values(self._get_fk_instance(entity), user, scope)]

    def _get_value_no_subreport(self, entity, user, scope):
        fk_instance = self._get_fk_instance(entity)

        if fk_instance is not None:
            if self._linked2entity and not user.has_perm_to_view(fk_instance):
                return settings.HIDDEN_VALUE

            return self._value_extractor(fk_instance, user)

    def get_linkable_ctypes(self):
        return (
            ContentType.objects.get_for_model(self._qs.model),
        ) if self._linked2entity else None

    @property
    def linked2entity(self) -> bool:
        return self._linked2entity


class RHManyToManyField(RHRegularField):
    def __init__(self, report_field):
        super().__init__(report_field, support_subreport=True)
        field_info = self._field_info

        if len(field_info) > 1:
            attr_name = self._field_info[1].name
            # TODO: move "or ''" in base class ??
            self._related_model_value_extractor = (
                lambda instance: getattr(instance, attr_name, None) or ''
            )
        else:
            self._related_model_value_extractor = str

    def _get_related_instances(self, entity, user):
        return getattr(entity, self._field_info[0].name).all()

    def get_linkable_ctypes(self):
        m2m_model = self._field_info[0].remote_field.model

        return (
            ContentType.objects.get_for_model(m2m_model),
        ) if issubclass(m2m_model, CremeEntity) else None


@REPORT_HANDS_MAP(constants.RFT_CUSTOM)
class RHCustomField(ReportHand):
    verbose_name = _('Custom field')

    def __init__(self, report_field):
        try:
            self._cfield = cf = CustomField.objects.get(uuid=UUID(report_field.name))
        except (ValueError, CustomField.DoesNotExist) as e:
            raise ReportHand.ValueError(
                f'Invalid custom field: "{report_field.name}"'
            ) from e

        super().__init__(report_field, title=cf.name)

    def _get_value_single_on_allowed(self, entity, user, scope):
        cvalue = entity.get_custom_value(self._cfield)
        # TODO: use a EntityCellCustomField & remove __str__ methods of CustomFieldValue models ?
        return str(cvalue) if cvalue else ''

    @property
    def hidden(self):
        return self._cfield.is_deleted


@REPORT_HANDS_MAP(constants.RFT_RELATION)
class RHRelation(ReportHand):
    verbose_name = _('Relationship')

    def __init__(self, report_field):
        rtype_id = report_field.name

        try:
            self._rtype = rtype = RelationType.objects.get(id=rtype_id)
        except RelationType.DoesNotExist as e:
            raise ReportHand.ValueError(
                f'Invalid relation type: "{rtype_id}"'
            ) from e

        if report_field.sub_report:
            self._related_model = report_field.sub_report.ct.model_class()

        super().__init__(
            report_field,
            title=str(rtype.predicate),
            support_subreport=True,
        )

    def _get_related_instances(self, entity, user):
        return self._related_model.objects.filter(
            relations__type=self._rtype.symmetric_type,
            relations__object_entity=entity.id,
        )

    # TODO: add a feature in base class to retrieved efficiently real entities ??
    # TODO: extract algorithm that retrieve efficiently real entity from
    #       CremeEntity.get_related_entities()
    def _get_value_no_subreport(self, entity, user, scope):
        has_perm = user.has_perm_to_view
        return ', '.join(
            str(e)
            for e in entity.get_related_entities(self._rtype.id, True)
            if has_perm(e)
        )

    def get_linkable_ctypes(self):
        return self._rtype.object_ctypes.all()

    @property
    def hidden(self):
        return not self._rtype.enabled

    @property
    def relation_type(self) -> RelationType:
        return self._rtype


@REPORT_HANDS_MAP(constants.RFT_FUNCTION)
class RHFunctionField(ReportHand):
    verbose_name = _('Computed field')

    def __init__(self, report_field):
        # TODO: get registry as argument
        funcfield = function_field_registry.get(report_field.model, report_field.name)
        if not funcfield:
            raise ReportHand.ValueError(
                f'Invalid function field: "{report_field.name}"'
            )

        self._funcfield = funcfield

        super().__init__(report_field, title=str(funcfield.verbose_name))

    def _get_value_single_on_allowed(self, entity, user, scope):
        return self._funcfield(entity, user).render(tag=ViewTag.TEXT_PLAIN)


# TODO: pass field_aggregation_registry as argument
class RHAggregate(ReportHand):
    verbose_name = _('Aggregated value')

    def __init__(self, report_field):
        self._cache_key   = None
        self._cache_value = None
        self._decimal_pos = None
        field_name, aggregation_id = report_field.name.split('__', 1)
        aggregation = field_aggregation_registry.get(aggregation_id)

        if aggregation is None:
            raise ReportHand.ValueError(f'Invalid aggregation: "{aggregation_id}"')

        self._field_name = field_name
        self._aggregation_q, verbose_name = self._build_query_n_vname(
            report_field,
            field_name,
            aggregation,
        )

        super().__init__(
            report_field,
            title=f'{aggregation.title} - {verbose_name}',
        )

    def _build_query_n_vname(self,
                             report_field: ReportField,
                             field_name: str,
                             aggregation: FieldAggregation,
                             ) -> tuple[Aggregate, str]:
        raise NotImplementedError

    def _get_value_single(self, entity, user, scope):
        if self._cache_key is scope:
            return self._cache_value

        self._cache_key = scope

        agg_result = scope.aggregate(
            rh_calculated_agg=self._aggregation_q,
        ).get('rh_calculated_agg') or 0
        self._cache_value = result = number_format(
            agg_result,
            # NB: if we do not set this, computed Decimals have trailing '0's
            decimal_pos=self._decimal_pos,
        )

        return result


@REPORT_HANDS_MAP(constants.RFT_AGG_FIELD)
class RHAggregateRegularField(RHAggregate):
    def _build_query_n_vname(self, report_field, field_name, aggregation):
        try:
            field = report_field.model._meta.get_field(field_name)
        except FieldDoesNotExist as e:
            raise ReportHand.ValueError(f'Unknown field: "{field_name}"') from e

        if not field_aggregation_registry.is_regular_field_allowed(field):
            raise ReportHand.ValueError(
                f'This type of field can not be aggregated: "{field_name}"'
            )

        # TODO: ugly (use a side effect instead of returning data)
        self._decimal_pos = getattr(field, 'decimal_places', None)

        return aggregation.func(field_name), field.verbose_name

    @cached_property
    def hidden(self):
        rfield = self._report_field

        return rfield.report._fields_configs.get_for_model(
            rfield.model,
        ).is_fieldname_hidden(
            self._field_name,
        )


@REPORT_HANDS_MAP(constants.RFT_AGG_CUSTOM)
class RHAggregateCustomField(RHAggregate):
    verbose_name = _('Aggregated value (custom field)')

    def _build_query_n_vname(self, report_field, field_name, aggregation):
        try:
            cfield = CustomField.objects.get(uuid=UUID(field_name))
        except (ValueError, CustomField.DoesNotExist) as e:
            raise ReportHand.ValueError(
                f'Invalid custom field aggregation: "{field_name}"'
            ) from e

        if not field_aggregation_registry.is_custom_field_allowed(cfield):
            raise ReportHand.ValueError(
                f'This type of custom field can not be aggregated: "{cfield.name}"'
            )

        value_class = cfield.value_class

        self._cfield = cfield  # TODO: ugly to set out of __init__ ...
        # TODO: ugly (use a side effect instead of returning data)
        self._decimal_pos = getattr(value_class._meta.get_field('value'), 'decimal_places', None)

        return (
            aggregation.func(f'{value_class.get_related_name()}__value'),
            cfield.name,
        )

    @property
    def hidden(self):
        return self._cfield.is_deleted


@REPORT_HANDS_MAP(constants.RFT_RELATED)
class RHRelated(ReportHand):
    verbose_name = _('Related field')

    def __init__(self, report_field) -> None:
        related_field = self._get_related_field(
            report_field.model,
            report_field.name,
        )

        if related_field is None:
            raise ReportHand.ValueError(
                f'Invalid related field: "{report_field.name}"'
            )

        self._related_field = related_field
        self._attr_name: str = related_field.get_accessor_name()

        super().__init__(
            report_field,
            title=model_verbose_name(related_field.related_model),
            support_subreport=True,
        )

    @staticmethod
    def _get_related_field(model: type[CremeEntity],
                           related_field_name: str,
                           ) -> Field | None:
        try:
            field = model._meta.get_field(related_field_name)
        except FieldDoesNotExist as e:
            logger.warning(
                'RHRelated._get_related_field(): problem with field "%s" ("%s")',
                related_field_name, e,
            )
            return None

        if not field.is_relation:
            logger.warning(
                'RHRelated._get_related_field(): the field "%s" is not a FK/M2M',
                related_field_name,
            )
            return None

        if related_field_name not in model.allowed_related:
            logger.warning(
                'RHRelated._get_related_field(): the field "%s" is not allowed',
                related_field_name,
            )
            return None

        return field

    def _get_related_instances(self, entity, user):
        return getattr(entity, self._attr_name).filter(is_deleted=False)

    def get_linkable_ctypes(self):
        return (
            ContentType.objects.get_for_model(self._related_field.related_model),
        )


class ExpandableLine:
    """Store a line of report values that can be expanded in several lines if
    there are selected sub-reports.
    """
    def __init__(self, values: list[str | list]):
        self._cvalues = values

    def _visit(self, lines: list, current_line: list) -> None:
        values: list[str | None] = []
        values_to_build = None

        for col_value in self._cvalues:
            if isinstance(col_value, list):
                values.append(None)
                values_to_build = col_value
            else:
                values.append(col_value)

        if None in current_line:
            idx = current_line.index(None)
            current_line[idx:idx + 1] = values
        else:
            current_line.extend(values)

        if values_to_build is not None:
            cls = type(self)

            for future_node in values_to_build:
                cls(future_node)._visit(lines, [*current_line])
        else:
            lines.append(current_line)

    def get_lines(self) -> list[list[str]]:
        lines: list[list[str]] = []
        self._visit(lines, [])

        return lines
