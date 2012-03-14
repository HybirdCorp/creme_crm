# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns

from creme_core.utils.imports import find_n_import


urlpatterns = patterns('activities.views',
    (r'^$', 'portal.portal'),

    (r'^activities$',                               'activity.listview'),
    (r'^phone_calls$',                              'phone_call.listview'),
    (r'^meetings$',                                 'meeting.listview'),
    (r'^activities/(?P<ids>([\d][,]*)+)/ical$',     'activity.download_ical'),
    (r'^activity/add/(?P<act_type>\w+)$',           'activity.add'),
    (r'^activity/add_popup$',                       'activity.add_popup'),
    (r'^activity/add_related/(?P<act_type>\w+)$',   'activity.add_related'),
    (r'^activity/edit/(?P<activity_id>\d+)$',       'activity.edit'),
    (r'^activity/(?P<activity_id>\d+)$',            'activity.detailview'),
    (r'^activity/(?P<activity_id>\d+)/popup$',      'activity.popupview'),
    (r'^activity/participant/delete$',              'activity.delete_participant'),

    #blocks
    (r'^activity/(?P<activity_id>\d+)/participant/add$', 'blocks.add_participant'),
    (r'^activity/(?P<activity_id>\d+)/subject/add$',     'blocks.add_subject'),
    (r'^linked_activity/unlink$',                        'blocks.unlink_activity'),

    #calendar
    (r'^calendar/my$',                                                  'calendar.user_calendar'),#for compatibility
    (r'^calendar/user$',                                                'calendar.user_calendar'),
    (r'^calendar/users_activities/(?P<usernames>([\w% ]+){1}(,[\w% ]+)*)/(?P<calendars_ids>([\d]+){0,1}(,[\d]+)*)$', 'calendar.get_users_activities'),
    (r'^calendar/activity/update',                                      'calendar.update_activity_date'),
    (r'^calendar/add$',                                                 'calendar.add_user_calendar'),
    (r'^calendar/(?P<calendar_id>\d+)/edit$',                           'calendar.edit_user_calendar'),
    (r'^calendar/delete$',                                              'calendar.delete_user_calendar'),

    (r'^indisponibility/add$', 'activity.add_indisponibility'), #TODO: use activity/add-(?P<type>.*) ?? with a factory type-based ?

    (r'^get_relationtype_choices$', 'ajax.get_relationtype_choices'),
)

find_n_import("activities_register", [])
