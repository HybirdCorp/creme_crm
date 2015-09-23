# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.forms.utils import ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.forms.bulk import BulkDefaultEditForm
from creme.creme_core.forms.fields import CreatorEntityField

from .. import get_folder_model
#from ..models import Folder


Folder = get_folder_model()


class _FolderForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = Folder
        help_texts = {
            'category': _(u"The parent's category will be copied if you do not select one."),
        }

    def save(self, *args, **kwargs):
        instance = self.instance
        if not instance.category and instance.parent_folder:
            instance.category = instance.parent_folder.category

        return super(_FolderForm, self).save(*args, **kwargs)


class FolderForm(_FolderForm):
    parent_folder = CreatorEntityField(label=_(u'Parent folder'), model=Folder, required=False)

    error_messages = {
        'loop': _(u'This folder is one of the child folders of «%(folder)s»'),
    }

    def __init__(self, *args, **kwargs):
        super(FolderForm, self).__init__(*args, **kwargs)
        pk = self.instance.id
        if pk:
            # TODO: remove direct children too ??
            self.fields['parent_folder'].q_filter = {'~id__in': [pk]}

#    def clean_category(self):
#        cleaned_data = self.cleaned_data
#        #parent_folder_data = cleaned_data['parent_folder']
#        parent_folder_data = cleaned_data.get('parent_folder')
#        category_data      = cleaned_data['category']
#
#        if parent_folder_data is not None and parent_folder_data.category != category_data:
#            raise ValidationError(ugettext(u"Folder's category must be the same than its parent's one: %s") %
#                                    parent_folder_data.category
#                                 )
#
#        return category_data

    def clean_parent_folder(self):
        parent_folder = self.cleaned_data['parent_folder']
        folder = self.instance

        if folder.pk and parent_folder and folder.already_in_children(parent_folder.id):
            raise ValidationError(self.error_messages['loop'],
                                  params={ 'folder': folder}, code='loop',
                                 )

        return parent_folder


class ChildFolderForm(_FolderForm):
    class Meta(_FolderForm.Meta):
        exclude = ('parent_folder',)

    def __init__(self, *args, **kwargs):
        super(ChildFolderForm, self).__init__(*args, **kwargs)
        self.instance.parent_folder = self.initial.get('parent')


class ParentFolderBulkForm(BulkDefaultEditForm):
    def __init__(self, field, user, entities, is_bulk=False, **kwargs):
        super(ParentFolderBulkForm, self).__init__(field, user, entities, is_bulk=is_bulk, **kwargs)

        if len(entities) == 1:
            # TODO: like above -> remove direct children too ??
            self.fields['field_value'].q_filter = {'~id__in': [entities[0].pk]}

    def _bulk_clean_entity(self, entity, values):
        parent_folder = values.get('parent_folder')

        if parent_folder:
            if parent_folder == entity:
                # TODO: self.error_messages ?
                raise ValidationError(ugettext(u'«%(folder)s» cannot be its own parent') % {
                                            'folder': entity,
                                        },
                                      code='itself',
                                     )

            if entity.already_in_children(parent_folder.id):
                raise ValidationError(ugettext(u'This folder is one of the child folders of «%(folder)s»') % {
                                            'folder': entity,
                                        },
                                      code='loop',
                                     )

            if not entity.category:
                entity.category = parent_folder.category

        return super(ParentFolderBulkForm, self)._bulk_clean_entity(entity, values)


def get_merge_form_builder():
    from creme.creme_core.forms.merge import MergeEntitiesBaseForm

    class FolderMergeForm(MergeEntitiesBaseForm):
        # TODO: uncomment & remove the code in init which eclude the field ? (MergeEntitiesBaseForm has to be a ModelForm...)
        #class Meta(MergeEntitiesBaseForm.Meta):
            #exclude = ('parent_folder',)

        def __init__(self, entity1, entity2, *args, **kwargs):
            if entity2.already_in_children(entity1.id):
                entity1, entity2 = entity2, entity1

            super(FolderMergeForm, self).__init__(entity1, entity2, *args, **kwargs)

            del self.fields['parent_folder']


    return FolderMergeForm
