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

from django.utils.translation import ugettext as _
from django.forms import ModelMultipleChoiceField
from django.forms.widgets import CheckboxSelectMultiple
from django.contrib.auth.models import User

from creme.activities.forms.activity import ActivityCreateForm

from .constants import PRIO_NOT_IMP_PK
from .models import UserMessage


def add_users_field(form):
    form.fields['informed_users'] = ModelMultipleChoiceField(queryset=User.objects.all(),
                                                             widget=CheckboxSelectMultiple(),
                                                             required=False, label=_(u"Users"),
                                                            )

    form.blocks = form.blocks.new(('informed_users', _(u'Users to keep informed'), ['informed_users']))

def save_users_field(form):
    cdata     = form.cleaned_data
    raw_users = cdata['informed_users']

    if not raw_users:
        return

    activity = form.instance
    title    = _(u'[Creme] Activity created: %s') % activity
    body     = _(u"""A new activity has been created: %(activity)s.
    Description: %(description)s.
    Start: %(start)s.
    End: %(end)s.
    Subjects: %(subjects)s.
    Participants: %(participants)s.""") % {
            'activity':     activity,
            'description':  activity.description,
            'start':        activity.start,
            'end':          activity.end,
            'subjects':     u' / '.join(unicode(e) for e in cdata['subjects']),
            'participants': u' / '.join(unicode(c) for c in form.participants),
        }

    UserMessage.create_messages(raw_users, title, body, PRIO_NOT_IMP_PK, activity.user, activity) #TODO: sender = the real user that created the activity ???


ActivityCreateForm.add_post_init_callback(add_users_field)
ActivityCreateForm.add_post_save_callback(save_users_field)
