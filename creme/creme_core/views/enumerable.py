################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2022  Hybird
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

from django.core.exceptions import FieldDoesNotExist
from django.http import Http404
from django.shortcuts import get_object_or_404

from ..core.enumerable import enumerable_registry
from ..core.exceptions import BadRequestError, ConflictError
from ..http import CremeJsonResponse
from ..models import CustomField, CustomFieldEnumValue
from .generic import base


class ChoicesView(base.ContentTypeRelatedMixin, base.CheckedView):
    response_class = CremeJsonResponse
    field_url_kwarg = 'field'
    registry = enumerable_registry
    limit_arg = 'limit'
    term_arg = 'term'

    def check_related_ctype(self, ctype):
        self.request.user.has_perm_to_access_or_die(ctype.app_label)

    def get_field_name(self):
        return self.kwargs[self.field_url_kwarg]

    def get_enumerator(self):
        try:
            return self.registry.enumerator_by_fieldname(
                model=self.get_ctype().model_class(),
                field_name=self.get_field_name(),
            )
        except FieldDoesNotExist as e:
            raise Http404('This field does not exist.') from e
        except ValueError as e:
            raise ConflictError(e) from e

    def get(self, request, *args, **kwargs):
        try:
            limit = request.GET.get(self.limit_arg)
            limit = int(limit) if limit is not None else None
            term = request.GET.get(self.term_arg)
        except ValueError as e:
            raise BadRequestError(e) from e

        return self.response_class(
            self.get_enumerator().choices(user=request.user, limit=limit, term=term),
            safe=False,  # Result is not a dictionary
        )


class CustomFieldEnumsView(base.CheckedView):
    response_class = CremeJsonResponse
    cfield_id_url_kwarg = 'cf_id'

    def get(self, request, *args, **kwargs):
        cf = get_object_or_404(CustomField, pk=kwargs[self.cfield_id_url_kwarg])

        return self.response_class(
            [*CustomFieldEnumValue.objects.filter(custom_field=cf).values_list('id', 'value')],
            safe=False,  # Result is not a dictionary
        )
