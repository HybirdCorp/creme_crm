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

# import logging
# import warnings
# from functools import partial

# from django.core.exceptions import ValidationError
# from django.db.transaction import atomic

# from creme import documents
from creme.creme_core.forms import CremeEntityForm
# from creme.creme_core.forms.validators import validate_linkable_model
# from creme.creme_core.models import Relation
# from creme.creme_core.utils import ellipsis
from creme.creme_core.views.file_handling import handle_uploaded_file

# from .. import constants
# from ..models import FolderCategory

# DEPRECATED
# logger = logging.getLogger(__name__)
# Folder   = documents.get_folder_model()
# Document = documents.get_document_model()


# class _DocumentBaseForm(CremeEntityForm):
#     class Meta(CremeEntityForm.Meta):
#         model = Document
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('_DocumentBaseForm is deprecated.', DeprecationWarning)
#
#         super().__init__(*args, **kwargs)
#         title_f = self.fields['title']
#         title_f.required = title_f.widget.is_required = False
#
#     def save(self, *args, **kwargs):
#         instance = self.instance
#
#         file_data = self.cleaned_data['filedata']
#         if file_data:
#             instance.filedata = handle_uploaded_file(
#                 file_data,
#                 path=['upload', 'documents'],
#                 max_length=Document._meta.get_field('filedata').max_length,
#             )
#
#         return super().save(*args, **kwargs)


# class DocumentCreateForm(_DocumentBaseForm):
#     def __init__(self, *args, **kwargs):
#         warnings.warn('DocumentCreateForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


# class DocumentEditForm(CremeEntityForm):
#     def __init__(self, *args, **kwargs):
#         warnings.warn('DocumentEditForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#
#     class Meta(CremeEntityForm.Meta):
#         model = Document
#         exclude = (*CremeEntityForm.Meta.exclude, 'filedata')


# # DEPRECATED
# _TITLE_MAX_LEN = Folder._meta.get_field('title').max_length


# class RelatedDocumentCreateForm(_DocumentBaseForm):
#     class Meta(_DocumentBaseForm.Meta):
#         exclude = (*_DocumentBaseForm.Meta.exclude, 'linked_folder')
#
#     def __init__(self, entity, *args, **kwargs):
#         warnings.warn('RelatedDocumentCreateForm is deprecated.', DeprecationWarning)
#
#         super().__init__(*args, **kwargs)
#         self.related_entity = entity
#         self.folder_category = None
#         self.root_folder = None
#
#     def clean_user(self):
#         return validate_linkable_model(Document, self.user, owner=self.cleaned_data['user'])
#
#     def clean(self):
#         cleaned_data = super().clean()
#
#         if not self._errors:
#             self.folder_category = cat = FolderCategory.objects.filter(
#                 pk=constants.DOCUMENTS_FROM_ENTITIES,
#             ).first()
#             if cat is None:
#                 raise ValidationError(
#                     f'Populate script has not been run '
#                     f'(unknown folder category pk={constants.DOCUMENTS_FROM_ENTITIES}) ; '
#                     f'please contact your administrator'
#                 )
#
#             self.root_folder = folder = Folder.objects.filter(
#                 uuid=constants.UUID_FOLDER_RELATED2ENTITIES,
#             ).first()
#             if folder is None:
#                 raise ValidationError(
#                     f'Populate script has not been run '
#                     f'(unknown folder uuid={constants.UUID_FOLDER_RELATED2ENTITIES}) ; '
#                     f'please contact your administrator'
#                 )
#
#         return cleaned_data
#
#     def _get_relations_to_create(self):
#         instance = self.instance
#
#         return super()._get_relations_to_create().append(
#             Relation(
#                 subject_entity=self.related_entity.get_real_entity(),
#                 type_id=constants.REL_SUB_RELATED_2_DOC,
#                 object_entity=instance,
#                 user=instance.user,
#             ),
#         )
#
#     def _get_folder(self):
#         entity = self.related_entity.get_real_entity()
#         get_or_create_folder = partial(
#             Folder.objects.get_or_create,
#             category=self.folder_category,
#             defaults={'user': self.cleaned_data['user']},
#         )
#         model_folder = get_or_create_folder(
#             title=str(entity.entity_type),
#             parent_folder=self.root_folder,
#         )[0]
#
#         return get_or_create_folder(
#             title=ellipsis(f'{entity.id}_{entity}', _TITLE_MAX_LEN),  # Meh
#             parent_folder=model_folder,
#         )[0]
#
#     @atomic
#     def save(self, *args, **kwargs):
#         self.instance.linked_folder = self._get_folder()
#
#         return super().save(*args, **kwargs)


class BaseDocumentCustomForm(CremeEntityForm):
    def save(self, *args, **kwargs):
        instance = self.instance
        file_data = self.cleaned_data.get('filedata')

        if file_data:
            file_field = type(instance)._meta.get_field('filedata')
            instance.filedata = handle_uploaded_file(
                file_data,
                path=file_field.upload_to.split('/'),
                max_length=file_field.max_length,
            )

        return super().save(*args, **kwargs)
