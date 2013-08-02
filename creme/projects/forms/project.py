# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from functools import partial

from django.forms.widgets import HiddenInput
from django.forms import DateTimeField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import Relation
from creme.creme_core.forms import CremeEntityForm, MultiCreatorEntityField
from creme.creme_core.forms.widgets import DateTimeWidget
from creme.creme_core.forms.validators import validate_linkable_entities

from creme.persons.models import Contact

from ..models import Project
from ..constants import REL_OBJ_PROJECT_MANAGER


class ProjectEditForm(CremeEntityForm):
    start_date         = DateTimeField(label=_(u'Start date'), required=True, widget=DateTimeWidget()) #TODO: not required in the model !
    end_date           = DateTimeField(label=_(u'End date'), required=True, widget=DateTimeWidget())
    effective_end_date = DateTimeField(widget=HiddenInput(), required=False)

    class Meta(CremeEntityForm.Meta):
        model = Project


class ProjectCreateForm(ProjectEditForm):
    responsibles = MultiCreatorEntityField(label=_(u'Project leaders'), required=True, model=Contact)

    def clean_responsibles(self):
        return validate_linkable_entities(self.cleaned_data['responsibles'], self.user)

    def save(self):
        instance = super(ProjectCreateForm, self).save()
        cleaned_data = self.cleaned_data
        create_relation = partial(Relation.objects.create, user=cleaned_data['user'],
                                  type_id=REL_OBJ_PROJECT_MANAGER, subject_entity=instance
                                 )

        for contact in cleaned_data['responsibles']:
            create_relation(object_entity=contact)

        return instance
