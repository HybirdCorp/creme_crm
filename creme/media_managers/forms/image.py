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
from os.path import basename  # join, split
# import shutil

from creme.creme_core.forms import CremeEntityForm
# from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.views.file_handling import handle_uploaded_file

from ..models import Image


logger = logging.getLogger(__name__)


class _ImageForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = Image
        # widgets = {
        #     'categories': UnorderedMultipleChoiceWidget,
        # }


class ImageCreateForm(_ImageForm):
    # def clean_image(self):
    #     return str(handle_uploaded_file(self.cleaned_data['image'], path=['upload', 'images']))

    # def save(self, *args, **kwargs):
    #     instance = super(ImageCreateForm, self).save(*args, **kwargs)
    #
    #     src_path = str(instance.image.file)
    #     path, filename = split(src_path)
    #
    #     dst_filename = "%s_%s" % (instance.id, filename)
    #     dst_path = join(path, dst_filename)
    #
    #     try:
    #         shutil.move(src_path, dst_path)
    #     except IOError, e:
    #         logger.debug('IOError in %s: %s', self.__class__, e)
    #     else:
    #         instance.image = join('upload', 'images', dst_filename)#Not dst_path! chrooted?
    #         instance.save()
    #
    #     return instance
    def save(self, *args, **kwargs):
        instance = self.instance
        instance.image = fpath = handle_uploaded_file(
                self.cleaned_data['image'],
                path=['upload', 'images'],
                max_length=Image._meta.get_field('image').max_length,
            )

        if not instance.name:
            assign_2_charfield(instance, 'name', basename(fpath))

        return super(ImageCreateForm, self).save(*args, **kwargs)


class ImageEditForm(_ImageForm):
    class Meta(_ImageForm.Meta):
        exclude = _ImageForm.Meta.exclude + ('image',)
