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

from datetime import timedelta

from django.conf import settings
from django.utils.timezone import now, make_aware, localtime, utc

from creme.creme_core.models import Relation
from creme.creme_core.utils.dates import get_dt_to_iso8601_str, get_dt_from_iso8601_str
                                         #get_creme_dt_from_utc_dt get_utc_dt_from_creme_dt, get_utc_now, get_naive_dt_from_tzdate

from creme.activities.models import Activity, Calendar
from creme.activities.constants import REL_SUB_PART_2_ACTIVITY, ACTIVITYTYPE_MEETING

from ..models import AS_Folder, EntityASData
from ..utils import generate_guid, encode_AS_timezone


ALL_DAY_EVENT = 1#An item marked as an all day event is understood to begin on midnight of the current day and to end on midnight of the next day.

ONE_DAY_TD = timedelta(days=1)

#Busy statuses
AS_BUSY_STATUSES = {
    0 : False,#Free
    1 : False,#Tentative
    2 : True, #Busy
    3 : True, #Out of Office
}

#Sensitivity values
#0 Normal
#1 Personal
#2 Private
#3 Confidential

def get_start_date(activity=None, needs_attr=False, *args, **kwargs):
    if needs_attr:
        return 'start'

    if activity.start:
        #return get_dt_to_iso8601_str(get_utc_dt_from_creme_dt(activity.start))
        return get_dt_to_iso8601_str(activity.start)

def get_end_date(activity=None, needs_attr=False, *args, **kwargs):
    if needs_attr:
        return 'end'

    if activity.end:
        #return get_dt_to_iso8601_str(get_utc_dt_from_creme_dt(activity.end))
        return get_dt_to_iso8601_str(activity.end)

def get_modified_date(activity=None, needs_attr=False, *args, **kwargs):
    if needs_attr:
        return 'modified'

    if activity.end:
        #return get_dt_to_iso8601_str(get_utc_dt_from_creme_dt(activity.modified))
        return get_dt_to_iso8601_str(activity.modified)

def handle_uid(entity=None, needs_attr=False, value=None, *args, **kwargs):
    if needs_attr:
        return 'UID'

    try:
        return EntityASData.objects.get(entity=entity, field_name='UID').field_value
    except EntityASData.DoesNotExist:
        return EntityASData.objects.create(entity=entity, field_name='UID', field_value=generate_guid()).field_value


#1 == Can be ghosted
CREME_ACTIVITY_MAPPING = {
    "Calendar:":{
        'title': 'Subject',#1

#        'start': 'StartTime',#0
#        'end': 'EndTime',#0
#        'modified':'DtStamp',#1
        
        get_start_date: 'StartTime',#0
        get_end_date: 'EndTime',#0
        get_modified_date:'DtStamp',#1

        'is_all_day': 'AllDayEvent',#1
        'busy':'BusyStatus',#1
#        :'Reminder',#1 In minutes before the notification TODO:make the function on creme side
#        :'MeetingStatus',#1

        #TODO: Handle attendees, Recurrence, Exceptions(need to?)

#        'UID': 'UID',#Keep the same name for data that are not in Creme
        handle_uid: 'UID',#Keep the same name for data that are not in Creme
        'Sensitivity': 'Sensitivity',#1
        'Timezone': 'Timezone',#1
        'OrganizerName':'OrganizerName',#1
        'OrganizerEmail': 'OrganizerEmail',#1
    },
    "AirSyncBase:":{

    }

}

if not settings.IS_ZPUSH:
    CREME_ACTIVITY_MAPPING['AirSyncBase:'].update({'description': 'Body'})

    
CREME_MEETING_MAPPING = {
    "Calendar:":{
        'place': 'Location'#1
    }
}
CREME_MEETING_MAPPING['Calendar:'].update(CREME_ACTIVITY_MAPPING['Calendar:'])#Meeting is a subclass of Activity

def handle_AS_data(entity, name, value):
    if value is not None:
        esd = EntityASData.objects.get_or_create(entity=entity, field_name=name)[0]
        esd.field_value = value
        esd.save()


def create_calendar_n_update_folder(folder, user):
        cal = Calendar.objects.create(name=folder.display_name, user=user, is_custom=False)
        folder.entity_id = cal.id
        folder.save()
        return cal

def get_calendar(folder, user):
    if folder.entity_id is not None:
        try:
            calendar = Calendar.objects.get(pk=folder.entity_id)
            if calendar.name != folder.display_name:
                calendar.name = folder.display_name
                calendar.save()
            return calendar
        except Calendar.DoesNotExist:
            return create_calendar_n_update_folder(folder, user)
    else:
        return create_calendar_n_update_folder(folder, user)

