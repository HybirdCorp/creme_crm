################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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

from django.apps import apps
from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig

from . import constants


class PersonsConfig(CremeAppConfig):
    default = True
    name = 'creme.persons'
    verbose_name = _('Accounts and Contacts')
    dependencies = ['creme.creme_core']

    def all_apps_ready(self):
        # NB: check MIGRATION_MODE to avoid error with empty SECRET_KEY with
        #     the command 'creme_start_project'
        if not self.MIGRATION_MODE:
            from creme import persons

            self.Contact      = persons.get_contact_model()
            self.Organisation = persons.get_organisation_model()
            self.Address      = persons.get_address_model()
            super().all_apps_ready()
            self.hook_user()
            self.hook_user_form()

            from . import signals  # NOQA

            if apps.is_installed('creme.reports'):
                # self.register_reports_graph_fetchers()
                self.register_reports_chart_fetchers()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Contact, self.Organisation)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            *bricks.brick_classes
        ).register_hat(
            self.Contact,
            main_brick_cls=bricks.ContactBarHatBrick,
            secondary_brick_classes=(bricks.ContactCardHatBrick,),
        ).register_hat(
            self.Organisation,
            main_brick_cls=bricks.OrganisationBarHatBrick,
            secondary_brick_classes=(bricks.OrganisationCardHatBrick,),
        )

    def register_bulk_update(self, bulk_update_registry):
        register = bulk_update_registry.register
        register(self.Organisation)
        register(self.Contact)

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(
            buttons.BecomeCustomerButton,
            buttons.BecomeProspectButton,
            buttons.BecomeSuspectButton,
            buttons.BecomeInactiveButton,
            buttons.BecomeSupplierButton,
            buttons.AddLinkedContactButton,
            buttons.TransformIntoUserButton,
        )

    def register_creme_config(self, config_registry):
        from . import bricks, models

        register_model = config_registry.register_model
        register_model(models.Position,  'position')
        register_model(models.Sector,    'sector')
        register_model(models.LegalForm, 'legal_form')
        register_model(models.StaffSize, 'staff_size')
        register_model(models.Civility,  'civility')

        config_registry.register_portal_bricks(bricks.ManagedOrganisationsBrick)

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.CONTACT_CREATION_CFORM,
            custom_forms.CONTACT_EDITION_CFORM,

            custom_forms.ORGANISATION_CREATION_CFORM,
            custom_forms.ORGANISATION_EDITION_CFORM,
        )

    def register_cloners(self, entity_cloner_registry):
        from . import cloners

        entity_cloner_registry.register(
            model=self.Contact, cloner_class=cloners.ContactCloner,
        ).register(
            model=self.Organisation, cloner_class=cloners.OrganisationCloner,
        )

    def register_deletors(self, entity_deletor_registry):
        from . import deletors

        entity_deletor_registry.register(
            model=self.Contact, deletor_class=deletors.ContactDeletor,
        ).register(
            model=self.Organisation, deletor_class=deletors.OrganisationDeletor,
        )

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(
            self.Contact,
            self.Organisation,
            self.Address,
        )

    def register_field_printers(self, field_printer_registry):
        from django.contrib.auth import get_user_model
        from django.db import models
        from django.utils.html import format_html

        from creme.creme_core.gui.view_tag import ViewTag

        def print_fk_user_html(*, value, user, html_fmt, **kwargs) -> str:
            # TODO: test staff case
            contact = value.linked_contact

            if contact and user.has_perm_to_view(contact):
                return format_html(
                    html_fmt,
                    url=contact.get_absolute_url(),
                    label=value,
                )

            return str(value)

        User = get_user_model()

        for field in (models.ForeignKey, models.OneToOneField):
            for printer in field_printer_registry.printers_for_field_type(
                type=field, tags=[ViewTag.HTML_DETAIL, ViewTag.HTML_LIST],
            ):
                printer.register(
                    model=User,
                    printer=partial(
                        print_fk_user_html, html_fmt='<a href="{url}">{label}</a>',
                    ),
                )

            for printer in field_printer_registry.printers_for_field_type(
                type=field, tags=[ViewTag.HTML_FORM],
            ):
                printer.register(
                    model=User,
                    printer=partial(
                        print_fk_user_html,
                        html_fmt='<a href="{url}" target="_blank">{label}</a>',
                    ),
                )

    def register_icons(self, icon_registry):
        icon_registry.register(
            self.Contact,      'images/contact_%(size)s.png'
        ).register(
            self.Organisation, 'images/organisation_%(size)s.png'
        )

    def register_imprints(self, imprint_manager):
        imprint_manager.register(self.Contact, hours=1)

    def register_mass_import(self, import_form_registry):
        from .forms.mass_import import (
            get_massimport_form_builder as form_builder,
        )

        Contact = self.Contact
        Organisation = self.Organisation
        import_form_registry.register(
            Contact, partial(form_builder, model=Contact),
        ).register(
            Organisation, partial(form_builder, model=Organisation),
        )

    def register_menu_entries(self, menu_registry):
        import creme.creme_core.menu as core_menu

        from . import menu

        menu_registry.register(
            menu.ContactsEntry,
            menu.OrganisationsEntry,
            menu.CustomersEntry,

            menu.ContactCreationEntry,
            menu.OrganisationCreationEntry,
        )

        # Hook CremeEntry
        children = core_menu.CremeEntry.child_classes
        children.insert(
            children.index(core_menu.CremeEntry.UserSeparatorEntry) + 1,
            menu.UserContactEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            group_id='persons-directory', label=_('Directory'), priority=10,
        ).add_link(
            'create_contact', self.Contact, priority=3,
        ).add_link(
            'create_organisation', self.Organisation, priority=5,
        )

    def register_merge_forms(self, merge_form_registry):
        from .forms.merge import get_merge_form_builder as form_builder

        Contact = self.Contact
        Organisation = self.Organisation
        merge_form_registry.register(
            Contact, partial(form_builder, model=Contact),
        ).register(
            Organisation, partial(form_builder, model=Organisation),
        )

    def register_quickforms(self, quickform_registry):
        from .forms import quick

        quickform_registry.register(
            self.Contact, quick.ContactQuickForm,
        ).register(
            self.Organisation, quick.OrganisationQuickForm,
        )

    def register_search_fields(self, search_field_registry):
        from django.db.models import ForeignKey

        from creme.creme_core.core import entity_cell

        from .forms.listview import AddressFKField

        search_field_registry[
            entity_cell.EntityCellRegularField.type_id
        ].builder_4_model_field_type(
            ForeignKey
        ).register_related_model(model=self.Address, sfield_builder=AddressFKField)

    def register_smart_columns(self, smart_columns_registry):
        register = smart_columns_registry.register_model
        register(self.Contact).register_field('first_name') \
                              .register_field('last_name') \
                              .register_field('email') \
                              .register_relationtype(constants.REL_SUB_EMPLOYED_BY)
        register(self.Organisation).register_field('name') \
                                   .register_field('billing_address__city') \
                                   .register_relationtype(constants.REL_OBJ_EMPLOYED_BY)

    def register_statistics(self, statistic_registry):
        from . import statistics

        Contact = self.Contact
        Organisation = self.Organisation
        statistic_registry.register(
            id='persons-contacts',
            label=Contact._meta.verbose_name_plural,
            func=lambda: [Contact.objects.count()],
            perm='persons', priority=3,
        ).register(
            id='persons-organisations',
            label=Organisation._meta.verbose_name_plural,
            func=lambda: [Organisation.objects.count()],
            perm='persons', priority=5,
        ).register(
            id='persons-customers', label=_('Customers'),
            func=statistics.CustomersStatistics(Organisation),
            perm='persons', priority=7,
        ).register(
            id='persons-prospects', label=_('Prospects'),
            func=statistics.ProspectsStatistics(Organisation),
            perm='persons', priority=9,
        ).register(
            id='persons-suspects', label=_('Suspects'),
            func=statistics.SuspectsStatistics(Organisation),
            perm='persons', priority=11,
        )

    def hook_user(self):
        from django.contrib.auth import get_user_model

        from .models.contact import _get_linked_contact

        User = get_user_model()
        User.linked_contact = property(_get_linked_contact)

        def get_absolute_url(this):
            contact = this.linked_contact

            return '' if contact is None else contact.get_absolute_url()

        User.get_absolute_url = get_absolute_url

    def hook_user_form(self):
        from django.contrib.contenttypes.models import ContentType
        from django.forms import ModelChoiceField

        from creme.creme_config.views.user import UserCreation
        from creme.creme_core.forms.widgets import DynamicSelect
        from creme.creme_core.models import Relation, RelationType

        class ContactUserCreationForm(UserCreation.form_class):
            organisation = ModelChoiceField(
                label=_('User organisation'),
                queryset=self.Organisation.objects.filter_managed_by_creme(),
                empty_label=None,
            )
            relation = ModelChoiceField(
                label=_('Position in the organisation'),
                # NB: the QuerySet is built in __init__() because a loading artefact
                #     makes ContentType values inconsistent in unit tests if the
                #     Queryset is built here.
                queryset=RelationType.objects.none(),
                empty_label=None,
                widget=DynamicSelect(attrs={'autocomplete': True}),
                initial=constants.REL_SUB_EMPLOYED_BY,
            )

            blocks = UserCreation.form_class.blocks.new({
                'id': 'contact',
                'label': _('Related Contact'),
                'fields': ('organisation', 'relation'),
            })

            def __init__(this, *args, **kwargs):
                super().__init__(*args, **kwargs)
                fields = this.fields

                get_ct = ContentType.objects.get_for_model
                # TODO: what if there is no choice (e.g. all disabled)?
                fields['relation'].queryset = RelationType.objects.filter(
                    subject_ctypes=get_ct(self.Contact),
                    symmetric_type__subject_ctypes=get_ct(self.Organisation),
                    is_internal=False,
                    enabled=True,
                )

                for field_name in ('first_name', 'last_name', 'email'):
                    field = fields[field_name]
                    field.required = field.widget.is_required = True

            def save(this, *args, **kwargs):
                user = super().save(*args, **kwargs)
                cdata = this.cleaned_data

                # TODO: check properties constraints?
                Relation.objects.create(
                    user=user, subject_entity=user.linked_contact,
                    type=cdata['relation'],
                    object_entity=cdata['organisation'],
                )

                return user

        UserCreation.form_class = ContactUserCreationForm

        # NB: to facilitate customisation by a child class
        return ContactUserCreationForm

    # def register_reports_graph_fetchers(self):
    #     from creme.reports.graph_fetcher_registry import graph_fetcher_registry
    #
    #     from . import reports
    #
    #     graph_fetcher_registry.register(
    #         reports.OwnedGraphFetcher,
    #     )
    def register_reports_chart_fetchers(self):
        from creme.reports.core.chart import fetcher

        from . import reports

        fetcher.chart_fetcher_registry.register(
            reports.OwnedChartFetcher,
        )
