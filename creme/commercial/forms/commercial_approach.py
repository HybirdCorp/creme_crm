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

from datetime import datetime

from django.forms import IntegerField
from django.forms.widgets import HiddenInput

from creme_core.forms import CremeModelForm

from commercial.models import CommercialApproach


class ComAppCreateForm(CremeModelForm):
    class Meta:
        model = CommercialApproach
        fields = ('title', 'description')

    def __init__(self, entity, *args, **kwargs):
        super(ComAppCreateForm, self).__init__(*args, **kwargs)
        self._entity = entity

    def save(self):
        instance = self.instance
        instance.creation_date = datetime.today()
        instance.creme_entity = self._entity

        return super(ComAppCreateForm, self).save()
