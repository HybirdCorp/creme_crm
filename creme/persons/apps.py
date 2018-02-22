# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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

from .statistics import CustomersStatistics


class PersonsConfig(CremeAppConfig):
    name = 'creme.persons'
    verbose_name = _(u'Accounts and Contacts')
    dependencies = ['creme.creme_core']

    def all_apps_ready(self):
        from creme import persons

        self.Contact      = persons.get_contact_model()
        self.Organisation = persons.get_organisation_model()
        self.Address      = persons.get_address_model()
        super(PersonsConfig, self).all_apps_ready()
        self.hook_user()
        self.hook_user_form()

        from . import signals

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Contact, self.Organisation)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(*bricks.bricks_list)
        brick_registry.register_hat(self.Contact,
                                    main_brick_cls=bricks.ContactBarHatBrick,
                                    secondary_brick_classes=(bricks.ContactCardHatBrick,),
                                   )
        brick_registry.register_hat(self.Organisation,
                                    main_brick_cls=bricks.OrganisationBarHatBrick,
                                    secondary_brick_classes=(bricks.OrganisationCardHatBrick,),
                                   )

    def register_bulk_update(self, bulk_update_registry):
        register = bulk_update_registry.register
        register(self.Organisation)
        register(self.Contact)

    def register_buttons(self, button_registry):
        # from .buttons import button_list
        # button_registry.register(*button_list)
        from . import buttons
        button_registry.register(
            buttons.BecomeCustomerButton,
            buttons.BecomeProspectButton,
            buttons.BecomeSuspectButton,
            buttons.BecomeInactiveButton,
            buttons.BecomeSupplierButton,
            buttons.AddLinkedContactButton,
        )

    def register_field_printers(self, field_printers_registry):
        from django.contrib.auth import get_user_model

        from creme.creme_core.gui.field_printers import print_foreignkey_html
        from creme.creme_core.templatetags.creme_widgets import widget_entity_hyperlink

        def print_fk_user_html(entity, fval, user, field):
            if fval.is_team:
                return unicode(fval)

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
        from django.conf import settings
        from django.core.urlresolvers import reverse_lazy as reverse

        Contact = self.Contact
        Organisation = self.Organisation

        if settings.OLD_MENU:
            from creme.creme_core.auth import build_creation_perm as cperm

            reg_item = creme_menu.register_app('persons', '/persons/').register_item
            reg_item(reverse('persons__portal'),              _(u'Portal of accounts and contacts'),     'persons')
            reg_item(reverse('persons__list_contacts'),       _(u'All contacts'),                        'persons')
            reg_item(reverse('persons__create_contact'),      Contact.creation_label,                    cperm(Contact))
            reg_item(reverse('persons__leads_customers'),     _(u'My customers / prospects / suspects'), 'persons')
            reg_item(reverse('persons__list_organisations'),  _(u'All organisations'),                   'persons')
            reg_item(reverse('persons__create_organisation'), Organisation.creation_label,               cperm(Organisation))
        else:
            from .gui import UserContactURLItem

            URLItem = creme_menu.URLItem
            creme_menu.get('creme', 'user').add(UserContactURLItem('persons-user_contact'), priority=2)
            creme_menu.get('features') \
                      .get_or_create(creme_menu.ContainerItem, 'persons-directory', priority=20,
                                     defaults={'label': _(u'Directory')},
                                    ) \
                      .add(URLItem.list_view('persons-organisations', model=Organisation), priority=10) \
                      .add(URLItem.list_view('persons-contacts',      model=Contact),      priority=20) \
                      .add(URLItem('persons-lead_customers', url=reverse('persons__leads_customers'),
                                   label=_(u'My customers / prospects / suspects'), perm='persons',
                                  ),
                           priority=30,
                          )
            creme_menu.get('creation', 'main_entities') \
                      .add(URLItem.creation_view('persons-create_organisation', model=Organisation), priority=10) \
                      .add(URLItem.creation_view('persons-create_contact',      model=Contact),      priority=20)
            creme_menu.get('creation', 'any_forms') \
                      .get_or_create_group('persons-directory', _(u'Directory'), priority=10) \
                      .add_link('create_contact',      Contact,      priority=3) \
                      .add_link('create_organisation', Organisation, priority=5)

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

    def register_statistics(self, statistics_registry):
        Contact = self.Contact
        Organisation = self.Organisation
        statistics_registry.register(id='persons-contacts', label=Contact._meta.verbose_name_plural,
                                     func=lambda: [Contact.objects.count()],
                                     perm='persons', priority=3,
                                    ) \
                           .register(id='persons-organisations', label=Organisation._meta.verbose_name_plural,
                                     func=lambda: [Organisation.objects.count()],
                                     perm='persons', priority=5,
                                    ) \
                           .register(id='persons-customers', label=_(u'Customers'),
                                     func=CustomersStatistics(Organisation),
                                     perm='persons', priority=7,
                                    )

    def hook_user(self):
        from django.contrib.auth import get_user_model

        from .models.contact import _get_linked_contact

        User = get_user_model()
        User.linked_contact = property(_get_linked_contact)
        User.get_absolute_url = lambda u: u.linked_contact.get_absolute_url()

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
                                        label=_(u'User organisation'),
                                        queryset=self.Organisation.get_all_managed_by_creme(),
                                        empty_label=None,
                                     )
            fields['relation'] = ModelChoiceField(
                                    label=_(u'Position in the organisation'),
                                    queryset=RelationType.objects.filter(subject_ctypes=get_ct(self.Contact),
                                                                         object_ctypes=get_ct(self.Organisation),
                                                                         is_internal=False,
                                                                        ),
                                    empty_label=None,
                                    widget=DynamicSelect(attrs={'autocomplete': True}),
                                 )

            def set_required(name):
                field = fields[name]
                field.required = field.widget.is_required = True

            set_required('first_name')
            set_required('last_name')
            set_required('email')

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
