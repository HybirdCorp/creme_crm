# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from . import event_model_is_custom


urlpatterns = patterns('creme.events.views',
    (r'^$', 'portal.portal'),

    (r'^event/(?P<event_id>\d+)/contacts$',      'event.list_contacts'),
    (r'^event/(?P<event_id>\d+)/link_contacts$', 'event.link_contacts'),

    (r'^event/(?P<event_id>\d+)/contact/(?P<contact_id>\d+)/set_invitation_status$', 'event.set_invitation_status'),
    (r'^event/(?P<event_id>\d+)/contact/(?P<contact_id>\d+)/set_presence_status$',   'event.set_presence_status'),
    (r'^event/(?P<event_id>\d+)/add_opportunity_with/(?P<contact_id>\d+)$',          'event.add_opportunity'),
)

if not event_model_is_custom():
    urlpatterns += patterns('creme.events.views.event',
        url(r'^events$',                       'listview',   name='events__list_events'),
        url(r'^event/add$',                    'add',        name='events__create_event'),
        url(r'^event/edit/(?P<event_id>\d+)$', 'edit',       name='events__edit_event'),
        url(r'^event/(?P<event_id>\d+)$',      'detailview', name='events__view_event'),
    )
