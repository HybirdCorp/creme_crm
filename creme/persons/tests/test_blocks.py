# -*- coding: utf-8 -*-

try:
    from datetime import timedelta
    from functools import partial

    from django.core.urlresolvers import reverse
    from django.test.html import parse_html, Element
    from django.utils.encoding import smart_unicode
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import RelationType, Relation, CremeProperty, FieldsConfig
    # from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME
    from creme.creme_core.tests.base import CremeTestCase

    from creme.activities.constants import (REL_SUB_ACTIVITY_SUBJECT,
            REL_SUB_PART_2_ACTIVITY, REL_SUB_LINKED_2_ACTIVITY,
            ACTIVITYTYPE_MEETING, ACTIVITYTYPE_PHONECALL)
    from creme.activities.models import Activity
    from creme.activities.tests.base import skipIfCustomActivity

    from ..blocks import NeglectedOrganisationsBlock, address_block
    from ..constants import (REL_SUB_CUSTOMER_SUPPLIER, REL_SUB_PROSPECT,
            REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES,REL_SUB_INACTIVE)

    from .base import (skipIfCustomOrganisation, skipIfCustomContact,
            Contact, Organisation, Address)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


def find_node_by_attr(node, tag, name, value):
    if not isinstance(node, Element):
        return

    if node.name == tag:
        for attr_name, attr_value in node.attributes:
            if attr_name == name and attr_value == value:
                return node

    for child in node.children:
        node = find_node_by_attr(child, tag, name, value)

        if node is not None:
            return node


