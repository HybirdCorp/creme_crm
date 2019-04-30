# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.function_field import (FunctionField,
        FunctionFieldResult, FunctionFieldResultsList)

from .models import Alert, Memo, ToDo


class _CachedFunctionField(FunctionField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = defaultdict(list)


# class AlertsField(FunctionField):
class AlertsField(_CachedFunctionField):
    name         = 'assistants-get_alerts'
    verbose_name = _('Alerts')
    result_type  = FunctionFieldResultsList

    def __call__(self, entity, user):
        # cache = getattr(entity, '_alerts_cache', None)
        #
        # if cache is None:
        #     cache = entity._alerts_cache = list(Alert.objects
        #                                              .filter(entity_id=entity.id, is_validated=False)
        #                                              .order_by('trigger_date')
        #                                              .values_list('title', flat=True)
        #                                        )
        #
        # return FunctionFieldResultsList(FunctionFieldResult(title) for title in cache)
        cache = self._cache
        e_id = entity.id
        cached = cache.get(e_id)

        if cached is None:
            cached = cache[e_id] = list(Alert.objects
                                             .filter(entity_id=e_id, is_validated=False)
                                             .order_by('trigger_date')
                                             .values_list('title', flat=True)
                                       )

        return FunctionFieldResultsList(FunctionFieldResult(title) for title in cached)

    # @classmethod
    # def populate_entities(cls, entities, user):
    #     alerts_map = defaultdict(list)
    #
    #     for title, e_id in Alert.objects.filter(entity_id__in=[e.id for e in entities], is_validated=False) \
    #                                     .order_by('trigger_date') \
    #                                     .values_list('title', 'entity_id'):
    #         alerts_map[e_id].append(title)
    #
    #     for entity in entities:
    #         entity._alerts_cache = alerts_map[entity.id]
    def populate_entities(self, entities, user):
        cache = self._cache

        for title, e_id in Alert.objects \
                                .filter(entity_id__in=[e.id for e in entities if e.id not in cache],
                                        is_validated=False,
                                       ) \
                                .order_by('trigger_date') \
                                .values_list('title', 'entity_id'):
            cache[e_id].append(title)


# class MemosField(FunctionField):
class MemosField(_CachedFunctionField):
    name         = 'assistants-get_memos'
    verbose_name = _('Memos')
    result_type  = FunctionFieldResultsList

    def __call__(self, entity, user):
        # cache = getattr(entity, '_memos_cache', None)
        #
        # if cache is None:
        #     cache = entity._memos_cache = list(Memo.objects.filter(entity_id=entity.id)
        #                                                    .order_by('-creation_date')
        #                                                    .values_list('content', flat=True)
        #                                       )
        #
        # return FunctionFieldResultsList(FunctionFieldResult(content) for content in cache)
        cache = self._cache
        e_id = entity.id
        cached = cache.get(e_id)

        if cached is None:
            cached = cache[e_id] = list(Memo.objects.filter(entity_id=entity.id)
                                                    .order_by('-creation_date')
                                                    .values_list('content', flat=True)
                                       )

        return FunctionFieldResultsList(FunctionFieldResult(content) for content in cached)

    # @classmethod
    # def populate_entities(cls, entities, user):
    #     memos_map = defaultdict(list)
    #
    #     for content, e_id in Memo.objects.filter(entity_id__in=[e.id for e in entities]) \
    #                                      .order_by('-creation_date') \
    #                                      .values_list('content', 'entity_id'):
    #         memos_map[e_id].append(content)
    #
    #     for entity in entities:
    #         entity._memos_cache = memos_map[entity.id]
    def populate_entities(self, entities, user):
        cache = self._cache

        for content, e_id in Memo.objects \
                                 .filter(entity_id__in=[e.id for e in entities if e.id not in cache]) \
                                 .order_by('-creation_date') \
                                 .values_list('content', 'entity_id'):
            cache[e_id].append(content)


# class TodosField(FunctionField):
class TodosField(_CachedFunctionField):
    name         = 'assistants-get_todos'
    verbose_name = _('Todos')
    result_type  = FunctionFieldResultsList

    def __call__(self, entity, user):
        # cache = getattr(entity, '_todos_cache', None)
        #
        # if cache is None:
        #     cache = entity._todos_cache = list(ToDo.objects.filter(entity_id=entity.id, is_ok=False)
        #                                                    .order_by('-creation_date')
        #                                                    .values_list('title', flat=True)
        #                                       )
        #
        # return FunctionFieldResultsList(FunctionFieldResult(title) for title in cache)
        cache = self._cache
        e_id = entity.id
        cached = cache.get(e_id)

        if cached is None:
            cached = cache[e_id] = list(ToDo.objects.filter(entity_id=entity.id, is_ok=False)
                                                    .order_by('-creation_date')
                                                    .values_list('title', flat=True)
                                       )

        return FunctionFieldResultsList(FunctionFieldResult(title) for title in cached)

    # @classmethod
    # def populate_entities(cls, entities, user):
    #     todos_map = defaultdict(list)
    #
    #     for title, e_id in ToDo.objects.filter(entity_id__in=[e.id for e in entities], is_ok=False) \
    #                                    .order_by('-creation_date') \
    #                                    .values_list('title', 'entity_id'):
    #         todos_map[e_id].append(title)
    #
    #     for entity in entities:
    #         entity._todos_cache = todos_map[entity.id]
    def populate_entities(self, entities, user):
        cache = self._cache

        for title, e_id in ToDo.objects \
                               .filter(entity_id__in=[e.id for e in entities if e.id not in cache],
                                       is_ok=False,
                                      ) \
                               .order_by('-creation_date') \
                               .values_list('title', 'entity_id'):
            cache[e_id].append(title)
