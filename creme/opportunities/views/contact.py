################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2022  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import Relation, RelationType
from creme.creme_core.views.generic import EntityCreationPopup
from creme.creme_core.views.generic.base import EntityRelatedMixin
from creme.persons import get_contact_model

from .. import get_opportunity_model
from ..constants import REL_SUB_LINKED_CONTACT
from ..forms.contact import RelatedContactForm


class RelatedContactCreation(EntityRelatedMixin, EntityCreationPopup):
    model = get_contact_model()
    form_class = RelatedContactForm
    permissions = 'opportunities'
    title = _('Create a contact linked to «{opportunity}»')
    entity_id_url_kwarg = 'opp_id'
    entity_classes = get_opportunity_model()
    entity_form_kwarg = 'opportunity'

    # NB: see LinkedContactsBrick
    relation_type_id = REL_SUB_LINKED_CONTACT

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        RelationType.objects.get(id=self.relation_type_id).is_enabled_or_die()

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)
        user.has_perm_to_link_or_die(entity)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.set_entity_in_form_kwargs(kwargs)

        return kwargs

    def form_valid(self, form):
        # with atomic():  # TODO ?
        response = super().form_valid(form)
        Relation.objects.create(
            user=self.request.user,
            subject_entity=form.instance,
            type_id=self.relation_type_id,
            object_entity=self.get_related_entity(),
        )

        return response

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['opportunity'] = self.get_related_entity().allowed_str(self.request.user)

        return data
