# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018  Hybird
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

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import get_ct_or_404

from ..utils import build_cancel_path


class CancellableMixin:
    """Mixin that helps building an URL to go back when the user is in a form."""
    cancel_url_post_argument = 'cancel_url'

    def get_cancel_url(self):
        request = self.request
        return request.POST.get(self.cancel_url_post_argument) \
               if request.method == 'POST' else \
               build_cancel_path(request)


class ContentTypeRelatedMixin:
    """Mixin for views which retrieve a ContentType from an URL argument."""
    ctype_id_url_kwarg = 'ct_id'

    def get_ctype(self):
        return get_ct_or_404(self.kwargs[self.ctype_id_url_kwarg])


class EntityCTypeRelatedMixin(ContentTypeRelatedMixin):
    """Specialisation of ContentTypeRelatedMixin to retrieve a ContentType
    related to a CremeEntity child class.
    """
    def get_ctype(self):
        ctype = super().get_ctype()
        self.request.user.has_perm_to_access_or_die(ctype.app_label)

        model = ctype.model_class()
        if not issubclass(model, CremeEntity):
            raise ConflictError('This model is not a entity model: {}'.format(model))

        return ctype