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

from collections import defaultdict

from django.db.models.query_utils import Q
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

import creme.creme_core.forms.listview as lv_form
from creme.creme_core.core.function_field import (
    FunctionField,
    FunctionFieldResult,
    FunctionFieldResultsList,
)

from .models import Alert, Memo, ToDo


class AlertsSearchField(lv_form.ListViewSearchField):
    widget = lv_form.TextLVSWidget

    def to_python(self, value):
        return Q(
            assistants_alerts__title__icontains=value,
            assistants_alerts__is_validated=False,
        ) if value else Q()


class MemosSearchField(lv_form.ListViewSearchField):
    widget = lv_form.TextLVSWidget

    def to_python(self, value):
        return Q(assistants_memos__content__icontains=value) if value else Q()


class TodosSearchField(lv_form.ListViewSearchField):
    widget = lv_form.TextLVSWidget

    def to_python(self, value):
        return Q(
            assistants_todos__title__icontains=value,
            assistants_todos__is_ok=False,
        ) if value else Q()


class _CachedFunctionField(FunctionField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = defaultdict(list)


class AlertsField(_CachedFunctionField):
    name = 'assistants-get_alerts'
    verbose_name = _('Active alerts')
    result_type = FunctionFieldResultsList
    search_field_builder = AlertsSearchField

    def __call__(self, entity, user):
        cache = self._cache
        e_id = entity.id
        cached = cache.get(e_id)

        if cached is None:
            cached = cache[e_id] = [
                *Alert.objects
                      .filter(entity_id=e_id, is_validated=False)
                      .order_by('trigger_date')
                      .values_list('title', flat=True)
            ] if user.has_perm_to_access('assistants') else [gettext('Forbidden app')]

        return FunctionFieldResultsList(
            FunctionFieldResult(title) for title in cached
        )

    def populate_entities(self, entities, user):
        if user.has_perm_to_access('assistants'):
            cache = self._cache

            for title, e_id in Alert.objects.filter(
                entity_id__in=[e.id for e in entities if e.id not in cache],
                is_validated=False,
            ).order_by('trigger_date').values_list('title', 'entity_id'):
                cache[e_id].append(title)


class MemosField(_CachedFunctionField):
    name = 'assistants-get_memos'
    verbose_name = _('Memos')
    result_type = FunctionFieldResultsList
    search_field_builder = MemosSearchField

    def __call__(self, entity, user):
        cache = self._cache
        e_id = entity.id
        cached = cache.get(e_id)

        if cached is None:
            cached = cache[e_id] = [
                *Memo.objects
                     .filter(entity_id=entity.id)
                     .order_by('-creation_date')
                     .values_list('content', flat=True)
            ] if user.has_perm_to_access('assistants') else [gettext('Forbidden app')]

        return FunctionFieldResultsList(
            FunctionFieldResult(content) for content in cached
        )

    def populate_entities(self, entities, user):
        if user.has_perm_to_access('assistants'):
            cache = self._cache

            for content, e_id in Memo.objects.filter(
                entity_id__in=[e.id for e in entities if e.id not in cache],
            ).order_by('-creation_date').values_list('content', 'entity_id'):
                cache[e_id].append(content)


class TodosField(_CachedFunctionField):
    name = 'assistants-get_todos'
    verbose_name = _('Active Todos')
    result_type = FunctionFieldResultsList
    search_field_builder = TodosSearchField

    def __call__(self, entity, user):
        cache = self._cache
        e_id = entity.id
        cached = cache.get(e_id)

        if cached is None:
            cached = cache[e_id] = [
                *ToDo.objects
                     .filter(entity_id=entity.id, is_ok=False)
                     .order_by('-creation_date')
                     .values_list('title', flat=True)
            ] if user.has_perm_to_access('assistants') else [gettext('Forbidden app')]

        return FunctionFieldResultsList(
            FunctionFieldResult(title) for title in cached
        )

    def populate_entities(self, entities, user):
        if user.has_perm_to_access('assistants'):
            cache = self._cache

            for title, e_id in ToDo.objects.filter(
                entity_id__in=[e.id for e in entities if e.id not in cache],
                is_ok=False,
            ).order_by('-creation_date').values_list('title', 'entity_id'):
                cache[e_id].append(title)
