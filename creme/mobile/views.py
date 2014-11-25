# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014  Hybird
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

from copy import copy
from datetime import datetime, time, timedelta
from functools import partial, wraps
import logging

from django.core.exceptions import PermissionDenied
from django.db.models.query_utils import Q
from django.db.transaction import commit_on_success
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.utils.encoding import smart_unicode
from django.utils.timezone import now, localtime
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CremeEntity, Relation, EntityCredentials
from creme.creme_core.utils import (get_from_GET_or_404, get_from_POST_or_404,
        jsonify, split_filter)
from creme.creme_core.utils.dates import make_aware_dt, get_dt_from_json_str
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.generic import add_entity

from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from creme.persons.models import Contact, Organisation

from creme.activities.constants import (NARROW, FLOATING_TIME, FLOATING,
        REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT,
        ACTIVITYTYPE_PHONECALL,
        ACTIVITYSUBTYPE_PHONECALL_FAILED, ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
        STATUS_IN_PROGRESS, STATUS_DONE, STATUS_CANCELLED)
from creme.activities.models import Activity, Calendar

from .forms import MobileContactCreateForm, MobileOrganisationCreateForm
from .models import MobileFavorite
from .templatetags.mobile_tags import orga_subjects


logger = logging.getLogger(__name__)

#TODO: in constants.py ? in settings ??
FLOATING_SIZE = 30

#TODO: in settings
WORKED_HOURS = (7, 18)


