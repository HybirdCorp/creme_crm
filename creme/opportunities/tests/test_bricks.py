from decimal import Decimal
from functools import partial

from django.conf import settings
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme import products
from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.models import (
    BrickDetailviewLocation,
    FieldsConfig,
    Relation,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.opportunities import bricks, constants
from creme.persons import get_contact_model
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)
from creme.products.models import SubCategory
from creme.products.tests.base import skipIfCustomProduct, skipIfCustomService

from .base import (
    OpportunitiesBaseTestCase,
    Opportunity,
    Organisation,
    skipIfCustomOpportunity,
)


@skipIfCustomOpportunity
@skipIfCustomOrganisation
class BricksTestCase(BrickTestCaseMixin, OpportunitiesBaseTestCase):
    # TODO: OpportunityBrick
    def test_basic(self):
        self.login()
        opp, target, emitter = self._create_opportunity_n_organisations(name='Opp#1')

        response1 = self.assertGET200(opp.get_absolute_url())
        tree1 = self.get_html_tree(response1.content)
        self.get_brick_node(tree1, brick=bricks.OppTotalBrick)  # TODO: improve tests...
        self.assertNoBrick(tree1, brick_id=MODELBRICK_ID)

        # ---
        BrickDetailviewLocation.objects.create_for_model_brick(
            model=Opportunity, order=1, zone=BrickDetailviewLocation.RIGHT,
        )
        response2 = self.assertGET200(opp.get_absolute_url())
        tree2 = self.get_html_tree(response2.content)
        brick_node = self.get_brick_node(tree2, brick=MODELBRICK_ID)
        self.assertEqual(
            _('Information on the opportunity'),
            self.get_brick_title(brick_node),
        )

    def test_target01(self):
        "Source is displayed."
        self.login()
        opp, target, emitter = self._create_opportunity_n_organisations(name='Opp#1')
        self.assertEqual(
            2, Organisation.objects.filter(is_managed=True, is_deleted=False).count(),
        )

        response = self.assertGET200(opp.get_absolute_url())
        tree = self.get_html_tree(response.content)

        brick_node = self.get_brick_node(tree, brick=bricks.OppTargetBrick)
        self.assertInstanceLink(brick_node, target)
        self.assertInstanceLink(brick_node, emitter)

    def test_target02(self):
        "Source is not displayed."
        self.login()
        opp, target, emitter = self._create_opportunity_n_organisations(
            name='Opp#1', managed=False,
        )
        self.assertEqual(
            1, Organisation.objects.filter(is_managed=True, is_deleted=False).count(),
        )

        response = self.assertGET200(opp.get_absolute_url())
        tree = self.get_html_tree(response.content)

        brick_node = self.get_brick_node(tree, brick=bricks.OppTargetBrick)
        self.assertInstanceLink(brick_node, target)
        self.assertNoInstanceLink(brick_node, emitter)

    @skipIfCustomContact
    def test_hat_card01(self):
        "All contacts can be displayed."
        user = self.login()

        brick_cls = bricks.OpportunityCardHatBrick
        self.assertEqual(5, brick_cls.displayed_contacts_number)

        opp01, target, emitter = self._create_opportunity_n_organisations(name='Opp#1')
        opp02 = Opportunity.objects.create(
            user=user, name='Opp#2', sales_phase=opp01.sales_phase,
            emitter=emitter, target=target,
        )

        create_contact = partial(get_contact_model().objects.create, user=user)
        contact01 = create_contact(first_name='Revy',  last_name='??')
        contact02 = create_contact(first_name='Rock',  last_name='??')
        contact03 = create_contact(first_name='Benny', last_name='??')
        contact04 = create_contact(first_name='Dutch', last_name='??')
        contact05 = create_contact(first_name='Balalaika', last_name='??', is_deleted=True)

        create_rel = partial(
            Relation.objects.create, user=user, type_id=constants.REL_OBJ_LINKED_CONTACT,
        )
        create_rel(subject_entity=opp01, object_entity=contact01)
        create_rel(subject_entity=opp01, object_entity=contact02)
        create_rel(subject_entity=opp02, object_entity=contact04)
        create_rel(subject_entity=opp01, object_entity=contact05)

        response = self.assertGET200(opp01.get_absolute_url())
        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=brick_cls)
        self.assertInstanceLink(brick_node, contact01)
        self.assertInstanceLink(brick_node, contact02)
        self.assertNoInstanceLink(brick_node, contact03)
        self.assertNoInstanceLink(brick_node, contact04)
        self.assertNoInstanceLink(brick_node, contact05)

    @skipIfCustomContact
    def test_hat_card02(self):
        "Too many contacts to display."
        user = self.login()

        brick_cls = bricks.OpportunityCardHatBrick
        brick_cls.displayed_contacts_number = 1

        opp = self._create_opportunity_n_organisations(name='Opp#1')[0]

        create_contact = partial(get_contact_model().objects.create, user=user)
        contact01 = create_contact(first_name='Revy',  last_name='??')
        contact02 = create_contact(first_name='Rock',  last_name='??')

        create_rel = partial(
            Relation.objects.create,
            user=user, subject_entity=opp, type_id=constants.REL_OBJ_LINKED_CONTACT,
        )
        create_rel(object_entity=contact01)
        create_rel(object_entity=contact02)

        response = self.assertGET200(opp.get_absolute_url())
        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=brick_cls)
        self.assertInstanceLink(brick_node, contact01)
        self.assertNoInstanceLink(brick_node, contact02)

    @skipIfCustomProduct
    def test_linked_products(self):
        brick_cls = bricks.LinkedProductsBrick
        brick_cls.page_size = max(5, settings.BLOCK_SIZE)

        user = self.login()
        opp01, target, emitter = self._create_opportunity_n_organisations(name='Opp#1')
        opp02 = Opportunity.objects.create(
            user=user, name='Opp#2', sales_phase=opp01.sales_phase,
            emitter=emitter, target=target,
        )

        sub_cat = SubCategory.objects.all()[0]
        create_product = partial(
            products.get_product_model().objects.create,
            user=user, unit_price=Decimal('1.23'),
            category=sub_cat.category, sub_category=sub_cat,
        )
        product01 = create_product(name='Eva00')
        product02 = create_product(name='Eva01')
        product03 = create_product(name='Eva02')
        product04 = create_product(name='Eva03')
        product05 = create_product(name='Eva04', is_deleted=True)

        create_rel = partial(
            Relation.objects.create, user=user, type_id=constants.REL_OBJ_LINKED_PRODUCT,
        )
        create_rel(subject_entity=opp01, object_entity=product01)
        create_rel(subject_entity=opp01, object_entity=product02)
        create_rel(subject_entity=opp02, object_entity=product04)
        create_rel(subject_entity=opp01, object_entity=product05)

        response = self.assertGET200(opp01.get_absolute_url())
        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=brick_cls)
        self.assertInstanceLink(brick_node, product01)
        self.assertInstanceLink(brick_node, product02)
        self.assertNoInstanceLink(brick_node, product03)
        self.assertNoInstanceLink(brick_node, product04)
        self.assertNoInstanceLink(brick_node, product05)

    @skipIfCustomService
    def test_linked_services(self):
        brick_cls = bricks.LinkedServicesBrick
        brick_cls.page_size = max(5, settings.BLOCK_SIZE)

        user = self.login()
        opp01, target, emitter = self._create_opportunity_n_organisations(name='Opp#1')
        opp02 = Opportunity.objects.create(
            user=user, name='Opp#2', sales_phase=opp01.sales_phase,
            emitter=emitter, target=target,
        )

        sub_cat = SubCategory.objects.all()[0]
        create_service = partial(
            products.get_service_model().objects.create,
            user=user, unit_price=Decimal('1.23'),
            category=sub_cat.category, sub_category=sub_cat,
        )
        service01 = create_service(name='Eva00 support')
        service02 = create_service(name='Eva01 support')
        service03 = create_service(name='Eva02 support')
        service04 = create_service(name='Eva03 support')
        service05 = create_service(name='Eva04 support', is_deleted=True)

        create_rel = partial(
            Relation.objects.create, user=user, type_id=constants.REL_OBJ_LINKED_SERVICE,
        )
        create_rel(subject_entity=opp01, object_entity=service01)
        create_rel(subject_entity=opp01, object_entity=service02)
        create_rel(subject_entity=opp02, object_entity=service04)
        create_rel(subject_entity=opp01, object_entity=service05)

        response = self.assertGET200(opp01.get_absolute_url())
        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=brick_cls)
        self.assertInstanceLink(brick_node, service01)
        self.assertInstanceLink(brick_node, service02)
        self.assertNoInstanceLink(brick_node, service03)
        self.assertNoInstanceLink(brick_node, service04)
        self.assertNoInstanceLink(brick_node, service05)

    @skipIfCustomContact
    @parameterized.expand([
        (bricks.LinkedContactsBrick, constants.REL_OBJ_LINKED_CONTACT),
        (bricks.BusinessManagersBrick, constants.REL_OBJ_RESPONSIBLE),
    ])
    def test_linked_contacts(self, brick_cls, rtype_id):
        brick_cls.page_size = max(5, settings.BLOCK_SIZE)

        user = self.login()
        opp01, target, emitter = self._create_opportunity_n_organisations(name='Opp#1')
        opp02 = Opportunity.objects.create(
            user=user, name='Opp#2', sales_phase=opp01.sales_phase,
            emitter=emitter, target=target,
        )

        create_contact = partial(get_contact_model().objects.create, user=user)
        contact01 = create_contact(first_name='Revy',  last_name='??')
        contact02 = create_contact(first_name='Rock',  last_name='??')
        contact03 = create_contact(first_name='Benny', last_name='??')
        contact04 = create_contact(first_name='Dutch', last_name='??')
        contact05 = create_contact(first_name='Balalaika', last_name='??', is_deleted=True)

        create_rel = partial(Relation.objects.create, user=user, type_id=rtype_id)
        create_rel(subject_entity=opp01, object_entity=contact01)
        create_rel(subject_entity=opp01, object_entity=contact02)
        create_rel(subject_entity=opp02, object_entity=contact04)
        create_rel(subject_entity=opp01, object_entity=contact05)

        response = self.assertGET200(opp01.get_absolute_url())
        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=brick_cls)
        self.assertInstanceLink(brick_node, contact01)
        self.assertInstanceLink(brick_node, contact02)
        self.assertNoInstanceLink(brick_node, contact03)
        self.assertNoInstanceLink(brick_node, contact04)
        self.assertNoInstanceLink(brick_node, contact05)

    # TODO: test title (several cases)
    def test_targeting01(self):
        user = self.login()

        opp01, target, emitter = self._create_opportunity_n_organisations(name='Opp#1')
        Opportunity.objects.create(
            user=user, name='Opp#2', sales_phase=opp01.sales_phase,
            emitter=emitter, target=target,
        )

        response = self.assertGET200(target.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=bricks.TargetingOpportunitiesBrick,
        )

        self.assertListEqual(
            [
                _('Name'),
                _('Sales phase'),
                _('Estimated sales'),
                _('Made sales'),
                _('Action'),
            ],
            self.get_brick_table_column_titles(brick_node),
        )

        rows = self.get_brick_table_rows(brick_node)
        self.assertEqual(2, len(rows))

        table_cells1 = rows[0].findall('.//td')
        self.assertEqual(5, len(table_cells1))
        # TODO: test content

    def test_targeting02(self):
        "Field 'Estimated sales' is hidden."
        self.login()

        FieldsConfig.objects.create(
            content_type=Opportunity,
            descriptions=[('estimated_sales', {FieldsConfig.HIDDEN: True})],
        )

        _opp, target, _emitter = self._create_opportunity_n_organisations(name='Opp#1')

        response = self.assertGET200(target.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=bricks.TargetingOpportunitiesBrick,
        )

        self.assertListEqual(
            [
                _('Name'),
                _('Sales phase'),
                # _('Estimated sales'),
                _('Made sales'),
                _('Action'),
            ],
            self.get_brick_table_column_titles(brick_node),
        )

        rows = self.get_brick_table_rows(brick_node)
        self.assertEqual(4, len(rows[0].findall('.//td')))
        # TODO: test content

    def test_targeting03(self):
        "Field 'Made sales' is hidden."
        self.login()

        FieldsConfig.objects.create(
            content_type=Opportunity,
            descriptions=[('made_sales', {FieldsConfig.HIDDEN: True})],
        )

        _opp, target, _emitter = self._create_opportunity_n_organisations(name='Opp#1')

        response = self.assertGET200(target.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=bricks.TargetingOpportunitiesBrick,
        )

        self.assertListEqual(
            [
                _('Name'),
                _('Sales phase'),
                _('Estimated sales'),
                # _('Made sales'),
                _('Action'),
            ],
            self.get_brick_table_column_titles(brick_node),
        )

        rows = self.get_brick_table_rows(brick_node)
        self.assertEqual(4, len(rows[0].findall('.//td')))
