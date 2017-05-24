# -*- coding: utf-8 -*-

try:
    from json import dumps as json_dump

    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse
    from django.db.models.query import QuerySet
    from django.forms.widgets import Select
    from django.utils.html import escape
    from django.utils.translation import ugettext as _, pgettext

    from ..fake_models import FakeContact, FakeCivility
    from .base import FieldTestCase
    from creme.creme_core.forms.widgets import (ActionButtonList,
        DynamicSelect,
        EntityCreatorWidget,
        EntitySelector,
        UnorderedMultipleChoiceWidget)
    from creme.creme_core.utils.url import TemplateURLBuilder
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class DynamicSelectTestCase(FieldTestCase):
    def test_options_list(self):
        select = DynamicSelect(options=[(1, 'A'), (2, 'B')])

        self.assertIsInstance(select.options, list)
        self.assertListEqual([(1, 'A'), (2, 'B')], select.choices)

    def test_options_queryset(self):
        user = self.login()
        FakeContact.objects.create(last_name='Doe', first_name='John', user=user)

        select = DynamicSelect(options=FakeContact.objects.values_list('id', 'last_name'))
        self.assertIsInstance(select.options, QuerySet)
        self.assertListEqual(list(FakeContact.objects.values_list('id', 'last_name')),
                             list(select.choices)
                            )

    def test_options_function(self):
        select = DynamicSelect(options=lambda: [(id, str(id)) for id in xrange(10)])

        self.assertTrue(callable(select.options))
        self.assertListEqual([(id_, str(id_)) for id_ in xrange(10)],
                             select.choices)

        self.assertListEqual([(id_, str(id_)) for id_ in xrange(10)],
                             select.choices)

    def test_options_generator(self):
        select = DynamicSelect(options=((id_, str(id_)) for id_ in xrange(10)))

        self.assertIsInstance(select.options, list)
        self.assertListEqual([(id_, str(id_)) for id_ in xrange(10)],
                             select.choices)

        self.assertListEqual([(id_, str(id_)) for id_ in xrange(10)],
                             select.choices)

    def test_render_options(self):
        select = DynamicSelect()
        self.assertEqual(u'<option value="%s">%s</option>' % (1, 'A'),
                         select.render_option([], 1, 'A'))

        self.assertEqual(u'<option value="%s" selected="selected">%s</option>' % (1, 'A'),
                         select.render_option(['1'], '1', 'A'))

    def test_render_options_choices(self):
        render_option = DynamicSelect().render_option
        Choice = DynamicSelect.Choice

        self.assertEqual(u'<option value="%s" disabled help="%s">%s</option>' % (1, 'is disabled', 'A'),
                         render_option(['2'], Choice(1, True, 'is disabled'), 'A')
                        )

        self.assertEqual(u'<option value="%s" disabled selected="selected" help="%s">%s</option>' % (
                                1, 'is disabled', 'A',
                            ),
                         render_option(['1'], Choice(1, True, 'is disabled'), 'A')
                        )

        self.assertEqual(u'<option value="%s" selected="selected" help="%s">%s</option>' % (
                                2, 'is enabled', 'B',
                            ),
                         render_option(['2'], Choice(2, False, 'is enabled'), 'B')
                        )

    def test_render(self):
        select = DynamicSelect(options=[(1, 'A'), (2, 'B')])
        self.assertHTMLEqual('<select class="ui-creme-input ui-creme-widget widget-auto ui-creme-dselect" '
                                     'name="test" url="" widget="ui-creme-dselect">'
                               '<option value="1">A</option>'
                               '<option value="2" selected="selected">B</option>'
                             '</select>',
                             select.render('test', 2)
                            )

        Choice = DynamicSelect.Choice
        select = DynamicSelect(options=[(Choice(1, True, 'disabled'), 'A'),
                                        (Choice(2, False, 'item B'), 'B'),
                                        (Choice(3, False, 'item C'), 'C'),
                                       ],
                              )
        self.assertHTMLEqual('<select class="ui-creme-input ui-creme-widget widget-auto ui-creme-dselect" '
                                     'name="test" url="" widget="ui-creme-dselect">'
                               '<option value="1" disabled help="disabled">A</option>'
                               '<option value="2" selected="selected" help="item B">B</option>'
                               '<option value="3" help="item C">C</option>'
                             '</select>',
                             select.render('test', 2)
                            )


