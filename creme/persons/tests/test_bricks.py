# -*- coding: utf-8 -*-

try:
    from datetime import timedelta
    from functools import partial
    from unittest import skipIf

    from django.apps import apps
    from django.core.urlresolvers import reverse
    # from django.test.html import parse_html, Element
    # from django.utils.encoding import smart_unicode
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import RelationType, Relation, FieldsConfig  # CremeProperty
    # from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.views.base import BrickTestCaseMixin

    if apps.is_installed('creme.activities'):
        from creme.activities import constants as act_constants
        from creme.activities.models import Activity
        from creme.activities.tests.base import skipIfCustomActivity

        def skipIfActivitiesisNotInstalled(test_func):
            return skipIf(False, 'The app "activities" is not installed')(test_func)
    else:
        def skipIfActivitiesisNotInstalled(test_func):
            return skipIf(True, 'The app "activities" is not installed')(test_func)

        def skipIfCustomActivity(test_func):
            return skipIf(True, 'The app "activities" is not installed')(test_func)

    from .. import bricks, constants

    from .base import (skipIfCustomOrganisation, skipIfCustomContact,
            Contact, Organisation, Address)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


# def find_node_by_attr(node, tag, name, value):
#     if not isinstance(node, Element):
#         return
#
#     if node.name == tag:
#         for attr_name, attr_value in node.attributes:
#             if attr_name == name and attr_value == value:
#                 return node
#
#     for child in node.children:
#         node = find_node_by_attr(child, tag, name, value)
#
#         if node is not None:
#             return node


