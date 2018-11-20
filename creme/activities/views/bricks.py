# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django import shortcuts, http
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import Relation, CremeEntity
from creme.creme_core.utils import get_from_POST_or_404
# from creme.creme_core.views.generic import add_to_entity
from creme.creme_core.views.generic import RelatedToEntityFormPopup

from .. import get_activity_model, constants
from ..forms import bricks as bricks_forms


Activity = get_activity_model()


# @login_required
# @permission_required('activities')
# def add_participant(request, activity_id):
#     return add_to_entity(request, activity_id, bricks_forms.ParticipantCreateForm,
#                          _('Adding participants to activity «%s»'),
#                          entity_class=Activity,
#                          link_perm=True,
#                          submit_label=_('Add the participants'),
#                          template='creme_core/generics/blockform/link_popup.html',
#                         )
class ParticipantsAdding(RelatedToEntityFormPopup):
    form_class = bricks_forms.ParticipantCreateForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title_format = _('Adding participants to activity «{}»')
    submit_label = _('Add the participants')
    entity_id_url_kwarg = 'activity_id'
    entity_classes = Activity

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)


@login_required
@permission_required('activities')
def delete_participant(request):
    relation = shortcuts.get_object_or_404(Relation,
                                           pk=get_from_POST_or_404(request.POST, 'id'),
                                           type=constants.REL_OBJ_PART_2_ACTIVITY,
                                          )
    subject = relation.subject_entity
    user    = request.user

    has_perm = user.has_perm_to_unlink_or_die
    has_perm(subject)
    has_perm(relation.object_entity)

    relation.delete()

    return shortcuts.redirect(subject.get_real_entity())


# @login_required
# @permission_required('activities')
# def add_subject(request, activity_id):
#     return add_to_entity(request, activity_id, bricks_forms.SubjectCreateForm,
#                          _('Adding subjects to activity «%s»'),
#                          entity_class=Activity, link_perm=True,
#                          submit_label=_('Add the subjects'),
#                          template='creme_core/generics/blockform/link_popup.html',
#                         )
class SubjectsAdding(RelatedToEntityFormPopup):
    form_class = bricks_forms.SubjectCreateForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title_format = _('Adding subjects to activity «{}»')
    submit_label = _('Add the subjects')
    entity_id_url_kwarg = 'activity_id'
    entity_classes = Activity

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)


@login_required
@permission_required('activities')
def unlink_activity(request):
    POST = request.POST
    activity_id = get_from_POST_or_404(POST, 'id')
    entity_id   = get_from_POST_or_404(POST, 'object_id')
    entities = list(CremeEntity.objects.filter(pk__in=[activity_id, entity_id]))

    if len(entities) != 2:
        raise http.Http404(ugettext('One entity does not exist any more.'))

    has_perm = request.user.has_perm_to_unlink_or_die

    for entity in entities:
        has_perm(entity)

    types = (constants.REL_SUB_PART_2_ACTIVITY,
             constants.REL_SUB_ACTIVITY_SUBJECT,
             constants.REL_SUB_LINKED_2_ACTIVITY,
            )
    for relation in Relation.objects.filter(subject_entity=entity_id,
                                            type__in=types,
                                            object_entity=activity_id):
        relation.delete()

    return http.HttpResponse()