class UnorderedMultipleChoiceTestCase(FieldTestCase):
    def setUp(self):
        super(UnorderedMultipleChoiceTestCase, self).setUp()
        self.maxDiff = None

    def test_render_options(self):
        select = UnorderedMultipleChoiceWidget(choices=[(1, 'A'), (2, 'B')])
        self.assertEqual(2, select._choice_count())

        self.assertEqual(u'<option value="%s">%s</option>' % (1, 'A'),
                         select.render_option([], 1, 'A')
                        )

        self.assertEqual(u'<option value="%s" selected="selected">%s</option>' % (1, 'A'),
                         select.render_option(['1'], '1', 'A')
                        )

        html = '''<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
                       style="" widget="ui-creme-checklistselect">
    <select multiple="multiple" class="ui-creme-input" name="A">
        <option value="1">A</option>
        <option value="2" selected="selected">B</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all hidden">%(check_all)s</a>
        <a type="button" class="checklist-check-none hidden">%(check_none)s</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content  "></ul></div>
</div>''' % {
            'check_all':  _(u'Check all'),
            'check_none': _(u'Check none'),
        }
        self.assertHTMLEqual(html, select.render('A', (2,)))

    def test_render_options_extra(self):
        select = UnorderedMultipleChoiceWidget(choices=[(1, 'A'), (2, 'B')])
        self.assertEqual(2, select._choice_count())

        self.assertEqual(u'<option value="%s">%s</option>' % (1, 'A'),
                         select.render_option([], 1, 'A')
                        )

        self.assertEqual(u'<option value="%s" selected="selected">%s</option>' % (1, 'A'),
                         select.render_option(['1'], '1', 'A')
                        )

        html = '''<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
                       style="" widget="ui-creme-checklistselect">
    <select multiple="multiple" class="ui-creme-input" name="A">
        <option value="1">A</option>
        <option value="2">B</option>
        <option value="3" selected="selected">C</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all hidden">%(check_all)s</a>
        <a type="button" class="checklist-check-none hidden">%(check_none)s</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content  "></ul></div>
</div>''' % {
            'check_all':  _(u'Check all'),
            'check_none': _(u'Check none'),
        }
        self.assertHTMLEqual(html, select.render('A', (3,), choices=[(3, 'C')]))

    def test_render_option_groups(self):
        select = UnorderedMultipleChoiceWidget(choices=[('Group A', ((1, 'A'), (2, 'B'))),
                                                        ('Group B', ((3, 'C'), (4, 'D'), (5, 'E'))),
                                                       ],
                                              )
        self.assertEqual(5, select._choice_count())

        html = u'''<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
                        style="" widget="ui-creme-checklistselect" >
    <select multiple="multiple" class="ui-creme-input" name="A">
        <optgroup label="Group A">
            <option value="1">A</option>
            <option value="2">B</option>
        </optgroup>
        <optgroup label="Group B">
            <option value="3" selected="selected">C</option>
            <option value="4" selected="selected">D</option>
            <option value="5">E</option>
        </optgroup>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all">%(check_all)s</a>
        <a type="button" class="checklist-check-none">%(check_none)s</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content  "></ul></div>
</div>''' % {
            'check_all':  _(u'Check all'),
            'check_none': _(u'Check none'),
        }
        self.assertHTMLEqual(html, select.render('A', (3, 4,)))

    def test_render_viewless(self):
        select = UnorderedMultipleChoiceWidget(choices=[(1, 'A'), (2, 'B')], viewless=True)
        self.assertEqual(2, select._choice_count())

        html = '''<div class="ui-creme-widget widget-auto ui-creme-checklistselect" less
                       style="" widget="ui-creme-checklistselect">
    <select multiple="multiple" class="ui-creme-input" name="A">
        <option value="1">A</option>
        <option value="2" selected="selected">B</option>
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all hidden">%(check_all)s</a>
        <a type="button" class="checklist-check-none hidden">%(check_none)s</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content  "></ul></div>
    <div class="checklist-footer"><a class="checklist-toggle-less">%(viewless_lbl)s</a></div>
</div>''' % {
            'check_all':  _(u'Check all'),
            'check_none': _(u'Check none'),
            'viewless_lbl': _(u'More'),
        }
        self.assertHTMLEqual(html, select.render('A', (2,)))

    def test_render_options_choices(self):
        select = UnorderedMultipleChoiceWidget()
        Choice = UnorderedMultipleChoiceWidget.Choice
        self.assertEqual(u'<option value="%s" disabled help="%s">%s</option>' % (
                                1, 'is disabled', 'A',
                            ),
                         select.render_option(['2'], Choice(1, True, 'is disabled'), 'A')
                        )
        self.assertEqual(u'<option value="%s" disabled selected="selected" help="%s">%s</option>' % (
                                1, 'is disabled', 'A',
                            ),
                         select.render_option(['1'], Choice(1, True, 'is disabled'), 'A')
                        )
        self.assertEqual(u'<option value="%s" selected="selected" help="%s">%s</option>' % (
                                2, 'is enabled', 'B',
                            ),
                         select.render_option(['2'], Choice(2, False, 'is enabled'), 'B')
                        )

    def test_build_header_filtertype(self):
        select = UnorderedMultipleChoiceWidget()
        self.assertIsNone(select._build_filtertype(0))
        self.assertIsNone(select._build_filtertype(5))
        self.assertEqual('search', select._build_filtertype(10))
        self.assertEqual('search', select._build_filtertype(20))
        self.assertEqual('filter', select._build_filtertype(30))
        self.assertEqual('filter', select._build_filtertype(100))

        select = UnorderedMultipleChoiceWidget(filtertype='search')
        self.assertEqual('search', select._build_filtertype(0))
        self.assertEqual('search', select._build_filtertype(5))
        self.assertEqual('search', select._build_filtertype(10))
        self.assertEqual('search', select._build_filtertype(20))
        self.assertEqual('search', select._build_filtertype(30))
        self.assertEqual('search', select._build_filtertype(100))

    def test_render_header_checkall(self):
        select = UnorderedMultipleChoiceWidget()
        self.assertHTMLEqual('<div class="checklist-header">'
                                 '<a type="button" class="checklist-check-all hidden">%(check_all)s</a>'
                                 '<a type="button" class="checklist-check-none hidden">%(check_none)s</a>'
                             '</div>' % {
                                 'check_all':  _(u'Check all'),
                                 'check_none': _(u'Check none'),
                             }, select._render_header({'checkall': True}, None, 1))

        self.assertHTMLEqual('<div class="checklist-header">'
                                 '<a type="button" class="checklist-check-all">%(check_all)s</a>'
                                 '<a type="button" class="checklist-check-none">%(check_none)s</a>'
                             '</div>' % {
                                 'check_all':  _(u'Check all'),
                                 'check_none': _(u'Check none'),
                             }, select._render_header({'checkall': True}, None, 3))

        self.assertHTMLEqual('<div class="checklist-header"></div>',
                             select._render_header({'checkall': False}, None, 3))

    def test_render_header_search(self):
        select = UnorderedMultipleChoiceWidget()
        self.assertHTMLEqual('<div class="checklist-header">'
                                 '<a type="button" class="checklist-check-all hidden">%(check_all)s</a>'
                                 '<a type="button" class="checklist-check-none hidden">%(check_none)s</a>'
                                 '<input type="search" class="checklist-filter" placeholder="%(filter_lbl)s">'
                             '</div>' % {
                                 'check_all':  _(u'Check all'),
                                 'check_none': _(u'Check none'),
                                 'filter_lbl': pgettext('creme_core-noun', 'Search').upper(),
                             }, select._render_header({'checkall': True}, 'search', 1))

        self.assertHTMLEqual('<div class="checklist-header">'
                                 '<a type="button" class="checklist-check-all">%(check_all)s</a>'
                                 '<a type="button" class="checklist-check-none">%(check_none)s</a>'
                                 '<input type="search" class="checklist-filter" placeholder="%(filter_lbl)s">'
                             '</div>' % {
                                 'check_all':  _(u'Check all'),
                                 'check_none': _(u'Check none'),
                                 'filter_lbl': pgettext('creme_core-noun', 'Search').upper(),
                             }, select._render_header({'checkall': True}, 'search', 3))

    def test_render_header_filter(self):
        select = UnorderedMultipleChoiceWidget()
        self.assertHTMLEqual('<div class="checklist-header">'
                                 '<a type="button" class="checklist-check-all hidden">%(check_all)s</a>'
                                 '<a type="button" class="checklist-check-none hidden">%(check_none)s</a>'
                                 '<input type="search" class="checklist-filter" placeholder="%(filter_lbl)s">'
                             '</div>' % {
                                 'check_all':  _(u'Check all'),
                                 'check_none': _(u'Check none'),
                                 'filter_lbl': _('Filter').upper(),
                             }, select._render_header({'checkall': True}, 'filter', 1))

        self.assertHTMLEqual('<div class="checklist-header">'
                                 '<a type="button" class="checklist-check-all">%(check_all)s</a>'
                                 '<a type="button" class="checklist-check-none">%(check_none)s</a>'
                                 '<input type="search" class="checklist-filter" placeholder="%(filter_lbl)s">'
                             '</div>' % {
                                 'check_all':  _(u'Check all'),
                                 'check_none': _(u'Check none'),
                                 'filter_lbl': _('Filter').upper(),
                             }, select._render_header({'checkall': True}, 'filter', 3))

    def test_render_header_creation(self):
        select = UnorderedMultipleChoiceWidget(creation_url='/add', creation_allowed=True)
        self.assertHTMLEqual('<div class="checklist-header">'
                                 '<a type="button" class="checklist-check-all hidden">%(check_all)s</a>'
                                 '<a type="button" class="checklist-check-none hidden">%(check_none)s</a>'
                                 '<a type="button" class="checklist-create" href="%(create_url)s">%(create_lbl)s</a>'
                             '</div>'  % {
                                 'check_all':  _(u'Check all'),
                                 'check_none': _(u'Check none'),
                                 'create_url': '/add',
                                 'create_lbl': _(u'Create'),
                             }, select._render_header({'checkall': True}, None, 1))

        self.assertHTMLEqual('<div class="checklist-header">'
                                 '<a type="button" class="checklist-check-all">%(check_all)s</a>'
                                 '<a type="button" class="checklist-check-none">%(check_none)s</a>'
                                 '<a type="button" class="checklist-create" href="%(create_url)s">%(create_lbl)s</a>'
                             '</div>' % {
                                 'check_all':  _(u'Check all'),
                                 'check_none': _(u'Check none'),
                                 'create_url': '/add',
                                 'create_lbl': _(u'Create'),
                             }, select._render_header({'checkall': True}, None, 3))

    def test_render_header_creation_disabled(self):
        select = UnorderedMultipleChoiceWidget(creation_url='/add')

        self.assertHTMLEqual('<div class="checklist-header">'
                                 '<a type="button" class="checklist-check-all hidden">%(check_all)s</a>'
                                 '<a type="button" class="checklist-check-none hidden">%(check_none)s</a>'
                                 '<a type="button" class="checklist-create" href="%(create_url)s" disabled>%(create_lbl)s</a>'
                             '</div>'  % {
                                 'check_all':  _(u'Check all'),
                                 'check_none': _(u'Check none'),
                                 'create_url': '/add',
                                 'create_lbl': _(u'Create'),
                             }, select._render_header({'checkall': True}, None, 1))

        self.assertHTMLEqual('<div class="checklist-header">'
                                 '<a type="button" class="checklist-check-all">%(check_all)s</a>'
                                 '<a type="button" class="checklist-check-none">%(check_none)s</a>'
                                 '<a type="button" class="checklist-create" href="%(create_url)s" disabled>%(create_lbl)s</a>'
                             '</div>' % {
                                 'check_all':  _(u'Check all'),
                                 'check_none': _(u'Check none'),
                                 'create_url': '/add',
                                 'create_lbl': _(u'Create'),
                             }, select._render_header({'checkall': True}, None, 3))

    def test_render_empty(self):
        select = UnorderedMultipleChoiceWidget(creation_url='/add')

        self.assertFalse(select.creation_allowed)
        self.assertHTMLEqual(_(u'No choice available.'), select.render('field', 1, {'checkall': True}))

    def test_render_empty_with_creation(self):
        select = UnorderedMultipleChoiceWidget(creation_url='/add', creation_allowed=True)

        self.assertTrue(select.creation_allowed)
        html = u'''<div class="ui-creme-widget widget-auto ui-creme-checklistselect"
                        style="" widget="ui-creme-checklistselect" >
    <select multiple="multiple" class="ui-creme-input" name="field">
    </select>
    <span class="checklist-counter"></span>
    <div class="checklist-header">
        <a type="button" class="checklist-check-all hidden">%(check_all)s</a>
        <a type="button" class="checklist-check-none hidden">%(check_none)s</a>
        <a type="button" class="checklist-create" href="%(create_url)s">%(create_lbl)s</a>
    </div>
    <div class="checklist-body"><ul class="checklist-content  "></ul></div>
</div>''' % {
            'check_all':  _(u'Check all'),
            'check_none': _(u'Check none'),
            'create_url': '/add',
            'create_lbl': _(u'Create'),
        }

        self.assertHTMLEqual(html, select.render('field', (), attrs={'checkall': True}))


