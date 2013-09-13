# -*- coding: utf-8 -*-

from django.conf.urls import patterns

from creme.creme_core.utils.imports import find_n_import

from .constants import ACTIVITYTYPE_PHONECALL, ACTIVITYTYPE_MEETING


urlpatterns = patterns('creme.activities.views',
    (r'^$', 'portal.portal'),

    (r'^activities$',                               'activity.listview'),
    (r'^phone_calls$',                              'activity.listview', {'type_id': ACTIVITYTYPE_PHONECALL}),
    (r'^meetings$',                                 'activity.listview', {'type_id': ACTIVITYTYPE_MEETING}),
    (r'^activities/(?P<ids>([\d][,]*)+)/ical$',     'activity.download_ical'),

    (r'^activity/add$',                             'activity.add'),
    (r'^activity/add/(?P<act_type>\w+)$',           'activity.add_fixedtype'),
    (r'^activity/add_indispo$',                     'activity.add_indisponibility'),
    (r'^activity/add_popup$',                       'activity.add_popup'),
    (r'^activity/add_related/(?P<entity_id>\d+)$',  'activity.add_related'),
    (r'^activity/edit/(?P<activity_id>\d+)$',       'activity.edit'),
    (r'^activity/(?P<activity_id>\d+)$',            'activity.detailview'),
    (r'^activity/(?P<activity_id>\d+)/popup$',      'activity.popupview'),
    (r'^type/(?P<type_id>[\w-]+)/json$',            'activity.get_types'),

    #blocks
    (r'^activity/(?P<activity_id>\d+)/participant/add$', 'blocks.add_participant'),
    (r'^activity/participant/delete$',                   'blocks.delete_participant'),
    (r'^activity/(?P<activity_id>\d+)/subject/add$',     'blocks.add_subject'),
    (r'^linked_activity/unlink$',                        'blocks.unlink_activity'),

    #calendar
    #(r'^calendar/my$',                                                  'calendar.user_calendar'),#for compatibility
    (r'^calendar/user$',                                                'calendar.user_calendar'),
    (r'^calendar/users_activities/(?P<calendar_ids>([\d]+){0,1}(,[\d]+)*)$', 'calendar.get_users_activities'),
    (r'^calendar/activity/update',                                      'calendar.update_activity_date'),
    (r'^calendar/add$',                                                 'calendar.add_user_calendar'),
    (r'^calendar/(?P<calendar_id>\d+)/edit$',                           'calendar.edit_user_calendar'),
    (r'^calendar/delete$',                                              'calendar.delete_user_calendar'),
    (r'^calendar/link/(?P<activity_id>\d+)$',                           'calendar.link_user_calendar'),
)

find_n_import("activities_register", [])
