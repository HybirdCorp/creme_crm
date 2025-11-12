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

from collections import OrderedDict
from collections.abc import Sequence
from functools import partial

from django.apps import apps
from django.conf import settings
from django.db.models.query_utils import FilteredRelation, Q
from django.utils.functional import cached_property, lazy
from django.utils.translation import gettext
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
from creme.creme_core.models import CremeEntity, Relation, RelationType
from creme.creme_core.utils.db import populate_related
from creme.creme_core.utils.paginators import OnePagePaginator

from . import constants

Address = persons.get_address_model()
Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


# TODO: move to creme core?
class CardSummary:
    dependencies: list[type[CremeEntity]] = []
    relation_type_deps: list[str] = []
    template_name = ''

    def get_context(self, *, entity: CremeEntity, brick_context: dict) -> dict:
        """Context used by the template system to render the summary."""
        template_name = self.template_name
        return {'template_name': template_name} if template_name else {}


if apps.is_installed('creme.activities'):
    from datetime import timedelta

    import creme.activities.constants as activities_constants
    from creme.activities import get_activity_model

    Activity = get_activity_model()

    class _ActivitySummary(CardSummary):
        dependencies = [Activity]
        # TODO: what if one RelationType.enable == False?
        relation_type_deps = [
            activities_constants.REL_SUB_PART_2_ACTIVITY,
            activities_constants.REL_SUB_ACTIVITY_SUBJECT,
            activities_constants.REL_SUB_LINKED_2_ACTIVITY,
        ]

    class LastActivityIntroSummary(_ActivitySummary):
        template_name = 'persons/bricks/frags/card-last-activity.html'

        def get_context(self, *, entity, brick_context):
            context = super().get_context(entity=entity, brick_context=brick_context)
            past = (
                Activity.objects.past_linked_to_organisation
                if isinstance(entity, Organisation) else
                Activity.objects.past_linked
            )
            context['activity'] = EntityCredentials.filter(
                user=brick_context['user'],
                queryset=past(entity, brick_context['today']),
            ).first()

            return context

    class NextActivitySummary(_ActivitySummary):
        template_name = 'persons/bricks/frags/card-summary-next-activity.html'

        def get_context(self, *, entity, brick_context):
            context = super().get_context(entity=entity, brick_context=brick_context)
            future = (
                Activity.objects.future_linked_to_organisation
                if isinstance(entity, Organisation) else
                Activity.objects.future_linked
            )
            context['activity'] = EntityCredentials.filter(
                user=brick_context['user'],
                queryset=future(entity, brick_context['today']),
            ).first()

            return context

    class NeglectedContactIndicator:
        delta = timedelta(days=15)
        label_not = _('Not contacted since 15 days')
        label_never = _('Never contacted')

        def __init__(self, context, contact):
            self.context = context
            self.contact = contact

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

    class LastActivityIntroSummary(CardSummary):
        pass

    class NextActivitySummary(CardSummary):
        pass

if apps.is_installed('creme.opportunities'):
    import creme.opportunities.constants as opp_constants
    from creme.opportunities import get_opportunity_model

    Opportunity = get_opportunity_model()

    class OpportunitiesSummary(CardSummary):
        dependencies = [Opportunity]
        relation_type_deps = [opp_constants.REL_OBJ_TARGETS]
        template_name = 'persons/bricks/frags/card-summary-opportunities.html'

        displayed_opportunities_number = 5

        def get_context(self, *, entity, brick_context):
            context = super().get_context(entity=entity, brick_context=brick_context)
            rtype_id = opp_constants.REL_SUB_TARGETS
            context['REL_SUB_TARGETS'] = rtype_id
            context['opportunities'] = OnePagePaginator(
                EntityCredentials.filter(
                    user=brick_context['user'],
                    queryset=Opportunity.objects.annotate(
                        relations_w_person=FilteredRelation(
                            'relations',
                            condition=Q(relations__object_entity=entity.id),
                        ),
                    ).filter(is_deleted=False, relations_w_person__type=rtype_id),
                ),
                per_page=self.displayed_opportunities_number,
            ).page(1)

            return context
else:
    class OpportunitiesSummary(CardSummary):
        pass

