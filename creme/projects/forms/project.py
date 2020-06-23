# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.forms import DateTimeField
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeEntityForm, MultiCreatorEntityField
from creme.creme_core.models import Relation
from creme.persons import get_contact_model

from .. import get_project_model
from ..constants import REL_OBJ_PROJECT_MANAGER


class ProjectEditForm(CremeEntityForm):
    # TODO: not required in the model !
    start_date = DateTimeField(label=_('Start date'), required=True)

    end_date = DateTimeField(label=_('End date'), required=True)

    class Meta(CremeEntityForm.Meta):
        model = get_project_model()
        # TODO: field not editable ??
        exclude = (*CremeEntityForm.Meta.exclude, 'effective_end_date')


class ProjectCreateForm(ProjectEditForm):
    responsibles = MultiCreatorEntityField(label=_('Project leaders'), model=get_contact_model())

    def _get_relations_to_create(self):
        instance = self.instance
        build_relation = partial(Relation, user=instance.user,
                                 type_id=REL_OBJ_PROJECT_MANAGER,
                                 subject_entity=instance,
                                )

        return super()._get_relations_to_create().extend(
            build_relation(object_entity=contact)
            for contact in self.cleaned_data['responsibles']
        )
