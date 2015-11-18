# -*- coding: utf-8 -*-

from django.conf.urls import url
from django.contrib.auth import REDIRECT_FIELD_NAME, views as auth_views

from creme.persons import contact_model_is_custom, organisation_model_is_custom

from creme.activities import activity_model_is_custom

from .forms import MobileAuthenticationForm
from creme.mobile import views


urlpatterns = [
    url(r'^$', views.portal),

    url(r'^persons$',          views.persons_portal),
    url(r'^person/search$',    views.search_person),

    url(r'^activity/(?P<activity_id>\d+)/start$', views.start_activity),
    url(r'^activity/(?P<activity_id>\d+)/stop$',  views.stop_activity),

    url(r'^activities$', views.activities_portal),

    url(r'^phone_call/(?P<pcall_id>\d+)/done$', views.phonecall_workflow_done),
    url(r'^phone_call/panel',                   views.phonecall_panel),

    url(r'^mark_as_favorite/(?P<entity_id>\d+)$', views.mark_as_favorite),
    url(r'^unmark_favorite/(?P<entity_id>\d+)$',  views.unmark_favorite),

    url(r'^login/$',  auth_views.login,
        {'template_name':       'mobile/login.html',
         'authentication_form': MobileAuthenticationForm,
         'extra_context':       {'REDIRECT_FIELD_NAME': REDIRECT_FIELD_NAME},
        }
       ),

    # NB: useful if mobile app is separated from the main domain (so not /mobile/* urls can be redirected)
    url(r'^logout/$', auth_views.logout_then_login),
]

if not contact_model_is_custom():
    urlpatterns += [
        url(r'^contact/add$', views.create_contact, name='mobile__create_contact'),
    ]

if not organisation_model_is_custom():
    urlpatterns += [
        url(r'^organisation/add$', views.create_organisation, name='mobile__create_organisation'),
    ]

if not activity_model_is_custom():
    urlpatterns += [
        url(r'^phone_call/lasted_5_minutes', views.phonecall_workflow_lasted_5_minutes, name='mobile__pcall_wf_lasted_5_minutes'),
        url(r'^phone_call/just_done',        views.phonecall_workflow_just_done,        name='mobile__pcall_wf_just_done'),
        url(r'^phone_call/failed$',          views.phonecall_workflow_failed,           name='mobile__pcall_wf_failed'),
        url(r'^phone_call/postponed$',       views.phonecall_workflow_postponed,        name='mobile__pcall_wf_postponed'),
    ]
