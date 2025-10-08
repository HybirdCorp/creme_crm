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

from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

import creme.creme_core.bricks as core_bricks
import creme.creme_core.constants as core_constants
from creme import persons
from creme.creme_core.core.entity_cell import (
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.entity_filter import (
    condition_handler,
    operands,
    operators,
)
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    ButtonMenuItem,
    CustomBrickConfigItem,
    EntityFilter,
    HeaderFilter,
    MenuConfigItem,
    RelationBrickItem,
    RelationType,
    SearchConfigItem,
)
from creme.documents.models import DocumentCategory

from . import bricks, buttons, constants, custom_forms, menu
from .models import Civility, LegalForm, Position, Sector, StaffSize

logger = logging.getLogger(__name__)

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()

# UUIDs for instances which can be deleted
UUID_CIVILITY_MRS  = '7c3867da-af53-43d4-bfcc-75c1c3e5121e'
UUID_CIVILITY_MISS = '6b84a23d-c4ec-41c1-a35d-e6c0af5af2a0'
UUID_CIVILITY_MR   = '08e68afd-64aa-4981-a1db-4bde37b08655'
UUID_CIVILITY_NA   = '547504b3-a886-4837-9170-62f2bc706e7f'

UUID_POSITION_CEO        = '1534eb82-f55c-45ef-af2e-4e2d5d68218f'
UUID_POSITION_SECRETARY  = '7e10f7f8-730c-45b4-8e81-6b2e4cfbab36'
UUID_POSITION_TECHNICIAN = '9669e6a9-4661-4248-bc7c-d675f6e13216'

UUID_SECTOR_FOOD        = '4995508b-069b-4ad5-a07d-9ae9c17918f2'
UUID_SECTOR_INDUSTRY    = '06581ce8-e5ab-4875-b18d-b1ae366a9073'
UUID_SECTOR_SOFTWARE    = 'd3d16967-b4e4-4dff-a401-c97ab36fa9a2'
UUID_SECTOR_TELECOM     = '471ec83d-d7cc-4b51-8ff4-b3b16c339927'
UUID_SECTOR_RESTORATION = '115ecac3-dda1-4388-ad8c-c1d4d6e86214'

UUID_LEGALFORM_FRANCE_SARL = '0f9ffebf-ae6a-4314-bf78-5ac33c477385'
UUID_LEGALFORM_FRANCE_1901 = '97ec5342-cfcd-47f2-9977-03238a4bb815'
UUID_LEGALFORM_FRANCE_SA   = '2a18cf05-19bd-47d1-96d0-7dd2ea969e74'
UUID_LEGALFORM_FRANCE_SAS  = '2085dfac-9714-407c-972b-2256e8472124'

UUID_STAFFSIZE_1_TO_5     = '625f5c71-db51-48f7-b548-63360d0b6653'
UUID_STAFFSIZE_6_TO_10    = '405efcfb-b6cc-4996-8062-b0794d6b718b'
UUID_STAFFSIZE_11_TO_50   = '57b8a9f0-b672-473a-bc77-db0cd73f4d71'
UUID_STAFFSIZE_51_TO_100  = 'bab5348c-9a46-4a05-a72e-b94db229f818'
UUID_STAFFSIZE_100_TO_500 = 'fd1a7587-624f-4cd1-adbc-309e237cfe91'
UUID_STAFFSIZE_GT_500     = 'ca0a585c-a40d-480c-86d0-c9610c93b23b'

UUID_CBRICK_CONTACT_INFO    = '9d945cba-f604-4552-a28c-28eb67ec4a73'
UUID_CBRICK_CONTACT_DETAILS = '4092894e-358c-4970-ad55-151862dee576'
UUID_CBRICK_CONTACT_COMP    = '4c6eb2a7-d7d4-4c19-a485-ad8da84f1211'
UUID_CBRICK_ORGA_INFO       = '05af52f4-fce8-4eca-b06a-49ea65186722'
UUID_CBRICK_ORGA_DETAILS    = '32446dad-ef2b-4099-aa71-573dc9d1099a'
UUID_CBRICK_ORGA_COMP       = '2a0f4a73-094f-492f-8fbd-125cb5ff30ed'

