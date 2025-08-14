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
from collections.abc import Iterator
from functools import partial
from typing import TYPE_CHECKING
from uuid import UUID

from django.core.exceptions import FieldDoesNotExist
from django.db.models import ForeignKey, Q
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext

from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.models import (
    CremeEntity,
    FieldsConfig,
    InstanceBrickConfigItem,
    RelationType,
)
from creme.creme_core.models.utils import model_verbose_name
from creme.creme_core.utils.meta import ModelFieldEnumerator

# from creme.reports import constants
if TYPE_CHECKING:
    from django.db.models import Field

    from creme.creme_core.gui.bricks import InstanceBrick
    from creme.creme_core.models import CremeUser
    from creme.reports.models import ReportChart

logger = logging.getLogger(__name__)


class ChartFetcher:
    """A chart fetcher can fetch the result of a given ReportChart, with or
    without a volatile link.
    It stores the verbose name of this link (for UI), and an error if the link
    data were invalid.
    """
    type_id = ''
    verbose_name = ''
    choices_group_name = ''
    error: str | None = None

    DICT_KEY_TYPE  = 'type'
    DICT_KEY_VALUE = 'value'
    DICT_KEYS = (DICT_KEY_TYPE, DICT_KEY_VALUE)

    class IncompatibleContentType(Exception):
        pass

    class UselessResult(Exception):
        pass

    def __init__(self,
                 chart: ReportChart,
                 value: str | None = None,
                 ):
        self.chart = chart
        self.value = value

    def as_dict_items(self):
        yield self.DICT_KEY_TYPE, self.type_id

        if self.value:
            yield self.DICT_KEY_VALUE, self.value

    @classmethod
    def choices(cls,
                model: type[CremeEntity],
                ) -> Iterator[tuple[str, str | list[tuple[str, str]]]]:
        raise NotImplementedError

    def create_brick_config_item(self,
                                 brick_class: type[InstanceBrick] | None = None,
                                 uuid: str | UUID | None = None,
                                 ) -> InstanceBrickConfigItem:
        if brick_class is None:
            from creme.reports.bricks import ReportChartInstanceBrick
            brick_class = ReportChartInstanceBrick

        chart = self.chart
        ibci = InstanceBrickConfigItem(
            entity=chart.linked_report,
            brick_class_id=brick_class.id,
        )
        ibci.set_extra_data(key=brick_class.chart_key, value=str(chart.uuid))

        if uuid:
            ibci.uuid = uuid

        for k, v in self.as_dict_items():
            ibci.set_extra_data(key=k, value=v)

        # TODO: argument to not commit ?
        ibci.save()

        return ibci

    def fetch(self, user, order: str = 'ASC') -> tuple[list[str], list]:
        return self.chart.fetch(user=user, order=order)

    def _aux_fetch_4_entity(self,
                            entity: CremeEntity,
                            user: CremeUser,
                            order: str):
        "To be overridden in child classes."
        return self.fetch(user=user, order=order)

    def fetch_4_entity(self,
                       entity: CremeEntity,
                       user: CremeUser,
                       order: str = 'ASC',
                       ) -> tuple[list[str], list]:
        """
        Data of the ReportChart narrowed to the entities linked to one
        entity (e.g. the entity corresponding to the visited detail-view).
        @param entity: Entity used to narrow the results.
        @param user: logged user.
        @param order: 'ASC' or 'DESC'.
        @return: see <ChartHand.fetch()>.
        @raise GraphFetcher.IncompatibleContentType if the ContentType of 'entity'
               is wrong (i.e. the configuration should probably be fixed).
        @raise ChartFetcher.UselessResult if fetching data for 'entity' is useless
               (e.g. it does mean anything in the business logic).
        """
        return (
            [], []
        ) if self.error else self._aux_fetch_4_entity(
            entity=entity, user=user, order=order,
        )

    @property
    def linked_models(self) -> list[type[CremeEntity]]:
        """List of models which are compatible for the volatile link.
        (i.e. the argument 'entity' of 'fetch_4_entity()' should be an instance
        of one of this model).
        An empty list means <all types of CremeEntity are accepted>.
        """
        return []


class SimpleChartFetcher(ChartFetcher):
    type_id = 'reports-no_link'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose_name = _('No volatile column')

        if self.value:
            self.error = _('No value is needed.')

    @classmethod
    def choices(cls, model):
        yield '', pgettext('reports-volatile_choice', 'None')


