# -*- coding: utf-8 -*-

from django.conf import settings
from django.template import Context, Template
from django.test import override_settings

from ..base import CremeTestCase
from ..fake_models import FakeOrganisation, FakeSector


class CremeWidgetsTagsTestCase(CremeTestCase):
    def test_widget_hyperlink01(self):
        "No get_absolute_url()"
        s = FakeSector(title='<i>Yello</i>')

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_hyperlink object %}')
            render = tpl.render(Context({'object': s}))

        self.assertEqual(render, '&lt;i&gt;Yello&lt;/i&gt;')

    def test_widget_hyperlink02(self):
        "get_absolute_url()"
        s = FakeSector(title='Yello<br>')
        s.get_absolute_url = lambda: '/creme_core/sectors'

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_hyperlink object %}')
            render = tpl.render(Context({'object': s}))

        self.assertEqual(render, '<a href="/creme_core/sectors">Yello&lt;br&gt;</a>')

    def test_widget_entity_hyperlink01(self):
        "Escaping"
        user = self.login()

        name = 'NERV'
        orga = FakeOrganisation.objects.create(user=user, name=name + '<br/>')  # escaping OK ??

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_entity_hyperlink my_entity user %}')
            render = tpl.render(Context({'user': user, 'my_entity': orga}))

        self.assertEqual(
            render,
            '<a href="/tests/organisation/{}">{}</a>'.format(
                orga.id,
                name + '&lt;br/&gt;',
            )
        )

    def test_widget_entity_hyperlink02(self):
        "Credentials"
        user = self.login(is_superuser=False)

        orga = FakeOrganisation.objects.create(user=self.other_user, name='NERV')
        self.assertFalse(user.has_perm_to_view(orga))

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_entity_hyperlink orga user %}')
            render = tpl.render(Context({'user': user, 'orga': orga}))

        self.assertEqual(render, settings.HIDDEN_VALUE)

    def test_widget_entity_hyperlink03(self):
        "Is deleted."
        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='Seele', is_deleted=True)

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_entity_hyperlink my_entity user %}')
            render = tpl.render(Context({'user': user, 'my_entity': orga}))

        self.assertEqual(render,
                         f'<a href="/tests/organisation/{orga.id}" class="is_deleted">{orga}</a>'
                        )

    @override_settings(URLIZE_TARGET_BLANK=False)
    def test_widget_urlize01(self):
        "No target"
        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{{text|widget_urlize}}')
            render = tpl.render(Context({'text': 'Do not forget to visit www.cremecrm.com'}))

        self.assertEqual(
            render,
            'Do not forget to visit <a href="http://www.cremecrm.com">www.cremecrm.com</a>'
        )

    @override_settings(URLIZE_TARGET_BLANK=True)
    def test_widget_urlize02(self):
        "Target"
        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{{text|widget_urlize}}')
            render = tpl.render(Context({'text': 'Do not forget to visit www.cremecrm.com'}))

        self.assertEqual(
            render,
            'Do not forget to visit <a target="_blank" rel="noopener noreferrer" '
            'href="http://www.cremecrm.com">www.cremecrm.com</a>'
        )

    # TODO: complete
