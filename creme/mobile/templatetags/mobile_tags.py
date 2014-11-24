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

import re

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.template import Library

from creme.persons.constants import REL_OBJ_EMPLOYED_BY, REL_OBJ_MANAGES
from creme.persons.models import Organisation

from creme.activities.constants import (STATUS_IN_PROGRESS, NARROW,
        ACTIVITYTYPE_PHONECALL, REL_SUB_ACTIVITY_SUBJECT)


register = Library()

_DOCUMENT_CLASSES = [
        (re.compile('Android',          re.I), 'android'),
        (re.compile('iPhone|iPad|iPod', re.I), 'ios'),
    ]

@register.simple_tag
def document_class(request):
    agent = request.META.get('HTTP_USER_AGENT')

    if agent is not None:
        for regex, class_name in _DOCUMENT_CLASSES:
            if regex.search(agent) is not None:
                return class_name

    return 'all'

_EMPLOYERS_RTYPE_IDS = (REL_OBJ_EMPLOYED_BY, REL_OBJ_MANAGES)

#TODO: improve Contact.get_employers() ? Add a method Contact.get_managed_orga() ?
#TODO: pre-populate ?
@register.filter #TODO: factorise with field_printers ?
def employers(contact):
    return Organisation.objects.filter(relations__type__in=_EMPLOYERS_RTYPE_IDS,
                                       relations__object_entity=contact.id,
                                      )

#TODO: remove when Organisation can participate
@register.filter
def orga_subjects(activity):
    return Organisation.objects.filter(relations__type=REL_SUB_ACTIVITY_SUBJECT,
                                       relations__object_entity=activity.id,
                                      )


START_STOP_BUTTONS  = 'start-stop'
NO_BUTTON           = 'no-button'

_BUTTONS = {
    START_STOP_BUTTONS: 'mobile/frags/buttons_start_stop.html',
    'done':             'mobile/frags/button_done.html',
    NO_BUTTON:          '',
  }

#TODO: takes user instead of context ??
@register.inclusion_tag('mobile/templatetags/activity_card.html', takes_context=True)
def activity_card(context, activity, button_panel=START_STOP_BUTTONS, show_date=True,
                  shortcut=False, never_edit_pcall=False,
                 ):
    extra_classes = ''

    if activity.type_id == ACTIVITYTYPE_PHONECALL:
        if button_panel == START_STOP_BUTTONS:
            button_panel = NO_BUTTON

        if not never_edit_pcall:
            extra_classes = 'editable-phonecall'

    user = context['user']

    return {'user':               user,
            'user_contact_id':    user.linked_contact.id,
            'activity':           activity,
            'STATUS_IN_PROGRESS': STATUS_IN_PROGRESS,
            'is_floating':        activity.floating_type != NARROW,
            'buttons_template':   _BUTTONS[button_panel],
            'show_date':          show_date,
            'shortcut':           shortcut,
            'extra_classes':      extra_classes,
           }

@register.inclusion_tag('mobile/templatetags/footer.html')
def get_footer(show_delog=True):
    return {'REDIRECT_FIELD_NAME':    REDIRECT_FIELD_NAME,
            'NON_MOBILE_SITE_DOMAIN': settings.NON_MOBILE_SITE_DOMAIN or '/',
            'show_delog':             show_delog,
           }
