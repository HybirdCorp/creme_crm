################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2025  Hybird
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

from creme.creme_core.core.enumerable import QSEnumerator
from creme.creme_core.enumerators import UserEnumerator
from creme.creme_core.utils.unicode_collation import collator


class ActivitySubTypeEnumerator(QSEnumerator):
    search_fields = ('name', 'type__name')

    @classmethod
    def instance_as_dict(cls, instance):
        return {
            'value': instance.pk,
            'label': str(instance),
            'group': str(instance.type),
        }

    def choices(self, user, *, term=None, only=None, limit=None):
        # Do not apply limits on queryset, because ordering is done later
        choices = super().choices(user, term=term, only=only)

        sort_key = collator.sort_key
        choices.sort(key=lambda d: sort_key(f"{d.get('group', '')}#{d['label']}"))

        return choices[:limit] if limit else choices


class CalendarOwnerEnumerator(UserEnumerator):
    def _queryset(self, user):
        return super()._queryset(
            user=user,
        ).exclude(
            # NB: this enumerator is used for calendar creation only (the owner
            #     cannot be changed), so we can safely exclude inactive users.
            is_active=False,
        ).exclude(is_team=True, calendar__isnull=False)