class RegularFieldLinkedChartFetcher(ChartFetcher):
    type_id = 'reports-fk'
    choices_group_name = _('Fields')

    _field: Field | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model = self.chart.model
        self._field = None
        self.verbose_name = '??'

        field_name = self.value
        if not field_name:
            logger.warning('Instance block: no given field in block config.')
            self.error = _('No field given.')
        else:
            try:
                field = model._meta.get_field(field_name)
            except FieldDoesNotExist as e:
                logger.warning(
                    'Instance block: invalid field in block config: %s',
                    e,
                )
                self.error = _('The field is invalid.')
            else:
                fconf = FieldsConfig.LocalCache()
                error = self._check_field(field=field, fields_configs=fconf)
                if error:
                    logger.warning(
                        'Instance block: invalid field in block config: %s',
                        error,
                    )
                    self.error = error
                else:
                    self.verbose_name = gettext('{field} (Field)').format(
                        field=field.verbose_name,
                    )
                    self._field = field

    @staticmethod
    def _check_field(field, fields_configs: FieldsConfig.LocalCache) -> str | None:
        if not isinstance(field, ForeignKey):
            return _('The field is invalid (not a foreign key).')

        if not issubclass(field.remote_field.model, CremeEntity):
            return _('The field is invalid (not a foreign key to CremeEntity).')

        if not field.get_tag(FieldTag.VIEWABLE):
            return 'the field is not viewable'  # TODO: test

        # TODO: take model as parameter because field.model could refer the
        #       parent class if the field is inherited (currently only "description")
        if fields_configs.get_for_model(field.model).is_field_hidden(field):
            return _('The field is hidden.')

        return None

    def _aux_fetch_4_entity(self, entity, order, user):
        field = self._field
        assert field is not None

        return self.chart.fetch(
            extra_q=Q(**{field.name: entity.pk}), order=order, user=user,
        ) if isinstance(entity, field.remote_field.model) else (
            [], []
        )

    @classmethod
    def choices(cls, model):
        fconf = FieldsConfig.LocalCache()
        check_field = partial(cls._check_field, fields_configs=fconf)

        yield from ModelFieldEnumerator(
            model, depth=0, only_leaves=False,
        ).filter(
            lambda model, field, depth: check_field(field=field) is None,
        ).choices()

    @property
    def linked_models(self):
        field = self._field
        assert field is not None

        return [field.remote_field.model]


class RelationLinkedChartFetcher(ChartFetcher):
    type_id = 'reports-relation'
    choices_group_name = _('Relationships')

    _rtype: RelationType | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose_name = '??'
        self._rtype = None
        rtype_id = self.value

        if not rtype_id:
            self.error = _('No relationship type given.')
        else:
            try:
                # TODO: selected_relation('symmetric_type') ??
                rtype = RelationType.objects.get(pk=rtype_id)
            except RelationType.DoesNotExist as e:
                logger.warning(
                    'Instance block: invalid RelationType in block config: %s',
                    e,
                )
                self.error = _('The relationship type is invalid.')
            else:
                model = self.chart.model
                if not rtype.is_compatible(model):
                    self.error = gettext(
                        'The relationship type is not compatible with «{}».'
                    ).format(model_verbose_name(model))
                else:
                    self.verbose_name = gettext(
                        '{rtype} (Relationship)'
                    ).format(rtype=rtype)
                    self._rtype = rtype

    def _aux_fetch_4_entity(self, entity, order, user):
        rtype = self._rtype
        assert rtype is not None

        return self.chart.fetch(
            extra_q=Q(
                relations__type=rtype,
                relations__object_entity=entity.pk,
            ),
            user=user,
            order=order,
        )

    @classmethod
    def choices(cls, model):
        for rtype in RelationType.objects.compatible(model, include_internals=True):
            yield rtype.id, str(rtype)

    @property
    def linked_models(self):
        rtype = self._rtype
        assert rtype is not None

        # TODO: should we check the properties constraints too (in _aux_fetch_4_entity() ??
        return [ct.model_class() for ct in rtype.object_ctypes.all()]


# ------------------------------------------------------------------------------
class ChartFetcherRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self, default_class: type[ChartFetcher]):
        self._fetcher_classes: dict[str, type[ChartFetcher]] = {}
        self.default_class = default_class

    def _build_default_fetcher(self, chart):
        fetcher = self.default_class(chart=chart)
        fetcher.error = _('Invalid volatile link; please contact your administrator.')

        return fetcher

    def register(self, *fetcher_classes: type[ChartFetcher]) -> ChartFetcherRegistry:
        set_default = self._fetcher_classes.setdefault

        for fetcher_cls in fetcher_classes:
            if set_default(fetcher_cls.type_id, fetcher_cls) is not fetcher_cls:
                raise self.RegistrationError(
                    f'{type(self).__name__}.register(): '
                    f'the ID "{fetcher_cls.type_id}" is already used'
                    f'(trying to register class {fetcher_cls}).'
                )

        return self

    def get(self,
            chart: ReportChart,
            fetcher_dict: dict[str, str],
            ) -> ChartFetcher:
        try:
            fetcher_type_id = fetcher_dict[ChartFetcher.DICT_KEY_TYPE]
        except KeyError:
            logger.warning(
                '%s.get(): no fetcher ID given (basic fetcher is used).',
                type(self).__name__,
            )

            return self._build_default_fetcher(chart=chart)
        else:
            fetcher_cls = self._fetcher_classes.get(fetcher_type_id)

            if fetcher_cls is None:
                logger.warning(
                    '%s.get(): invalid ID "%s" for fetcher (basic fetcher is used).',
                    type(self).__name__, fetcher_type_id,
                )

                return self._build_default_fetcher(chart=chart)

        return fetcher_cls(
            chart=chart,
            value=fetcher_dict.get(ChartFetcher.DICT_KEY_VALUE),
        )

    @property
    def fetcher_classes(self) -> Iterator[type[ChartFetcher]]:
        yield from self._fetcher_classes.values()


chart_fetcher_registry = ChartFetcherRegistry(SimpleChartFetcher)
