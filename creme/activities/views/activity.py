# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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
from functools import partial

from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.models import RelationType, EntityCredentials, Relation
from creme.creme_core.views.generic import view_real_entity, add_entity, list_view, inner_popup
from creme.creme_core.utils import get_ct_or_404, get_from_GET_or_404, get_from_POST_or_404

from creme.activities.models import Activity
from creme.activities.forms import *
from creme.activities.utils import get_ical
from creme.activities.constants import ACTIVITYTYPE_INDISPO


INDISPONIBILITY_HELP_MESSAGE = _("""*** How indisponibility works ***
Unlike other kind of activities, an indisponibility works only for one Creme user participant. This user will be the one chosen by the assigned user field.
He will be in charge of the indisponibility entity and considered as unavailable on the chosen dates.
A user's indisponibility isn't linked to a specific calendar. It can be seen by anyone who chooses to see the activities of this user.
Don't be surprised if you can't add new participant on an indisponibility's detailview and don't forget that the person unavailable by this indisponibility is the assigned user of this detailview.
""")

@login_required
@permission_required('activities')
@permission_required('activities.add_activity')
def add_indisponibility(request):
    return add_entity(request, IndisponibilityCreateForm, '/activities/calendar/user',
                      extra_template_dict={'help_message' : INDISPONIBILITY_HELP_MESSAGE,
                                           'title':         ugettext(u'Add an indisponibility'),
                                          }
                     )

def _add_activity(request, class_form, **form_args):
    if request.method == 'POST':
        activity_form = class_form(user=request.user, data=request.POST, **form_args)

        if activity_form.is_valid():
            activity_form.save()

            related_url = None
            if hasattr(activity_form, 'entity_for_relation'): #TODO: not great (expeand form_args instead)
                related_url = activity_form.entity_for_relation.get_absolute_url()
            elif hasattr(activity_form.instance, 'get_absolute_url'):
                related_url = activity_form.instance.get_absolute_url()

            #TODO: factorise get_absolute_url()
            return HttpResponseRedirect(related_url or '/activities/calendar/my')
    else:
        activity_form = class_form(user=request.user, **form_args)

    return render(request, 'activities/add_activity_form.html', {'form': activity_form})

_forms_map = {
        "meeting":   (RelatedMeetingCreateForm,        MeetingCreateForm),
        "task":      (RelatedTaskCreateForm,           TaskCreateForm),
        "phonecall": (RelatedPhoneCallCreateForm,      PhoneCallCreateForm),
        "activity":  (RelatedCustomActivityCreateForm, CustomActivityCreateForm),
    }

@login_required
@permission_required('activities')
@permission_required('activities.add_activity')
def add_related(request, act_type):
    GET = request.GET
    ct_id     = get_from_GET_or_404(GET, 'ct_entity_for_relation')
    entity_id = get_from_GET_or_404(GET, 'id_entity_for_relation')
    rtype_id  = get_from_GET_or_404(GET, 'entity_relation_type')

    model_class   = get_ct_or_404(ct_id).model_class()
    entity        = get_object_or_404(model_class, pk=entity_id)
    relation_type = get_object_or_404(RelationType, pk=rtype_id)

    entity.can_link_or_die(request.user)

    #TODO: move to a RelationType method...
    subject_ctypes = frozenset(relation_type.subject_ctypes.values_list('id', flat=True))
    if subject_ctypes and not int(ct_id) in subject_ctypes:
        raise Http404('Incompatible relation type') #bof bof

    form_class = _forms_map.get(act_type)

    if not form_class:
        raise Http404('No activity type matches with: %s' % act_type)

    return _add_activity(request, form_class[0], entity_for_relation=entity, relation_type=relation_type)

@login_required
@permission_required('activities')
@permission_required('activities.add_activity')
def add(request, act_type):
    form_class = _forms_map.get(act_type)

    if not form_class:
        raise Http404('No activity type matches with: %s' % act_type)

    return _add_activity(request, form_class[1])

@login_required
@permission_required('activities')
@permission_required('activities.add_activity')
def add_popup(request):
    if request.method == 'POST':
        form = CalendarActivityCreateForm(user=request.user, data=request.POST, files=request.FILES or None)
        if form.is_valid():
            form.save()
    else:
        get_or_404 = partial(get_from_GET_or_404, GET=request.GET, cast=int)

        today = datetime.today()
        start_date = datetime(get_or_404(key='year',   default=today.year),
                              get_or_404(key='month',  default=today.month),
                              get_or_404(key='day',    default=today.day),
                              get_or_404(key='hour',   default=today.hour),
                              get_or_404(key='minute', default=today.minute))

        form = CalendarActivityCreateForm(start=start_date, user=request.user)

    return inner_popup(request, "activities/add_popup_activity_form.html",
                       {'form':   form,
                        'title':  _(u'New activity'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

#TODO: use edit_entity() ? (problem additionnal get_real_entity())
@login_required
@permission_required('activities')
def edit(request, activity_id):
    activity = get_object_or_404(Activity, pk=activity_id).get_real_entity()

    activity.can_change_or_die(request.user)

    form_class = ActivityEditForm if activity.type_id != ACTIVITYTYPE_INDISPO else IndisponibilityCreateForm

    if request.method == 'POST':
        form = form_class(user=request.user, data=request.POST, instance=activity)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/activities/activity/%s' % activity_id)
    else:
        form = form_class(instance=activity, user=request.user)

    return render(request, 'creme_core/generics/blockform/edit.html',
                  {'form': form, 'object': activity}
                 )

@login_required
@permission_required('activities')
def detailview(request, activity_id):
    return view_real_entity(request, activity_id, '/activities/activity', 'activities/view_activity.html')

@login_required
@permission_required('activities')
def popupview(request, activity_id):
    return view_real_entity(request, activity_id, '/activities/activity', 'activities/view_activity_popup.html')

@login_required
@permission_required('activities')
def listview(request):
    return list_view(request, Activity,
                     extra_dict={'extra_bt_templates':
                                    ('activities/frags/ical_list_view_button.html',
                                     'activities/frags/button_add_meeting.html',
                                     'activities/frags/button_add_phonecall.html') #TODO: add Task too ??
                                }
                    )

@login_required
@permission_required('activities')
def download_ical(request, ids):
    #TODO: is_deleted=False ??
    activities = EntityCredentials.filter(queryset=Activity.objects.filter(pk__in=ids.split(',')),
                                          user=request.user
                                         )
    response = HttpResponse(get_ical(activities), mimetype="text/calendar")
    response['Content-Disposition'] = "attachment; filename=Calendar.ics"

    return response

@login_required
@permission_required('activities')
def delete_participant(request):
    relation = get_object_or_404(Relation, pk=get_from_POST_or_404(request.POST, 'id'))
    subject  = relation.subject_entity
    user     = request.user

    subject.can_unlink_or_die(user)
    relation.object_entity.can_unlink_or_die(user)

    relation.delete()

    return HttpResponseRedirect(subject.get_real_entity().get_absolute_url())
