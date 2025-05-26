################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2025  Hybird
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
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from .fields import CremeUserForeignKey


class FileRef(models.Model):  # NB: not a CremeModel, because it's used by CremeModel.delete()
    filedata = models.FileField(verbose_name=_('Path'), max_length=500)

    # True/user-friendly name of the file
    # (in 'filedata' there is the path uniqueness constraint).
    basename = models.CharField(max_length=200)

    created = models.DateTimeField(
        verbose_name=pgettext_lazy('creme_core-temporary_file', 'Created'), auto_now_add=True,
    )
    user = CremeUserForeignKey(verbose_name=_('Owner user'), null=True, on_delete=models.SET_NULL)
    temporary = models.BooleanField(verbose_name=_('To be deleted by the job?'), default=True)

    description = models.TextField(verbose_name=_('Description'))

    # Can be used by third party code to store the data they want,
    # without having to modify the code.
    extra_data = models.JSONField(editable=False, default=dict)

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

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if update_fields is not None:
            raise ValueError('Argument "update_fields" not managed.')

        if not self.basename:
            self.basename = basename(self.filedata.path)

        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
