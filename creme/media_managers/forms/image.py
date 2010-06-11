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

from creme_core.forms import CremeModelForm
from creme_core.forms.widgets import UploadedFileWidget
from creme_core.views.file_handling import handle_uploaded_file

from media_managers.models import Image


__all__ = (
    'ImageForm', #'ImageListViewForm', 
)

#class ImageListViewForm(CremeModelForm):
    #class Meta:
        #model   = Image
        #exclude = CremeModelForm.exclude + ('image',)


class ImageForm(CremeModelForm):
    class Meta:
        model = Image
        exclude = CremeModelForm.exclude + ('height', 'width')

    def __init__(self, *args, **kwargs):
        super (ImageForm,self ).__init__(*args, **kwargs)
        if self.instance.image is not None :
            self.fields['image'].__dict__['widget'] = UploadedFileWidget(url='%s' % (self.instance.image)) #TODO: why not str(self.instance.image) ??

    def clean_image(self):
#        return str(handle_uploaded_file(self.cleaned_data['image'], path='upload/images'))
        return str(handle_uploaded_file(self.cleaned_data['image'], path=['upload','images']))