if apps.is_installed('creme.commercial'):
    import creme.commercial.constants as commercial_constants
    from creme.commercial import get_act_model

    Act = get_act_model()

    class CommercialActsSummary(CardSummary):
        dependencies = [Act]
        # TODO: what if RelationType.enable == False?
        relation_type_deps = [commercial_constants.REL_SUB_COMPLETE_GOAL]
        # TODO: factorise templates (base-summary...)?
        template_name = 'persons/bricks/frags/card-summary-acts.html'

        displayed_acts_number = 5

        def get_context(self, *, entity, brick_context):
            context = super().get_context(entity=entity, brick_context=brick_context)
            rtype_id = commercial_constants.REL_OBJ_COMPLETE_GOAL
            context['REL_OBJ_COMPLETE_GOAL'] = rtype_id
            context['acts'] = OnePagePaginator(
                EntityCredentials.filter(
                    user=brick_context['user'],
                    queryset=Act.objects.annotate(
                        relations_w_person=FilteredRelation(
                            'relations',
                            condition=Q(relations__object_entity=entity.id),
                        ),
                    ).filter(
                        is_deleted=False,
                        relations_w_person__type=rtype_id,
                    ),
                ),
                per_page=self.displayed_acts_number,
            ).page(1)

            return context
else:
    class CommercialActsSummary(CardSummary):
        pass


class ContactBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'persons/bricks/contact-hat-bar.html'


class OrganisationBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'persons/bricks/organisation-hat-bar.html'


# TODO: move to core ?
# class _PersonsCardHatBrick(Brick):
class _PersonsCardHatBrick(SimpleBrick):
    intro_summary = LastActivityIntroSummary  # TODO: accept several summaries?
    summaries = [
        CommercialActsSummary,
        OpportunitiesSummary,
        NextActivitySummary,
    ]

    def __init__(self):
        super().__init__()
        # NB: we use sets to avoid duplicates
        all_summaries = [*self.summaries, self.intro_summary]
        self.dependencies = [*{
            *self.dependencies,
            *(model for summary in all_summaries for model in summary.dependencies),
        }]
        self.relation_type_deps = [*{
            *self.relation_type_deps,
            *(rtype_id for summary in all_summaries for rtype_id in summary.relation_type_deps),
        }]

    def get_template_context(self, context, **extra_kwargs):
        entity = context['object']

        return super().get_template_context(
            context,
            intro_summary=self.intro_summary().get_context(
                entity=entity, brick_context=context,
            ),
            summaries=[
                summary_cls().get_context(entity=entity, brick_context=context)
                for summary_cls in self.summaries
            ],
            **extra_kwargs
        )


class ContactCardHatBrick(_PersonsCardHatBrick):
    id = _PersonsCardHatBrick._generate_hat_id('persons', 'contact_card')
    verbose_name = _('Card header block')
    dependencies = [
        Contact, Organisation, Relation,
    ]
    relation_type_deps = [
        constants.REL_SUB_EMPLOYED_BY,
        constants.REL_SUB_MANAGES,
    ]
    template_name = 'persons/bricks/contact-hat-card.html'

    max_related_organisations = 8

    def get_template_context(self, context, **extra_kwargs):
        contact = context['object']
        user = context['user']
        managed_orgas = Organisation.objects.filter_managed_by_creme()
        max_organisations = self.max_related_organisations

        def retrieve_organisations_n_count(rtype_id):
            qs = EntityCredentials.filter(
                user,
                Organisation.objects.filter(
                    is_deleted=False,
                    relations__object_entity=contact,
                    relations__type=rtype_id,
                ),
            )
            organisations = qs[:max_organisations]
            count = len(organisations)
            if count == max_organisations:
                count = qs.count()

            return organisations, count

        managed, managed_count = retrieve_organisations_n_count(constants.REL_OBJ_MANAGES)
        employers, employers_count = retrieve_organisations_n_count(constants.REL_OBJ_EMPLOYED_BY)

        return super().get_template_context(
            context,

            max_organisations=max_organisations,
            managed=managed,
            managed_count=managed_count,
            REL_OBJ_MANAGES=constants.REL_OBJ_MANAGES,
            employers=employers,
            employers_count=employers_count,
            REL_OBJ_EMPLOYED_BY=constants.REL_OBJ_EMPLOYED_BY,

            # TODO: factorise (see OrganisationCardHatBrick)
            is_customer=managed_orgas.filter(
                relations__type=constants.REL_OBJ_CUSTOMER_SUPPLIER,
                relations__object_entity=contact.id,
            ).exists(),
            is_supplier=managed_orgas.filter(
                relations__type=constants.REL_SUB_CUSTOMER_SUPPLIER,
                relations__object_entity=contact.id,
            ).exists(),

            neglected_indicator=NeglectedContactIndicator(context, contact),

            **extra_kwargs
        )


