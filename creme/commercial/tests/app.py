# -*- coding: utf-8 -*-

try:
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact

    from commercial.models import Act, ActType
    from commercial.constants import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('CommercialTestCase',)


class CommercialTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons', 'commercial')

    def test_populate(self):
        self.get_relationtype_or_fail(REL_SUB_SOLD_BY)
        self.get_relationtype_or_fail(REL_OBJ_SOLD_BY)
        self.get_relationtype_or_fail(REL_SUB_COMPLETE_GOAL, [], [Act])

        self.get_propertytype_or_fail(PROP_IS_A_SALESMAN, [Contact])

        self.assertEqual(3, ActType.objects.count())

    def test_salesman_create(self):
        self.login()

        url = '/commercial/salesman/add'
        self.assertGET200(url)

        first_name = 'John'
        last_name  = 'Doe'
        response = self.client.post(url, follow=True,
                                    data={'user':       self.user.pk,
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

    def test_salesman_listview01(self):
        self.login()

        self.assertFalse(Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN).exists())

        response = self.assertGET200('/commercial/salesmen')

        with self.assertNoException():
            salesmen_page = response.context['entities']

        self.assertEqual(1, salesmen_page.number)
        self.assertFalse(salesmen_page.paginator.count)

    def test_salesman_listview02(self):
        self.login()

        def add_salesman(first_name, last_name):
            self.client.post('/commercial/salesman/add',
                             data={'user':        self.user.pk,
                                   'first_name': 'first_name1',
                                   'last_name':   'last_name1',
                                  }
                            )

        add_salesman('first_name1', 'last_name1')
        add_salesman('first_name2', 'last_name2')
        salesmen = Contact.objects.filter(properties__type=PROP_IS_A_SALESMAN)
        self.assertEqual(2, len(salesmen))

        response = self.assertGET200('/commercial/salesmen')

        with self.assertNoException():
            salesmen_page = response.context['entities']

        self.assertEqual(1, salesmen_page.number)
        self.assertEqual(2, salesmen_page.paginator.count)
        self.assertEqual(set(salesmen), set(salesmen_page.object_list))

    def test_portal(self):
        self.login()
        self.assertGET200('/commercial/')
