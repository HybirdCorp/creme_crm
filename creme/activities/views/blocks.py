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

from datetime import datetime

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.utils.simplejson import JSONEncoder
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, Relation
from creme_core.views.generic import inner_popup
from creme_core.entities_access.functions_for_permissions import get_view_or_die, edit_object_or_die, edit_view_or_die

from activities.models import Activity
from activities.forms import ParticipantCreateForm, SubjectCreateForm
from activities.constants import REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY
from activities.blocks import participants_block, subjects_block, future_activities_block, past_activities_block


@login_required
@edit_view_or_die(ContentType.objects.get_for_model(Activity), None, 'activity') #useful ????
@get_view_or_die('activities')
def _add_link(request, activity_id, form_class, title):
    activity = get_object_or_404(Activity, pk=activity_id)

    die_status = edit_object_or_die(request, activity)
    if die_status:
        return die_status

    POST = request.POST

    if POST:
        form = form_class(activity, POST)

        if form.is_valid():
            form.save()
    else:
        form = form_class(activity=activity)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':  form,
                        'title': title % activity,
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

def add_participant(request, activity_id):
    return _add_link(request, activity_id, ParticipantCreateForm, u"Ajout de participants pour l'activité <%s>")

def add_subject(request, activity_id):
    return _add_link(request, activity_id, SubjectCreateForm, u"Ajout de sujets pour l'activité <%s>")

@login_required
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
    POST = request.POST
    activity_id = POST.get('id')
    entity_id = POST.get('object_id')

    if activity_id is None or entity_id is None:
        return HttpResponse('', status=404)

    types = (REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY)
    for relation in Relation.objects.filter(subject_entity__id=entity_id, type__id__in=types, object_entity__id=activity_id):
        relation.delete()

    #return HttpResponseRedirect(entity.get_absolute_url())
#    return HttpResponseRedirect('/')
    return HttpResponse('')

@login_required
def reload_participants(request, activity_id):
    return participants_block.detailview_ajax(request, activity_id)

@login_required
def reload_subjects(request, activity_id):
    return subjects_block.detailview_ajax(request, activity_id)

@login_required
def reload_linked_activities(request, entity_id):
    entity = CremeEntity.objects.get(id=entity_id).get_real_entity()
    context = {'request': request, 'object': entity, 'today': datetime.today()}
    rendered = [
                (future_activities_block.id_, future_activities_block.detailview_display(context)),
                (past_activities_block.id_,   past_activities_block.detailview_display(context)),
                #(relations_block.id_,   relations_block.detailview_display(context)), #TODO: Reload relation block too ?
               ]

    return HttpResponse(JSONEncoder().encode(rendered), mimetype="text/javascript")
