# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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
#from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.blocks import (properties_block, relations_block,
        customfields_block, history_block)
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (RelationType, SearchConfigItem, SettingValue,
        BlockDetailviewLocation, BlockPortalLocation, CustomBlockConfigItem,
        ButtonMenuItem, HeaderFilter)

from creme.persons import get_contact_model, get_organisation_model
#from creme.persons.models import Organisation, Contact

from . import (get_emailcampaign_model, get_entityemail_model,
        get_emailtemplate_model, get_mailinglist_model)
#from .models import MailingList, EmailCampaign, EmailTemplate, EntityEmail
from . import blocks, constants
from .buttons import entityemail_link_button
from .setting_keys import emailcampaign_sender

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_MAIL_RECEIVED).exists()

        EmailCampaign = get_emailcampaign_model()
        EmailTemplate = get_emailtemplate_model()
        EntityEmail   = get_entityemail_model()
        MailingList   = get_mailinglist_model()

        Contact = get_contact_model()
        Organisation = get_organisation_model()

        SettingValue.create_if_needed(key=emailcampaign_sender, user=None, value="")

        RelationType.create((constants.REL_SUB_MAIL_RECEIVED, _(u"(email) received by"),  [EntityEmail]),
                            (constants.REL_OBJ_MAIL_RECEIVED, _(u"received the email"),   [Organisation, Contact]))
        RelationType.create((constants.REL_SUB_MAIL_SENDED,   _(u"(email) sended"),       [EntityEmail]),
                            (constants.REL_OBJ_MAIL_SENDED,   _(u"sended the email"),     [Organisation, Contact]))
        RelationType.create((constants.REL_SUB_RELATED_TO,    _(u'(email) related to'),   [EntityEmail]),
                            (constants.REL_OBJ_RELATED_TO,    _(u'related to the email'), []))

        create_hf = HeaderFilter.create
        create_hf(pk=constants.DEFAULT_HFILTER_MAILINGLIST,
                  model=MailingList,
                  name=_(u'Mailing list view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_CAMPAIGN,
                  model=EmailCampaign,
                  name=_(u'Campaign view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_TEMPLATE,
                  model=EmailTemplate,
                  name=_(u'Email template view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'subject'}),
                             ],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_EMAIL,
                  model=EntityEmail,
                  name=_(u'Email view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'sender'}),
                              (EntityCellRegularField, {'name': 'recipient'}),
                              (EntityCellRegularField, {'name': 'subject'}),
                             ],
                 )

        create_searchconf = SearchConfigItem.create_if_needed
        create_searchconf(EmailCampaign, ['name', 'mailing_lists__name'])
        create_searchconf(MailingList,   ['name', 'children__name', 'contacts__first_name', 'contacts__last_name', 'organisations__name'])
        create_searchconf(EmailTemplate, ['name', 'subject', 'body', 'attachments__title'])
        create_searchconf(EntityEmail,   ['sender', 'recipient', 'subject'])

        if not already_populated:
            get_ct = ContentType.objects.get_for_model
            create_cbci = CustomBlockConfigItem.objects.create
            build_cell = EntityCellRegularField.build

            cbci_email = create_cbci(id='emails-entityemail_info',
                                     name=_(u'Email information'),
                                     content_type=get_ct(EntityEmail),
                                     cells=[build_cell(EntityEmail, 'user'),
                                            build_cell(EntityEmail, 'reads'),
                                            build_cell(EntityEmail, 'status'),
                                            build_cell(EntityEmail, 'sender'),
                                            build_cell(EntityEmail, 'recipient'),
                                            build_cell(EntityEmail, 'subject'),
                                            build_cell(EntityEmail, 'reception_date'),
                                            build_cell(EntityEmail, 'attachments'),
                                            build_cell(EntityEmail, 'body'),
                                           ],
                                    )
            cbci_template = create_cbci(id='emails-emailtemplate_info',
                                        name=_(u'Email template information'),
                                        content_type=get_ct(EmailTemplate),
                                        cells=[build_cell(EmailTemplate, 'created'),
                                               build_cell(EmailTemplate, 'modified'),
                                               build_cell(EmailTemplate, 'user'),
                                               build_cell(EmailTemplate, 'name'),
                                               build_cell(EmailTemplate, 'subject'),
                                               build_cell(EmailTemplate, 'body'),
                                               build_cell(EmailTemplate, 'signature'),
                                              ],
                                       )

            create_bdl = BlockDetailviewLocation.create
            TOP   = BlockDetailviewLocation.TOP
            LEFT  = BlockDetailviewLocation.LEFT
            RIGHT = BlockDetailviewLocation.RIGHT

            create_bdl(block_id=cbci_email.generate_id(),         order=5,   zone=LEFT,  model=EntityEmail)
            create_bdl(block_id=blocks.email_html_body_block.id_, order=20,  zone=LEFT,  model=EntityEmail)
            create_bdl(block_id=customfields_block.id_,           order=40,  zone=LEFT,  model=EntityEmail)
            create_bdl(block_id=properties_block.id_,             order=450, zone=LEFT,  model=EntityEmail)
            create_bdl(block_id=relations_block.id_,              order=500, zone=LEFT,  model=EntityEmail)
            create_bdl(block_id=history_block.id_,                order=20,  zone=RIGHT, model=EntityEmail)

            BlockDetailviewLocation.create_4_model_block(order=5,             zone=LEFT,  model=MailingList)
            create_bdl(block_id=customfields_block.id_,            order=40,  zone=LEFT,  model=MailingList)
            create_bdl(block_id=blocks.email_recipients_block.id_, order=80,  zone=LEFT,  model=MailingList)
            create_bdl(block_id=blocks.contacts_block.id_,         order=90,  zone=LEFT,  model=MailingList)
            create_bdl(block_id=blocks.organisations_block.id_,    order=95,  zone=LEFT,  model=MailingList)
            create_bdl(block_id=blocks.child_lists_block.id_,      order=100, zone=LEFT,  model=MailingList)
            create_bdl(block_id=blocks.parent_lists_block.id_,     order=105, zone=LEFT,  model=MailingList)
            create_bdl(block_id=properties_block.id_,              order=450, zone=LEFT,  model=MailingList)
            create_bdl(block_id=relations_block.id_,               order=500, zone=LEFT,  model=MailingList)
            create_bdl(block_id=history_block.id_,                 order=20,  zone=RIGHT, model=MailingList)

            create_bdl(block_id=blocks.sendings_block.id_,      order=2,   zone=TOP,   model=EmailCampaign)
            BlockDetailviewLocation.create_4_model_block(order=5,          zone=LEFT,  model=EmailCampaign)
            create_bdl(block_id=customfields_block.id_,         order=40,  zone=LEFT,  model=EmailCampaign)
            create_bdl(block_id=blocks.mailing_lists_block.id_, order=120, zone=LEFT,  model=EmailCampaign)
            create_bdl(block_id=properties_block.id_,           order=450, zone=LEFT,  model=EmailCampaign)
            create_bdl(block_id=relations_block.id_,            order=500, zone=LEFT,  model=EmailCampaign)
            create_bdl(block_id=history_block.id_,              order=20,  zone=RIGHT, model=EmailCampaign)

            # BlockDetailviewLocation.create_4_model_block(order=5,          zone=LEFT,  model=EmailTemplate)
            create_bdl(block_id=cbci_template.generate_id(),         order=5,   zone=LEFT,  model=EmailTemplate)
            create_bdl(block_id=customfields_block.id_,              order=40,  zone=LEFT,  model=EmailTemplate)
            create_bdl(block_id=blocks.attachments_block.id_,        order=60,  zone=LEFT,  model=EmailTemplate)
            create_bdl(block_id=blocks.template_html_body_block.id_, order=70,  zone=LEFT,  model=EmailTemplate)
            create_bdl(block_id=properties_block.id_,                order=450, zone=LEFT,  model=EmailTemplate)
            create_bdl(block_id=relations_block.id_,                 order=500, zone=LEFT,  model=EmailTemplate)
            create_bdl(block_id=history_block.id_,                   order=20,  zone=RIGHT, model=EmailTemplate)

            # 'persons' app
            create_bdl(block_id=blocks.mails_history_block.id_, order=600, zone=RIGHT, model=Contact)
            create_bdl(block_id=blocks.mails_history_block.id_, order=600, zone=RIGHT, model=Organisation)

            BlockPortalLocation.create(app_name='emails', block_id=blocks.signatures_block.id_, order=10)
            BlockPortalLocation.create(app_name='emails', block_id=history_block.id_,    order=30)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

                for model in (MailingList, EmailCampaign, EmailTemplate):
                    create_bdl(block_id=todos_block.id_,    order=100, zone=RIGHT, model=model)
                    create_bdl(block_id=memos_block.id_,    order=200, zone=RIGHT, model=model)
                    create_bdl(block_id=alerts_block.id_,   order=300, zone=RIGHT, model=model)
                    create_bdl(block_id=messages_block.id_, order=400, zone=RIGHT, model=model)

                BlockPortalLocation.create(app_name='emails', block_id=memos_block.id_,    order=100)
                BlockPortalLocation.create(app_name='emails', block_id=alerts_block.id_,   order=200)
                BlockPortalLocation.create(app_name='emails', block_id=messages_block.id_, order=300)

            ButtonMenuItem.create_if_needed(pk='emails-entity_email_link_button', model=EntityEmail, button=entityemail_link_button, order=20)
