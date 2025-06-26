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

import logging
from collections.abc import Iterable

from django.db.models import Model
from django.db.models.query import Q, QuerySet

from ..core import entity_cell
from ..models import CustomField, FieldsConfig, SearchConfigItem
from ..utils.string import smart_split

logger = logging.getLogger(__name__)


# TODO: see creme_core.forms.listview.CustomCharField/CustomChoiceField
def _q_for_customfield(cell, word):
    match cell.custom_field.field_type:
        case CustomField.ENUM:
            # TODO: avoid a JOIN by doing a first query in Enum values ?
            return Q(
                pk__in=cell.custom_field
                           .value_class
                           .objects
                           .filter(custom_field=cell.custom_field, value__value__icontains=word)
                           .values_list('entity_id', flat=True)
            )
        case CustomField.MULTI_ENUM:
            enum_ids = (
                cell.custom_field
                    .customfieldenumvalue_set
                    .filter(value__icontains=word)
                    .values_list('id', flat=True)
            )

            return Q(
                pk__in=cell.custom_field
                           .value_class
                           .objects
                           .filter(custom_field=cell.custom_field, value__in=enum_ids)
                           .values_list('entity_id', flat=True)
            )
        case _:
            return Q(
                pk__in=cell.custom_field
                           .value_class
                           .objects
                           .filter(custom_field=cell.custom_field, value__icontains=word)
                           .values_list('entity_id', flat=True)
            )


class Searcher:
    """Build QuerySets to search strings contained in instances of some given models.

    The search configuration (see the model SearchConfigItem) is used to know
    which fields to use.
    Hidden fields (see model FieldsConfig) are ignored.
    """
    CELL_TO_Q = {
        entity_cell.EntityCellRegularField.type_id:
            lambda cell, word: Q(**{f'{cell.value}__icontains': word}),

        entity_cell.EntityCellCustomField.type_id: _q_for_customfield,
    }

    def __init__(self, models: Iterable[type[Model]], user):
        """Constructor.

        @param models: Iterable of classes inheriting <django.db.models.Model>.
        @param user: Instance of <django.contrib.auth.get_user_model()>.
        """
        self.user = user

        search_map: dict[type[Model], list[entity_cell.EntityCell]] = {}
        models = [*models]  # Several iterations
        # TODO: move in iter_for_models() ?
        FieldsConfig.objects.get_for_models(models)  # Fill cache

        for sci in SearchConfigItem.objects.iter_for_models(models, user):
            if not sci.disabled:
                model = sci.content_type.model_class()
                search_map[model] = [*sci.refined_cells]

        self._search_map = search_map

    def _build_query(self, words, cells) -> Q:
        """Build a Q with given fields for the given search.
        Each word must be contained in (at least) one field.

        @param words: Searched strings.
        @param cells: Sequence of <creme_core.core.entity_cell.EntityCell> objects.
        @return: Instance of <django.db.models.query.Q>.
        """
        result_q = Q()
        get_q_builder = self.CELL_TO_Q.get

        for word in words:
            word_q = Q()
            for cell in cells:
                builder = get_q_builder(cell.type_id)
                if builder:
                    word_q |= builder(cell, word)
                else:
                    logger.warning(
                        '%s._build_query: cell type not managed "%s".',
                        type(self).__name__, cell.type_id,
                    )

            result_q &= word_q

        return result_q

    def get_cells(self, model: type[Model]) -> list[entity_cell.EntityCell]:
        """Get the list of EntityCells instances used to search in 'model'."""
        return self._search_map[model]

    @property
    def models(self):
        "View on the models this Searcher use."
        return self._search_map.keys()

    def search(self, model: type[Model], searched: str) -> QuerySet | None:
        """Return a query with the models which fields contain the wanted value.
        @param model: Class inheriting django.db.Model (CremeEntity)
        @param searched: Searched string; it's split in words (see <utils.string.smart_split()>).
        @return: Queryset on model or None; None means 'All fields are hidden'.
        """
        cells = self.get_cells(model)

        assert cells is not None  # search on a disabled model ?

        strings = smart_split(searched)

        # TODO: distinct() only if there is a JOIN...
        return model.objects.filter(
            self._build_query(strings, cells)
        ).distinct() if cells else None
