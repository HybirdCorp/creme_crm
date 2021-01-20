# -*- coding: utf-8 -*-

from django.urls import include, re_path

from creme.creme_core.conf.urls import Swappable, swap_manager
from creme.opportunities import opportunity_model_is_custom

from . import event_model_is_custom
from .views import event

urlpatterns = [
    re_path(
        r'^event/(?P<event_id>\d+)/contacts[/]?$',
        event.RelatedContactsList.as_view(),
        name='events__list_related_contacts',
    ),
    re_path(
        r'^event/(?P<event_id>\d+)/link_contacts[/]?$',
        event.AddContactsToEvent.as_view(),
        name='events__link_contacts',
    ),

    re_path(
        r'^event/(?P<event_id>\d+)/contact/(?P<contact_id>\d+)/',
        include([
            re_path(
                r'^set_invitation_status[/]?$',
                event.InvitationStatusSetting.as_view(),
                name='events__set_invitation_status',
            ),
            re_path(
                r'^set_presence_status[/]?$',
                event.PresenceStatusSetting.as_view(),
                name='events__set_presence_status',
            ),
        ]),
    ),

    *swap_manager.add_group(
        event_model_is_custom,
        Swappable(
            re_path(
                r'^events[/]?$',
                event.EventsList.as_view(),
                name='events__list_events',
            ),
        ),
        Swappable(
            re_path(
                r'^event/add[/]?$',
                event.EventCreation.as_view(),
                name='events__create_event',
            ),
        ),
        Swappable(
            re_path(
                r'^event/edit/(?P<event_id>\d+)[/]?$',
                event.EventEdition.as_view(),
                name='events__edit_event'),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^event/(?P<event_id>\d+)[/]?$',
                event.EventDetail.as_view(),
                name='events__view_event',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='events',
    ).kept_patterns(),

    *swap_manager.add_group(
        opportunity_model_is_custom,
        Swappable(
            re_path(
                r'^event/(?P<event_id>\d+)/add_opportunity_with/(?P<contact_id>\d+)[/]?$',
                event.RelatedOpportunityCreation.as_view(),
                name='events__create_related_opportunity',
            ),
            check_args=(1, 2),
        ),
        app_name='events',
    ).kept_patterns(),
]
