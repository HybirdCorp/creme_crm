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
    CustomFormConfigItem,
    EntityFilter,
    HeaderFilter,
    MenuConfigItem,
    RelationBrickItem,
    RelationType,
    SearchConfigItem,
)
from creme.creme_core.utils import create_if_needed
from creme.documents.models import DocumentCategory

from . import bricks, buttons, constants, custom_forms, menu
from .models import Civility, LegalForm, Position, Sector, StaffSize

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'documents']

    SEARCH = {
        'CONTACT': [
            'last_name', 'first_name', 'phone', 'mobile', 'email',
        ],
        'ORGANISATION': [
            'name', 'phone', 'email', 'sector__title', 'legal_form__title',
        ],
    }

    BUTTONS = {
        'CONTACT': [
            # (class, order)
            (buttons.BecomeProspectButton, 21),
            (buttons.BecomeSuspectButton,  22),
            (buttons.BecomeInactiveButton, 23),
        ],
        'ORGANISATION': [
            # (class, order)
            (buttons.BecomeCustomerButton,   20),
            (buttons.BecomeProspectButton,   21),
            (buttons.BecomeSuspectButton,    22),
            (buttons.BecomeInactiveButton,   23),
            (buttons.BecomeSupplierButton,   24),
            (buttons.AddLinkedContactButton, 25),
        ],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Contact      = persons.get_contact_model()
        self.Organisation = persons.get_organisation_model()

    def _already_populated(self):
        return RelationType.objects.filter(
            pk=constants.REL_SUB_EMPLOYED_BY,
        ).exists()

    def _populate(self):
        super()._populate()
        self._populate_doc_categories()

    def _first_populate(self):
        super()._first_populate()
        self._populate_civilities()
        self._populate_managed_organisation()
        self._populate_positions()
        self._populate_sectors()
        self._populate_legal_forms()
        self._populate_staff_sizes()

    def _populate_doc_categories(self) -> None:
        create_doc_cat = DocumentCategory.objects.get_or_create
        create_doc_cat(
            uuid=constants.UUID_DOC_CAT_IMG_ORGA,
            defaults={
                'name': _('Organisation logo'),
                'is_custom': False,
            },
        )
        create_doc_cat(
            uuid=constants.UUID_DOC_CAT_IMG_CONTACT,
            defaults={
                'name': _('Contact photograph'),
                'is_custom': False,
            },
        )

    def _populate_civilities(self):
        create_if_needed(Civility, {'pk': 1}, title=_('Madam'),  shortcut=_('Mrs.'))
        create_if_needed(Civility, {'pk': 2}, title=_('Miss'),   shortcut=_('Ms.'))
        create_if_needed(Civility, {'pk': 3}, title=_('Mister'), shortcut=_('Mr.'))
        create_if_needed(Civility, {'pk': 4}, title=_('N/A'),    shortcut='')

    def _populate_managed_organisation(self):
        # TODO: add relationship to admin?
        if not self.Organisation.objects.exists():
            self.Organisation.objects.create(
                user=get_user_model().objects.get_admin(),
                name=_('ReplaceByYourSociety'), is_managed=True,
                uuid=constants.UUID_FIRST_ORGA,
            )

    def _populate_positions(self):
        # TODO: for pk, title in enumerate(self.POSITIONS, start=1)
        create_if_needed(Position, {'pk': 1}, title=_('CEO'))
        create_if_needed(Position, {'pk': 2}, title=_('Secretary'))
        create_if_needed(Position, {'pk': 3}, title=_('Technician'))

    def _populate_sectors(self):
        create_if_needed(Sector, {'pk': 1}, title=_('Food Industry'))
        create_if_needed(Sector, {'pk': 2}, title=_('Industry'))
        create_if_needed(Sector, {'pk': 3}, title=_('Software'))
        create_if_needed(Sector, {'pk': 4}, title=_('Telecom'))
        create_if_needed(Sector, {'pk': 5}, title=_('Restoration'))

    def _populate_legal_forms(self):
        # TODO: add data depending on the current country
        create_if_needed(LegalForm, {'pk': 1}, title='SARL')
        create_if_needed(LegalForm, {'pk': 2}, title='Association loi 1901')
        create_if_needed(LegalForm, {'pk': 3}, title='SA')
        create_if_needed(LegalForm, {'pk': 4}, title='SAS')

    def _populate_staff_sizes(self):
        create_if_needed(StaffSize, {'pk': 1}, size='1 - 5',     order=1)
        create_if_needed(StaffSize, {'pk': 2}, size='6 - 10',    order=2)
        create_if_needed(StaffSize, {'pk': 3}, size='11 - 50',   order=3)
        create_if_needed(StaffSize, {'pk': 4}, size='51 - 100',  order=4)
        create_if_needed(StaffSize, {'pk': 5}, size='100 - 500', order=5)
        create_if_needed(StaffSize, {'pk': 6}, size='> 500',     order=6)

    def _populate_relation_types(self):
        Contact      = self.Contact
        Organisation = self.Organisation
        any_person = [Contact, Organisation]

        create_rtype = RelationType.objects.smart_update_or_create
        create_rtype(
            (constants.REL_SUB_EMPLOYED_BY, _('is an employee of'), [Contact]),
            (constants.REL_OBJ_EMPLOYED_BY, _('employs'),           [Organisation]),
        )
        create_rtype(
            (constants.REL_SUB_CUSTOMER_SUPPLIER, _('is a customer of'), any_person),
            (constants.REL_OBJ_CUSTOMER_SUPPLIER, _('is a supplier of'), any_person),
        )
        create_rtype(
            (constants.REL_SUB_MANAGES, _('manages'),    [Contact]),
            (constants.REL_OBJ_MANAGES, _('managed by'), [Organisation]),
        )
        create_rtype(
            (constants.REL_SUB_PROSPECT, _('is a prospect of'), any_person),
            (constants.REL_OBJ_PROSPECT, _('has as prospect'),  any_person),
        )
        create_rtype(
            (constants.REL_SUB_SUSPECT, _('is a suspect of'), any_person),
            (constants.REL_OBJ_SUSPECT, _('has as suspect'),  any_person),
        )
        create_rtype(
            (constants.REL_SUB_PARTNER, _('is a partner of'), any_person),
            (constants.REL_OBJ_PARTNER, _('has as partner'),  any_person),
        )
        create_rtype(
            (constants.REL_SUB_INACTIVE, _('is an inactive customer of'), any_person),
            (constants.REL_OBJ_INACTIVE, _('has as inactive customer'),   any_person),
        )
        create_rtype(
            (constants.REL_SUB_SUBSIDIARY, _('has as subsidiary'),  [Organisation]),
            (constants.REL_OBJ_SUBSIDIARY, _('is a subsidiary of'), [Organisation]),
        )
        create_rtype(
            (constants.REL_SUB_COMPETITOR, _('is a competitor of'), any_person),
            (constants.REL_OBJ_COMPETITOR, _('has as competitor'),  any_person),
        )

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

    def _populate_header_filters_for_contact(self):
        Contact = self.Contact
        HeaderFilter.objects.create_if_needed(
            pk=constants.DEFAULT_HFILTER_CONTACT, model=Contact,
            name=_('Contact view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'last_name'}),
                (EntityCellRegularField, {'name': 'first_name'}),
                (EntityCellRegularField, {'name': 'phone'}),
                (EntityCellRegularField, {'name': 'email'}),
                (EntityCellRegularField, {'name': 'user'}),
                EntityCellRelation(
                    model=Contact,
                    rtype=RelationType.objects.get(id=constants.REL_SUB_EMPLOYED_BY),
                ),
            ],
        )

    def _populate_header_filters_for_organisation(self):
        Organisation = self.Organisation
        create_hf = HeaderFilter.objects.create_if_needed
        get_rtype = RelationType.objects.get
        create_hf(
            pk=constants.DEFAULT_HFILTER_ORGA, model=Organisation,
            name=_('Organisation view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'phone'}),
                (EntityCellRegularField, {'name': 'user'}),
                EntityCellRelation(
                    model=Organisation, rtype=get_rtype(id=constants.REL_OBJ_MANAGES),
                ),
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
                    model=Organisation, rtype=get_rtype(id=constants.REL_SUB_CUSTOMER_SUPPLIER),
                ),
                EntityCellRelation(
                    model=Organisation, rtype=get_rtype(id=constants.REL_SUB_PROSPECT),
                ),
                EntityCellRelation(
                    model=Organisation, rtype=get_rtype(id=constants.REL_SUB_SUSPECT),
                ),
            ],
        )

    def _populate_header_filters(self):
        self._populate_header_filters_for_contact()
        self._populate_header_filters_for_organisation()

    # TODO: more declarative (move in base)
    def _populate_custom_forms(self):
        create_cfci = CustomFormConfigItem.objects.create_if_needed
        create_cfci(descriptor=custom_forms.CONTACT_CREATION_CFORM)
        create_cfci(descriptor=custom_forms.CONTACT_EDITION_CFORM)
        create_cfci(descriptor=custom_forms.ORGANISATION_CREATION_CFORM)
        create_cfci(descriptor=custom_forms.ORGANISATION_EDITION_CFORM)

    def _populate_search_config(self):
        create_sci = SearchConfigItem.objects.create_if_needed
        create_sci(model=self.Contact,      fields=self.SEARCH['CONTACT'])
        create_sci(model=self.Organisation, fields=self.SEARCH['ORGANISATION'])

    def _populate_menu_config(self):
        directory_entry = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Directory')},
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

    def _populate_buttons_config(self):
        create_bmi = ButtonMenuItem.objects.create_if_needed

        for button_cls, order in self.BUTTONS['CONTACT']:
            create_bmi(model=self.Contact, button=button_cls, order=order)

        for button_cls, order in self.BUTTONS['ORGANISATION']:
            create_bmi(model=self.Organisation, button=button_cls, order=order)

    def _populate_bricks_config_for_contact(self):
        Contact = self.Contact

        create_cbci = CustomBrickConfigItem.objects.create
        build_cell = EntityCellRegularField.build

        create_cbci(
            # id='persons-contact_main_info',
            uuid='9d945cba-f604-4552-a28c-28eb67ec4a73',
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
            # id='persons-contact_details',
            uuid='4092894e-358c-4970-ad55-151862dee576',
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
            # id='persons-contact_complementary',
            uuid='4c6eb2a7-d7d4-4c19-a485-ad8da84f1211',
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
            # id='persons-organisation_main_info',
            uuid='05af52f4-fce8-4eca-b06a-49ea65186722',
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
        create_cbci(
            # id='persons-organisation_details',
            uuid='32446dad-ef2b-4099-aa71-573dc9d1099a',
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
            # id='persons-organisation_complementary',
            uuid='2a0f4a73-094f-492f-8fbd-125cb5ff30ed',
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
