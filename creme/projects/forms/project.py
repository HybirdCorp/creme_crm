# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

# import warnings
from functools import partial

from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeEntityForm, MultiCreatorEntityField
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell
from creme.creme_core.models import Relation
from creme.persons import get_contact_model

# from .. import get_project_model
from ..constants import REL_OBJ_PROJECT_MANAGER

# class ProjectEditForm(CremeEntityForm):
#     def __init__(self, *args, **kwargs):
#         warnings.warn('ProjectEditForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#
#     class Meta(CremeEntityForm.Meta):
#         model = get_project_model()


# class ProjectCreateForm(ProjectEditForm):
#     responsibles = MultiCreatorEntityField(label=_('Project leaders'), model=get_contact_model())
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('ProjectCreateForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#
#     def _get_relations_to_create(self):
#         instance = self.instance
#         build_relation = partial(
#             Relation, user=instance.user,
#             type_id=REL_OBJ_PROJECT_MANAGER, subject_entity=instance,
#         )
#
#         return super()._get_relations_to_create().extend(
#             build_relation(object_entity=contact)
#             for contact in self.cleaned_data['responsibles']
#         )


class ProjectLeadersSubCell(CustomFormExtraSubCell):
    sub_type_id = 'projects_leaders'
    verbose_name = _('Project leaders')

    def formfield(self, instance, user, **kwargs):
        return MultiCreatorEntityField(
            label=_('Project leaders'), model=get_contact_model(), user=user,
        )


class BaseProjectCreationCustomForm(CremeEntityForm):
    def _get_relations_to_create(self):
        instance = self.instance
        build_relation = partial(
            Relation,
            user=instance.user, type_id=REL_OBJ_PROJECT_MANAGER, subject_entity=instance,
        )

        return super()._get_relations_to_create().extend(
            build_relation(object_entity=contact)
            for contact in self.cleaned_data[self.subcell_key(ProjectLeadersSubCell)]
        )
