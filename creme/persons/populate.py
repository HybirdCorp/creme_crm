# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD, HFI_RELATION
from creme_core.models import CremeProperty, CremePropertyType, ButtonMenuItem
from creme_core.models.relation import create_relation_type
from creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from persons.models import *
from persons.constants import *
from persons.buttons import (become_customer_button, become_prospect_button, become_suspect_button,
                             become_inactive_button, become_supplier_button, add_linked_contact_button)


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        create_relation_type((REL_SUB_EMPLOYED_BY, u'est salarié de',             [Contact]),
                             (REL_OBJ_EMPLOYED_BY, u'a pour salarié',             [Organisation]))
        create_relation_type((REL_SUB_CUSTOMER_OF, u'est client de',              [Contact, Organisation]),
                             (REL_OBJ_CUSTOMER_OF, u'a pour client',              [Contact, Organisation]))
        create_relation_type((REL_SUB_MANAGES,     u'est un des responsables de', [Contact]),
                             (REL_OBJ_MANAGES,     u'a pour responsable',         [Organisation]))
        create_relation_type((REL_SUB_PROSPECT,    u'est prospect de',            [Contact, Organisation]),
                             (REL_OBJ_PROSPECT,    u'a pour prospect',            [Contact, Organisation]))
        create_relation_type((REL_SUB_SUSPECT,     u'est suspect de',             [Contact, Organisation]),
                             (REL_OBJ_SUSPECT,     u'a pour suspect',             [Contact, Organisation]))
        create_relation_type((REL_SUB_PARTNER,     u'est partenaire de',          [Contact, Organisation]),
                             (REL_OBJ_PARTNER,     u'a pour partenaire',          [Contact, Organisation]))
        create_relation_type((REL_SUB_SUPPLIER,    u'est un fournisseur de',      [Contact, Organisation]),
                             (REL_OBJ_SUPPLIER,    u'a pour fournisseur',         [Contact, Organisation]))
        create_relation_type((REL_SUB_INACTIVE,    u'est un client inactif de',   [Contact, Organisation]),
                             (REL_OBJ_INACTIVE,    u'a pour client inactif',      [Contact, Organisation]))

        create(Civility, 1, civility_name=_(u"Madame"))
        create(Civility, 2, civility_name=_(u"Mademoiselle"))
        mister = create(Civility, 3, civility_name=_(u"Monsieur"))
        create(Civility, 4, civility_name=_(u"Non renseigné"))

        create(PeopleFunction, 1, function_name=_(u"PDG"))
        create(PeopleFunction, 2, function_name=_(u"Secrétaire"))
        create(PeopleFunction, 3, function_name=_(u"Développeur"))

        create(Sector, 1, sector_name=_(u"Agro-Alimentaire"))
        create(Sector, 2, sector_name=_(u"Industrie"))
        create(Sector, 3, sector_name=_(u"Informatique"))
        create(Sector, 4, sector_name=_(u"Télécom"))
        create(Sector, 5, sector_name=_(u"Restauration"))

        create(LegalForm, 1, legal_form_name=_(u"SARL"))
        create(LegalForm, 2, legal_form_name=_(u"Association loi 1901"))
        create(LegalForm, 3, legal_form_name=_(u"SA"))
        create(LegalForm, 4, legal_form_name=_(u"SAS"))

        create(StaffSize, 1, employees="1 - 5")
        create(StaffSize, 2, employees="6 - 10")
        create(StaffSize, 3, employees="11 - 50")
        create(StaffSize, 4, employees="51 - 100")
        create(StaffSize, 5, employees="100 - 500")
        create(StaffSize, 6, employees="> 500")

        get_ct = ContentType.objects.get_for_model
        contact_ct_id = get_ct(Contact).id

        hf_id = create(HeaderFilter, 'persons-hf_contact', name=u'Vue de Contact', entity_type_id=contact_ct_id, is_custom=False).id
        pref  = 'persons-hfi_contact_'
        create(HeaderFilterItem, pref + 'lastname',  order=1, name='last_name',        title=u'Nom',              type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True,  filter_string="last_name__icontains")
        create(HeaderFilterItem, pref + 'firstname', order=2, name='first_name',       title=u'Prénom',           type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True,  filter_string="first_name__icontains")
        create(HeaderFilterItem, pref + 'landline',  order=3, name='landline',         title=u'Téléphone',        type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True,  filter_string="landline__icontains")
        create(HeaderFilterItem, pref + 'email',     order=4, name='email',            title=u'E-mail',           type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True,  filter_string="email__icontains")
        create(HeaderFilterItem, pref + 'user',      order=5, name='user',             title=u'Utilisateur',      type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True,  filter_string="user__username__icontains")
        create(HeaderFilterItem, pref + 'employee',  order=6, name='est_salarie_chez', title=u'Est salarié chez', type=HFI_RELATION, header_filter_id=hf_id, has_a_filter=True, editable=False, filter_string="", relation_predicat_id=REL_SUB_EMPLOYED_BY)

        hf_id = create(HeaderFilter, 'persons-hf_leadcustomer', name=u"Vue Prospect/Suspect", entity_type_id=contact_ct_id, is_custom=False).id
        pref  = 'persons-hfi_leadcustomer_'
        create(HeaderFilterItem, pref + 'lastname',  order=1, name='last_name',       title=u'Nom',             type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True,  filter_string="last_name__icontains")
        create(HeaderFilterItem, pref + 'firstname', order=2, name='first_name',      title=u'Prénom',          type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True,  filter_string="first_name__icontains")
        create(HeaderFilterItem, pref + 'landline',  order=3, name='landline',        title=u'Téléphone',       type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True,  filter_string="landline__icontains")
        create(HeaderFilterItem, pref + 'email',     order=4, name='email',           title=u'E-mail',          type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True,  filter_string="email__icontains")
        create(HeaderFilterItem, pref + 'user',      order=5, name='user',            title=u'Utilisateur',     type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True,  filter_string="user__username__icontains")
        create(HeaderFilterItem, pref + 'customer',  order=6, name='est_client_de',   title=u'Est client de',   type=HFI_RELATION, header_filter_id=hf_id, has_a_filter=True, editable=False, filter_string="", relation_predicat_id=REL_SUB_CUSTOMER_OF)
        create(HeaderFilterItem, pref + 'prospect',  order=7, name='est_prospect_de', title=u'Est prospect de', type=HFI_RELATION, header_filter_id=hf_id, has_a_filter=True, editable=False, filter_string="", relation_predicat_id=REL_SUB_PROSPECT)
        create(HeaderFilterItem, pref + 'suspect',   order=8, name='est_suspect_de',  title=u'Est suspect de',  type=HFI_RELATION, header_filter_id=hf_id, has_a_filter=True, editable=False, filter_string="", relation_predicat_id=REL_SUB_SUSPECT)


        orga_ct_id  = get_ct(Organisation).id

        hf_id = create(HeaderFilter, 'persons-hf_organisation', name=u"Vue de Société", entity_type_id=orga_ct_id, is_custom=False).id
        pref  = 'persons-hfi_organisation_'
        create(HeaderFilterItem, pref + 'name',  order=1, name='name',               title=u'Nom',                type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'phone', order=2, name='phone',              title=u'Téléphone',          type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="phone__icontains")
        create(HeaderFilterItem, pref + 'user',  order=3, name='user',               title=u'Utilisateur',        type=HFI_FIELD,    header_filter_id=hf_id, has_a_filter=True, editable=True, filter_string="user__username__icontains")
        create(HeaderFilterItem, pref + 'resp',  order=4, name='object_responsable', title=u'A pour responsable', type=HFI_RELATION, header_filter_id=hf_id, has_a_filter=True, editable=False, filter_string="", relation_predicat_id=REL_OBJ_MANAGES)

        create(ButtonMenuItem, 'persons-customer_contact_button', content_type_id=contact_ct_id, button_id=become_customer_button.id_, order=20)
        create(ButtonMenuItem, 'persons-prospect_contact_button', content_type_id=contact_ct_id, button_id=become_prospect_button.id_, order=21)
        create(ButtonMenuItem, 'persons-suspect_contact_button',  content_type_id=contact_ct_id, button_id=become_suspect_button.id_,  order=22)
        create(ButtonMenuItem, 'persons-inactive_contact_button', content_type_id=contact_ct_id, button_id=become_inactive_button.id_, order=24)

        create(ButtonMenuItem, 'persons-customer_orga_button',  content_type_id=orga_ct_id, button_id=become_customer_button.id_,    order=20)
        create(ButtonMenuItem, 'persons-prospect_orga_button',  content_type_id=orga_ct_id, button_id=become_prospect_button.id_,    order=21)
        create(ButtonMenuItem, 'persons-suspect_orga_button',   content_type_id=orga_ct_id, button_id=become_suspect_button.id_,     order=22)
        create(ButtonMenuItem, 'persons-inactive_orga_button',  content_type_id=orga_ct_id, button_id=become_inactive_button.id_,    order=23)
        create(ButtonMenuItem, 'persons-supplier_button',       content_type_id=orga_ct_id, button_id=become_supplier_button.id_,    order=24)
        create(ButtonMenuItem, 'persons-linked_contact_button', content_type_id=orga_ct_id, button_id=add_linked_contact_button.id_, order=25)


        admin = User.objects.get(pk=1) #TODO: use constant ?????

        admin_contact = create(Contact, first_name='Fulbert', last_name='Creme', civility_id=mister.pk, description="Creme master", user_id=admin.pk, is_user_id=admin.pk)

        #TODO: add relation to admin ????
        orga = create(Organisation, name="ReplaceByYourSociety", user_id=admin.pk)
        managed_by_creme = CremePropertyType.objects.get(pk=PROP_IS_MANAGED_BY_CREME)
        property_ = CremeProperty(type=managed_by_creme, creme_entity=orga)
        property_.save()