@skipIfCustomOrganisation
# class BlocksTestCase(CremeTestCase):
class BricksTestCase(CremeTestCase, BrickTestCaseMixin):
    # @classmethod
    # def setUpClass(cls):
    #     CremeTestCase.setUpClass()
    #     cls.populate('creme_core', 'persons', 'activities')

    def setUp(self):
        self.login()

    # def _get_address_block_content(self, entity, no_titles=False):
    #     response = self.assertGET200(entity.get_absolute_url())
    #
    #     try:
    #         content = smart_unicode(response.content)
    #     except Exception as e:
    #         self.fail(e)
    #
    #     try:
    #         html = parse_html(content)
    #     except Exception as e:
    #         self.fail(u'%s\n----\n%s' % (e, content))
    #
    #     block_node = find_node_by_attr(html, 'table', 'id', bricks.DetailedAddressesBrick.id_)
    #     self.assertIsNotNone(block_node, 'Block content not found')
    #
    #     header_node = find_node_by_attr(block_node, 'th', 'class', 'collapser')
    #     self.assertIsNotNone(header_node, 'Block header not found')
    #
    #     buttons_node = find_node_by_attr(block_node, 'div', 'class', 'buttons')
    #     self.assertIsNotNone(buttons_node, 'Block buttons not found')
    #
    #     body_node = find_node_by_attr(block_node, 'tbody', 'class', 'collapsable')
    #     self.assertIsNotNone(body_node, 'Block body not found')
    #
    #     titles_node = find_node_by_attr(block_node, 'tr', 'class', 'header')
    #     if no_titles:
    #         self.assertIsNone(titles_node, 'Block titles found !')
    #     else:
    #         self.assertIsNotNone(titles_node, 'Block titles not found')
    #
    #     return {
    #         'header':  header_node,
    #         'buttons': unicode(buttons_node),
    #         'body':    unicode(body_node),
    #         'titles':  unicode(titles_node),
    #     }
    def _get_address_brick_node(self, entity):
        response = self.assertGET200(entity.get_absolute_url())
        return self.get_brick_node(self.get_html_tree(response.content), bricks.PrettyAddressesBrick.id_)

    # def _assertAddressIn(self, block_content, address, title, country_in=True):
    #     self.assertIn(title, block_content['titles'])
    #
    #     block_body = block_content['body']
    #     self.assertIn(address.address, block_body)
    #     self.assertIn(address.city,    block_body)
    #
    #     if country_in:
    #         self.assertIn(address.country, block_body)
    #     else:
    #         self.assertNotIn(address.country, block_body)
    def _assertAddressIn(self, brick_node, address, title, country_in=True):
        self.assertIn(title, self.get_address_titles(brick_node))

        pretty_addr_node = brick_node.findall(".//div[@class='address']")
        self.assertIsNotNone(pretty_addr_node)
        pretty_addr = {elt.text.strip() for elt in brick_node.findall(".//div[@class='address']")}
        self.assertIn(address.address, pretty_addr)
        # self.assertIn(address.city,    pretty_addr) # NB: not in 'text', because of <br/> (eg: Main square<br />Lenos)

        fields = {elt.text for elt in brick_node.findall(".//span[@class='address-option-value']")}

        if country_in:
            self.assertIn(address.country, fields)
        else:
            self.assertNotIn(address.country, fields)

    # def _assertAddressNotIn(self, block_body, address):
    #     self.assertNotIn(address.address, block_body)
    #     self.assertNotIn(address.city,    block_body)
    def _assertAddressNotIn(self, brick_node, address):
        pretty_addr_node = brick_node.findall(".//div[@class='address']")
        self.assertIsNotNone(pretty_addr_node)

        pretty_addr = {elt.text.strip() for elt in brick_node.findall(".//div[@class='address']")}
        self.assertNotIn(address.address, pretty_addr)

    # def _assertButtonIn(self, block_content, url_name, entity):
    #     self.assertIn(reverse(url_name, args=(entity.id,)), block_content['buttons'])

    def _get_URLs(self, brick_node):
        return {elt.get('href').split('?')[0] for elt in brick_node.findall(".//a")}

    def get_address_titles(self, brick_node):
        return {elt.text.strip() for elt in brick_node.findall(".//span[@class='address-title']")}

    # def _assertButtonNotIn(self, block_content, url_name, entity):
    #     self.assertNotIn(reverse(url_name, args=(entity.id,)), block_content['buttons'])
    def _assertNoAction(self, brick_node, url_name, entity):
        self.assertNotIn(reverse(url_name, args=(entity.id,)), self._get_URLs(brick_node))

    def _assertAction(self, brick_node, url_name, entity):
        self.assertIn(reverse(url_name, args=(entity.id,)), self._get_URLs(brick_node))

    # def _assertColspanEqual(self, block_content, colspan):
    #     for attr_name, attr_value in block_content['header'].attributes:
    #         if attr_name == 'colspan':
    #             found_colspan = int(attr_value)
    #             break
    #     else:
    #         self.fail('"colspan" attribute not found.')
    #
    #     self.assertEqual(colspan, found_colspan)

    def _create_contact_n_addresses(self, billing_address=True, shipping_address=True):
        c = Contact.objects.create(user=self.user, first_name='Lawrence', last_name='?')

        create_address = partial(Address.objects.create, owner=c)

        if billing_address:
            c.billing_address = create_address(name='Billing address',
                                               address='Main square',
                                               city='Lenos',
                                               country='North',
                                              )

        if shipping_address:
            c.shipping_address = create_address(name='Shipping address',
                                                address='Market',
                                                city='Yorentz',
                                                country='South',
                                               )

        c.save()

        return c

    # def test_addresses_block01(self):
    def test_addresses_brick01(self):
        c = self._create_contact_n_addresses()
        # content = self._get_address_block_content(c)
        #
        # self._assertAddressIn(content, c.billing_address,  _(u'Billing address'))
        # self._assertAddressIn(content, c.shipping_address, _(u'Shipping address'))
        #
        # self._assertButtonNotIn(content, 'persons__create_billing_address', c)
        # self._assertButtonNotIn(content, 'persons__create_shipping_address', c)
        #
        # self._assertColspanEqual(content, 6)
        brick_node = self._get_address_brick_node(c)
        self._assertAddressIn(brick_node, c.billing_address,  _(u'Billing address'))
        self._assertAddressIn(brick_node, c.shipping_address, _(u'Shipping address'))

        self._assertNoAction(brick_node, 'persons__create_billing_address', c)
        self._assertNoAction(brick_node, 'persons__create_shipping_address', c)

    # def test_addresses_block02(self):
    def test_addresses_brick02(self):
        "No shipping address set"
        c = self._create_contact_n_addresses(shipping_address=False)
        # content = self._get_address_block_content(c)
        #
        # self._assertAddressIn(content, c.billing_address, _(u'Billing address'))
        # self.assertNotIn(_(u'Shipping address'), content['titles'])
        #
        # self._assertButtonNotIn(content, 'persons__create_billing_address', c)
        # self._assertButtonIn(content, 'persons__create_shipping_address', c)
        #
        # self._assertColspanEqual(content, 3)
        brick_node = self._get_address_brick_node(c)
        self._assertAddressIn(brick_node, c.billing_address, _(u'Billing address'))
        self.assertNotIn(_(u'Shipping address'), self.get_address_titles(brick_node))

        self._assertNoAction(brick_node, 'persons__create_billing_address', c)
        self._assertAction(brick_node, 'persons__create_shipping_address', c)

    # def test_addresses_block03(self):
    def test_addresses_brick03(self):
        "No billing address set"
        c = self._create_contact_n_addresses(billing_address=False)
        # content = self._get_address_block_content(c)
        #
        # self._assertAddressIn(content, c.shipping_address, _(u'Shipping address'))
        # self.assertNotIn(_(u'Billing address'), content['titles'])
        #
        # self._assertButtonNotIn(content, 'persons__create_shipping_address', c)
        # self._assertButtonIn(content, 'persons__create_billing_address', c)
        #
        # self._assertColspanEqual(content, 3)
        brick_node = self._get_address_brick_node(c)
        self._assertAddressIn(brick_node, c.shipping_address, _(u'Shipping address'))
        self.assertNotIn(_(u'Billing address'), self.get_address_titles(brick_node))

        self._assertAction(brick_node, 'persons__create_billing_address', c)
        self._assertNoAction(brick_node, 'persons__create_shipping_address', c)

    # def test_addresses_block04(self):
    def test_addresses_brick04(self):
        "No address set"
        c = self._create_contact_n_addresses(billing_address=False, shipping_address=False)
        # content = self._get_address_block_content(c, no_titles=True)
        # self._assertColspanEqual(content, 1)
        brick_node = self._get_address_brick_node(c)
        msg_node = brick_node.find("div[@class='brick-content is-empty']")
        self.assertIsNotNone(msg_node)
        self.assertEqual(_(u'No address for the moment'), msg_node.text.strip())

    # def test_addresses_block05(self):
    def test_addresses_brick05(self):
        "With field config on sub-field"
        FieldsConfig.create(Address,
                            descriptions=[('country', {FieldsConfig.HIDDEN: True})],
                           )

        c = self._create_contact_n_addresses()
        # content = self._get_address_block_content(c)
        # self._assertAddressIn(content, c.billing_address,  _(u'Billing address'),  country_in=False)
        # self._assertAddressIn(content, c.shipping_address, _(u'Shipping address'), country_in=False)
        brick_node = self._get_address_brick_node(c)
        self._assertAddressIn(brick_node, c.billing_address,  _(u'Billing address'),  country_in=False)
        self._assertAddressIn(brick_node, c.shipping_address, _(u'Shipping address'), country_in=False)

    # def test_addresses_block06(self):
    def test_addresses_brick06(self):
        "With field config on 'billing_address' FK field"
        FieldsConfig.create(Contact,
                            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
                           )

        c = self._create_contact_n_addresses()
        # content = self._get_address_block_content(c)
        # self._assertAddressIn(content, c.shipping_address, _(u'Shipping address'))
        # self._assertAddressNotIn(content, c.billing_address)
        #
        # self._assertButtonNotIn(content, 'persons__create_billing_address', c)
        # self._assertButtonNotIn(content, 'persons__create_shipping_address', c)
        brick_node = self._get_address_brick_node(c)
        self._assertAddressIn(brick_node, c.shipping_address, _(u'Shipping address'))
        self._assertAddressNotIn(brick_node, c.billing_address)

        self._assertNoAction(brick_node, 'persons__create_billing_address', c)
        self._assertNoAction(brick_node, 'persons__create_shipping_address', c)

    # def test_addresses_block07(self):
    def test_addresses_brick07(self):
        "With field config on 'shipping_address' FK field"
        FieldsConfig.create(Contact,
                            descriptions=[('shipping_address', {FieldsConfig.HIDDEN: True})],
                           )

        c = self._create_contact_n_addresses()
        # content = self._get_address_block_content(c)
        # self._assertAddressIn(content, c.billing_address, _(u'Billing address'))
        # self._assertAddressNotIn(content, c.shipping_address)
        brick_node = self._get_address_brick_node(c)
        self._assertAddressIn(brick_node, c.billing_address, _(u'Billing address'))
        self._assertAddressNotIn(brick_node, c.shipping_address)


