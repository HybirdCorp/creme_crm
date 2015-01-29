# -*- coding: utf-8 -*-

try:
    from django.db.models.query import QuerySet

    from creme.creme_core.tests.forms.base import FieldTestCase
    from creme.creme_core.forms.widgets import DynamicSelect

    from creme.persons.models import Contact
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))

__all__ = ('DynamicSelectTestCase',)


class DynamicSelectTestCase(FieldTestCase):
    def test_options_list(self):
        select = DynamicSelect(options=[(1, 'A'), (2, 'B')])

        self.assertIsInstance(select.options, list)
        self.assertListEqual([(1, 'A'), (2, 'B')], select.choices)

    def test_options_queryset(self):
        self.login()

        select = DynamicSelect(options=Contact.objects.values_list('id', 'last_name'))

        Contact.objects.create(last_name='Doe', first_name='John', user=self.user)

        self.assertIsInstance(select.options, QuerySet)
        self.assertListEqual(list(Contact.objects.values_list('id', 'last_name')),
                             list(select.choices)
                            )

    def test_options_function(self):
        select = DynamicSelect(options=lambda: [(id, str(id)) for id in xrange(10)])

        self.assertTrue(callable(select.options))
        self.assertListEqual([(id, str(id)) for id in xrange(10)],
                             select.choices)

        self.assertListEqual([(id, str(id)) for id in xrange(10)],
                             select.choices)

    def test_options_generator(self):
        select = DynamicSelect(options=((id, str(id)) for id in xrange(10)))

        self.assertIsInstance(select.options, list)
        self.assertListEqual([(id, str(id)) for id in xrange(10)],
                             select.choices)

        self.assertListEqual([(id, str(id)) for id in xrange(10)],
                             select.choices)
