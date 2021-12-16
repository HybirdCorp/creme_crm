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

from django.http import Http404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity, Relation
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from .. import constants, get_activity_model
from ..forms import bricks as bricks_forms

Activity = get_activity_model()


class ParticipantsAdding(generic.RelatedToEntityFormPopup):
    form_class = bricks_forms.ParticipantCreateForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title = _('Adding participants to activity «{entity}»')
    submit_label = _('Add the participants')
    entity_id_url_kwarg = 'activity_id'
    entity_classes = Activity

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)


class ParticipantRemoving(generic.CremeModelDeletion):
    model = Relation
    permissions = 'activities'

    def check_instance_permissions(self, instance, user):
        has_perm = user.has_perm_to_unlink_or_die
        has_perm(instance.subject_entity)
        has_perm(instance.object_entity)

    def get_query_kwargs(self):
        kwargs = super().get_query_kwargs()
        kwargs['type'] = constants.REL_OBJ_PART_2_ACTIVITY

        return kwargs

    def get_success_url(self):
        # TODO: callback_url?
        return self.object.subject_entity.get_absolute_url()


class SubjectsAdding(generic.RelatedToEntityFormPopup):
    form_class = bricks_forms.SubjectCreateForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title = _('Adding subjects to activity «{entity}»')
    submit_label = _('Add the subjects')
    entity_id_url_kwarg = 'activity_id'
    entity_classes = Activity

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)


class ActivityUnlinking(generic.CremeDeletion):
    permissions = 'activities'
    activity_pk_arg = 'id'
    entity_pk_arg = 'object_id'

    relation_types = (
        constants.REL_SUB_PART_2_ACTIVITY,
        constants.REL_SUB_ACTIVITY_SUBJECT,
        constants.REL_SUB_LINKED_2_ACTIVITY,
    )

    def check_instances_permissions(self, entities, user):
        has_perm = user.has_perm_to_unlink_or_die
        for entity in entities.values():
            has_perm(entity)

    def get_entities(self):
        request = self.request
        POST = request.POST
        activity_id = get_from_POST_or_404(POST, self.activity_pk_arg, cast=int)
        subject_id = get_from_POST_or_404(POST, self.entity_pk_arg, cast=int)
        entities_per_id = CremeEntity.objects.in_bulk([activity_id, subject_id])

        if len(entities_per_id) != 2:
            raise Http404(gettext('One entity does not exist any more.'))

        entities = {
            'entity': entities_per_id[subject_id],
            'activity': entities_per_id[activity_id],
        }

        self.check_instances_permissions(entities=entities, user=request.user)

        return entities

    def perform_deletion(self, request):
        entities = self.get_entities()

        for relation in Relation.objects.filter(
            subject_entity=entities['entity'].id,
            type__in=self.relation_types,
            object_entity=entities['activity'].id,
        ):
            relation.delete()
