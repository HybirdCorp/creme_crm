from django.urls import include, re_path

from creme import emails
from creme.creme_core.conf.urls import Swappable, swap_manager

from .views import (
    campaign,
    mail,
    mailing_list,
    recipient,
    sending,
    signature,
    synchronization,
    template,
)

urlpatterns = [
    # Campaign: mailing_list brick
    re_path(
        r'^campaign/(?P<campaign_id>\d+)/mailing_list/add[/]?$',
        campaign.MailingListsAdding.as_view(),
        name='emails__add_mlists_to_campaign'
    ),
    re_path(
        r'^campaign/(?P<campaign_id>\d+)/mailing_list/delete[/]?$',
        campaign.MailingListRemoving.as_view(),
        name='emails__remove_mlist_from_campaign'
    ),

    # Campaign: sending configuration
    re_path(
        r'^sending/config/add[/]?$',
        sending.SendingConfigItemCreation.as_view(),
        name='emails__create_sending_config_item',
    ),
    re_path(
        r'^sending/config/edit/(?P<item_id>\d+)[/]?$',
        sending.SendingConfigItemEdition.as_view(),
        name='emails__edit_sending_config_item',
    ),
    re_path(
        r'^sending/config/set_password/(?P<item_id>\d+)[/]?$',
        sending.SendingConfigItemPasswordEdition.as_view(),
        name='emails__set_sending_config_item_password',
    ),
    re_path(
        r'^sending/config/delete[/]?$',
        sending.SendingConfigItemDeletion.as_view(),
        name='emails__delete_sending_config_item',
    ),

    # Campaign: sending brick
    re_path(
        r'^campaign/(?P<campaign_id>\d+)/sending/add[/]?$',
        sending.SendingCreation.as_view(),
        name='emails__create_sending',
    ),
    re_path(
        r'^sending/(?P<sending_id>\d+)/edit[/]?$',
        sending.SendingEdition.as_view(),
        name='emails__edit_sending',
    ),

    # Campaign: sending details brick
    re_path(
        r'^sending/(?P<sending_id>\d+)[/]?$',
        sending.SendingDetail.as_view(),
        name='emails__view_sending',
    ),
    re_path(
        r'^sending/(?P<sending_id>\d+)/get_body[/]?$',
        sending.SendingBody.as_view(),
        name='emails__sending_body',
    ),
    re_path(
        r'^sending/(?P<sending_id>\d+)/reload[/]?$',
        sending.SendingBricksReloading.as_view(),
        name='emails__reload_sending_bricks',
    ),

    # Mailing list: recipients brick
    re_path(
        r'^mailing_list/(?P<ml_id>\d+)/recipient/add[/]?$',
        recipient.RecipientsAdding.as_view(),
        name='emails__add_recipients',
    ),
    re_path(
        r'^mailing_list/(?P<ml_id>\d+)/recipient/add_csv[/]?$',
        recipient.RecipientsAddingFromCSV.as_view(),
        name='emails__add_recipients_from_csv',
    ),

    # Mailing list: contacts brick
    re_path(
        r'^mailing_list/(?P<ml_id>\d+)/contact/add[/]?$',
        mailing_list.ContactsAdding.as_view(),
        name='emails__add_contacts_to_mlist',
    ),
    re_path(
        r'^mailing_list/(?P<ml_id>\d+)/contact/add_from_filter[/]?$',
        mailing_list.ContactsAddingFromFilter.as_view(),
        name='emails__add_contacts_to_mlist_from_filter',
    ),
    re_path(
        r'^mailing_list/(?P<ml_id>\d+)/contact/delete[/]?$',
        mailing_list.ContactRemoving.as_view(),
        name='emails__remove_contact_from_mlist',
    ),

    # Mailing list: organisations brick
    re_path(
        r'^mailing_list/(?P<ml_id>\d+)/organisation/add[/]?$',
        mailing_list.OrganisationsAdding.as_view(),
        name='emails__add_orgas_to_mlist',
    ),
    re_path(
        r'^mailing_list/(?P<ml_id>\d+)/organisation/add_from_filter[/]?$',
        mailing_list.OrganisationsAddingFromFilter.as_view(),
        name='emails__add_orgas_to_mlist_from_filter',
    ),
    re_path(
        r'^mailing_list/(?P<ml_id>\d+)/organisation/delete[/]?$',
        mailing_list.OrganisationRemoving.as_view(),
        name='emails__remove_orga_from_mlist',
    ),

    # Mailing list: child lists brick
    re_path(
        r'^mailing_list/(?P<ml_id>\d+)/child/add[/]?$',
        mailing_list.ChildrenAdding.as_view(),
        name='emails__add_child_mlists',
    ),
    re_path(
        r'^mailing_list/(?P<ml_id>\d+)/child/delete[/]?$',
        mailing_list.ChildRemoving.as_view(),
        name='emails__remove_child_mlist',
    ),

    # Template: attachment brick
    re_path(
        r'^template/(?P<template_id>\d+)/attachment/add[/]?$',
        template.AttachmentsAdding.as_view(),
        name='emails__add_attachments_to_template',
    ),
    re_path(
        r'^template/(?P<template_id>\d+)/attachment/delete[/]?$',
        template.AttachmentRemoving.as_view(),
        name='emails__remove_attachment_from_template',
    ),

    # Mails history bricks
    re_path(
        r'^mails_history/(?P<mail_id>\w+)[/]?$',
        mail.LightWeightEmailPopup.as_view(),
        name='emails__view_lw_mail'
    ),  # TODO: improve URL (lw_mail...)
    re_path(
        r'^mail/get_body/(?P<mail_id>\w+)[/]?$',
        mail.LightWeightEmailBody.as_view(),
        name='emails__lw_mail_body',
    ),  # TODO: idem
    re_path(
        r'^mail/resend[/]?$',
        mail.EntityEmailsResending.as_view(),
        name='emails__resend_emails',
    ),
    re_path(
        r'^mail/link/(?P<subject_id>\w+)[/]?$',
        mail.EntityEmailLinking.as_view(),
        name='emails__link_emails',
    ),

    # Signature
    re_path(
        r'^signature/',
        include([
            re_path(
                r'^add[/]?$',
                signature.SignatureCreation.as_view(),
                name='emails__create_signature',
            ),
            re_path(
                r'^edit/(?P<signature_id>\d+)[/]?$',
                signature.SignatureEdition.as_view(),
                name='emails__edit_signature',
            ),
            re_path(
                r'^delete[/]?$',
                signature.SignatureDeletion.as_view(),
                name='emails__delete_signature',
            ),
        ]),
    ),

    # Synchronization
    re_path(
        r'^synchronization/',
        include([
            re_path(
                r'^portal[/]?$',
                synchronization.SynchronizationPortal.as_view(),
                name='emails__sync_portal',
            ),
            re_path(
                r'^email_to_sync/accept[/]?$',
                synchronization.EmailToSyncAcceptation.as_view(),
                name='emails__accept_email_to_sync',
            ),
            re_path(
                r'^email_to_sync/delete[/]?$',
                synchronization.EmailToSyncDeletion.as_view(),
                name='emails__delete_email_to_sync',
            ),

            re_path(
                r'^email_to_sync/person/edit/(?P<person_id>\d+)[/]?$',
                synchronization.EmailToSyncPersonEdition.as_view(),
                name='emails__edit_email_to_sync_person',
            ),
            re_path(
                r'^email_to_sync/(?P<mail_id>\d+)/fix[/]?$',
                synchronization.EmailToSyncCorrection.as_view(),
                name='emails__fix_email_to_sync',
            ),
            re_path(
                r'^email_to_sync/(?P<mail_id>\d+)/recipient/mark[/]?$',
                synchronization.EmailToSyncRecipientMarking.as_view(),
                name='emails__mark_email_to_sync_recipient',
            ),
            re_path(
                r'^email_to_sync/(?P<mail_id>\d+)/recipient/delete[/]?$',
                synchronization.EmailToSyncRecipientDeletion.as_view(),
                name='emails__delete_email_to_sync_recipient',
            ),

            re_path(
                r'^email_to_sync/(?P<mail_id>\d+)/attachment/delete[/]?$',
                synchronization.EmailToSyncAttachmentDeletion.as_view(),
                name='emails__delete_email_to_sync_attachment',
            ),

            # Configuration
            re_path(
                r'^config/add[/]?$',
                synchronization.SynchronizationConfigItemCreation.as_view(),
                name='emails__create_sync_config_item',
            ),
            re_path(
                r'^config/edit/(?P<item_id>\d+)[/]?$',
                synchronization.SynchronizationConfigItemEdition.as_view(),
                name='emails__edit_sync_config_item',
            ),
            re_path(
                r'^config/delete[/]?$',
                synchronization.SynchronizationConfigItemDeletion.as_view(),
                name='emails__delete_sync_config_item',
            ),
        ]),
    ),

    *swap_manager.add_group(
        emails.emailcampaign_model_is_custom,
        Swappable(
            re_path(
                r'^campaigns[/]?$',
                campaign.EmailCampaignsList.as_view(),
                name='emails__list_campaigns',
            ),
        ),
        Swappable(
            re_path(
                r'^campaign/add[/]?$',
                campaign.EmailCampaignCreation.as_view(),
                name='emails__create_campaign',
            ),
        ),
        Swappable(
            re_path(
                r'^campaign/edit/(?P<campaign_id>\d+)[/]?$',
                campaign.EmailCampaignEdition.as_view(),
                name='emails__edit_campaign',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^campaign/(?P<campaign_id>\d+)[/]?$',
                campaign.EmailCampaignDetail.as_view(),
                name='emails__view_campaign',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='emails',
    ).kept_patterns(),

    *swap_manager.add_group(
        emails.emailtemplate_model_is_custom,
        Swappable(
            re_path(
                r'^templates[/]?$',
                template.EmailTemplatesList.as_view(),
                name='emails__list_templates',
            ),
        ),
        Swappable(
            re_path(
                r'^template/add[/]?$',
                template.EmailTemplateCreation.as_view(),
                name='emails__create_template',
            ),
        ),
        Swappable(
            re_path(
                r'^template/edit/(?P<template_id>\d+)[/]?$',
                template.EmailTemplateEdition.as_view(),
                name='emails__edit_template',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^template/(?P<template_id>\d+)[/]?$',
                template.EmailTemplateDetail.as_view(),
                name='emails__view_template',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='emails',
    ).kept_patterns(),

    *swap_manager.add_group(
        emails.entityemail_model_is_custom,
        Swappable(
            re_path(
                r'^mails[/]?$',
                mail.EntityEmailsList.as_view(),
                name='emails__list_emails',
            ),
        ),
        Swappable(
            re_path(
                r'^mail/add/(?P<entity_id>\d+)[/]?$',
                mail.EntityEmailCreation.as_view(),
                name='emails__create_email',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^mail/add_from_template/(?P<entity_id>\d+)[/]?$',
                mail.EntityEmailWizard.as_view(),
                name='emails__create_email_from_template',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^mail/(?P<mail_id>\d+)[/]?$',
                mail.EntityEmailDetail.as_view(),
                name='emails__view_email',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^mail/(?P<mail_id>\d+)/popup[/]?$',
                mail.EntityEmailPopup.as_view(),
                name='emails__view_email_popup',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='emails',
    ).kept_patterns(),

    *swap_manager.add_group(
        emails.mailinglist_model_is_custom,
        Swappable(
            re_path(
                r'^mailing_lists[/]?$',
                mailing_list.MailingListsList.as_view(),
                name='emails__list_mlists',
            ),
        ),
        Swappable(
            re_path(
                r'^mailing_list/add[/]?$',
                mailing_list.MailingListCreation.as_view(),
                name='emails__create_mlist',
            ),
        ),
        Swappable(
            re_path(
                r'^mailing_list/edit/(?P<ml_id>\d+)[/]?$',
                mailing_list.MailingListEdition.as_view(),
                name='emails__edit_mlist',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^mailing_list/(?P<ml_id>\d+)[/]?$',
                mailing_list.MailingListDetail.as_view(),
                name='emails__view_mlist',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='emails',
    ).kept_patterns(),
]
