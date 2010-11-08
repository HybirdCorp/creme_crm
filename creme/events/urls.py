# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('events.views',
    (r'^$', 'portal.portal'),

    (r'^events$',                                'event.listview'),
    (r'^event/add$',                             'event.add'),
    (r'^event/edit/(?P<event_id>\d+)$',          'event.edit'),
    (r'^event/(?P<event_id>\d+)$',               'event.detailview'),
    (r'^event/(?P<event_id>\d+)/contacts$',      'event.list_contacts'),
    (r'^event/(?P<event_id>\d+)/link_contacts$', 'event.link_contacts'),

    (r'^event/(?P<event_id>\d+)/contact/(?P<contact_id>\d+)/set_invitation_status$', 'event.set_invitation_status'),
    (r'^event/(?P<event_id>\d+)/contact/(?P<contact_id>\d+)/set_presence_status$',   'event.set_presence_status'),
)

urlpatterns += patterns('creme_core.views',
    (r'^event/delete/(?P<object_id>\d+)$', 'generic.delete_entity'),
)
