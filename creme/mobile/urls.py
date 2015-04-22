# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url
from django.contrib.auth import REDIRECT_FIELD_NAME

from creme.persons import contact_model_is_custom, organisation_model_is_custom

from .forms import MobileAuthenticationForm


urlpatterns = patterns('creme.mobile.views',
    (r'^$', 'portal'),

    (r'^persons$',          'persons_portal'),
    (r'^person/search$',    'search_person'),

    (r'^activity/(?P<activity_id>\d+)/start$', 'start_activity'),
    (r'^activity/(?P<activity_id>\d+)/stop$',  'stop_activity'),

    (r'^activities$', 'activities_portal'),

    (r'^phone_call/(?P<pcall_id>\d+)/done$', 'phonecall_workflow_done'),

    (r'^phone_call/panel',            'phonecall_panel'),
    (r'^phone_call/lasted_5_minutes', 'phonecall_workflow_lasted_5_minutes'),
    (r'^phone_call/just_done',        'phonecall_workflow_just_done'),
    (r'^phone_call/failed$',          'phonecall_workflow_failed'),
    (r'^phone_call/postponed$',       'phonecall_workflow_postponed'),

    (r'^mark_as_favorite/(?P<entity_id>\d+)$', 'mark_as_favorite'),
    (r'^unmark_favorite/(?P<entity_id>\d+)$',  'unmark_favorite'),
)

if not contact_model_is_custom():
    urlpatterns += patterns('creme.mobile.views',
        url(r'^contact/add$', 'create_contact', name='mobile__create_contact'),
    )

if not organisation_model_is_custom():
    urlpatterns += patterns('creme.mobile.views',
        url(r'^organisation/add$', 'create_organisation', name='mobile__create_organisation'),
    )

urlpatterns += patterns('django.contrib.auth.views',
    (r'^login/$',  'login', {'template_name':       'mobile/login.html',
                              'authentication_form': MobileAuthenticationForm,
                              'extra_context':       {'REDIRECT_FIELD_NAME': REDIRECT_FIELD_NAME},
                            }),

    #NB: useful if mobile app is separated from the main domain (so not /mobile/* urls can be redirected)
    (r'^logout/$', 'logout_then_login'),
)
