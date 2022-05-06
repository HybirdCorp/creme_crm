# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django import http
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.http import is_ajax
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from ..core import CLASS_MAP as _CLASS_MAP
from ..core import CONVERT_MATRIX


class Conversion(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = 'billing'
    entity_id_url_kwarg = 'src_id'
    dest_type_arg = 'type'

    dest_title = _('{src} (converted into {dest._meta.verbose_name})')

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)

        # TODO: move to EntityRelatedMixin ??
        if entity.is_deleted:
            raise ConflictError(
                'This entity cannot be converted because it is deleted.'
            )

    def get_destination_model(self, src):
        request = self.request

        allowed_dests = CONVERT_MATRIX.get(src.__class__)
        if not allowed_dests:
            raise ConflictError(
                'This entity cannot be converted to a(nother) billing document.'
            )

        dest_class_id = get_from_POST_or_404(request.POST, self.dest_type_arg)
        if dest_class_id not in allowed_dests:
            raise ConflictError(
                f'Invalid destination type '
                f'[allowed destinations for this type: {allowed_dests}]'
            )

        dest_class = _CLASS_MAP[dest_class_id]

        request.user.has_perm_to_create_or_die(dest_class)

        return dest_class

    def post(self, *args, **kwargs):
        src = self.get_related_entity()
        dest_class = self.get_destination_model(src)

        # TODO: build() copy the number (it's a feature for recurrent generation
        #       to fallback to the TemplateBase instance's number)
        #       but here copy a Quote number into an Invoice number does not mean anything.
        #  => add a argument 'copy_number=False'? do not use 'build()'?
        src.number = ''

        with atomic():
            dest = dest_class()
            dest.build(src)
            dest.name = self.dest_title.format(src=src, dest=dest)
            # dest.generate_number()
            dest.save()

        url = dest.get_absolute_url()

        return (
            http.HttpResponse(url, content_type='text/plain')
            # if self.request.is_ajax() else
            if is_ajax(self.request) else
            http.HttpResponseRedirect(url)
        )
