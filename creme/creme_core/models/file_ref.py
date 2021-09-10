# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2021  Hybird
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

from os.path import basename

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse

from .fields import CremeUserForeignKey


class FileRef(models.Model):  # NB: not a CremeModel, because it's used by CremeModel.delete()
    filedata = models.FileField(max_length=200)

    # True/user-friendly name of the file
    # (in 'filedata' there is the path uniqueness constraint).
    basename = models.CharField(max_length=200)

    created = models.DateTimeField(auto_now_add=True)
    user = CremeUserForeignKey(verbose_name='Owner user', null=True, on_delete=models.SET_NULL)
    temporary = models.BooleanField(verbose_name='Is temporary?', default=True)

    class Meta:
        app_label = 'creme_core'

    def get_download_absolute_url(self) -> str:
        return reverse(
            'creme_core__download',
            args=(
                ContentType.objects.get_for_model(self.__class__).id,
                self.id,
                'filedata',
            ),
        )

    def save(self, *args, **kwargs):
        if not self.basename:
            self.basename = basename(self.filedata.path)

        super().save(*args, **kwargs)
