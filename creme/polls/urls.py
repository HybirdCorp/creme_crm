# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from . import pollcampaign_model_is_custom, pollform_model_is_custom, pollreply_model_is_custom


urlpatterns = patterns('creme.polls.views',
    (r'^$', 'portal.portal'),

    (r'^poll_form/stats/(?P<pform_id>\d+)$', 'poll_form.stats'),

    #Form lines
    (r'^poll_form/(?P<pform_id>\d+)/add/line$',        'poll_form.add_line'),
    (r'^pform_line/(?P<line_id>\d+)/edit$',            'poll_form.edit_line'),
    (r'^pform_line/(?P<line_id>\d+)/disable$',         'poll_form.disable_line'),
    (r'^pform_line/(?P<line_id>\d+)/conditions/edit$', 'poll_form.edit_line_conditions'),
    (r'^pform_line/(?P<line_id>\d+)/choices$',         'poll_form.get_choices'),

    #Form section
    (r'^poll_form/(?P<pform_id>\d+)/add/section$',     'poll_form.add_section'),
    (r'^pform_section/(?P<section_id>\d+)/edit$',      'poll_form.edit_section'),
    (r'^pform_section/(?P<section_id>\d+)/add/child$', 'poll_form.add_section_child'),
    (r'^pform_section/(?P<section_id>\d+)/add/line$',  'poll_form.add_line_to_section'),

    #Replies
    (r'^poll_reply/fill/(?P<preply_id>\d+)$',                'poll_reply.fill'),
    (r'^poll_reply/clean$',                                  'poll_reply.clean'),
    (r'^poll_reply/link_to_person/(?P<person_id>\d+)$',      'poll_reply.link_to_person'),

    (r'^poll_reply/(?P<preply_id>\d+)/line/(?P<line_id>\d+)/edit$',        'poll_reply.edit_line'),
    (r'^poll_reply/(?P<preply_id>\d+)/line/(?P<line_id>\d+)/edit_wizard$', 'poll_reply.edit_line_wizard'),
)

if not pollcampaign_model_is_custom():
    urlpatterns += patterns('creme.polls.views.campaign',
        url(r'^campaigns',                           'listview',   name='polls__list_campaigns'),
        url(r'^campaign/add$',                       'add',        name='polls__create_campaign'),
        url(r'^campaign/edit/(?P<campaign_id>\d+)$', 'edit',       name='polls__edit_campaign'),
        url(r'^campaign/(?P<campaign_id>\d+)$',      'detailview', name='polls__view_campaign'),
    )

if not pollform_model_is_custom():
    urlpatterns += patterns('creme.polls.views.poll_form',
        url(r'^poll_forms',                        'listview',   name='polls__list_forms'),
        url(r'^poll_form/add$',                    'add',        name='polls__create_form'),
        url(r'^poll_form/edit/(?P<pform_id>\d+)$', 'edit',       name='polls__edit_form'),
        url(r'^poll_form/(?P<pform_id>\d+)$',      'detailview', name='polls__view_form'),
    )

if not pollreply_model_is_custom():
    urlpatterns += patterns('creme.polls.views.poll_reply',
        url(r'^poll_replies$',                                      'listview',          name='polls__list_replies'),
        url(r'^poll_reply/add$',                                    'add',               name='polls__create_reply'),
        url(r'^poll_reply/add_from_pform/(?P<pform_id>\d+)$',       'add_from_pform',    name='polls__create_reply_from_pform'),
        url(r'^poll_reply/add_from_campaign/(?P<campaign_id>\d+)$', 'add_from_campaign', name='polls__create_reply_from_campaign'),
        url(r'^poll_reply/add_from_person/(?P<person_id>\d+)$',     'add_from_person',   name='polls__create_reply_from_person'),
        url(r'^poll_reply/edit/(?P<preply_id>\d+)$',                'edit',              name='polls__edit_reply'),
        url(r'^poll_reply/(?P<preply_id>\d+)$',                     'detailview',        name='polls__view_reply'),
    )
