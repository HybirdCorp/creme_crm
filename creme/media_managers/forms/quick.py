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
import shutil

from os.path import join, split

from creme.creme_core.forms import CremeModelWithUserForm
from creme.creme_core.views.file_handling import handle_uploaded_file

from ..models import Image

logger = logging.getLogger(__name__)


class ImageQuickForm(CremeModelWithUserForm):
    class Meta:
        model = Image
        exclude = ('description', 'height', 'width', 'categories')

    def __init__(self, categories=None, user=None, *args, **kwargs):
        super(ImageQuickForm, self).__init__(user=user, *args, **kwargs)
        self.categories = categories

    def clean_image(self):
        return str(handle_uploaded_file(self.cleaned_data['image'], path=['upload', 'images']))

    def save(self, *args, **kwargs):
        instance = super(ImageQuickForm, self).save(*args, **kwargs)

        if self.categories is not None:
            instance.categories = self.categories

        upload_path = str(instance.image.file)
        upload_dirname, upload_filename = split(upload_path)

        image_filename = "%s_%s" % (instance.id, upload_filename)
        image_path = join(upload_dirname, image_filename)

        try:
            shutil.move(upload_path, image_path)
        except IOError, e:
            logger.debug('IOError in %s: %s', self.__class__, e)
        else:
            instance.image = join('upload', 'images', image_filename) #Not dst_path! chrooted?
            instance.save()

        return instance
