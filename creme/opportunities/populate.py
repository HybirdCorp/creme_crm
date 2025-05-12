################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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
from django.utils.translation import pgettext

import creme.creme_core.bricks as core_bricks
from creme import persons, products
from creme.creme_core.core.entity_cell import (
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    ButtonMenuItem,
    CustomBrickConfigItem,
    CustomFormConfigItem,
    EntityFilter,
    HeaderFilter,
    MenuConfigItem,
    RelationType,
    SearchConfigItem,
    SettingValue,
)

from . import (
    bricks,
    constants,
    custom_forms,
    get_opportunity_model,
    menu,
    setting_keys,
)
from .buttons import LinkedOpportunityButton
from .models import Origin, SalesPhase

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons', 'activities', 'products', 'billing']

    SEARCH = ['name', 'made_sales', 'sales_phase__name', 'origin__name']
    SALES_PHASES = [
        # is_custom=True => only created during the first execution
        SalesPhase(
            uuid='9fc5ff38-b358-4131-b03e-6c1f800bfb08',
            order=1, name=_('Forthcoming'),
        ),
        SalesPhase(
            uuid='4445c750-bcec-4fcd-afb2-c9e35a3bf38c',
            order=2, name=_('In progress'),
        ),
        SalesPhase(
            uuid='aa59fcec-2dde-46e1-a362-c30c18386c19',
            order=3, name=_('Under negotiation'),
        ),
        SalesPhase(
            uuid='779931a8-a2ed-47b1-96a1-8694452e9905',
            order=4, name=pgettext('opportunities-sales_phase', 'Abandoned'),
        ),
        SalesPhase(
            uuid='d8b5429f-89e5-46cc-9e53-5d1a0127f880',
            order=5, name=pgettext('opportunities-sales_phase', 'Won'),
            won=True, color='1dd420',
        ),
        SalesPhase(
            uuid='597d796e-a368-48f0-8dfb-56f16965792b',
            order=6, name=pgettext('opportunities-sales_phase', 'Lost'),
            lost=True, color='ae4444',
        ),
    ]
    ORIGINS = [
        # is_custom=True => only created during the first execution
        Origin(
            uuid='814e485e-418a-42d5-a6ef-720aaffee7a0',
            name=pgettext('opportunities-origin', 'None'),
        ),
        Origin(
            uuid='96f55fa8-df31-4d64-8f7e-c0b5f1ca0bc6',
            name=_('Web site'),
        ),
        Origin(
            uuid='0e914271-b162-4554-afae-837916378220',
            name=_('Mouth'),
        ),
        Origin(
            uuid='14d5bb2f-5ad7-46ab-a194-59f2bb105b66',
            name=_('Show'),
        ),
        Origin(
            uuid='0f23d337-7a64-4f22-9448-7c0d2df9891b',
            name=_('Direct email'),
        ),
        Origin(
            uuid='b4e097b9-05c0-4fc9-8c12-bc62cf106046',
            name=_('Direct phone call'),
        ),
        Origin(
            uuid='c8632a03-4b78-4c00-8e45-7b04bacab2e8',
            name=_('Employee'),
        ),
        Origin(
            uuid='9bb9012f-a4dd-4e4c-8fb8-65c2aaaea789',
            name=_('Partner'),
        ),
        Origin(
            uuid='4b0a0229-cd0d-400d-8fb5-29a1479c41fe',
            name=pgettext('opportunities-origin', 'Other'),
        ),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.Contact      = persons.get_contact_model()
        self.Organisation = persons.get_organisation_model()

        self.Product = products.get_product_model()
        self.Service = products.get_service_model()

        self.Opportunity = get_opportunity_model()

    def _already_populated(self):
        return RelationType.objects.filter(pk=constants.REL_SUB_TARGETS).exists()

    def _populate(self):
        super()._populate()
        self._populate_phases()
        self._populate_origins()

    def _first_populate(self):
        super()._first_populate()

        if apps.is_installed('creme.reports'):
            logger.info(
                'Reports app is installed'
                ' => we create an Opportunity report, with 2 graphs, and related blocks'
            )
            self._populate_report_n_graphes()

    def _populate_phases(self):
        # create_sphase = SalesPhase.objects.create
        # create_sphase(order=1, name=_('Forthcoming'))
        # create_sphase(order=2, name=_('In progress'))
        # create_sphase(order=3, name=_('Under negotiation'))
        # create_sphase(
        #     order=4, name=pgettext('opportunities-sales_phase', 'Abandoned'),
        # )
        # create_sphase(
        #     order=5, name=pgettext('opportunities-sales_phase', 'Won'),
        #     won=True, color='1dd420',
        # )
        # create_sphase(
        #     order=6, name=pgettext('opportunities-sales_phase', 'Lost'),
        #     lost=True, color='ae4444',
        # )
        self._save_minions(self.SALES_PHASES)

    def _populate_origins(self):
        # create_origin = Origin.objects.create
        # create_origin(name=pgettext('opportunities-origin', 'None'))
        # create_origin(name=_('Web site'))
        # create_origin(name=_('Mouth'))
        # create_origin(name=_('Show'))
        # create_origin(name=_('Direct email'))
        # create_origin(name=_('Direct phone call'))
        # create_origin(name=_('Employee'))
        # create_origin(name=_('Partner'))
        # create_origin(name=pgettext('opportunities-origin', 'Other'))
        self._save_minions(self.ORIGINS)

    def _populate_relation_types(self):
        Opportunity = self.Opportunity
        Contact = self.Contact
        Organisation = self.Organisation

        create_rtype = RelationType.objects.smart_update_or_create
        # rt_sub_targets = create_rtype(...)[0]
        create_rtype(
            (
                constants.REL_SUB_TARGETS,
                _('targets the organisation/contact'),
                [Opportunity],
            ), (
                constants.REL_OBJ_TARGETS,
                _('targeted by the opportunity'),
                [Organisation, Contact],
            ),
            is_internal=True,
            minimal_display=(True, True),
        )
        # rt_obj_emit_orga = create_rtype(...)[1]
        create_rtype(
            (
                constants.REL_SUB_EMIT_ORGA,
                _('has generated the opportunity'),
                [Organisation],
            ), (
                constants.REL_OBJ_EMIT_ORGA,
                _('has been generated by'),
                [Opportunity],
            ),
            is_internal=True,
            minimal_display=(True, True),
        )
        create_rtype(
            (constants.REL_SUB_LINKED_PRODUCT, _('is linked to the opportunity'), [self.Product]),
            (constants.REL_OBJ_LINKED_PRODUCT, _('concerns the product'),         [Opportunity])
        )
        create_rtype(
            (constants.REL_SUB_LINKED_SERVICE, _('is linked to the opportunity'), [self.Service]),
            (constants.REL_OBJ_LINKED_SERVICE, _('concerns the service'),         [Opportunity]),
        )
        create_rtype(
            (constants.REL_SUB_LINKED_CONTACT, _('involves in the opportunity'),  [Contact]),
            (constants.REL_OBJ_LINKED_CONTACT, _('stages'),                       [Opportunity])),
        create_rtype(
            (constants.REL_SUB_RESPONSIBLE,    _('is responsible for'),           [Contact]),
            (constants.REL_OBJ_RESPONSIBLE,    _('has as responsible contact'),   [Opportunity]),
        )

        if apps.is_installed('creme.activities'):
            logger.info(
                'Activities app is installed'
                ' => an Opportunity can be the subject of an Activity'
            )

            from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

            RelationType.objects.get(
                pk=REL_SUB_ACTIVITY_SUBJECT,
            ).add_subject_ctypes(Opportunity)

        if apps.is_installed('creme.billing'):
            logger.info(
                'Billing app is installed'
                ' => we create relationships between Opportunities & billing models'
            )

            from creme import billing

            Invoice    = billing.get_invoice_model()
            Quote      = billing.get_quote_model()
            SalesOrder = billing.get_sales_order_model()

            create_rtype(
                (
                    constants.REL_SUB_LINKED_SALESORDER,
                    _('is associate with the opportunity'),
                    [SalesOrder],
                ), (
                    constants.REL_OBJ_LINKED_SALESORDER,
                    _('has generated the salesorder'),
                    [Opportunity]
                ),
            )
            create_rtype(
                (
                    constants.REL_SUB_LINKED_INVOICE,
                    pgettext('opportunities-invoice', 'generated for the opportunity'),
                    [Invoice],
                ), (
                    constants.REL_OBJ_LINKED_INVOICE,
                    _('has resulted in the invoice'),
                    [Opportunity],
                ),
            )
            create_rtype(
                (
                    constants.REL_SUB_LINKED_QUOTE,
                    pgettext('opportunities-quote', 'generated for the opportunity'),
                    [Quote],
                ), (
                    constants.REL_OBJ_LINKED_QUOTE,
                    _('has resulted in the quote'),
                    [Opportunity],
                ),
            )
            create_rtype(
                (
                    constants.REL_SUB_CURRENT_DOC,
                    _('is the current accounting document of'),
                    [SalesOrder, Invoice, Quote],
                ), (
                    constants.REL_OBJ_CURRENT_DOC,
                    _('has as current accounting document'),
                    [Opportunity],
                ),
            )

    def _populate_entity_filters(self):
        create_efilter = partial(
            EntityFilter.objects.smart_update_or_create,
            model=self.Opportunity, user='admin',
        )
        build_cond = partial(
            condition_handler.RegularFieldConditionHandler.build_condition,
            model=self.Opportunity,
        )
        create_efilter(
            'opportunities-opportunities_won',
            name=_('Opportunities won'),
            conditions=[
                build_cond(
                    operator=operators.EqualsOperator,
                    field_name='sales_phase__won',
                    values=[True],
                ),
            ],
        )
        create_efilter(
            'opportunities-opportunities_lost',
            name=_('Opportunities lost'),
            conditions=[
                build_cond(
                    operator=operators.EqualsOperator,
                    field_name='sales_phase__lost',
                    values=[True],
                ),
            ],
        )
        create_efilter(
            'opportunities-neither_won_nor_lost_opportunities',
            name=_('Neither won nor lost opportunities'),
            conditions=[
                build_cond(
                    operator=operators.EqualsNotOperator,
                    field_name='sales_phase__won',
                    values=[True],
                ),
                build_cond(
                    operator=operators.EqualsNotOperator,
                    field_name='sales_phase__lost',
                    values=[True],
                ),
            ],
        )

    def _populate_header_filters(self):
        HeaderFilter.objects.create_if_needed(
            pk=constants.DEFAULT_HFILTER_OPPORTUNITY, model=self.Opportunity,
            name=_('Opportunity view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                # EntityCellRelation(model=self.Opportunity, rtype=rt_sub_targets),
                EntityCellRelation(
                    model=self.Opportunity,
                    rtype=RelationType.objects.get(id=constants.REL_SUB_TARGETS),
                ),
                (EntityCellRegularField, {'name': 'sales_phase'}),
                (EntityCellRegularField, {'name': 'estimated_sales'}),
                (EntityCellRegularField, {'name': 'made_sales'}),
                (EntityCellRegularField, {'name': 'closing_date'}),
            ],
        )

    def _populate_custom_forms(self):
        create_cfci = CustomFormConfigItem.objects.create_if_needed
        create_cfci(descriptor=custom_forms.OPPORTUNITY_CREATION_CFORM)
        create_cfci(descriptor=custom_forms.OPPORTUNITY_EDITION_CFORM)

    def _populate_search_config(self):
        SearchConfigItem.objects.create_if_needed(
            model=self.Opportunity, fields=self.SEARCH,
        )

    def _populate_setting_values(self):
        create_sv = SettingValue.objects.get_or_create
        create_sv(key_id=setting_keys.quote_key.id,              defaults={'value': False})
        create_sv(key_id=setting_keys.target_constraint_key.id,  defaults={'value': True})
        create_sv(key_id=setting_keys.emitter_constraint_key.id, defaults={'value': True})

    def _populate_menu_config(self):
        menu_container = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Commercial')},
            role=None, superuser=False,
            defaults={'order': 30},
        )[0]

        MenuConfigItem.objects.create(
            entry_id=menu.OpportunitiesEntry.id, order=10, parent=menu_container,
        )

        creations_entry = MenuConfigItem.objects.filter(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('+ Creation')},
        ).first()
        if creations_entry is not None:
            MenuConfigItem.objects.create(
                entry_id=menu.OpportunityCreationEntry.id,
                order=30, parent=creations_entry,
            )

    def _populate_buttons_config(self):
        create_button = ButtonMenuItem.objects.create_if_needed
        create_button(model=self.Organisation, button=LinkedOpportunityButton, order=1030)
        create_button(model=self.Contact,      button=LinkedOpportunityButton, order=1030)

    def _populate_bricks_config(self):
        Opportunity = self.Opportunity
        LEFT = BrickDetailviewLocation.LEFT
        RIGHT = BrickDetailviewLocation.RIGHT

        build_cell = EntityCellRegularField.build
        cbci = CustomBrickConfigItem.objects.create(
            # id='opportunities-complementary',
            uuid='43ac42b1-3b6d-4c9a-8133-942b19679353',
            name=_('Opportunity complementary information'),
            content_type=Opportunity,
            cells=[
                build_cell(Opportunity, 'reference'),
                build_cell(Opportunity, 'currency'),
                build_cell(Opportunity, 'chance_to_win'),
                build_cell(Opportunity, 'expected_closing_date'),
                build_cell(Opportunity, 'closing_date'),
                build_cell(Opportunity, 'origin'),
                build_cell(Opportunity, 'first_action_date'),
                build_cell(Opportunity, 'description'),
            ],
        )

        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': Opportunity, 'zone': LEFT},
            data=[
                {
                    'brick': bricks.OpportunityCardHatBrick, 'order': 1,
                    'zone': BrickDetailviewLocation.HAT,
                },

                {'brick': cbci.brick_id,                 'order':   5},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': bricks.BusinessManagersBrick,  'order':  60},
                {'brick': bricks.LinkedContactsBrick,    'order':  62},
                {'brick': bricks.LinkedProductsBrick,    'order':  64},
                {'brick': bricks.LinkedServicesBrick,    'order':  66},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {'brick': bricks.OppTargetBrick,    'order':  1, 'zone': RIGHT},
                {'brick': bricks.OppTotalBrick,     'order':  2, 'zone': RIGHT},
                {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
            ],
        )

        if apps.is_installed('creme.activities'):
            logger.info(
                'Activities app is installed'
                ' => we use the "Future activities" & "Past activities" blocks'
            )

            import creme.activities.bricks as act_bricks

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Opportunity, 'zone': RIGHT},
                data=[
                    {'brick': act_bricks.FutureActivitiesBrick, 'order': 20},
                    {'brick': act_bricks.PastActivitiesBrick,   'order': 21},
                ],
            )

        if apps.is_installed('creme.assistants'):
            logger.info(
                'Assistants app is installed'
                ' => we use the assistants blocks on detail views and portal'
            )

            import creme.assistants.bricks as a_bricks

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Opportunity, 'zone': RIGHT},
                data=[
                    {'brick': a_bricks.TodosBrick,        'order': 100},
                    {'brick': a_bricks.MemosBrick,        'order': 200},
                    {'brick': a_bricks.AlertsBrick,       'order': 300},
                    {'brick': a_bricks.UserMessagesBrick, 'order': 500},
                ],
            )

        if apps.is_installed('creme.documents'):
            # logger.info('Documents app is installed
            # => we use the documents block on detail view')

            from creme.documents.bricks import LinkedDocsBrick

            BrickDetailviewLocation.objects.create_if_needed(
                brick=LinkedDocsBrick, order=600, zone=RIGHT,
                model=Opportunity,
            )

        if apps.is_installed('creme.billing'):
            logger.info(
                'Billing app is installed'
                ' => we use the billing blocks on detail view'
            )

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Opportunity, 'zone': LEFT},
                data=[
                    {'brick': bricks.QuotesBrick,      'order': 70},
                    {'brick': bricks.SalesOrdersBrick, 'order': 72},
                    {'brick': bricks.InvoicesBrick,    'order': 74},
                ],
            )

        if apps.is_installed('creme.emails'):
            logger.info(
                'Emails app is installed'
                ' => we use the emails blocks on detail view'
            )

            from creme.emails.bricks import MailsHistoryBrick

            BrickDetailviewLocation.objects.create_if_needed(
                brick=MailsHistoryBrick, order=600, zone=RIGHT,
                model=Opportunity,
            )

        BrickDetailviewLocation.objects.create_if_needed(
            brick=bricks.TargetingOpportunitiesBrick, order=16, zone=RIGHT,
            model=self.Organisation,
        )

    # def create_report_n_graphes(self, rt_obj_emit_orga):
    def _populate_report_n_graphes(self):
        "Create the report 'Opportunities' and 2 ReportGraphs."
        # NB: the fixed UUIDs were added with Creme2.5 in order to facilitate
        #     import/export in 'creme_config'. So the Reports/ReportGraphes
        #     populated with previous versions will have different UUIDs.
        from django.contrib.auth import get_user_model

        from creme import reports
        from creme.creme_core.utils.meta import FieldInfo
        from creme.reports.constants import RFT_FIELD, RFT_RELATION
        from creme.reports.core.graph.fetcher import SimpleGraphFetcher
        from creme.reports.models import Field

        admin = get_user_model().objects.get_admin()

        if reports.report_model_is_custom():
            logger.info('Report model is custom => no Opportunity report is created.')
            return

        Opportunity = self.Opportunity

        # Create the report ----------------------------------------------------
        report = reports.get_report_model().objects.create(
            uuid='18a8226d-c2f1-4732-a4d5-705bd30c141f',
            name=_('Opportunities'),
            user=admin,
            ct=Opportunity,
        )

        # TODO: helper method(s) (see EntityFilterCondition)
        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        create_field(name='name',              order=1)
        create_field(name='estimated_sales',   order=2)
        create_field(name='made_sales',        order=3)
        create_field(name='sales_phase__name', order=4)
        # create_field(name=rt_obj_emit_orga.id, order=5, type=RFT_RELATION)
        create_field(name=constants.REL_OBJ_EMIT_ORGA, order=5, type=RFT_RELATION)

        # Create 2 graphs ------------------------------------------------------
        if reports.rgraph_model_is_custom():
            logger.info(
                'ReportGraph model is custom'
                ' => no Opportunity report-graph is created.'
            )
            return

        sales_cell = EntityCellRegularField.build(Opportunity, 'estimated_sales')
        if sales_cell is None:
            logger.warning(
                'Opportunity seems not having a field "estimated_sales"'
                ' => no ReportGraph created.'
            )
            return

        ReportGraph = reports.get_rgraph_model()

        # TODO: helper method (range only on DateFields etc...)
        create_graph = partial(
            ReportGraph.objects.create,
            linked_report=report, user=admin,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=sales_cell.key,
        )
        esales_vname = FieldInfo(Opportunity, 'estimated_sales').verbose_name
        rgraph1 = create_graph(
            uuid='bab31c4c-368d-4c72-a62b-57350a00f669',
            name=_('Sum {estimated_sales} / {sales_phase}').format(
                estimated_sales=esales_vname,
                sales_phase=FieldInfo(Opportunity, 'sales_phase').verbose_name,
            ),
            abscissa_type=ReportGraph.Group.FK,
            abscissa_cell_value='sales_phase',
        )
        rgraph2 = create_graph(
            uuid='47d9f0db-b96e-48e1-b975-4ffdbe5f4fa4',
            name=_('Sum {estimated_sales} / Quarter (90 days on {closing_date})').format(
                estimated_sales=esales_vname,
                closing_date=FieldInfo(Opportunity, 'closing_date').verbose_name,
            ),
            abscissa_type=ReportGraph.Group.RANGE,
            abscissa_cell_value='closing_date',
            abscissa_parameter='90',
        )

        # Create 2 instance block items for the 2 graphs -----------------------
        brick_id1 = SimpleGraphFetcher(rgraph1).create_brick_config_item(
            uuid='0ba26e9c-5525-4ca1-b7e4-aea9828fc876',
        ).brick_id
        brick_id2 = SimpleGraphFetcher(rgraph2).create_brick_config_item(
            uuid='b3e54a05-f050-4d33-9476-1e8c85aeab08',
        ).brick_id

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            zone=BrickDetailviewLocation.RIGHT, model=Opportunity,
        )
        create_bdl(brick=brick_id1, order=4)
        create_bdl(brick=brick_id2, order=6)

        create_hbl = BrickHomeLocation.objects.create
        create_hbl(brick_id=brick_id1, order=5)
        create_hbl(brick_id=brick_id2, order=6)
