# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2019  Hybird
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

from functools import reduce
from operator import or_

from django.db.models.query import Q

from ..models import SearchConfigItem, FieldsConfig
from ..utils.string import smart_split


class Searcher:
    """Build QuerySets to search strings contained in instances of some given models.

    The search configuration (see the model SearchConfigItem) is used to know
    which fields to use.
    Hidden fields (see model FieldsConfig) are ignored.
    """
    def __init__(self, models, user):
        """Constructor.

        @param models: Iterable of classes inheriting <django.db.models.Model>.
        @param user: Instance of <django.contrib.auth.get_user_model()>.
        """
        self.user = user
        self._search_map = search_map = {}
        models = [*models]  # Several iterations
        fconfigs = FieldsConfig.get_4_models(models)

        for sci in SearchConfigItem.get_4_models(models, user):
            if not sci.disabled:
                model = sci.content_type.model_class()
                is_hidden = fconfigs[model].is_fieldname_hidden
                # TODO: work with FieldInfo instead of strings + split() (see creme_config too)
                search_map[model] = [sfield
                                        for sfield in sci.searchfields
                                            if not is_hidden(sfield.name.split('__', 1)[0])
                                    ]

    # def _build_query(self, research, fields):
    #     result_q = Q()
    #
    #     for f in fields:
    #         result_q |= Q(**{'{}__icontains'.format(f.name): research})
    #
    #     return result_q
    def _build_query(self, words, fields):
        """Build a Q with given fields for the given search.
        Each word must be contained in (at least) one field.

        @param words: Searched strings.
        @param fields: Sequence of <creme_core.models.search.SearchField> objects.
        @return: Instance of <django.db.models.query.Q>.
        """
        result_q = Q()

        for word in words:
            result_q &= reduce(or_, (Q(**{'{}__icontains'.format(field.name): word}) for field in fields))

        return result_q

    def get_fields(self, model):
        """Get the list of SearchFields instances used to search in 'model'.

        @param model: Class inheriting <django.db.models.Model>.
        @return: List of <creme_core.models.search.SearchField> objects.
        """
        return self._search_map[model]

    @property
    def models(self):
        "View on the models this Searcher use."
        return self._search_map.keys()

    def search(self, model, research):
        """Return a query with the models which fields contain the wanted value.
        @param model: Class inheriting django.db.Model (CremeEntity)
        @param research: Searched string ; it's split in words (see utils.string.smart_split()).
        @return: Queryset on model or None ; None means 'All fields are hidden'.
        """
        searchfields = self.get_fields(model)

        assert searchfields is not None  # search on a disabled model ?

        strings = smart_split(research)

        # TODO: distinct() only if there is a JOIN...
        # return model.objects.filter(self._build_query(research, searchfields)).distinct() \
        #        if searchfields else None
        return model.objects.filter(self._build_query(strings, searchfields)).distinct() \
               if searchfields else None
