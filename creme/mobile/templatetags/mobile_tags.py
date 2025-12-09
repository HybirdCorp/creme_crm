################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2025  Hybird
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

from creme.activities.constants import (
    REL_SUB_ACTIVITY_SUBJECT,
    UUID_STATUS_IN_PROGRESS,
    UUID_TYPE_MEETING,
    UUID_TYPE_PHONECALL,
    UUID_TYPE_TASK,
)
from creme.creme_core.models import SettingValue
from creme.mobile import setting_keys
from creme.persons import get_organisation_model

register = Library()
Organisation = get_organisation_model()


@register.simple_tag
def mobile_location_map_url(address):
    url = SettingValue.objects.value_4_key(setting_keys.location_map_url_key)
    data = {'search': str(address).replace(' ', '+')}

    geoaddress = getattr(address, 'geoaddress', None)
    if geoaddress is not None:
        data['lat'] = geoaddress.latitude or ''
        data['lng'] = geoaddress.longitude or ''

    return url.format(**data)


# ------------------------------------------------------------------------------
# TODO: move to creme_core ??
@register.simple_tag(takes_context=True)
def mobile_prepare_fields(context, instance, *field_names):
    is_hidden = context['fields_configs'].get_for_model(type(instance)).is_fieldname_hidden

    for field_name in field_names:
        if is_hidden(field_name):
            setattr(instance, field_name, None)

    return ''


# ------------------------------------------------------------------------------
_DOCUMENT_CLASSES = [
    (re.compile('Android',          re.I), 'android'),
    (re.compile('iPhone|iPad|iPod', re.I), 'ios'),
]


@register.simple_tag
def mobile_document_class(request):
    agent = request.META.get('HTTP_USER_AGENT')  # TODO: request.headers['User-Agent'] ??

    if agent is not None:
        for regex, class_name in _DOCUMENT_CLASSES:
            if regex.search(agent) is not None:
                return class_name

    return 'all'


# ------------------------------------------------------------------------------
# TODO: remove when Organisations can participate
@register.filter
def mobile_organisation_subjects(activity):
    return Organisation.objects.filter(
        relations__type=REL_SUB_ACTIVITY_SUBJECT,
        relations__object_entity=activity.id,
    )


# ------------------------------------------------------------------------------
ACTIVITY_TYPES_AS_STR = {
    UUID_TYPE_MEETING:   'meeting',
    UUID_TYPE_PHONECALL: 'phonecall',
    UUID_TYPE_TASK:      'task',  # currently not used...
}


# TODO: move to app 'activities'?
@register.filter
def mobile_activity_type_str(activity):
    return ACTIVITY_TYPES_AS_STR.get(str(activity.type.uuid), 'misc')


# ------------------------------------------------------------------------------
@register.filter
def mobile_activity_in_progress(activity):
    status = activity.status

    return status is not None and str(status.uuid) == UUID_STATUS_IN_PROGRESS


# ------------------------------------------------------------------------------
START_STOP_BUTTONS  = 'start-stop'
NO_BUTTON           = 'no-button'

_BUTTONS = {
    START_STOP_BUTTONS: 'mobile/frags/buttons_start_stop.html',
    'done':             'mobile/frags/button_done.html',
    NO_BUTTON:          '',
}


@register.inclusion_tag('mobile/templatetags/activity_card.html', takes_context=True)
def mobile_activity_card(context, activity,
                         button_panel=START_STOP_BUTTONS,
                         show_date=True,
                         shortcut=False,
                         never_edit_pcall=False,
                         ):
    extra_classes = ''

    if str(activity.type.uuid) == UUID_TYPE_PHONECALL:
        if button_panel == START_STOP_BUTTONS:
            button_panel = NO_BUTTON

        if not never_edit_pcall:
            extra_classes = 'editable-phonecall'

    user = context['user']
    linked_contact = user.linked_contact

    return {
        'user':               user,
        # TODO: test with is staff
        'user_contact_id':    linked_contact.id if linked_contact else None,
        'activity':           activity,
        'is_floating':        activity.floating_type != activity.FloatingType.NARROW,
        'buttons_template':   _BUTTONS[button_panel],
        'show_date':          show_date,
        'shortcut':           shortcut,
        'extra_classes':      extra_classes,
        'fields_configs':     context['fields_configs'],
    }


# ------------------------------------------------------------------------------
@register.inclusion_tag('mobile/templatetags/footer.html')
def mobile_footer(show_delog=True):
    return {
        'REDIRECT_FIELD_NAME':    REDIRECT_FIELD_NAME,
        'NON_MOBILE_SITE_DOMAIN': settings.NON_MOBILE_SITE_DOMAIN or '/',
        'show_delog':             show_delog,
    }
