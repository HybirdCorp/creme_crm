# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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

from functools import partial

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class PersonsConfig(CremeAppConfig):
    name = 'creme.persons'
    verbose_name = _(u'Accounts and Contacts')
    dependencies = ['creme.creme_core']

    def all_apps_ready(self):
        from . import get_contact_model, get_organisation_model, get_address_model

        self.Contact = get_contact_model()
        self.Organisation = get_organisation_model()
        self.Address = get_address_model()
        super(PersonsConfig, self).all_apps_ready()
        self.hook_user()
        self.hook_user_form()

        from . import signals

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('persons', _(u'Accounts and Contacts'), '/persons')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Contact, self.Organisation)

    def register_blocks(self, block_registry):
        from .blocks import block_list

        block_registry.register(*block_list)

    def register_bulk_update(self, bulk_update_registry):
        register = bulk_update_registry.register
        register(self.Organisation)
        register(self.Contact)

    def register_buttons(self, button_registry):
        from .buttons import button_list

        button_registry.register(*button_list)

    # def register_fields_config(self, fields_config_registry):
    #     fields_config_registry.register(self.Address)

    def register_field_printers(self, field_printers_registry):
        from django.contrib.auth import get_user_model

        from creme.creme_core.gui.field_printers import print_foreignkey_html
        from creme.creme_core.templatetags.creme_widgets import widget_entity_hyperlink

        def print_fk_user_html(entity, fval, user, field):
            return widget_entity_hyperlink(fval.linked_contact, user)

        print_foreignkey_html.register(get_user_model(), print_fk_user_html)

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.Contact,      'images/contact_%(size)s.png')
        reg_icon(self.Organisation, 'images/organisation_%(size)s.png')

    def register_mass_import(self, import_form_registry):
        from .forms.mass_import import get_massimport_form_builder

        reg_form = import_form_registry.register
        Contact = self.Contact
        Organisation = self.Organisation
        reg_form(Contact, partial(get_massimport_form_builder, model=Contact))
        reg_form(Organisation, partial(get_massimport_form_builder, model=Organisation))

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm as cperm

        Contact = self.Contact
        Organisation = self.Organisation
        reg_item = creme_menu.register_app('persons', '/persons/').register_item
        reg_item('/persons/',                             _(u'Portal of accounts and contacts'),     'persons')
        reg_item(reverse('persons__list_contacts'),       _(u'All contacts'),                        'persons')
        reg_item(reverse('persons__create_contact'),      Contact.creation_label,                    cperm(Contact))
        reg_item(reverse('persons__leads_customers'),     _(u'My customers / prospects / suspects'), 'persons')
        reg_item(reverse('persons__list_organisations'),  _(u'All organisations'),                   'persons')
        reg_item(reverse('persons__create_organisation'), Organisation.creation_label,               cperm(Organisation))

    def register_merge_forms(self, merge_form_registry):
        from .forms.merge import get_merge_form_builder

        reg_merge_form = merge_form_registry.register
        Contact = self.Contact
        Organisation = self.Organisation
        reg_merge_form(Contact,      partial(get_merge_form_builder, model=Contact))
        reg_merge_form(Organisation, partial(get_merge_form_builder, model=Organisation))

    def register_quickforms(self, quickforms_registry):
        from .forms.quick import ContactQuickForm, OrganisationQuickForm

        reg_qform = quickforms_registry.register
        reg_qform(self.Contact,      ContactQuickForm)
        reg_qform(self.Organisation, OrganisationQuickForm)

    def register_smart_columns(self, smart_columns_registry):
        from .constants import REL_SUB_EMPLOYED_BY, REL_OBJ_EMPLOYED_BY

        register = smart_columns_registry.register_model
        register(self.Contact).register_field('first_name') \
                              .register_field('last_name') \
                              .register_field('email') \
                              .register_relationtype(REL_SUB_EMPLOYED_BY)
        register(self.Organisation).register_field('name') \
                                   .register_field('billing_address__city') \
                                   .register_relationtype(REL_OBJ_EMPLOYED_BY)

    def hook_user(self):
        from django.contrib.auth import get_user_model

        from .models.contact import _get_linked_contact

        get_user_model().linked_contact = property(_get_linked_contact)


    def hook_user_form(self):
        from creme.creme_config.forms.user import UserAddForm

        def _add_related_orga_fields(form):
            from django.contrib.contenttypes.models import ContentType
            from django.forms import ModelChoiceField

            from creme.creme_core.forms.widgets import DynamicSelect
            from creme.creme_core.models import RelationType

            fields = form.fields
            get_ct = ContentType.objects.get_for_model
            fields['organisation'] = ModelChoiceField(
                                        label=_('User organisation'),
                                        queryset=self.Organisation.get_all_managed_by_creme(),
                                        empty_label=None,
                                     )
            fields['relation'] = ModelChoiceField(
                                    label=_('Position in the organisation'),
                                    queryset=RelationType.objects.filter(subject_ctypes=get_ct(self.Contact),
                                                                         object_ctypes=get_ct(self.Organisation),
                                                                         is_internal=False,
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
