# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template, TemplateSyntaxError
from django.test import override_settings
from django.utils.translation import gettext as _

from creme.creme_core.templatetags.creme_widgets import (
    JoinNode,
    enum_comma_and,
)
from creme.creme_core.utils.media import get_creme_media_url

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
        user = self.create_user()

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
        user = self.create_user()
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

    def test_widget_join01(self):
        self.assertIs(enum_comma_and, JoinNode.behaviours.get(''))
        self.assertIs(enum_comma_and, JoinNode.behaviours.get('en'))

        items = ['Cat', 'Dog', 'Fish']

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% for item in items %}'
                r'{% widget_join %}<span>{{item}}</span>{% end_widget_join %}'
                r'{% endfor %}'
            ).render(Context({'items': items, 'LANGUAGE_CODE': ''}))

        self.assertEqual(
            f'''<span>{items[0]}</span>'''
            f''',&emsp14;<span>{items[1]}</span>'''
            f'''&emsp14;{_('and')}&emsp14;<span>{items[2]}</span>''',
            render.strip(),
        )

    def test_widget_join_error01(self):
        "Argument passed."
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_widgets %}'
                r'{% for item in items %}'
                r'{% widget_join "annoying_arg" %}<span>{{item}}</span>{% end_widget_join %}'
                r'{% endfor %}'
            ).render(Context({'items': ['Cat', 'Dog'], 'LANGUAGE_CODE': ''}))

        self.assertEqual(
            '"widget_join" tag takes no argument',
            str(cm.exception),
        )

    def test_widget_join_error02(self):
        "Not inside {% for %}."
        with self.assertRaises(ValueError) as cm:
            Template(
                r'{% load creme_widgets %}'
                r'{% widget_join %}<span>{{item}}</span>{% end_widget_join %}'
            ).render(Context({'items': ['Cat', 'Dog'], 'LANGUAGE_CODE': ''}))

        self.assertEqual(
            'The tag {% widget_join %} must be used inside a {% for %} loop.',
            str(cm.exception),
        )

    def test_widget_icon_named01(self):
        theme = 'icecream'

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon name="add" %}'
            ).render(Context({'THEME_NAME': theme}))

        self.assertHTMLEqual(
            '<img src="{}" title="" alt="" width="22px"/>'.format(
                get_creme_media_url(theme, 'images/add_22.png'),
            ),
            render,
        )

    def test_widget_icon_named02(self):
        theme = 'chantilly'
        label = "My beautiful icon"

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon name="edit" size="global-button" label=label %}'
            ).render(Context({'THEME_NAME': theme, 'label': label}))

        self.assertHTMLEqual(
            '<img src="{path}" title="{label}" alt="{label}" width="32px"/>'.format(
                path=get_creme_media_url(theme, 'images/edit_32.png'),
                label=label,
            ),
            render,
        )

    def test_widget_icon_ctype(self):
        theme = 'icecream'

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon ctype=ctype %}'
            ).render(Context({
                'THEME_NAME': theme,
                'ctype': ContentType.objects.get_for_model(FakeOrganisation),
            }))

        self.assertHTMLEqual(
            '<img src="{path}" title="{title}" alt="{title}" width="22px"/>'.format(
                path=get_creme_media_url(theme, 'images/organisation_22.png'),
                title='Test Organisation',
            ),
            render,
        )

    def test_widget_icon_instance(self):
        user = self.create_user()
        orga = FakeOrganisation.objects.create(user=user, name='Seele')
        theme = 'icecream'

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon instance=orga %}'
            ).render(Context({'THEME_NAME': theme, 'orga': orga}))

        self.assertHTMLEqual(
            '<img src="{path}" title="{title}" alt="{title}" width="22px"/>'.format(
                path=get_creme_media_url(theme, 'images/organisation_22.png'),
                title='Test Organisation',
            ),
            render,
        )

    def test_widget_icon_named_error01(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon %}'
            ).render(Context({'THEME_NAME': 'icecream'}))

        self.assertEqual(
            '"widget_icon" takes at least one argument (name/ctype/instance=...)',
            str(cm.exception),
        )

    def test_widget_icon_named_error02(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon "add" %}'
            ).render(Context({'THEME_NAME': 'icecream'}))

        self.assertEqual(
            'Malformed 1rst argument to "widget_icon" tag.',
            str(cm.exception),
        )

    def test_widget_icon_named_error03(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon invalid="add" %}'
            ).render(Context({'THEME_NAME': 'icecream'}))

        self.assertEqual(
            '''Invalid 1rst argument to "widget_icon" tag ; '''
            '''it must be in dict_keys(['name', 'ctype', 'instance'])''',
            str(cm.exception),
        )

    def test_widget_icon_named_error04(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon name="add" 12 %}'
            ).render(Context({'THEME_NAME': 'icecream'}))

        self.assertEqual(
            'Malformed arguments to "widget_icon" tag: 12',
            str(cm.exception),
        )

    def test_widget_icon_named_error05(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon name="add" invalid="whatever" %}'
            ).render(Context({'THEME_NAME': 'icecream'}))

        self.assertEqual(
            'Invalid argument name to "widget_icon" tag: invalid',
            str(cm.exception),
        )

    def test_widget_render_icon(self):
        theme = 'icecream'

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon name="add" as my_icon %}'
                r'<span>{% widget_render_icon my_icon class="brick-action-icon" %}</span>'
            ).render(Context({'THEME_NAME': theme}))

        self.assertHTMLEqual(
            '<span>'
            '<img src="{}" class="brick-action-icon" title="" alt="" width="22px"/>'
            '</span>'.format(
                get_creme_media_url(theme, 'images/add_22.png'),
            ),
            render,
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon name="add" as my_icon %}'
                r'<span>{% widget_render_icon my_icon %}</span>'
            ).render(Context({'THEME_NAME': theme}))

        self.assertEqual(
            '"widget_render_icon" takes 2 arguments (icon & class)',
            str(cm.exception),
        )

    def test_widget_help_sign(self):
        theme = 'icecream'

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_help_sign message=help_msg %}'
            ).render(Context({
                'THEME_NAME': theme,
                'help_msg': 'Be careful:\ndo not duplicate entities!',
            }))

        self.assertHTMLEqual(
            '<div class="help-sign">'
            '<img src="{}" title="" alt="" width="16px"><p>'
            'Be careful:<br>do not duplicate entities!'
            '</p>'
            '</div>'.format(
                get_creme_media_url(theme, 'images/info_16.png'),
            ),
            render,
        )
