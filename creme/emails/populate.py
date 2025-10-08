################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
from functools import partial

from django.apps import apps
from django.utils.translation import gettext as _

import creme.creme_core.bricks as core_bricks
from creme import emails, persons
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    ButtonMenuItem,
    CustomBrickConfigItem,
    HeaderFilter,
    Job,
    MenuConfigItem,
    RelationType,
    SearchConfigItem,
)
from creme.creme_core.utils.date_period import date_period_registry
from creme.documents.models import FolderCategory

from . import bricks, buttons, constants, creme_jobs, custom_forms, menu

logger = logging.getLogger(__name__)

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()

EntityEmail   = emails.get_entityemail_model()
EmailCampaign = emails.get_emailcampaign_model()
EmailTemplate = emails.get_emailtemplate_model()
MailingList   = emails.get_mailinglist_model()

# UUIDs for instances which can be deleted
UUID_CBRICK_EMAIL    = 'dbabb94a-a92e-41af-89ee-b18a6a920345'
UUID_CBRICK_TEMPLATE = 'b1bf8a0a-26ef-4f05-a666-a328da6c52fd'


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons', 'documents']

    RELATION_TYPES = [
        RelationType.objects.builder(
            id=constants.REL_SUB_MAIL_RECEIVED,
            predicate=_('(email) received by'),
            models=[EntityEmail],
        ).symmetric(
            id=constants.REL_OBJ_MAIL_RECEIVED,
            predicate=_('received the email'),
            models=[Organisation, Contact],
        ),
        RelationType.objects.builder(
            id=constants.REL_SUB_MAIL_SENT,
            predicate=_('(email) sent by'),
            models=[EntityEmail],
        ).symmetric(
            id=constants.REL_OBJ_MAIL_SENT,
            predicate=_('sent the email'),
            models=[Organisation, Contact],
        ),
        RelationType.objects.builder(
            id=constants.REL_SUB_RELATED_TO,
            predicate=_('(email) related to'),
            models=[EntityEmail],
        ).symmetric(
            id=constants.REL_OBJ_RELATED_TO,
            predicate=_('related to the email'),
        ),
    ]
    HEADER_FILTERS = [
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_MAILINGLIST,
            model=MailingList,
            name=_('Mailing list view'),
            cells=[(EntityCellRegularField, 'name')],
        ),
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_CAMPAIGN,
            model=EmailCampaign,
            name=_('Campaign view'),
            cells=[(EntityCellRegularField, 'name')],
        ),
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_TEMPLATE,
            model=EmailTemplate,
            name=_('Email template view'),
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'subject'),
            ],
        ),
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_EMAIL,
            model=EntityEmail,
            name=_('Email view'),
            cells=[
                (EntityCellRegularField, 'sender'),
                (EntityCellRegularField, 'recipient'),
                (EntityCellRegularField, 'subject'),
            ],
        ),
    ]
    JOBS = [
        Job(type=creme_jobs.entity_emails_send_type),
        Job(type=creme_jobs.campaign_emails_send_type),
        Job(type=creme_jobs.workflow_emails_send_type),
        Job(
            type=creme_jobs.entity_emails_sync_type,
            periodicity=date_period_registry.get_period('minutes', 30),
        ),
    ]
    CUSTOM_FORMS = [
        custom_forms.CAMPAIGN_CREATION_CFORM,
        custom_forms.CAMPAIGN_EDITION_CFORM,
        custom_forms.TEMPLATE_CREATION_CFORM,
        custom_forms.TEMPLATE_EDITION_CFORM,
        custom_forms.MAILINGLIST_CREATION_CFORM,
        custom_forms.MAILINGLIST_EDITION_CFORM,
    ]
    BUTTONS = [
        ButtonMenuItem.objects.proxy(
            model=EntityEmail, button=buttons.EntityEmailLinkButton, order=1020,
        ),
    ]
    # SEARCH = {
    #     'CAMPAIGN': ['name', 'mailing_lists__name'],
    #     'MAILING_LIST': [
    #         'name', 'children__name',
    #         'contacts__first_name', 'contacts__last_name',
    #         'organisations__name',
    #     ],
    #     'TEMPLATE': ['name', 'subject', 'body', 'attachments__title'],
    #     'EMAIL': ['sender', 'recipient', 'subject'],
    # }
    SEARCH = [
        SearchConfigItem.objects.builder(
            model=EmailCampaign, fields=['name', 'mailing_lists__name'],
        ),
        SearchConfigItem.objects.builder(
            model=MailingList,
            fields=[
                'name', 'children__name',
                'contacts__first_name', 'contacts__last_name',
                'organisations__name',
            ],
        ),
        SearchConfigItem.objects.builder(
            model=EmailTemplate,
            fields=['name', 'subject', 'body', 'attachments__title'],
        ),
        SearchConfigItem.objects.builder(
            model=EntityEmail, fields=['sender', 'recipient', 'subject'],
        ),
    ]
    FOLDER_CATEGORIES = [
        FolderCategory(
            uuid=constants.UUID_FOLDER_CAT_EMAILS,
            name=_('Documents received by email'),
            is_custom=False,
        ),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.Contact      = persons.get_contact_model()
        # self.Organisation = persons.get_organisation_model()
        #
        # self.EntityEmail   = emails.get_entityemail_model()
        # self.EmailCampaign = emails.get_emailcampaign_model()
        # self.EmailTemplate = emails.get_emailtemplate_model()
        # self.MailingList   = emails.get_mailinglist_model()
        self.Contact      = Contact
        self.Organisation = Organisation

        self.EntityEmail   = EntityEmail
        self.EmailCampaign = EmailCampaign
        self.EmailTemplate = EmailTemplate
        self.MailingList   = MailingList

    def _already_populated(self):
        return RelationType.objects.filter(
            pk=constants.REL_SUB_MAIL_RECEIVED,
        ).exists()

    def _populate(self):
        super()._populate()
        self._populate_folder_categories()

    def _populate_folder_categories(self):
        self._save_minions(self.FOLDER_CATEGORIES)

    # def _populate_relation_types(self):
    #     create_rtype = RelationType.objects.smart_update_or_create
    #     create_rtype(
    #         (
    #             constants.REL_SUB_MAIL_RECEIVED,
    #             _('(email) received by'),
    #             [self.EntityEmail],
    #         ),
    #         (
    #             constants.REL_OBJ_MAIL_RECEIVED,
    #             _('received the email'),
    #             [self.Organisation, self.Contact],
    #         ),
    #     )
    #     create_rtype(
    #         (
    #             constants.REL_SUB_MAIL_SENT,
    #             _('(email) sent by'),
    #             [self.EntityEmail],
    #         ),
    #         (
    #             constants.REL_OBJ_MAIL_SENT,
    #             _('sent the email'),
    #             [self.Organisation, self.Contact],
    #         ),
    #     )
    #     create_rtype(
    #         (constants.REL_SUB_RELATED_TO, _('(email) related to'),   [self.EntityEmail]),
    #         (constants.REL_OBJ_RELATED_TO, _('related to the email'), []),
    #     )

    # def _populate_header_filters(self):
    #     create_hf = HeaderFilter.objects.create_if_needed
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_MAILINGLIST,
    #         model=self.MailingList,
    #         name=_('Mailing list view'),
    #         cells_desc=[(EntityCellRegularField, {'name': 'name'})],
    #     )
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_CAMPAIGN,
    #         model=self.EmailCampaign,
    #         name=_('Campaign view'),
    #         cells_desc=[(EntityCellRegularField, {'name': 'name'})],
    #     )
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_TEMPLATE,
    #         model=self.EmailTemplate,
    #         name=_('Email template view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'name'}),
    #             (EntityCellRegularField, {'name': 'subject'}),
    #         ],
    #     )
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_EMAIL,
    #         model=self.EntityEmail,
    #         name=_('Email view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'sender'}),
    #             (EntityCellRegularField, {'name': 'recipient'}),
    #             (EntityCellRegularField, {'name': 'subject'}),
    #         ],
    #     )

    # def _populate_search_config(self):
    #     create_sci = SearchConfigItem.objects.create_if_needed
    #     create_sci(model=self.EmailCampaign, fields=self.SEARCH['CAMPAIGN'])
    #     create_sci(model=self.MailingList,   fields=self.SEARCH['MAILING_LIST'])
    #     create_sci(model=self.EmailTemplate, fields=self.SEARCH['TEMPLATE'])
    #     create_sci(model=self.EntityEmail,   fields=self.SEARCH['EMAIL'])

    def _populate_menu_config(self):
        menu_container = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Marketing')},
            role=None, superuser=False,
            defaults={'order': 200},
        )[0]

        create_mitem = partial(MenuConfigItem.objects.create, parent=menu_container)
        create_mitem(entry_id=menu.EmailCampaignsEntry.id, order=10)
        create_mitem(entry_id=menu.MailingListsEntry.id,   order=15)
        create_mitem(entry_id=menu.EmailTemplatesEntry.id, order=20)
        create_mitem(entry_id=menu.EntityEmailsEntry.id,   order=25)
        create_mitem(entry_id=menu.EmailSyncEntry.id,      order=30)

    # def _populate_buttons_config(self):
    #     ButtonMenuItem.objects.create_if_needed(
    #         model=self.EntityEmail,
    #         button=buttons.EntityEmailLinkButton,
    #         order=1020,
    #     )

    def _populate_bricks_config_for_email(self):
        EntityEmail = self.EntityEmail
        build_cell = EntityCellRegularField.build
        cbci = CustomBrickConfigItem.objects.create(
            uuid=UUID_CBRICK_EMAIL,
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

        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.EntityEmail, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'brick': cbci.brick_id,                 'order':   5},
                {'brick': bricks.EmailHTMLBodyBrick,     'order':  20},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {
                    'brick': core_bricks.HistoryBrick,
                    'order': 20, 'zone': BrickDetailviewLocation.RIGHT,
                },
            ],
        )

    def _populate_bricks_config_for_mlist(self):
        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.MailingList, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': bricks.EmailRecipientsBrick,   'order':  80},
                {'brick': bricks.ContactsBrick,          'order':  90},
                {'brick': bricks.OrganisationsBrick,     'order':  95},
                {'brick': bricks.ChildListsBrick,        'order': 100},
                {'brick': bricks.ParentListsBrick,       'order': 105},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {
                    'brick': core_bricks.HistoryBrick, 'order': 20,
                    'zone': BrickDetailviewLocation.RIGHT,
                },
            ],
        )

    def _populate_bricks_config_for_template(self):
        EmailTemplate = self.EmailTemplate
        build_cell = EntityCellRegularField.build
        cbci = CustomBrickConfigItem.objects.create(
            uuid=UUID_CBRICK_TEMPLATE,
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

        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.EmailTemplate, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'brick': cbci.brick_id,                 'order':   5},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': bricks.AttachmentsBrick,       'order':  60},
                {'brick': bricks.TemplateHTMLBodyBrick,  'order':  70},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {
                    'brick': core_bricks.HistoryBrick, 'order': 20,
                    'zone': BrickDetailviewLocation.RIGHT,
                },
            ],
        )

    def _populate_bricks_config_for_campaign(self):
        BrickDetailviewLocation.objects.multi_create(
            defaults={
                'model': self.EmailCampaign, 'zone': BrickDetailviewLocation.LEFT,
            },
            data=[
                {
                    'brick': bricks.SendingsBrick, 'order': 2,
                    'zone': BrickDetailviewLocation.TOP,
                },

                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order': 40},
                {'brick': bricks.MailingListsBrick, 'order': 120},
                {'brick': core_bricks.PropertiesBrick, 'order': 450},
                {'brick': core_bricks.RelationsBrick, 'order': 500},

                {
                    'brick': core_bricks.HistoryBrick, 'order': 20,
                    'zone': BrickDetailviewLocation.RIGHT,
                },
            ],
        )

    def _populate_bricks_config_for_persons(self):
        BrickDetailviewLocation.objects.multi_create(
            defaults={
                'brick': bricks.MailsHistoryBrick, 'order': 600,
                'zone': BrickDetailviewLocation.RIGHT,
            },
            data=[
                {'model': self.Contact},
                {'model': self.Organisation},
            ],
        )

    def _populate_bricks_config_for_documents(self):
        # logger.info("Documents app is installed
        # => we use the documents block on EmailCampaign's detail view")

        from creme.documents.bricks import LinkedDocsBrick

        BrickDetailviewLocation.objects.create_if_needed(
            brick=LinkedDocsBrick,
            order=600, zone=BrickDetailviewLocation.RIGHT,
            model=self.EmailCampaign,
        )

    def _populate_bricks_config_for_assistants(self):
        logger.info(
            'Assistants app is installed => we use the assistants blocks on detail views'
        )

        import creme.assistants.bricks as a_bricks

        for model in (self.MailingList, self.EmailCampaign, self.EmailTemplate):
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': model, 'zone': BrickDetailviewLocation.RIGHT},
                data=[
                    {'brick': a_bricks.TodosBrick,        'order': 100},
                    {'brick': a_bricks.MemosBrick,        'order': 200},
                    {'brick': a_bricks.AlertsBrick,       'order': 300},
                    {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                ],
            )

    def _populate_bricks_config(self):
        self._populate_bricks_config_for_email()
        self._populate_bricks_config_for_mlist()
        self._populate_bricks_config_for_template()
        self._populate_bricks_config_for_campaign()

        self._populate_bricks_config_for_persons()

        if apps.is_installed('creme.documents'):
            self._populate_bricks_config_for_documents()

        if apps.is_installed('creme.assistants'):
            self._populate_bricks_config_for_assistants()
