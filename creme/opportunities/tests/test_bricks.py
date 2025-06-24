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
        user = self.login_as_root_and_get()
        opp, target, emitter = self._create_opportunity_n_organisations(user=user, name='Opp#1')

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
        user = self.login_as_root_and_get()
        opp, target, emitter = self._create_opportunity_n_organisations(user=user, name='Opp#1')
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
        user = self.login_as_root_and_get()
        opp, target, emitter = self._create_opportunity_n_organisations(
            user=user, name='Opp#1', managed=False,
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
        user = self.login_as_root_and_get()

        brick_cls = bricks.OpportunityCardHatBrick
        self.assertEqual(5, bricks.ContactsSummary.displayed_contacts_number)

        opp1, target, emitter = self._create_opportunity_n_organisations(user=user, name='Opp#1')
        opp2 = Opportunity.objects.create(
            user=user, name='Opp#2', sales_phase=opp1.sales_phase,
            emitter=emitter, target=target,
        )

        create_contact = partial(get_contact_model().objects.create, user=user)
        contact1 = create_contact(first_name='Revy',  last_name='??')
        contact2 = create_contact(first_name='Rock',  last_name='??')
        contact3 = create_contact(first_name='Benny', last_name='??')
        contact4 = create_contact(first_name='Dutch', last_name='??')
        contact5 = create_contact(first_name='Balalaika', last_name='??', is_deleted=True)

        create_rel = partial(
            Relation.objects.create, user=user, type_id=constants.REL_OBJ_LINKED_CONTACT,
        )
        create_rel(subject_entity=opp1, object_entity=contact1)
        create_rel(subject_entity=opp1, object_entity=contact2)
        create_rel(subject_entity=opp2, object_entity=contact4)
        create_rel(subject_entity=opp1, object_entity=contact5)

        # ---
        summary = bricks.ContactsSummary()
        sum_ctxt = summary.get_context(entity=opp1, brick_context={'user': user})
        self.assertIsDict(sum_ctxt, length=2)
        self.assertEqual(
            'opportunities/bricks/frags/card-summary-contacts.html',
            sum_ctxt.get('template_name'),
        )
        self.assertCountEqual(
            [contact1, contact2],
            sum_ctxt.get('contacts').object_list,
        )

        # ---
        response = self.assertGET200(opp1.get_absolute_url())
        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=brick_cls)
        self.assertInstanceLink(brick_node, contact1)
        self.assertInstanceLink(brick_node, contact2)
        self.assertNoInstanceLink(brick_node, contact3)
        self.assertNoInstanceLink(brick_node, contact4)
        self.assertNoInstanceLink(brick_node, contact5)

    @skipIfCustomContact
    def test_hat_card02(self):
        "Too many contacts to display."
        user = self.login_as_root_and_get()

        brick_cls = bricks.OpportunityCardHatBrick

        old_contacts_number = bricks.ContactsSummary.displayed_contacts_number
        try:
            bricks.ContactsSummary.displayed_contacts_number = 1

            opp = self._create_opportunity_n_organisations(user=user, name='Opp#1')[0]

            create_contact = partial(get_contact_model().objects.create, user=user)
            contact1 = create_contact(first_name='Revy',  last_name='??')
            contact2 = create_contact(first_name='Rock',  last_name='??')

            create_rel = partial(
                Relation.objects.create,
                user=user, subject_entity=opp, type_id=constants.REL_OBJ_LINKED_CONTACT,
            )
            create_rel(object_entity=contact1)
            create_rel(object_entity=contact2)

            # ---
            summary = bricks.ContactsSummary()
            sum_ctxt = summary.get_context(entity=opp, brick_context={'user': user})
            self.assertCountEqual(
                [contact1],
                sum_ctxt.get('contacts').object_list,
            )

            # ---
            response = self.assertGET200(opp.get_absolute_url())
            tree = self.get_html_tree(response.content)
            brick_node = self.get_brick_node(tree, brick=brick_cls)
            self.assertInstanceLink(brick_node, contact1)
            self.assertNoInstanceLink(brick_node, contact2)
        finally:
            bricks.ContactsSummary.displayed_contacts_number = old_contacts_number

    @skipIfCustomProduct
    def test_linked_products(self):
        brick_cls = bricks.LinkedProductsBrick
        brick_cls.page_size = max(5, settings.BLOCK_SIZE)

        user = self.login_as_root_and_get()
        opp1, target, emitter = self._create_opportunity_n_organisations(user=user, name='Opp#1')
        opp2 = Opportunity.objects.create(
            user=user, name='Opp#2', sales_phase=opp1.sales_phase,
            emitter=emitter, target=target,
        )

        sub_cat = SubCategory.objects.all()[0]
        create_product = partial(
            products.get_product_model().objects.create,
            user=user, unit_price=Decimal('1.23'),
            category=sub_cat.category, sub_category=sub_cat,
        )
        product1 = create_product(name='Eva-00')
        product2 = create_product(name='Eva-01')
        product3 = create_product(name='Eva-02')
        product4 = create_product(name='Eva-03')
        product5 = create_product(name='Eva-04', is_deleted=True)

        create_rel = partial(
            Relation.objects.create, user=user, type_id=constants.REL_OBJ_LINKED_PRODUCT,
        )
        create_rel(subject_entity=opp1, object_entity=product1)
        create_rel(subject_entity=opp1, object_entity=product2)
        create_rel(subject_entity=opp2, object_entity=product4)
        create_rel(subject_entity=opp1, object_entity=product5)

        response = self.assertGET200(opp1.get_absolute_url())
        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=brick_cls)
        self.assertInstanceLink(brick_node, product1)
        self.assertInstanceLink(brick_node, product2)
        self.assertNoInstanceLink(brick_node, product3)
        self.assertNoInstanceLink(brick_node, product4)
        self.assertNoInstanceLink(brick_node, product5)

    @skipIfCustomService
    def test_linked_services(self):
        brick_cls = bricks.LinkedServicesBrick
        brick_cls.page_size = max(5, settings.BLOCK_SIZE)

        user = self.login_as_root_and_get()
        opp1, target, emitter = self._create_opportunity_n_organisations(user=user, name='Opp#1')
        opp2 = Opportunity.objects.create(
            user=user, name='Opp#2', sales_phase=opp1.sales_phase,
            emitter=emitter, target=target,
        )

        sub_cat = SubCategory.objects.all()[0]
        create_service = partial(
            products.get_service_model().objects.create,
            user=user, unit_price=Decimal('1.23'),
            category=sub_cat.category, sub_category=sub_cat,
        )
        service1 = create_service(name='Eva-00 support')
        service2 = create_service(name='Eva-01 support')
        service3 = create_service(name='Eva-02 support')
        service4 = create_service(name='Eva-03 support')
        service5 = create_service(name='Eva-04 support', is_deleted=True)

        create_rel = partial(
            Relation.objects.create, user=user, type_id=constants.REL_OBJ_LINKED_SERVICE,
        )
        create_rel(subject_entity=opp1, object_entity=service1)
        create_rel(subject_entity=opp1, object_entity=service2)
        create_rel(subject_entity=opp2, object_entity=service4)
        create_rel(subject_entity=opp1, object_entity=service5)

        response = self.assertGET200(opp1.get_absolute_url())
        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=brick_cls)
        self.assertInstanceLink(brick_node, service1)
        self.assertInstanceLink(brick_node, service2)
        self.assertNoInstanceLink(brick_node, service3)
        self.assertNoInstanceLink(brick_node, service4)
        self.assertNoInstanceLink(brick_node, service5)

    @skipIfCustomContact
    @parameterized.expand([
        (bricks.LinkedContactsBrick, constants.REL_OBJ_LINKED_CONTACT),
        (bricks.BusinessManagersBrick, constants.REL_OBJ_RESPONSIBLE),
    ])
    def test_linked_contacts(self, brick_cls, rtype_id):
        brick_cls.page_size = max(5, settings.BLOCK_SIZE)

        user = self.login_as_root_and_get()
        opp1, target, emitter = self._create_opportunity_n_organisations(user=user, name='Opp#1')
        opp2 = Opportunity.objects.create(
            user=user, name='Opp#2', sales_phase=opp1.sales_phase,
            emitter=emitter, target=target,
        )

        create_contact = partial(get_contact_model().objects.create, user=user)
        contact1 = create_contact(first_name='Revy',  last_name='??')
        contact2 = create_contact(first_name='Rock',  last_name='??')
        contact3 = create_contact(first_name='Benny', last_name='??')
        contact4 = create_contact(first_name='Dutch', last_name='??')
        contact5 = create_contact(first_name='Balalaika', last_name='??', is_deleted=True)

        create_rel = partial(Relation.objects.create, user=user, type_id=rtype_id)
        create_rel(subject_entity=opp1, object_entity=contact1)
        create_rel(subject_entity=opp1, object_entity=contact2)
        create_rel(subject_entity=opp2, object_entity=contact4)
        create_rel(subject_entity=opp1, object_entity=contact5)

        response = self.assertGET200(opp1.get_absolute_url())
        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=brick_cls)
        self.assertInstanceLink(brick_node, contact1)
        self.assertInstanceLink(brick_node, contact2)
        self.assertNoInstanceLink(brick_node, contact3)
        self.assertNoInstanceLink(brick_node, contact4)
        self.assertNoInstanceLink(brick_node, contact5)

    # TODO: test title (several cases)
    def test_targeting01(self):
        user = self.login_as_root_and_get()

        opp1, target, emitter = self._create_opportunity_n_organisations(user=user, name='Opp#1')
        Opportunity.objects.create(
            user=user, name='Opp#2', sales_phase=opp1.sales_phase,
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
                _('Actions'),
            ],
            self.get_brick_table_column_titles(brick_node),
        )

        rows = self.get_brick_table_rows(brick_node)
        self.assertEqual(2, len(rows))

        table_cells1 = rows[0].findall('.//td')
        self.assertEqual(6, len(table_cells1))
        # TODO: test content

    def test_targeting02(self):
        "Field 'Estimated sales' is hidden."
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Opportunity,
            descriptions=[('estimated_sales', {FieldsConfig.HIDDEN: True})],
        )

        _opp, target, _emitter = self._create_opportunity_n_organisations(user=user, name='Opp#1')

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
                _('Actions'),
            ],
            self.get_brick_table_column_titles(brick_node),
        )

        rows = self.get_brick_table_rows(brick_node)
        self.assertEqual(5, len(rows[0].findall('.//td')))
        # TODO: test content

    def test_targeting03(self):
        "Field 'Made sales' is hidden."
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Opportunity,
            descriptions=[('made_sales', {FieldsConfig.HIDDEN: True})],
        )

        _opp, target, _emitter = self._create_opportunity_n_organisations(user=user, name='Opp#1')

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
                _('Actions'),
            ],
            self.get_brick_table_column_titles(brick_node),
        )

        rows = self.get_brick_table_rows(brick_node)
        self.assertEqual(5, len(rows[0].findall('.//td')))
