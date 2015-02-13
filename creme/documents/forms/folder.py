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

from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.forms.fields import CreatorEntityField

from ..models import Folder


class FolderForm(CremeEntityForm):
    parent_folder = CreatorEntityField(label=_(u'Parent folder'), model=Folder, required=False)

    class Meta(CremeEntityForm.Meta):
        model = Folder

    def __init__(self, *args, **kwargs):
        super(FolderForm, self).__init__(*args, **kwargs)
        fields = self.fields
        pk = self.instance.id
        if pk:
            # TODO: remove direct children too ??
            fields['parent_folder'].q_filter = {'~id__in': [pk]}

        #TODO: django 1.6: use Meta.help_texts
        fields['category'].help_text = _(u"The parent's category will be copied if you do not select one.")

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
            raise ValidationError(ugettext(u'This folder is one of the child folders of «%(folder)s»') % {
                                    'folder': folder,
                                  }
                                 )

        return parent_folder

    def save(self, *args, **kwargs):
        instance = self.instance
        if not instance.category and instance.parent_folder:
            instance.category = instance.parent_folder.category
        
        return super(FolderForm, self).save(*args, **kwargs)
