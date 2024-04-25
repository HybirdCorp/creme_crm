################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2024  Hybird
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

from django.db.models import Q
from django.utils.translation import gettext as _

from creme.creme_core.auth import EntityCredentials
from creme.creme_core.core import enumerable
from creme.creme_core.models import (
    CremeEntity,
    CustomField,
    CustomFieldEnumValue,
)
from creme.creme_core.utils.content_type import ctype_choices, entity_ctypes
from creme.creme_core.utils.unicode_collation import collator

logger = logging.getLogger(__name__)


# NB: currently not used by UI, it's here for security purposes
class EntityEnumerator(enumerable.QSEnumerator):
    search_fields = ('header_filter_search_field',)

    def _queryset(self, user):
        qs = super()._queryset(user=user)

        # TODO: unit test (new fake model?)
        model = qs.model
        if model is CremeEntity:
            logger.warning(
                'Cannot enumerate a ForeignKey which references just <CremeEntity>: %s',
                self.field,
            )
            return model.objects.none()

        return EntityCredentials.filter(user=user, queryset=qs)


class UserEnumerator(enumerable.QSEnumerator):
    search_fields = ('first_name', 'last_name', 'username')

    @classmethod
    def instance_as_dict(cls, instance):
        d = {'value': instance.pk}

        if instance.is_team:
            # NB: we avoid the " (team)" suffix, because we create group> for teams.
            d['label'] = instance.username
            d['group'] = _('Teams')
        else:
            d['label'] = str(instance)

            if not instance.is_active:
                d['group'] = _('Inactive users')

        return d

    def choices(self, user, *, term=None, only=None, limit=None):
        # Do not apply limits on queryset, because ordering is done later
        choices = super().choices(user, term=term, only=only)

        sort_key = collator.sort_key
        choices.sort(key=lambda d: sort_key(f"{d.get('group', '')}#{d['label']}"))

        return choices[:limit] if limit else choices


class EntityFilterEnumerator(enumerable.QSEnumerator):
    search_fields = ('name',)

    @classmethod
    def instance_as_dict(cls, instance):
        d = super().instance_as_dict(instance)
        d['group'] = str(instance.entity_type)
        d['help'] = _('Private ({})').format(instance.user) if instance.is_private else ''

        return d

    def choices(self, user, *, term=None, only=None, limit=None):
        # Do not apply limits on queryset, because ordering is done later
        choices = super().choices(user, term=term, only=only)

        sort_key = collator.sort_key
        choices.sort(key=lambda d: sort_key(f"{d.get('group', '')}#{d['label']}"))

        return choices[:limit] if limit else choices


class EntityCTypeForeignKeyEnumerator(enumerable.Enumerator):
    def choices(self, user, *, term=None, only=None, limit=None):
        choices = ctype_choices(entity_ctypes())

        if only:
            choices = [c for c in choices if c[0] in only]
        elif term:
            term = term.lower()
            choices = [c for c in choices if term in c[1].lower()]

        return [
            {'value': ct_id, 'label': label}
            for ct_id, label in (choices[:limit] if limit else choices)
        ]

    def to_python(self, user, values):
        return [c for c in entity_ctypes() if c.id in values]


class VatEnumerator(enumerable.QSEnumerator):
    search_fields = ('value',)


class CustomFieldEnumerator(enumerable.Enumerator):
    """Similar to QSEnumerator but only for CustomField values"""

    search_fields = ('value',)
    limit_choices_to = None

    def __init__(self, custom_field: CustomField):
        super().__init__(None)
        self.custom_field = custom_field

    def search_q(self, term):
        q = Q()

        for name in self.search_fields:
            q |= Q(**{f'{name}__icontains': term})

        return q

    def _queryset(self, user):
        qs = CustomFieldEnumValue.objects.filter(custom_field=self.custom_field)
        qs = qs.complex_filter(self.limit_choices_to) if self.limit_choices_to else qs

        return qs

    def to_python(self, user, values):
        return list(self._queryset(user).filter(pk__in=values))

    def filter_term(self, queryset, term):
        return queryset.filter(self.search_q(term))

    def filter_only(self, queryset, values):
        return queryset.filter(id__in=values)

    @classmethod
    def instance_as_dict(cls, instance):
        return {
            'value': instance.pk,
            'label': str(instance.value),
        }

    def choices(self, user, *, term=None, only=None, limit=None):
        queryset = self._queryset(user)

        if term:
            queryset = self.filter_term(queryset, term)
        elif only:
            queryset = self.filter_only(queryset, only)

        return list(
            map(self.instance_as_dict, queryset[:limit] if limit else queryset)
        )
