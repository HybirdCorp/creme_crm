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

from collections import OrderedDict
from functools import partial

from django.apps import apps
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.bricks import Brick, SimpleBrick, PaginatedBrick, QuerysetBrick
from creme.creme_core.models import Relation
from creme.creme_core.utils.db import populate_related

from creme import persons
from . import constants


Address = persons.get_address_model()
Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


if apps.is_installed('creme.activities'):
    from datetime import timedelta

    from creme.activities import get_activity_model, constants as activities_constants

    Activity = get_activity_model()


    class Activities4Card:
        dependencies = [Activity]
        relation_type_deps = [activities_constants.REL_SUB_PART_2_ACTIVITY,
                              activities_constants.REL_SUB_ACTIVITY_SUBJECT,
                              activities_constants.REL_SUB_LINKED_2_ACTIVITY,
                             ]

        @staticmethod
        def get(context, entity):
            now = context['today']
            user = context['user']

            if isinstance(entity, Organisation):
                past = Activity.get_past_linked_for_orga
                future = Activity.get_future_linked_for_orga
            else:
                past = Activity.get_past_linked
                future = Activity.get_future_linked

            return {
                'last': EntityCredentials.filter(user, past(entity, now)).first(),
                'next': EntityCredentials.filter(user, future(entity, now)).first(),
            }


    class NeglectedContactIndicator:
        delta = timedelta(days=15)
        label_not = _('Not contacted since 15 days')
        label_never = _('Never contacted')

        def __init__(self, context, contact):
            self.context = context
            self.contact = contact

        @property  # TODO: cached_property ??
        def label(self):
            contact = self.contact

            if not contact.is_user_id:
                time_limit = self.context['today'] - self.delta

                if not Activity.get_future_linked(contact, today=time_limit).exists():
                    return self.label_not if time_limit > contact.created else self.label_never

            return ''
else:
    class NeglectedContactIndicator:
        def __init__(self, context, contact):
            pass

        @property
        def label(self):
            return ''


    class Activities4Card:
        dependencies = []
        relation_type_deps = []

        @staticmethod
        def get(context, entity):
            return {}


if apps.is_installed('creme.opportunities'):
    from creme.opportunities import get_opportunity_model
    from creme.opportunities import constants as opp_constants

    Opportunity = get_opportunity_model()

    class Opportunities4Card:
        dependencies = [Opportunity]
        relation_type_deps = [opp_constants.REL_OBJ_TARGETS]

        @staticmethod
        def get(context, entity):
            return EntityCredentials.filter(context['user'],
                                            Opportunity.objects.filter(is_deleted=False,
                                                                       relations__type=opp_constants.REL_SUB_TARGETS,
                                                                       relations__object_entity=entity.id,
                                                                      )
                                           )
else:
    class Opportunities4Card:
        dependencies = []
        relation_type_deps = []

        @staticmethod
        def get(context, entity):
            return None

if apps.is_installed('creme.commercial'):
    from creme.commercial import get_act_model
    from creme.commercial import constants as commercial_constants

    Act = get_act_model()

    class CommercialActs4Card:
        dependencies = [Act]
        relation_type_deps = [commercial_constants.REL_SUB_COMPLETE_GOAL]

        @staticmethod
        def get(context, entity):
            return EntityCredentials.filter(context['user'],
                                            Act.objects.filter(is_deleted=False,
                                                               relations__type=commercial_constants.REL_OBJ_COMPLETE_GOAL,
                                                               relations__object_entity=entity.id,
                                                              )
                                           )
else:
    class CommercialActs4Card:
        dependencies = []
        relation_type_deps = []

        @staticmethod
        def get(context, entity):
            return None


class ContactBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'persons/bricks/contact-hat-bar.html'


class OrganisationBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'persons/bricks/organisation-hat-bar.html'


