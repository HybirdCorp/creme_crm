# -*- coding: utf-8 -*-

from django.urls import include, re_path

from creme import polls
from creme.creme_core.conf.urls import Swappable, swap_manager

from .views import campaign, poll_form, poll_reply

urlpatterns = [
    re_path(
        r'^poll_form/stats/(?P<pform_id>\d+)[/]?$',
        poll_form.Statistics.as_view(),
        name='polls__form_stats',
    ),

    # Form lines
    re_path(
        r'^poll_form/(?P<pform_id>\d+)/add/line[/]?$',
        poll_form.LineCreation.as_view(),
        name='polls__create_form_line',
    ),
    re_path(
        r'^pform_line/(?P<line_id>\d+)/edit[/]?$',
        poll_form.LineEdition.as_view(),
        name='polls__edit_form_line',
    ),
    re_path(
        r'^pform_line/(?P<line_id>\d+)/disable[/]?$',
        poll_form.disable_line,
        name='polls__disable_form_line',
    ),
    re_path(
        r'^pform_line/(?P<line_id>\d+)/conditions/edit[/]?$',
        poll_form.ConditionsEdition.as_view(),
        name='polls__edit_form_line_conditions',
    ),
    re_path(
        r'^pform_line/(?P<line_id>\d+)/choices[/]?$',
        poll_form.LineChoices.as_view(),
        name='polls__form_line_choices',
    ),

    # Form section
    re_path(
        r'^poll_form/(?P<pform_id>\d+)/add/section[/]?$',
        poll_form.SectionCreation.as_view(),
        name='polls__create_form_section'
    ),
    re_path(
        r'^pform_section/(?P<section_id>\d+)/edit[/]?$',
        poll_form.SectionEdition.as_view(),
        name='polls__edit_form_section'
    ),
    re_path(
        r'^pform_section/(?P<section_id>\d+)/add/child[/]?$',
        poll_form.ChildSectionCreation.as_view(),
        name='polls__create_child_form_section'
    ),
    re_path(
        r'^pform_section/(?P<section_id>\d+)/add/line[/]?$',
        poll_form.AddingLineToSection.as_view(),
        name='polls__create_form_line_in_section'
    ),

    # Replies
    re_path(
        r'^poll_reply/fill/(?P<preply_id>\d+)[/]?$',
        poll_reply.fill,
        name='polls__fill_reply',
    ),
    re_path(
        r'^poll_reply/clean[/]?$',
        # poll_reply.clean
        poll_reply.PollReplyCleaning.as_view(),
        name='polls__clean_reply',
    ),
    re_path(
        r'^poll_reply/link_to_person/(?P<person_id>\d+)[/]?$',
        poll_reply.LinkingRepliesToPerson.as_view(),
        name='polls__link_reply_to_person',
    ),

    re_path(
        r'^poll_reply/(?P<preply_id>\d+)/line/(?P<line_id>\d+)/',
        include([
            re_path(
                r'^edit[/]?$',
                poll_reply.LineEdition.as_view(),
                name='polls__edit_reply_line',
            ),
            re_path(
                r'^edit_wizard[/]?$',
                poll_reply.edit_line_wizard,
                name='polls__edit_reply_line_wizard',
            ),
        ]),
    ),

    *swap_manager.add_group(
        polls.pollcampaign_model_is_custom,
        Swappable(
            re_path(
                r'^campaigns[/]?$',
                campaign.PollCampaignsList.as_view(),
                name='polls__list_campaigns',
            ),
        ),
        Swappable(
            re_path(
                r'^campaign/add[/]?$',
                campaign.PollCampaignCreation.as_view(),
                name='polls__create_campaign',
            ),
        ),
        Swappable(
            re_path(
                r'^campaign/edit/(?P<campaign_id>\d+)[/]?$',
                campaign.PollCampaignEdition.as_view(),
                name='polls__edit_campaign',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^campaign/(?P<campaign_id>\d+)[/]?$',
                campaign.PollCampaignDetail.as_view(),
                name='polls__view_campaign',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='polls',
    ).kept_patterns(),

    *swap_manager.add_group(
        polls.pollform_model_is_custom,
        Swappable(
            re_path(
                r'^poll_forms[/]?$',
                poll_form.PollFormsList.as_view(),
                name='polls__list_forms',
            ),
        ),
        Swappable(
            re_path(
                r'^poll_form/add[/]?$',
                poll_form.PollFormCreation.as_view(),
                name='polls__create_form',
            ),
        ),
        Swappable(
            re_path(
                r'^poll_form/edit/(?P<pform_id>\d+)[/]?$',
                poll_form.PollFormEdition.as_view(),
                name='polls__edit_form',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^poll_form/(?P<pform_id>\d+)[/]?$',
                poll_form.PollFormDetail.as_view(),
                name='polls__view_form',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='polls',
    ).kept_patterns(),

    *swap_manager.add_group(
        polls.pollreply_model_is_custom,
        Swappable(
            re_path(
                r'^poll_replies[/]?$',
                poll_reply.PollRepliesList.as_view(),
                name='polls__list_replies',
            ),
        ),

        # TODO: change url (reply->replies or add_several ??)
        Swappable(
            re_path(
                r'^poll_reply/add[/]?$',
                poll_reply.PollRepliesCreation.as_view(),
                name='polls__create_reply',
            ),
        ),
        Swappable(
            re_path(
                r'^poll_reply/add_from_pform/(?P<pform_id>\d+)[/]?$',
                poll_reply.RepliesCreationFromPForm.as_view(),
                name='polls__create_reply_from_pform',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^poll_reply/add_from_campaign/(?P<campaign_id>\d+)[/]?$',
                poll_reply.RepliesCreationFromCampaign.as_view(),
                name='polls__create_reply_from_campaign',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^poll_reply/add_from_person/(?P<person_id>\d+)[/]?$',
                poll_reply.RepliesCreationFromPerson.as_view(),
                name='polls__create_reply_from_person',
            ),
            check_args=Swappable.INT_ID,
        ),

        Swappable(
            re_path(
                r'^poll_reply/edit/(?P<preply_id>\d+)[/]?$',
                poll_reply.PollReplyEdition.as_view(),
                name='polls__edit_reply',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^poll_reply/(?P<preply_id>\d+)[/]?$',
                poll_reply.PollReplyDetail.as_view(),
                name='polls__view_reply',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='polls',
    ).kept_patterns(),
]
