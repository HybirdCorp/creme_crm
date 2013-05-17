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

from datetime import datetime
from functools import partial

from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import RelationType
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.views.generic import view_real_entity, list_view, inner_popup, edit_entity
from creme.creme_core.utils import get_ct_or_404, get_from_GET_or_404, jsonify

from ..models import Activity, ActivityType, ActivitySubType
from ..forms.activity import (ActivityCreateForm, IndisponibilityCreateForm,
                              RelatedActivityCreateForm, CalendarActivityCreateForm,
                              ActivityEditForm)
from ..utils import get_ical
from ..constants import ACTIVITYTYPE_INDISPO, ACTIVITYTYPE_MEETING, ACTIVITYTYPE_PHONECALL, ACTIVITYTYPE_TASK


def _add_activity(request, form_class,
                  content_template='activities/frags/activity_form_content.html',
                  type_id=None, **form_args):
    if request.method == 'POST':
        form = form_class(activity_type_id=type_id, user=request.user, data=request.POST, **form_args)

        if form.is_valid():
            form.save()

            #TODO: hasattr is not great (expand form_args instead ?)
            entity = form.entity_for_relation if hasattr(form, 'entity_for_relation') else \
                     form.instance

            return HttpResponseRedirect(entity.get_absolute_url())
    else:
        form = form_class(activity_type_id=type_id, user=request.user, **form_args)

    return render(request, 'activities/add_activity_form.html',
                  {'form':             form,
                   'title':            Activity.get_creation_title(type_id),
                   'content_template': content_template,
                  }
                 )

@login_required
@permission_required('activities')
@permission_required('activities.add_activity')
def add(request):
    return _add_activity(request, ActivityCreateForm)

_TYPES_MAP = {
        "meeting":   ACTIVITYTYPE_MEETING,
        "phonecall": ACTIVITYTYPE_PHONECALL,
        "task":      ACTIVITYTYPE_TASK,
    }

@login_required
@permission_required('activities')
@permission_required('activities.add_activity')
def add_fixedtype(request, act_type):
    type_id = _TYPES_MAP.get(act_type)

    if not type_id:
        raise Http404('No activity type matches with: %s' % act_type)

    return _add_activity(request, ActivityCreateForm, type_id=type_id)

@login_required
@permission_required('activities')
@permission_required('activities.add_activity')
def add_indisponibility(request):
    return _add_activity(request, IndisponibilityCreateForm,
                         content_template='activities/frags/indispo_form_content.html',
                         type_id=ACTIVITYTYPE_INDISPO,
                        )

@login_required
@permission_required('activities')
@permission_required('activities.add_activity')
def add_related(request):
    GET = request.GET
    ct_id       = get_from_GET_or_404(GET, 'ct_entity_for_relation')
    entity_id   = get_from_GET_or_404(GET, 'id_entity_for_relation')
    rtype_id    = get_from_GET_or_404(GET, 'entity_relation_type')
    #act_type_id = get_from_GET_or_404(GET, 'activity_type')
    act_type_id = GET.get('activity_type')

    model_class   = get_ct_or_404(ct_id).model_class()
    entity        = get_object_or_404(model_class, pk=entity_id)
    relation_type = get_object_or_404(RelationType, pk=rtype_id)
    #activity_type = get_object_or_404(ActivityType, pk=act_type_id)

    if act_type_id:
        get_object_or_404(ActivityType, pk=act_type_id)

    request.user.has_perm_to_link_or_die(entity)

    #TODO: move to a RelationType method...
    subject_ctypes = frozenset(relation_type.subject_ctypes.values_list('id', flat=True))
    if subject_ctypes and not int(ct_id) in subject_ctypes:
        raise ConflictError('Incompatible relation type')

    return _add_activity(request, RelatedActivityCreateForm,
                         entity_for_relation=entity,
                         relation_type=relation_type,
                         #type_id=activity_type.id,
                         type_id=act_type_id,
                        )

@login_required
@permission_required('activities')
@permission_required('activities.add_activity')
def add_popup(request):
    if request.method == 'POST':
        form = CalendarActivityCreateForm(user=request.user, data=request.POST,
                                          files=request.FILES or None,
                                         )

        if form.is_valid():
            form.save()
    else:
        get_or_404 = partial(get_from_GET_or_404, GET=request.GET, cast=int)
        today = datetime.today()
        start_date = datetime(get_or_404(key='year',   default=today.year),
                              get_or_404(key='month',  default=today.month),
                              get_or_404(key='day',    default=today.day),
                              get_or_404(key='hour',   default=today.hour),
                              get_or_404(key='minute', default=today.minute),
                             )
        form = CalendarActivityCreateForm(start=start_date, user=request.user)

    return inner_popup(request, 'activities/add_popup_activity_form.html',
                       {'form':   form,
                        'title':  _(u'New activity'),
                        #TODO: content_template ?? (see template)
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
@permission_required('activities')
def edit(request, activity_id):
    return edit_entity(request, activity_id, Activity, ActivityEditForm)

@login_required
@permission_required('activities')
def detailview(request, activity_id):
    return view_real_entity(request, activity_id, '/activities/activity',
                            'activities/view_activity.html',
                           )

@login_required
@permission_required('activities')
def popupview(request, activity_id):
    return view_real_entity(request, activity_id, '/activities/activity',
                            'activities/view_activity_popup.html',
                           )

@login_required
@permission_required('activities')
def listview(request, type_id=None):
    kwargs = {}

    from django.db.models import Q

    if type_id:
        #TODO: change 'add' button too ??
        kwargs['extra_q'] = Q(type=type_id)

    return list_view(request, Activity,
                     extra_dict={'add_url': '/activities/activity/add',
                                 'extra_bt_templates': ('activities/frags/ical_list_view_button.html', )
                                },
                     **kwargs
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

@jsonify
@login_required
def get_types(request, type_id):
    get_object_or_404(ActivityType, pk=type_id)
    return list(ActivitySubType.objects.filter(type=type_id).order_by('id')
                                       .values_list('id', 'name')
               )
