# -*- coding: utf-8 -*-

from json import dumps as json_dump

from django.urls import reverse
from django.utils.html import escape, format_html_join
from django.utils.translation import gettext as _

from creme.creme_config.registry import config_registry
from creme.creme_core.forms.fields import ChoiceModelIterator
from creme.creme_core.forms.widgets import ChainedInput, WidgetAction
from creme.creme_core.tests.base import CremeTestCase

from ..forms.fields import CreatorCategorySelector
from ..models import Category, SubCategory


# class CreatorCategorySelectorWidgetTestCase(FieldTestCase):
class CreatorCategorySelectorWidgetTestCase(CremeTestCase):
    @staticmethod
    def _build_create_action(label, title, url='', enabled=True):
        # return ('create', label, enabled, {'title': title, 'popupUrl': url})
        return WidgetAction(
            name='create',
            label=label,
            enabled=enabled,
            icon='add',

            title=title,
            popupUrl=url,
        )

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
        widget = CreatorCategorySelector(
            categories=categories, creation_url=creation_url, creation_allowed=True,
        )
        widget._build_actions({})

        self.assertListEqual(
            [
                self._build_create_action(
                    SubCategory.creation_label, _('Create'),
                    url=creation_url + '?category=${_delegate_.category}',
                    enabled=True,
                ),
            ],
            widget.actions,
        )

    def test_actions_creation_not_allowed(self):
        user = self.login()

        categories = ChoiceModelIterator(Category.objects.all())
        creation_url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        widget = CreatorCategorySelector(
            categories=categories, creation_url=creation_url, creation_allowed=False,
        )
        widget._build_actions({})

        self.assertListEqual(
            [
                self._build_create_action(
                    SubCategory.creation_label, _("Can't create"),
                    url=creation_url + '?category=${_delegate_.category}',
                    enabled=False,
                ),
            ],
            widget.actions,
        )

    def test_actions_disabled(self):
        user = self.login()

        categories = ChoiceModelIterator(Category.objects.all())
        creation_url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        widget = CreatorCategorySelector(
            categories=categories, creation_url=creation_url, creation_allowed=True,
        )
        widget._build_actions({})

        self.assertListEqual(
            [
                self._build_create_action(
                    SubCategory.creation_label, _('Create'),
                    creation_url + '?category=${_delegate_.category}',
                ),
            ],
            widget.actions,
        )

        widget._build_actions({'readonly': True})
        self.assertListEqual([], widget.actions)

        widget._build_actions({'disabled': True})
        self.assertListEqual([], widget.actions)

    def test_render(self):
        user = self.login()

        categories = ChoiceModelIterator(Category.objects.all())
        creation_url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        widget = CreatorCategorySelector(
            categories=categories, creation_url=creation_url, creation_allowed=True,
        )
        value = json_dump({'category': 1, 'subcategory': 1})

        html = '''
<ul class="hbox ui-creme-widget ui-layout widget-auto ui-creme-actionbuttonlist"
    widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <div class="ui-creme-widget widget-auto ui-creme-chainedselect"
             widget="ui-creme-chainedselect">
            <input class="ui-creme-input ui-creme-chainedselect"
                   name="sub_category" type="hidden" value="{value}" />
            <ul class="ui-layout vbox">
                <li chained-name="category" class="ui-creme-chainedselect-item">
                    <span class="ui-creme-dselectlabel">{categories_label}</span>
                    <select class="ui-creme-input ui-creme-widget ui-creme-dselect"
                            name="" url="" widget="ui-creme-dselect">
                        {categories}
                    </select>
                </li>
                <li chained-name="subcategory" class="ui-creme-chainedselect-item">
                    <span class="ui-creme-dselectlabel">{sub_categories_label}</span>
                    <select class="ui-creme-input ui-creme-widget ui-creme-dselect"
                            name="" url="{choices_url}" widget="ui-creme-dselect">
                    </select>
                </li>
            </ul>
        </div>
    </li>
    <li>
        <button class="ui-creme-actionbutton with-icon"
                name="create" title="{create_title}" type="button" popupUrl="{create_url}">
            {create_icon}<span>{create_label}</span>
        </button>
    </li>
</ul>'''.format(
            value=escape(value),

            categories=format_html_join(
                '',
                '<option value="{}">{}</option>',
                Category.objects.values_list('id', 'name'),
            ),
            categories_label=_('Category'),

            sub_categories_label=_('Sub-category'),
            choices_url=reverse(
                'products__subcategories', args=('1234',),
            ).replace('1234', '${category}'),

            create_title=_('Create'),
            create_label=SubCategory.creation_label,
            create_url=creation_url + '?category=${_delegate_.category}',
            create_icon=self.get_icon(
                'add', size='form-widget', label=SubCategory.creation_label,
            ).render(),
        )

        self.maxDiff = None
        self.assertHTMLEqual(
            html,
            widget.render(
                'sub_category', value,
                attrs={'reset': False, 'direction': ChainedInput.VERTICAL},
            )
        )
