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
from datetime import datetime, timedelta

from django.conf import settings
from activesync.models.active_sync import AS_Folder

from activesync.utils import get_dt_from_iso8601_str, get_dt_to_iso8601_str
from activities.models.activity import Meeting, Calendar

ALL_DAY_EVENT = 1#An item marked as an all day event is understood to begin on midnight of the current day and to end on midnight of the next day.

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
    return get_dt_to_iso8601_str(activity.start) if activity.start else None

def get_end_date(activity=None, needs_attr=False, *args, **kwargs):
    if needs_attr:
        return 'end'
    return get_dt_to_iso8601_str(activity.end) if activity.end else None


#1 == Can be ghosted
CREME_ACTIVITY_MAPPING = {
    "Calendar:":{
#        :'Timezone'#1
#        :'OrganizerName'#1
#        :'OrganizerEmail'#1
        'title': 'Subject',#1
        get_start_date: 'StartTime',#0
        get_end_date: 'EndTime',#0
#        'start': 'StartTime',#0
#        'end': 'EndTime',#0
        'is_all_day': 'AllDayEvent',#1
        'modified':'DtStamp',#1
        'busy':'BusyStatus',#1
#        :'Reminder',#1 In minutes before the notification TODO:make the function on creme side
#        :'Sensitivity',#1
#        :'MeetingStatus',#1

        #TODO: Handle attendees, Recurrence, Exceptions(need to?)

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
CREME_MEETING_MAPPING.update(CREME_ACTIVITY_MAPPING)#Meeting is a subclass of Activity


def create_calendar_n_update_folder(folder, user):
        cal = Calendar.objects.create(name=folder.display_name, user=user, is_custom=False)
        folder.entity_id = cal.id
        folder.save()
        return cal

def get_calendar(folder, user):
    if folder.entity_id is not None:
        try:
            return Calendar.objects.get(pk=folder.entity_id)
        except Calendar.DoesNotExist:
            return create_calendar_n_update_folder(folder, user)
    else:
        return create_calendar_n_update_folder(folder, user)

def _set_meeting_from_data(meeting, data, user, folder):
    data_pop = data.pop

    data_pop('', None)

    is_all_day = data_pop('is_all_day', False)

    meeting.is_all_day = is_all_day

    if not is_all_day:
        try:
            meeting.start = get_dt_from_iso8601_str(data_pop('start'))
        except (ValueError, KeyError):
            pass

        try:
            meeting.end = get_dt_from_iso8601_str(data_pop('end'))
        except (ValueError, KeyError):
            pass
    else:
        meeting.start = meeting.end = datetime.now().replace(hour=0, minute=0, second=0)#Don't use meeting.handle_all_day AS semantic is different
        meeting.end  += timedelta(days=1)

    try:
        meeting.modified = get_dt_from_iso8601_str(data_pop('modified'))
    except (ValueError, KeyError):
        pass

    meeting.title = data_pop('title', "")
    meeting.place = data_pop('place', "")
    meeting.busy = AS_BUSY_STATUSES.get(int(data_pop('busy', 0)))

    meeting.save()
    

def save_meeting(data, user, folder, *args, **kwargs):
    """Save a meeting from a populated data dict
        @Returns : A saved meeting instance
    """

    meeting = Meeting(user=user)
    calendar = get_calendar(folder, user)
    _set_meeting_from_data(meeting, data, user, folder)

    meeting.calendars.add(calendar)

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
    #TODO: Fill the history
    return meeting


