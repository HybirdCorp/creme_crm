# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.models import Relation #CremeEntity
from creme_core.views.generic import add_to_entity

from activities.models import Activity
from activities.forms import ParticipantCreateForm, SubjectCreateForm
from activities.constants import REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY


@login_required
@permission_required('activities')
def add_participant(request, activity_id):
    return add_to_entity(request, activity_id, ParticipantCreateForm,
                         _(u'Adding participants to activity <%s>'),
                         entity_class=Activity
                        )

@login_required
@permission_required('activities')
def add_subject(request, activity_id):
    return add_to_entity(request, activity_id, SubjectCreateForm,
                         _(u'Adding subjects to activity <%s>'),
                         entity_class=Activity
                        )

@login_required
@permission_required('activities')
#def unlink_activity(request, activity_id, entity_id):
def unlink_activity(request):
    #TODO: use credentials ????

    #entity = get_object_or_404(CremeEntity, pk=entity_id) #.get_real_entity() ??????
    #die_status = edit_object_or_die(request, entity)
    #if die_status:
        #return die_status

    #activity = get_object_or_404(Activity, pk=activity_id)  #TODO: really need to retrieve the object ????
    #die_status = edit_object_or_die(request, activity)
    #if die_status:
        #return die_status
    post_get = request.POST.get
    activity_id = post_get('id')
    entity_id   = post_get('object_id')

    if activity_id is None or entity_id is None:
        return HttpResponse('', status=404)

    types = (REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY)
    for relation in Relation.objects.filter(subject_entity=entity_id, type__in=types, object_entity=activity_id):
        relation.delete()

    return HttpResponse('')
