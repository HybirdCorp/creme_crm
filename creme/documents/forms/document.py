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

from logging import debug

from django.db.models.query_utils import Q
from django.forms import CharField

from creme_core.models import Relation
from creme_core.forms import CremeEntityForm
from creme_core.forms.widgets import UploadedFileWidget
from creme_core.views.file_handling import handle_uploaded_file

from documents.models import FolderCategory, Folder, Document
from documents.constants import REL_SUB_RELATED_2_DOC, DOCUMENTS_FROM_ENTITIES


class DocumentCreateForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = Document

    def __init__(self, *args, **kwargs):
        super(DocumentCreateForm,self ).__init__(* args, **kwargs)
        if self.instance.filedata is not None :
            self.fields['filedata'].__dict__['widget'] = UploadedFileWidget(url='%s' % (self.instance.filedata))

    def clean_filedata(self):
#        return str(handle_uploaded_file(self.cleaned_data['filedata'], path='upload/documents'))
        return str(handle_uploaded_file(self.cleaned_data['filedata'], path=['upload','documents']))


class DocumentEditForm(CremeEntityForm):
    filedata = CharField(required=False)

    class Meta(CremeEntityForm.Meta):
        model = Document

    def __init__(self, *args, ** kwargs):
        super(DocumentEditForm,self ).__init__(*args, ** kwargs)
        if self.instance.filedata is not None :
            #TODO: why __dict__['widget'] ??
            self.fields['filedata'].__dict__['widget'] = UploadedFileWidget(url='%s' % (self.instance.filedata))


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

        try:
            creme_folder = Folder.objects.get(title='Creme') #Unique title (created in populate.py)
            creme_folder_category = FolderCategory.objects.get(pk=DOCUMENTS_FROM_ENTITIES)
            model_folder_kwargs = {'title': entity.entity_type, 'parent_folder': creme_folder, 'category': creme_folder_category}

            try:
                model_folder = Folder.objects.get(Q(**model_folder_kwargs))
            except Folder.DoesNotExist, e:
                debug('Folder.DoesNotExist: %s', e)
                model_folder = Folder(**model_folder_kwargs)
                model_folder.user = user
                model_folder.save()

            try:
                entity_folder = Folder.objects.get(title=u'%s_%s' % (entity.id, unicode(entity))) #beurkkk
            except Folder.DoesNotExist, e:
                debug('Folder.DoesNotExist: %s', e)
                entity_folder = Folder(title=u'%s_%s' % (entity.id, unicode(entity)),
                                       parent_folder=model_folder,
                                       category=creme_folder_category,
                                       user=user
                                      )
                entity_folder.save()
        except (Folder.DoesNotExist, FolderCategory.DoesNotExist), e:
            debug("Populate.py had not been run ?! : %s", e)

        self.instance.folder = entity_folder
        super(DocumentCreateViewForm, self).save()

        Relation.objects.create(subject_entity=entity,
                                type_id=REL_SUB_RELATED_2_DOC,
                                object_entity=self.instance,
                                user=user
                               )

        return self.instance
