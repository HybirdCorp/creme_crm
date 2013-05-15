# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.models import Relation, CremeEntity
from creme.creme_core.views.generic import add_to_entity
from creme.creme_core.utils import get_from_POST_or_404

from ..models import Activity
from ..forms.blocks import ParticipantCreateForm, SubjectCreateForm
from ..constants import (REL_SUB_PART_2_ACTIVITY, REL_OBJ_PART_2_ACTIVITY,
                         REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY)


@login_required
@permission_required('activities')
def add_participant(request, activity_id):
    return add_to_entity(request, activity_id, ParticipantCreateForm,
                         _(u'Adding participants to activity <%s>'),
                         entity_class=Activity, link_perm=True,
                        )

@login_required
@permission_required('activities')
def delete_participant(request):
    relation = get_object_or_404(Relation,
                                 pk=get_from_POST_or_404(request.POST, 'id'),
                                 type=REL_OBJ_PART_2_ACTIVITY,
                                )
    subject  = relation.subject_entity
    user     = request.user

    subject.can_unlink_or_die(user)
    relation.object_entity.can_unlink_or_die(user)

    relation.delete()

    return HttpResponseRedirect(subject.get_real_entity().get_absolute_url())

@login_required
@permission_required('activities')
def add_subject(request, activity_id):
    return add_to_entity(request, activity_id, SubjectCreateForm,
                         _(u'Adding subjects to activity <%s>'),
                         entity_class=Activity, link_perm=True,
                        )

@login_required
@permission_required('activities')
def unlink_activity(request):
    POST = request.POST
    activity_id = get_from_POST_or_404(POST, 'id')
    entity_id   = get_from_POST_or_404(POST, 'object_id')
    entities = list(CremeEntity.objects.filter(pk__in=[activity_id, entity_id]))

    if len(entities) != 2:
        raise Http404(_('One entity does not exist any more.'))

    user = request.user
    #CremeEntity.populate_credentials(entities, user)

    for entity in entities:
        entity.can_unlink_or_die(user)

    types = (REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY)
    for relation in Relation.objects.filter(subject_entity=entity_id, 
                                            type__in=types,
                                            object_entity=activity_id):
        relation.delete()

    return HttpResponse('')
