# -*- coding: utf-8 -*-

try:
    from django.db.models.query import QuerySet

    from ..fake_models import FakeContact as Contact
    from .base import FieldTestCase
    from creme.creme_core.forms.widgets import DynamicSelect, UnorderedMultipleChoiceWidget

    #from creme.persons.models import Contact
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


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


class UnorderedMultipleChoiceTestCase(FieldTestCase):
    def test_option_list(self):
        select = UnorderedMultipleChoiceWidget(choices=[(1, 'A'), (2, 'B')])
        self.assertEqual(2, select._choice_count())
        select.render('A', (2,), choices=select.choices)

    def test_option_group_list(self):
        select = UnorderedMultipleChoiceWidget(choices=[('Group A', ((1, 'A'), (2, 'B'))),
                                                        ('Group B', ((3, 'C'), (4, 'D'), (5, 'E'))),])
        self.assertEqual(5, select._choice_count())
        select.render('A', (3, 4,), choices=select.choices)

