# -*- coding: utf-8 -*-

from datetime import date, timedelta
from functools import partial
from unittest import skipIf
from urllib.parse import urlencode

from django.apps import apps
from django.conf import settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.auth import EntityCredentials
from creme.creme_core.models import (
    BrickDetailviewLocation,
    FieldsConfig,
    Relation,
    RelationType,
    SetCredentials,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from .. import bricks, constants
from .base import (
    Address,
    Contact,
    Organisation,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

if apps.is_installed('creme.activities'):
    from creme.activities import constants as act_constants
    from creme.activities.models import Activity
    from creme.activities.tests.base import skipIfCustomActivity

    def skipIfActivitiesIsNotInstalled(test_func):
        return skipIf(False, 'The app "activities" is not installed')(test_func)
else:
    def skipIfActivitiesIsNotInstalled(test_func):
        return skipIf(True, 'The app "activities" is not installed')(test_func)

    def skipIfCustomActivity(test_func):
        return skipIf(True, 'The app "activities" is not installed')(test_func)

if apps.is_installed('creme.opportunities'):
    from creme.opportunities.models import Opportunity, SalesPhase
    from creme.opportunities.tests.base import skipIfCustomOpportunity
else:
    def skipIfCustomOpportunity(test_func):
        return skipIf(True, 'The app "opportunities" is not installed')(test_func)

if apps.is_installed('creme.commercial'):
    from creme.commercial.constants import REL_OBJ_COMPLETE_GOAL
    from creme.commercial.models import Act, ActType, MarketSegment
    from creme.commercial.tests.base import skipIfCustomAct
else:
    def skipIfCustomAct(test_func):
        return skipIf(True, 'The app "commercial" is not installed')(test_func)


@skipIfCustomOrganisation
@skipIfCustomContact
class BricksTestCase(BrickTestCaseMixin, CremeTestCase):
    def _get_address_brick_node(self, entity, brick_cls):
        response = self.assertGET200(entity.get_absolute_url())
        return self.get_brick_node(
            self.get_html_tree(response.content),
            brick_cls.id_,
        )

    def _assertInDetailedAddress(self,
                                 brick_node, address, title,
                                 address_type=None,
                                 country_in=True,
                                 ):
        self.assertIn(title, self.get_address_titles(brick_node))

        address_node = self.get_html_node_or_fail(
            brick_node,
            f".//div[@class='address-container {address_type}-address-container']"
            if address_type else
            ".//div[@class='address-container']",
        )

        fields = {
            elt.text.strip()
            for elt in address_node.findall(".//span[@class='address-option-value']")
            if elt.text
        }
        # self.assertIn(address.address, fields)   # TODO: extract from <p>
        self.assertIn(address.city,    fields)

        if country_in:
            self.assertIn(address.country, fields)
        else:
            self.assertNotIn(address.country, fields)

    def _assertInPrettyAddress(self,
                               brick_node, address, title,
                               address_type=None,
                               country_in=True,
                               ):
        self.assertIn(title, self.get_address_titles(brick_node))

        address_node = self.get_html_node_or_fail(
            brick_node,
            f".//div[@class='address-container {address_type}-address-container']"
            if address_type else
            ".//div[@class='address-container']",
        )

        pretty_addr_node = self.get_html_node_or_fail(address_node, ".//div[@class='address']")
        self.assertEqual(address.address, pretty_addr_node.text)

        fields = {
            elt.text
            for elt in address_node.findall(".//span[@class='address-option-value']")
        }

        if country_in:
            self.assertIn(address.country, fields)
        else:
            self.assertNotIn(address.country, fields)

    def _assertAddressNotIn(self, brick_node, address):
        pretty_addr_node = brick_node.findall(".//div[@class='address']")
        self.assertIsNotNone(pretty_addr_node)

        pretty_addr = {
            elt.text.strip()
            for elt in brick_node.findall(".//div[@class='address']")
        }
        self.assertNotIn(address.address, pretty_addr)

    @staticmethod
    def _get_URLs(brick_node):
        return {elt.get('href').split('?')[0] for elt in brick_node.findall('.//a')}

    @staticmethod
    def get_address_titles(brick_node):
        return {
            elt.text.strip()
            for elt in brick_node.findall(".//span[@class='address-title']")
        }

    def _assertNoAction(self, brick_node, url_name, entity):
        self.assertNotIn(reverse(url_name, args=(entity.id,)), self._get_URLs(brick_node))

    def _assertAction(self, brick_node, url_name, entity):
        self.assertIn(reverse(url_name, args=(entity.id,)), self._get_URLs(brick_node))

    def _create_contact_n_addresses(self, billing_address=True, shipping_address=True):
        c = Contact.objects.create(user=self.user, first_name='Lawrence', last_name='Kraft')

        create_address = partial(Address.objects.create, owner=c)

        if billing_address:
            c.billing_address = create_address(
                name='Billing address',
                address='Main square',
                city='Lenos',
                country='North',
            )

        if shipping_address:
            c.shipping_address = create_address(
                name='Shipping address',
                address='Market',
                city='Yorentz',
                country='South',
            )

        c.save()

        return c

    @skipIfCustomOpportunity
    def test_contact_hat_card_brick_opp(self):
        user = self.login()
        c = Contact.objects.create(user=user, first_name='Lawrence', last_name='Kraft')

        create_orga = partial(Organisation.objects.create, user=user)
        emitter = create_orga(name='Lenos')
        target_orga = create_orga(name='Yorentz')

        create_opp = partial(
            Opportunity.objects.create,
            user=user,
            sales_phase=SalesPhase.objects.first(),
            emitter=emitter,
        )
        opp1 = create_opp(name='Opp#01', target=c)
        opp2 = create_opp(name='Opp#02', target=target_orga)
        opp3 = create_opp(name='Opp#03', target=c)

        response = self.assertGET200(c.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), bricks.ContactCardHatBrick.id_,
        )

        self.assertInstanceLink(brick_node, opp1)
        self.assertNoInstanceLink(brick_node, opp2)
        self.assertInstanceLink(brick_node, opp3)

    @skipIfCustomOpportunity
    def test_orga_hat_card_brick_opp(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        emitter = create_orga(name='Lenos')
        target_orga = create_orga(name='Yorentz')

        c = Contact.objects.create(user=user, first_name='Lawrence', last_name='Kraft')

        create_opp = partial(
            Opportunity.objects.create,
            user=user, sales_phase=SalesPhase.objects.first(), emitter=emitter,
        )
        opp1 = create_opp(name='Opp#01', target=target_orga)
        opp2 = create_opp(name='Opp#02', target=c)
        opp3 = create_opp(name='Opp#03', target=target_orga)

        response = self.assertGET200(target_orga.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), bricks.OrganisationCardHatBrick.id_,
        )

        self.assertInstanceLink(brick_node, opp1)
        self.assertNoInstanceLink(brick_node, opp2)
        self.assertInstanceLink(brick_node, opp3)

    @skipIfCustomAct
    def test_contact_hat_card_brick_commercial(self):
        user = self.login()
        c = Contact.objects.create(user=user, first_name='Lawrence', last_name='Kraft')
        orga = Organisation.objects.create(user=user, name='Lenos')

        segment = MarketSegment.objects.first()

        def create_act(name, entity):
            act = Act.objects.create(
                name=name, user=user, expected_sales=1000,
                cost=50, goal='GOAL',
                start=date(2019, 2, 22), due_date=date(2019, 2, 26),
                act_type=ActType.objects.create(title='Show'),
                segment=segment,
            )

            Relation.objects.create(
                user=user, type_id=REL_OBJ_COMPLETE_GOAL,
                subject_entity=act, object_entity=entity,
            )

            return act

        act1 = create_act('Act #01', c)
        act2 = create_act('Act #02', orga)
        act3 = create_act('Act #02', c)

        response = self.assertGET200(c.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), bricks.ContactCardHatBrick.id_,
        )

        self.assertInstanceLink(brick_node, act1)
        self.assertNoInstanceLink(brick_node, act2)
        self.assertInstanceLink(brick_node, act3)

    @skipIfCustomAct
    def test_orga_hat_card_brick_commercial(self):
        user = self.login()
        orga = Organisation.objects.create(user=user, name='Lenos')
        c = Contact.objects.create(user=user, first_name='Lawrence', last_name='Kraft')

        segment = MarketSegment.objects.first()

        def create_act(name, entity):
            act = Act.objects.create(
                name=name, user=user, expected_sales=1000,
                cost=50, goal='GOAL',
                start=date(2019, 2, 22), due_date=date(2019, 2, 26),
                act_type=ActType.objects.create(title='Show'),
                segment=segment,
            )

            Relation.objects.create(
                user=user, type_id=REL_OBJ_COMPLETE_GOAL,
                subject_entity=act, object_entity=entity,
            )

            return act

        act1 = create_act('Act #01', orga)
        act2 = create_act('Act #02', c)
        act3 = create_act('Act #02', orga)

        response = self.assertGET200(orga.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), bricks.OrganisationCardHatBrick.id_,
        )

        self.assertInstanceLink(brick_node, act1)
        self.assertNoInstanceLink(brick_node, act2)
        self.assertInstanceLink(brick_node, act3)

    def test_pretty_addresses_brick01(self):
        self.login()
        c = self._create_contact_n_addresses()

        brick_node = self._get_address_brick_node(c, bricks.PrettyAddressesBrick)
        self._assertInPrettyAddress(
            brick_node, c.billing_address, _('Billing address'), address_type='billing',
        )
        self._assertInPrettyAddress(
            brick_node, c.shipping_address, _('Shipping address'), address_type='shipping',
        )

        self._assertNoAction(brick_node, 'persons__create_billing_address', c)
        self._assertNoAction(brick_node, 'persons__create_shipping_address', c)

    def test_pretty_addresses_brick02(self):
        "No shipping address set."
        self.login()
        c = self._create_contact_n_addresses(shipping_address=False)

        brick_node = self._get_address_brick_node(c, bricks.PrettyAddressesBrick)
        self._assertInPrettyAddress(
            brick_node, c.billing_address, _('Billing address'), address_type='billing',
        )
        self.assertNotIn(_('Shipping address'), self.get_address_titles(brick_node))

        self._assertNoAction(brick_node, 'persons__create_billing_address', c)
        self._assertAction(brick_node, 'persons__create_shipping_address', c)

    def test_pretty_addresses_brick03(self):
        "No billing address set."
        self.login()
        c = self._create_contact_n_addresses(billing_address=False)

        brick_node = self._get_address_brick_node(c, bricks.PrettyAddressesBrick)
        self._assertInPrettyAddress(
            brick_node, c.shipping_address, _('Shipping address'), address_type='shipping',
        )
        self.assertNotIn(_('Billing address'), self.get_address_titles(brick_node))

        self._assertAction(brick_node, 'persons__create_billing_address', c)
        self._assertNoAction(brick_node, 'persons__create_shipping_address', c)

    def test_pretty_addresses_brick04(self):
        "No address set."
        self.login()
        c = self._create_contact_n_addresses(billing_address=False, shipping_address=False)

        brick_node = self._get_address_brick_node(c, bricks.PrettyAddressesBrick)
        msg_node = brick_node.find("div[@class='brick-content is-empty']")
        self.assertIsNotNone(msg_node)
        self.assertEqual(_('No address for the moment'), msg_node.text.strip())

    def test_pretty_addresses_brick05(self):
        "With field config on sub-field."
        self.login()
        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[('country', {FieldsConfig.HIDDEN: True})],
        )

        c = self._create_contact_n_addresses()

        brick_node = self._get_address_brick_node(c, bricks.PrettyAddressesBrick)
        self._assertInPrettyAddress(
            brick_node, c.billing_address, _('Billing address'),
            country_in=False, address_type='billing',
        )
        self._assertInPrettyAddress(
            brick_node, c.shipping_address, _('Shipping address'),
            country_in=False, address_type='shipping',
        )

    def test_pretty_addresses_brick06(self):
        "With field config on 'billing_address' FK field."
        self.login()
        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
        )

        c = self._create_contact_n_addresses()

        brick_node = self._get_address_brick_node(c, bricks.PrettyAddressesBrick)
        self._assertInPrettyAddress(
            brick_node, c.shipping_address, _('Shipping address'), address_type='shipping',
        )
        self._assertAddressNotIn(brick_node, c.billing_address)

        self._assertNoAction(brick_node, 'persons__create_billing_address', c)
        self._assertNoAction(brick_node, 'persons__create_shipping_address', c)

    def test_pretty_addresses_brick07(self):
        "With field config on 'shipping_address' FK field."
        self.login()
        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('shipping_address', {FieldsConfig.HIDDEN: True})],
        )

        c = self._create_contact_n_addresses()

        brick_node = self._get_address_brick_node(c, bricks.PrettyAddressesBrick)
        self._assertInPrettyAddress(
            brick_node, c.billing_address, _('Billing address'), address_type='billing',
        )
        self._assertAddressNotIn(brick_node, c.shipping_address)

    def test_pretty_other_addresses_brick(self):
        self.login()
        c = self._create_contact_n_addresses()
        address = Address.objects.create(
            owner=c,
            name='Other address',
            address='Main street',
            city='Svelnel',
            country='North',
        )

        brick_node = self._get_address_brick_node(c, bricks.PrettyOtherAddressesBrick)
        self._assertInPrettyAddress(brick_node, address, address.name)

        self._assertAction(brick_node, 'persons__create_address', c)

    def test_detailed_addresses_brick01(self):
        self.login()
        c = self._create_contact_n_addresses()

        brick_cls = bricks.DetailedAddressesBrick
        BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_cls, order=600, zone=BrickDetailviewLocation.RIGHT, model=Contact,
        )

        brick_node = self._get_address_brick_node(c, brick_cls)
        self._assertInDetailedAddress(
            brick_node, c.billing_address, _('Billing address'), address_type='billing',
        )
        self._assertInDetailedAddress(
            brick_node, c.shipping_address, _('Shipping address'), address_type='shipping',
        )

        self._assertNoAction(brick_node, 'persons__create_billing_address', c)
        self._assertNoAction(brick_node, 'persons__create_shipping_address', c)

    def test_detailed_addresses_brick02(self):
        "No shipping address set."
        self.login()
        c = self._create_contact_n_addresses(shipping_address=False)

        brick_cls = bricks.DetailedAddressesBrick
        BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_cls, order=600, zone=BrickDetailviewLocation.RIGHT, model=Contact,
        )

        brick_node = self._get_address_brick_node(c, brick_cls)
        self._assertInDetailedAddress(
            brick_node, c.billing_address, _('Billing address'), address_type='billing',
        )
        self.assertNotIn(_('Shipping address'), self.get_address_titles(brick_node))

        self._assertNoAction(brick_node, 'persons__create_billing_address', c)
        self._assertAction(brick_node, 'persons__create_shipping_address', c)

    def test_detailed_addresses_brick03(self):
        "No billing address set."
        self.login()
        c = self._create_contact_n_addresses(billing_address=False)

        brick_cls = bricks.DetailedAddressesBrick
        BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_cls, order=600, zone=BrickDetailviewLocation.RIGHT, model=Contact,
        )

        brick_node = self._get_address_brick_node(c, brick_cls)
        self._assertInDetailedAddress(
            brick_node, c.shipping_address, _('Shipping address'), address_type='shipping',
        )
        self.assertNotIn(_('Billing address'), self.get_address_titles(brick_node))

        self._assertAction(brick_node, 'persons__create_billing_address', c)
        self._assertNoAction(brick_node, 'persons__create_shipping_address', c)

    def test_detailed_addresses_brick04(self):
        "No address set."
        self.login()
        c = self._create_contact_n_addresses(billing_address=False, shipping_address=False)

        brick_cls = bricks.DetailedAddressesBrick
        BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_cls, order=600, zone=BrickDetailviewLocation.RIGHT, model=Contact,
        )

        brick_node = self._get_address_brick_node(c, brick_cls)
        msg_node = brick_node.find("div[@class='brick-content is-empty']")
        self.assertIsNotNone(msg_node)
        self.assertEqual(_('No address for the moment'), msg_node.text.strip())

    def test_detailed_addresses_brick05(self):
        "With field config on sub-field."
        self.login()
        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[('country', {FieldsConfig.HIDDEN: True})],
        )

        c = self._create_contact_n_addresses()

        brick_cls = bricks.DetailedAddressesBrick
        BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_cls, order=600, zone=BrickDetailviewLocation.RIGHT, model=Contact,
        )

        brick_node = self._get_address_brick_node(c, brick_cls)
        self._assertInDetailedAddress(
            brick_node, c.billing_address, _('Billing address'),
            address_type='billing', country_in=False,
        )
        self._assertInDetailedAddress(
            brick_node, c.shipping_address, _('Shipping address'),
            address_type='shipping', country_in=False,
        )

    def test_detailed_addresses_brick06(self):
        "With field config on 'billing_address' FK field."
        self.login()
        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
        )

        c = self._create_contact_n_addresses()

        brick_cls = bricks.DetailedAddressesBrick
        BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_cls, order=600, zone=BrickDetailviewLocation.RIGHT, model=Contact,
        )

        brick_node = self._get_address_brick_node(c, brick_cls)
        self._assertInDetailedAddress(
            brick_node, c.shipping_address, _('Shipping address'), address_type='shipping',
        )
        self._assertAddressNotIn(brick_node, c.billing_address)

        self._assertNoAction(brick_node, 'persons__create_billing_address', c)
        self._assertNoAction(brick_node, 'persons__create_shipping_address', c)

    def test_detailed_addresses_brick07(self):
        "With field config on 'shipping_address' FK field."
        self.login()
        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('shipping_address', {FieldsConfig.HIDDEN: True})],
        )

        c = self._create_contact_n_addresses()

        brick_cls = bricks.DetailedAddressesBrick
        BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_cls, order=600, zone=BrickDetailviewLocation.RIGHT, model=Contact,
        )

        brick_node = self._get_address_brick_node(c, brick_cls)
        self._assertInDetailedAddress(
            brick_node, c.billing_address, _('Billing address'), address_type='billing',
        )
        self._assertAddressNotIn(brick_node, c.shipping_address)

    def test_detailed_other_addresses_brick(self):
        self.login()
        c = self._create_contact_n_addresses()
        address = Address.objects.create(
            owner=c,
            name='Other address',
            address='Main street',
            city='Svelnel',
            country='North',
        )

        brick_cls = bricks.DetailedOtherAddressesBrick
        BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_cls, order=600, zone=BrickDetailviewLocation.RIGHT, model=Contact,
        )

        brick_node = self._get_address_brick_node(c, brick_cls)
        self._assertInDetailedAddress(brick_node, address, address.name)

        self._assertAction(brick_node, 'persons__create_address', c)

    def test_managers_brick01(self):
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(
            first_name='Lawrence', last_name='Kraft', email='lawrence@kraft.lns',
        )
        c2 = create_contact(
            first_name='Nora', last_name='Arendt', phone='123456', mobile='456789',
        )
        c3 = create_contact(first_name='Kohl', last_name='Tôte')

        create_orga = partial(Organisation.objects.create, user=user)
        o1 = create_orga(name='Lenos')
        o2 = create_orga(name='Yorentz')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=c1, type_id=constants.REL_SUB_MANAGES, object_entity=o1)
        create_rel(subject_entity=c2, type_id=constants.REL_SUB_MANAGES, object_entity=o1)

        # Not used
        create_rel(subject_entity=c3, type_id=constants.REL_SUB_MANAGES,     object_entity=o2)
        create_rel(subject_entity=c3, type_id=constants.REL_SUB_EMPLOYED_BY, object_entity=o1)

        bricks.ManagersBrick.page_size = max(bricks.ManagersBrick.page_size, 3)
        url = o1.get_absolute_url()

        def get_brick_node():
            response = self.assertGET200(url)
            return self.get_brick_node(
                self.get_html_tree(response.content), bricks.ManagersBrick.id_,
            )

        brick_node1 = get_brick_node()
        self.assertInstanceLink(brick_node1, c1)
        self.assertInstanceLink(brick_node1, c2)
        self.assertNoInstanceLink(brick_node1, c3)

        buttons_node = self.get_brick_header_buttons(brick_node1)
        self.assertBrickHeaderHasButton(
            buttons_node,
            url='{}?{}'.format(
                reverse(
                    'persons__create_related_contact',
                    args=(o1.id, constants.REL_OBJ_MANAGES),
                ),
                urlencode({'callback_url': url}),
            ),
            label=_('Create a manager'),
        )

        def get_phones(brick_node):
            return [
                n.text
                for n in brick_node.findall('.//td[@data-type="phone"]')
                if n.text
            ]

        self.assertListEqual(
            [f'mailto:{c1.email}'],
            [n.attrib.get('href') for n in brick_node1.findall('.//td[@data-type="email"]/a')],
        )
        self.assertListEqual([c2.phone, c2.mobile], get_phones(brick_node1))

        # email hidden ---
        fconf = FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )

        brick_node2 = get_brick_node()
        self.assertFalse(brick_node2.findall('.//td[@data-type="email"]'))
        self.assertListEqual([c2.phone, c2.mobile], get_phones(brick_node2))

        # phone hidden ---
        fconf.descriptions = [('phone', {FieldsConfig.HIDDEN: True})]
        fconf.save()
        self.assertListEqual([c2.mobile], get_phones(get_brick_node()))

        # mobile hidden ---
        fconf.descriptions = [('mobile', {FieldsConfig.HIDDEN: True})]
        fconf.save()
        self.assertListEqual([c2.phone], get_phones(get_brick_node()))

    def test_managers_brick02(self):
        user = self.login(is_superuser=False, allowed_apps=['persons'])
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        c = Contact.objects.create(
            user=self.other_user,
            first_name='Lawrence', last_name='Kraft', email='lawrence@kraft.lns',
        )
        o = Organisation.objects.create(user=user, name='Lenos')

        Relation.objects.create(
            user=user, subject_entity=c, type_id=constants.REL_SUB_MANAGES, object_entity=o,
        )

        response = self.assertGET200(o.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), bricks.ManagersBrick.id_,
        )

        self.assertEqual(1, len(brick_node.findall('.//td[@data-table-primary-column]')))
        self.assertFalse(brick_node.findall('.//td[@data-type="email"]'))
        self.assertFalse(brick_node.findall('.//td[@data-type="phone"]'))

        self.assertEqual(
            4,
            sum(
                int(n.text == settings.HIDDEN_VALUE)
                for n in brick_node.findall('.//tbody/tr/td')
            ),
        )

    def test_employees_brick(self):
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        c1 = create_contact(first_name='Lawrence', last_name='Kraft')
        c2 = create_contact(first_name='Nora',     last_name='Arendt')
        c3 = create_contact(first_name='Kohl',     last_name='Tôte')

        create_orga = partial(Organisation.objects.create, user=user)
        o1 = create_orga(name='Lenos')
        o2 = create_orga(name='Yorentz')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=c1, type_id=constants.REL_SUB_EMPLOYED_BY, object_entity=o1)
        create_rel(subject_entity=c2, type_id=constants.REL_SUB_EMPLOYED_BY, object_entity=o1)

        # Not used
        create_rel(subject_entity=c3, type_id=constants.REL_SUB_EMPLOYED_BY, object_entity=o2)
        create_rel(subject_entity=c3, type_id=constants.REL_SUB_MANAGES,     object_entity=o1)

        bricks.EmployeesBrick.page_size = max(bricks.EmployeesBrick.page_size, 3)

        url = o1.get_absolute_url()
        response = self.assertGET200(url)
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), bricks.EmployeesBrick.id_,
        )
        self.assertInstanceLink(brick_node, c1)
        self.assertInstanceLink(brick_node, c2)
        self.assertNoInstanceLink(brick_node, c3)

        buttons_node = self.get_brick_header_buttons(brick_node)
        self.assertBrickHeaderHasButton(
            buttons_node,
            url='{}?{}'.format(
                reverse(
                    'persons__create_related_contact',
                    args=(o1.id, constants.REL_OBJ_EMPLOYED_BY),
                ),
                urlencode({'callback_url': url}),
            ),
            label=_('Create an employee'),
        )


