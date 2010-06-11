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

from creme_core.models import CremeEntity
from creme_core.forms import CremeModelForm

from commercial.models import CommercialApproach


class ComAppCreateForm(CremeModelForm):
    entity_id = IntegerField(widget=HiddenInput())

    class Meta:
        model = CommercialApproach
        exclude = ['related_activity_id', 'ok_or_in_futur', 'is_validated', 'creation_date', 'entity_content_type', 'activity_related']

    def save(self):
        self.instance.creation_date = datetime.today()
        entity = CremeEntity.objects.get(pk=self.cleaned_data['entity_id'])
        self.instance.entity_content_type = entity.entity_type
        super(ComAppCreateForm, self).save()