@skipIfActivitiesisNotInstalled
@skipIfCustomOrganisation
class NeglectedOrganisationsBrickTestCase(CremeTestCase):
    def setUp(self):
        self.login()

    def _build_customer_orga(self, mng_orga, name, **kwargs):
        customer = Organisation.objects.create(user=self.user, name=name, **kwargs)
        Relation.objects.create(user=self.user, subject_entity=customer,
                                object_entity=mng_orga,
                                type_id=constants.REL_SUB_CUSTOMER_SUPPLIER,
                               )

        return customer

    def _get_neglected_orgas(self):
        neglected_orgas_block = bricks.NeglectedOrganisationsBrick()
        return neglected_orgas_block._get_neglected(now())

    def test_neglected_brick01(self):
        bricks.NeglectedOrganisationsBrick()

        orgas = Organisation.objects.all()
        self.assertEqual(1, len(orgas))

        mng_orga = orgas[0]
        # self.assertTrue(CremeProperty.objects.filter(type=PROP_IS_MANAGED_BY_CREME, creme_entity=mng_orga).exists())
        self.assertTrue(mng_orga.is_managed)
        self.assertFalse(self._get_neglected_orgas())

        customer01 = Organisation.objects.create(user=self.user, name='orga02')
        self.assertFalse(self._get_neglected_orgas())

        rtype_customer = RelationType.objects.get(pk=constants.REL_SUB_CUSTOMER_SUPPLIER)
        create_rel = partial(Relation.objects.create, user=self.user)
        create_rel(subject_entity=customer01, object_entity=mng_orga, type=rtype_customer)
        self.assertEqual([customer01.id], [orga.id for orga in self._get_neglected_orgas()])

        customer02 = Organisation.objects.create(user=self.user, name='orga03')
        create_rel(subject_entity=customer02, object_entity=mng_orga,
                   type=RelationType.objects.get(pk=constants.REL_SUB_PROSPECT),
                  )
        neglected_orgas = self._get_neglected_orgas()
        self.assertEqual(2, len(neglected_orgas))
        self.assertEqual({customer01.id, customer02.id}, {orga.id for orga in neglected_orgas})

        create_rel(subject_entity=customer02, object_entity=mng_orga, type=rtype_customer)
        self.assertEqual(2, len(self._get_neglected_orgas()))

    @skipIfCustomActivity
    def test_neglected_brick02(self):
        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = user.linked_contact

        customer01 = self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')
        self.assertEqual(2, len(self._get_neglected_orgas()))

        tomorrow = now() + timedelta(days=1)  # So in the future
        meeting  = Activity.objects.create(user=user, type_id=act_constants.ACTIVITYTYPE_MEETING,
                                           title='meet01', start=tomorrow,
                                           end=tomorrow + timedelta(hours=2),
                                          )

        get_rtype = RelationType.objects.get
        create_rel = partial(Relation.objects.create, user=user, object_entity=meeting)
        create_rel(subject_entity=customer02, type=get_rtype(pk=act_constants.REL_SUB_ACTIVITY_SUBJECT))
        self.assertEqual(2, len(self._get_neglected_orgas()))

        create_rel(subject_entity=user_contact, type=get_rtype(pk=act_constants.REL_SUB_PART_2_ACTIVITY))
        self.assertEqual([customer01.id], [orga.id for orga in self._get_neglected_orgas()])

    @skipIfCustomActivity
    def test_neglected_brick03(self):
        "Past activity => orga is still neglected"
        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = user.linked_contact

        self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')

        yesterday = now() - timedelta(days=1)  # So in the past
        meeting  = Activity.objects.create(user=user, type_id=act_constants.ACTIVITYTYPE_MEETING,
                                           title='meet01', start=yesterday,
                                           end=yesterday + timedelta(hours=2),
                                          )

        create_rel = partial(Relation.objects.create, user=user, object_entity=meeting)
        create_rel(subject_entity=customer02,   type_id=act_constants.REL_SUB_ACTIVITY_SUBJECT)
        create_rel(subject_entity=user_contact, type_id=act_constants.REL_SUB_PART_2_ACTIVITY)
        self.assertEqual(2, len(self._get_neglected_orgas()))  # And not 1

    @skipIfCustomContact
    @skipIfCustomActivity
    def test_neglected_brick04(self):
        "A people linked to customer is linked to a future activity"
        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = user.linked_contact

        customer = self._build_customer_orga(mng_orga, 'Suna')

        tomorrow = now() + timedelta(days=1)  # So in the future
        meeting = Activity.objects.create(user=user, type_id=act_constants.ACTIVITYTYPE_MEETING,
                                          title='meet01', start=tomorrow,
                                          end=tomorrow + timedelta(hours=2),
                                         )
        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=user_contact, object_entity=meeting,
                   type_id=act_constants.REL_SUB_PART_2_ACTIVITY,
                  )

        employee = Contact.objects.create(user=user, first_name='Kankuro', last_name='???')

        get_rtype = RelationType.objects.get
        create_rel(subject_entity=employee, object_entity=customer,
                   type=get_rtype(pk=constants.REL_SUB_EMPLOYED_BY),
                  )
        self.assertEqual(1, len(self._get_neglected_orgas()))

        create_rel(subject_entity=employee, object_entity=meeting,
                   type=get_rtype(pk=act_constants.REL_SUB_LINKED_2_ACTIVITY),
                  )
        self.assertFalse(self._get_neglected_orgas())

    @skipIfCustomContact
    @skipIfCustomActivity
    def test_neglected_brick05(self):
        "2 people linked to customer are linked to a future activity"
        user = self.user
        mng_orga = Organisation.objects.all()[0]

        create_contact = partial(Contact.objects.create, user=user)
        user_contact = user.linked_contact

        customer = self._build_customer_orga(mng_orga, 'Suna')

        tomorrow = now() + timedelta(days=1)  # So in the future
        create_activity = partial(Activity.objects.create, user=user, start=tomorrow)
        meeting   = create_activity(title='meet01', type_id=act_constants.ACTIVITYTYPE_MEETING,
                                    end=tomorrow + timedelta(hours=2)
                                   )
        phonecall = create_activity(title='call01', type_id=act_constants.ACTIVITYTYPE_PHONECALL,
                                    end=tomorrow + timedelta(minutes=15),
                                   )

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=user_contact, object_entity=phonecall, type_id=act_constants.REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=user_contact, object_entity=meeting,   type_id=act_constants.REL_SUB_PART_2_ACTIVITY)

        manager  = create_contact(first_name='Gaara', last_name='???')
        employee = create_contact(first_name='Temari', last_name='???')
        create_rel(subject_entity=manager,  object_entity=customer, type_id=constants.REL_SUB_MANAGES)
        create_rel(subject_entity=employee, object_entity=customer, type_id=constants.REL_SUB_EMPLOYED_BY)
        self.assertEqual(1, len(self._get_neglected_orgas()))

        create_rel(subject_entity=manager, object_entity=phonecall, type_id=act_constants.REL_SUB_PART_2_ACTIVITY)
        self.assertFalse(self._get_neglected_orgas())

        create_rel(subject_entity=employee, object_entity=meeting, type_id=act_constants.REL_SUB_ACTIVITY_SUBJECT)
        self.assertFalse(self._get_neglected_orgas())

    @skipIfCustomContact
    @skipIfCustomActivity
    def test_neglected_brick06(self):
        "Future activity, but not with managed organisation !"
        user = self.user
        mng_orga   = Organisation.objects.all()[0]
        customer   = self._build_customer_orga(mng_orga, 'Suna')
        competitor = Organisation.objects.create(user=user, name='Akatsuki')

        tomorrow = now() + timedelta(days=1)  # So in the future
        meeting  = Activity.objects.create(user=user, type_id=act_constants.ACTIVITYTYPE_MEETING,
                                           title='meet01', start=tomorrow,
                                           end=tomorrow + timedelta(hours=2),
                                          )

        manager = Contact.objects.create(user=user,  first_name='Gaara', last_name='???')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=manager, object_entity=customer, type_id=constants.REL_SUB_MANAGES)

        create_rel(subject_entity=manager,    object_entity=meeting, type_id=act_constants.REL_SUB_PART_2_ACTIVITY)
        create_rel(subject_entity=competitor, object_entity=meeting, type_id=act_constants.REL_SUB_ACTIVITY_SUBJECT)
        self.assertEqual(1, len(self._get_neglected_orgas()))

    def test_neglected_brick07(self):
        "Inactive customers are not counted"
        mng_orga   = Organisation.objects.all()[0]
        customer01 = self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')
        Relation.objects.create(user=self.user, subject_entity=customer02,
                                object_entity=mng_orga, type_id=constants.REL_SUB_INACTIVE
                               )
        self.assertEqual([customer01], list(self._get_neglected_orgas()))

    def test_neglected_brick08(self):
        "Deleted customers are not counted"
        mng_orga = Organisation.objects.all()[0]
        customer = self._build_customer_orga(mng_orga, 'Konoha')
        self._build_customer_orga(mng_orga, 'Suna', is_deleted=True)
        self.assertEqual([customer], list(self._get_neglected_orgas()))

    def _oldify(self, entity, days_delta):
        entity.created -= timedelta(days=days_delta)
        return entity

    def test_neglected_indicator01(self):
        "Young entity => special label"
        contact = self._oldify(Contact.objects.create(user=self.user, first_name='Gaara', last_name='???'),
                               days_delta=10
                              )
        indicator = bricks.NeglectedContactIndicator(context={'today': now()}, contact=contact)
        self.assertEqual(_(u'Never contacted'), indicator.label)

    def test_neglected_indicator02(self):
        "regular label for neglected"
        user = self.user
        contact = self._oldify(Contact.objects.create(user=self.user, first_name='Gaara', last_name='???'),
                               days_delta=16
                              )

        now_value = now()
        one_month_ago = now_value - timedelta(days=30)
        meeting = Activity.objects.create(user=user, type_id=act_constants.ACTIVITYTYPE_MEETING,
                                          title='meet01',
                                          start=one_month_ago,
                                          end=one_month_ago + timedelta(hours=2),
                                         )

        Relation.objects.create(user=user, subject_entity=contact, object_entity=meeting, type_id=act_constants.REL_SUB_PART_2_ACTIVITY)

        indicator = bricks.NeglectedContactIndicator(context={'today': now_value}, contact=contact)
        self.assertEqual(_(u'Not contacted since 15 days'), indicator.label)

    def test_neglected_indicator03(self):
        "Not neglected"
        user = self.user
        contact = self._oldify(Contact.objects.create(user=self.user, first_name='Gaara', last_name='???'),
                               days_delta=16
                              )

        now_value = now()
        one_week_ago = now_value - timedelta(days=7)
        meeting = Activity.objects.create(user=user, type_id=act_constants.ACTIVITYTYPE_MEETING,
                                          title='meet01',
                                          start=one_week_ago,
                                          end=one_week_ago + timedelta(hours=2),
                                         )

        Relation.objects.create(user=user, subject_entity=contact, object_entity=meeting, type_id=act_constants.REL_SUB_PART_2_ACTIVITY)

        indicator = bricks.NeglectedContactIndicator(context={'today': now_value}, contact=contact)
        self.assertFalse(indicator.label)

    def test_neglected_indicator04(self):
        "User-contacts are ignored"
        user = self.user
        contact = self._oldify(user.linked_contact, days_delta=16)

        now_value = now()
        one_month_ago = now_value - timedelta(days=30)
        meeting = Activity.objects.create(user=user, type_id=act_constants.ACTIVITYTYPE_MEETING,
                                          title='meet01',
                                          start=one_month_ago,
                                          end=one_month_ago + timedelta(hours=2),
                                         )

        Relation.objects.create(user=user, subject_entity=contact, object_entity=meeting, type_id=act_constants.REL_SUB_PART_2_ACTIVITY)

        indicator = bricks.NeglectedContactIndicator(context={'today': now_value}, contact=contact)
        self.assertFalse(indicator.label)
