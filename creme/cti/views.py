# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from datetime import datetime, timedelta

from django.db.models.query_utils import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.models import CremeEntity, RelationType, Relation, EntityCredentials
from creme_core.views.generic import add_entity
from creme_core.utils import jsonify, get_from_POST_or_404, get_from_GET_or_404

from persons.models import Contact, Organisation
from persons.forms.contact import ContactForm
from persons.forms.organisation import OrganisationForm

from activities.models import Activity, Status, PhoneCall, PhoneCallType, Calendar, CalendarActivityLink
from activities import constants


def _build_phonecall(user, entity_id, calltype_id, title_format):
    entity = get_object_or_404(CremeEntity, pk=entity_id)

    entity.can_link_or_die(user)

    user.has_perm_to_create_or_die(Activity) #TODO: PhoneCall instead ???

    user_contact = get_object_or_404(Contact, is_user=user)
    entity = entity.get_real_entity()
    now = datetime.now()
    pcall = PhoneCall.objects.create(user=user,
                                     title=title_format % entity,
                                     description=_(u'Automatically created by CTI'),
                                     status=get_object_or_404(Status, pk=constants.STATUS_IN_PROGRESS),
                                     call_type=get_object_or_404(PhoneCallType, pk=calltype_id),
                                     start=now,
                                     end=now + timedelta(minutes=5),
                                    )

    CalendarActivityLink.objects.create(calendar=Calendar.get_user_default_calendar(user), activity_id=pcall.id)

    #TODO: link credentials
    caller_rtype = constants.REL_SUB_PART_2_ACTIVITY
    entity_rtype = constants.REL_SUB_PART_2_ACTIVITY if isinstance(entity, Contact) else constants.REL_SUB_LINKED_2_ACTIVITY
    rtypes_ids   =  set((caller_rtype, entity_rtype))

    rtypes_map = RelationType.objects.in_bulk(rtypes_ids)
    if len(rtypes_map) != len(rtypes_ids):
        raise Http404('An activities RelationType does not exists !!')

    rel_create = Relation.objects.create
    rel_create(subject_entity=user_contact, type=rtypes_map[caller_rtype], object_entity=pcall, user=user)
    rel_create(subject_entity=entity,       type=rtypes_map[entity_rtype], object_entity=pcall, user=user)

    return pcall

@jsonify
@login_required
def create_phonecall_as_caller(request):
    pcall = _build_phonecall(request.user,
                             get_from_POST_or_404(request.POST, 'entity_id'),
                             constants.PHONECALLTYPE_OUTGOING,
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

    return render_to_response('cti/respond_to_a_call.html',
                              {
                                'callers':              callers,
                                'number':               number,
                                'can_create_contact':   can_create(Contact),
                                'can_create_orga':      can_create(Organisation),
                                'can_create_activity':  can_create(Activity),
                              },
                              context_instance=RequestContext(request)
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
    pcall = _build_phonecall(request.user, entity_id, constants.PHONECALLTYPE_INCOMING, _(u'Call from %s'))

    return HttpResponseRedirect(pcall.get_absolute_url())
