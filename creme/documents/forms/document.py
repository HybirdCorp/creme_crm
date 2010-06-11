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

import logging

#from django.forms import CharField
from django.db.models.query_utils import Q
from django.forms.widgets import HiddenInput
#from django.forms.models import ModelChoiceField
from django.forms import ModelChoiceField, CharField

from creme_core.models import CremeEntity, Relation
from creme_core.forms import CremeModelForm
from creme_core.forms.widgets import UploadedFileWidget
from creme_core.views.file_handling import handle_uploaded_file

from documents.models import FolderCategory, Folder, Document
from documents.constants import REL_SUB_RELATED_2_DOC


#class DocumentListViewForm(CremeModelForm):
    #class Meta:
        #model   = Document
        #exclude = ('filedata', )


class DocumentCreateForm(CremeModelForm):
    class Meta:
        model = Document
        exclude = CremeModelForm.exclude

    def __init__(self, *args, **kwargs):
        super(DocumentCreateForm,self ).__init__(* args, **kwargs)
        if self.instance.filedata is not None :
            self.fields['filedata'].__dict__['widget'] = UploadedFileWidget(url='%s' % (self.instance.filedata))

    def clean_filedata(self):
#        return str(handle_uploaded_file(self.cleaned_data['filedata'], path='upload/documents'))
        return str(handle_uploaded_file(self.cleaned_data['filedata'], path=['upload','documents']))


class DocumentEditForm(CremeModelForm):
    filedata = CharField(required=False)

    class Meta:
        model = Document
        exclude = CremeModelForm.exclude

    def __init__(self, *args, ** kwargs):
        super(DocumentEditForm,self ).__init__(*args, ** kwargs)
        if self.instance.filedata is not None :
            #TODO: why __dict__['widget'] ??
            self.fields['filedata'].__dict__['widget'] = UploadedFileWidget(url='%s' % (self.instance.filedata))


class DocumentCreateViewForm(DocumentCreateForm):
    entity = ModelChoiceField(queryset=CremeEntity.objects.all(), widget=HiddenInput())

    def __init__(self, *args, **kwargs):
        super(DocumentCreateViewForm, self).__init__(*args, **kwargs)
        entity_id = self.initial.get('entity_id')
        logging.debug('entity_id : %s ', entity_id)
        logging.debug('self.initial : %s ', self.initial)

        if entity_id:
            try:
                self.fields['entity'].queryset = CremeEntity.objects.filter(pk=entity_id)
                self.initial['entity'] = entity_id
            except CremeEntity.DoesNotExist, e:
                logging.debug('CremeEntity.DoesNotExist : %s', e)

    def save(self):
        cleaned_data = self.cleaned_data
        entity = cleaned_data['entity']
        user = cleaned_data['user']

        try:
            entity_klass = entity.entity_type.model_class()
            real_entity = entity_klass.objects.get(pk=entity.id)
        except entity_klass.DoesNotExist, e:
            logging.debug('Erreur : %s', e)

        try:
            creme_folder = Folder.objects.get(title='Creme')#Ce titre est unique et dans les initial_datas
            creme_folder_category = FolderCategory.objects.get(name="Documents crées à partir des fiches") #beuarkkkk
            model_folder_kwargs = {'title':real_entity.entity_type, 'parent_folder':creme_folder, 'category':creme_folder_category}

            try:
                model_folder = Folder.objects.get(Q(**model_folder_kwargs))
            except Folder.DoesNotExist, c_exc:
                logging.debug('Folder.DoesNotExist :%s', c_exc)
                model_folder = Folder(**model_folder_kwargs)
                model_folder.user = user
                model_folder.save()

            try:
                entity_folder = Folder.objects.get(title='%s_%s' % (real_entity.id, real_entity.__unicode__()))
            except Folder.DoesNotExist, c_exc:
                entity_folder_kwargs = {'title':'%s_%s' % (real_entity.id,real_entity.__unicode__()),
                          'parent_folder':model_folder, 'category':creme_folder_category,
                          'user' : user}
                entity_folder = Folder(**entity_folder_kwargs)
                entity_folder.save()
                logging.debug('Folder.DoesNotExist :%s', c_exc)
        except (Folder.DoesNotExist, FolderCategory.DoesNotExist), c_exc:
            logging.debug('Les initials datas n ont pas etes executees ? : %s', c_exc)

        self.instance.folder = entity_folder
        super(DocumentCreateViewForm, self).save()
        Relation.create_relation_with_object(real_entity, REL_SUB_RELATED_2_DOC, self.instance)

    class Meta:
        model   = Document
        exclude = CremeModelForm.exclude + ('folder', )
