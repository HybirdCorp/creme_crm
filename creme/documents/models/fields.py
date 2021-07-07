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

from copy import copy

from django.conf import settings
from django.db import models
from django.db.models import Q

from ..constants import MIMETYPE_PREFIX_IMG


def _build_limit_choices_to(extra_limit_choices_to):
    kwargs = {'mime_type__name__startswith': MIMETYPE_PREFIX_IMG}
    limit_choices_to = Q(**kwargs)

    if extra_limit_choices_to is not None:
        if callable(extra_limit_choices_to):
            raise NotImplementedError(
                'documents.models.fields: callable "limit_choices_to" is not managed yet.'
            )

        if isinstance(extra_limit_choices_to, dict):
            # XXX: transform to Q VS let a dictionary like the user wanted
            limit_choices_to = {**extra_limit_choices_to, **kwargs}
        else:
            assert isinstance(extra_limit_choices_to, Q)

            limit_choices_to &= extra_limit_choices_to

    return limit_choices_to


def _deconstruct_limit_choices_to(limit_choices_to):
    deconstructed = copy(limit_choices_to)

    if isinstance(limit_choices_to, dict):
        deconstructed.pop('mime_type__name__startswith')
    else:
        assert isinstance(deconstructed, Q)

        children = deconstructed.children

        while children and children[0] == ('mime_type__name__startswith', 'image/'):
            del children[0]

    return deconstructed or None


class ImageEntityForeignKey(models.ForeignKey):
    def __init__(self, **kwargs):
        kwargs['to'] = settings.DOCUMENTS_DOCUMENT_MODEL
        kwargs['limit_choices_to'] = _build_limit_choices_to(kwargs.get('limit_choices_to'))

        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

        limit_choices_to = kwargs.get('limit_choices_to')
        if limit_choices_to is not None:
            kwargs['limit_choices_to'] = _deconstruct_limit_choices_to(limit_choices_to)

        return name, path, args, kwargs

    def formfield(self, **kwargs):
        from ..forms.fields import ImageEntityField

        return ImageEntityField(
            label=self.verbose_name,
            required=not self.blank,
            q_filter=self.remote_field.limit_choices_to,
            help_text=self.help_text,
        )

    def get_internal_type(self):
        return 'ForeignKey'


class ImageEntityManyToManyField(models.ManyToManyField):
    def __init__(self, **kwargs):
        kwargs['to'] = settings.DOCUMENTS_DOCUMENT_MODEL
        kwargs['limit_choices_to'] = _build_limit_choices_to(kwargs.get('limit_choices_to'))

        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

        # TODO: factorise
        limit_choices_to = kwargs.get('limit_choices_to')
        if limit_choices_to is not None:
            kwargs['limit_choices_to'] = _deconstruct_limit_choices_to(limit_choices_to)

        return name, path, args, kwargs

    def formfield(self, **kwargs):
        from ..forms.fields import MultiImageEntityField

        return MultiImageEntityField(
            label=self.verbose_name,
            required=not self.blank,
            q_filter=self.remote_field.limit_choices_to,
            help_text=self.help_text,
        )

    def get_internal_type(self):
        return 'ManyToManyField'
