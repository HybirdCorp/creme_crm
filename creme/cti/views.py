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

from datetime import timedelta # datetime

from django.db.models.query_utils import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.models import CremeEntity, RelationType, Relation, EntityCredentials
from creme.creme_core.views.generic import add_entity
from creme.creme_core.utils import jsonify, get_from_POST_or_404, get_from_GET_or_404

from creme.persons.models import Contact, Organisation
from creme.persons.forms.contact import ContactForm
from creme.persons.forms.organisation import OrganisationForm

from creme.activities.models import Activity, Calendar
from creme.activities.constants import (ACTIVITYTYPE_PHONECALL,
                                        ACTIVITYSUBTYPE_PHONECALL_INCOMING,
                                        ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
                                        STATUS_IN_PROGRESS, REL_SUB_PART_2_ACTIVITY,
                                        REL_SUB_LINKED_2_ACTIVITY)


def _build_phonecall(user, entity_id, calltype_id, title_format):
    entity = get_object_or_404(CremeEntity, pk=entity_id)

    user.has_perm_to_link_or_die(entity)

    user.has_perm_to_create_or_die(Activity)

    user_contact = get_object_or_404(Contact, is_user=user)
    entity = entity.get_real_entity()
    now_value = now()
    pcall = Activity.objects.create(user=user,
                                     title=title_format % entity,
                                     type_id=ACTIVITYTYPE_PHONECALL,
                                     description=_(u'Automatically created by CTI'),
                                     status_id=STATUS_IN_PROGRESS,
                                     sub_type_id=calltype_id,
                                     start=now_value,
                                     end=now_value + timedelta(minutes=5),
                                    )

    pcall.calendars.add(Calendar.get_user_default_calendar(user))

    # if the entity is a contact with related user, should add the phone call to his calendar
    if isinstance(entity, Contact) and entity.is_user:
        pcall.calendars.add(Calendar.get_user_default_calendar(entity.is_user))

    #TODO: link credentials
    caller_rtype = REL_SUB_PART_2_ACTIVITY
    entity_rtype = REL_SUB_PART_2_ACTIVITY if isinstance(entity, Contact) else REL_SUB_LINKED_2_ACTIVITY
    rtypes_ids   = set((caller_rtype, entity_rtype))

    rtypes_map = RelationType.objects.in_bulk(rtypes_ids)
    if len(rtypes_map) != len(rtypes_ids):
        raise Http404('An activities RelationType does not exists !!')

    rel_create = Relation.objects.create

    if entity.pk != user_contact.pk:
        rel_create(subject_entity=user_contact, type=rtypes_map[caller_rtype], object_entity=pcall, user=user)
    rel_create(subject_entity=entity, type=rtypes_map[entity_rtype], object_entity=pcall, user=user)

    return pcall

@jsonify
@login_required
def create_phonecall_as_caller(request):
    pcall = _build_phonecall(request.user,
                             get_from_POST_or_404(request.POST, 'entity_id'),
                             ACTIVITYSUBTYPE_PHONECALL_OUTGOING,
                             _(u'Call to %s')
                            )

    return u'%s<br/><a href="%s">%s</a>' % (
                    _(u'Phone call successfully created.'),
                    pcall.get_absolute_url(),
                    unicode(pcall),
                )

@login_required
def respond_to_a_call(request):
    number = get_from_GET_or_404(request.GET, 'number')
    user = request.user
    filter_viewable = EntityCredentials.filter

    callers = list(filter_viewable(user, Contact.objects.filter(Q(phone=number) | Q(mobile=number))))
    callers.extend(filter_viewable(user, Organisation.objects.filter(phone=number)))

    can_create = user.has_perm_to_create

    return render(request, 'cti/respond_to_a_call.html',
                  {'callers':              callers,
                   'number':               number,
                   'can_create_contact':   can_create(Contact),
                   'can_create_orga':      can_create(Organisation),
                   'can_create_activity':  can_create(Activity),
                  }
                 )

@login_required
@permission_required('persons')
@permission_required('persons.add_contact')
def add_contact(request, number):
    return add_entity(request, ContactForm,
                      template="persons/add_contact_form.html",
                      extra_initial={'phone': number}
                     )

@login_required
@permission_required('persons')
@permission_required('persons.add_organisation')
def add_orga(request, number):
    return add_entity(request, OrganisationForm,
                      template="persons/add_organisation_form.html",
                      extra_initial={'phone': number}
                     )

@login_required
@permission_required('activities')
@permission_required('activities.add_activity')
def add_phonecall(request, entity_id):
    pcall = _build_phonecall(request.user, entity_id, ACTIVITYSUBTYPE_PHONECALL_INCOMING, _(u'Call from %s'))

    return HttpResponseRedirect(pcall.get_absolute_url())
