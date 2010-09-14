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

from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType
from creme_core.views.generic import (view_real_entity_with_template, #view_real_entity,
                                      add_entity, inner_popup, list_view)
from creme_core.entities_access.functions_for_permissions import get_view_or_die, edit_object_or_die, add_view_or_die, edit_view_or_die
from creme_core.utils import get_ct_or_404
#from creme_core.gui.last_viewed import change_page_for_last_viewed

from activities.models import Activity
from activities.forms import*
from activities.utils import get_ical
from activities.constants import ACTIVITYTYPE_INDISPO

__activity_ct = ContentType.objects.get_for_model(Activity)


@login_required
@add_view_or_die(__activity_ct, None, 'activities')
@get_view_or_die('activities')
def add_indisponibility(request):
    return add_entity(request, IndisponibilityCreateForm, '/activities/calendar/user')

def _add_activity(request, class_form, **form_args):
    POST = request.POST

    if POST:
        activity_form = class_form(data=POST, **form_args)

        if activity_form.is_valid():
            activity_form.save()

            return  HttpResponseRedirect('/activities/calendar/my')
    else:
        activity_form = class_form(**form_args)

    return render_to_response('creme_core/generics/blockform/add.html',
                              {'form': activity_form},
                              context_instance=RequestContext(request))

_forms_map = {
        "meeting":   (MeetingCreateForm,   MeetingCreateWithoutRelationForm),
        "task":      (TaskCreateForm,      TaskCreateWithoutRelationForm),
        "phonecall": (PhoneCallCreateForm, PhoneCallCreateWithoutRelationForm),
    }

@login_required
@add_view_or_die(__activity_ct, None, 'activities')
@get_view_or_die('activities')
def add_with_relation(request, act_type):
    #change_page_for_last_viewed(request) #TODO: works ???

    GET = request.GET
    model_class   = get_ct_or_404(GET['ct_entity_for_relation']).model_class()
    entity        = get_object_or_404(model_class, pk=GET['id_entity_for_relation'])
    relation_type = get_object_or_404(RelationType, pk=GET['entity_relation_type'])

    #TODO: credentials ??

    form_class = _forms_map.get(act_type)

    if not form_class:
        raise Http404('No activity type matches with: %s' % act_type)

    return _add_activity(request, form_class[0], entity_for_relation=entity, relation_type=relation_type)

@login_required
@add_view_or_die(__activity_ct, None, 'activities')
@get_view_or_die('activities')
def add_without_relation(request, act_type):
    form_class = _forms_map.get(act_type)

    if not form_class:
        raise Http404('No activity type matches with: %s' % act_type)

    return _add_activity(request, form_class[1])

@login_required
@get_view_or_die('activities')
def edit(request, activity_id):
    """
        @Permissions : Acces or Admin to ticket app & Edit on current Activity object
    """
    activity = get_object_or_404(Activity, pk=activity_id)
    activity = activity.get_real_entity() #after edit_object_or_die ????

    die_status = edit_object_or_die(request, activity)
    if die_status:
        return die_status

    form_class = ActivityEditForm if activity.type_id != ACTIVITYTYPE_INDISPO else IndisponibilityCreateForm

    if request.POST:
        form = form_class(request.POST, instance=activity)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/activities/activity/%s' % activity_id)
    else:
        form = form_class(instance=activity)

    return render_to_response('creme_core/generics/blockform/edit.html',
                              {
                                'form':   form,
                                'object': activity,
                              },
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('activities')
def detailview(request, activity_id):
    return view_real_entity_with_template(request, activity_id,
                                          '/activities/activity',
                                          'activities/view_activity.html')

@login_required
@get_view_or_die('activities')
def popupview(request, activity_id):
#    activity = view_real_entity(request, activity_id)
#
#    return inner_popup(request, 'activity/view_activity_popup.html',#TODO : Implement the real template without head/title/meta... ASAP
#                              {
#                                'object': activity,
#                                'title':  u"%s" % activity,
#                              },
#                              is_valid=False,
#                              context_instance=RequestContext(request))

    return view_real_entity_with_template(request,
                                          activity_id,
                                          '/activities/activity',
                                          'activities/view_activity_popup.html')

@login_required
@get_view_or_die('activities')
def listview(request):
    return list_view(request, Activity, 
                     extra_dict={'extra_bt_templates':
                                    ('activities/frags/ical_list_view_button.html',
                                     'activities/frags/button_add_meeting_without_relation.html',
                                     'activities/frags/button_add_phonecall_without_relation.html') #TODO: add Task too ??
                                }
                    )

@login_required
@get_view_or_die('activities')
def download_ical(request, ids):
    activities = Activity.objects.filter(pk__in=ids.split(','))
    response = HttpResponse(get_ical(activities), mimetype="text/calendar")
    response['Content-Disposition'] = "attachment; filename=Calendar.ics"
    return response
