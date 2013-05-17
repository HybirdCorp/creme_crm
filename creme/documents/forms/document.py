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

import logging

from django.forms import CharField

from creme.creme_core.models import Relation
from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.forms.widgets import UploadedFileWidget
from creme.creme_core.views.file_handling import handle_uploaded_file
from creme.creme_core.utils import ellipsis

from ..models import FolderCategory, Folder, Document
from ..constants import REL_SUB_RELATED_2_DOC, DOCUMENTS_FROM_ENTITIES


logger = logging.getLogger(__name__)


class DocumentCreateForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = Document

    def clean_filedata(self):
        return str(handle_uploaded_file(self.cleaned_data['filedata'], path=['upload', 'documents']))


class DocumentEditForm(CremeEntityForm):
    filedata = CharField(required=False, widget=UploadedFileWidget) #TODO: useful to see the file (can not change it) ???

    class Meta(CremeEntityForm.Meta):
        model = Document


_TITLE_MAX_LEN = Folder._meta.get_field('title').max_length


#TODO : rename it in RelatedDocumentCreateForm
class DocumentCreateViewForm(DocumentCreateForm):
    class Meta(CremeEntityForm.Meta):
        model   = Document
        exclude = CremeEntityForm.Meta.exclude + ('folder', )

    def __init__(self, *args, **kwargs):
        super(DocumentCreateViewForm, self).__init__(*args, **kwargs)
        self.related_entity = self.initial['entity']

    def save(self):
        entity = self.related_entity.get_real_entity()
        user   = self.cleaned_data['user']
        entity_folder = None

        #TODO: reduce code depth
        try:
            creme_folder = Folder.objects.get(title='Creme') #Unique title (created in populate.py)
            category = FolderCategory.objects.get(pk=DOCUMENTS_FROM_ENTITIES)
            get_folder = Folder.objects.get_or_create
            model_folder = get_folder(title=unicode(entity.entity_type),
                                      parent_folder=creme_folder,
                                      category=category,
                                      defaults={'user': user},
                                     ) [0]
            entity_folder = get_folder(title=ellipsis(u'%s_%s' % (entity.id, unicode(entity)),
                                                      _TITLE_MAX_LEN,
                                                     ), #beurkkk
                                       defaults={'parent_folder': model_folder,
                                                 'category':      category,
                                                 'user':          user,
                                                },
                                      ) [0]
        except (Folder.DoesNotExist, FolderCategory.DoesNotExist) as e:
            logger.debug("Populate.py had not been run ?! : %s", e)
            #TODO: continue !?

        self.instance.folder = entity_folder
        super(DocumentCreateViewForm, self).save()

        Relation.objects.create(subject_entity=entity,
                                type_id=REL_SUB_RELATED_2_DOC,
                                object_entity=self.instance,
                                user=user
                               )

        return self.instance
