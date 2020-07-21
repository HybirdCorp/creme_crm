# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from creme import persons
from creme.creme_core import bricks as core_bricks
from creme.creme_core import constants as core_constants
from creme.creme_core.core.entity_cell import (
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.entity_filter import (
    condition_handler,
    operands,
    operators,
)
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    ButtonMenuItem,
    CustomBrickConfigItem,
    EntityFilter,
    HeaderFilter,
    RelationBrickItem,
    RelationType,
    SearchConfigItem,
)
from creme.creme_core.utils import create_if_needed

from . import bricks, buttons, constants
from .models import Civility, LegalForm, Position, Sector, StaffSize

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        already_populated = RelationType.objects.filter(
            pk=constants.REL_SUB_EMPLOYED_BY,
        ).exists()

        Contact      = persons.get_contact_model()
        Organisation = persons.get_organisation_model()

        rt_map = {}
        for rt_info in [
            (
                (constants.REL_SUB_EMPLOYED_BY, _('is an employee of'), [Contact]),
                (constants.REL_OBJ_EMPLOYED_BY, _('employs'),           [Organisation]),
            ), (
                (
                    constants.REL_SUB_CUSTOMER_SUPPLIER,
                    _('is a customer of'),
                    [Contact, Organisation],
                ),
                (
                    constants.REL_OBJ_CUSTOMER_SUPPLIER,
                    _('is a supplier of'),
                    [Contact, Organisation],
                ),
            ), (
                (constants.REL_SUB_MANAGES, _('manages'),    [Contact]),
                (constants.REL_OBJ_MANAGES, _('managed by'), [Organisation]),
            ), (
                (constants.REL_SUB_PROSPECT, _('is a prospect of'), [Contact, Organisation]),
                (constants.REL_OBJ_PROSPECT, _('has as prospect'),  [Contact, Organisation]),
            ), (
                (constants.REL_SUB_SUSPECT, _('is a suspect of'), [Contact, Organisation]),
                (constants.REL_OBJ_SUSPECT, _('has as suspect'),  [Contact, Organisation]),
            ), (
                (constants.REL_SUB_PARTNER, _('is a partner of'), [Contact, Organisation]),
                (constants.REL_OBJ_PARTNER, _('has as partner'),  [Contact, Organisation]),
            ), (
                (
                    constants.REL_SUB_INACTIVE,
                    _('is an inactive customer of'),
                    [Contact, Organisation],
                ),
                (
                    constants.REL_OBJ_INACTIVE,
                    _('has as inactive customer'),
                    [Contact, Organisation],
                ),
            ), (
                (constants.REL_SUB_SUBSIDIARY, _('has as subsidiary'),  [Organisation]),
                (constants.REL_OBJ_SUBSIDIARY, _('is a subsidiary of'), [Organisation]),
            ), (
                (constants.REL_SUB_COMPETITOR, _('is a competitor of'), [Contact, Organisation]),
                (constants.REL_OBJ_COMPETITOR, _('has as competitor'),  [Contact, Organisation]),
            ),
        ]:
            rt, sym_rt = RelationType.create(*rt_info)
            rt_map[rt.id] = rt
            rt_map[sym_rt.id] = sym_rt

        get_rtype = RelationType.objects.get
        get_rtype(pk=core_constants.REL_SUB_HAS).add_subject_ctypes(Contact, Organisation)
        get_rtype(pk=core_constants.REL_OBJ_HAS).add_subject_ctypes(Organisation)

        # ---------------------------
        EntityFilter.objects.smart_update_or_create(
            constants.FILTER_MANAGED_ORGA, name=_('Managed by creme'),
            model=Organisation, user='admin',
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Organisation,
                    operator=operators.EqualsOperator,
                    field_name='is_managed',
                    values=[True],
                ),
            ],
        )
        EntityFilter.objects.smart_update_or_create(
            constants.FILTER_CONTACT_ME, name=_('Me'),
            model=Contact, user='admin',
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Contact,
                    operator=operators.EqualsOperator,
                    field_name='is_user',
                    values=[operands.CurrentUserOperand.type_id],
                ),
            ],
        )

        # ---------------------------
        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(
            pk=constants.DEFAULT_HFILTER_CONTACT, model=Contact,
            name=_('Contact view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'last_name'}),
                (EntityCellRegularField, {'name': 'first_name'}),
                (EntityCellRegularField, {'name': 'phone'}),
                (EntityCellRegularField, {'name': 'email'}),
                (EntityCellRegularField, {'name': 'user'}),
                EntityCellRelation(model=Contact, rtype=rt_map[constants.REL_SUB_EMPLOYED_BY]),
            ],
        )
        create_hf(
            pk=constants.DEFAULT_HFILTER_ORGA, model=Organisation,
            name=_('Organisation view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'phone'}),
                (EntityCellRegularField, {'name': 'user'}),
                EntityCellRelation(model=Organisation, rtype=rt_map[constants.REL_OBJ_MANAGES]),
            ],
        )
        create_hf(
            pk=constants.DEFAULT_HFILTER_ORGA_CUSTOMERS, model=Organisation,
            name=_('Prospect/Suspect view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'sector'}),
                (EntityCellRegularField, {'name': 'phone'}),
                (EntityCellRegularField, {'name': 'email'}),
                (EntityCellRegularField, {'name': 'user'}),
                EntityCellRelation(
                    model=Organisation, rtype=rt_map[constants.REL_SUB_CUSTOMER_SUPPLIER],
                ),
                EntityCellRelation(
                    model=Organisation, rtype=rt_map[constants.REL_SUB_PROSPECT],
                ),
                EntityCellRelation(
                    model=Organisation, rtype=rt_map[constants.REL_SUB_SUSPECT],
                ),
            ],
        )

        # ---------------------------
        create_sci = SearchConfigItem.objects.create_if_needed
        create_sci(Contact, ['last_name', 'first_name', 'phone', 'mobile', 'email'])
        create_sci(Organisation, ['name', 'phone', 'email', 'sector__title', 'legal_form__title'])

        # ---------------------------
        if not already_populated:
            create_if_needed(Civility, {'pk': 1}, title=_('Madam'),  shortcut=_('Mrs.'))
            create_if_needed(Civility, {'pk': 2}, title=_('Miss'),   shortcut=_('Ms.'))
            create_if_needed(Civility, {'pk': 3}, title=_('Mister'), shortcut=_('Mr.'))
            create_if_needed(Civility, {'pk': 4}, title=_('N/A'),    shortcut='')

            # ---------------------------
            # TODO: add relation to admin ????
            if not Organisation.objects.exists():
                Organisation.objects.create(
                    user=get_user_model().objects.get_admin(),
                    name=_('ReplaceByYourSociety'), is_managed=True,
                    uuid=constants.UUID_FIRST_ORGA,
                )

            # ---------------------------
            create_if_needed(Position, {'pk': 1}, title=_('CEO'))
            create_if_needed(Position, {'pk': 2}, title=_('Secretary'))
            create_if_needed(Position, {'pk': 3}, title=_('Technician'))

            # ---------------------------
            create_if_needed(Sector, {'pk': 1}, title=_('Food Industry'))
            create_if_needed(Sector, {'pk': 2}, title=_('Industry'))
            create_if_needed(Sector, {'pk': 3}, title=_('Software'))
            create_if_needed(Sector, {'pk': 4}, title=_('Telecom'))
            create_if_needed(Sector, {'pk': 5}, title=_('Restoration'))

            # ---------------------------
            # TODO: depend on the country no ??
            create_if_needed(LegalForm, {'pk': 1}, title='SARL')
            create_if_needed(LegalForm, {'pk': 2}, title='Association loi 1901')
            create_if_needed(LegalForm, {'pk': 3}, title='SA')
            create_if_needed(LegalForm, {'pk': 4}, title='SAS')

            # ---------------------------
            create_if_needed(StaffSize, {'pk': 1}, size='1 - 5',     order=1)
            create_if_needed(StaffSize, {'pk': 2}, size='6 - 10',    order=2)
            create_if_needed(StaffSize, {'pk': 3}, size='11 - 50',   order=3)
            create_if_needed(StaffSize, {'pk': 4}, size='51 - 100',  order=4)
            create_if_needed(StaffSize, {'pk': 5}, size='100 - 500', order=5)
            create_if_needed(StaffSize, {'pk': 6}, size='> 500',     order=6)

            # ---------------------------
            create_bmi = ButtonMenuItem.objects.create_if_needed
            create_bmi(
                pk='persons-customer_contact_button',
                model=Contact, button=buttons.BecomeCustomerButton, order=20,
            )
            create_bmi(
                pk='persons-prospect_contact_button',
                model=Contact, button=buttons.BecomeProspectButton, order=21,
            )
            create_bmi(
                pk='persons-suspect_contact_button',
                model=Contact, button=buttons.BecomeSuspectButton,  order=22,
            )
            create_bmi(
                pk='persons-inactive_contact_button',
                model=Contact, button=buttons.BecomeInactiveButton, order=24,
            )

            create_bmi(
                pk='persons-customer_orga_button',
                model=Organisation, button=buttons.BecomeCustomerButton,   order=20,
            )
            create_bmi(
                pk='persons-prospect_orga_button',
                model=Organisation, button=buttons.BecomeProspectButton,   order=21,
            )
            create_bmi(
                pk='persons-suspect_orga_button',
                model=Organisation, button=buttons.BecomeSuspectButton,    order=22,
            )
            create_bmi(
                pk='persons-inactive_orga_button',
                model=Organisation, button=buttons.BecomeInactiveButton,   order=23,
            )
            create_bmi(
                pk='persons-supplier_button',
                model=Organisation, button=buttons.BecomeSupplierButton,   order=24,
            )
            create_bmi(
                pk='persons-linked_contact_button',
                model=Organisation, button=buttons.AddLinkedContactButton, order=25,
            )

            # Populate bricks ------------------
            create_rbi = RelationBrickItem.objects.create_if_needed
            rbi_1 = create_rbi(constants.REL_SUB_CUSTOMER_SUPPLIER)
            rbi_2 = create_rbi(constants.REL_OBJ_CUSTOMER_SUPPLIER)

            create_cbci = CustomBrickConfigItem.objects.create
            build_cell = EntityCellRegularField.build

            # cbci_orga_1 =
            create_cbci(
                id='persons-organisation_main_info',
                name=_('Organisation information'),
                content_type=Organisation,
                cells=[
                    build_cell(Organisation, 'name'),
                    build_cell(Organisation, 'is_managed'),
                    build_cell(Organisation, 'staff_size'),
                    build_cell(Organisation, 'legal_form'),
                    build_cell(Organisation, 'sector'),
                    build_cell(Organisation, 'capital'),
                    build_cell(Organisation, 'siren'),
                    build_cell(Organisation, 'naf'),
                    build_cell(Organisation, 'siret'),
                    build_cell(Organisation, 'rcs'),
                    build_cell(Organisation, 'tvaintra'),
                    build_cell(Organisation, 'subject_to_vat'),
                    build_cell(Organisation, 'annual_revenue'),
                    build_cell(Organisation, 'creation_date'),
                    build_cell(Organisation, 'image'),
                    # --
                    build_cell(Organisation, 'description'),
                    # --
                    build_cell(Organisation, 'created'),
                    build_cell(Organisation, 'modified'),
                    build_cell(Organisation, 'user'),
                ],
            )
            # cbci_orga_2 =
            create_cbci(
                id='persons-organisation_details',
                name=_('Organisation details'),
                content_type=Organisation,
                cells=[
                    build_cell(Organisation, 'phone'),
                    build_cell(Organisation, 'fax'),
                    build_cell(Organisation, 'email'),
                    build_cell(Organisation, 'url_site'),
                ],
            )
            cbci_orga_extra = create_cbci(
                id='persons-organisation_complementary',
                name=_('Organisation complementary information'),
                content_type=Organisation,
                cells=[
                    build_cell(Organisation, 'staff_size'),
                    build_cell(Organisation, 'sector'),
                    build_cell(Organisation, 'capital'),
                    build_cell(Organisation, 'siren'),
                    build_cell(Organisation, 'naf'),
                    build_cell(Organisation, 'siret'),
                    build_cell(Organisation, 'rcs'),
                    build_cell(Organisation, 'tvaintra'),
                    build_cell(Organisation, 'subject_to_vat'),
                    build_cell(Organisation, 'annual_revenue'),
                    build_cell(Organisation, 'creation_date'),
                    build_cell(Organisation, 'image'),
                    # --
                    build_cell(Organisation, 'description'),
                    # --
                    build_cell(Organisation, 'fax'),
                    build_cell(Organisation, 'email'),
                    build_cell(Organisation, 'url_site'),
                ],
            )

            HAT   = BrickDetailviewLocation.HAT
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Organisation, 'zone': LEFT},
                data=[
                    {'brick': bricks.OrganisationCardHatBrick, 'order': 1, 'zone': HAT},

                    {'brick': cbci_orga_extra.brick_id,         'order':   5},
                    {'brick': core_bricks.CustomFieldsBrick,    'order':  40},
                    {'brick': bricks.PrettyAddressesBrick,      'order':  50},
                    {'brick': bricks.PrettyOtherAddressesBrick, 'order':  60},
                    {'brick': bricks.ManagersBrick,             'order': 100},
                    {'brick': bricks.EmployeesBrick,            'order': 120},
                    {'brick': core_bricks.PropertiesBrick,      'order': 450},
                    {'brick': core_bricks.RelationsBrick,       'order': 500},

                    {'brick': rbi_1.brick_id,           'order':   5, 'zone': RIGHT},
                    {'brick': rbi_2.brick_id,           'order':  10, 'zone': RIGHT},
                    {'brick': core_bricks.HistoryBrick, 'order':  30, 'zone': RIGHT},
                ],
            )

            create_cbci(
                id='persons-contact_main_info',
                name=_('Contact information'),
                content_type=Contact,
                cells=[
                    build_cell(Contact, 'civility'),
                    build_cell(Contact, 'first_name'),
                    build_cell(Contact, 'last_name'),
                    build_cell(Contact, 'sector'),
                    build_cell(Contact, 'position'),
                    build_cell(Contact, 'full_position'),
                    build_cell(Contact, 'is_user'),
                    build_cell(Contact, 'birthday'),
                    build_cell(Contact, 'image'),
                    # --
                    build_cell(Contact, 'description'),
                    # --
                    build_cell(Contact, 'created'),
                    build_cell(Contact, 'modified'),
                    build_cell(Contact, 'user'),
                ],
            )
            create_cbci(
                id='persons-contact_details',
                name=_('Contact details'),
                content_type=Contact,
                cells=[
                    build_cell(Contact, 'phone'),
                    build_cell(Contact, 'mobile'),
                    build_cell(Contact, 'fax'),
                    build_cell(Contact, 'email'),
                    build_cell(Contact, 'url_site'),
                    build_cell(Contact, 'skype'),
                ],
            )
            cbci_contact_extra = create_cbci(
                id='persons-contact_complementary',
                name=_('Contact complementary information'),
                content_type=Contact,
                cells=[
                    build_cell(Contact, 'sector'),
                    build_cell(Contact, 'full_position'),
                    build_cell(Contact, 'birthday'),
                    build_cell(Contact, 'image'),
                    # --
                    build_cell(Contact, 'description'),
                    # --
                    build_cell(Contact, 'fax'),
                    build_cell(Contact, 'url_site'),
                    build_cell(Contact, 'skype'),
                ],
            )

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Contact, 'zone': LEFT},
                data=[
                    {'brick': bricks.ContactCardHatBrick, 'order': 1, 'zone': HAT},

                    {'brick': cbci_contact_extra.brick_id,      'order':  30},
                    {'brick': core_bricks.CustomFieldsBrick,    'order':  40},
                    {'brick': bricks.PrettyAddressesBrick,      'order':  50},
                    {'brick': bricks.PrettyOtherAddressesBrick, 'order':  60},
                    {'brick': core_bricks.PropertiesBrick,      'order': 450},
                    {'brick': core_bricks.RelationsBrick,       'order': 500},

                    {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
                ],
            )

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed'
                    ' => we use the assistants blocks on detail views and portal'
                )

                from creme.assistants import bricks as a_bricks

                for model in (Contact, Organisation):
                    BrickDetailviewLocation.objects.multi_create(
                        defaults={'model': model, 'zone': RIGHT},
                        data=[
                            {'brick': a_bricks.TodosBrick,        'order': 100},
                            {'brick': a_bricks.MemosBrick,        'order': 200},
                            {'brick': a_bricks.AlertsBrick,       'order': 300},
                            {'brick': a_bricks.UserMessagesBrick, 'order': 500},
                        ],
                    )

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed
                # => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                BrickDetailviewLocation.objects.multi_create(
                    defaults={'brick': LinkedDocsBrick, 'order': 600, 'zone': RIGHT},
                    data=[
                        {'model': Contact},
                        {'model': Organisation},
                    ],
                )

            if apps.is_installed('creme.activities'):
                BrickHomeLocation.objects.create(
                    brick_id=bricks.NeglectedOrganisationsBrick.id_, order=15,
                )
