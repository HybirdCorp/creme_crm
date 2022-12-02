################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from django.db.models import Q
from django.db.transaction import atomic
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import RelationType, SemiFixedRelationType
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from ..forms import relation_type as rtype_forms
from . import base


class Portal(generic.BricksView):
    template_name = 'creme_config/portals/relation-type.html'


class RelationTypeCreation(base.ConfigModelCreation):
    model = RelationType
    form_class = rtype_forms.RelationTypeCreateForm
    title = _('New custom type')


class SemiFixedRelationTypeCreation(base.ConfigModelCreation):
    model = SemiFixedRelationType
    form_class = rtype_forms.SemiFixedRelationTypeCreateForm


class RelationTypeEdition(base.ConfigModelEdition):
    # model = RelationType
    queryset = RelationType.objects.filter(is_custom=True, enabled=True)
    form_class = rtype_forms.RelationTypeEditForm
    pk_url_kwarg = 'rtype_id'
    title = pgettext_lazy('creme_config-relationship', 'Edit the type «{object}»')


class SemiFixedRelationTypeEdition(base.ConfigModelEdition):
    # model = SemiFixedRelationType
    queryset = SemiFixedRelationType.objects.filter(relation_type__enabled=True)
    form_class = rtype_forms.SemiFixedRelationTypeEditionForm
    pk_url_kwarg = 'semifixed_rtype_id'


# TODO: factorise with Job ?
class RelationTypeEnabling(generic.CheckedView):
    permissions = base._PERM
    pk_url_kwarg = 'rtype_id'
    enabled_arg = 'enabled'
    enabled_default = True

    @atomic
    def post(self, *args, **kwargs):
        # NB: does not work with PGSQL
        # rtype = get_object_or_404(
        #     RelationType.objects
        #                 .exclude(is_internal=True)
        #                 .select_related('symmetric_type')
        #                 .select_for_update(),
        #     id=kwargs[self.pk_url_kwarg],
        # )
        # sym_type = rtype.symmetric_type
        rtype_id = kwargs[self.pk_url_kwarg]
        rtypes = [
            *RelationType.objects
                         .filter(Q(id=rtype_id) | Q(symmetric_type_id=rtype_id))
                         .select_for_update()
        ]

        if len(rtypes) != 2:
            raise Http404(f'The RelationType with id="{rtype_id}" cannot be found.')

        rtype, sym_type = rtypes

        rtype.is_not_internal_or_die()

        rtype.enabled = sym_type.enabled = kwargs.get(self.enabled_arg, self.enabled_default)
        rtype.save()
        sym_type.save()

        return HttpResponse()


class RelationTypeDeletion(base.ConfigDeletion):
    id_arg = 'id'

    def perform_deletion(self, request):
        relation_type = get_object_or_404(
            RelationType,
            pk=get_from_POST_or_404(request.POST, self.id_arg),
        )

        if not relation_type.is_custom:
            raise Http404("Can't delete a standard RelationType")

        relation_type.delete()


class SemiFixedRelationTypeDeletion(base.ConfigDeletion):
    id_arg = 'id'

    def perform_deletion(self, request):
        get_object_or_404(
            SemiFixedRelationType,
            pk=get_from_POST_or_404(request.POST, self.id_arg),
        ).delete()
