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
import os
import shutil

from creme_core.forms import CremeEntityForm
from creme_core.forms.widgets import UploadedFileWidget
from creme_core.views.file_handling import handle_uploaded_file

from media_managers.models import Image

class ImageForm(CremeEntityForm):
    class Meta:
        model = Image
        exclude = CremeEntityForm.Meta.exclude + ('height', 'width')

    def __init__(self, *args, **kwargs):
        super (ImageForm,self ).__init__(*args, **kwargs)
        if self.instance.image is not None:
            self.fields['image'].__dict__['widget'] = UploadedFileWidget(url='%s' % (self.instance.image)) #TODO: why not str(self.instance.image) ??

    def clean_image(self):
        return str(handle_uploaded_file(self.cleaned_data['image'], path=['upload', 'images']))

    def save(self, *args, **kwargs):
        super(ImageForm, self).save(*args, **kwargs)
        instance = self.instance

        src_path = str(instance.image.file)
        path, s, filename = src_path.rpartition(os.sep)

        dst_filename = "%s_%s" % (instance.id, filename)
        dst_path = os.path.join(path, dst_filename)

        try:
            shutil.move(src_path, dst_path)
            instance.image = os.path.join('upload', 'images', dst_filename)#Not dst_path! chrooted?
            instance.save()
        except IOError:
            pass