class ActionButtonListTestCase(FieldTestCase):
    def setUp(self):
        self.maxDiff = None

    def test_render_action(self):
        widget = ActionButtonList(Select(choices=[(1, 'A'), (2, 'B')]))

        html = '''<li>
    <button class="ui-creme-actionbutton" name="action_a" type="button" disabled=""
            title="Do action A" alt="Do action A"
            arg_A="12" arg_B="B">Action A</button>
</li>'''
        self.assertHTMLEqual(html,
                             widget._render_action('action_a', 'Action A', enabled=False, title='Do action A',
                                                   arg_A=12, arg_B='B'
                                                  )
                            )

    def test_render_empty_action_list(self):
        widget = ActionButtonList(Select(choices=[(1, 'A'), (2, 'B')]))

        html = u'''<ul class="ui-layout hbox ui-creme-widget widget-auto ui-creme-actionbuttonlist" style="" widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <select name="field">
            <option value="1">A</option>
            <option value="2" selected="selected">B</option>
        </select>
    </li>
</ul>'''
        self.assertHTMLEqual(html, widget.render('field', 2))

    def test_render_action_list(self):
        widget = ActionButtonList(Select(choices=[(1, 'A'), (2, 'B')]))
        widget.add_action('action_a', u'Action A', title='Do the action A')
        widget.add_action('action_b', u'Action B', False)

        html = u'''<ul class="ui-layout hbox ui-creme-widget widget-auto ui-creme-actionbuttonlist" style="" widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <select name="field">
            <option value="1" selected="selected">A</option>
            <option value="2">B</option>
        </select>
    </li>
    <li><button class="ui-creme-actionbutton" name="action_a" title="Do the action A" alt="Do the action A" type="button">Action A</button></li>
    <li><button class="ui-creme-actionbutton" name="action_b" title="Action B" alt="Action B" type="button" disabled="">Action B</button></li>
</ul>'''
        self.assertHTMLEqual(html, widget.render('field', 1))


