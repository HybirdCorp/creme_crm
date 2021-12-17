# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from typing import List, Sequence, Tuple, Type

from django.apps import apps
from django.db.models.query_utils import FilteredRelation, Q
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.bricks import (
    Brick,
    PaginatedBrick,
    QuerysetBrick,
    SimpleBrick,
)
from creme.creme_core.models import CremeEntity, Relation
from creme.creme_core.utils.db import populate_related

from . import constants

Address = persons.get_address_model()
Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


if apps.is_installed('creme.activities'):
    from datetime import timedelta

    from creme.activities import constants as activities_constants
    from creme.activities import get_activity_model
    from creme.activities.constants import NARROW

    Activity = get_activity_model()

    class Activities4Card:
        dependencies = [Activity]
        relation_type_deps = [
            activities_constants.REL_SUB_PART_2_ACTIVITY,
            activities_constants.REL_SUB_ACTIVITY_SUBJECT,
            activities_constants.REL_SUB_LINKED_2_ACTIVITY,
        ]

        @staticmethod
        def get(context, entity):
            now = context['today']
            user = context['user']

            if isinstance(entity, Organisation):
                past = Activity.objects.past_linked_to_organisation
                future = Activity.objects.future_linked_to_organisation
            else:
                past = Activity.objects.past_linked
                future = Activity.objects.future_linked

            return {
                'last': EntityCredentials.filter(user, past(entity, now)).first(),
                'next': EntityCredentials.filter(user, future(entity, now)).first(),
                # NB: we avoid a templatetag from activities, because dynamic
                #     {% load %} is not possible.
                'NARROW': NARROW,
            }

    class NeglectedContactIndicator:
        delta = timedelta(days=15)
        label_not = _('Not contacted since 15 days')
        label_never = _('Never contacted')

        def __init__(self, context, contact):
            self.context = context
            self.contact = contact

        # @property  # TODO: cached_property ??
        @cached_property
        def label(self):
            contact = self.contact

            if not contact.is_user_id:
                time_limit = self.context['today'] - self.delta

                if not Activity.objects.future_linked(contact, today=time_limit).exists():
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
        dependencies: List[Type[CremeEntity]] = []
        relation_type_deps: List[str] = []

        @staticmethod
        def get(context, entity):
            return {}

if apps.is_installed('creme.opportunities'):
    from creme.opportunities import constants as opp_constants
    from creme.opportunities import get_opportunity_model

    Opportunity = get_opportunity_model()

    class Opportunities4Card:
        dependencies = [Opportunity]
        relation_type_deps = [opp_constants.REL_OBJ_TARGETS]

        @staticmethod
        def get(context, entity):
            return EntityCredentials.filter(
                context['user'],
                Opportunity.objects.annotate(
                    relations_w_person=FilteredRelation(
                        'relations',
                        condition=Q(relations__object_entity=entity.id),
                    ),
                ).filter(
                    is_deleted=False,
                    relations_w_person__type=opp_constants.REL_SUB_TARGETS,
                )
            )
else:
    class Opportunities4Card:
        dependencies: List[Type[CremeEntity]] = []
        relation_type_deps: List[str] = []

        @staticmethod
        def get(context, entity):
            return None

if apps.is_installed('creme.commercial'):
    from creme.commercial import constants as commercial_constants
    from creme.commercial import get_act_model

    Act = get_act_model()

    class CommercialActs4Card:
        dependencies = [Act]
        relation_type_deps = [commercial_constants.REL_SUB_COMPLETE_GOAL]

        @staticmethod
        def get(context, entity):
            return EntityCredentials.filter(
                context['user'],
                Act.objects.annotate(
                    relations_w_person=FilteredRelation(
                        'relations',
                        condition=Q(relations__object_entity=entity.id),
                    ),
                ).filter(
                    is_deleted=False,
                    relations_w_person__type=commercial_constants.REL_OBJ_COMPLETE_GOAL,
                )
            )
