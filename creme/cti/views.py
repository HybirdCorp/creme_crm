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

from datetime import timedelta
from functools import partial

from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.timezone import now
from django.utils.translation import ugettext as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity, RelationType, Relation
from creme.creme_core.utils import jsonify, get_from_POST_or_404, get_from_GET_or_404
from creme.creme_core.views.bricks import build_context, bricks_render_info
from creme.creme_core.views.generic import add_entity

from creme import persons
from creme.persons.forms.contact import ContactForm
from creme.persons.forms.organisation import OrganisationForm

from creme import activities
from creme.activities import constants as act_constants
from creme.activities.models import Calendar

from .bricks import CallersBrick

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()
Activity = activities.get_activity_model()

RESPOND_TO_A_CALL_MODELS = (Contact, Organisation)  # TODO: move to bricks.py ?


def _create_phonecall(user, title, calltype_id):
    now_value = now()
    return Activity.objects.create(user=user,
                                   title=title,
                                   description=_(u'Automatically created by CTI'),
                                   status_id=act_constants.STATUS_IN_PROGRESS,
                                   type_id=act_constants.ACTIVITYTYPE_PHONECALL,
                                   sub_type_id=calltype_id,
                                   start=now_value,
                                   end=now_value + timedelta(minutes=5),
                                  )


def abstract_create_phonecall_as_caller(request, pcall_creator=_create_phonecall):
    pcall = _build_related_phonecall(request.user,
                                     get_from_POST_or_404(request.POST, 'entity_id'),
                                     act_constants.ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
                                     # _(u'Call to %s'),
                                     _(u'Call to {entity}'),
                                     pcall_creator=pcall_creator,
                                    )

    return format_html(u'{msg}<br/><a href="{url}">{pcall}</a>',
                       msg=_(u'Phone call successfully created.'),
                       url=pcall.get_absolute_url(),
                       pcall=pcall,
                      )


def abstract_add_contact(request, number, form=ContactForm,
                         template='persons/add_contact_form.html',
                        ):
    return add_entity(request, form, template=template,
                      extra_initial={'phone': number},
                     )


def abstract_add_organisation(request, number, form=OrganisationForm,
                              template='persons/add_organisation_form.html',
                              ):
    return add_entity(request, form, template=template,
                      extra_initial={'phone': number},
                     )


def abstract_add_phonecall(request, entity_id, pcall_creator=_create_phonecall):
    pcall = _build_related_phonecall(request.user, entity_id,
                                     act_constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING,
                                     # _(u'Call from %s'),
                                     _(u'Call from {entity}'),
                                     pcall_creator=pcall_creator,
                                    )

    return redirect(pcall)


def _build_related_phonecall(user, entity_id, calltype_id, title_format, pcall_creator=_create_phonecall):
    entity = get_object_or_404(CremeEntity, pk=entity_id)

    user.has_perm_to_link_or_die(entity)
    user.has_perm_to_create_or_die(Activity)

    entity = entity.get_real_entity()
    # pcall = pcall_creator(user, title=title_format % entity, calltype_id=calltype_id)
    pcall = pcall_creator(user, title=title_format.format(entity=entity), calltype_id=calltype_id)

    pcall.calendars.add(Calendar.get_user_default_calendar(user))

    # If the entity is a contact with related user, should add the phone call to his calendar
    if isinstance(entity, Contact) and entity.is_user:
        pcall.calendars.add(Calendar.get_user_default_calendar(entity.is_user))

    # TODO: link credentials
    caller_rtype = act_constants.REL_SUB_PART_2_ACTIVITY
    entity_rtype = act_constants.REL_SUB_PART_2_ACTIVITY if isinstance(entity, Contact) else \
                   act_constants.REL_SUB_LINKED_2_ACTIVITY
    rtypes_ids   = {caller_rtype, entity_rtype}

    rtypes_map = RelationType.objects.in_bulk(rtypes_ids)
    if len(rtypes_map) != len(rtypes_ids):
        raise Http404('An activities RelationType does not exists !!')

    user_contact = user.linked_contact
    rel_create = partial(Relation.objects.create, object_entity=pcall, user=user)

    if entity.pk != user_contact.pk:
        rel_create(subject_entity=user_contact, type=rtypes_map[caller_rtype])
    rel_create(subject_entity=entity, type=rtypes_map[entity_rtype])

    return pcall


@jsonify
@login_required
def create_phonecall_as_caller(request):
    return abstract_create_phonecall_as_caller(request)


@login_required
def respond_to_a_call(request):
    number = get_from_GET_or_404(request.GET, 'number')

    return render(request, 'cti/respond_to_a_call.html',
                  {'number':            number,
                   'bricks_reload_url': reverse('cti__reload_callers_brick', args=(number,)),
                  }
                 )


@login_required
@jsonify
def reload_callers_brick(request, number):
    return bricks_render_info(request, bricks=[CallersBrick()],
                              context=build_context(request, number=number),
                             )


@login_required
@permission_required(('persons', cperm(Contact)))
def add_contact(request, number):
    return abstract_add_contact(request, number)


@login_required
@permission_required(('persons', cperm(Organisation)))
def add_orga(request, number):
    return abstract_add_organisation(request, number)


@login_required
@permission_required(('activities', cperm(Activity)))
def add_phonecall(request, entity_id):
    return abstract_add_phonecall(request, entity_id)
