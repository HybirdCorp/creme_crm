# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('activities.views',
    (r'^$', 'portal.portal'),

    (r'^activities$',                                      'activity.listview'),
    (r'^activities/(?P<ids>([\d][,]*)+)/ical$',            'activity.download_ical'),
    (r'^activity/add-with-relation/(?P<act_type>\w+)$',    'activity.add_with_relation'),
    (r'^activity/add-without-relation/(?P<act_type>\w+)$', 'activity.add_without_relation'),
    (r'^activity/edit/(?P<activity_id>\d+)$',              'activity.edit'),
    (r'^activity/(?P<activity_id>\d+)$',                   'activity.detailview'),
    (r'^activity/(?P<activity_id>\d+)/popup$',             'activity.popupview'),

    #blocks
    (r'^activity/(?P<activity_id>\d+)/participant/add$', 'blocks.add_participant'),
    (r'^activity/(?P<activity_id>\d+)/subject/add$',     'blocks.add_subject'),
    (r'^linked_activity/unlink$',                        'blocks.unlink_activity'),

    #calendar
    (r'^calendar/my$',                                                  'calendar.user_calendar'),#for compatibility
    (r'^calendar/user$',                                                'calendar.user_calendar'),
    (r'^calendar/users_activities/(?P<usernames>([\w]+){1}(,[\w]+)*)$', 'calendar.get_users_activities'),
    (r'^calendar/activity/update',                                      'calendar.update_activity_date'),

    (r'^indisponibility/add$', 'activity.add_indisponibility'), #TODO: use activity/add-(?P<type>.*) ?? with a factory type-based ?

    (r'^get_entity_relation_choices_for_activity$', 'ajax.get_entity_relation_choices_for_activity'),
)

urlpatterns += patterns('creme_core.views.generic',
    #(r'^edit_js/$', 'creme_core.views.edit_js'),
    (r'^activity/delete/(?P<object_id>\d+)$',               'delete_entity'),
    (r'^activity/delete_js/(?P<entities_ids>([\d]+[,])+)$', 'delete_entities_js'),
)
