# -*- coding: utf-8 -*-

from django.conf.urls import url, include

from creme.opportunities import opportunity_model_is_custom

from . import event_model_is_custom
from .views import portal, event


urlpatterns = [
    url(r'^$', portal.portal, name='events__portal'),

    url(r'^event/(?P<event_id>\d+)/contacts$',      event.list_contacts, name='events__list_related_contacts'),
    url(r'^event/(?P<event_id>\d+)/link_contacts$', event.link_contacts, name='events__link_contacts'),

    url(r'^event/(?P<event_id>\d+)/contact/(?P<contact_id>\d+)/', include([
        url(r'^set_invitation_status$', event.set_invitation_status, name='events__set_invitation_status'),
        url(r'^set_presence_status$',   event.set_presence_status,   name='events__set_presence_status'),
    ])),
]

if not event_model_is_custom():
    urlpatterns += [
        url(r'^events$',                       event.listview,   name='events__list_events'),
        url(r'^event/add$',                    event.add,        name='events__create_event'),
        url(r'^event/edit/(?P<event_id>\d+)$', event.edit,       name='events__edit_event'),
        url(r'^event/(?P<event_id>\d+)$',      event.detailview, name='events__view_event'),
    ]

if not opportunity_model_is_custom():
    urlpatterns += [
        url(r'^event/(?P<event_id>\d+)/add_opportunity_with/(?P<contact_id>\d+)$', event.add_opportunity,
            name='events__create_related_opportunity',
           ),
    ]