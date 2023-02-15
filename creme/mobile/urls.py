from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import views as auth_views
from django.urls import re_path

from creme import activities, persons
from creme.creme_core.conf.urls import Swappable, swap_manager

from . import forms, views

urlpatterns = [
    re_path(r'^$', views.portal, name='mobile__portal'),

    re_path(r'^persons[/]?$',       views.persons_portal, name='mobile__directory'),
    re_path(r'^person/search[/]?$', views.search_person,  name='mobile__search_person'),

    re_path(
        r'^activity/(?P<activity_id>\d+)/start[/]?$',
        views.start_activity,
        name='mobile__start_activity',
    ),
    re_path(
        r'^activity/(?P<activity_id>\d+)/stop[/]?$',
        views.stop_activity,
        name='mobile__stop_activity',
    ),

    re_path(r'^activities[/]?$', views.activities_portal, name='mobile__activities'),

    re_path(
        r'^phone_call/(?P<pcall_id>\d+)/done[/]?$',
        views.phonecall_workflow_done,
        name='mobile__pcall_wf_done',
    ),
    re_path(r'^phone_call/panel[/]?', views.phonecall_panel, name='mobile__pcall_panel'),

    re_path(
        r'^mark_as_favorite/(?P<entity_id>\d+)[/]?$',
        views.mark_as_favorite,
        name='mobile__mark_as_favorite',
    ),
    re_path(
        r'^unmark_favorite/(?P<entity_id>\d+)[/]?$',
        views.unmark_favorite,
        name='mobile__unmark_favorite',
    ),

    re_path(
        r'^login[/]?$',
        auth_views.LoginView.as_view(
            template_name='mobile/login.html',
            authentication_form=forms.MobileAuthenticationForm,
            # TODO: use attribute 'next_page'?
            extra_context={'REDIRECT_FIELD_NAME': REDIRECT_FIELD_NAME},
        ),
        name='mobile__login',
    ),

    # NB: useful if mobile app is separated from the main domain
    # (so not /mobile/* urls can be redirected)
    re_path(r'^logout[/]?$', auth_views.logout_then_login, name='mobile__logout'),

    *swap_manager.add_group(
        persons.contact_model_is_custom,
        Swappable(
            re_path(
                r'^contact/add[/]?$',
                views.MobileContactCreation.as_view(),
                name='mobile__create_contact',
            )
        ),
        app_name='mobile',
    ).kept_patterns(),

    *swap_manager.add_group(
        persons.organisation_model_is_custom,
        Swappable(
            re_path(
                r'^organisation/add[/]?$',
                views.MobileOrganisationCreation.as_view(),
                name='mobile__create_organisation',
            )
        ),
        app_name='mobile',
    ).kept_patterns(),

    *swap_manager.add_group(
        activities.activity_model_is_custom,
        Swappable(
            re_path(
                r'^phone_call/lasted_5_minutes[/]?$',
                views.phonecall_workflow_lasted_5_minutes,
                name='mobile__pcall_wf_lasted_5_minutes',
            ),
        ),
        Swappable(
            re_path(
                r'^phone_call/just_done[/]?$',
                views.phonecall_workflow_just_done,
                name='mobile__pcall_wf_just_done',
            ),
        ),
        Swappable(
            re_path(
                r'^phone_call/failed[/]?$',
                views.phonecall_workflow_failed,
                name='mobile__pcall_wf_failed',
            ),
        ),
        Swappable(
            re_path(
                r'^phone_call/postponed[/]?$',
                views.phonecall_workflow_postponed,
                name='mobile__pcall_wf_postponed',
            ),
        ),
        app_name='mobile',
    ).kept_patterns(),
]
