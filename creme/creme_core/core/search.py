# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2021  Hybird
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

# from functools import reduce
# from operator import or_
import logging
from typing import Dict, Iterable, List, Optional, Type

from django.db.models import Model
from django.db.models.query import Q, QuerySet

from ..core import entity_cell
from ..models import CustomField, FieldsConfig, SearchConfigItem
# from ..models.search import SearchField
from ..utils.string import smart_split

logger = logging.getLogger(__name__)


# TODO: see creme_core.forms.listview.CustomCharField/CustomChoiceField
def _q_for_customfield(cell, word):
    field_type = cell.custom_field.field_type
    if field_type == CustomField.ENUM:
        # TODO: avoid a JOIN by doing a first query in Enum values ?
        return Q(
            pk__in=cell.custom_field
                       .value_class
                       .objects
                       .filter(custom_field=cell.custom_field, value__value__icontains=word)
                       .values_list('entity_id', flat=True)
        )
    elif field_type == CustomField.MULTI_ENUM:
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
    else:
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

    def __init__(self, models: Iterable[Type[Model]], user):
        """Constructor.

        @param models: Iterable of classes inheriting <django.db.models.Model>.
        @param user: Instance of <django.contrib.auth.get_user_model()>.
        """
        self.user = user

        # search_map: Dict[Type[Model], List[SearchField]] = {}
        search_map: Dict[Type[Model], List[entity_cell.EntityCell]] = {}
        models = [*models]  # Several iterations
        # fconfigs = FieldsConfig.objects.get_for_models(models)
        # TODO: move in iter_for_models() ?
        FieldsConfig.objects.get_for_models(models)  # Fill cache

        for sci in SearchConfigItem.objects.iter_for_models(models, user):
            if not sci.disabled:
                model = sci.content_type.model_class()
                # is_hidden = fconfigs[model].is_fieldname_hidden
                search_map[model] = [
                    # sfield
                    # for sfield in sci.searchfields
                    # if not is_hidden(sfield.name.split('__', 1)[0])
                    *sci.refined_cells
                ]

        self._search_map = search_map

    # def _build_query(self, words, fields) -> Q:
    def _build_query(self, words, cells) -> Q:
        """Build a Q with given fields for the given search.
        Each word must be contained in (at least) one field.

        @param words: Searched strings.
        # @param fields: Sequence of <creme_core.models.search.SearchField> objects.
        @param cells: Sequence of <creme_core.core.entity_cell.EntityCell> objects.
        @return: Instance of <django.db.models.query.Q>.
        """
        result_q = Q()
        get_q_builder = self.CELL_TO_Q.get

        for word in words:
            # result_q &= reduce(
            #     or_,
            #     (Q(**{f'{field.name}__icontains': word}) for field in fields)
            # )
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

    # def get_fields(self, model):
    #     """Get the list of SearchFields instances used to search in 'model'.
    #
    #     @param model: Class inheriting <django.db.models.Model>.
    #     @return: List of <creme_core.models.search.SearchField> objects.
    #     """
    #     return self._search_map[model]
    def get_cells(self, model: Type[Model]) -> List[entity_cell.EntityCell]:
        """Get the list of EntityCells instances used to search in 'model'."""
        return self._search_map[model]

    @property
    def models(self):
        "View on the models this Searcher use."
        return self._search_map.keys()

    def search(self, model: Type[Model], research: str) -> Optional[QuerySet]:
        """Return a query with the models which fields contain the wanted value.
        @param model: Class inheriting django.db.Model (CremeEntity)
        @param research: Searched string ; it's split in words (see utils.string.smart_split()).
        @return: Queryset on model or None ; None means 'All fields are hidden'.
        """
        # searchfields = self.get_fields(model)
        cells = self.get_cells(model)

        # assert searchfields is not None  # search on a disabled model ?
        assert cells is not None  # search on a disabled model ?

        strings = smart_split(research)

        # TODO: distinct() only if there is a JOIN...
        # return model.objects.filter(
        #     self._build_query(strings, searchfields)
        # ).distinct() if searchfields else None
        return model.objects.filter(
            self._build_query(strings, cells)
        ).distinct() if cells else None
