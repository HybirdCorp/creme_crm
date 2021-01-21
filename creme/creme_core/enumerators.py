# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2021  Hybird
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

from django.utils.translation import gettext as _

from creme.creme_core.core import enumerable
from creme.creme_core.utils.content_type import ctype_choices, entity_ctypes
from creme.creme_core.utils.unicode_collation import collator


class UserEnumerator(enumerable.QSEnumerator):
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

    def choices(self, user):
        choices = super().choices(user)

        sort_key = collator.sort_key
        choices.sort(key=lambda d: sort_key('{}#{}'.format(d.get('group', ''), d['label'])))

        return choices


class EntityFilterEnumerator(enumerable.QSEnumerator):
    @classmethod
    def instance_as_dict(cls, instance):
        d = super().instance_as_dict(instance)
        d['group'] = str(instance.entity_type)
        d['help'] = _('Private ({})').format(instance.user) if instance.is_private else ''

        return d

    def choices(self, user):
        choices = super().choices(user)

        sort_key = collator.sort_key
        choices.sort(key=lambda d: sort_key('{}#{}'.format(d['group'], d['label'])))

        return choices


class EntityCTypeForeignKeyEnumerator(enumerable.Enumerator):
    def choices(self, user):
        return [
            {'value': ct_id, 'label': label}
            for ct_id, label in ctype_choices(entity_ctypes())
        ]
