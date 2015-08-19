# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.creme_core.utils.imports import find_n_import

from . import activity_model_is_custom
from .constants import ACTIVITYTYPE_PHONECALL, ACTIVITYTYPE_MEETING
from .views import portal, activity, blocks, calendar


urlpatterns = [
    url(r'^$', portal.portal),

    url(r'^activities/(?P<ids>([\d][,]*)+)/ical$', activity.download_ical),
    url(r'^type/(?P<type_id>[\w-]+)/json$',        activity.get_types),

    # Blocks
    url(r'^activity/(?P<activity_id>\d+)/participant/add$', blocks.add_participant),
    url(r'^activity/participant/delete$',                   blocks.delete_participant),
    url(r'^activity/(?P<activity_id>\d+)/subject/add$',     blocks.add_subject),
    url(r'^linked_activity/unlink$',                        blocks.unlink_activity),

    # Calendar
    url(r'^calendar/user$',                                                     calendar.user_calendar),
    url(r'^calendar/users_activities/(?P<calendar_ids>([\d]+){0,1}(,[\d]+)*)$', calendar.get_users_activities),
    url(r'^calendar/activity/update',                                           calendar.update_activity_date),
    url(r'^calendar/add$',                                                      calendar.add_user_calendar),
    url(r'^calendar/(?P<calendar_id>\d+)/edit$',                                calendar.edit_user_calendar),
    url(r'^calendar/delete$',                                                   calendar.delete_user_calendar),
    url(r'^calendar/link/(?P<activity_id>\d+)$',                                calendar.link_user_calendar),
]

if not activity_model_is_custom():
    urlpatterns += [
        url(r'^activities$',  activity.listview,                                      name='activities__list_activities'),
        url(r'^phone_calls$', activity.listview, {'type_id': ACTIVITYTYPE_PHONECALL}, name='activities__list_phone_calls'),
        url(r'^meetings$',    activity.listview, {'type_id': ACTIVITYTYPE_MEETING},   name='activities__list_meetings'),

        url(r'^activity/add$',                            activity.add,                 name='activities__create_activity'),
#        url(r'^activity/add/(?P<act_type>\w+)$',          activity.add_fixedtype,       name='activities__create_fixedtype_activity'),
        url(r'^activity/add/(?P<act_type>\w+)$',          activity.add,                 name='activities__create_activity'),
        url(r'^activity/add_indispo$',                    activity.add_indisponibility, name='activities__create_indispo'),
        url(r'^activity/add_popup$',                      activity.add_popup,           name='activities__create_activity_popup'),
        url(r'^activity/add_related/(?P<entity_id>\d+)$', activity.add_related,         name='activities__create_related_activity'),
        url(r'^activity/edit/(?P<activity_id>\d+)$',      activity.edit,                name='activities__edit_activity'),
        url(r'^activity/(?P<activity_id>\d+)$',           activity.detailview,          name='activities__view_activity'),
        url(r'^activity/(?P<activity_id>\d+)/popup$',     activity.popupview,           name='activities__view_activity_popup'),
    ]

find_n_import("activities_register", [])
