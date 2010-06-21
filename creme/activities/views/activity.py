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

from creme_core.views.generic import (view_real_entity_with_template, #view_real_entity,
                                      add_entity, inner_popup, list_view)
from creme_core.entities_access.functions_for_permissions import get_view_or_die, edit_object_or_die, add_view_or_die, edit_view_or_die
from creme_core.gui.last_viewed import change_page_for_last_viewed

from activities.models import Activity
from activities.forms import (MeetingEditForm, PhoneCallEditForm, IndisponibilityCreateForm, ActivityEditForm,
                              MeetingCreateForm, PhoneCallCreateForm)
from activities.utils import get_ical

__activity_ct = ContentType.objects.get_for_model(Activity)


@login_required
@add_view_or_die(__activity_ct, None, 'activities')
@get_view_or_die('activities')
def add_indisponibility(request):
    return add_entity(request, IndisponibilityCreateForm, '/activities/calendar/user')

def _add_activity(request, class_form, extra_initial=None):
    GET_get = request.GET.get
    POST    = request.POST

    initial_dict = {
                    'id_entity_for_relation': GET_get('id_entity_for_relation'),
                    'ct_entity_for_relation': GET_get('ct_entity_for_relation'),
                    'entity_relation_type':   GET_get('entity_relation_type'),
                    'user':                   request.user.id,
                   }
    if extra_initial:
        initial_dict.update(extra_initial)

    if POST:
        activity_form = class_form(POST, initial=initial_dict)
        if activity_form.is_valid():
            activity_form.save()
            activity_form.save_participants() #TODO: move in activity_form.save() ??

            return  HttpResponseRedirect('/activities/calendar/my')
    else:
        activity_form = class_form(initial=initial_dict)

    return render_to_response('creme_core/generics/blockform/add.html',
                              { 'form': activity_form},
                              context_instance=RequestContext(request))

@login_required
@add_view_or_die(__activity_ct, None, 'activities')
@get_view_or_die('activities')
def add(request, type):
    change_page_for_last_viewed(request) #TODO: works ???

    class_form = None
    extra_initial = None

    if type == "meeting":
        class_form = MeetingCreateForm
    elif type == "phonecall":
        class_form    = PhoneCallCreateForm
        extra_initial = {'call_type' : 2,} #TODO: use a constant.....

    if class_form is None:
        raise Http404('No activity type matches with: %s', type)

    return _add_activity(request, class_form, extra_initial)

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

    #TODO: improve this ugly part
    if activity.type.name == "Rendez-vous":
        form_class = MeetingEditForm
    elif activity.type.name == "Telephone":
        form_class = PhoneCallEditForm
    elif activity.type.name == "Indisponible":
        form_class = IndisponibilityCreateForm
    else:
        form_class = ActivityEditForm

    if request.POST:
        form = form_class(request.POST, instance=activity)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/activities/activity/%s' % activity_id)
    else:
        form = form_class(instance=activity)

    return render_to_response('creme_core/generics/blockform/edit.html',
                              {'form': form},
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
    return list_view(request, Activity, extra_dict={'extra_bt_template': 'activities/frags/ical_list_view_button.html'})


@login_required
@get_view_or_die('activities')
def download_ical(request, ids):
    activities = Activity.objects.filter(pk__in=ids.split(','))
    response = HttpResponse(get_ical(activities), mimetype="text/calendar")
    response['Content-Disposition'] = "attachment; filename=Calendar.ics"
    return response