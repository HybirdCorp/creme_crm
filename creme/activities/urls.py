# -*- coding: utf-8 -*-

# from django.conf.urls import url, include
from django.urls import re_path, include

from creme.creme_core.conf.urls import Swappable, swap_manager

from . import activity_model_is_custom  # constants
from .views import activity, bricks, calendar


calendar_patterns = [
    # re_path(r'^user[/]?$',                      calendar.user_calendar,              name='activities__calendar'),
    re_path(r'^user[/]?$',                      calendar.CalendarView.as_view(),       name='activities__calendar'),
    # re_path(r'^activities[/]?$',                calendar.get_users_activities,       name='activities__calendars_activities'),
    re_path(r'^activities[/]?$',                calendar.ActivitiesData.as_view(),     name='activities__calendars_activities'),
    re_path(r'^select[/]?$',                    calendar.CalendarsSelection.as_view(), name='activities__select_calendars'),
    re_path(r'^activity/update[/]?$',           calendar.update_activity_date,         name='activities__set_activity_dates'),
    re_path(r'^add[/]?$',                       calendar.CalendarCreation.as_view(),   name='activities__create_calendar'),
    re_path(r'^(?P<calendar_id>\d+)/edit[/]?$', calendar.CalendarEdition.as_view(),    name='activities__edit_calendar'),
    re_path(r'^delete[/]?$',                    calendar.delete_user_calendar,         name='activities__delete_calendar'),
    re_path(r'^link/(?P<activity_id>\d+)[/]?$', calendar.CalendarLinking.as_view(),    name='activities__link_calendar'),
]

urlpatterns = [
    re_path(r'^activities/ical[/]?$', activity.download_ical, name='activities__dl_ical'),

    # re_path(r'^type/(?P<type_id>[\w-]*)/json[/]?$', activity.get_types, name='activities__get_types'),
    re_path(r'^type/(?P<type_id>[\w-]*)/json[/]?$', activity.TypeChoices.as_view(), name='activities__get_types'),

    # Bricks
    re_path(r'^activity/(?P<activity_id>\d+)/participant/add[/]?$', bricks.ParticipantsAdding.as_view(), name='activities__add_participants'),
    re_path(r'^activity/participant/delete[/]?$',                   bricks.delete_participant,           name='activities__remove_participant'),
    re_path(r'^activity/(?P<activity_id>\d+)/subject/add[/]?$',     bricks.SubjectsAdding.as_view(),     name='activities__add_subjects'),
    re_path(r'^linked_activity/unlink[/]?$',                        bricks.unlink_activity,              name='activities__unlink_activity'),

    re_path(r'^calendar/', include(calendar_patterns)),
]

urlpatterns += swap_manager.add_group(
    activity_model_is_custom,
    # Swappable(url(r'^activities[/]?$',  activity.listview,                                                name='activities__list_activities')),
    # Swappable(url(r'^phone_calls[/]?$', activity.listview, {'type_id': constants.ACTIVITYTYPE_PHONECALL}, name='activities__list_phone_calls')),
    # Swappable(url(r'^meetings[/]?$',    activity.listview, {'type_id': constants.ACTIVITYTYPE_MEETING},   name='activities__list_meetings')),
    Swappable(re_path(r'^activities[/]?$',  activity.ActivitiesList.as_view(), name='activities__list_activities')),
    Swappable(re_path(r'^phone_calls[/]?$', activity.PhoneCallsList.as_view(), name='activities__list_phone_calls')),
    Swappable(re_path(r'^meetings[/]?$',    activity.MeetingsList.as_view(),   name='activities__list_meetings')),

    Swappable(re_path(r'^activity/add[/]?$',                            activity.ActivityCreation.as_view(),        name='activities__create_activity')),
    Swappable(re_path(r'^activity/add/(?P<act_type>\w+)[/]?$',          activity.ActivityCreation.as_view(),        name='activities__create_activity'),         check_args=('idxxx',)),
    Swappable(re_path(r'^activity/add_indispo[/]?$',                    activity.UnavailabilityCreation.as_view(),  name='activities__create_indispo')),
    Swappable(re_path(r'^activity/add_popup[/]?$',                      activity.ActivityCreationPopup.as_view(),   name='activities__create_activity_popup')),
    Swappable(re_path(r'^activity/add_related/(?P<entity_id>\d+)[/]?$', activity.RelatedActivityCreation.as_view(), name='activities__create_related_activity'), check_args=Swappable.INT_ID),
    Swappable(re_path(r'^activity/edit/(?P<activity_id>\d+)[/]?$',      activity.ActivityEdition.as_view(),         name='activities__edit_activity'),           check_args=Swappable.INT_ID),
    Swappable(re_path(r'^activity/(?P<activity_id>\d+)[/]?$',           activity.ActivityDetail.as_view(),          name='activities__view_activity'),           check_args=Swappable.INT_ID),
    Swappable(re_path(r'^activity/(?P<activity_id>\d+)/popup[/]?$',     activity.ActivityPopup.as_view(),           name='activities__view_activity_popup'),     check_args=Swappable.INT_ID),
    app_name='activities',
).kept_patterns()
