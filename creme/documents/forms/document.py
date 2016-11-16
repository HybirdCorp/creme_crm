# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

# from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import Relation
from creme.creme_core.forms import CremeEntityForm
# from creme.creme_core.forms.fields import CreatorEntityField
from creme.creme_core.forms.validators import validate_linkable_model
from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.views.file_handling import handle_uploaded_file
from creme.creme_core.utils import ellipsis


from .. import get_folder_model, get_document_model
from ..constants import REL_SUB_RELATED_2_DOC, DOCUMENTS_FROM_ENTITIES
from ..models import FolderCategory


logger = logging.getLogger(__name__)
Folder   = get_folder_model()
Document = get_document_model()


class _DocumentBaseForm(CremeEntityForm):  # TODO: rename to_DocumentCreateBaseForm ?
    class Meta(CremeEntityForm.Meta):
        model = Document

    # def clean_filedata(self):
    #     return str(handle_uploaded_file(self.cleaned_data['filedata'],
    #                                     path=['upload', 'documents'],
    #                                    )
    #               )
    def __init__(self, *args, **kwargs):
        super(_DocumentBaseForm, self).__init__(*args, **kwargs)
        self.fields['title'].required = False

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
    # folder = CreatorEntityField(label=_(u'Folder'), model=Folder)
    pass


class DocumentEditForm(CremeEntityForm):
    # folder = CreatorEntityField(label=_(u'Folder'), model=Folder)
    pass

    class Meta(CremeEntityForm.Meta):
        model = Document
        exclude = CremeEntityForm.Meta.exclude + ('filedata',)


_TITLE_MAX_LEN = Folder._meta.get_field('title').max_length


class RelatedDocumentCreateForm(_DocumentBaseForm):
    class Meta(_DocumentBaseForm.Meta):
        exclude = _DocumentBaseForm.Meta.exclude + ('folder', )

    def __init__(self, *args, **kwargs):
        super(RelatedDocumentCreateForm, self).__init__(*args, **kwargs)
        self.related_entity = self.initial['entity']

    def clean_user(self):
        return validate_linkable_model(Document, self.user, owner=self.cleaned_data['user'])

    def save(self):
        instance = self.instance
        entity = self.related_entity.get_real_entity()
        user   = self.cleaned_data['user']
        entity_folder = None

        # TODO: reduce code depth
        try:
            creme_folder = Folder.objects.get(title='Creme')  # Unique title (created in populate.py)
            category = FolderCategory.objects.get(pk=DOCUMENTS_FROM_ENTITIES)
            get_folder = Folder.objects.get_or_create
            model_folder = get_folder(title=unicode(entity.entity_type),
                                      parent_folder=creme_folder,
                                      category=category,
                                      defaults={'user': user},
                                     )[0]
            entity_folder = get_folder(title=ellipsis(u'%s_%s' % (entity.id, unicode(entity)),
                                                      _TITLE_MAX_LEN,
                                                     ),  # meh
                                       parent_folder=model_folder,
                                       category=category,
                                       defaults={'user': user},
                                      )[0]
        except (Folder.DoesNotExist, FolderCategory.DoesNotExist) as e:
            logger.warn("Populate.py had not been run ?! : %s", e)
        else:
            instance.folder = entity_folder

        super(RelatedDocumentCreateForm, self).save()

        Relation.objects.create(subject_entity=entity,
                                type_id=REL_SUB_RELATED_2_DOC,
                                object_entity=instance,
                                user=user,
                               )

        return instance