@skipIfActivitiesIsNotInstalled
@skipIfCustomOrganisation
class NeglectedOrganisationsBrickTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def _build_customer_orga(self, mng_orga, name, **kwargs):
        user = self.user
        customer = Organisation.objects.create(user=user, name=name, **kwargs)
        Relation.objects.create(
            user=user,
            subject_entity=customer,
            object_entity=mng_orga,
            type_id=constants.REL_SUB_CUSTOMER_SUPPLIER,
        )

        return customer

    @staticmethod
    def _get_neglected_orgas():
        neglected_orgas_block = bricks.NeglectedOrganisationsBrick()
        return neglected_orgas_block._get_neglected(now())

    def test_neglected_brick01(self):
        user = self.user
        bricks.NeglectedOrganisationsBrick()

        orgas = Organisation.objects.all()
        self.assertEqual(1, len(orgas))

        mng_orga = orgas[0]
        self.assertTrue(mng_orga.is_managed)
        self.assertFalse(self._get_neglected_orgas())

        customer01 = Organisation.objects.create(user=user, name='orga02')
        self.assertFalse(self._get_neglected_orgas())

        rtype_customer = RelationType.objects.get(pk=constants.REL_SUB_CUSTOMER_SUPPLIER)
        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=customer01, object_entity=mng_orga, type=rtype_customer)
        self.assertListEqual(
            [customer01.id], [orga.id for orga in self._get_neglected_orgas()],
        )

        customer02 = Organisation.objects.create(user=user, name='orga03')
        create_rel(
            subject_entity=customer02, object_entity=mng_orga,
            type=RelationType.objects.get(pk=constants.REL_SUB_PROSPECT),
        )
        neglected_orgas = self._get_neglected_orgas()
        self.assertEqual(2, len(neglected_orgas))
        self.assertSetEqual(
            {customer01.id, customer02.id}, {orga.id for orga in neglected_orgas},
        )

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
        meeting = Activity.objects.create(
            user=user,
            type_id=act_constants.ACTIVITYTYPE_MEETING,
            title='meet01', start=tomorrow,
            end=tomorrow + timedelta(hours=2),
        )

        get_rtype = RelationType.objects.get
        create_rel = partial(Relation.objects.create, user=user, object_entity=meeting)
        create_rel(
            subject_entity=customer02,
            type=get_rtype(pk=act_constants.REL_SUB_ACTIVITY_SUBJECT),
        )
        self.assertEqual(2, len(self._get_neglected_orgas()))

        create_rel(
            subject_entity=user_contact,
            type=get_rtype(pk=act_constants.REL_SUB_PART_2_ACTIVITY),
        )
        self.assertListEqual(
            [customer01.id],
            [orga.id for orga in self._get_neglected_orgas()],
        )

    @skipIfCustomActivity
    def test_neglected_brick03(self):
        "Past activity => orga is still neglected"
        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = user.linked_contact

        self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')

        yesterday = now() - timedelta(days=1)  # So in the past
        meeting = Activity.objects.create(
            user=user, type_id=act_constants.ACTIVITYTYPE_MEETING,
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
        "A people linked to customer is linked to a future activity."
        user = self.user
        mng_orga = Organisation.objects.all()[0]
        user_contact = user.linked_contact

        customer = self._build_customer_orga(mng_orga, 'Suna')

        tomorrow = now() + timedelta(days=1)  # So in the future
        meeting = Activity.objects.create(
            user=user,
            type_id=act_constants.ACTIVITYTYPE_MEETING,
            title='meet01', start=tomorrow,
            end=tomorrow + timedelta(hours=2),
        )
        create_rel = partial(Relation.objects.create, user=user)
        create_rel(
            subject_entity=user_contact, object_entity=meeting,
            type_id=act_constants.REL_SUB_PART_2_ACTIVITY,
        )

        employee = Contact.objects.create(
            user=user, first_name='Kankuro', last_name='???',
        )

        get_rtype = RelationType.objects.get
        create_rel(
            subject_entity=employee, object_entity=customer,
            type=get_rtype(pk=constants.REL_SUB_EMPLOYED_BY),
        )
        self.assertEqual(1, len(self._get_neglected_orgas()))

        create_rel(
            subject_entity=employee, object_entity=meeting,
            type=get_rtype(pk=act_constants.REL_SUB_LINKED_2_ACTIVITY),
        )
        self.assertFalse(self._get_neglected_orgas())

    @skipIfCustomContact
    @skipIfCustomActivity
    def test_neglected_brick05(self):
        "2 people linked to customer are linked to a future activity."
        user = self.user
        mng_orga = Organisation.objects.all()[0]

        create_contact = partial(Contact.objects.create, user=user)
        user_contact = user.linked_contact

        customer = self._build_customer_orga(mng_orga, 'Suna')

        tomorrow = now() + timedelta(days=1)  # So in the future
        create_activity = partial(Activity.objects.create, user=user, start=tomorrow)
        meeting = create_activity(
            title='meet01',
            type_id=act_constants.ACTIVITYTYPE_MEETING,
            end=tomorrow + timedelta(hours=2),
        )
        phonecall = create_activity(
            title='call01',
            type_id=act_constants.ACTIVITYTYPE_PHONECALL,
            end=tomorrow + timedelta(minutes=15),
        )

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(
            subject_entity=user_contact, object_entity=phonecall,
            type_id=act_constants.REL_SUB_PART_2_ACTIVITY,
        )
        create_rel(
            subject_entity=user_contact, object_entity=meeting,
            type_id=act_constants.REL_SUB_PART_2_ACTIVITY,
        )

        manager  = create_contact(first_name='Gaara', last_name='???')
        employee = create_contact(first_name='Temari', last_name='???')
        create_rel(
            subject_entity=manager, object_entity=customer,
            type_id=constants.REL_SUB_MANAGES,
        )
        create_rel(
            subject_entity=employee, object_entity=customer,
            type_id=constants.REL_SUB_EMPLOYED_BY,
        )
        self.assertEqual(1, len(self._get_neglected_orgas()))

        create_rel(
            subject_entity=manager, object_entity=phonecall,
            type_id=act_constants.REL_SUB_PART_2_ACTIVITY,
        )
        self.assertFalse(self._get_neglected_orgas())

        create_rel(
            subject_entity=employee, object_entity=meeting,
            type_id=act_constants.REL_SUB_ACTIVITY_SUBJECT,
        )
        self.assertFalse(self._get_neglected_orgas())

    @skipIfCustomContact
    @skipIfCustomActivity
    def test_neglected_brick06(self):
        "Future activity, but not with managed organisation!"
        user = self.user
        mng_orga = Organisation.objects.all()[0]
        customer = self._build_customer_orga(mng_orga, 'Suna')
        competitor = Organisation.objects.create(user=user, name='Akatsuki')

        tomorrow = now() + timedelta(days=1)  # So in the future
        meeting = Activity.objects.create(
            user=user, type_id=act_constants.ACTIVITYTYPE_MEETING,
            title='meet01', start=tomorrow,
            end=tomorrow + timedelta(hours=2),
        )

        manager = Contact.objects.create(user=user,  first_name='Gaara', last_name='???')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(
            subject_entity=manager, object_entity=customer,
            type_id=constants.REL_SUB_MANAGES,
        )

        create_rel(
            subject_entity=manager, object_entity=meeting,
            type_id=act_constants.REL_SUB_PART_2_ACTIVITY
        )
        create_rel(
            subject_entity=competitor, object_entity=meeting,
            type_id=act_constants.REL_SUB_ACTIVITY_SUBJECT,
        )
        self.assertEqual(1, len(self._get_neglected_orgas()))

    def test_neglected_brick07(self):
        "Inactive customers are not counted"
        mng_orga = Organisation.objects.all()[0]
        customer01 = self._build_customer_orga(mng_orga, 'Konoha')
        customer02 = self._build_customer_orga(mng_orga, 'Suna')
        Relation.objects.create(
            user=self.user, subject_entity=customer02,
            object_entity=mng_orga, type_id=constants.REL_SUB_INACTIVE,
        )
        self.assertListEqual([customer01], [*self._get_neglected_orgas()])

    def test_neglected_brick08(self):
        "Deleted customers are not counted."
        mng_orga = Organisation.objects.all()[0]
        customer = self._build_customer_orga(mng_orga, 'Konoha')
        self._build_customer_orga(mng_orga, 'Suna', is_deleted=True)
        self.assertListEqual([customer], [*self._get_neglected_orgas()])

    @staticmethod
    def _oldify(entity, days_delta):
        entity.created -= timedelta(days=days_delta)
        return entity

    def test_neglected_indicator01(self):
        "Young entity => special label."
        contact = self._oldify(
            Contact.objects.create(user=self.user, first_name='Gaara', last_name='???'),
            days_delta=10,
        )
        indicator = bricks.NeglectedContactIndicator(context={'today': now()}, contact=contact)
        self.assertEqual(_('Never contacted'), indicator.label)

    def test_neglected_indicator02(self):
        "regular label for neglected."
        user = self.user
        contact = self._oldify(
            Contact.objects.create(user=user, first_name='Gaara', last_name='???'),
            days_delta=16,
        )

        now_value = now()
        one_month_ago = now_value - timedelta(days=30)
        meeting = Activity.objects.create(
            user=user,
            type_id=act_constants.ACTIVITYTYPE_MEETING,
            title='meet01',
            start=one_month_ago,
            end=one_month_ago + timedelta(hours=2),
        )

        Relation.objects.create(
            user=user, subject_entity=contact, object_entity=meeting,
            type_id=act_constants.REL_SUB_PART_2_ACTIVITY,
        )

        indicator = bricks.NeglectedContactIndicator(
            context={'today': now_value}, contact=contact,
        )
        self.assertEqual(_('Not contacted since 15 days'), indicator.label)

    def test_neglected_indicator03(self):
        "Not neglected"
        user = self.user
        contact = self._oldify(
            Contact.objects.create(user=self.user, first_name='Gaara', last_name='???'),
            days_delta=16,
        )

        now_value = now()
        one_week_ago = now_value - timedelta(days=7)
        meeting = Activity.objects.create(
            user=user,
            type_id=act_constants.ACTIVITYTYPE_MEETING,
            title='meet01',
            start=one_week_ago,
            end=one_week_ago + timedelta(hours=2),
        )

        Relation.objects.create(
            user=user, subject_entity=contact, object_entity=meeting,
            type_id=act_constants.REL_SUB_PART_2_ACTIVITY,
        )

        indicator = bricks.NeglectedContactIndicator(
            context={'today': now_value}, contact=contact,
        )
        self.assertFalse(indicator.label)

    def test_neglected_indicator04(self):
        "User-contacts are ignored."
        user = self.user
        contact = self._oldify(user.linked_contact, days_delta=16)

        now_value = now()
        one_month_ago = now_value - timedelta(days=30)
        meeting = Activity.objects.create(
            user=user,
            type_id=act_constants.ACTIVITYTYPE_MEETING,
            title='meet01',
            start=one_month_ago,
            end=one_month_ago + timedelta(hours=2),
        )

        Relation.objects.create(
            user=user, subject_entity=contact, object_entity=meeting,
            type_id=act_constants.REL_SUB_PART_2_ACTIVITY,
        )

        indicator = bricks.NeglectedContactIndicator(
            context={'today': now_value}, contact=contact,
        )
        self.assertFalse(indicator.label)
