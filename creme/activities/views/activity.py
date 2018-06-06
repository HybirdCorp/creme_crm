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

from datetime import datetime
from functools import partial
# import warnings

from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.models import CremeEntity, RelationType
from creme.creme_core.utils import get_from_GET_or_404, jsonify
from creme.creme_core.views import generic
from creme.creme_core.views.utils import build_cancel_path

from creme.persons import get_contact_model

from .. import get_activity_model, constants
from ..forms import activity as act_forms
from ..models import ActivityType, ActivitySubType
from ..utils import get_ical


Activity = get_activity_model()
_CREATION_PERM_STR = cperm(Activity)


def _add_activity(request, form_class,
                  content_template='activities/frags/activity_form_content.html',
                  type_id=None, **form_args):
    if request.method == 'POST':
        POST = request.POST
        form = form_class(activity_type_id=type_id, user=request.user, data=POST, **form_args)

        if form.is_valid():
            form.save()
            entity = form_args.get('related_entity', form.instance)

            return redirect(entity)

        cancel_url = POST.get('cancel_url')
    else:
        form = form_class(activity_type_id=type_id, user=request.user, **form_args)
        cancel_url = build_cancel_path(request)

    return render(request, 'activities/add_activity_form.html',
                  {'form':             form,
                   'title':            Activity.get_creation_title(type_id),
                   'content_template': content_template,
                   'submit_label':     Activity.save_label,
                   'cancel_url':       cancel_url,
                  },
                 )


_TYPES_MAP = {
        'meeting':   constants.ACTIVITYTYPE_MEETING,
        'phonecall': constants.ACTIVITYTYPE_PHONECALL,
        'task':      constants.ACTIVITYTYPE_TASK,
    }


def abstract_add_activity(request, act_type=None, form=act_forms.ActivityCreateForm):
    if act_type is None:
        type_id = None
    else:
        type_id = _TYPES_MAP.get(act_type)

        if not type_id:
            raise Http404('No activity type matches with: {}'.format(act_type))

    return _add_activity(request, form, type_id=type_id)


def abstract_add_unavailability(request, form=act_forms.IndisponibilityCreateForm,
                                content='activities/frags/indispo_form_content.html',
                               ):
    return _add_activity(request, form, content_template=content,
                         type_id=constants.ACTIVITYTYPE_INDISPO,
                        )


def abstract_add_related_activity(request, entity_id, form=act_forms.RelatedActivityCreateForm):
    act_type_id = request.GET.get('activity_type')
    entity = get_object_or_404(CremeEntity, pk=entity_id).get_real_entity()

    if act_type_id:
        get_object_or_404(ActivityType, pk=act_type_id)

    request.user.has_perm_to_link_or_die(entity)

    if isinstance(entity, get_contact_model()):
        rtype_id = constants.REL_SUB_PART_2_ACTIVITY
    else:
        rtype = RelationType.objects.get(pk=constants.REL_SUB_ACTIVITY_SUBJECT)

        if rtype.is_compatible(entity.entity_type_id):
            rtype_id = constants.REL_SUB_ACTIVITY_SUBJECT
        else:
            rtype_id = constants.REL_SUB_LINKED_2_ACTIVITY  # Not custom, & all ContentTypes should be accepted

    return _add_activity(request, form,
                         related_entity=entity,
                         relation_type_id=rtype_id,
                         type_id=act_type_id,
                        )


def abstract_add_activity_popup(request, form=act_forms.CalendarActivityCreateForm,
                                template='activities/add_popup_activity_form.html',
                                title=_(u'New activity'),
                                submit_label=Activity.save_label,
                               ):
    if request.method == 'POST':
        form_instance = form(user=request.user, data=request.POST,
                             files=request.FILES or None,
                            )

        if form_instance.is_valid():
            form_instance.save()
    else:
        get_or_404 = partial(get_from_GET_or_404, GET=request.GET, cast=int)
        today = datetime.today()
        start_date = datetime(get_or_404(key='year',   default=today.year),
                              get_or_404(key='month',  default=today.month),
                              get_or_404(key='day',    default=today.day),
                              get_or_404(key='hour',   default=today.hour),
                              get_or_404(key='minute', default=today.minute),
                             )
        form_instance = form(start=start_date, user=request.user)

    return generic.inner_popup(request, template,
                               {'form': form_instance,
                                'title': title,
                                'submit_label': submit_label,
                                # TODO: content_template ?? (see template)
                               },
                               is_valid=form_instance.is_valid(),
                               reload=False,
                               delegate_reload=True,
                              )


def abstract_edit_activity(request, activity_id, model=Activity, form=act_forms.ActivityEditForm):
    return generic.edit_entity(request, activity_id, model, form)


def abstract_view_activity(request, activity_id,
                           template='activities/view_activity.html',
                          ):
    return generic.view_entity(request, activity_id, model=Activity, template=template)


def abstract_view_activity_popup(request, activity_id,
                                 template='activities/view_activity_popup.html',
                                ):
    return generic.view_entity(request, activity_id, model=Activity, template=template)


@login_required
@permission_required(('activities', _CREATION_PERM_STR))
def add(request, act_type=None):
    return abstract_add_activity(request, act_type)


@login_required
@permission_required(('activities', _CREATION_PERM_STR))
def add_indisponibility(request):
    return abstract_add_unavailability(request)


@login_required
@permission_required(('activities', _CREATION_PERM_STR))
def add_related(request, entity_id):
    return abstract_add_related_activity(request, entity_id)


@login_required
@permission_required(('activities', _CREATION_PERM_STR))
def add_popup(request):
    return abstract_add_activity_popup(request)


@login_required
@permission_required('activities')
def edit(request, activity_id):
    return abstract_edit_activity(request, activity_id)


@login_required
@permission_required('activities')
def detailview(request, activity_id):
    return abstract_view_activity(request, activity_id)


@login_required
@permission_required('activities')
def popupview(request, activity_id):
    return abstract_view_activity_popup(request, activity_id)


@login_required
@permission_required('activities')
def listview(request, type_id=None):
    kwargs = {}

    if type_id:
        # TODO: change 'add' button too ??
        kwargs['extra_q'] = Q(type=type_id)

    return generic.list_view(request, Activity, hf_pk=constants.DEFAULT_HFILTER_ACTIVITY,
                             extra_dict={'extra_bt_templates': ('activities/frags/ical_list_view_button.html', )},
                             **kwargs
                            )


@login_required
@permission_required('activities')
# def download_ical(request, ids=None):
def download_ical(request):
    # if ids is not None:
    #     warnings.warn('download_ical(): the URL argument "ids" is deprecated ; '
    #                   'use the GET parameter "id" instead.',
    #                   DeprecationWarning
    #                  )
    #     act_ids = ids.split(',')
    # else:
    #     act_ids = request.GET.getlist('id')
    act_ids = request.GET.getlist('id')

    # TODO: is_deleted=False ??
    activities = EntityCredentials.filter(queryset=Activity.objects.filter(pk__in=act_ids),
                                          user=request.user,
                                         )
    response = HttpResponse(get_ical(activities), content_type='text/calendar')
    response['Content-Disposition'] = 'attachment; filename=Calendar.ics'

    return response


@jsonify
@login_required
def get_types(request, type_id):
    if not type_id:
        return []

    get_object_or_404(ActivityType, pk=type_id)

    return list(ActivitySubType.objects.filter(type=type_id).values_list('id', 'name'))
