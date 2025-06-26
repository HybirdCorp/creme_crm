################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django import http
# from django.db.transaction import atomic
# from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext as _

from creme import billing
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.http import is_ajax
from creme.creme_core.models import CremeEntity  # Relation, RelationType
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

# from ..core import CLASS_MAP as _CLASS_MAP
# from ..core import CONVERT_MATRIX, RTYPE_MATRIX
from ..core import conversion
from ..models import Base

logger = logging.getLogger(__name__)


class Conversion(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = 'billing'
    entity_id_url_kwarg = 'src_id'
    dest_type_arg = 'type'  # TODO: rename "target"?

    # dest_title = _('{src} (converted into {dest._meta.verbose_name})')
    converter_registry = conversion.converter_registry

    target_models = {
        'credit_note': billing.get_credit_note_model(),  # NB: unused
        'invoice':     billing.get_invoice_model(),
        'quote':       billing.get_quote_model(),
        'sales_order': billing.get_sales_order_model(),
    }

    def get_converter(self, source: CremeEntity, target_model: type[Base]) -> conversion.Converter:
        """Gets the Converter instance.
        @raise ConflictError: If the conversion is not possible.
        @raise PermissionDenied: If the conversion is not allowed.
        """
        converter = self.converter_registry.get_converter(
            source=source, target_model=target_model, user=self.request.user,
        )

        if converter is None:
            raise ConflictError(_('This model cannot be converted.'))

        converter.check_permissions()

        return converter

    def check_related_entity_permissions(self, entity, user):
        # user.has_perm_to_view_or_die(entity)
        #
        # if entity.is_deleted:
        #     raise ConflictError(
        #         'This entity cannot be converted because it is deleted.'
        #     )
        # NB: we check permissions with the converter later (it needs the entity)
        pass

    # def get_destination_model(self, src):
    #     request = self.request
    #
    #     allowed_dests = CONVERT_MATRIX.get(src.__class__)
    #     if not allowed_dests:
    #         raise ConflictError(
    #             'This entity cannot be converted to a(nother) billing document.'
    #         )
    #
    #     dest_class_id = get_from_POST_or_404(request.POST, self.dest_type_arg)
    #     if dest_class_id not in allowed_dests:
    #         raise ConflictError(
    #             f'Invalid destination type '
    #             f'[allowed destinations for this type: {allowed_dests}]'
    #         )
    #
    #     dest_class = _CLASS_MAP[dest_class_id]
    #
    #     request.user.has_perm_to_create_or_die(dest_class)
    #
    #     return dest_class
    def get_target_model(self):
        model_id = get_from_POST_or_404(self.request.POST, self.dest_type_arg)
        model = self.target_models.get(model_id)

        if model is None:
            raise ConflictError(
                _('This target model is invalid: "{model}"').format(model=model_id)
            )

        return model

    # def get_conversion_relation_type(self, source_model, dest_model):
    #     rtype_id = RTYPE_MATRIX.get((source_model, dest_model))
    #     if not rtype_id:
    #         return None
    #
    #     rtype = RelationType.objects.get(id=rtype_id)
    #     if not rtype.enabled:
    #         logger.info(
    #             'Billing conversion: the relation type "%s" is disabled, '
    #             'no relationship is created.',
    #             rtype,
    #         )
    #         return None
    #
    #     return rtype

    def post(self, *args, **kwargs):
        # src = self.get_related_entity()
        # dest_class = self.get_destination_model(src)
        # src.number = ''
        # rtype = self.get_conversion_relation_type(
        #     source_model=type(src), dest_model=dest_class,
        # )
        #
        # with atomic():
        #     dest = dest_class()
        #     dest.build(src)
        #     dest.name = self.dest_title.format(src=src, dest=dest)
        #     dest.save()
        #
        #     if rtype:
        #         Relation.objects.safe_create(
        #             user=self.request.user,
        #             subject_entity=dest,
        #             type=rtype,
        #             object_entity=src,
        #         )
        #
        # url = dest.get_absolute_url()
        #
        # return (
        #     http.HttpResponse(url, content_type='text/plain')
        #     if is_ajax(self.request) else
        #     http.HttpResponseRedirect(url)
        # )
        converter = self.get_converter(
            source=self.get_related_entity(),
            target_model=self.get_target_model(),
        )
        converted = converter.perform()
        url = converted.get_absolute_url()

        return (
            http.HttpResponse(url, content_type='text/plain')
            if is_ajax(self.request) else
            http.HttpResponseRedirect(url)
        )
