# -*- coding: utf-8 -*-

try:
    from json import dumps as json_dump

    from django.utils.html import escape
    from django.utils.translation import ugettext as _

    from creme.creme_config.registry import config_registry

    from creme.creme_core.forms.fields import ChoiceModelIterator
    from creme.creme_core.forms.widgets import ChainedInput
    from creme.creme_core.tests.forms.base import FieldTestCase

    from ..forms.fields import CreatorCategorySelector
    from ..models import Category, SubCategory
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class CreatorCategorySelectorWidgetTestCase(FieldTestCase):
    def _build_create_action(self, label, title, url='', enabled=True):
        return ('create', label, enabled, {'title': title, 'popupTitle': label, 'popupUrl': url})

    def test_is_disabled(self):
        widget = CreatorCategorySelector()
        self.assertFalse(widget._is_disabled({}))
        self.assertFalse(widget._is_disabled(None))
        self.assertTrue(widget._is_disabled({'readonly': True}))
        self.assertTrue(widget._is_disabled({'disabled': True}))

    def test_actions(self):
        user = self.login()

        categories = ChoiceModelIterator(Category.objects.all())
        creation_url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        widget = CreatorCategorySelector(categories=categories, creation_url=creation_url, creation_allowed=True)
        widget._build_actions({})

        self.assertEqual([
            self._build_create_action(SubCategory.creation_label, _(u'Create'),
                                      url=creation_url + '?category=${_delegate_.category}',
                                      enabled=True),
        ], widget.actions)

    def test_actions_creation_not_allowed(self):
        user = self.login()

        categories = ChoiceModelIterator(Category.objects.all())
        creation_url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        widget = CreatorCategorySelector(categories=categories, creation_url=creation_url, creation_allowed=False)
        widget._build_actions({})

        self.assertEqual([
            self._build_create_action(SubCategory.creation_label, _(u"Can't create"),
                                      url=creation_url + '?category=${_delegate_.category}',
                                      enabled=False),
        ], widget.actions)

    def test_actions_disabled(self):
        user = self.login()

        categories = ChoiceModelIterator(Category.objects.all())
        creation_url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        widget = CreatorCategorySelector(categories=categories, creation_url=creation_url, creation_allowed=True)
        widget._build_actions({})

        self.assertEqual([
            self._build_create_action(SubCategory.creation_label, _(u'Create'), creation_url + '?category=${_delegate_.category}'),
        ], widget.actions)

        widget._build_actions({'readonly': True})
        self.assertEqual([], widget.actions)

        widget._build_actions({'disabled': True})
        self.assertEqual([], widget.actions)

    def test_render(self):
        user = self.login()

        categories = ChoiceModelIterator(Category.objects.all())
        creation_url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        widget = CreatorCategorySelector(categories=categories, creation_url=creation_url, creation_allowed=True)
        value = json_dump({'category':1, 'subcategory':1})

        html = u'''<ul class="hbox ui-creme-widget ui-layout widget-auto ui-creme-actionbuttonlist" style="" widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <div class="ui-creme-widget widget-auto ui-creme-chainedselect" style="" widget="ui-creme-chainedselect">
            <input class="ui-creme-input ui-creme-chainedselect" name="sub_category" type="hidden" value="%(value)s" />
            <ul class="ui-layout vbox">
                <li chained-name="category" class="ui-creme-chainedselect-item">
                    <span class="ui-creme-dselectlabel">%(categories_label)s</span>
                    <select class="ui-creme-input ui-creme-widget ui-creme-dselect" name="" url="" widget="ui-creme-dselect">
                        %(categories)s
                    </select>
                </li>
                <li chained-name="subcategory" class="ui-creme-chainedselect-item">
                    <span class="ui-creme-dselectlabel">%(sub_categories_label)s</span>
                    <select class="ui-creme-input ui-creme-widget ui-creme-dselect" name="" url="/products/sub_category/${category}/json" widget="ui-creme-dselect">
                    </select>
                </li>
            </ul>
        </div>
    </li>
    <li>
        <button class="ui-creme-actionbutton" name="create" title="%(create_title)s" alt="%(create_title)s" type="button"
                popupUrl="%(create_url)s" popupTitle="%(create_label)s">
            %(create_label)s
        </button>
    </li>
</ul>''' % {
    'value': escape(value),
    'categories': ''.join('<option value="%s">%s</option>' % (v, escape(l)) for v, l in ChoiceModelIterator(Category.objects.all())),
    'categories_label': _(u'Category'),
    'sub_categories_label': _(u'Sub-category'),
    'create_title': _(u"Create"),
    'create_label': SubCategory.creation_label,
    'create_url': creation_url + '?category=${_delegate_.category}',
}

        self.maxDiff = None
        self.assertHTMLEqual(html, widget.render('sub_category', value, attrs={'reset': False, 'direction': ChainedInput.VERTICAL}))
