from django.apps import apps
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.persons.tests.base import skipIfCustomContact

from ..constants import (
    REL_OBJ_COMPLETE_GOAL,
    REL_OBJ_SOLD,
    REL_SUB_COMPLETE_GOAL,
    REL_SUB_SOLD,
    UUID_PROP_IS_A_SALESMAN,
)
from ..models import ActType, MarketSegment
from .base import Act, Contact, Organisation, Product, Service


class CommercialTestCase(CremeTestCase):
    ADD_SALESMAN_URL = reverse('commercial__create_salesman')
    SALESMEN_URL = reverse('commercial__list_salesmen')

    def test_populate(self):
        sold = self.get_relationtype_or_fail(
            REL_SUB_SOLD, [Contact, Organisation], [Product, Service],
        )
        self.assertEqual(REL_OBJ_SOLD, sold.symmetric_type_id)

        complete_goal = self.get_object_or_fail(RelationType, id=REL_SUB_COMPLETE_GOAL)
        self.assertEqual(REL_OBJ_COMPLETE_GOAL, complete_goal.symmetric_type_id)
        self.assertListEqual([Act], [*complete_goal.object_models])

        subject_models = {*complete_goal.subject_models}
        self.assertIn(Contact,      subject_models)
        self.assertIn(Organisation, subject_models)

        if apps.is_installed('creme.billing'):
            from creme import billing
            self.assertIn(billing.get_invoice_model(),     subject_models)
            self.assertIn(billing.get_quote_model(),       subject_models)
            self.assertIn(billing.get_sales_order_model(), subject_models)

            self.assertNotIn(billing.get_product_line_model(),  subject_models)
            self.assertNotIn(billing.get_service_line_model(),  subject_models)
            self.assertNotIn(billing.get_template_base_model(), subject_models)

        self.get_propertytype_or_fail(UUID_PROP_IS_A_SALESMAN, [Contact])

        self.assertEqual(3, ActType.objects.count())

        self.get_object_or_fail(MarketSegment, property_type=None)

    @skipIfCustomContact
    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_salesman_create01(self):
        user = self.login_as_root_and_get()

        url = self.ADD_SALESMAN_URL
        response = self.assertGET200(url)

        context = response.context
        self.assertEqual(_('Create a salesman'), context.get('title'))
        self.assertEqual(_('Save the salesman'), context.get('submit_label'))

        first_name = 'John'
        last_name = 'Doe'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user': user.pk,
                'first_name': first_name,
                'last_name': last_name,
            },
        )
        self.assertNoFormError(response)

        salesman = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.get_object_or_fail(
            CremeProperty, type__uuid=UUID_PROP_IS_A_SALESMAN, creme_entity=salesman.id,
        )

        self.assertRedirects(response, salesman.get_absolute_url())

    @skipIfCustomContact
    @override_settings(FORMS_RELATION_FIELDS=False)
    def test_salesman_create02(self):
        "No <properties> field."
        user = self.login_as_root_and_get()

        first_name = 'John'
        last_name = 'Smith'
        response = self.client.post(
            self.ADD_SALESMAN_URL,
            follow=True,
            data={
                'user': user.pk,
                'first_name': first_name,
                'last_name': last_name,
            },
        )
        self.assertNoFormError(response)

        salesman = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.get_object_or_fail(
            CremeProperty, type__uuid=UUID_PROP_IS_A_SALESMAN, creme_entity=salesman.id,
        )

    def test_salesman_create03(self):
        "Property type is disabled => error."
        self.login_as_root()

        ptype = self.get_object_or_fail(CremePropertyType, uuid=UUID_PROP_IS_A_SALESMAN)
        ptype.enabled = False
        ptype.save()

        self.assertGET409(self.ADD_SALESMAN_URL)

    @skipIfCustomContact
    def test_salesman_listview01(self):
        self.login_as_root()

        self.assertFalse(
            Contact.objects.filter(properties__type__uuid=UUID_PROP_IS_A_SALESMAN).exists()
        )

        response = self.assertGET200(self.SALESMEN_URL)

        with self.assertNoException():
            salesmen_page = response.context['page_obj']

        self.assertEqual(1, salesmen_page.number)
        self.assertFalse(salesmen_page.paginator.count)

    @skipIfCustomContact
    @override_settings(FORMS_RELATION_FIELDS=False)  # To avoid "properties" POST argument
    def test_salesman_listview02(self):
        user = self.login_as_root_and_get()

        def add_salesman(first_name, last_name):
            self.client.post(
                self.ADD_SALESMAN_URL,
                data={
                    'user': user.pk,
                    'first_name': first_name,
                    'last_name': last_name,
                },
            )

        add_salesman('first_name1', 'last_name1')
        add_salesman('first_name2', 'last_name2')
        salesmen = Contact.objects.filter(properties__type__uuid=UUID_PROP_IS_A_SALESMAN)
        self.assertEqual(2, len(salesmen))

        response = self.assertGET200(self.SALESMEN_URL)

        with self.assertNoException():
            salesmen_page = response.context['page_obj']

        self.assertEqual(1, salesmen_page.number)
        self.assertEqual(2, salesmen_page.paginator.count)
        self.assertCountEqual(salesmen, salesmen_page.object_list)