else:
    class CommercialActs4Card:
        dependencies: List[Type[CremeEntity]] = []
        relation_type_deps: List[str] = []

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
    verbose_name = _('Card header block')
    dependencies = [
        Contact, Organisation, Relation,
        *Activities4Card.dependencies,
        *Opportunities4Card.dependencies,
        *CommercialActs4Card.dependencies
    ]
    relation_type_deps = [
        constants.REL_SUB_EMPLOYED_BY,
        constants.REL_SUB_MANAGES,
        *Activities4Card.relation_type_deps,
        *Opportunities4Card.relation_type_deps,
        *CommercialActs4Card.relation_type_deps,
    ]
    template_name = 'persons/bricks/contact-hat-card.html'

    def detailview_display(self, context):
        contact = context['object']
        is_hidden = context['fields_configs'].get_for_model(Contact).is_fieldname_hidden

        return self._render(self.get_template_context(
            context,
            hidden_fields={
                fname
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
    verbose_name = _('Card header block')
    dependencies = [
        Organisation, Contact, Address, Relation,
        *Activities4Card.dependencies,
        *Opportunities4Card.dependencies,
        *CommercialActs4Card.dependencies,
    ]
    relation_type_deps = [
        constants.REL_OBJ_CUSTOMER_SUPPLIER,
        constants.REL_SUB_CUSTOMER_SUPPLIER,
        constants.REL_OBJ_MANAGES,
        constants.REL_OBJ_EMPLOYED_BY,
        *Activities4Card.relation_type_deps,
        *Opportunities4Card.relation_type_deps,
        *CommercialActs4Card.relation_type_deps,
    ]
    template_name = 'persons/bricks/organisation-hat-card.html'

    def detailview_display(self, context):
        organisation = context['object']
        user = context['user']
        managed_orgas = Organisation.objects.filter_managed_by_creme()

        get_fconfigs = context['fields_configs'].get_for_model
        is_hidden = get_fconfigs(Organisation).is_fieldname_hidden

        return self._render(self.get_template_context(
            context,
            hidden_fields={
                fname
                for fname in ('phone', 'billing_address', 'legal_form')
                if is_hidden(fname)
            },
            position_is_hidden=get_fconfigs(Contact).is_fieldname_hidden('position'),

            is_customer=managed_orgas.filter(
                relations__type=constants.REL_OBJ_CUSTOMER_SUPPLIER,
                relations__object_entity=organisation.id,
            ).exists(),
            is_supplier=managed_orgas.filter(
                relations__type=constants.REL_SUB_CUSTOMER_SUPPLIER,
                relations__object_entity=organisation.id,
            ).exists(),

            managers=EntityCredentials.filter(user, organisation.get_managers())[:16],
            employees=EntityCredentials.filter(user, organisation.get_employees())[:16],

            activities=Activities4Card.get(context, organisation),
            opportunities=Opportunities4Card.get(context, organisation),
            acts=CommercialActs4Card.get(context, organisation)
        ))


class ManagersBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('persons', 'managers')
    verbose_name = _('Organisation managers')
    description = _(
        'Displays the list of the managers of an Organisation.\n'
        'The managers of an Organisation are Contacts which are linked to this '
        'Organisation by relationships «manages».\n'
        'App: Accounts and Contacts'
    )
    dependencies = (Relation, Contact)
    relation_type_deps = (constants.REL_OBJ_MANAGES, )
    template_name = 'persons/bricks/managers.html'
    target_ctypes = (Organisation,)

    def _get_people_qs(self, orga):
        return orga.get_managers()

    def _get_add_title(self):
        return _('Create a manager')  # Lazy -> translated only if used

    def detailview_display(self, context):
        orga = context['object']
        is_hidden = context['fields_configs'].get_for_model(Contact).is_fieldname_hidden

        return self._render(self.get_template_context(
            context,
            self._get_people_qs(orga).select_related('civility'),
            rtype_id=self.relation_type_deps[0],
            add_title=self._get_add_title(),
            hidden_fields={
                fname
                for fname in ('phone', 'mobile', 'email')
                if is_hidden(fname)
            },
        ))


class EmployeesBrick(ManagersBrick):
    id_ = QuerysetBrick.generate_id('persons', 'employees')
    verbose_name = _('Organisation employees')
    description = _(
        'Displays the list of the employees of an Organisation.\n'
        'The managers of an Organisation are Contacts which are linked to this '
        'Organisation by relationships «is an employee of».\n'
        'App: Accounts and Contacts'
    )
    relation_type_deps = (constants.REL_OBJ_EMPLOYED_BY, )
    template_name = 'persons/bricks/employees.html'

    def _get_people_qs(self, orga):
        return orga.get_employees()

    def _get_add_title(self):
        return _('Create an employee')  # Lazy -> translated only if used


# TODO: factorise (see CSV import) ? (exclude param in info_field_names())
def _get_address_field_names():
    field_names = [*Address.info_field_names()]

    try:
        field_names.remove('name')
    except ValueError:
        pass

    return field_names


class _AddressesBrick(Brick):
    dependencies = (Address,)
    verbose_name = 'Addresses'
    target_ctypes: Sequence[Type[CremeEntity]] = (Contact, Organisation)

    def get_template_context(self, context, **kwargs):
        person = context['object']
        model = type(person)
        is_hidden = context['fields_configs'].get_for_model(model).is_field_hidden

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

            addr.display_button = display_button
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
            cells=OrderedDict(
                (fname, build_cell(name=fname)) for fname in _get_address_field_names()
            ),
        )

    def detailview_display(self, context):
        return self._render(self.get_template_context(context))


class DetailedAddressesBrick(_AddressesBrick):
    id_ = Brick.generate_id('persons', 'address')  # TODO: rename 'addresses'
    verbose_name = _('Addresses (detailed)')
    description = _(
        'Displays the billing & shipping addresses (if the related fields are '
        'not hidden).\n'
        'In this version of the block, all the visible fields of the addresses '
        'are shown.\n'
        'App: Accounts and Contacts'
    )
    template_name = 'persons/bricks/addresses-detailed.html'


class PrettyAddressesBrick(_AddressesBrick):
    id_ = Brick.generate_id('persons', 'addresses_pretty')
    verbose_name = _('Addresses (pretty)')
    description = _(
        'Displays the billing & shipping addresses (if the related fields are '
        'not hidden).\n'
        'In this version of the block, the addresses are shown in a pretty way '
        '(some fields can be ignored).\n'
        'App: Accounts and Contacts'
    )
    template_name = 'persons/bricks/addresses-pretty.html'


class _OtherAddressesBrick(QuerysetBrick):
    dependencies = (Address,)
    verbose_name = 'Other addresses'
    target_ctypes = (Contact, Organisation)

    def get_template_context(self, context, **kwargs):
        build_cell = partial(EntityCellRegularField.build, model=Address)

        return super().get_template_context(
            context,
            context['object'].other_addresses,
            cells=OrderedDict(
                (fname, build_cell(name=fname))
                for fname in _get_address_field_names()
            ),
        )

    def detailview_display(self, context):
        return self._render(self.get_template_context(context))


class DetailedOtherAddressesBrick(_OtherAddressesBrick):
    # TODO: rename 'other_addresses'
    id_ = QuerysetBrick.generate_id('persons', 'other_address')
    dependencies = (Address,)
    verbose_name = _('Other addresses (detailed)')
    description = _(
        'Displays the additional addresses (ie: not billing & shipping ones).\n'
        'In this version of the block, all the visible fields of the addresses '
        'are shown.\n'
        'App: Accounts and Contacts'
    )
    template_name = 'persons/bricks/other-addresses-detailed.html'
    target_ctypes = (Contact, Organisation)


class PrettyOtherAddressesBrick(_OtherAddressesBrick):
    id_ = QuerysetBrick.generate_id('persons', 'other_addresses_pretty')
    verbose_name = _('Other addresses (pretty)')
    description = _(
        'Displays the additional addresses (ie: not billing & shipping ones).\n'
        'In this version of the block, the addresses are shown in a pretty way '
        '(some fields can be ignored).\n'
        'App: Accounts and Contacts'
    )
    template_name = 'persons/bricks/other-addresses-pretty.html'


class ManagedOrganisationsBrick(PaginatedBrick):
    id_ = Brick.generate_id('persons', 'managed_organisations')
    dependencies = (Organisation,)
    verbose_name = 'Managed organisations'
    template_name = 'persons/bricks/managed-organisations.html'
    configurable = False

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            Organisation.objects.filter_managed_by_creme(),
        ))


