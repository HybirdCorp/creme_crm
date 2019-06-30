# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import logging

from django.apps import apps
from django.conf import settings
from django.utils.translation import gettext as _

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (RelationType, SearchConfigItem, SettingValue,
        BrickDetailviewLocation, CustomBrickConfigItem,
        ButtonMenuItem, HeaderFilter, Job)

from creme import persons, emails

from . import buttons, bricks, constants
from .creme_jobs import entity_emails_send_type, campaign_emails_send_type
from .setting_keys import emailcampaign_sender

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_MAIL_RECEIVED).exists()

        EmailCampaign = emails.get_emailcampaign_model()
        EmailTemplate = emails.get_emailtemplate_model()
        EntityEmail   = emails.get_entityemail_model()
        MailingList   = emails.get_mailinglist_model()

        Contact      = persons.get_contact_model()
        Organisation = persons.get_organisation_model()

        # ---------------------------
        SettingValue.objects.get_or_create(key_id=emailcampaign_sender.id, defaults={'value': ''})

        # ---------------------------
        RelationType.create((constants.REL_SUB_MAIL_RECEIVED, _('(email) received by'),  [EntityEmail]),
                            (constants.REL_OBJ_MAIL_RECEIVED, _('received the email'),   [Organisation, Contact]))
        RelationType.create((constants.REL_SUB_MAIL_SENDED,   _('(email) sent by'),      [EntityEmail]),
                            (constants.REL_OBJ_MAIL_SENDED,   _('sent the email'),       [Organisation, Contact]))
        RelationType.create((constants.REL_SUB_RELATED_TO,    _('(email) related to'),   [EntityEmail]),
                            (constants.REL_OBJ_RELATED_TO,    _('related to the email'), []))

        # ---------------------------
        create_hf = HeaderFilter.create
        create_hf(pk=constants.DEFAULT_HFILTER_MAILINGLIST,
                  model=MailingList,
                  name=_('Mailing list view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_CAMPAIGN,
                  model=EmailCampaign,
                  name=_('Campaign view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_TEMPLATE,
                  model=EmailTemplate,
                  name=_('Email template view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'subject'}),
                             ],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_EMAIL,
                  model=EntityEmail,
                  name=_('Email view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'sender'}),
                              (EntityCellRegularField, {'name': 'recipient'}),
                              (EntityCellRegularField, {'name': 'subject'}),
                             ],
                 )

        # ---------------------------
        create_searchconf = SearchConfigItem.create_if_needed
        create_searchconf(EmailCampaign, ['name', 'mailing_lists__name'])
        create_searchconf(MailingList,   ['name', 'children__name', 'contacts__first_name', 'contacts__last_name', 'organisations__name'])
        create_searchconf(EmailTemplate, ['name', 'subject', 'body', 'attachments__title'])
        create_searchconf(EntityEmail,   ['sender', 'recipient', 'subject'])

        # ---------------------------
        create_job = Job.objects.get_or_create
        create_job(type_id=entity_emails_send_type.id,
                   defaults={'language': settings.LANGUAGE_CODE,
                             'status':   Job.STATUS_OK,
                            }
                  )
        create_job(type_id=campaign_emails_send_type.id,
                   defaults={'language': settings.LANGUAGE_CODE,
                             'status':   Job.STATUS_OK,
                            }
                  )

        # ---------------------------
        if not already_populated:
            create_cbci = CustomBrickConfigItem.objects.create
            build_cell = EntityCellRegularField.build

            cbci_email = create_cbci(id='emails-entityemail_info',
                                     name=_('Email information'),
                                     content_type=EntityEmail,
                                     cells=[
                                        build_cell(EntityEmail, 'user'),
                                        build_cell(EntityEmail, 'reads'),
                                        build_cell(EntityEmail, 'status'),
                                        build_cell(EntityEmail, 'sender'),
                                        build_cell(EntityEmail, 'recipient'),
                                        build_cell(EntityEmail, 'subject'),
                                        build_cell(EntityEmail, 'reception_date'),
                                        build_cell(EntityEmail, 'attachments'),
                                        build_cell(EntityEmail, 'body'),
                                        build_cell(EntityEmail, 'description'),
                                     ],
                                    )
            cbci_template = create_cbci(id='emails-emailtemplate_info',
                                        name=_('Email template information'),
                                        content_type=EmailTemplate,
                                        cells=[
                                            build_cell(EmailTemplate, 'created'),
                                            build_cell(EmailTemplate, 'modified'),
                                            build_cell(EmailTemplate, 'user'),
                                            build_cell(EmailTemplate, 'name'),
                                            build_cell(EmailTemplate, 'subject'),
                                            build_cell(EmailTemplate, 'body'),
                                            build_cell(EmailTemplate, 'signature'),
                                            build_cell(EmailTemplate, 'description'),
                                        ],
                                       )

            create_bdl         = BrickDetailviewLocation.objects.create_if_needed
            create_bdl_4_model = BrickDetailviewLocation.objects.create_for_model_brick
            TOP   = BrickDetailviewLocation.TOP
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            create_bdl(brick=cbci_email.generate_id(),      order=5,   zone=LEFT,  model=EntityEmail)
            create_bdl(brick=bricks.EmailHTMLBodyBrick,     order=20,  zone=LEFT,  model=EntityEmail)
            create_bdl(brick=core_bricks.CustomFieldsBrick, order=40,  zone=LEFT,  model=EntityEmail)
            create_bdl(brick=core_bricks.PropertiesBrick,   order=450, zone=LEFT,  model=EntityEmail)
            create_bdl(brick=core_bricks.RelationsBrick,    order=500, zone=LEFT,  model=EntityEmail)
            create_bdl(brick=core_bricks.HistoryBrick,      order=20,  zone=RIGHT, model=EntityEmail)

            create_bdl_4_model(                             order=5,   zone=LEFT,  model=MailingList)
            create_bdl(brick=core_bricks.CustomFieldsBrick, order=40,  zone=LEFT,  model=MailingList)
            create_bdl(brick=bricks.EmailRecipientsBrick,   order=80,  zone=LEFT,  model=MailingList)
            create_bdl(brick=bricks.ContactsBrick,          order=90,  zone=LEFT,  model=MailingList)
            create_bdl(brick=bricks.OrganisationsBrick,     order=95,  zone=LEFT,  model=MailingList)
            create_bdl(brick=bricks.ChildListsBrick,        order=100, zone=LEFT,  model=MailingList)
            create_bdl(brick=bricks.ParentListsBrick,       order=105, zone=LEFT,  model=MailingList)
            create_bdl(brick=core_bricks.PropertiesBrick,   order=450, zone=LEFT,  model=MailingList)
            create_bdl(brick=core_bricks.RelationsBrick,    order=500, zone=LEFT,  model=MailingList)
            create_bdl(brick=core_bricks.HistoryBrick,      order=20,  zone=RIGHT, model=MailingList)

            create_bdl(brick=bricks.SendingsBrick,          order=2,   zone=TOP,   model=EmailCampaign)
            create_bdl_4_model(                             order=5,   zone=LEFT,  model=EmailCampaign)
            create_bdl(brick=core_bricks.CustomFieldsBrick, order=40,  zone=LEFT,  model=EmailCampaign)
            create_bdl(brick=bricks.MailingListsBrick,      order=120, zone=LEFT,  model=EmailCampaign)
            create_bdl(brick=core_bricks.PropertiesBrick,   order=450, zone=LEFT,  model=EmailCampaign)
            create_bdl(brick=core_bricks.RelationsBrick,    order=500, zone=LEFT,  model=EmailCampaign)
            create_bdl(brick=core_bricks.HistoryBrick,      order=20,  zone=RIGHT, model=EmailCampaign)

            create_bdl(brick=cbci_template.generate_id(),   order=5,   zone=LEFT,  model=EmailTemplate)
            create_bdl(brick=core_bricks.CustomFieldsBrick, order=40,  zone=LEFT,  model=EmailTemplate)
            create_bdl(brick=bricks.AttachmentsBrick,       order=60,  zone=LEFT,  model=EmailTemplate)
            create_bdl(brick=bricks.TemplateHTMLBodyBrick,  order=70,  zone=LEFT,  model=EmailTemplate)
            create_bdl(brick=core_bricks.PropertiesBrick,   order=450, zone=LEFT,  model=EmailTemplate)
            create_bdl(brick=core_bricks.RelationsBrick,    order=500, zone=LEFT,  model=EmailTemplate)
            create_bdl(brick=core_bricks.HistoryBrick,      order=20,  zone=RIGHT, model=EmailTemplate)

            # 'persons' app
            create_bdl(brick=bricks.MailsHistoryBrick, order=600, zone=RIGHT, model=Contact)
            create_bdl(brick=bricks.MailsHistoryBrick, order=600, zone=RIGHT, model=Organisation)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants import bricks as a_bricks

                for model in (MailingList, EmailCampaign, EmailTemplate):
                    create_bdl(brick=a_bricks.TodosBrick,        order=100, zone=RIGHT, model=model)
                    create_bdl(brick=a_bricks.MemosBrick,        order=200, zone=RIGHT, model=model)
                    create_bdl(brick=a_bricks.AlertsBrick,       order=300, zone=RIGHT, model=model)
                    create_bdl(brick=a_bricks.UserMessagesBrick, order=400, zone=RIGHT, model=model)

            if apps.is_installed('creme.documents'):
                # logger.info("Documents app is installed => we use the documents block on EmailCampaign's detail view")

                from creme.documents.bricks import LinkedDocsBrick

                create_bdl(brick=LinkedDocsBrick, order=600, zone=RIGHT, model=EmailCampaign)

            # ---------------------------
            ButtonMenuItem.create_if_needed(pk='emails-entity_email_link_button', model=EntityEmail, button=buttons.EntityEmailLinkButton, order=20)