def _set_meeting_from_data(meeting, data, user, folder):
    data_pop = data.pop

    data_pop('', None)

    try:
        is_all_day = bool(int(data_pop('is_all_day', False)))
    except (ValueError, TypeError):
        is_all_day = False

    meeting.is_all_day = is_all_day

    start = data_pop('start', None)
    end   = data_pop('end', None)
    modified = data_pop('modified', None)

#    if not is_all_day:
    try:
        meeting.start = localtime(make_aware(get_dt_from_iso8601_str(start), utc))
    except (ValueError, TypeError):
        pass

    try:
        meeting.end = localtime(make_aware(get_dt_from_iso8601_str(end), utc))
    except (ValueError, TypeError):
        pass

#    else:
    #is_all_day or not if a meeting hasn't a start and/or end it last one day
    if meeting.start is None and meeting.end is None:
        #meeting.start = meeting.end = get_utc_now()#Don't use meeting.handle_all_day AS semantic is different
        meeting.start = meeting.end = now()#Don't use meeting.handle_all_day AS semantic is different
        meeting.end  += ONE_DAY_TD

    elif meeting.start is None and meeting.end is not None:
        meeting.end = meeting.end.replace(hour=0, minute=0, second=0)
        meeting.start = meeting.end-ONE_DAY_TD

    elif meeting.start is not None and meeting.end is None:
        meeting.start = meeting.start.replace(hour=0, minute=0, second=0)
        meeting.end = meeting.start+ONE_DAY_TD

    try:
        meeting.modified = get_dt_from_iso8601_str(modified)
    except (ValueError, TypeError):
        pass

    #meeting.start    = get_naive_dt_from_tzdate(get_creme_dt_from_utc_dt(meeting.start))
    #meeting.end      = get_naive_dt_from_tzdate(get_creme_dt_from_utc_dt(meeting.end))
    #meeting.modified = get_naive_dt_from_tzdate(get_creme_dt_from_utc_dt(meeting.modified))

    meeting.title = data_pop('title', "")
    meeting.place = data_pop('place', "")

    meeting.busy = AS_BUSY_STATUSES.get(int(data_pop('busy', 0)))

    meeting.save()

    CREME_MEETING_MAPPING_copy = CREME_MEETING_MAPPING.copy()
    for ns, fields in CREME_MEETING_MAPPING_copy.iteritems():
        for c_field, x_field in fields.iteritems():
            if callable(c_field):
                val=CREME_MEETING_MAPPING_copy[ns][c_field]
                del CREME_MEETING_MAPPING_copy[ns][c_field]
                CREME_MEETING_MAPPING_copy[ns][c_field(needs_attr=True)] = val

                
    for name, value in data.iteritems():
        for ns, fields in CREME_MEETING_MAPPING_copy.iteritems():
            field_name = fields.get(name)
            if field_name is not None:
                handle_AS_data(meeting, field_name, value)


def save_meeting(data, user, folder, *args, **kwargs):
    """Save a meeting from a populated data dict
        @Returns : A saved meeting instance
    """

    meeting = Activity(user=user, type_id=ACTIVITYTYPE_MEETING)
    calendar = get_calendar(folder, user)
    _set_meeting_from_data(meeting, data, user, folder)

    meeting.calendars.add(calendar)
    meeting.save()

    #TODO is the except really usefull (can be the related contact deleted?)
    try :
        Relation.objects.create(object_entity=meeting, type_id=REL_SUB_PART_2_ACTIVITY,
                                subject_entity=meeting.user.related_contact.all()[0], user=meeting.user)
    except Exception :
        pass

    return meeting



def update_meeting(meeting, data, user, history, folder, *args, **kwargs):
    calendar = get_calendar(folder, user)

    _set_meeting_from_data(meeting, data, user, folder)

    AS_Folder.objects.filter(entity_id=calendar.id)\
                     .exclude(id=folder.id)\
                     .update(entity_id=None)

    #We remove other AS synced calendars from the meeting. A meeting has to be present in only one synced calendar
    for cal_id in AS_Folder.objects.filter(entity_id__isnull=False, client__user=user).values_list('pk', flat=True):
        meeting.calendars.remove(cal_id)

    meeting.calendars.add(calendar)
    meeting.save()
    #TODO: Fill the history
    return meeting


def pre_serialize_meeting(value, c_field, xml_field, f_class, entity):
    if value not in (None, ''):
        return value

    if c_field == "Timezone":
        return encode_AS_timezone(settings.TIME_ZONE) #In case of adding from Creme




