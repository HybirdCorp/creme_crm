# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016  Hybird
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

from django.core.urlresolvers import reverse_lazy

from creme.creme_core import forms

from .. import get_document_model
from ..constants import MIMETYPE_PREFIX_IMG


class ImageFieldMixin(object):
    @property
    def _image_creation_url(self):
        return reverse_lazy('documents__create_image_popup')

    def build_q_filter(self, q_filter):
        basic_filter = {'mime_type__name__startswith': MIMETYPE_PREFIX_IMG}

        q_filter = dict(q_filter) if q_filter else {}
        q_filter.update(basic_filter)

        return q_filter, q_filter != basic_filter

    @property
    def force_creation(self):
        return self._force_creation

    @force_creation.setter
    def force_creation(self, force_creation):
        self._force_creation = force_creation

        if force_creation and not self._create_action_url:
            self._create_action_url = self._image_creation_url

        self._update_creation_info()

    @property
    def q_filter(self):
        return self._q_filter

    @q_filter.setter
    def q_filter(self, q_filter):
        self._check_qfilter(q_filter)

        q_filter, is_extra_filter = self.build_q_filter(q_filter)
        self.widget.q_filter = self._q_filter = q_filter

        if is_extra_filter:
            self._force_creation = False
            self._create_action_url = ''

        self._update_creation_info()


class ImageEntityField(ImageFieldMixin, forms.CreatorEntityField):
    def __init__(self, q_filter=None, create_action_url='', force_creation=False, *args, **kwargs):
        q_filter, is_extra_filter = self.build_q_filter(q_filter)

        if not is_extra_filter or (force_creation and not create_action_url):
            force_creation = True
            create_action_url = self._image_creation_url

        super(ImageEntityField, self).__init__(
                model=get_document_model(),
                q_filter=q_filter,
                create_action_url=create_action_url,
                force_creation=force_creation,
                *args, **kwargs
            )


class MultiImageEntityField(ImageFieldMixin, forms.MultiCreatorEntityField):
    def __init__(self, q_filter=None, create_action_url='', force_creation=False, *args, **kwargs):
        q_filter, is_extra_filter = self.build_q_filter(q_filter)

        if not is_extra_filter or (force_creation and not create_action_url):
            force_creation = True
            create_action_url = self._image_creation_url

        super(MultiImageEntityField, self).__init__(
                model=get_document_model(),
                q_filter=q_filter,
                create_action_url=create_action_url,
                force_creation=force_creation,
                *args, **kwargs
            )