def lw_exceptions(view):
    "Lightweight exceptions handling (templates are not the legacy ones)."
    @wraps(view)
    def _aux(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except PermissionDenied as e:
            status = 403
            msg = _('You do not have access to this page, please contact your administrator.')
        except Http404 as e:
            status = 404
            msg = _('The page you have requested is unfoundable.')
        except ConflictError as e:
            status = 409
            msg = _('You can not perform this action because of business constraints.')
        #except Exception as e:
            #status = 500
            #msg = _('An internal error has occurred.')

            ##todo: what about sentry ???
            #logger.exception(e)

        return render(request, 'mobile/error.html',
                      {'status':    status,
                       'msg':       msg,
                       'exception': smart_unicode(e),
                      },
                      status=status,
                     )

    return _aux

#TODO: in creme_core ? factorise with @jsonify ?
def lw_ajax_exceptions(view):
    @wraps(view)
    def _aux(*args, **kwargs):
        status = 200

        try:
            content = view(*args, **kwargs)
        except Http404 as e:
            content = unicode(e)
            status = 404
        except PermissionDenied as e:
            content = unicode(e)
            status = 403
        except ConflictError as e:
            content = unicode(e)
            status = 409
        except Exception as e:
            logger.exception('Exception in @lw_ajax_exceptions(%s)', view.__name__)
            content = unicode(e)
            status = 400

        return HttpResponse(content, status=status) #, mimetype='text/javascript'

    return _aux

@lw_exceptions
@login_required
def portal(request):
    user = request.user

    #now_val = now()
    #build_dt = lambda h, m, s: make_aware_dt(datetime.combine(now_val, time(hour=h, minute=m, second=s)))
    now_val = localtime(now())
    build_dt = lambda h, m, s: datetime(year=now_val.year, month=now_val.month, day=now_val.day,
                                        hour=h, minute=m, second=s,
                                        tzinfo=now_val.tzinfo,
                                       )

    activities = EntityCredentials.filter(
            user,
            Activity.objects
                    .filter(is_deleted=False,
                            relations__type=REL_OBJ_PART_2_ACTIVITY,
                            relations__object_entity=user.linked_contact,
                            start__range=(build_dt(0,  0,  0),
                                          build_dt(23, 59, 59),
                                         ),
                           )
                    .exclude(status__in=(STATUS_DONE, STATUS_CANCELLED))
                    .order_by('start')
        )

    #TODO: an activity which starts before now, & ends before now too, with status != PROGRESS
    #      -> should it be displayed in this hot_activities (or in today_activities) ????

    #NB: FLOATING_TIME activities will naturally be the first activities in
    #    'today_activities' as we want (they are ordered by start, and NARROW
    #    activities which start at 0h00 will be in 'hot_activities').
    hot_activities, today_activities = split_filter(
            lambda a: a.floating_type == NARROW and
                      (a.status_id == STATUS_IN_PROGRESS or a.start < now_val),
            activities
        )
    #TODO: populate participants (regroup queries for Relation + real entities) ??

    used_worked_hours = frozenset(localtime(a.start).hour
                                    for a in today_activities
                                      if a.floating_type == NARROW
                                 )
    shortcuts_map = [(hour, hour in used_worked_hours)
                        for hour in xrange(WORKED_HOURS[0], WORKED_HOURS[1] + 1)
                    ]

    return render(request, 'mobile/index.html',
                  {'hot_activities':    hot_activities,
                   'today_activities':  today_activities,
                   'shortcuts_map':     shortcuts_map,
                  }
                 )

@lw_exceptions
@login_required
def persons_portal(request):
    #TODO: populate employers
    user = request.user
    cred_filter = partial(EntityCredentials.filter, user)

    return render(request, 'mobile/directory.html',
                  {'favorite_contacts': cred_filter(Contact.objects.filter(is_deleted=False,
                                                                           mobile_favorite__user=user,
                                                                          )
                                                   ),
                    'contact_model': Contact,

                    'favorite_organisations': cred_filter(Organisation.objects.filter(is_deleted=False,
                                                                                      mobile_favorite__user=user,
                                                                                     )
                                                         ),
                    'orga_model': Organisation,
                  }
                 )

@lw_exceptions
@login_required
@permission_required('persons.add_contact')
def create_contact(request):
    last_name = request.GET.get('last_name')

    return add_entity(request, MobileContactCreateForm,
                      url_redirect='/mobile/persons',
                      template='mobile/add_contact.html',
                      extra_initial={'last_name': last_name.title()} if last_name else None,
                     )

@lw_exceptions
@login_required
@permission_required('persons.add_organisation')
def create_organisation(request):
    name = request.GET.get('name')

    return add_entity(request, MobileOrganisationCreateForm,
                      url_redirect='/mobile/persons',
                      template='mobile/add_orga.html',
                      extra_initial={'name': name.title()} if name else None,
                     )

@lw_exceptions
@login_required
def search_person(request):
    search = get_from_GET_or_404(request.GET, 'search')

    if len(search) < 3:
        raise ConflictError(_('Your search is too short.')) #TODO: client-side validation

    #TODO: populate employers
    contacts = EntityCredentials.filter(
            request.user,
            Contact.objects.exclude(is_deleted=True)
                           .filter(Q(first_name__icontains=search) |
                                   Q(last_name__icontains=search) |
                                   Q(relations__type__in=(REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES),
                                     relations__object_entity__header_filter_search_field__icontains=search,
                                    )
                                  )
                           .distinct()
        )[:30]

    orgas = EntityCredentials.filter(
            request.user,
            Organisation.objects.exclude(is_deleted=True)
                                .filter(name__icontains=search)
        )[:30]

    return render(request, 'mobile/search.html',
                  {'search':        search,

                   'contacts':      contacts,
                   'contact_model': Contact,

                   'organisations': orgas,
                   'orga_model':    Organisation,
                  }
                 )

def _get_page_url(request):
  return request.META.get('HTTP_REFERER', '/mobile/')

@lw_exceptions
@login_required
@POST_only
def start_activity(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)

    request.user.has_perm_to_change_or_die(activity)

    activity.start = now()

    if not activity.end or activity.start >= activity.end:
        activity.end = activity.start + activity.type.as_timedelta()

    activity.floating_type = NARROW
    activity.status_id = STATUS_IN_PROGRESS
    activity.save()

    return HttpResponseRedirect('%s#activity_%s' % (_get_page_url(request), activity_id))

@lw_exceptions
@login_required
@POST_only
def stop_activity(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)

    request.user.has_perm_to_change_or_die(activity)

    now_val = now()

    if activity.start > now_val:
        raise ConflictError("This activity cannot be stopped before it is started.")

    activity.end = now_val
    activity.status_id = STATUS_DONE
    activity.save()

    return HttpResponseRedirect(_get_page_url(request))

@lw_exceptions
@login_required
def activities_portal(request):
    user = request.user
    cred_filter = partial(EntityCredentials.filter, user)
    now_val = now()
    activities = Activity.objects.filter(is_deleted=False,
                                         relations__type=REL_OBJ_PART_2_ACTIVITY,
                                         relations__object_entity=user.linked_contact,
                                        ) \
                                 .exclude(status__in=(STATUS_DONE, STATUS_CANCELLED)) \
                                 .order_by('start')

    phone_calls = cred_filter(activities.filter(type=ACTIVITYTYPE_PHONECALL,
                                                start__lte=now_val,
                                               )
                             )[:10]

    floating_qs = cred_filter(activities.filter(floating_type=FLOATING).order_by('title'))
    floating = floating_qs[:FLOATING_SIZE]
    floating_count = len(floating)

    if floating_count == FLOATING_SIZE: #NB: max size is reached ; we are obliged to make a query to know the real count
        floating_count = floating_qs.count()

    #tomorrow = now_val + timedelta(days=1)
    #build_dt = lambda h, m, s: make_aware_dt(datetime.combine(tomorrow, time(hour=h, minute=m, second=s)))
    tomorrow = localtime(now_val + timedelta(days=1))
    build_dt = lambda h, m, s: datetime(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day,
                                        hour=h, minute=m, second=s,
                                        tzinfo=tomorrow.tzinfo
                                       )
    tomorrow_act = cred_filter(activities.filter(start__range=(build_dt(0,  0,  0),
                                                               build_dt(23, 59, 59),
                                                              ),
                                                )
                              )

    #TODO: populate participants (regroup queries for Relation + real entities) ??

    return render(request, 'mobile/activities.html',
                  {'phone_calls':               phone_calls,

                   'floating_activities':       floating,
                   'floating_activities_count': floating_count,

                   'tomorrow_activities':       tomorrow_act,
                   'tomorrow':                  tomorrow,
                  }
                 )

def _build_date_or_404(date_str):
    try:
        return get_dt_from_json_str(date_str)
    except ValueError as e:
        raise Http404(e)

@login_required
@lw_ajax_exceptions #TODO: remove and send popup with a close button instead
def phonecall_panel(request):
    user = request.user

    GET = request.GET
    call_start = _build_date_or_404(get_from_GET_or_404(GET, 'call_start'))
    person_id  = get_from_GET_or_404(GET, 'person_id')
    number     = get_from_GET_or_404(GET, 'number')

    context = {'type_id':         ACTIVITYTYPE_PHONECALL,
               'call_start':      call_start,
               'number':          number,
               'user_contact_id': user.linked_contact.id,
              }

    pcall = None
    pcall_id = GET.get('pcall_id')
    if pcall_id is not None:
        context['phone_call'] = pcall = get_object_or_404(Activity, id=pcall_id,
                                                          type_id=ACTIVITYTYPE_PHONECALL,
                                                        )
        user.has_perm_to_view_or_die(pcall)

        context['participant_contacts'] = [r.object_entity.get_real_entity()
                                              for r in pcall.get_participant_relations()
                                          ]
        context['participant_organisations'] = list(orga_subjects(pcall))

    person = get_object_or_404(CremeEntity, pk=person_id).get_real_entity()
    user.has_perm_to_view_or_die(person)

    if isinstance(person, Contact):
        context['called_contact'] = person

        if not pcall:
          context['participant_contacts'] = [person]
    elif isinstance(person, Organisation):
        context['called_orga'] = person

        if not pcall:
          context['participant_organisations'] = [person]
    else:
        raise Http404('"person_id" must be the ID of a Contact/Organisation')

    return render(request, 'mobile/workflow_panel.html', context)

def _get_pcall(request):
    pcall_id = request.POST.get('pcall_id')

    if pcall_id is None:
        return None

    pcall = get_object_or_404(Activity, id=pcall_id, type_id=ACTIVITYTYPE_PHONECALL)

    request.user.has_perm_to_change_or_die(pcall)

    return pcall

@login_required
@POST_only
def phonecall_workflow_done(request, pcall_id):
    pcall = get_object_or_404(Activity,
                              type_id=ACTIVITYTYPE_PHONECALL,
                              id=pcall_id,
                             )

    request.user.has_perm_to_change_or_die(pcall)

    pcall.status_id = STATUS_DONE
    pcall.save()

    return HttpResponseRedirect(_get_page_url(request))

def _get_person_or_404(person_id, user):
    person = get_object_or_404(CremeEntity, pk=person_id).get_real_entity()
    user.has_perm_to_view_or_die(person) #TODO: test

    if not isinstance(person, (Contact, Organisation)):
        raise Http404('"person_id" must be the ID of a Contact/Organisation')

    return person

def _get_participants(user, POST):
    me = user.linked_contact
    user.has_perm_to_link_or_die(me)

    person_id = get_from_POST_or_404(POST, 'person_id', int)

    if person_id == me.id:
        raise ConflictError(_('You cannot create a call to youself.'))

    person = _get_person_or_404(person_id, user)
    user.has_perm_to_link_or_die(person)

    return me, person

#TODO: factorise with activities.form
def _add_participants(activity, persons):
    create_relation = partial(Relation.objects.create,
                              subject_entity=activity, user=activity.user,
                              #type_id=REL_OBJ_PART_2_ACTIVITY TODO: when orga can participate
                             )

    #TODO: when orga can participate
    for person in persons:
        if isinstance(person, Contact):
            create_relation(object_entity=person, type_id=REL_OBJ_PART_2_ACTIVITY)

            #TODO: we should move this in a signal in activities
            if person.is_user:
              activity.calendars.add(Calendar.get_user_default_calendar(person.is_user))
        else:
            create_relation(object_entity=person, type_id=REL_OBJ_ACTIVITY_SUBJECT)

@login_required
@POST_only
@jsonify
def _phonecall_workflow_set_end(request, end_function):
    POST = request.POST
    start = _build_date_or_404(get_from_POST_or_404(POST, 'call_start')) #TODO: assert in the past
    end   = end_function(start)

    pcall = _get_pcall(request)

    if pcall is not None:
        pcall.status_id = STATUS_DONE
        pcall.start = start
        pcall.end = end
        pcall.save()
    else:
        user = request.user
        user.has_perm_to_create_or_die(Activity)

        me, person = _get_participants(user, POST)

        with commit_on_success():
            pcall = Activity.objects.create(user=user,
                                            title=_('%(status)s call to %(person)s from Creme Mobile') % {
                                                    'status': _('Successful'),
                                                    'person': person,
                                                },
                                            type_id=ACTIVITYTYPE_PHONECALL,
                                            sub_type_id=ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
                                            status_id=STATUS_DONE,
                                            start=start,
                                            end=end,
                                           )
            _add_participants(pcall, (me, person))

    return ''

def phonecall_workflow_lasted_5_minutes(request):
    return _phonecall_workflow_set_end(request,
                                       lambda start: min(now(), start + timedelta(minutes=5))
                                      )

def phonecall_workflow_just_done(request):
    return _phonecall_workflow_set_end(request, lambda start: now())

def _create_failed_pcall(request):
    POST = request.POST
    start = _build_date_or_404(get_from_POST_or_404(POST, 'call_start'))

    user = request.user
    user.has_perm_to_create_or_die(Activity)

    me, person = _get_participants(user, POST)

    with commit_on_success():
        pcall = Activity.objects.create(user=user,
                                        title=_('%(status)s call to %(person)s from Creme Mobile') % {
                                                'status': _('Failed'),
                                                'person':  person,
                                            },
                                        type_id=ACTIVITYTYPE_PHONECALL,
                                        sub_type_id=ACTIVITYSUBTYPE_PHONECALL_FAILED,
                                        status_id=STATUS_DONE,
                                        start=start,
                                        end=start,
                                       )
        _add_participants(pcall, (me, person))

    return pcall, me, person

def _set_pcall_as_failed(pcall, request):
    pcall.sub_type_id = ACTIVITYSUBTYPE_PHONECALL_FAILED
    pcall.status_id = STATUS_DONE
    pcall.floating_type = NARROW
    pcall.start = pcall.end = _build_date_or_404(get_from_POST_or_404(request.POST, 'call_start'))

    pcall.save()

@login_required
@POST_only
@jsonify
def phonecall_workflow_failed(request):
    pcall = _get_pcall(request)

    if pcall is not None:
        _set_pcall_as_failed(pcall, request)
    else:
        _create_failed_pcall(request)

    return ''

@login_required
@POST_only
@jsonify
@commit_on_success
def phonecall_workflow_postponed(request):
    pcall = _get_pcall(request)

    if pcall is not None:
        postponed = copy(pcall) #NB: we avoid a double save here (clone() + save()) by modifying our live copy before cloning

        _set_pcall_as_failed(pcall, request)
    else:
        pcall, me, person = _create_failed_pcall(request)

        postponed = copy(pcall) #NB: idem
        postponed.title = _('Call to %s from Creme Mobile') % person
        postponed.sub_type_id = ACTIVITYSUBTYPE_PHONECALL_OUTGOING
        postponed.status = None

    postponed.floating_type = FLOATING_TIME

    tomorrow = now() + timedelta(days=1)
    dt_combine = datetime.combine
    postponed.start = make_aware_dt(dt_combine(tomorrow, time(hour=0,  minute=0)))
    postponed.end   = make_aware_dt(dt_combine(tomorrow, time(hour=23, minute=59)))

    postponed.clone()

    return ''

@login_required
@POST_only
def mark_as_favorite(request, entity_id):
    entity = get_object_or_404(CremeEntity, id=entity_id)
    user = request.user

    user.has_perm_to_view_or_die(entity)
    MobileFavorite.objects.get_or_create(entity=entity, user=user)

    return HttpResponse()

@login_required
@POST_only
def unmark_favorite(request, entity_id):
    MobileFavorite.objects.filter(entity=entity_id, user=request.user).delete()

    return HttpResponse()
