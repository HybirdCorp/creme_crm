# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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
from django.db.models.query_utils import Q

# from .. import get_folder_model
from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.forms.bulk import BulkDefaultEditForm

# Folder = get_folder_model()


# class _FolderForm(CremeEntityForm):
#     class Meta(CremeEntityForm.Meta):
#         model = Folder
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('_FolderForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


# class FolderForm(_FolderForm):
#     def __init__(self, *args, **kwargs):
#         warnings.warn('FolderForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#         pk = self.instance.id
#         if pk:
#             self.fields['parent_folder'].q_filter = ~Q(id=pk)


# class ChildFolderForm(_FolderForm):
#     class Meta(_FolderForm.Meta):
#         exclude = ('parent_folder',)
#
#     def __init__(self, entity, *args, **kwargs):
#         warnings.warn('ChildFolderForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#         self.instance.parent_folder = entity


class BaseFolderCustomForm(CremeEntityForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pk = self.instance.id
        if pk:
            # TODO: remove direct children too ??
            # TODO: would be cool to get 'instance' in limit_choices_to...
            self.fields['parent_folder'].q_filter = ~Q(id=pk)


class ParentFolderBulkForm(BulkDefaultEditForm):
    def __init__(self, model, field, user, entities, is_bulk=False, **kwargs):
        super().__init__(model, field, user, entities, is_bulk=is_bulk, **kwargs)

        if len(entities) == 1:
            # TODO: like above -> remove direct children too ??
            self.fields['field_value'].q_filter = ~Q(id__in=[entities[0].id])


def get_merge_form_builder():
    from creme.creme_core.forms.merge import MergeEntitiesBaseForm

    class FolderMergeForm(MergeEntitiesBaseForm):
        # TODO: uncomment & remove the code in init which exclude the field ?
        #      (MergeEntitiesBaseForm has to be a ModelForm...)
        # class Meta(MergeEntitiesBaseForm.Meta):
        #     exclude = ('parent_folder',)

        def __init__(self, entity1, entity2, *args, **kwargs):
            if entity2.already_in_children(entity1.id):
                entity1, entity2 = entity2, entity1

            super().__init__(entity1, entity2, *args, **kwargs)

            del self.fields['parent_folder']

    return FolderMergeForm
