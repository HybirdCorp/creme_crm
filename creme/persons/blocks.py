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

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, Relation
from creme_core.gui.block import Block, PaginatedBlock, QuerysetBlock

from activities.models import Activity
from activities.constants import REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY, REL_OBJ_PART_2_ACTIVITY

from persons.models import Contact, Organisation, Address
from persons.constants import *


class ManagersBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('persons', 'managers')
    dependencies  = (Relation,) #Contact
    relation_type_deps = (REL_OBJ_MANAGES, )
    verbose_name  = _(u"Organisation managers")
    template_name = 'persons/templatetags/block_managers.html'

    def _get_people_qs(self, orga):
        return orga.get_managers()

    def _get_add_title(self):
        return _(u'Create a manager') #lazy -> translated only if used

    def detailview_display(self, context):
        orga = context['object']
        btc = self.get_block_template_context(context,
                                              self._get_people_qs(orga).select_related('civility'),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, orga.pk),
                                              rtype_id=self.relation_type_deps[0],
                                              ct=ContentType.objects.get_for_model(Contact),
                                              add_title=self._get_add_title(),
                                             )

        CremeEntity.populate_credentials(btc['page'].object_list, context['user'])

        return self._render(btc)


class EmployeesBlock(ManagersBlock):
    id_           = QuerysetBlock.generate_id('persons', 'employees')
    relation_type_deps = (REL_OBJ_EMPLOYED_BY, )
    verbose_name  = _(u"Organisation employees")
    template_name = 'persons/templatetags/block_employees.html'

    def _get_people_qs(self, orga):
        return orga.get_employees()

    def _get_add_title(self):
        return _(u'Create an employee') #lazy -> translated only if used


class NeglectedOrganisationsBlock(PaginatedBlock):
    """Customers/propsects organisations that have no Activity in the future."""
    id_           = QuerysetBlock.generate_id('persons', 'neglected_orgas')
    dependencies  = (Activity,)
    verbose_name  = u"Neglected organisations"
    template_name = 'persons/templatetags/block_neglected_orgas.html'
    permission    = 'persons' #NB: used by the view creme_core.views.blocks.reload_basic

    def _get_neglected(self, now):
        user_contacts     = Contact.objects.filter(is_user__isnull=False).values_list('id', flat=True)
        future_activities = list(Activity.objects.filter(start__gte=now,
                                                         relations__type=REL_OBJ_PART_2_ACTIVITY,
                                                         relations__object_entity__in=user_contacts) \
                                                 .values_list('id', flat=True)
                                )
        neglected_orgas_qs = Organisation.objects.filter(relations__type__in=(REL_SUB_CUSTOMER_OF, REL_SUB_PROSPECT),
                                                         relations__object_entity__in=Organisation.get_all_managed_by_creme()) \
                                                 .distinct()

        if not future_activities:
            return neglected_orgas_qs #no need to rerieve it & transform into a list (good idea ??)

        neglected_orgas = list(neglected_orgas_qs.exclude(relations__object_entity__in=future_activities,
                                                          relations__type__in=(REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY)
                                                         )
                              )

        if neglected_orgas:
            linked_people_map = dict(Relation.objects.filter(type__in=(REL_SUB_MANAGES, REL_SUB_EMPLOYED_BY),
                                                             object_entity__in=[o.id for o in neglected_orgas]) \
                                                     .values_list('subject_entity_id', 'object_entity_id')
                                    )
            activity_links = Relation.objects.filter(type__in=(REL_SUB_PART_2_ACTIVITY, REL_SUB_ACTIVITY_SUBJECT, REL_SUB_LINKED_2_ACTIVITY),
                                                     subject_entity__in=linked_people_map.keys(),
                                                     object_entity__in=future_activities,
                                                    )

            neglected_map = dict((orga.id, True) for orga in neglected_orgas) #True means 'neglected'
            for rel in activity_links:
                neglected_map[linked_people_map[rel.subject_entity_id]] = False

            neglected_orgas = [orga for orga in neglected_orgas if neglected_map[orga.id]]

        return neglected_orgas

    def detailview_display(self, context): #indeed it is displayed on portal of 'persons'
        btc = self.get_block_template_context(context,
                                              self._get_neglected(context['today']),
                                              update_url='/creme_core/blocks/reload/basic/%s/' % self.id_,
                                             )

        CremeEntity.populate_credentials(btc['page'].object_list, context['user'])

        return self._render(btc)


class AddressBlock(Block):
    id_           = Block.generate_id('persons', 'address')
    dependencies  = (Address,)
    verbose_name  = _(u'Address')
    template_name = 'persons/templatetags/block_address.html'

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, context['object'].pk),
                                                           ))


class OtherAddressBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('persons', 'other_address')
    dependencies  = (Address,)
    verbose_name  = _(u'Other Address')
    template_name = 'persons/templatetags/block_other_address.html'
    page_size = 1

    def detailview_display(self, context):
        person = context['object']
        l_pk = [address.pk for address in (person.billing_address, person.shipping_address) if address]

        return self._render(self.get_block_template_context(context,
                                                            Address.objects.filter(object_id=person.id).exclude(pk__in=l_pk),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, person.pk),
                                                            ct_id=ContentType.objects.get_for_model(Address).id,
                                                           ))


address_block = AddressBlock()
other_address_block = OtherAddressBlock()
managers_block  = ManagersBlock()
employees_block = EmployeesBlock()
neglected_orgas_block = NeglectedOrganisationsBlock()
