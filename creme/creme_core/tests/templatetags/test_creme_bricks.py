# -*- coding: utf-8 -*-

try:
    from django.contrib.sessions.backends.base import SessionBase
    from django.template import Template, RequestContext
    from django.test.client import RequestFactory

    from ..base import CremeTestCase
    from ..views.base import BrickTestCaseMixin
    from ..fake_models import FakeContact
    from creme.creme_core.gui.bricks import brick_registry, Brick
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class CremeBricksTagsTestCase(CremeTestCase, BrickTestCaseMixin):
    def setUp(self):
        super(CremeTestCase, self).setUp()
        self.factory = RequestFactory()

    def _build_request(self, url='/'):  # TODO: in CremeTestCase ??
        request = self.factory.get(url)
        request.session = SessionBase()
        request.user = self.user

        return request

    def test_brick_import_n_display01(self):
        "Named Brick"
        self.login()

        brick_str = '<div>FOOBAR</div>'
        name = 'CremeBricksTagsTestCase__test_brick_import_n_display01'

        class FooBrick(Brick):
            id_          = Brick.generate_id('creme_core', name)
            verbose_name = u'Testing purpose'

            def detailview_display(self, context):
                return brick_str

        brick_registry.register(FooBrick)

        with self.assertNoException():
            template = Template("{%% load creme_bricks %%}"
                                "{%% brick_import app='creme_core' name='%(name)s' as my_brick %%}"
                                "{%% brick_display my_brick %%}" % {'name': name}
                               )
            render = template.render(RequestContext(self._build_request()))

        self.assertEqual(brick_str, render.strip())

    def test_brick_import_n_display02(self):
        "Object Brick (generic brick)"
        user = self.login()
        motoko = FakeContact.objects.create(user=user, first_name='Motoko', last_name='Kusanagi', phone='123489')

        with self.assertNoException():
            template = Template('{% load creme_bricks %}'
                                '{% brick_import object=object as my_brick %}'
                                '{% brick_display my_brick %}'
                               )
            render = template.render(RequestContext(self._build_request(), {'object': motoko}))

        document = self.get_html_tree(render)
        brick_node = self.get_brick_node(document, brick_registry._generate_modelbrick_id(FakeContact))

        content_node = brick_node.find('.//div[@class="brick-content "]')
        self.assertIsNotNone(content_node)
        self.assertEqual(motoko.last_name, self.get_brick_tile(content_node, 'regular_field-last_name').text)
        self.assertIn(motoko.phone, self.get_brick_tile(content_node, 'regular_field-phone').text)

    def test_brick_declare_n_display(self):
        "Named Brick"
        self.login()

        class _FooBrick(Brick):
            verbose_name = u'Testing purpose'
            brick_str = 'OVERLOAD ME'

            def detailview_display(self, context):
                return self.brick_str

        class FooBrick1(_FooBrick):
            id_ = _FooBrick.generate_id('creme_core', 'CremeBricksTagsTestCase__brick_test_brick_declare_n_display_01')
            brick_str = '<div>FOOBARBAZ #1</div>'

        class FooBrick2(_FooBrick):
            id_ = _FooBrick.generate_id('creme_core', 'CremeBricksTagsTestCase__brick_test_brick_declare_n_display_02')
            brick_str = '<div>FOOBARBAZ #2</div>'

        class FooBrick3(_FooBrick):
            id_ = _FooBrick.generate_id('creme_core', 'CremeBricksTagsTestCase__brick_test_brick_declare_n_display_03')
            verbose_name = u'Testing purpose'
            brick_str = '<div>FOOBARBAZ #3</div>'

        context = RequestContext(self._build_request(),
                                 {'my_brick1': FooBrick1(),
                                  'my_bricks': [FooBrick2(), FooBrick3()],
                                 }
                                )

        with self.assertRaises(ValueError):  # No {% brick_declare my_brick %}
            Template('{% load creme_bricks %}'
                     '{% brick_display my_brick1 %}'
                    ).render(context)

        with self.assertNoException():
            render = Template('{% load creme_bricks %}'
                              '{% brick_declare my_brick1 my_bricks %}'
                              '{% brick_display my_brick1 %}{% brick_display my_bricks.0 %}{% brick_display my_bricks.1 %}'
                             ).render(context)

        self.assertEqual(FooBrick1.brick_str + FooBrick2.brick_str + FooBrick3.brick_str, render.strip())

    def test_brick_end(self):
        self.login()

        class FooBrick(Brick):
            id_ = Brick.generate_id('creme_core', 'CremeBricksTagsTestCase__brick_test_brick_end')
            verbose_name = u'Testing purpose'
            brick_str = '<div>FOO</div>'

            def detailview_display(self, context):
                return self.brick_str

        context = RequestContext(self._build_request(), {'my_brick': FooBrick()})

        with self.assertNoException():
            render = Template('{% load creme_bricks %}'
                              '{% brick_declare my_brick %}'
                              '{% brick_display my_brick %}'
                              '{% brick_end %}'
                             ).render(context)

        msg = 'BEWARE ! There are some unused imported bricks.'
        self.assertNotIn(msg, render.strip())

        # -----------
        with self.assertNoException():
            render = Template('{% load creme_bricks %}'
                              '{% brick_declare my_brick %}'
                              # '{% brick_display my_brick %}'
                              '{% brick_end %}'
                             ).render(context)

        self.assertIn(msg, render.strip())

    def test_brick_table_data_status(self):
        self.login()

        with self.assertNoException():
            render = Template('{% load creme_bricks %}'
                              '{% brick_table_data_status foo bar %}'
                             ).render(RequestContext(self._build_request()))

        self.assertEqual('data-table-foo-column data-table-bar-column', render.strip())

    # TODO: complete
