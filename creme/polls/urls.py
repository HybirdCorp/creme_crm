# -*- coding: utf-8 -*-

from django.conf.urls import patterns


urlpatterns = patterns('creme.polls.views',
    (r'^$', 'portal.portal'),

    #Poll forms
    (r'^poll_forms',                         'poll_form.listview'),
    (r'^poll_form/add$',                     'poll_form.add'),
    (r'^poll_form/edit/(?P<pform_id>\d+)$',  'poll_form.edit'),
    (r'^poll_form/(?P<pform_id>\d+)$',       'poll_form.detailview'),
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

    #Campaigns
    (r'^campaigns',                           'campaign.listview'),
    (r'^campaign/add$',                       'campaign.add'),
    (r'^campaign/edit/(?P<campaign_id>\d+)$', 'campaign.edit'),
    (r'^campaign/(?P<campaign_id>\d+)$',      'campaign.detailview'),

    #Replies
    (r'^poll_replies$',                                      'poll_reply.listview'),
    (r'^poll_reply/add$',                                    'poll_reply.add'),
    (r'^poll_reply/add_from_pform/(?P<pform_id>\d+)$',       'poll_reply.add_from_pform'),
    (r'^poll_reply/add_from_campaign/(?P<campaign_id>\d+)$', 'poll_reply.add_from_campaign'),
    (r'^poll_reply/add_from_person/(?P<person_id>\d+)$',     'poll_reply.add_from_person'),
    (r'^poll_reply/edit/(?P<preply_id>\d+)$',                'poll_reply.edit'),
    (r'^poll_reply/(?P<preply_id>\d+)$',                     'poll_reply.detailview'),
    (r'^poll_reply/fill/(?P<preply_id>\d+)$',                'poll_reply.fill'),
    (r'^poll_reply/clean$',                                  'poll_reply.clean'),
    (r'^poll_reply/link_to_person/(?P<person_id>\d+)$',      'poll_reply.link_to_person'),

    (r'^poll_reply/(?P<preply_id>\d+)/line/(?P<line_id>\d+)/edit$',        'poll_reply.edit_line'),
    (r'^poll_reply/(?P<preply_id>\d+)/line/(?P<line_id>\d+)/edit_wizard$', 'poll_reply.edit_line_wizard'),
)
