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

from django.http import HttpResponse
from django.utils.simplejson.encoder import JSONEncoder
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType
from creme_core.utils import get_from_POST_or_404

from persons.models.contact import Contact

from activities.constants import REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY


#TODO: use the more generic system existing in creme_core for relations (that filter relation type with contenttype) ?????

_RTYPE_CHOICES = { #key means 'can participate'
        True:  (REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY),
        False: (REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY),
    }
_CONTACT_CT_ID = ContentType.objects.get_for_model(Contact).id

#TODO: why not GET ??
@login_required
def get_relationtype_choices(request):
    can_part = bool(get_from_POST_or_404(request.POST, 'ct_id', int) == _CONTACT_CT_ID)
#    data = list(RelationType.objects.filter(pk__in=_RTYPE_CHOICES[can_part]).values('pk', 'predicate'))
    
    choices = _RTYPE_CHOICES[can_part]
    query_dict = dict(RelationType.objects.filter(pk__in=choices).values_list('pk', 'predicate'))
    data = [{'pk': pk, 'predicate': query_dict[pk]} for pk in choices]
    return HttpResponse(JSONEncoder().encode(data), mimetype='text/javascript')