class ContactCardHatBrick(Brick):
    id_ = SimpleBrick._generate_hat_id('persons', 'contact_card')
    dependencies = [Contact, Organisation, Relation] + Activities4Card.dependencies\
                                                     + Opportunities4Card.dependencies\
                                                     + CommercialActs4Card.dependencies
    relation_type_deps = [constants.REL_SUB_EMPLOYED_BY] + Activities4Card.relation_type_deps\
                                                         + Opportunities4Card.relation_type_deps\
                                                         + CommercialActs4Card.relation_type_deps
    verbose_name  = _('Card header block')
    template_name = 'persons/bricks/contact-hat-card.html'

    def detailview_display(self, context):
        contact = context['object']
        is_hidden = context['fields_configs'].get_4_model(Contact).is_fieldname_hidden

        return self._render(self.get_template_context(
                    context,
                    hidden_fields={fname
                                       for fname in ('phone', 'mobile', 'email', 'position')
                                           if is_hidden(fname)
                                  },
                    activities=Activities4Card.get(context, contact),
                    neglected_indicator=NeglectedContactIndicator(context, contact),
                    opportunities=Opportunities4Card.get(context, contact),
                    acts=CommercialActs4Card.get(context, contact),
        ))


class OrganisationCardHatBrick(Brick):
    id_ = SimpleBrick._generate_hat_id('persons', 'organisation_card')
    dependencies = [Organisation, Contact, Address, Relation] + Activities4Card.dependencies\
                                                              + Opportunities4Card.dependencies\
                                                              + CommercialActs4Card.dependencies
    relation_type_deps = [constants.REL_OBJ_CUSTOMER_SUPPLIER, constants.REL_SUB_CUSTOMER_SUPPLIER,
                          constants.REL_OBJ_MANAGES, constants.REL_OBJ_EMPLOYED_BY,
                         ] + Activities4Card.relation_type_deps\
                           + Opportunities4Card.relation_type_deps\
                           + CommercialActs4Card.relation_type_deps
    verbose_name  = _('Card header block')
    template_name = 'persons/bricks/organisation-hat-card.html'

    def detailview_display(self, context):
        organisation = context['object']
        user = context['user']
        managed_orgas = Organisation.get_all_managed_by_creme()

        get_fconfigs = context['fields_configs'].get_4_model
        is_hidden = get_fconfigs(Organisation).is_fieldname_hidden

        return self._render(self.get_template_context(
                    context,
                    hidden_fields={fname
                                       for fname in ('phone', 'billing_address', 'legal_form')
                                          if is_hidden(fname)
                                  },
                    position_is_hidden=get_fconfigs(Contact).is_fieldname_hidden('position'),

                    is_customer=managed_orgas.filter(relations__type=constants.REL_OBJ_CUSTOMER_SUPPLIER,
                                                     relations__object_entity=organisation.id,
                                                    )
                                             .exists(),
                    is_supplier=managed_orgas.filter(relations__type=constants.REL_SUB_CUSTOMER_SUPPLIER,
                                                     relations__object_entity=organisation.id,
                                                    )
                                             .exists(),

                    managers=EntityCredentials.filter(user, organisation.get_managers())[:16],
                    employees=EntityCredentials.filter(user, organisation.get_employees())[:16],

                    activities=Activities4Card.get(context, organisation),
                    opportunities=Opportunities4Card.get(context, organisation),
                    acts=CommercialActs4Card.get(context, organisation)
        ))


class ManagersBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('persons', 'managers')
    dependencies  = (Relation, Contact)
    relation_type_deps = (constants.REL_OBJ_MANAGES, )
    verbose_name  = _('Organisation managers')
    template_name = 'persons/bricks/managers.html'
    target_ctypes = (Organisation,)

    def _get_people_qs(self, orga):
        return orga.get_managers()

    def _get_add_title(self):
        return _('Create a manager')  # Lazy -> translated only if used

    def detailview_display(self, context):
        orga = context['object']
        is_hidden = context['fields_configs'].get_4_model(Contact).is_fieldname_hidden

        return self._render(self.get_template_context(context,
                    self._get_people_qs(orga).select_related('civility'),
                    rtype_id=self.relation_type_deps[0],
                    add_title=self._get_add_title(),
                    hidden_fields={fname
                                    for fname in ('phone', 'mobile', 'email')
                                        if is_hidden(fname)
                                  },
        ))


