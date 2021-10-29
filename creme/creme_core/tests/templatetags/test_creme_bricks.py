# -*- coding: utf-8 -*-

from django.template import Context, RequestContext, Template
from django.utils.translation import gettext as _

from creme.creme_core.bricks import HistoryBrick
from creme.creme_core.constants import MODELBRICK_ID, REL_SUB_HAS
from creme.creme_core.gui.bricks import Brick, EntityBrick, brick_registry
# from creme.creme_core.gui.icons import get_icon_by_name, get_icon_size_px
from creme.creme_core.models import (
    FakeContact,
    RelationBrickItem,
    RelationType,
)
# from creme.creme_core.utils.media import get_current_theme
from creme.creme_core.utils.serializers import json_encode

from ..base import CremeTestCase
from ..views.base import BrickTestCaseMixin


# class CremeBricksTagsTestCase(CremeTestCase, BrickTestCaseMixin):
class CremeBricksTagsTestCase(BrickTestCaseMixin, CremeTestCase):
    def test_brick_import_n_display01(self):
        "Named Brick."
        self.login()

        brick_str = '<div>FOOBAR</div>'
        name = 'CremeBricksTagsTestCase__test_brick_import_n_display01'

        class FooBrick(Brick):
            id_ = Brick.generate_id('creme_core', name)
            verbose_name = 'Testing purpose'

            def detailview_display(this, context):
                return brick_str

        brick_registry.register(FooBrick)

        with self.assertNoException():
            template = Template(
                f"{{% load creme_bricks %}}"
                f"{{% brick_import app='creme_core' name='{name}' as my_brick %}}"
                f"{{% brick_display my_brick %}}"
            )
            render = template.render(RequestContext(self.build_request()))

        self.assertEqual(brick_str, render.strip())

    def test_brick_import_n_display02(self):
        "Object Brick (generic brick)"
        user = self.login()
        motoko = FakeContact.objects.create(
            user=user, first_name='Motoko', last_name='Kusanagi', phone='123489',
        )

        with self.assertNoException():
            template = Template(
                '{% load creme_bricks %}'
                '{% brick_import object=object as my_brick %}'
                '{% brick_display my_brick %}'
            )
            render = template.render(RequestContext(self.build_request(), {'object': motoko}))

        document = self.get_html_tree(render)
        brick_node = self.get_brick_node(document, MODELBRICK_ID)

        content_node = self.get_html_node_or_fail(brick_node, './/div[@class="brick-content "]')
        self.assertEqual(
            motoko.last_name,
            self.get_brick_tile(content_node, 'regular_field-last_name').text
        )
        self.assertIn(motoko.phone, self.get_brick_tile(content_node, 'regular_field-phone').text)

    def test_brick_declare_n_display01(self):
        "Named Brick."
        self.login()

        class _FooBrick(Brick):
            verbose_name = 'Testing purpose'
            brick_str = 'OVERLOAD ME'

            def detailview_display(this, context):
                return this.brick_str

        prefix = 'CremeBricksTagsTestCase__brick_test_brick_declare_n_display01'

        class FooBrick1(_FooBrick):
            id_ = _FooBrick.generate_id('creme_core', f'{prefix}_01')
            brick_str = '<div>FOOBARBAZ #1</div>'

        class FooBrick2(_FooBrick):
            id_ = _FooBrick.generate_id('creme_core', f'{prefix}_02')
            brick_str = '<div>FOOBARBAZ #2</div>'

        class FooBrick3(_FooBrick):
            id_ = _FooBrick.generate_id('creme_core', f'{prefix}_03')
            verbose_name = 'Testing purpose'
            brick_str = '<div>FOOBARBAZ #3</div>'

        context = RequestContext(
            self.build_request(),
            {
                'my_brick1': FooBrick1(),
                'my_bricks': [FooBrick2(), FooBrick3()],
            },
        )

        with self.assertRaises(ValueError):  # No {% brick_declare my_brick %}
            Template(
                '{% load creme_bricks %}'
                '{% brick_display my_brick1 %}'
            ).render(context)

        with self.assertNoException():
            render = Template(
                '{% load creme_bricks %}'
                '{% brick_declare my_brick1 my_bricks %}'
                '{% brick_display my_brick1 %}'
                '{% brick_display my_bricks.0 %}'
                '{% brick_display my_bricks.1 %}'
            ).render(context)

        self.assertEqual(
            FooBrick1.brick_str + FooBrick2.brick_str + FooBrick3.brick_str,
            render.strip()
        )

    def test_brick_declare_n_display02(self):
        "Invalid Brick => no crash please"
        self.login()

        class InvalidBrick(Brick):
            id_ = Brick.generate_id(
                'creme_core',
                'CremeBricksTagsTestCase__brick_test_brick_declare_n_display02',
            )
            verbose_name = 'Testing purpose'

        context = RequestContext(self.build_request(), {'my_brick': InvalidBrick()})

        with self.assertNoException():
            render = Template(
                '{% load creme_bricks %}'
                '{% brick_declare my_brick %}'
                '{% brick_display my_brick %}'
            ).render(context)

        self.assertFalse(render.strip())

    def test_brick_end(self):
        self.login()

        class FooBrick(Brick):
            id_ = Brick.generate_id('creme_core', 'CremeBricksTagsTestCase__brick_test_brick_end')
            verbose_name = 'Testing purpose'
            brick_str = '<div>FOO</div>'

            def detailview_display(this, context):
                return this.brick_str

        context = RequestContext(self.build_request(), {'my_brick': FooBrick()})

        with self.assertNoException():
            render = Template(
                '{% load creme_bricks %}'
                '{% brick_declare my_brick %}'
                '{% brick_display my_brick %}'
                '{% brick_end %}'
            ).render(context)

        msg = 'BEWARE ! There are some unused imported bricks.'
        self.assertNotIn(msg, render.strip())

        # -----------
        with self.assertNoException():
            render = Template(
                '{% load creme_bricks %}'
                '{% brick_declare my_brick %}'
                # '{% brick_display my_brick %}'
                '{% brick_end %}'
            ).render(context)

        self.assertIn(msg, render.strip())

    def test_brick_table_data_status(self):
        self.login()

        with self.assertNoException():
            render = Template(
                '{% load creme_bricks %}'
                '{% brick_table_data_status foo bar %}'
            ).render(RequestContext(self.build_request()))

        self.assertEqual(
            'data-table-foo-column data-table-bar-column',
            render.strip()
        )

    def test_brick_get_by_ids01(self):
        self.login()
        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        rbi = RelationBrickItem.objects.create_if_needed(rtype)

        with self.assertNoException():
            render = Template(
                '{% load creme_bricks %}'
                '{% brick_get_by_ids brick_id1 brick_id2 as bricks %}'
                '{{bricks.0.verbose_name}}##{{bricks.1.config_item.brick_id}}'
            ).render(RequestContext(
                self.build_request(),
                {
                    'brick_id1': HistoryBrick.id_,
                    'brick_id2': rbi.brick_id,
                },
            ))

        self.assertEqual(
            f'{HistoryBrick.verbose_name}##{rbi.brick_id}',
            render.strip()
        )

    def test_brick_get_by_ids02(self):
        "'entity' argument."
        user = self.login()
        motoko = FakeContact.objects.create(
            user=user, first_name='Motoko', last_name='Kusanagi',
        )

        with self.assertNoException():
            render = Template(
                '{% load creme_bricks %}'
                '{% brick_get_by_ids brick_id1 brick_id2 entity=motoko as bricks %}'
                '{{bricks.0.verbose_name}}##{{bricks.1.verbose_name}}'
            ).render(RequestContext(
                self.build_request(),
                {
                    'brick_id1': HistoryBrick.id_,
                    'brick_id2': MODELBRICK_ID,
                    'motoko': motoko,
                },
            ))

        self.assertEqual(
            '{}##{}'.format(
                HistoryBrick.verbose_name,
                EntityBrick.verbose_name,
            ),
            render.strip()
        )

    # TODO: complete


