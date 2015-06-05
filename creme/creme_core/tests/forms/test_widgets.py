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

    def test_render_options(self):
        select = DynamicSelect()
        self.assertEqual(u'<option value="%s">%s</option>' % (1, 'A'),
                         select.render_option([], 1, 'A'))

        self.assertEqual(u'<option value="%s" selected="selected">%s</option>' % (1, 'A'),
                         select.render_option(['1'], '1', 'A'))

    def test_render_options_choices(self):
        select = DynamicSelect()

        self.assertEqual(u'<option value="%s" disabled help="%s">%s</option>' % (1, 'is disabled', 'A'),
                         select.render_option(['2'], DynamicSelect.Choice(1, True, 'is disabled'), 'A'))

        self.assertEqual(u'<option value="%s" disabled selected="selected" help="%s">%s</option>' % (1, 'is disabled', 'A'),
                         select.render_option(['1'], DynamicSelect.Choice(1, True, 'is disabled'), 'A'))

        self.assertEqual(u'<option value="%s" selected="selected" help="%s">%s</option>' % (2, 'is enabled', 'B'),
                         select.render_option(['2'], DynamicSelect.Choice(2, False, 'is enabled'), 'B'))

    def test_render(self):
        select = DynamicSelect(options=[(1, 'A'), (2, 'B')])

        self.assertEqual(u'<select class="ui-creme-input ui-creme-widget widget-auto ui-creme-dselect" name="test" url="" widget="ui-creme-dselect">\n'
                           u'<option value="1">A</option>\n'
                           u'<option value="2" selected="selected">B</option>\n'
                         u'</select>',
                         select.render('test', 2))

        select = DynamicSelect(options=[(DynamicSelect.Choice(1, True, 'disabled'), 'A'),
                                        (DynamicSelect.Choice(2, False, 'item B'), 'B'),
                                        (DynamicSelect.Choice(3, False, 'item C'), 'C')])

        self.assertEqual(u'<select class="ui-creme-input ui-creme-widget widget-auto ui-creme-dselect" name="test" url="" widget="ui-creme-dselect">\n'
                           u'<option value="1" disabled help="disabled">A</option>\n'
                           u'<option value="2" selected="selected" help="item B">B</option>\n'
                           u'<option value="3" help="item C">C</option>\n'
                         u'</select>',
                         select.render('test', 2))

class UnorderedMultipleChoiceTestCase(FieldTestCase):
    def test_option_list(self):
        select = UnorderedMultipleChoiceWidget(choices=[(1, 'A'), (2, 'B')])
        self.assertEqual(2, select._choice_count())
        select.render('A', (2,), choices=select.choices)

        self.assertEqual(u'<option value="%s">%s</option>' % (1, 'A'),
                         select.render_option([], 1, 'A'))

        self.assertEqual(u'<option value="%s" selected="selected">%s</option>' % (1, 'A'),
                         select.render_option(['1'], '1', 'A'))

    def test_option_group_list(self):
        select = UnorderedMultipleChoiceWidget(choices=[('Group A', ((1, 'A'), (2, 'B'))),
                                                        ('Group B', ((3, 'C'), (4, 'D'), (5, 'E'))),])
        self.assertEqual(5, select._choice_count())
        select.render('A', (3, 4,), choices=select.choices)

    def test_render_options_choices(self):
        select = UnorderedMultipleChoiceWidget()

        self.assertEqual(u'<option value="%s" disabled help="%s">%s</option>' % (1, 'is disabled', 'A'),
                         select.render_option(['2'], UnorderedMultipleChoiceWidget.Choice(1, True, 'is disabled'), 'A'))

        self.assertEqual(u'<option value="%s" disabled selected="selected" help="%s">%s</option>' % (1, 'is disabled', 'A'),
                         select.render_option(['1'], UnorderedMultipleChoiceWidget.Choice(1, True, 'is disabled'), 'A'))

        self.assertEqual(u'<option value="%s" selected="selected" help="%s">%s</option>' % (2, 'is enabled', 'B'),
                         select.render_option(['2'], UnorderedMultipleChoiceWidget.Choice(2, False, 'is enabled'), 'B'))