class EmployeesBrick(ManagersBrick):
    id_           = QuerysetBrick.generate_id('persons', 'employees')
    relation_type_deps = (constants.REL_OBJ_EMPLOYED_BY, )
    verbose_name  = _('Organisation employees')
    template_name = 'persons/bricks/employees.html'

    def _get_people_qs(self, orga):
        return orga.get_employees()

    def _get_add_title(self):
        return _('Create an employee')  # Lazy -> translated only if used


# TODO: factorise (see CSV import) ? (exclude param in info_field_names())
def _get_address_field_names():
    field_names = list(Address.info_field_names())

    try:
        field_names.remove('name')
    except ValueError:
        pass

    return field_names


class _AddressesBrick(Brick):
    dependencies  = (Address,)
    verbose_name  = 'Addresses'
    target_ctypes = (Contact, Organisation)

    def get_template_context(self, context, **kwargs):
        person = context['object']
        model = person.__class__
        is_hidden = context['fields_configs'].get_4_model(model).is_field_hidden

        def prepare_address(attr_name):
            display_button = display_content = False

            try:
                addr = getattr(person, attr_name)
            except AttributeError:
                addr = Address()
            else:
                if is_hidden(model._meta.get_field(attr_name)):
                    if addr is None:
                        addr = Address()
                elif addr is None:
                    addr = Address()
                    display_button = True
                else:
                    display_content = True

            addr.display_button  = display_button
            addr.display_content = display_content

            addr.owner = person  # NB: avoids a query (per address) for credentials.

            return addr

        populate_related((person,), ['billing_address', 'shipping_address'])
        b_address = prepare_address('billing_address')
        s_address = prepare_address('shipping_address')

        build_cell = partial(EntityCellRegularField.build, model=Address)

        return super().get_template_context(
                    context,
                    b_address=b_address,
                    s_address=s_address,
                    cells=OrderedDict((fname, build_cell(name=fname)) for fname in _get_address_field_names()),
        )

    def detailview_display(self, context):
        return self._render(self.get_template_context(context))



class DetailedAddressesBrick(_AddressesBrick):
    id_           = Brick.generate_id('persons', 'address')  # TODO: rename 'addresses'
    verbose_name  = _('Addresses (detailed)')
    template_name = 'persons/bricks/addresses-detailed.html'


class PrettyAddressesBrick(_AddressesBrick):
    id_           = Brick.generate_id('persons', 'addresses_pretty')
    verbose_name  = _('Addresses (pretty)')
    template_name = 'persons/bricks/addresses-pretty.html'


class _OtherAddressesBrick(QuerysetBrick):
    dependencies  = (Address,)
    verbose_name  = 'Other addresses'
    target_ctypes = (Contact, Organisation)

    def get_template_context(self, context, **kwargs):
        build_cell = partial(EntityCellRegularField.build, model=Address)

        return super().get_template_context(
                    context,
                    context['object'].other_addresses,
                    cells=OrderedDict((fname, build_cell(name=fname)) for fname in _get_address_field_names()),
        )

    def detailview_display(self, context):
        return self._render(self.get_template_context(context))


class DetailedOtherAddressesBrick(_OtherAddressesBrick):
    id_           = QuerysetBrick.generate_id('persons', 'other_address')  # TODO: rename 'other_addresses'
    dependencies  = (Address,)
    verbose_name  = _('Other addresses (detailed)')
    template_name = 'persons/bricks/other-addresses-detailed.html'
    target_ctypes = (Contact, Organisation)


class PrettyOtherAddressesBrick(_OtherAddressesBrick):
    id_           = QuerysetBrick.generate_id('persons', 'other_addresses_pretty')
    verbose_name  = _('Other addresses (pretty)')
    template_name = 'persons/bricks/other-addresses-pretty.html'