class OrganisationCardHatBrick(_PersonsCardHatBrick):
    id = _PersonsCardHatBrick._generate_hat_id('persons', 'organisation_card')
    verbose_name = _('Card header block')
    dependencies = [
        Organisation, Contact, Address, Relation,
    ]
    # TODO: what if RelationType.enable == False?
    relation_type_deps = [
        constants.REL_OBJ_CUSTOMER_SUPPLIER,
        constants.REL_SUB_CUSTOMER_SUPPLIER,
        constants.REL_OBJ_MANAGES,
        constants.REL_OBJ_EMPLOYED_BY,
    ]
    template_name = 'persons/bricks/organisation-hat-card.html'

    max_related_contacts = 15

    def get_template_context(self, context, **extra_kwargs):
        organisation = context['object']
        user = context['user']
        managed_orgas = Organisation.objects.filter_managed_by_creme()
        max_contacts = self.max_related_contacts

        def retrieve_contacts_n_count(qs):
            qs = EntityCredentials.filter(user, qs)
            contacts = qs[:max_contacts]
            count = len(contacts)
            if count == max_contacts:
                count = qs.count()

            return contacts, count

        managers, managers_count = retrieve_contacts_n_count(organisation.get_managers())
        employees, employees_count = retrieve_contacts_n_count(organisation.get_employees())

        return super().get_template_context(
            context,
            position_is_hidden=context['fields_configs'].get_for_model(
                Contact
            ).is_fieldname_hidden('position'),

            is_customer=managed_orgas.filter(
                relations__type=constants.REL_OBJ_CUSTOMER_SUPPLIER,
                relations__object_entity=organisation.id,
            ).exists(),
            is_supplier=managed_orgas.filter(
                relations__type=constants.REL_SUB_CUSTOMER_SUPPLIER,
                relations__object_entity=organisation.id,
            ).exists(),

            max_contacts=max_contacts,
            managers=managers,
            managers_count=managers_count,
            REL_SUB_MANAGES=constants.REL_SUB_MANAGES,
            employees=employees,
            employees_count=employees_count,
            REL_SUB_EMPLOYED_BY=constants.REL_SUB_EMPLOYED_BY,

            **extra_kwargs
        )


class _LinkedPeopleBrick(QuerysetBrick):
    # id = ...
    # verbose_name = ...
    # description =  ...
    dependencies = (Relation, Contact)
    # relation_type_deps = ...
    template_name = 'persons/bricks/base/linked-people.html'
    target_ctypes = (Organisation,)
    permissions = 'persons'

    creation_label = 'Create a related contact'
    cells_desc = [
        (EntityCellRegularField, 'phone'),
        (EntityCellRegularField, 'mobile'),
        (EntityCellRegularField, 'email'),
    ]

    def _get_people_qs(self, orga):
        raise NotImplementedError

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            # TODO: better system to know which field(s) to select_related()
            #       when we represent an entity.
            self._get_people_qs(context['object']).select_related('civility'),
            relation_type=RelationType.objects.get(id=self.relation_type_deps[0]),
            add_title=self.creation_label,
            cells=[
                cell
                for cell_class, cell_name in self.cells_desc
                if (
                    cell := cell_class.build(Contact, cell_name)
                ) is not None and not cell.is_excluded
            ],
        ))


class ManagersBrick(_LinkedPeopleBrick):
    id = _LinkedPeopleBrick.generate_id('persons', 'managers')
    verbose_name = _('Organisation managers')
    description = _(
        'Displays the list of the managers of an Organisation.\n'
        'The managers of an Organisation are Contacts which are linked to this '
        'Organisation by relationships «manages».\n'
        'App: Accounts and Contacts'
    )
    # dependencies = (Relation, Contact)
    relation_type_deps = (constants.REL_OBJ_MANAGES, )
    template_name = 'persons/bricks/managers.html'
    # target_ctypes = (Organisation,)

    creation_label = _('Create a manager')

    def _get_people_qs(self, orga):
        return orga.get_managers()


