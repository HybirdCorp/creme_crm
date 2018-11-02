# -*- coding: utf-8 -*-

from django.conf.urls import url
from django.contrib.auth import REDIRECT_FIELD_NAME, views as auth_views

from creme.creme_core.conf.urls import Swappable, swap_manager

from creme import persons, activities

from . import views, forms


urlpatterns = [
    url(r'^$', views.portal, name='mobile__portal'),

    url(r'^persons[/]?$',       views.persons_portal, name='mobile__directory'),
    url(r'^person/search[/]?$', views.search_person,  name='mobile__search_person'),

    url(r'^activity/(?P<activity_id>\d+)/start[/]?$', views.start_activity, name='mobile__start_activity'),
    url(r'^activity/(?P<activity_id>\d+)/stop[/]?$',  views.stop_activity,  name='mobile__stop_activity'),

    url(r'^activities[/]?$', views.activities_portal, name='mobile__activities'),

    url(r'^phone_call/(?P<pcall_id>\d+)/done[/]?$', views.phonecall_workflow_done, name='mobile__pcall_wf_done'),
    url(r'^phone_call/panel[/]?',                   views.phonecall_panel,         name='mobile__pcall_panel'),

    url(r'^mark_as_favorite/(?P<entity_id>\d+)[/]?$', views.mark_as_favorite, name='mobile__mark_as_favorite'),
    url(r'^unmark_favorite/(?P<entity_id>\d+)[/]?$',  views.unmark_favorite,  name='mobile__unmark_favorite'),

    # url(r'^login[/]?$',  auth_views.login,
    #     {'template_name':       'mobile/login.html',
    #      'authentication_form': forms.MobileAuthenticationForm,
    #      'extra_context':       {'REDIRECT_FIELD_NAME': REDIRECT_FIELD_NAME},
    #     },
    #     name='mobile__login',
    #    ),
    url(r'^login[/]?$',
        auth_views.LoginView.as_view(
             template_name='mobile/login.html',
             authentication_form=forms.MobileAuthenticationForm,
             extra_context={'REDIRECT_FIELD_NAME': REDIRECT_FIELD_NAME},
        ),
        name='mobile__login',
   ),

    # NB: useful if mobile app is separated from the main domain (so not /mobile/* urls can be redirected)
    url(r'^logout[/]?$', auth_views.logout_then_login, name='mobile__logout'),
]

# if not persons.contact_model_is_custom():
#     urlpatterns += [
#         url(r'^contact/add[/]?$', views.create_contact, name='mobile__create_contact'),
#     ]
urlpatterns += swap_manager.add_group(
    persons.contact_model_is_custom,
    Swappable(url(r'^contact/add[/]?$',
                  views.MobileContactCreation.as_view(),
                  name='mobile__create_contact',
                 )
             ),
    app_name='mobile',
).kept_patterns()

# if not persons.organisation_model_is_custom():
#     urlpatterns += [
#         url(r'^organisation/add[/]?$', views.create_organisation, name='mobile__create_organisation'),
#     ]
urlpatterns += swap_manager.add_group(
    persons.organisation_model_is_custom,
    Swappable(url(r'^organisation/add[/]?$',
                  views.MobileOrganisationCreation.as_view(),
                  name='mobile__create_organisation',
                 )
             ),
    app_name='mobile',
).kept_patterns()

# if not activities.activity_model_is_custom():
#     urlpatterns += [
#         url(r'^phone_call/lasted_5_minutes[/]?$', views.phonecall_workflow_lasted_5_minutes, name='mobile__pcall_wf_lasted_5_minutes'),
#         url(r'^phone_call/just_done[/]?$',        views.phonecall_workflow_just_done,        name='mobile__pcall_wf_just_done'),
#         url(r'^phone_call/failed[/]?$',           views.phonecall_workflow_failed,           name='mobile__pcall_wf_failed'),
#         url(r'^phone_call/postponed[/]?$',        views.phonecall_workflow_postponed,        name='mobile__pcall_wf_postponed'),
#     ]
urlpatterns += swap_manager.add_group(
    activities.activity_model_is_custom,
    Swappable(url(r'^phone_call/lasted_5_minutes[/]?$', views.phonecall_workflow_lasted_5_minutes, name='mobile__pcall_wf_lasted_5_minutes')),
    Swappable(url(r'^phone_call/just_done[/]?$',        views.phonecall_workflow_just_done,        name='mobile__pcall_wf_just_done')),
    Swappable(url(r'^phone_call/failed[/]?$',           views.phonecall_workflow_failed,           name='mobile__pcall_wf_failed')),
    Swappable(url(r'^phone_call/postponed[/]?$',        views.phonecall_workflow_postponed,        name='mobile__pcall_wf_postponed')),
    app_name='mobile',
).kept_patterns()
