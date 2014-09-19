# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms.widgets import DynamicSelect
from creme.creme_core.registry import creme_registry
from creme.creme_core.gui import (creme_menu, button_registry, block_registry,
        icon_registry, quickforms_registry, import_form_registry,
        bulk_update_registry, merge_form_registry, smart_columns_registry)

from .constants import REL_SUB_EMPLOYED_BY, REL_OBJ_EMPLOYED_BY
from .blocks import block_list, ContactBlock, OrganisationBlock
from .buttons import button_list
from .forms.quick import ContactQuickForm, OrganisationQuickForm
from .forms.lv_import import get_csv_form_builder
from .forms.merge import get_merge_form_builder
from .models import Contact, Organisation


creme_registry.register_entity_models(Contact, Organisation)
creme_registry.register_app('persons', _(u'Accounts and Contacts'), '/persons')

reg_item = creme_menu.register_app('persons', '/persons/').register_item
reg_item('/persons/',                 _(u'Portal of accounts and contacts'),     'persons')
reg_item('/persons/contacts',         _(u'All contacts'),                        'persons')
reg_item('/persons/leads_customers',  _(u'My customers / prospects / suspects'), 'persons')
reg_item('/persons/contact/add',      Contact.creation_label,                    'persons.add_contact')
reg_item('/persons/organisations',    _(u'All organisations'),                   'persons')
reg_item('/persons/organisation/add', Organisation.creation_label,               'persons.add_organisation')

button_registry.register(*button_list)

block_registry.register_4_model(Contact,      ContactBlock())
block_registry.register_4_model(Organisation, OrganisationBlock())
block_registry.register(*block_list)

reg_icon = icon_registry.register
reg_icon(Contact,      'images/contact_%(size)s.png')
reg_icon(Organisation, 'images/organisation_%(size)s.png')

reg_qform = quickforms_registry.register
reg_qform(Contact,      ContactQuickForm)
reg_qform(Organisation, OrganisationQuickForm)

reg_csv_form = import_form_registry.register
reg_csv_form(Contact,      get_csv_form_builder)
reg_csv_form(Organisation, get_csv_form_builder)

reg_merge_form = merge_form_registry.register
reg_merge_form(Contact,      get_merge_form_builder)
reg_merge_form(Organisation, get_merge_form_builder)

bulk_update_registry.register(Contact)
bulk_update_registry.register(Organisation, exclude=['siren'])

smart_columns_registry.register_model(Contact).register_field('first_name') \
                                              .register_field('last_name') \
                                              .register_field('email') \
                                              .register_relationtype(REL_SUB_EMPLOYED_BY)
smart_columns_registry.register_model(Organisation).register_field('name') \
                                                   .register_field('billing_address__city') \
                                                   .register_relationtype(REL_OBJ_EMPLOYED_BY)


#Hooking the User creation form ------------------------------------------------
from creme.creme_config.forms.user import UserAddForm

def _add_related_orga_fields(form):
    from django.contrib.contenttypes.models import ContentType
    from django.forms import ModelChoiceField

    from creme.creme_core.models import RelationType

    fields = form.fields
    get_ct = ContentType.objects.get_for_model
    fields['organisation'] = ModelChoiceField(label=_('User organisation'),
                                              queryset=Organisation.get_all_managed_by_creme(),
                                              empty_label=None,
                                             )
    fields['relation'] = ModelChoiceField(label=_('Position in the organisation'),
                                          queryset=RelationType.objects.filter(subject_ctypes=get_ct(Contact),
                                                                               object_ctypes=get_ct(Organisation),
                                                                              ),
                                          empty_label=None,
                                          widget=DynamicSelect(attrs={'autocomplete':True}),
                                         )
    fields['first_name'].required = True
    fields['last_name'].required = True
    fields['email'].required = True

def _save_related_orga_fields(form):
    from creme.creme_core.models import Relation

    cdata = form.cleaned_data
    user = form.instance

    Relation.objects.create(user=user, subject_entity=user.linked_contact,
                            type=cdata['relation'],
                            object_entity=cdata['organisation'],
                           )

UserAddForm.add_post_init_callback(_add_related_orga_fields)
UserAddForm.add_post_save_callback(_save_related_orga_fields)
