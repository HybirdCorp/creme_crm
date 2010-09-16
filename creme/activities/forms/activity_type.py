# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from creme_core.forms import CremeModelForm
from creme_core.utils.id_generator import generate_string_id_and_save

from activities.models import ActivityType


class ActivityTypeForm(CremeModelForm):
    class Meta:
        model = ActivityType
        exclude = ('id', 'is_custom')

    def save(self):
        instance = self.instance

        if not instance.id:
            super(ActivityTypeForm, self).save(commit=False)
            generate_string_id_and_save(ActivityType, [instance], 'creme_config-useractivitytype')
        else:
            super(ActivityTypeForm, self).save()

        return instance
