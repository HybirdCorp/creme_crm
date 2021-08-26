# -*- coding: utf-8 -*-

from django.conf import settings
from django.template import Context, Template
from django.test import override_settings
from django.utils.translation import gettext as _

from ..base import CremeTestCase
from ..fake_models import FakeOrganisation, FakeSector


class CremeWidgetsTagsTestCase(CremeTestCase):
    def test_widget_hyperlink01(self):
        "No method get_absolute_url()."
        s = FakeSector(title='<i>Yello</i>')

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}{% widget_hyperlink object %}'
            ).render(Context({'object': s}))

        self.assertEqual('&lt;i&gt;Yello&lt;/i&gt;', render)

    def test_widget_hyperlink02(self):
        "The method get_absolute_url() exists()."
        s = FakeSector(title='Yello<br>')
        s.get_absolute_url = lambda: '/creme_core/sectors'

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}{% widget_hyperlink object %}'
            ).render(Context({'object': s}))

        self.assertEqual(
            '<a href="/creme_core/sectors">Yello&lt;br&gt;</a>',
            render,
        )

    def test_widget_entity_hyperlink01(self):
        "Escaping."
        user = self.login()

        name = 'NERV'
        orga = FakeOrganisation.objects.create(user=user, name=name + '<br/>')  # escaping OK ??

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}{% widget_entity_hyperlink my_entity user %}'
            ).render(Context({'user': user, 'my_entity': orga}))

        self.assertEqual(
            '<a href="/tests/organisation/{}">{}</a>'.format(
                orga.id,
                name + '&lt;br/&gt;',
            ),
            render,
        )

    def test_widget_entity_hyperlink02(self):
        "Credentials."
        user = self.login(is_superuser=False)

        orga = FakeOrganisation.objects.create(user=self.other_user, name='NERV')
        self.assertFalse(user.has_perm_to_view(orga))

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_entity_hyperlink orga user %}')
            render = tpl.render(Context({'user': user, 'orga': orga}))

        self.assertEqual(settings.HIDDEN_VALUE, render)

    def test_widget_entity_hyperlink03(self):
        "Is deleted."
        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='Seele', is_deleted=True)

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}{% widget_entity_hyperlink my_entity user %}'
            ).render(Context({'user': user, 'my_entity': orga}))

        self.assertHTMLEqual(
            f'<a href="/tests/organisation/{orga.id}" class="is_deleted">{orga}</a>',
            render,
        )

    @override_settings(URLIZE_TARGET_BLANK=False)
    def test_widget_urlize01(self):
        "No target."
        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}{{text|widget_urlize}}'
            ).render(Context({'text': 'Do not forget to visit www.cremecrm.com'}))

        self.assertEqual(
            'Do not forget to visit <a href="http://www.cremecrm.com">www.cremecrm.com</a>',
            render,
        )

    @override_settings(URLIZE_TARGET_BLANK=True)
    def test_widget_urlize02(self):
        "Target."
        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}{{text|widget_urlize}}'
            ).render(
                Context({'text': 'Do not forget to visit www.cremecrm.com'}),
            )

        self.assertEqual(
            'Do not forget to visit <a target="_blank" rel="noopener noreferrer" '
            'href="http://www.cremecrm.com">www.cremecrm.com</a>',
            render,
        )

    def test_widget_enumerator01(self):
        "Items (length < threshold)."
        items = ['Cat', 'Dog']

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_enumerator items threshold=10 %}'
            ).render(Context({'items': items}))

        # TODO: skip if not "enum_comma_and" behaviour
        self.assertEqual(
            f'''<span class="enumerator-item">{items[0]}</span>'''
            f'''&emsp14;{_('and')}&emsp14;<span class="enumerator-item">{items[1]}</span>''',
            render.strip(),
        )

    def test_widget_enumerator02(self):
        "Empty (no message)."
        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_enumerator items threshold=10 %}'
            ).render(Context({'items': []}))

        self.assertHTMLEqual('<span class="enumerator-empty"></span>', render.strip())

    def test_widget_enumerator03(self):
        "Empty with message."
        msg = 'No item'

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_enumerator items threshold=10 empty=msg %}'
            ).render(Context({'items': [], 'msg': msg}))

        self.assertHTMLEqual(
            f'<span class="enumerator-empty">{msg}</span>', render,
        )

    def test_widget_enumerator04(self):
        "Items with length >= threshold (no message)."
        items = ['Cat', 'Dog', 'Fish']

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_enumerator items threshold=2 %}'
            ).render(Context({'items': items}))

        # msg = _('{count} items').format(count=len(items))
        msg = _('%(count)s items') % {'count': len(items)}
        self.assertHTMLEqual(
            f'''
            <a data-action="popover">
                {msg}
                <details>
                    <ul><li>{items[0]}</li><li>{items[1]}</li><li>{items[2]}</li></ul>
                </details>
            </a>
            ''',
            render,
        )

    def test_widget_enumerator05(self):
        "Items with length >= threshold."
        items = ['Cat', 'Dog', 'Fish']

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_enumerator items threshold=2 summary=_("{count} animals") %}'
            ).render(Context({'items': items}))

        msg = f'{len(items)} animals'  # NB: the translation should not exist
        self.assertHTMLEqual(
            f'''<a data-action="popover">
                {msg}
                <details>
                    <ul><li>{items[0]}</li><li>{items[1]}</li><li>{items[2]}</li></ul>
                </details>
            </a>
            ''',
            render,
        )

    # TODO: complete:
    #   - widget_icon
    #   - widget_join
    #   - widget_help_sign
