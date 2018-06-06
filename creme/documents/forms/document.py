# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import logging
from os.path import basename

from django.core.exceptions import ValidationError
from django.db.transaction import atomic

from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.forms.validators import validate_linkable_model
from creme.creme_core.models import Relation
from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.utils import ellipsis
from creme.creme_core.views.file_handling import handle_uploaded_file

from creme import documents
from .. import constants
from ..models import FolderCategory


logger = logging.getLogger(__name__)
Folder   = documents.get_folder_model()
Document = documents.get_document_model()


class _DocumentBaseForm(CremeEntityForm):  # TODO: rename to_DocumentCreateBaseForm ?
    class Meta(CremeEntityForm.Meta):
        model = Document

    def __init__(self, *args, **kwargs):
        super(_DocumentBaseForm, self).__init__(*args, **kwargs)
        title_f = self.fields['title']
        title_f.required = title_f.widget.is_required = False

    def save(self, *args, **kwargs):
        instance = self.instance

        instance.filedata = fpath = handle_uploaded_file(
                self.cleaned_data['filedata'],
                path=['upload', 'documents'],
                max_length=Document._meta.get_field('filedata').max_length,
            )

        if not instance.title:
            # TODO: truncate but keep extension if possible ?
            assign_2_charfield(instance, 'title', basename(fpath))

        return super(_DocumentBaseForm, self).save(*args, **kwargs)


class DocumentCreateForm(_DocumentBaseForm):
    pass


class DocumentEditForm(CremeEntityForm):
    pass

    class Meta(CremeEntityForm.Meta):
        model = Document
        exclude = CremeEntityForm.Meta.exclude + ('filedata',)


_TITLE_MAX_LEN = Folder._meta.get_field('title').max_length


class RelatedDocumentCreateForm(_DocumentBaseForm):
    class Meta(_DocumentBaseForm.Meta):
        # exclude = _DocumentBaseForm.Meta.exclude + ('folder', )
        exclude = _DocumentBaseForm.Meta.exclude + ('linked_folder', )

    def __init__(self, *args, **kwargs):
        super(RelatedDocumentCreateForm, self).__init__(*args, **kwargs)
        self.related_entity = self.initial['entity']
        self.folder_category = None
        self.root_folder = None

    def clean_user(self):
        return validate_linkable_model(Document, self.user, owner=self.cleaned_data['user'])

    def clean(self):
        cleaned_data = super(RelatedDocumentCreateForm, self).clean()

        if not self._errors:
            self.folder_category = cat = FolderCategory.objects.filter(pk=constants.DOCUMENTS_FROM_ENTITIES).first()
            if cat is None:
                raise ValidationError('Populate script has not been run (unknown folder category pk={}) ; '
                                      'please contact your administrator'.format(constants.DOCUMENTS_FROM_ENTITIES)
                                     )

            self.root_folder = folder = Folder.objects.filter(uuid=constants.UUID_FOLDER_RELATED2ENTITIES).first()
            if folder is None:
                raise ValidationError('Populate script has not been run (unknown folder uuid={}) ; '
                                      'please contact your administrator'.format(constants.UUID_FOLDER_RELATED2ENTITIES)
                                     )

        return cleaned_data

    @atomic
    def save(self, *args, **kwargs):
        instance = self.instance
        entity   = self.related_entity.get_real_entity()
        user     = self.cleaned_data['user']
        category = self.folder_category

        get_or_create_folder = Folder.objects.get_or_create
        model_folder = get_or_create_folder(
                            title=unicode(entity.entity_type),
                            parent_folder=self.root_folder,
                            category=category,
                            defaults={'user': user},
        )[0]
        # instance.folder = get_or_create_folder(
        instance.linked_folder = get_or_create_folder(
                            title=ellipsis(u'{}_{}'.format(entity.id, entity), _TITLE_MAX_LEN),  # Meh
                            parent_folder=model_folder,
                            category=category,
                            defaults={'user': user},
        )[0]

        super(RelatedDocumentCreateForm, self).save(*args, **kwargs)

        Relation.objects.create(subject_entity=entity,
                                type_id=constants.REL_SUB_RELATED_2_DOC,
                                object_entity=instance,
                                user=user,
                               )

        return instance