class ManagedOrganisationsBrick(PaginatedBrick):
    id_           = Brick.generate_id('persons', 'managed_organisations')
    dependencies  = (Organisation,)
    verbose_name  = 'Managed organisations'
    template_name = 'persons/bricks/managed-organisations.html'
    configurable  = False

    def detailview_display(self, context):
        return self._render(self.get_template_context(
                    context,
                    Organisation.get_all_managed_by_creme(),
        ))


bricks_list = (
    DetailedAddressesBrick,
    PrettyAddressesBrick,
    DetailedOtherAddressesBrick,
    PrettyOtherAddressesBrick,
    ManagersBrick,
    EmployeesBrick,
    ManagedOrganisationsBrick,
)


if apps.is_installed('creme.activities'):
    class NeglectedOrganisationsBrick(PaginatedBrick):
        """Customers/prospects organisations that have no Activity in the future."""
        id_           = PaginatedBrick.generate_id('persons', 'neglected_orgas')
        dependencies  = (Activity,)
        verbose_name  = _('Neglected organisations')
        template_name = 'persons/bricks/neglected-organisations.html'

        _RTYPE_IDS_CUSTOMERS = (constants.REL_SUB_CUSTOMER_SUPPLIER, constants.REL_SUB_PROSPECT)
        _RTYPE_IDS_ORGA_N_ACT = (activities_constants.REL_SUB_ACTIVITY_SUBJECT, activities_constants.REL_SUB_LINKED_2_ACTIVITY)
        _RTYPE_IDS_EMPLOYEES = (constants.REL_SUB_MANAGES, constants.REL_SUB_EMPLOYED_BY)
        _RTYPE_IDS_CONTACT_N_ACT = (activities_constants.REL_SUB_PART_2_ACTIVITY,
                                    activities_constants.REL_SUB_ACTIVITY_SUBJECT,
                                    activities_constants.REL_SUB_LINKED_2_ACTIVITY,
                                   )

        def _get_neglected(self, now):
            user_contacts     = Contact.objects.filter(is_user__isnull=False).values_list('id', flat=True)
            future_activities = list(Activity.objects.filter(start__gte=now,
                                                             relations__type=activities_constants.REL_OBJ_PART_2_ACTIVITY,
                                                             relations__object_entity__in=user_contacts,
                                                             )
                                                     .values_list('id', flat=True)
                                    )
            neglected_orgas_qs = Organisation.objects.filter(is_deleted=False,
                                                             relations__type__in=self._RTYPE_IDS_CUSTOMERS,
                                                             relations__object_entity__in=Organisation.get_all_managed_by_creme(),
                                                            ) \
                                                     .exclude(relations__type=constants.REL_SUB_INACTIVE) \
                                                     .distinct()

            if not future_activities:
                return neglected_orgas_qs  # No need to retrieve it & transform into a list (good idea ??)

            neglected_orgas = list(neglected_orgas_qs.exclude(relations__object_entity__in=future_activities,
                                                              relations__type__in=self._RTYPE_IDS_ORGA_N_ACT,
                                                             )
                                  )

            if neglected_orgas:
                linked_people_map = dict(Relation.objects.filter(type__in=self._RTYPE_IDS_EMPLOYEES,
                                                                 object_entity__in=[o.id for o in neglected_orgas],
                                                                )
                                                         .values_list('subject_entity_id', 'object_entity_id')
                                        )
                activity_links = Relation.objects.filter(type__in=self._RTYPE_IDS_CONTACT_N_ACT,
                                                         subject_entity__in=linked_people_map.keys(),
                                                         object_entity__in=future_activities,
                                                        )

                neglected_map = {orga.id: True for orga in neglected_orgas}  # 'True' means 'neglected'
                for rel in activity_links:
                    neglected_map[linked_people_map[rel.subject_entity_id]] = False

                neglected_orgas = [orga for orga in neglected_orgas if neglected_map[orga.id]]

            return neglected_orgas

        def home_display(self, context):
            # We do not check the 'persons' permission, because it's only
            # statistics for people who cannot see Organisations.
            return self._render(self.get_template_context(
                        context,
                        self._get_neglected(context['today']),
            ))

    bricks_list += (
        NeglectedOrganisationsBrick,
    )