# TODO: rename brick_classes + list() ?
bricks_list: Tuple[Type[Brick], ...] = (
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
        id_ = PaginatedBrick.generate_id('persons', 'neglected_orgas')
        verbose_name = _('Neglected organisations')
        description = _(
            'Displays customers/prospects organisations (for the Organisations managed by Creme) '
            'which have no Activity in the future. Expected Activities are related to:\n'
            '- The Organisations with a relationship «is subject of the activity» or '
            '«related to the activity»\n'
            '- The managers & employees with a relationship «participates to the activity» '
            '(plus the above ones)\n'
            'App: Accounts and Contacts'
        )
        dependencies = (Activity,)
        template_name = 'persons/bricks/neglected-organisations.html'

        _RTYPE_IDS_CUSTOMERS = (
            constants.REL_SUB_CUSTOMER_SUPPLIER,
            constants.REL_SUB_PROSPECT,
        )
        _RTYPE_IDS_ORGA_N_ACT = (
            activities_constants.REL_SUB_ACTIVITY_SUBJECT,
            activities_constants.REL_SUB_LINKED_2_ACTIVITY,
        )
        _RTYPE_IDS_EMPLOYEES = (
            constants.REL_SUB_MANAGES,
            constants.REL_SUB_EMPLOYED_BY,
        )
        _RTYPE_IDS_CONTACT_N_ACT = (
            activities_constants.REL_SUB_PART_2_ACTIVITY,
            activities_constants.REL_SUB_ACTIVITY_SUBJECT,
            activities_constants.REL_SUB_LINKED_2_ACTIVITY,
        )

        def _get_neglected(self, now):
            user_contacts = Contact.objects.filter(
                is_user__isnull=False,
            ).values_list('id', flat=True)
            future_activities = [
                *Activity.objects.filter(
                    start__gte=now,
                    relations__type=activities_constants.REL_OBJ_PART_2_ACTIVITY,
                    relations__object_entity__in=user_contacts,
                ).values_list('id', flat=True),
            ]
            neglected_orgas_qs = Organisation.objects.filter(
                is_deleted=False,
                relations__type__in=self._RTYPE_IDS_CUSTOMERS,
                relations__object_entity__in=Organisation.objects.filter_managed_by_creme(),
            ).exclude(relations__type=constants.REL_SUB_INACTIVE).distinct()

            if not future_activities:
                # No need to retrieve it & transform into a list (good idea ??)
                return neglected_orgas_qs

            neglected_orgas = [
                *neglected_orgas_qs.exclude(
                    relations__object_entity__in=future_activities,
                    relations__type__in=self._RTYPE_IDS_ORGA_N_ACT,
                ),
            ]

            if neglected_orgas:
                linked_people_map = dict(
                    Relation.objects.filter(
                        type__in=self._RTYPE_IDS_EMPLOYEES,
                        object_entity__in=[o.id for o in neglected_orgas],
                    ).values_list('subject_entity_id', 'object_entity_id'),
                )
                activity_links = Relation.objects.filter(
                    type__in=self._RTYPE_IDS_CONTACT_N_ACT,
                    subject_entity__in=linked_people_map.keys(),
                    object_entity__in=future_activities,
                )

                # 'True' means 'neglected'
                neglected_map = {orga.id: True for orga in neglected_orgas}
                for rel in activity_links:
                    neglected_map[linked_people_map[rel.subject_entity_id]] = False

                neglected_orgas = [
                    orga
                    for orga in neglected_orgas
                    if neglected_map[orga.id]
                ]

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
