from pathlib import Path

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template, TemplateSyntaxError
from django.test import override_settings
from django.test.testcases import assert_and_parse_html
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.templatetags.creme_widgets import (
    JoinNode,
    enum_comma_and,
)
from creme.creme_core.utils.media import get_creme_media_url

from ..base import CremeTestCase
from ..fake_models import FakeContact, FakeOrganisation, FakeSector, FakeTicket


class CremeWidgetsTagsTestCase(CremeTestCase):
    def test_widget_hyperlink__not_url(self):
        "No method get_absolute_url()."
        s = FakeSector(title='<i>Yello</i>')

        with self.assertLogs(level='WARNING'):
            with self.assertNoException():
                render = Template(
                    r'{% load creme_widgets %}{% widget_hyperlink object %}'
                ).render(Context({'object': s}))

        self.assertHTMLEqual('&lt;i&gt;Yello&lt;/i&gt;', render)

    def test_widget_hyperlink__url_ok(self):
        "The method get_absolute_url() exists()."
        s = FakeSector(title='Yello<br>')
        s.get_absolute_url = lambda: '/creme_core/sectors'

        with self.assertNoException():
            render1 = Template(
                r'{% load creme_widgets %}{% widget_hyperlink object %}'
            ).render(Context({'object': s}))
        self.assertHTMLEqual(
            '<a href="/creme_core/sectors">Yello&lt;br&gt;</a>',
            render1,
        )

        # Label given
        with self.assertNoException():
            render2 = Template(
                r'{% load creme_widgets %}{% widget_hyperlink object label=label %}'
            ).render(Context({'object': s, 'label': 'My favorite <i>one</i>'}))
        self.assertHTMLEqual(
            '<a href="/creme_core/sectors">My favorite &lt;i&gt;one&lt;/i&gt;</a>',
            render2,
        )

    def test_widget_hyperlink__disabled(self):
        s = FakeSector(title='Yellow')
        s.get_absolute_url = lambda: '/creme_core/sectors'
        ctxt = Context({'object': s})

        # disabled == False -----
        with self.assertNoException():
            render1 = Template(
                r'{% load creme_widgets %}{% widget_hyperlink object disabled=False %}'
            ).render(ctxt)
        self.assertHTMLEqual(
            '<a href="/creme_core/sectors">Yellow</a>', render1,
        )

        # disabled == True -----
        with self.assertNoException():
            render2 = Template(
                r'{% load creme_widgets %}{% widget_hyperlink object disabled=True %}'
            ).render(ctxt)
        self.assertHTMLEqual(
            '<span class="disabled-link">Yellow</span>', render2,
        )

        # disabled == 'a message' -----
        with self.assertNoException():
            render3 = Template(
                r'{% load creme_widgets %}'
                r'{% widget_hyperlink object label="Details" disabled="You cannot view that" %}'
            ).render(ctxt)
        self.assertHTMLEqual(
            '<span class="disabled-link" title="You cannot view that">Details</span>',
            render3,
        )

    def test_widget_ctype_hyperlink01(self):
        self.assertHasAttr(FakeContact, 'get_lv_absolute_url')

        user = self.get_root_user()

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_ctype_hyperlink ctype=ctype user=user %}'
            ).render(Context({
                'ctype': ContentType.objects.get_for_model(FakeContact),
                'user': user,
            }))

        url = reverse('creme_core__list_fake_contacts')
        self.assertEqual(f'<a href="{url}">Test Contacts</a>', render)

    def test_widget_ctype_hyperlink02(self):
        "Model without related list-view."
        self.assertHasNoAttr(FakeTicket, 'get_lv_absolute_url')

        user = self.get_root_user()

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_ctype_hyperlink ctype=ctype user=user %}'
            ).render(Context({
                'ctype': ContentType.objects.get_for_model(FakeTicket),
                'user': user,
            }))

        self.assertEqual('Test Tickets', render)

    def test_widget_ctype_hyperlink03(self):
        "No app perm."
        user = self.create_user(
            role=self.create_role(name='No core', allowed_apps=['documents']),
        )

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_ctype_hyperlink ctype=ctype user=user %}'
            ).render(Context({
                'ctype': ContentType.objects.get_for_model(FakeContact),
                'user': user,
            }))

        self.assertEqual('Test Contacts', render)

    def test_widget_entity_hyperlink(self):
        "Escaping."
        user = self.get_root_user()

        name = 'NERV'
        orga = FakeOrganisation.objects.create(user=user, name=name + '<br/>')  # escaping OK ??

        with self.assertNoException():
            render1 = Template(
                r'{% load creme_widgets %}{% widget_entity_hyperlink my_entity user %}'
            ).render(Context({'user': user, 'my_entity': orga}))

        self.assertHTMLEqual(
            '<a href="/tests/organisation/{}" target="_self">{}</a>'.format(
                orga.id,
                name + '&lt;br/&gt;',
            ),
            render1,
        )

        # Label given
        with self.assertNoException():
            render2 = Template(
                r'{% load creme_widgets %}'
                r'{% widget_entity_hyperlink my_entity user label=label %}'
            ).render(Context({
                'user': user,
                'my_entity': orga,
                'label': 'My favorite <i>one</i>',
            }))

        self.assertHTMLEqual(
            '<a href="/tests/organisation/{}" target="_self">{}</a>'.format(
                orga.id,
                'My favorite &lt;i&gt;one&lt;/i&gt;'
            ),
            render2,
        )

        # Other tag ---
        with self.assertNoException():
            render3 = Template(
                r'{% load creme_widgets %}'
                r'{% widget_entity_hyperlink my_entity user label=label target="_blank" %}'
            ).render(Context({
                'user': user,
                'my_entity': orga,
                'label': name,
            }))

        self.assertEqual(
            f'<a href="/tests/organisation/{orga.id}" target="_blank">{name}</a>',
            render3,
        )

    def test_widget_entity_hyperlink__credentials(self):
        user = self.login_as_standard()

        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='NERV')
        self.assertFalse(user.has_perm_to_view(orga))

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_entity_hyperlink orga user %}')
            render = tpl.render(Context({'user': user, 'orga': orga}))

        self.assertEqual(settings.HIDDEN_VALUE, render)

    def test_widget_entity_hyperlink__is_deleted(self):
        "Is deleted."
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Seele', is_deleted=True)
        ctxt = Context({'user': user, 'my_entity': orga})

        with self.assertNoException():
            render1 = Template(
                r'{% load creme_widgets %}{% widget_entity_hyperlink my_entity user %}'
            ).render(ctxt)

        self.assertHTMLEqual(
            f'<a href="/tests/organisation/{orga.id}" target="_self" class="is_deleted">'
            f'{orga}'
            f'</a>',
            render1,
        )

        # Ignore deleted
        with self.assertNoException():
            render2 = Template(
                r'{% load creme_widgets %}'
                r'{% widget_entity_hyperlink my_entity user ignore_deleted=True %}'
            ).render(ctxt)

        self.assertHTMLEqual(
            f'<a href="/tests/organisation/{orga.id}" target="_self">{orga}</a>',
            render2,
        )

    @override_settings(SITE_DOMAIN='https://crm.domain')
    def test_widget_entity_hyperlink__relative(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='NERV')
        ctxt = Context({'user': user, 'orga': orga})

        with self.assertNoException():
            render1 = Template(
                r'{% load creme_widgets %}{% widget_entity_hyperlink orga user %}'
            ).render(ctxt)

        relative_render = f'<a href="/tests/organisation/{orga.id}" target="_self">{orga.name}</a>'
        self.assertHTMLEqual(relative_render, render1)

        # ---
        with self.assertNoException():
            render2 = Template(
                r'{% load creme_widgets %}'
                r'{% widget_entity_hyperlink entity=orga user=user relative=True %}'
            ).render(ctxt)
        self.assertHTMLEqual(relative_render, render2)

        # ---
        with self.assertNoException():
            render3 = Template(
                r'{% load creme_widgets %}'
                r'{% widget_entity_hyperlink orga user=user relative=False %}'
            ).render(ctxt)
        self.assertHTMLEqual(
            f'<a href="https://crm.domain/tests/organisation/{orga.id}" target="_self">'
            f'{orga.name}'
            f'</a>',
            render3,
        )

    @override_settings(URLIZE_TARGET_BLANK=False)
    def test_widget_urlize01(self):
        "No target."
        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}{{text|widget_urlize}}'
            ).render(Context({'text': 'Do <b>not</b> forget to visit www.cremecrm.com'}))

        self.assertEqual(
            'Do &lt;b&gt;not&lt;/b&gt; forget to visit '
            '<a href="http://www.cremecrm.com">www.cremecrm.com</a>',
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
        user = self.get_root_user()
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

    def test_widget_icon_data__high(self):
        path = Path(
            # 16 x 16 px
            settings.CREME_ROOT, 'static', 'icecream', 'images', 'remove_16.png',
        )
        self.assertTrue(path.exists())

        label = 'My image'

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon data=path label=label %}'
            ).render(Context({
                'THEME_NAME': 'icecream',
                'path': path,
                'label': label,
            }))

        dom = assert_and_parse_html(self, render, 'Rendered icon is not valid HTML', None)
        self.assertEqual('img', dom.name)
        self.assertFalse(dom.children)

        get_attribute = dict(dom.attributes).get
        self.assertEqual('22px', get_attribute('height'))
        self.assertEqual(label, get_attribute('alt'))
        self.assertEqual(label, get_attribute('title'))
        self.assertEqual('', get_attribute('style'))
        self.assertStartsWith(
            get_attribute('src', ''),
            'data:image/png;base64, iVBORw0KGgoAAAANSUh',
        )

    def test_widget_icon_data__large(self):
        path = Path(
            # 89 x 40 px
            settings.CREME_ROOT, 'static', 'common', 'images', 'creme_powered.png',
        )
        self.assertTrue(path.exists())

        label = 'Large image'

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_icon data=path label=label size="header-menu-home" %}'
            ).render(Context({
                'THEME_NAME': 'icecream',
                'path': path,
                'label': label,
            }))

        dom = assert_and_parse_html(self, render, 'Rendered icon is not valid HTML', None)
        self.assertEqual('img', dom.name)
        self.assertFalse(dom.children)

        get_attribute = dict(dom.attributes).get
        self.assertEqual('30px', get_attribute('width'))
        self.assertEqual('padding-top: 8px;', get_attribute('style'))
        self.assertEqual(label, get_attribute('title'))

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
            '''it must be in dict_keys(['name', 'ctype', 'instance', 'data'])''',
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

    def test_widget_help_sign_with_another_icon(self):
        theme = 'icecream'

        with self.assertNoException():
            render = Template(
                r'{% load creme_widgets %}'
                r'{% widget_help_sign message=help_msg icon="cancel" %}'
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
                get_creme_media_url(theme, 'images/cancel_16.png'),
            ),
            render,
        )