class CremeBrickActionTagsTestCase(CremeTestCase, BrickTestCaseMixin):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

    # def _get_icon(self, name, size, label=''):
    #     theme = get_current_theme()
    #     return get_icon_by_name(
    #         name, theme,
    #         size_px=get_icon_size_px(theme, size),
    #         label=label,
    #     )

    def assertBrickActionHTML(self, bricktag, expected):
        with self.assertNoException():
            template = Template('{% load creme_bricks %}' + bricktag)
            render = template.render(Context()).strip()

        self.assertHTMLEqual(expected, render)

    def test_brick_action(self):
        icon = self.get_icon('add', 'brick-action')
        self.assertBrickActionHTML(
            "{% brick_action 'add' label='Add something' %}",
            '''<a href="" title="{label}" class="brick-action action-type-add  "
                  data-action="add">
                <img src="{icon_url}" class="brick-action-icon" title="{label}"
                     alt="{label}" width="{icon_size}px"/>
            </a>'''.format(
                label='Add something',
                # icon_url=self._get_icon('add', 'brick-action').url,
                icon_url=icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'brick-action'),
                icon_size=icon.size,
            )
        )

    def test_brick_action_label_placeholder(self):
        add_icon = self.get_icon('add', 'brick-action')
        # No action_type placeholder
        self.assertBrickActionHTML(
            "{% brick_action 'add' %}",
            '''<a href="" title="{label}" class="brick-action action-type-add  "
                  data-action="add">
                <img src="{icon_url}" class="brick-action-icon" title="{label}"
                     alt="{label}" width="{icon_size}px"/>
            </a>'''.format(
                label=_('Information'),
                # icon_url=self._get_icon('add', 'brick-action').url,
                icon_url=add_icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'brick-action'),
                icon_size=add_icon.size,
            )
        )

        # action_type placeholder
        edit_icon = self.get_icon('edit', 'brick-action')
        self.assertBrickActionHTML(
            "{% brick_action 'edit' %}",
            '''<a href="" title="{label}" class="brick-action action-type-edit  "
                  data-action="edit">
                <img src="{icon_url}" class="brick-action-icon" title="{label}"
                     alt="{label}" width="{icon_size}px"/>
            </a>'''.format(
                label=_('Edit'),
                # icon_url=self._get_icon('edit', 'brick-action').url,
                icon_url=edit_icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'brick-action'),
                icon_size=edit_icon.size,
            )
        )

        # force to empty string
        self.assertBrickActionHTML(
            "{% brick_action 'add' label='' %}",
            '''<a href="" title="{label}" class="brick-action action-type-add  "
                  data-action="add">
                <img src="{icon_url}" class="brick-action-icon" title="{label}"
                     alt="{label}" width="{icon_size}px"/>
            </a>'''.format(
                label='',
                # icon_url=self._get_icon('add', 'brick-action').url,
                icon_url=add_icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'brick-action'),
                icon_size=add_icon.size,
            )
        )

    def test_brick_action_icon(self):
        icon = self.get_icon('delete', 'small')
        self.assertBrickActionHTML(
            "{% brick_action 'add' label='Add something' icon='delete' icon_size='small' %}",
            '''<a href="" title="{label}" class="brick-action action-type-add  "
                  data-action="add">
                <img src="{icon_url}" class="brick-action-icon" title="{label}"
                     alt="{label}" width="{icon_size}px"/>
            </a>'''.format(
                label='Add something',
                # icon_url=self._get_icon('delete', 'small').url,
                icon_url=icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'small'),
                icon_size=icon.size,
            )
        )

        self.assertBrickActionHTML(
            "{% brick_action 'add' label='Add something' icon='delete' "
            "help_text='This action adds something' icon_size='small' %}",
            '''<a href="" title="{help_text}" class="brick-action action-type-add  "
                  data-action="add">
                <img src="{icon_url}" class="brick-action-icon" title="{help_text}"
                     alt="{help_text}" width="{icon_size}px"/>
            </a>'''.format(
                # label='Add something',
                help_text='This action adds something',
                # icon_url=self._get_icon('delete', 'small').url,
                icon_url=icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'small'),
                icon_size=icon.size,
            )
        )

    def test_brick_action_text(self):
        self.assertBrickActionHTML(
            "{% brick_action 'add' label='Add something' display='text' %}",
            '''<a href="" title="{label}" class="brick-action action-type-add  "
                  data-action="add">
                <span class="brick-action-title">{label}</span>
            </a>'''.format(label='Add something')
        )

        self.assertBrickActionHTML(
            "{% brick_action 'add' label='Add something' display='text' "
            "help_text='This action adds something' %}",
            '''<a href="" title="{help_text}" class="brick-action action-type-add  "
                  data-action="add">
                <span class="brick-action-title">{label}</span>
            </a>'''.format(
                label='Add something',
                help_text='This action adds something',
            )
        )

    def test_brick_action_both(self):
        icon = self.get_icon('add', 'brick-action')
        self.assertBrickActionHTML(
            "{% brick_action 'add' label='Add something' display='both' %}",
            '''<a href="" title="{label}" class="brick-action action-type-add  "
                  data-action="add">
                <img src="{icon_url}" class="brick-action-icon" title="{label}"
                     alt="{label}" width="{icon_size}px"/>
                <span class="brick-action-title">{label}</span>
            </a>'''.format(
                label='Add something',
                # icon_url=self._get_icon('add', 'brick-action').url,
                icon_url=icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'brick-action'),
                icon_size=icon.size,
            ),
        )
        self.assertBrickActionHTML(
            "{% brick_action 'add' label='Add something' display='both' "
            "help_text='This action adds something' %}",
            '''<a href="" title="{help_text}" class="brick-action action-type-add  "
                  data-action="add">
                <img src="{icon_url}" class="brick-action-icon" title="{help_text}"
                     alt="{help_text}" width="{icon_size}px"/>
                <span class="brick-action-title">{label}</span>
            </a>'''.format(
                label='Add something',
                help_text='This action adds something',
                # icon_url=self._get_icon('add', 'brick-action').url,
                icon_url=icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'brick-action'),
                icon_size=icon.size,
            )
        )

    def test_brick_action_disabled(self):
        icon = self.get_icon('add', 'brick-action')
        self.assertBrickActionHTML(
            "{% brick_action 'add' label='Add something' enabled=False %}",
            '''<a href="" title="{label}" data-action="add"
                  class="brick-action action-type-add is-disabled ">
                <img src="{icon_url}" class="brick-action-icon" title="{label}"
                     alt="{label}" width="{icon_size}px"/>
            </a>'''.format(
                label='Add something',
                # icon_url=self._get_icon('add', 'brick-action').url,
                icon_url=icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'brick-action'),
                icon_size=icon.size,
            ),
        )

    def test_brick_action_loading(self):
        icon = self.get_icon('add', 'brick-action')
        self.assertBrickActionHTML(
            "{% brick_action 'add' label='Add something' loading=True %}",
            '''<a href="" title="{label}" class="brick-action action-type-add is-async-action "
                  data-action="add">
                <img src="{icon_url}" class="brick-action-icon" title="{label}"
                     alt="{label}" width="{icon_size}px"/>
            </a>'''.format(
                label='Add something',
                # icon_url=self._get_icon('add', 'brick-action').url,
                icon_url=icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'brick-action'),
                icon_size=icon.size,
            ),
        )

    def test_brick_action_confirm(self):
        icon = self.get_icon('add', 'brick-action')
        self.assertBrickActionHTML(
            "{% brick_action 'add' label='Add something' confirm=True %}",
            '''<a href="" title="{label}" class="brick-action action-type-add  "
                  data-action="add">
                <script class="brick-action-data" type="application/json">
                <!-- {json_data} -->
                </script>
                <img src="{icon_url}" class="brick-action-icon" title="{label}"
                     alt="{label}" width="{icon_size}px"/>
            </a>'''.format(
                label='Add something',
                # icon_url=self._get_icon('add', 'brick-action').url,
                icon_url=icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'brick-action'),
                icon_size=icon.size,
                json_data=json_encode({
                    'options': {'confirm': True},
                    'data': {},
                }),
            )
        )
        self.assertBrickActionHTML(
            "{% brick_action 'add' label='Add something' confirm='Are you sure ?' %}",
            '''<a href="" title="{label}" class="brick-action action-type-add  "
                  data-action="add">
                <script class="brick-action-data" type="application/json">
                <!-- {json_data} -->
                </script>
                <img src="{icon_url}" class="brick-action-icon" title="{label}"
                     alt="{label}" width="{icon_size}px"/>
            </a>'''.format(
                label='Add something',
                # icon_url=self._get_icon('add', 'brick-action').url,
                icon_url=icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'brick-action'),
                icon_size=icon.size,
                json_data=json_encode({
                    'options': {'confirm': 'Are you sure ?'},
                    'data': {},
                }),
            )
        )

    def test_brick_action_extra_data(self):
        icon = self.get_icon('add', 'brick-action')
        self.assertBrickActionHTML(
            "{% brick_action 'add' label='Add something' confirm=True "
            "__name1='value1' __name2=2 %}",
            '''<a href="" title="{label}" class="brick-action action-type-add  "
                  data-action="add">
                <script class="brick-action-data" type="application/json">
                <!-- {json_data} -->
                </script>
                <img src="{icon_url}" class="brick-action-icon" title="{label}"
                     alt="{label}" width="{icon_size}px"/>
            </a>'''.format(
                label='Add something',
                # icon_url=self._get_icon('add', 'brick-action').url,
                icon_url=icon.url,
                # icon_size=get_icon_size_px(get_current_theme(), 'brick-action'),
                icon_size=icon.size,
                json_data=json_encode({
                    'options': {'confirm': True},
                    'data': {'name1': 'value1', 'name2': 2},
                }),
            )
        )