class EntitySelectorTestCase(FieldTestCase):
    def setUp(self):
        self.maxDiff = None

    def test_listview_url(self):
        widget = EntitySelector()
        url = '%s?ct_id=${ctype}&selection=${selection}&q_filter=${qfilter}' % reverse('creme_core__listview_popup')
        self.assertEqual(url, widget.url)

        widget = EntitySelector(content_type=12)
        url = '%s?ct_id=12&selection=${selection}&q_filter=${qfilter}' % reverse('creme_core__listview_popup')
        self.assertEqual(url, widget.url)

    def test_text_url(self):
        widget = EntitySelector(content_type=12)
        url = TemplateURLBuilder(entity_id=(TemplateURLBuilder.Int, '${id}')).resolve('creme_core__entity_as_json')
        self.assertEqual(url, widget.text_url)

    def test_render(self):
        url = '%s?ct_id=12&selection=${selection}&q_filter=${qfilter}' % reverse('creme_core__listview_popup')
        text_url = TemplateURLBuilder(entity_id=(TemplateURLBuilder.Int, '${id}')).resolve('creme_core__entity_as_json')

        widget = EntitySelector(content_type=12)
        html = '''<span class="ui-creme-widget widget-auto ui-creme-entityselector" style="" widget="ui-creme-entityselector"
                        labelURL="%(text_url)s" label="%(label)s"
                        popupURL="%(url)s" popupSelection="single"
                        qfilter="%(q_filter)s">
    <input name="field" type="hidden" class="ui-creme-input ui-creme-entityselector" value="1"/>
    <button type="button">%(label)s</button>
</span>''' % {
    'label': _(u'Select…'),
    'text_url': text_url,
    'url': url,
    'q_filter': '',
}
        self.assertHTMLEqual(html, widget.render('field', '1'))

    def test_render_qfilter(self):
        url = '%s?ct_id=12&selection=${selection}&q_filter=${qfilter}' % reverse('creme_core__listview_popup')
        text_url = TemplateURLBuilder(entity_id=(TemplateURLBuilder.Int, '${id}')).resolve('creme_core__entity_as_json')

        widget = EntitySelector(content_type=12)
        html = '''<span class="ui-creme-widget widget-auto ui-creme-entityselector" style="" widget="ui-creme-entityselector"
                        labelURL="%(text_url)s" label="%(label)s"
                        popupURL="%(url)s" popupSelection="single"
                        qfilter="%(q_filter)s">
    <input name="field" type="hidden" class="ui-creme-input ui-creme-entityselector" value="1"/>
    <button type="button">%(label)s</button>
</span>''' % {
    'label': _(u'Select…'),
    'text_url': text_url,
    'url': url,
    'q_filter': escape(json_dump({'pk__in': 12})),
}
        self.assertHTMLEqual(html, widget.render('field', '1', attrs={'qfilter': {'pk__in': 12}}))

    def test_render_popup_options(self):
        url = '%s?ct_id=12&selection=${selection}&q_filter=${qfilter}' % reverse('creme_core__listview_popup')
        text_url = TemplateURLBuilder(entity_id=(TemplateURLBuilder.Int, '${id}')).resolve('creme_core__entity_as_json')

        widget = EntitySelector(content_type=12)
        html = '''<span class="ui-creme-widget widget-auto ui-creme-entityselector" style="" widget="ui-creme-entityselector"
                        labelURL="%(text_url)s" label="%(label)s"
                        popupURL="%(url)s" popupSelection="multiple" popupAuto
                        qfilter="%(q_filter)s">
    <input name="field" type="hidden" class="ui-creme-input ui-creme-entityselector" value="1"/>
    <button type="button">%(label)s</button>
</span>''' % {
    'label': _(u'Select…'),
    'text_url': text_url,
    'url': url,
    'q_filter': '',
}
        self.assertHTMLEqual(html, widget.render('field', '1', attrs={'multiple': True, 'autoselect': True}))


