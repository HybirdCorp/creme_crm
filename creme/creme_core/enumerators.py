# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018  Hybird
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

from django.utils.translation import ugettext as _

from creme.creme_core.core import enumerable
from creme.creme_core.utils import build_ct_choices, creme_entity_content_types
from creme.creme_core.utils.unicode_collation import collator


class EntityFilterEnumerator(enumerable.QSEnumerator):
    @classmethod
    def efilter_as_dict(cls, efilter):
        d = cls.instance_as_dict(efilter)
        d['group'] = str(efilter.entity_type)
        d['help'] = _('Private ({})').format(efilter.user) if efilter.is_private else ''

        return d

    def choices(self, user):
        choices = list(map(self.efilter_as_dict, self._queryset()))

        sort_key = collator.sort_key
        choices.sort(key=lambda d: sort_key('{}#{}'.format(d['group'], d['label'])))

        return choices


class EntityCTypeForeignKeyEnumerator(enumerable.Enumerator):
    def choices(self, user):
        return [{'value': ct_id, 'label': label} for ct_id, label in
                    build_ct_choices(creme_entity_content_types())
               ]