_Button = ButtonMenuItem.objects.proxy


class Populator(BasePopulator):
    dependencies = ['creme_core', 'documents']

    RELATION_TYPES = [
        RelationType.objects.builder(
            id=constants.REL_SUB_EMPLOYED_BY, predicate=_('is an employee of'),
            models=[Contact],
        ).symmetric(
            id=constants.REL_OBJ_EMPLOYED_BY, predicate=_('employs'),
            models=[Organisation],
        ),
        RelationType.objects.builder(
            id=constants.REL_SUB_CUSTOMER_SUPPLIER, predicate=_('is a customer of'),
            models=[Contact, Organisation],
        ).symmetric(
            id=constants.REL_OBJ_CUSTOMER_SUPPLIER, predicate=_('is a supplier of'),
            models=[Contact, Organisation],
        ),
        RelationType.objects.builder(
            id=constants.REL_SUB_MANAGES, predicate=_('manages'),
            models=[Contact],
        ).symmetric(
            id=constants.REL_OBJ_MANAGES, predicate=_('managed by'),
            models=[Organisation],
        ),
        RelationType.objects.builder(
            id=constants.REL_SUB_PROSPECT, predicate=_('is a prospect of'),
            models=[Contact, Organisation],
        ).symmetric(
            id=constants.REL_OBJ_PROSPECT, predicate=_('has as prospect'),
            models=[Contact, Organisation],
        ),
        RelationType.objects.builder(
            id=constants.REL_SUB_SUSPECT, predicate=_('is a suspect of'),
            models=[Contact, Organisation],
        ).symmetric(
            id=constants.REL_OBJ_SUSPECT, predicate=_('has as suspect'),
            models=[Contact, Organisation],
        ),
        RelationType.objects.builder(
            id=constants.REL_SUB_PARTNER, predicate=_('is a partner of'),
            models=[Contact, Organisation],
        ).symmetric(
            id=constants.REL_OBJ_PARTNER, predicate=_('has as partner'),
            models=[Contact, Organisation],
        ),
        RelationType.objects.builder(
            id=constants.REL_SUB_INACTIVE, predicate=_('is an inactive customer of'),
            models=[Contact, Organisation],
        ).symmetric(
            id=constants.REL_OBJ_INACTIVE, predicate=_('has as inactive customer'),
            models=[Contact, Organisation],
        ),
        RelationType.objects.builder(
            id=constants.REL_SUB_SUBSIDIARY, predicate=_('has as subsidiary'),
            models=[Organisation],
        ).symmetric(
            id=constants.REL_OBJ_SUBSIDIARY, predicate=_('is a subsidiary of'),
            models=[Organisation],
        ),
        RelationType.objects.builder(
            id=constants.REL_SUB_COMPETITOR, predicate=_('is a competitor of'),
            models=[Contact, Organisation],
        ).symmetric(
            id=constants.REL_OBJ_COMPETITOR, predicate=_('has as competitor'),
            models=[Contact, Organisation],
        ),
    ]
    HEADER_FILTERS = [
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_CONTACT,
            model=Contact,
            name=_('Contact view'),
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'first_name'),
                (EntityCellRegularField, 'phone'),
                (EntityCellRegularField, 'email'),
                (EntityCellRegularField, 'user'),
                (EntityCellRelation, constants.REL_SUB_EMPLOYED_BY),
            ],
        ),
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_ORGA,
            model=Organisation,
            name=_('Organisation view'),
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'phone'),
                (EntityCellRegularField, 'user'),
                (EntityCellRelation, constants.REL_OBJ_MANAGES),
            ],
        ),
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_ORGA_CUSTOMERS,
            model=Organisation,
            name=_('Prospect/Suspect view'),
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'sector'),
                (EntityCellRegularField, 'phone'),
                (EntityCellRegularField, 'email'),
                (EntityCellRegularField, 'user'),
                (EntityCellRelation, constants.REL_SUB_CUSTOMER_SUPPLIER),
                (EntityCellRelation, constants.REL_SUB_PROSPECT),
                (EntityCellRelation, constants.REL_SUB_SUSPECT),
            ],
        ),
    ]
    CUSTOM_FORMS = [
        custom_forms.CONTACT_CREATION_CFORM,
        custom_forms.CONTACT_EDITION_CFORM,
        custom_forms.ORGANISATION_CREATION_CFORM,
        custom_forms.ORGANISATION_EDITION_CFORM,
    ]
    # BUTTONS = {
    #     'CONTACT': [
    #         # (class, order)
    #         (buttons.BecomeProspectButton, 1021),
    #         (buttons.BecomeSuspectButton,  1022),
    #         (buttons.BecomeInactiveButton, 1023),
    #     ],
    #     'ORGANISATION': [
    #         # (class, order)
    #         (buttons.BecomeCustomerButton,   1020),
    #         (buttons.BecomeProspectButton,   1021),
    #         (buttons.BecomeSuspectButton,    1022),
    #         (buttons.BecomeInactiveButton,   1023),
    #         (buttons.BecomeSupplierButton,   1024),
    #         (buttons.AddLinkedContactButton, 1025),
    #     ],
    # }
    BUTTONS = [
        _Button(model=Contact, button=buttons.BecomeProspectButton, order=1021),
        _Button(model=Contact, button=buttons.BecomeSuspectButton,  order=1022),
        _Button(model=Contact, button=buttons.BecomeInactiveButton, order=1023),

        _Button(model=Organisation, button=buttons.BecomeCustomerButton,   order=1020),
        _Button(model=Organisation, button=buttons.BecomeProspectButton,   order=1021),
        _Button(model=Organisation, button=buttons.BecomeSuspectButton,    order=1022),
        _Button(model=Organisation, button=buttons.BecomeInactiveButton,   order=1023),
        _Button(model=Organisation, button=buttons.BecomeSupplierButton,   order=1024),
        _Button(model=Organisation, button=buttons.AddLinkedContactButton, order=1025),
    ]
    # SEARCH = {
    #     'CONTACT': [
    #         'last_name', 'first_name', 'phone', 'mobile', 'email',
    #     ],
    #     'ORGANISATION': [
    #         'name', 'phone', 'email', 'sector__title', 'legal_form__title',
    #     ],
    # }
    SEARCH = [
        SearchConfigItem.objects.builder(
            model=Contact,
            fields=['last_name', 'first_name', 'phone', 'mobile', 'email'],
        ),
        SearchConfigItem.objects.builder(
            model=Organisation,
            fields=['name', 'phone', 'email', 'sector__title', 'legal_form__title'],
        ),
    ]
    DOC_CATEGORIES = [
        DocumentCategory(
            uuid=constants.UUID_DOC_CAT_IMG_ORGA,
            name=_('Organisation logo'),
            is_custom=False,
        ),
        DocumentCategory(
            uuid=constants.UUID_DOC_CAT_IMG_CONTACT,
            name=_('Contact photograph'),
            is_custom=False,
        ),
    ]
    CIVILITIES = [
        # is_custom=True => only created during the first execution
        Civility(uuid=UUID_CIVILITY_MRS,  title=_('Madam'),  shortcut=_('Mrs.')),
        Civility(uuid=UUID_CIVILITY_MISS, title=_('Miss'),   shortcut=_('Ms.')),
        Civility(uuid=UUID_CIVILITY_MR,   title=_('Mister'), shortcut=_('Mr.')),
        Civility(uuid=UUID_CIVILITY_NA,   title=_('N/A'),    shortcut=''),
    ]
    POSITIONS = [
        # is_custom=True => only created during the first execution
        Position(uuid=UUID_POSITION_CEO,        title=_('CEO')),
        Position(uuid=UUID_POSITION_SECRETARY,  title=_('Secretary')),
        Position(uuid=UUID_POSITION_TECHNICIAN, title=_('Technician')),
    ]
    SECTORS = [
        # is_custom=True => only created during the first execution
        Sector(uuid=UUID_SECTOR_FOOD,        title=_('Food Industry')),
        Sector(uuid=UUID_SECTOR_INDUSTRY,    title=_('Industry')),
        Sector(uuid=UUID_SECTOR_SOFTWARE,    title=_('Software')),
        Sector(uuid=UUID_SECTOR_TELECOM,     title=_('Telecom')),
        Sector(uuid=UUID_SECTOR_RESTORATION, title=_('Restoration')),
    ]
    LEGAL_FORMS = [
        # TODO: add data depending on the current country
        # is_custom=True => only created during the first execution
        LegalForm(uuid=UUID_LEGALFORM_FRANCE_SARL, title='SARL'),
        LegalForm(uuid=UUID_LEGALFORM_FRANCE_1901, title='Association loi 1901'),
        LegalForm(uuid=UUID_LEGALFORM_FRANCE_SA,   title='SA'),
        LegalForm(uuid=UUID_LEGALFORM_FRANCE_SAS,  title='SAS'),
    ]
    STAFF_SIZES = [
        # is_custom=True => only created during the first execution
        StaffSize(uuid=UUID_STAFFSIZE_1_TO_5,     size='1 - 5',     order=1),
        StaffSize(uuid=UUID_STAFFSIZE_6_TO_10,    size='6 - 10',    order=2),
        StaffSize(uuid=UUID_STAFFSIZE_11_TO_50,   size='11 - 50',   order=3),
        StaffSize(uuid=UUID_STAFFSIZE_51_TO_100,  size='51 - 100',  order=4),
        StaffSize(uuid=UUID_STAFFSIZE_100_TO_500, size='100 - 500', order=5),
        StaffSize(uuid=UUID_STAFFSIZE_GT_500,     size='> 500',     order=6),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.Contact      = persons.get_contact_model()
        # self.Organisation = persons.get_organisation_model()
        self.Contact      = Contact
        self.Organisation = Organisation

    def _already_populated(self):
        return RelationType.objects.filter(
            pk=constants.REL_SUB_EMPLOYED_BY,
        ).exists()

    def _populate(self):
        super()._populate()
        self._populate_doc_categories()
        self._populate_civilities()
        self._populate_positions()
        self._populate_sectors()
        self._populate_legal_forms()
        self._populate_staff_sizes()

    def _first_populate(self):
        super()._first_populate()
        self._populate_managed_organisation()

    def _populate_doc_categories(self) -> None:
        self._save_minions(self.DOC_CATEGORIES)

    def _populate_civilities(self):
        self._save_minions(self.CIVILITIES)

    def _populate_managed_organisation(self):
        # TODO: add relationship to admin?
        if not self.Organisation.objects.exists():
            self.Organisation.objects.create(
                user=get_user_model().objects.get_admin(),
                name=_('ReplaceByYourSociety'), is_managed=True,
                uuid=constants.UUID_FIRST_ORGA,
            )

    def _populate_positions(self):
        self._save_minions(self.POSITIONS)

    def _populate_sectors(self):
        self._save_minions(self.SECTORS)

    def _populate_legal_forms(self):
        self._save_minions(self.LEGAL_FORMS)

    def _populate_staff_sizes(self):
        self._save_minions(self.STAFF_SIZES)

    def _populate_relation_types(self):
        # Contact      = self.Contact
        # Organisation = self.Organisation
        # any_person = [Contact, Organisation]
        #
        # create_rtype = RelationType.objects.smart_update_or_create
        # create_rtype(
        #     (constants.REL_SUB_EMPLOYED_BY, _('is an employee of'), [Contact]),
        #     (constants.REL_OBJ_EMPLOYED_BY, _('employs'),           [Organisation]),
        # )
        # create_rtype(
        #     (constants.REL_SUB_CUSTOMER_SUPPLIER, _('is a customer of'), any_person),
        #     (constants.REL_OBJ_CUSTOMER_SUPPLIER, _('is a supplier of'), any_person),
        # )
        # create_rtype(
        #     (constants.REL_SUB_MANAGES, _('manages'),    [Contact]),
        #     (constants.REL_OBJ_MANAGES, _('managed by'), [Organisation]),
        # )
        # create_rtype(
        #     (constants.REL_SUB_PROSPECT, _('is a prospect of'), any_person),
        #     (constants.REL_OBJ_PROSPECT, _('has as prospect'),  any_person),
        # )
        # create_rtype(
        #     (constants.REL_SUB_SUSPECT, _('is a suspect of'), any_person),
        #     (constants.REL_OBJ_SUSPECT, _('has as suspect'),  any_person),
        # )
        # create_rtype(
        #     (constants.REL_SUB_PARTNER, _('is a partner of'), any_person),
        #     (constants.REL_OBJ_PARTNER, _('has as partner'),  any_person),
        # )
        # create_rtype(
        #     (constants.REL_SUB_INACTIVE, _('is an inactive customer of'), any_person),
        #     (constants.REL_OBJ_INACTIVE, _('has as inactive customer'),   any_person),
        # )
        # create_rtype(
        #     (constants.REL_SUB_SUBSIDIARY, _('has as subsidiary'),  [Organisation]),
        #     (constants.REL_OBJ_SUBSIDIARY, _('is a subsidiary of'), [Organisation]),
        # )
        # create_rtype(
        #     (constants.REL_SUB_COMPETITOR, _('is a competitor of'), any_person),
        #     (constants.REL_OBJ_COMPETITOR, _('has as competitor'),  any_person),
        # )
        super()._populate_relation_types()

        get_rtype = RelationType.objects.get
        get_rtype(pk=core_constants.REL_SUB_HAS).add_subject_ctypes(Contact, Organisation)
        get_rtype(pk=core_constants.REL_OBJ_HAS).add_subject_ctypes(Organisation)

    def _populate_entity_filters_for_contact(self):
        EntityFilter.objects.smart_update_or_create(
            constants.FILTER_CONTACT_ME, name=_('Me'),
            model=self.Contact, user='admin',
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=self.Contact,
                    operator=operators.EqualsOperator,
                    field_name='is_user',
                    values=[operands.CurrentUserOperand.type_id],
                ),
            ],
        )

    def _populate_entity_filters_for_organisation(self):
        EntityFilter.objects.smart_update_or_create(
            constants.FILTER_MANAGED_ORGA, name=_('Managed by creme'),
            model=self.Organisation, user='admin',
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=self.Organisation,
                    operator=operators.EqualsOperator,
                    field_name='is_managed',
                    values=[True],
                ),
            ],
        )

    def _populate_entity_filters(self):
        self._populate_entity_filters_for_contact()
        self._populate_entity_filters_for_organisation()

    # def _populate_header_filters_for_contact(self):
    #     Contact = self.Contact
    #     HeaderFilter.objects.create_if_needed(
    #         pk=constants.DEFAULT_HFILTER_CONTACT, model=Contact,
    #         name=_('Contact view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'last_name'}),
    #             (EntityCellRegularField, {'name': 'first_name'}),
    #             (EntityCellRegularField, {'name': 'phone'}),
    #             (EntityCellRegularField, {'name': 'email'}),
    #             (EntityCellRegularField, {'name': 'user'}),
    #             EntityCellRelation(
    #                 model=Contact,
    #                 rtype=RelationType.objects.get(id=constants.REL_SUB_EMPLOYED_BY),
    #             ),
    #         ],
    #     )
    #
    # def _populate_header_filters_for_organisation(self):
    #     Organisation = self.Organisation
    #     create_hf = HeaderFilter.objects.create_if_needed
    #     get_rtype = RelationType.objects.get
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_ORGA, model=Organisation,
    #         name=_('Organisation view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'name'}),
    #             (EntityCellRegularField, {'name': 'phone'}),
    #             (EntityCellRegularField, {'name': 'user'}),
    #             EntityCellRelation(
    #                 model=Organisation, rtype=get_rtype(id=constants.REL_OBJ_MANAGES),
    #             ),
    #         ],
    #     )
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_ORGA_CUSTOMERS, model=Organisation,
    #         name=_('Prospect/Suspect view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'name'}),
    #             (EntityCellRegularField, {'name': 'sector'}),
    #             (EntityCellRegularField, {'name': 'phone'}),
    #             (EntityCellRegularField, {'name': 'email'}),
    #             (EntityCellRegularField, {'name': 'user'}),
    #             EntityCellRelation(
    #                 model=Organisation, rtype=get_rtype(id=constants.REL_SUB_CUSTOMER_SUPPLIER),
    #             ),
    #             EntityCellRelation(
    #                 model=Organisation, rtype=get_rtype(id=constants.REL_SUB_PROSPECT),
    #             ),
    #             EntityCellRelation(
    #                 model=Organisation, rtype=get_rtype(id=constants.REL_SUB_SUSPECT),
    #             ),
    #         ],
    #     )
    #
    # def _populate_header_filters(self):
    #     self._populate_header_filters_for_contact()
    #     self._populate_header_filters_for_organisation()

    # def _populate_search_config(self):
    #     create_sci = SearchConfigItem.objects.create_if_needed
    #     create_sci(model=self.Contact,      fields=self.SEARCH['CONTACT'])
    #     create_sci(model=self.Organisation, fields=self.SEARCH['ORGANISATION'])

    def _populate_menu_config(self):
        directory_entry = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Directory')},
            role=None, superuser=False,
            defaults={'order': 20},
        )[0]

        create_mitem = MenuConfigItem.objects.create
        create_mitem(entry_id=menu.OrganisationsEntry.id, order=10, parent=directory_entry)
        create_mitem(entry_id=menu.ContactsEntry.id,      order=20, parent=directory_entry)
        create_mitem(entry_id=menu.CustomersEntry.id,     order=30, parent=directory_entry)

        creations_entry = MenuConfigItem.objects.filter(
            entry_id=ContainerEntry.id, entry_data={'label': _('+ Creation')},
        ).first()
        if creations_entry is not None:
            create_mitem(
                entry_id=menu.OrganisationCreationEntry.id,
                order=10, parent=creations_entry,
            )
            create_mitem(
                entry_id=menu.ContactCreationEntry.id,
                order=20, parent=creations_entry,
            )

    # def _populate_buttons_config(self):
    #     create_bmi = ButtonMenuItem.objects.create_if_needed
    #
    #     for button_cls, order in self.BUTTONS['CONTACT']:
    #         create_bmi(model=self.Contact, button=button_cls, order=order)
    #
    #     for button_cls, order in self.BUTTONS['ORGANISATION']:
    #         create_bmi(model=self.Organisation, button=button_cls, order=order)

    def _populate_bricks_config_for_contact(self):
        Contact = self.Contact

        create_cbci = CustomBrickConfigItem.objects.create
        build_cell = EntityCellRegularField.build

        create_cbci(
            uuid=UUID_CBRICK_CONTACT_INFO,
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
                build_cell(Contact, 'languages'),
                # --
                build_cell(Contact, 'description'),
                # --
                build_cell(Contact, 'created'),
                build_cell(Contact, 'modified'),
                build_cell(Contact, 'user'),
            ],
        )
        create_cbci(
            uuid=UUID_CBRICK_CONTACT_DETAILS,
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
            uuid=UUID_CBRICK_CONTACT_COMP,
            name=_('Contact complementary information'),
            content_type=Contact,
            cells=[
                build_cell(Contact, 'sector'),
                build_cell(Contact, 'position'),
                build_cell(Contact, 'full_position'),
                build_cell(Contact, 'birthday'),
                build_cell(Contact, 'image'),
                build_cell(Contact, 'languages'),
                # --
                build_cell(Contact, 'description'),
                # --
                build_cell(Contact, 'fax'),
                build_cell(Contact, 'url_site'),
                build_cell(Contact, 'skype'),
            ],
        )

        RIGHT = BrickDetailviewLocation.RIGHT
        HAT = BrickDetailviewLocation.HAT
        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': Contact, 'zone': BrickDetailviewLocation.LEFT},
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

    def _populate_bricks_config_for_organisation(self):
        Organisation = self.Organisation

        create_rbi = RelationBrickItem.objects.get_or_create
        rbi_1 = create_rbi(relation_type_id=constants.REL_SUB_CUSTOMER_SUPPLIER)[0]
        rbi_2 = create_rbi(relation_type_id=constants.REL_OBJ_CUSTOMER_SUPPLIER)[0]

        create_cbci = CustomBrickConfigItem.objects.create
        build_cell = EntityCellRegularField.build

        create_cbci(
            uuid=UUID_CBRICK_ORGA_INFO,
            name=_('Organisation information'),
            content_type=Organisation,
            cells=[
                build_cell(Organisation, 'name'),
                build_cell(Organisation, 'is_managed'),
                build_cell(Organisation, 'staff_size'),
                build_cell(Organisation, 'legal_form'),
                build_cell(Organisation, 'sector'),
                build_cell(Organisation, 'capital'),
                build_cell(Organisation, 'code'),
                build_cell(Organisation, 'siren'),
                build_cell(Organisation, 'naf'),
                build_cell(Organisation, 'siret'),
                build_cell(Organisation, 'rcs'),
                build_cell(Organisation, 'eori'),
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
        create_cbci(
            uuid=UUID_CBRICK_ORGA_DETAILS,
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
            uuid=UUID_CBRICK_ORGA_COMP,
            name=_('Organisation complementary information'),
            content_type=Organisation,
            cells=[
                build_cell(Organisation, 'staff_size'),
                build_cell(Organisation, 'sector'),
                build_cell(Organisation, 'capital'),
                build_cell(Organisation, 'code'),
                build_cell(Organisation, 'siren'),
                build_cell(Organisation, 'naf'),
                build_cell(Organisation, 'siret'),
                build_cell(Organisation, 'rcs'),
                build_cell(Organisation, 'eori'),
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

        RIGHT = BrickDetailviewLocation.RIGHT
        HAT = BrickDetailviewLocation.HAT
        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': Organisation, 'zone': BrickDetailviewLocation.LEFT},
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

                {'brick': rbi_1.brick_id,           'order':  5, 'zone': RIGHT},
                {'brick': rbi_2.brick_id,           'order': 10, 'zone': RIGHT},
                {'brick': core_bricks.HistoryBrick, 'order': 30, 'zone': RIGHT},
            ],
        )

    def _populate_bricks_config_for_assistants(self):
        logger.info(
            'Assistants app is installed'
            ' => we use the assistants blocks on detail views and portal'
        )

        import creme.assistants.bricks as a_bricks

        for model in (self.Contact, self.Organisation):
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': model, 'zone': BrickDetailviewLocation.RIGHT},
                data=[
                    {'brick': a_bricks.TodosBrick,        'order': 100},
                    {'brick': a_bricks.MemosBrick,        'order': 200},
                    {'brick': a_bricks.AlertsBrick,       'order': 300},
                    {'brick': a_bricks.UserMessagesBrick, 'order': 500},
                ],
            )

    def _populate_bricks_config_for_documents(self):
        # logger.info('Documents app is installed
        # => we use the documents block on detail views')

        from creme.documents.bricks import LinkedDocsBrick

        BrickDetailviewLocation.objects.multi_create(
            defaults={
                'brick': LinkedDocsBrick,
                'order': 600,
                'zone': BrickDetailviewLocation.RIGHT,
            },
            data=[
                {'model': self.Contact},
                {'model': self.Organisation},
            ],
        )

    def _populate_bricks_config_for_activities(self):
        BrickHomeLocation.objects.create(
            brick_id=bricks.NeglectedOrganisationsBrick.id, order=15,
        )

    def _populate_bricks_config(self):
        self._populate_bricks_config_for_contact()
        self._populate_bricks_config_for_organisation()

        if apps.is_installed('creme.assistants'):
            self._populate_bricks_config_for_assistants()

        if apps.is_installed('creme.documents'):
            self._populate_bricks_config_for_documents()

        if apps.is_installed('creme.activities'):
            self._populate_bricks_config_for_activities()