class EntityCreatorWidgetTestCase(FieldTestCase):
    def _build_reset_action(self, enabled=True, value=''):
        return ('reset', _(u'Clear'), enabled, {'action': 'reset', 'title': _(u'Clear'), 'value': value})

    def _build_create_action(self, label, title, url='', enabled=True):
        return ('create', label, enabled, {'title': title, 'popupUrl': url})

    def test_is_disabled(self):
        widget = EntityCreatorWidget(FakeContact)
        self.assertFalse(widget._is_disabled({}))
        self.assertFalse(widget._is_disabled(None))
        self.assertTrue(widget._is_disabled({'readonly': True}))
        self.assertTrue(widget._is_disabled({'disabled': True}))

    def test_actions(self):
        creation_url = reverse('creme_core__quick_form', args=(ContentType.objects.get_for_model(FakeContact).id,))
        widget = EntityCreatorWidget(model=FakeContact, creation_url=creation_url, creation_allowed=True)
        widget._build_actions(FakeContact, {})

        self.assertEqual([
            self._build_reset_action(),
            self._build_create_action(FakeContact.creation_label, _(u'Create'), creation_url),
        ], widget.actions)

    def test_actions_creation_url_empty(self):
        widget = EntityCreatorWidget(FakeContact, creation_url='', creation_allowed=True)
        widget._build_actions(FakeContact, {})

        self.assertEqual([
            self._build_reset_action(),
        ], widget.actions)

    def test_actions_creation_not_allowed(self):
        creation_url = reverse('creme_core__quick_form', args=(ContentType.objects.get_for_model(FakeContact).id,))
        widget = EntityCreatorWidget(FakeContact, creation_url=creation_url, creation_allowed=False)
        widget._build_actions(FakeContact, {})

        self.assertEqual([
            self._build_reset_action(),
            self._build_create_action(FakeContact.creation_label, _(u"Can't create"), creation_url, enabled=False),
        ], widget.actions)

    def test_actions_required(self):
        creation_url = reverse('creme_core__quick_form', args=(ContentType.objects.get_for_model(FakeContact).id,))
        widget = EntityCreatorWidget(FakeContact, creation_url=creation_url, creation_allowed=True)
        widget.is_required = True
        widget._build_actions(FakeContact, {})

        self.assertEqual([
            self._build_create_action(FakeContact.creation_label, _(u"Create"), creation_url),
        ], widget.actions)

    def test_actions_disabled(self):
        creation_url = reverse('creme_core__quick_form', args=(ContentType.objects.get_for_model(FakeContact).id,))
        widget = EntityCreatorWidget(FakeContact, creation_url=creation_url, creation_allowed=True)
        widget._build_actions(FakeContact, {})

        self.assertEqual([
            self._build_reset_action(),
            self._build_create_action(FakeContact.creation_label, _(u"Create"), creation_url),
        ], widget.actions)

        widget._build_actions(FakeContact, {'readonly': True})
        self.assertEqual([], widget.actions)

        widget._build_actions(FakeContact, {'disabled': True})
        self.assertEqual([], widget.actions)

    def test_render_no_model(self):
        widget = EntityCreatorWidget()
        html = '''<ul class="hbox ui-creme-widget ui-layout widget-auto ui-creme-actionbuttonlist" style="" widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <input name="field" style="display:none;" type="text" />
        <span name="field">%(no_model_label)s</span>
    </li>
</ul>''' % {
    'no_model_label': u'Model is not set',
}
        self.assertHTMLEqual(html, widget.render('field', ''))

    def test_render(self):
        ct_id = ContentType.objects.get_for_model(FakeContact).id
        creation_url = reverse('creme_core__quick_form', args=(ct_id,))
        widget = EntityCreatorWidget(FakeContact, creation_url=creation_url, creation_allowed=False)
        html = '''<ul class="hbox ui-creme-widget ui-layout widget-auto ui-creme-actionbuttonlist" style="" widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <span class="ui-creme-widget ui-creme-entityselector" style="" widget="ui-creme-entityselector"
              labelURL="%(select_label_url)s" label="%(select_label)s"
              popupURL="%(select_url)s" popupSelection="single"
              qfilter="%(select_q_filter)s">
            <input name="field" type="hidden" class="ui-creme-input ui-creme-entityselector"/>
            <button type="button">%(select_label)s</button>
        </span>
    </li>
    <li>
        <button class="ui-creme-actionbutton" action="reset" name="reset" title="%(reset_title)s" alt="%(reset_title)s" type="button" value="">
            %(reset_label)s
        </button>
    </li>
    <li>
        <button class="ui-creme-actionbutton" name="create" title="%(create_title)s" alt="%(create_title)s" type="button"
                disabled="" popupUrl="%(create_url)s">
            %(create_label)s
        </button>
    </li>
</ul>''' % {
    'select_label': _(u'Select…'),
    'select_label_url': EntitySelector(content_type=ct_id).text_url,
    'select_url': EntitySelector(content_type=ct_id).url,
    'select_q_filter': '',
    'reset_title': _(u'Clear'),
    'reset_label': _(u'Clear'),
    'create_title': _(u"Can't create"),
    'create_label': FakeContact.creation_label,
    'create_url': creation_url,
}
        self.assertHTMLEqual(html, widget.render('field', ''))

