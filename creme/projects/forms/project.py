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

from django.forms.widgets import HiddenInput
from django.forms import DateTimeField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, Relation
from creme_core.forms import CremeEntityForm, MultiCremeEntityField
from creme_core.forms.widgets import DateTimeWidget

from persons.models import Contact

from projects.models import Project
from projects.constants import REL_OBJ_PROJECT_MANAGER


class ProjectEditForm(CremeEntityForm):
    start_date          = DateTimeField(label=_(u'Start date'), required=True, widget=DateTimeWidget())
    end_date            = DateTimeField(label=_(u'End date'), required=True, widget=DateTimeWidget())
    effective_end_date  = DateTimeField(widget=HiddenInput(), required=False)

    class Meta(CremeEntityForm.Meta):
        model = Project


class ProjectCreateForm(ProjectEditForm):
    responsibles = MultiCremeEntityField(label=_(u'Project leaders'),
                                        required=True, model=Contact)

    def save(self):
        cleaned_data = self.cleaned_data
        instance = super(ProjectCreateForm, self).save()
        create_relation = Relation.objects.create
        user = cleaned_data['user']

        for contact in self.cleaned_data['responsibles']:
            create_relation(subject_entity=instance,
                            type_id=REL_OBJ_PROJECT_MANAGER,
                            object_entity=contact,
                            user=user
                           )

        return instance
