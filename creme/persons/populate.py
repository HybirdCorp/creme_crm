# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from creme_core import autodiscover as creme_core_autodiscover
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD, HFI_RELATION
from creme_core.models import (RelationType, CremeProperty, CremePropertyType, ButtonMenuItem,
                              SearchConfigItem, RelationBlockItem, BlockConfigItem)
from creme_core.models.list_view_filter import FilterCondition, FilterValue, Filter
from creme_core.constants import PROP_IS_MANAGED_BY_CREME, FILTER_TYPE_EQUALS
from creme_core.utils import create_or_update as create
from creme_core.utils.id_generator import generate_string_id_and_save
from creme_core.gui.block import block_registry
from creme_core.management.commands.creme_populate import BasePopulator

from assistants.blocks import *

from persons.models import *
from persons.constants import *
from persons.buttons import (become_customer_button, become_prospect_button, become_suspect_button,
                             become_inactive_button, become_supplier_button, add_linked_contact_button)


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_EMPLOYED_BY, _(u'is an employee of'),          [Contact]),
                            (REL_OBJ_EMPLOYED_BY, _(u'employs'),                    [Organisation]))
        RelationType.create((REL_SUB_CUSTOMER_OF, _(u'is a customer of'),           [Contact, Organisation]),
                            (REL_OBJ_CUSTOMER_OF, _(u'has as customer'),            [Contact, Organisation]))
        RelationType.create((REL_SUB_MANAGES,     _(u'manages'),                    [Contact]),
                            (REL_OBJ_MANAGES,     _(u'managed by'),                 [Organisation]))
        RelationType.create((REL_SUB_PROSPECT,    _(u'is a prospect of'),           [Contact, Organisation]),
                            (REL_OBJ_PROSPECT,    _(u'has as prospect'),            [Contact, Organisation]))
        RelationType.create((REL_SUB_SUSPECT,     _(u'is a suspect of'),            [Contact, Organisation]),
                            (REL_OBJ_SUSPECT,     _(u'has as suspect'),             [Contact, Organisation]))
        RelationType.create((REL_SUB_PARTNER,     _(u'is a partner of'),            [Contact, Organisation]),
                            (REL_OBJ_PARTNER,     _(u'has as partner'),             [Contact, Organisation]))
        RelationType.create((REL_SUB_SUPPLIER,    _(u'is a supplier of'),           [Contact, Organisation]),
                            (REL_OBJ_SUPPLIER,    _(u'has as supplier'),            [Contact, Organisation]))
        RelationType.create((REL_SUB_INACTIVE,    _(u'is an inactive customer of'), [Contact, Organisation]),
                            (REL_OBJ_INACTIVE,    _(u'has as inactive customer'),   [Contact, Organisation]))
        RelationType.create((REL_SUB_SUBSIDIARY,  _(u'has as subsidiary'),          [Organisation]),
                            (REL_OBJ_SUBSIDIARY,  _(u"is a subsidiary of"),         [Organisation]))


        create(Civility, 1, civility_name=_(u"Mrs."))
        create(Civility, 2, civility_name=_(u"Miss"))
        mister = create(Civility, 3, civility_name=_(u"Mr."))
        create(Civility, 4, civility_name=_(u"Unknown"))

        create(PeopleFunction, 1, function_name=_(u"CEO"))
        create(PeopleFunction, 2, function_name=_(u"Secretary"))
        create(PeopleFunction, 3, function_name=_(u"Technician"))

        create(Sector, 1, sector_name=_(u"Food Industry"))
        create(Sector, 2, sector_name=_(u"Industry"))
        create(Sector, 3, sector_name=_(u"Informatic"))
        create(Sector, 4, sector_name=_(u"Telecom"))
        create(Sector, 5, sector_name=_(u"Restoration"))

        #TODO: depend on the country no ??
        create(LegalForm, 1, legal_form_name=u"SARL")
        create(LegalForm, 2, legal_form_name=u"Association loi 1901")
        create(LegalForm, 3, legal_form_name=u"SA")
        create(LegalForm, 4, legal_form_name=u"SAS")

        create(StaffSize, 1, employees="1 - 5")
        create(StaffSize, 2, employees="6 - 10")
        create(StaffSize, 3, employees="11 - 50")
        create(StaffSize, 4, employees="51 - 100")
        create(StaffSize, 5, employees="100 - 500")
        create(StaffSize, 6, employees="> 500")

        hf   = HeaderFilter.create(pk='persons-hf_contact', name=_(u'Contact view'), model=Contact)
        pref = 'persons-hfi_contact_'
        create(HeaderFilterItem, pref + 'lastname',  order=1, name='last_name',        title=_(u'Last name'),       type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True,  filter_string="last_name__icontains")
        create(HeaderFilterItem, pref + 'firstname', order=2, name='first_name',       title=_(u'First name'),      type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True,  filter_string="first_name__icontains")
        create(HeaderFilterItem, pref + 'landline',  order=3, name='landline',         title=_(u'Landline'),        type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True,  filter_string="landline__icontains")
        create(HeaderFilterItem, pref + 'email',     order=4, name='email',            title=_(u'E-mail'),          type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True,  filter_string="email__icontains")
        create(HeaderFilterItem, pref + 'user',      order=5, name='user__username',   title=_(u'User - Username'), type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True,  filter_string="user__username__icontains")
        create(HeaderFilterItem, pref + 'employee',  order=6, name='est_salarie_chez', title=_(u'Employed by'),     type=HFI_RELATION, header_filter=hf, has_a_filter=True, editable=False, filter_string="", relation_predicat_id=REL_SUB_EMPLOYED_BY)

        hf   = HeaderFilter.create(pk='persons-hf_leadcustomer', name=_(u'Prospect/Suspect view'), model=Organisation)
        pref = 'persons-hfi_leadcustomer_'
        create(HeaderFilterItem, pref + 'name',      order=1, name='name',                title=_(u'Name'),                 type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True,  filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'sector',    order=2, name='sector__sector_name', title=_(u'Sector - Sector name'), type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True,  filter_string="sector__sector_name__icontains")
        create(HeaderFilterItem, pref + 'phone',     order=3, name='phone',               title=_(u'Phone'),                type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True,  filter_string="phone__icontains")
        create(HeaderFilterItem, pref + 'email',     order=4, name='email',               title=_(u'E-mail'),               type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True,  filter_string="email__icontains")
        create(HeaderFilterItem, pref + 'user',      order=5, name='user__username',      title=_(u'User - Username'),      type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True,  filter_string="user__username__icontains")
        create(HeaderFilterItem, pref + 'customer',  order=6, name='est_client_de',       title=_(u'Customer of'),          type=HFI_RELATION, header_filter=hf, has_a_filter=True, editable=False, filter_string="", relation_predicat_id=REL_SUB_CUSTOMER_OF)
        create(HeaderFilterItem, pref + 'prospect',  order=7, name='est_prospect_de',     title=_(u'Prospect of'),          type=HFI_RELATION, header_filter=hf, has_a_filter=True, editable=False, filter_string="", relation_predicat_id=REL_SUB_PROSPECT)
        create(HeaderFilterItem, pref + 'suspect',   order=8, name='est_suspect_de',      title=_(u'Suspect of'),           type=HFI_RELATION, header_filter=hf, has_a_filter=True, editable=False, filter_string="", relation_predicat_id=REL_SUB_SUSPECT)

        hf   = HeaderFilter.create(pk='persons-hf_organisation', name=_(u'Organisation view'), model=Organisation)
        pref = 'persons-hfi_organisation_'
        create(HeaderFilterItem, pref + 'name',  order=1, name='name',               title=_(u'Name'),            type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'phone', order=2, name='phone',              title=_(u'Landline'),        type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True, filter_string="phone__icontains")
        create(HeaderFilterItem, pref + 'user',  order=3, name='user__username',     title=_(u'User - Username'), type=HFI_FIELD,    header_filter=hf, has_a_filter=True, editable=True, filter_string="user__username__icontains")
        create(HeaderFilterItem, pref + 'resp',  order=4, name='object_responsable', title=_(u'Managed by'),      type=HFI_RELATION, header_filter=hf, has_a_filter=True, editable=False, filter_string="", relation_predicat_id=REL_OBJ_MANAGES)

        ButtonMenuItem.create(pk='persons-customer_contact_button', model=Contact, button=become_customer_button, order=20)
        ButtonMenuItem.create(pk='persons-prospect_contact_button', model=Contact, button=become_prospect_button, order=21)
        ButtonMenuItem.create(pk='persons-suspect_contact_button',  model=Contact, button=become_suspect_button,  order=22)
        ButtonMenuItem.create(pk='persons-inactive_contact_button', model=Contact, button=become_inactive_button, order=24)

        ButtonMenuItem.create(pk='persons-customer_orga_button',  model=Organisation, button=become_customer_button,    order=20)
        ButtonMenuItem.create(pk='persons-prospect_orga_button',  model=Organisation, button=become_prospect_button,    order=21)
        ButtonMenuItem.create(pk='persons-suspect_orga_button',   model=Organisation, button=become_suspect_button,     order=22)
        ButtonMenuItem.create(pk='persons-inactive_orga_button',  model=Organisation, button=become_inactive_button,    order=23)
        ButtonMenuItem.create(pk='persons-supplier_button',       model=Organisation, button=become_supplier_button,    order=24)
        ButtonMenuItem.create(pk='persons-linked_contact_button', model=Organisation, button=add_linked_contact_button, order=25)

        orga_ct = ContentType.objects.get_for_model(Organisation)

        #Create a list view filter to use it in the report
        managed_orga_filter = create(Filter, name=_(u"Managed by creme"), model_ct=orga_ct, is_custom=False)
        managed_orga_filter_cond  = create(FilterCondition, type_id=FILTER_TYPE_EQUALS, champ='properties__type__id')
        managed_orga_filter_value = create(FilterValue, value=PROP_IS_MANAGED_BY_CREME)

        managed_orga_filter_cond.values = [managed_orga_filter_value]
        managed_orga_filter_cond.save()

        managed_orga_filter.conditions = [managed_orga_filter_cond]
        managed_orga_filter.save()


        admin = User.objects.get(pk=1)

        if not Contact.objects.filter(is_user=admin).exists():
            Contact.objects.create(first_name='Fulbert', last_name='Creme',
                                   civility_id=mister.pk, description="Creme master",
                                   user=admin, is_user=admin
                                  )

        #TODO: add relation to admin ????
        if not Organisation.objects.exists():
            orga = Organisation.objects.create(user=admin, name=_("ReplaceByYourSociety"))
            managed_by_creme = CremePropertyType.objects.get(pk=PROP_IS_MANAGED_BY_CREME)
            CremeProperty.objects.create(type=managed_by_creme, creme_entity=orga)

        SearchConfigItem.create(Contact, ['first_name', 'last_name', 'landline', 'mobile', 'email'])
        SearchConfigItem.create(Organisation, ['name', 'phone', 'email', 'sector__sector_name', 'legal_form__legal_form_name'])

        #Populate blocks
        rbi_1 = RelationBlockItem.create(REL_SUB_CUSTOMER_OF)
        rbi_2 = RelationBlockItem.create(REL_OBJ_CUSTOMER_OF)

        blocks_2_save = [
            BlockConfigItem(content_type=orga_ct, block_id=rbi_1.block_id, order=1, on_portal=False),
            BlockConfigItem(content_type=orga_ct, block_id=rbi_2.block_id, order=2, on_portal=False),
        ]

        creme_core_autodiscover()
        block_ids = [id_ for id_, block in block_registry if block.configurable]
        for i, block_id in enumerate(block_ids):
            blocks_2_save.append(BlockConfigItem(content_type=orga_ct, block_id=block_id, order=i+3, on_portal=False))

        generate_string_id_and_save(BlockConfigItem, blocks_2_save, 'creme_config-userbci')