@skipIfCustomOrganisation
class BlocksTestCase(CremeTestCase):
    # @classmethod
    # def setUpClass(cls):
    #     CremeTestCase.setUpClass()
    #     cls.populate('creme_core', 'persons', 'activities')

    def setUp(self):
        self.login()

    def _build_customer_orga(self, mng_orga, name, **kwargs):
        customer = Organisation.objects.create(user=self.user, name=name, **kwargs)
        Relation.objects.create(user=self.user, subject_entity=customer,
                                object_entity=mng_orga,
                                type_id=REL_SUB_CUSTOMER_SUPPLIER,
                               )

        return customer

    def _get_neglected_orgas(self):
        neglected_orgas_block = NeglectedOrganisationsBlock()
        return neglected_orgas_block._get_neglected(now())

    def test_neglected_block01(self):
        NeglectedOrganisationsBlock()

        orgas = Organisation.objects.all()
        self.assertEqual(1, len(orgas))

        mng_orga = orgas[0]
        # self.assertTrue(CremeProperty.objects.filter(type=PROP_IS_MANAGED_BY_CREME, creme_entity=mng_orga).exists())
        self.assertTrue(mng_orga.is_managed)
        self.assertFalse(self._get_neglected_orgas())

        customer01 = Organisation.objects.create(user=self.user, name='orga02')
        self.assertFalse(self._get_neglected_orgas())

        rtype_customer = RelationType.objects.get(pk=REL_SUB_CUSTOMER_SUPPLIER)
        create_rel = partial(Relation.objects.create, user=self.user)
        create_rel(subject_entity=customer01, object_entity=mng_orga, type=rtype_customer)
        self.assertEqual([customer01.id], [orga.id for orga in self._get_neglected_orgas()])

        customer02 = Organisation.objects.create(user=self.user, name='orga03')
        create_rel(subject_entity=customer02, object_entity=mng_orga,
                   type=RelationType.objects.get(pk=REL_SUB_PROSPECT),
                  )
        neglected_orgas = self._get_neglected_orgas()
        self.assertEqual(2, len(neglected_orgas))
        self.assertEqual({customer01.id, customer02.id}, {orga.id for orga in neglected_orgas})

        create_rel(subject_entity=customer02, object_entity=mng_orga, type=rtype_customer)
        self.assertEqual(2, len(self._get_neglected_orgas()))

    @skipIfCustomActivity
    def test_neglected_block02(self):
        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = user.linked_contact

        customer01 = self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')
        self.assertEqual(2, len(self._get_neglected_orgas()))

        tomorrow = now() + timedelta(days=1)  # So in the future
        meeting  = Activity.objects.create(user=user, type_id=ACTIVITYTYPE_MEETING,
                                           title='meet01', start=tomorrow,
                                           end=tomorrow + timedelta(hours=2),
                                          )

        get_rtype = RelationType.objects.get
        create_rel = partial(Relation.objects.create, user=user, object_entity=meeting)
        create_rel(subject_entity=customer02, type=get_rtype(pk=REL_SUB_ACTIVITY_SUBJECT))
        self.assertEqual(2, len(self._get_neglected_orgas()))

        create_rel(subject_entity=user_contact, type=get_rtype(pk=REL_SUB_PART_2_ACTIVITY))
        self.assertEqual([customer01.id], [orga.id for orga in self._get_neglected_orgas()])

    @skipIfCustomActivity
    def test_neglected_block03(self):
        "Past activity => orga is still neglected"
        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = user.linked_contact

        self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')

        yesterday = now() - timedelta(days=1)  # So in the past
        meeting  = Activity.objects.create(user=user, type_id=ACTIVITYTYPE_MEETING,
                                           title='meet01', start=yesterday,
                                           end=yesterday + timedelta(hours=2),
                                          )

        create_rel = partial(Relation.objects.create, user=user, object_entity=meeting)
        create_rel(subject_entity=customer02,   type_id=REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=user_contact, type_id=REL_SUB_PART_2_ACTIVITY)
        self.assertEqual(2, len(self._get_neglected_orgas()))  # And not 1

    @skipIfCustomContact
    @skipIfCustomActivity
    def test_neglected_block04(self):
        "A people linked to customer is linked to a future activity"
        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = user.linked_contact

        customer = self._build_customer_orga(mng_orga, 'Suna')

        tomorrow = now() + timedelta(days=1)  # So in the future
        meeting = Activity.objects.create(user=user, type_id=ACTIVITYTYPE_MEETING,
                                          title='meet01', start=tomorrow,
                                          end=tomorrow + timedelta(hours=2),
                                         )
        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=user_contact, object_entity=meeting,
                   type_id=REL_SUB_PART_2_ACTIVITY,
                  )

        employee = Contact.objects.create(user=user, first_name='Kankuro', last_name='???')

        get_rtype = RelationType.objects.get
        create_rel(subject_entity=employee, object_entity=customer,
                   type=get_rtype(pk=REL_SUB_EMPLOYED_BY),
                  )
        self.assertEqual(1, len(self._get_neglected_orgas()))

        create_rel(subject_entity=employee, object_entity=meeting,
                   type=get_rtype(pk=REL_SUB_LINKED_2_ACTIVITY),
                  )
        self.assertFalse(self._get_neglected_orgas())

    @skipIfCustomContact
    @skipIfCustomActivity
    def test_neglected_block05(self):
        "2 people linked to customer are linked to a future activity"
        user = self.user
        mng_orga = Organisation.objects.all()[0]

        create_contact = partial(Contact.objects.create, user=user)
        user_contact = user.linked_contact

        customer = self._build_customer_orga(mng_orga, 'Suna')

        tomorrow = now() + timedelta(days=1)  # So in the future
        create_activity = partial(Activity.objects.create, user=user, start=tomorrow)
        meeting   = create_activity(title='meet01', type_id=ACTIVITYTYPE_MEETING,
                                    end=tomorrow + timedelta(hours=2)
                                   )
        phonecall = create_activity(title='call01', type_id=ACTIVITYTYPE_PHONECALL,
                                    end=tomorrow + timedelta(minutes=15),
                                   )

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=user_contact, object_entity=phonecall, type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=user_contact, object_entity=meeting,   type_id=REL_SUB_PART_2_ACTIVITY)

        manager  = create_contact(first_name='Gaara', last_name='???')
        employee = create_contact(first_name='Temari', last_name='???')
        create_rel(subject_entity=manager,  object_entity=customer, type_id=REL_SUB_MANAGES)
        create_rel(subject_entity=employee, object_entity=customer, type_id=REL_SUB_EMPLOYED_BY)
        self.assertEqual(1, len(self._get_neglected_orgas()))

        create_rel(subject_entity=manager, object_entity=phonecall, type_id=REL_SUB_PART_2_ACTIVITY)
        self.assertFalse(self._get_neglected_orgas())

        create_rel(subject_entity=employee, object_entity=meeting, type_id=REL_SUB_ACTIVITY_SUBJECT)
        self.assertFalse(self._get_neglected_orgas())

    @skipIfCustomContact
    @skipIfCustomActivity
    def test_neglected_block06(self):
        "Future activity, but not with managed organisation !"
        user = self.user
        mng_orga   = Organisation.objects.all()[0]
        customer   = self._build_customer_orga(mng_orga, 'Suna')
        competitor = Organisation.objects.create(user=user, name='Akatsuki')

        tomorrow = now() + timedelta(days=1)  # So in the future
        meeting  = Activity.objects.create(user=user, type_id=ACTIVITYTYPE_MEETING, 
                                           title='meet01', start=tomorrow,
                                           end=tomorrow + timedelta(hours=2),
                                          )

        manager = Contact.objects.create(user=user,  first_name='Gaara', last_name='???')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=manager,  object_entity=customer, type_id=REL_SUB_MANAGES)

        create_rel(subject_entity=manager,    object_entity=meeting, type_id=REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=competitor, object_entity=meeting, type_id=REL_SUB_ACTIVITY_SUBJECT)
        self.assertEqual(1, len(self._get_neglected_orgas()))

    def test_neglected_block07(self):
        "Inactive customers are not counted"
        mng_orga   = Organisation.objects.all()[0]
        customer01 = self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')
        Relation.objects.create(user=self.user, subject_entity=customer02,
                                object_entity=mng_orga, type_id=REL_SUB_INACTIVE
                               )
        self.assertEqual([customer01], list(self._get_neglected_orgas()))

    def test_neglected_block08(self):
        "Deleted customers are not counted"
        mng_orga = Organisation.objects.all()[0]
        customer = self._build_customer_orga(mng_orga, 'Konoha')
        self._build_customer_orga(mng_orga, 'Suna', is_deleted=True)
        self.assertEqual([customer], list(self._get_neglected_orgas()))

    def _get_address_block_content(self, entity, no_titles=False):
        response = self.assertGET200(entity.get_absolute_url())

        try:
            content = smart_unicode(response.content)
        except Exception as e:
            self.fail(e)

        try:
            html = parse_html(content)
        except Exception as e:
            self.fail(u'%s\n----\n%s' % (e, content))

        block_node = find_node_by_attr(html, 'table', 'id', address_block.id_)
        self.assertIsNotNone(block_node, 'Block content not found')

        header_node = find_node_by_attr(block_node, 'th', 'class', 'collapser')
        self.assertIsNotNone(header_node, 'Block header not found')

        buttons_node = find_node_by_attr(block_node, 'div', 'class', 'buttons')
        self.assertIsNotNone(buttons_node, 'Block buttons not found')

        body_node = find_node_by_attr(block_node, 'tbody', 'class', 'collapsable')
        self.assertIsNotNone(body_node, 'Block body not found')

        titles_node = find_node_by_attr(block_node, 'tr', 'class', 'header')
        if no_titles:
            self.assertIsNone(titles_node, 'Block titles found !')
        else:
            self.assertIsNotNone(titles_node, 'Block titles not found')

        return {
            'header':  header_node,
            'buttons': unicode(buttons_node),
            'body':    unicode(body_node),
            'titles':  unicode(titles_node),
        }

    def _assertAddressIn(self, block_content, address, title, country_in=True):
        self.assertIn(title, block_content['titles'])

        block_body = block_content['body']
        self.assertIn(address.address, block_body)
        self.assertIn(address.city,    block_body)

        if country_in:
            self.assertIn(address.country, block_body)
        else:
            self.assertNotIn(address.country, block_body)

    def _assertAddressNotIn(self, block_body, address):
        self.assertNotIn(address.address, block_body)
        self.assertNotIn(address.city,    block_body)

    def _assertButtonIn(self, block_content, url_name, entity):
        self.assertIn(reverse(url_name, args=(entity.id,)), block_content['buttons'])

    def _assertButtonNotIn(self, block_content, url_name, entity):
        self.assertNotIn(reverse(url_name, args=(entity.id,)), block_content['buttons'])

    def _assertColspanEqual(self, block_content, colspan):
        for attr_name, attr_value in block_content['header'].attributes:
            if attr_name == 'colspan':
                found_colspan = int(attr_value)
                break
        else:
            self.fail('"colspan" attribute not found.')

        self.assertEqual(colspan, found_colspan)

    def _create_contact_n_addresses(self, billing_address=True, shipping_address=True):
        c = Contact.objects.create(user=self.user, first_name='Lawrence', last_name='?')

        create_address = partial(Address.objects.create, owner=c)

        if billing_address:
            c.billing_address = create_address(name='Billing address',
                                               address='Main square',
                                               city='Lenos', country='North',
                                              )

        if shipping_address:
            c.shipping_address = create_address(name='Shipping address',
                                                address='Market',
                                                city='Yorentz', country='South',
                                               )

        c.save()

        return c

    def test_addresses_block01(self):
        c = self._create_contact_n_addresses()
        content = self._get_address_block_content(c)

        self._assertAddressIn(content, c.billing_address,  _('Billing address'))
        self._assertAddressIn(content, c.shipping_address, _('Shipping address'))

        self._assertButtonNotIn(content, 'persons__create_billing_address', c)
        self._assertButtonNotIn(content, 'persons__create_shipping_address', c)

        self._assertColspanEqual(content, 6)

    def test_addresses_block02(self):
        "No shipping address set"
        c = self._create_contact_n_addresses(shipping_address=False)
        content = self._get_address_block_content(c)

        self._assertAddressIn(content, c.billing_address, _('Billing address'))
        self.assertNotIn(_('Shipping address'), content['titles'])

        self._assertButtonNotIn(content, 'persons__create_billing_address', c)
        self._assertButtonIn(content, 'persons__create_shipping_address', c)

        self._assertColspanEqual(content, 3)

    def test_addresses_block03(self):
        "No billing address set"
        c = self._create_contact_n_addresses(billing_address=False)
        content = self._get_address_block_content(c)

        self._assertAddressIn(content, c.shipping_address, _('Shipping address'))
        self.assertNotIn(_('Billing address'), content['titles'])

        self._assertButtonNotIn(content, 'persons__create_shipping_address', c)
        self._assertButtonIn(content, 'persons__create_billing_address', c)

        self._assertColspanEqual(content, 3)

    def test_addresses_block04(self):
        "No address set"
        c = self._create_contact_n_addresses(billing_address=False, shipping_address=False)
        content = self._get_address_block_content(c, no_titles=True)
        self._assertColspanEqual(content, 1)

    def test_addresses_block05(self):
        "With field config on sub-field"
        FieldsConfig.create(Address,
                            descriptions=[('country', {FieldsConfig.HIDDEN: True})],
                           )

        c = self._create_contact_n_addresses()
        content = self._get_address_block_content(c)
        self._assertAddressIn(content, c.billing_address,  _('Billing address'),  country_in=False)
        self._assertAddressIn(content, c.shipping_address, _('Shipping address'), country_in=False)

    def test_addresses_block06(self):
        "With field config on 'billing_address' FK field"
        FieldsConfig.create(Contact,
                            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
                           )

        c = self._create_contact_n_addresses()
        content = self._get_address_block_content(c)
        self._assertAddressIn(content, c.shipping_address, _('Shipping address'))
        self._assertAddressNotIn(content, c.billing_address)

        self._assertButtonNotIn(content, 'persons__create_billing_address', c)
        self._assertButtonNotIn(content, 'persons__create_shipping_address', c)

    def test_addresses_block07(self):
        "With field config on 'shipping_address' FK field"
        FieldsConfig.create(Contact,
                            descriptions=[('shipping_address', {FieldsConfig.HIDDEN: True})],
                           )

        c = self._create_contact_n_addresses()
        content = self._get_address_block_content(c)
        self._assertAddressIn(content, c.billing_address, _('Billing address'))
        self._assertAddressNotIn(content, c.shipping_address)