class EmployeesBrick(_LinkedPeopleBrick):
    id = _LinkedPeopleBrick.generate_id('persons', 'employees')
    verbose_name = _('Organisation employees')
    description = _(
        'Displays the list of the employees of an Organisation.\n'
        'The managers of an Organisation are Contacts which are linked to this '
        'Organisation by relationships «is an employee of».\n'
        'App: Accounts and Contacts'
    )
    relation_type_deps = (constants.REL_OBJ_EMPLOYED_BY, )
    template_name = 'persons/bricks/employees.html'

    creation_label = _('Create an employee')

    def _get_people_qs(self, orga):
        return orga.get_employees()


# TODO: factorise (see CSV import) ? (exclude param in info_field_names())
def _get_address_field_names():
    field_names = [*Address.info_field_names()]

    try:
        field_names.remove('name')
    except ValueError:
        pass

    return field_names


class _AddressesBrick(SimpleBrick):
    dependencies = (Address,)
    verbose_name = 'Addresses'
    target_ctypes: Sequence[type[CremeEntity]] = (Contact, Organisation)
    permissions = 'persons'

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


class DetailedAddressesBrick(_AddressesBrick):
    # TODO: rename 'addresses'
    id = _AddressesBrick.generate_id('persons', 'address')
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
    id = _AddressesBrick.generate_id('persons', 'addresses_pretty')
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
    permissions = 'persons'

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
    id = _OtherAddressesBrick.generate_id('persons', 'other_address')
    dependencies = (Address,)
    verbose_name = _('Other addresses (detailed)')
    description = _(
        'Displays the additional addresses (i.e. not billing & shipping ones).\n'
        'In this version of the block, all the visible fields of the addresses '
        'are shown.\n'
        'App: Accounts and Contacts'
    )
    template_name = 'persons/bricks/other-addresses-detailed.html'
    # target_ctypes = (Contact, Organisation)


class PrettyOtherAddressesBrick(_OtherAddressesBrick):
    id = _OtherAddressesBrick.generate_id('persons', 'other_addresses_pretty')
    verbose_name = _('Other addresses (pretty)')
    description = _(
        'Displays the additional addresses (i.e. not billing & shipping ones).\n'
        'In this version of the block, the addresses are shown in a pretty way '
        '(some fields can be ignored).\n'
        'App: Accounts and Contacts'
    )
    template_name = 'persons/bricks/other-addresses-pretty.html'


class ManagedOrganisationsBrick(PaginatedBrick):
    id = PaginatedBrick.generate_id('persons', 'managed_organisations')
    dependencies = (Organisation,)
    verbose_name = 'Managed organisations'
    template_name = 'persons/bricks/managed-organisations.html'
    configurable = False

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            Organisation.objects.filter_managed_by_creme(),
        ))


brick_classes: list[type[Brick]] = [
    DetailedAddressesBrick,
    PrettyAddressesBrick,
    DetailedOtherAddressesBrick,
    PrettyOtherAddressesBrick,
    ManagersBrick,
    EmployeesBrick,
]

if apps.is_installed('creme.activities'):
    class NeglectedOrganisationsBrick(PaginatedBrick):
        id = PaginatedBrick.generate_id('persons', 'neglected_orgas')
        verbose_name = _('Neglected organisations')
        description = lazy(
            lambda: gettext(
                'Displays customers/prospects organisations (for the Organisations '
                'managed by {software}) which have no Activity in the future. '
                'Expected Activities are related to:\n'
                '- The Organisations with a relationship «is subject of the activity» or '
                '«related to the activity»\n'
                '- The managers & employees with a relationship «participates in the activity» '
                '(plus the above ones)\n'
                'App: Accounts and Contacts'
            ).format(software=settings.SOFTWARE_LABEL),
            str
        )()
        dependencies = (Activity,)
        permissions = ['persons', 'activities']
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

    brick_classes.append(NeglectedOrganisationsBrick)
