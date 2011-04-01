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

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required

from creme_core.models import CremeEntity, RelationType, Relation
from creme_core.utils import jsonify, get_from_POST_or_404

from persons.models import Contact

from activities.models import Activity, Status, PhoneCall, PhoneCallType, Calendar, CalendarActivityLink
from activities.constants import (PHONECALLTYPE_OUTGOING, STATUS_IN_PROGRESS,
                                  REL_SUB_PART_2_ACTIVITY, REL_SUB_LINKED_2_ACTIVITY)


@jsonify
@login_required
def add_phonecall(request):
    entity = get_object_or_404(CremeEntity, pk=get_from_POST_or_404(request.POST, 'entity_id'))
    user = request.user

    entity.can_link_or_die(user)

    user.has_perm_to_create_or_die(Activity) #TODO: PhoneCall instead ???

    user_contact = get_object_or_404(Contact, is_user=user)
    callee = entity.get_real_entity()
    now = datetime.now()
    pcall = PhoneCall.objects.create(user=user,
                                     title=_(u'Call to %s') % callee,
                                     description=_(u'Automatically created by CTI'),
                                     status=get_object_or_404(Status, pk=STATUS_IN_PROGRESS),
                                     call_type=get_object_or_404(PhoneCallType, pk=PHONECALLTYPE_OUTGOING),
                                     start=now,
                                     end=now + timedelta(minutes=5),
                                    )

    CalendarActivityLink.objects.create(calendar=Calendar.get_user_default_calendar(user), activity_id=pcall.id)

    #TODO: link credentials
    caller_rtype = REL_SUB_PART_2_ACTIVITY
    callee_rtype = REL_SUB_PART_2_ACTIVITY if isinstance(callee, Contact) else REL_SUB_LINKED_2_ACTIVITY
    rtypes_ids   =  set((caller_rtype, callee_rtype))

    rtypes_map = RelationType.objects.in_bulk(rtypes_ids)
    if len(rtypes_map) != len(rtypes_ids):
        raise Http404('An activities RelationType does not exists !!')

    rel_create = Relation.objects.create
    rel_create(subject_entity=user_contact, type=rtypes_map[caller_rtype], object_entity=pcall, user=user)
    rel_create(subject_entity=callee,       type=rtypes_map[callee_rtype], object_entity=pcall, user=user)

    return _(u'Phone call successfully created.') + u'<br/><a href="%s">%s</a>' % (pcall.get_absolute_url(), unicode(pcall))
