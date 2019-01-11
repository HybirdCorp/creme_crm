# -*- coding: utf-8 -*-

try:
    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.tests.base import skipIfCustomContact

    from ..models import ActType, MarketSegment
    from ..constants import (REL_SUB_SOLD_BY, REL_OBJ_SOLD_BY,
            REL_SUB_COMPLETE_GOAL, PROP_IS_A_SALESMAN)
    from .base import Act, Contact
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class CommercialTestCase(CremeTestCase):
    ADD_SALESMAN_URL = reverse('commercial__create_salesman')
    SALESMEN_URL = reverse('commercial__list_salesmen')

    def test_populate(self):
        self.get_relationtype_or_fail(REL_SUB_SOLD_BY)
        self.get_relationtype_or_fail(REL_OBJ_SOLD_BY)
        self.get_relationtype_or_fail(REL_SUB_COMPLETE_GOAL, [], [Act])

        self.get_propertytype_or_fail(PROP_IS_A_SALESMAN, [Contact])

        self.assertEqual(3, ActType.objects.count())

        self.get_object_or_fail(MarketSegment, property_type=None)

    @skipIfCustomContact
    def test_salesman_create(self):
        user = self.login()

        url = self.ADD_SALESMAN_URL
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'persons/add_contact_form.html')

        context = response.context
        self.assertEqual(_('Create a salesman'), context.get('title'))
        self.assertEqual(_('Save the salesman'), context.get('submit_label'))

        first_name = 'John'
        last_name  = 'Doe'
        response = self.client.post(url, follow=True,
                                    data={'user':       user.pk,
                                          'first_name': first_name,
                                          'last_name':  last_name,
                                         }
                                   )
        self.assertNoFormError(response)

        salesmen = Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN)
        self.assertEqual(1, len(salesmen))

        salesman = salesmen[0]
        self.assertEqual(first_name, salesman.first_name)
        self.assertEqual(last_name,  salesman.last_name)

        self.assertRedirects(response, salesman.get_absolute_url())

    @skipIfCustomContact
    def test_salesman_listview01(self):
        self.login()

        self.assertFalse(Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN).exists())

        response = self.assertGET200(self.SALESMEN_URL)

        with self.assertNoException():
            salesmen_page = response.context['entities']

        self.assertEqual(1, salesmen_page.number)
        self.assertFalse(salesmen_page.paginator.count)

    @skipIfCustomContact
    def test_salesman_listview02(self):
        user = self.login()

        def add_salesman(first_name, last_name):
            self.client.post(self.ADD_SALESMAN_URL,
                             data={'user':       user.pk,
                                   'first_name': first_name,
                                   'last_name':  last_name,
                                  }
                            )

        add_salesman('first_name1', 'last_name1')
        add_salesman('first_name2', 'last_name2')
        salesmen = Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN)
        self.assertEqual(2, len(salesmen))

        response = self.assertGET200(self.SALESMEN_URL)

        with self.assertNoException():
            salesmen_page = response.context['entities']

        self.assertEqual(1, salesmen_page.number)
        self.assertEqual(2, salesmen_page.paginator.count)
        self.assertEqual(set(salesmen), set(salesmen_page.object_list))
