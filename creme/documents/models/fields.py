# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2018  Hybird
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

from django.conf import settings
from django.db.models import ForeignKey, ManyToManyField

from ..constants import MIMETYPE_PREFIX_IMG


class ImageEntityForeignKey(ForeignKey):
    def __init__(self, **kwargs):
        kwargs['to'] = settings.DOCUMENTS_DOCUMENT_MODEL

        limit_choices_to = kwargs.setdefault('limit_choices_to', {})
        limit_choices_to['mime_type__name__startswith'] = MIMETYPE_PREFIX_IMG

        super(ImageEntityForeignKey, self).__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(ImageEntityForeignKey, self).deconstruct()
        # kwargs.pop('to', None)
        #  + 'limit_choices_to' stuff

        return name, path, args, kwargs

    def formfield(self, **kwargs):
        from ..forms.fields import ImageEntityField

        return ImageEntityField(label=self.verbose_name,
                                required=not self.blank,
                                # q_filter=self.rel.limit_choices_to,
                                q_filter=self.remote_field.limit_choices_to,
                                help_text=self.help_text,
                               )

    def get_internal_type(self):
        return 'ForeignKey'


class ImageEntityManyToManyField(ManyToManyField):
    def __init__(self, **kwargs):
        kwargs['to'] = settings.DOCUMENTS_DOCUMENT_MODEL

        limit_choices_to = kwargs.setdefault('limit_choices_to', {})
        limit_choices_to['mime_type__name__startswith'] = MIMETYPE_PREFIX_IMG

        super(ImageEntityManyToManyField, self).__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(ImageEntityManyToManyField, self).deconstruct()
        # kwargs.pop('to', None)
        #  + 'limit_choices_to' stuff

        return name, path, args, kwargs

    def formfield(self, **kwargs):
        from ..forms.fields import MultiImageEntityField

        return MultiImageEntityField(label=self.verbose_name,
                                     required=not self.blank,
                                     # q_filter=self.rel.limit_choices_to,
                                     q_filter=self.remote_field.limit_choices_to,
                                     help_text=self.help_text,
                                    )

    def get_internal_type(self):
        return 'ManyToManyField'
