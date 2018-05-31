# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _

from creme.creme_core import bricks as core_bricks, models as core_models
from creme.creme_core.core.entity_cell import EntityCellRegularField, EntityCellRelation
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import EntityFilter, EntityFilterCondition, EntityFilterVariable
from creme.creme_core.utils import create_if_needed

from . import get_contact_model, get_organisation_model
from . import bricks, buttons, constants
from .models import Civility, Sector, Position, StaffSize, LegalForm


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        already_populated = core_models.RelationType.objects.filter(pk=constants.REL_SUB_EMPLOYED_BY).exists()

        Contact = get_contact_model()
        Organisation = get_organisation_model()

        rt_map = {}
        for rt_info in [((constants.REL_SUB_EMPLOYED_BY,       _(u'is an employee of'),          [Contact]),
                         (constants.REL_OBJ_EMPLOYED_BY,       _(u'employs'),                    [Organisation]),
                        ),
                        ((constants.REL_SUB_CUSTOMER_SUPPLIER, _(u'is a customer of'),           [Contact, Organisation]),
                         (constants.REL_OBJ_CUSTOMER_SUPPLIER, _(u'is a supplier of'),           [Contact, Organisation]),
                        ),
                        ((constants.REL_SUB_MANAGES,           _(u'manages'),                    [Contact]),
                         (constants.REL_OBJ_MANAGES,           _(u'managed by'),                 [Organisation]),
                        ),
                        ((constants.REL_SUB_PROSPECT,          _(u'is a prospect of'),           [Contact, Organisation]),
                         (constants.REL_OBJ_PROSPECT,          _(u'has as prospect'),            [Contact, Organisation]),
                        ),
                        ((constants.REL_SUB_SUSPECT,           _(u'is a suspect of'),            [Contact, Organisation]),
                         (constants.REL_OBJ_SUSPECT,           _(u'has as suspect'),             [Contact, Organisation]),
                        ),
                        ((constants.REL_SUB_PARTNER,           _(u'is a partner of'),            [Contact, Organisation]),
                         (constants.REL_OBJ_PARTNER,           _(u'has as partner'),             [Contact, Organisation]),
                        ),
                        ((constants.REL_SUB_INACTIVE,          _(u'is an inactive customer of'), [Contact, Organisation]),
                         (constants.REL_OBJ_INACTIVE,          _(u'has as inactive customer'),   [Contact, Organisation]),
                        ),
                        ((constants.REL_SUB_SUBSIDIARY,        _(u'has as subsidiary'),          [Organisation]),
                         (constants.REL_OBJ_SUBSIDIARY,        _(u'is a subsidiary of'),         [Organisation]),
                        ),
                        ((constants.REL_SUB_COMPETITOR,        _(u'is a competitor of'),         [Contact, Organisation]),
                         (constants.REL_OBJ_COMPETITOR,        _(u'has as competitor'),          [Contact, Organisation]),
                        ),
                       ]:
            rt, sym_rt = core_models.RelationType.create(*rt_info)
            rt_map[rt.id] = rt
            rt_map[sym_rt.id] = sym_rt

        # ---------------------------
        EntityFilter.create(constants.FILTER_MANAGED_ORGA, name=_(u'Managed by creme'),
                            model=Organisation, user='admin',
                            conditions=[EntityFilterCondition.build_4_field(
                                              model=Organisation,
                                              operator=EntityFilterCondition.EQUALS,
                                              name='is_managed',
                                              values=[True],
                                          ),
                                       ],
                           )
        EntityFilter.create(constants.FILTER_CONTACT_ME, name=_(u'Me'),
                            model=Contact, user='admin',
                            conditions=[EntityFilterCondition.build_4_field(
                                              model=Contact,
                                              operator=EntityFilterCondition.EQUALS,
                                              name='is_user',
                                              values=[EntityFilterVariable.CURRENT_USER],
                                          ),
                                       ],
                           )

        # ---------------------------
        create_hf = core_models.HeaderFilter.create
        create_hf(pk=constants.DEFAULT_HFILTER_CONTACT, model=Contact,
                  name=_(u'Contact view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                              (EntityCellRegularField, {'name': 'first_name'}),
                              (EntityCellRegularField, {'name': 'phone'}),
                              (EntityCellRegularField, {'name': 'email'}),
                              (EntityCellRegularField, {'name': 'user'}),
                              EntityCellRelation(model=Contact, rtype=rt_map[constants.REL_SUB_EMPLOYED_BY]),
                             ],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_ORGA, model=Organisation,
                  name=_(u'Organisation view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'phone'}),
                              (EntityCellRegularField, {'name': 'user'}),
                              EntityCellRelation(model=Organisation, rtype=rt_map[constants.REL_OBJ_MANAGES]),
                             ],
                 )
        create_hf(pk='persons-hf_leadcustomer', model=Organisation,
                  name=_(u'Prospect/Suspect view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'sector'}),
                              (EntityCellRegularField, {'name': 'phone'}),
                              (EntityCellRegularField, {'name': 'email'}),
                              (EntityCellRegularField, {'name': 'user'}),
                              EntityCellRelation(model=Organisation, rtype=rt_map[constants.REL_SUB_CUSTOMER_SUPPLIER]),
                              EntityCellRelation(model=Organisation, rtype=rt_map[constants.REL_SUB_PROSPECT]),
                              EntityCellRelation(model=Organisation, rtype=rt_map[constants.REL_SUB_SUSPECT]),
                             ],
                 )

        # ---------------------------
        create_sci = core_models.SearchConfigItem.create_if_needed
        create_sci(Contact, ['last_name', 'first_name', 'phone', 'mobile', 'email'])
        create_sci(Organisation, ['name', 'phone', 'email', 'sector__title', 'legal_form__title'])

        # ---------------------------
        if not already_populated:
            create_if_needed(Civility, {'pk': 1}, title=_(u'Madam'),  shortcut=_(u'Mrs.'))
            create_if_needed(Civility, {'pk': 2}, title=_(u'Miss'),   shortcut=_(u'Ms.'))
            create_if_needed(Civility, {'pk': 3}, title=_(u'Mister'), shortcut=_(u'Mr.'))
            create_if_needed(Civility, {'pk': 4}, title=_(u'N/A'),    shortcut=u'')

            # ---------------------------
            # TODO: add relation to admin ????
            if not Organisation.objects.exists():
                Organisation.objects.create(user=get_user_model().objects.get_admin(),
                                            name=_(u'ReplaceByYourSociety'), is_managed=True,
                                            uuid=constants.UUID_FIRST_ORGA,
                                           )

            # ---------------------------
            create_if_needed(Position, {'pk': 1}, title=_(u'CEO'))
            create_if_needed(Position, {'pk': 2}, title=_(u'Secretary'))
            create_if_needed(Position, {'pk': 3}, title=_(u'Technician'))

            # ---------------------------
            create_if_needed(Sector, {'pk': 1}, title=_(u'Food Industry'))
            create_if_needed(Sector, {'pk': 2}, title=_(u'Industry'))
            create_if_needed(Sector, {'pk': 3}, title=_(u'Software'))
            create_if_needed(Sector, {'pk': 4}, title=_(u'Telecom'))
            create_if_needed(Sector, {'pk': 5}, title=_(u'Restoration'))

            # ---------------------------
            # TODO: depend on the country no ??
            create_if_needed(LegalForm, {'pk': 1}, title=u'SARL')
            create_if_needed(LegalForm, {'pk': 2}, title=u'Association loi 1901')
            create_if_needed(LegalForm, {'pk': 3}, title=u'SA')
            create_if_needed(LegalForm, {'pk': 4}, title=u'SAS')

            # ---------------------------
            create_if_needed(StaffSize, {'pk': 1}, size='1 - 5',     order=1)
            create_if_needed(StaffSize, {'pk': 2}, size='6 - 10',    order=2)
            create_if_needed(StaffSize, {'pk': 3}, size='11 - 50',   order=3)
            create_if_needed(StaffSize, {'pk': 4}, size='51 - 100',  order=4)
            create_if_needed(StaffSize, {'pk': 5}, size='100 - 500', order=5)
            create_if_needed(StaffSize, {'pk': 6}, size='> 500',     order=6)

            # ---------------------------
            create_bmi = core_models.ButtonMenuItem.create_if_needed
            create_bmi(pk='persons-customer_contact_button', model=Contact, button=buttons.BecomeCustomerButton, order=20)
            create_bmi(pk='persons-prospect_contact_button', model=Contact, button=buttons.BecomeProspectButton, order=21)
            create_bmi(pk='persons-suspect_contact_button',  model=Contact, button=buttons.BecomeSuspectButton,  order=22)
            create_bmi(pk='persons-inactive_contact_button', model=Contact, button=buttons.BecomeInactiveButton, order=24)

            create_bmi(pk='persons-customer_orga_button',  model=Organisation, button=buttons.BecomeCustomerButton,   order=20)
            create_bmi(pk='persons-prospect_orga_button',  model=Organisation, button=buttons.BecomeProspectButton,   order=21)
            create_bmi(pk='persons-suspect_orga_button',   model=Organisation, button=buttons.BecomeSuspectButton,    order=22)
            create_bmi(pk='persons-inactive_orga_button',  model=Organisation, button=buttons.BecomeInactiveButton,   order=23)
            create_bmi(pk='persons-supplier_button',       model=Organisation, button=buttons.BecomeSupplierButton,   order=24)
            create_bmi(pk='persons-linked_contact_button', model=Organisation, button=buttons.AddLinkedContactButton, order=25)

            # Populate bricks ------------------
            rbi_1 = core_models.RelationBrickItem.create(constants.REL_SUB_CUSTOMER_SUPPLIER)
            rbi_2 = core_models.RelationBrickItem.create(constants.REL_OBJ_CUSTOMER_SUPPLIER)

            get_ct = ContentType.objects.get_for_model
            create_cbci = core_models.CustomBrickConfigItem.objects.create
            build_cell = EntityCellRegularField.build

            # cbci_orga_1 =
            create_cbci(id='persons-organisation_main_info',
                        name=_(u'Organisation information'),
                        content_type=get_ct(Organisation),
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
            create_cbci(id='persons-organisation_details',
                        name=_(u'Organisation details'),
                        content_type=get_ct(Organisation),
                        cells=[
                          build_cell(Organisation, 'phone'),
                          build_cell(Organisation, 'fax'),
                          build_cell(Organisation, 'email'),
                          build_cell(Organisation, 'url_site'),
                        ],
                       )
            cbci_orga_extra = create_cbci(id='persons-organisation_complementary',
                                          name=_(u'Organisation complementary information'),
                                          content_type=get_ct(Organisation),
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

            HAT   = core_models.BrickDetailviewLocation.HAT
            LEFT  = core_models.BrickDetailviewLocation.LEFT
            RIGHT = core_models.BrickDetailviewLocation.RIGHT

            create_bdl = core_models.BrickDetailviewLocation.create_if_needed
            create_bdl(brick_id=bricks.OrganisationCardHatBrick.id_,  order=1,   zone=HAT,   model=Organisation)
            create_bdl(brick_id=cbci_orga_extra.generate_id(),        order=5,   zone=LEFT,  model=Organisation)
            create_bdl(brick_id=core_bricks.CustomFieldsBrick.id_,    order=40,  zone=LEFT,  model=Organisation)
            create_bdl(brick_id=bricks.PrettyAddressesBrick.id_,      order=50,  zone=LEFT,  model=Organisation)
            create_bdl(brick_id=bricks.PrettyOtherAddressesBrick.id_, order=60,  zone=LEFT,  model=Organisation)
            create_bdl(brick_id=bricks.ManagersBrick.id_,             order=100, zone=LEFT,  model=Organisation)
            create_bdl(brick_id=bricks.EmployeesBrick.id_,            order=120, zone=LEFT,  model=Organisation)
            create_bdl(brick_id=core_bricks.PropertiesBrick.id_,      order=450, zone=LEFT,  model=Organisation)
            create_bdl(brick_id=core_bricks.RelationsBrick.id_,       order=500, zone=LEFT,  model=Organisation)
            create_bdl(brick_id=rbi_1.brick_id,                       order=5,   zone=RIGHT, model=Organisation)
            create_bdl(brick_id=rbi_2.brick_id,                       order=10,  zone=RIGHT, model=Organisation)
            create_bdl(brick_id=core_bricks.HistoryBrick.id_,         order=30,  zone=RIGHT, model=Organisation)

            create_cbci(id='persons-contact_main_info',
                        name=_(u'Contact information'),
                        content_type=get_ct(Contact),
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
            create_cbci(id='persons-contact_details',
                        name=_(u'Contact details'),
                        content_type=get_ct(Contact),
                        cells=[
                           build_cell(Contact, 'phone'),
                           build_cell(Contact, 'mobile'),
                           build_cell(Contact, 'fax'),
                           build_cell(Contact, 'email'),
                           build_cell(Contact, 'url_site'),
                           build_cell(Contact, 'skype'),
                        ],
                       )
            cbci_contact_extra = create_cbci(id='persons-contact_complementary',
                                             name=_(u'Contact complementary information'),
                                             content_type=get_ct(Contact),
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

            create_bdl(brick_id=bricks.ContactCardHatBrick.id_,       order=1,   zone=HAT,   model=Contact)
            create_bdl(brick_id=cbci_contact_extra.generate_id(),     order=30,  zone=LEFT,  model=Contact)
            create_bdl(brick_id=core_bricks.CustomFieldsBrick.id_,    order=40,  zone=LEFT,  model=Contact)
            create_bdl(brick_id=bricks.PrettyAddressesBrick.id_,      order=50,  zone=LEFT,  model=Contact)
            create_bdl(brick_id=bricks.PrettyOtherAddressesBrick.id_, order=60,  zone=LEFT,  model=Contact)
            create_bdl(brick_id=core_bricks.PropertiesBrick.id_,      order=450, zone=LEFT,  model=Contact)
            create_bdl(brick_id=core_bricks.RelationsBrick.id_,       order=500, zone=LEFT,  model=Contact)
            create_bdl(brick_id=core_bricks.HistoryBrick.id_,         order=20,  zone=RIGHT, model=Contact)

            # create_bpl = core_models.BlockPortalLocation.create_or_update
            # create_bpl(app_name='persons', brick_id=core_bricks.HistoryBrick.id_, order=30)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views and portal')

                from creme.assistants import bricks as a_bricks

                create_bdl(brick_id=a_bricks.TodosBrick.id_,        order=100, zone=RIGHT, model=Contact)
                create_bdl(brick_id=a_bricks.MemosBrick.id_,        order=200, zone=RIGHT, model=Contact)
                create_bdl(brick_id=a_bricks.AlertsBrick.id_,       order=300, zone=RIGHT, model=Contact)
                create_bdl(brick_id=a_bricks.UserMessagesBrick.id_, order=500, zone=RIGHT, model=Contact)

                create_bdl(brick_id=a_bricks.TodosBrick.id_,        order=100, zone=RIGHT, model=Organisation)
                create_bdl(brick_id=a_bricks.MemosBrick.id_,        order=200, zone=RIGHT, model=Organisation)
                create_bdl(brick_id=a_bricks.AlertsBrick.id_,       order=300, zone=RIGHT, model=Organisation)
                create_bdl(brick_id=a_bricks.UserMessagesBrick.id_, order=500, zone=RIGHT, model=Organisation)

                # create_bpl(app_name='persons', brick_id=a_bricks.MemosBrick.id_,        order=100)
                # create_bpl(app_name='persons', brick_id=a_bricks.AlertsBrick.id_,       order=200)
                # create_bpl(app_name='persons', brick_id=a_bricks.UserMessagesBrick.id_, order=400)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                create_bdl(brick_id=LinkedDocsBrick.id_, order=600, zone=RIGHT, model=Contact)
                create_bdl(brick_id=LinkedDocsBrick.id_, order=600, zone=RIGHT, model=Organisation)

            if apps.is_installed('creme.activities'):
                # create_bpl(app_name='persons',    brick_id=bricks.NeglectedOrganisationsBrick.id_, order=10)

                # create_bpl(app_name='creme_core', brick_id=bricks.NeglectedOrganisationsBrick.id_, order=15)
                core_models.BrickHomeLocation.objects.create(brick_id=bricks.NeglectedOrganisationsBrick.id_, order=15)