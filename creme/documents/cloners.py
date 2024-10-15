################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from random import randint

from django.utils.translation import gettext as _

from creme.creme_core.core.cloning import EntityCloner
from creme.creme_core.core.copying import PreSaveCopier
from creme.creme_core.utils import truncate_str


class TitleCopier(PreSaveCopier):
    MAXINT = 100000

    def copy_to(self, target):
        model = type(target)
        max_length = model._meta.get_field('title').max_length
        base_title = self._source.title

        for _i in range(1000):
            title = truncate_str(
                str=base_title, max_length=max_length,
                suffix=' ({} {:08x})'.format(_('Copy'), randint(0, self.MAXINT)),
            )
            if not model.objects.filter(title=title).exists():
                target.title = title
                break


class FolderCloner(EntityCloner):
    pre_save_copiers = [
        *EntityCloner.pre_save_copiers,
        TitleCopier,
    ]
