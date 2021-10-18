# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from decimal import Decimal
from functools import partial
from json import loads as json_load

from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template, TemplateSyntaxError
from django.urls import reverse
from django.utils.translation import gettext, gettext_lazy

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import (
    FakeContact,
    FakeOrganisation,
    SetCredentials,
)
from creme.creme_core.utils.html import escapejson

from ..base import CremeTestCase


class CremeCoreTagsTestCase(CremeTestCase):
    def test_get_by_index(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{{xs|get_by_index:0}}#'
                '{{xs|get_by_index:1}}#'
                '{{ys|get_by_index:1}}'
            ).render(Context({'xs': [1, 2, 3], 'ys': (4, 5)}))

        self.assertEqual('1#2#5', render.strip())

        template = Template('{% load creme_core_tags %}{{xs|get_by_index:2}}')
        with self.assertRaises(IndexError):
            template.render(Context({'xs': [1, 2]}))

    def test_lt(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{% with xlesser=x|lt:3 xequal=x|lt:2 xgreater=x|lt:1 %}'
                '{% if xlesser %}True{% endif %}#'
                '{% if not xequal %}False{% endif %}#'
                '{% if not xgreater %}False{% endif %}#'
                '{% if 0|lt:1 %}True{% endif %}'
                '{% endwith %}'
            ).render(Context({'x': 2}))

        self.assertEqual('True#False#False#True', render.strip())

    def test_lte(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{% with xlesser=x|lte:3 xequal=x|lte:2 xgreater=x|lte:1 %}'
                '{% if xlesser %}True{% endif %}#'
                '{% if xequal %}True{% endif %}#'
                '{% if not xgreater %}False{% endif %}#'
                '{% if 0|lte:1 %}True{% endif %}'
                '{% endwith %}'
            ).render(Context({'x': 2}))

        self.assertEqual('True#True#False#True', render.strip())

    def test_gt(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{% with xlesser=x|gt:3 xequal=x|gt:2 xgreater=x|gt:1 %}'
                '{% if not xlesser %}False{% endif %}#'
                '{% if not xequal %}False{% endif %}#'
                '{% if xgreater %}True{% endif %}#'
                '{% if 4|gt:3 %}True{% endif %}'
                '{% endwith %}'
            ).render(Context({'x': 2}))

        self.assertEqual('False#False#True#True', render.strip())

    def test_gte(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{% with xlesser=x|gte:3 xequal=x|gte:2 xgreater=x|gte:1 %}'
                '{% if not xlesser %}False{% endif %}#'
                '{% if xequal %}True{% endif %}#'
                '{% if xgreater %}True{% endif %}#'
                '{% if 4|gte:3 %}True{% endif %}'
                '{% endwith %}'
            ).render(Context({'x': 2}))

        self.assertEqual('False#True#True#True', render.strip())

    def test_eq(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{% with xlesser=x|eq:3 xequal=x|eq:2 xgreater=x|eq:1 %}'
                '{% if not xlesser %}False{% endif %}#'
                '{% if xequal %}True{% endif %}#'
                '{% if not xgreater %}False{% endif %}#'
                '{% if 3|eq:3 %}True{% endif %}'
                '{% endwith %}'
            ).render(Context({'x': 2}))

        self.assertEqual('False#True#False#True', render.strip())

    def test_sub(self):
        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}'
                '{{x|sub:3}}#{{13|sub:6}}'
            )
            render = template.render(Context({'x': 5}))

        self.assertEqual('2#7', render.strip())

    def test_mult(self):
        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}'
                '{{x|mult:3}}#{{10|mult:6}}'
            )
            render = template.render(Context({'x': 5}))

        self.assertEqual('15#60', render.strip())

    def test_idiv(self):
        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}'
                '{{x|idiv:2}}#{{13|idiv:3}}'
            )
            render = template.render(Context({'x': 5}))

        self.assertEqual('2#4', render.strip())

    def test_mod(self):
        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}'
                '{{x|mod:3}}#{{13|mod:6}}'
            )
            render = template.render(Context({'x': 5}))

        self.assertEqual('2#1', render.strip())

    def test_has_attr(self):
        with self.assertNoException():
            template = Template(
                "{% load creme_core_tags %}"
                "{% if orga|has_attr:'name' %}OK{% else %}KO{% endif %}#"
                "{% if orga|has_attr:'invalid' %}OK{% else %}KO{% endif %}"
            )
            render = template.render(Context({
                'orga': FakeOrganisation(name='Amestris'),
            }))

        self.assertEqual('OK#KO', render.strip())

    def test_format(self):
        with self.assertNoException():
            template = Template(
                "{% load creme_core_tags %}"
                "{{ 'world'|format:'Hello %s' }}"
            )
            render = template.render(Context())

        self.assertEqual('Hello world', render.strip())

    def test_listify(self):
        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}'
                '{% listify email phone as mylist %}'
                '{{mylist|join:","}}'
            )
            render = template.render(Context({
                'email': 'foo@bar.org',
                'phone': '123-FOOBAR',
            }))

        self.assertEqual('foo@bar.org,123-FOOBAR', render.strip())

    def test_filter_empty(self):
        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}'
                '{{mylist|filter_empty|join:","}}'
            )
            render = template.render(Context({
                'mylist': ['', 'foo@bar.org', None, '123-FOOBAR', False],
            }))

        self.assertEqual('foo@bar.org,123-FOOBAR', render.strip())

    def test_verbose_models(self):
        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}'
                '{% with m=models|verbose_models %}{{m.0}}, {{m.1}}{% endwith %}'
            )
            render = template.render(Context({
                'models': [FakeContact, FakeOrganisation],
            }))

        self.assertEqual('Test Contact, Test Organisation', render.strip())

    def test_templatize(self):
        with self.assertNoException():
            template = Template(
                r'{% load creme_core_tags %}'
                r'{% templatize "{{columns|length}}" as colspan %}'
                r'<h1>{{colspan}}</h1>'
            )
            render = template.render(Context({'columns': range(3)}))

        self.assertEqual('<h1>3</h1>', render.strip())

    def test_templatize_error01(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_core_tags %}'
                r'{% templatize %}'
            ).render(Context({}))

        self.assertEqual(
            '"templatize" tag requires arguments',
            str(cm.exception),
        )

    def test_templatize_error02(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_core_tags %}'
                r'{% templatize "{{1|add:2}}" as %}'
            ).render(Context({}))

        self.assertEqual(
            '"templatize" tag has invalid arguments: <"{{1|add:2}}" as>',
            str(cm.exception),
        )

    def test_templatize_error03(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_core_tags %}'
                r'{% templatize #{{1|add:2}}# as result %}'
            ).render(Context({}))

        self.assertEqual(
            '''"templatize" tag's argument should be in quotes.''',
            str(cm.exception),
        )

    # TODO: complete with other field types
    def test_print_field(self):
        user = self.login()
        orga = FakeOrganisation.objects.create(
            user=self.user, name='<br/>Amestris', url_site='www.amestris.org',
        )

        with self.assertNoException():
            template = Template(
                "{% load creme_core_tags %}"
                "<ul>"
                "<li>{% print_field object=entity field='name' %}</li>"
                "<li>{% print_field object=entity field='url_site' %}</li>"
                "</ul>"
            )
            render = template.render(Context({'entity': orga, 'user': user}))

        self.assertEqual(
            '<ul>'
            '<li>&lt;br/&gt;Amestris</li>'
            '<li><a href="www.amestris.org" target="_blank">www.amestris.org</a></li>'
            '</ul>',
            render.strip()
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_core_tags %}'
                r'{% print_field %}'
            )

        self.assertEqual(
            '"print_field" tag requires arguments.',
            str(cm.exception),
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_core_tags %}'
                r'{% print_field entity "url_site" %}'
            )

        self.assertEqual(
            '"print_field" tag has invalid arguments.',
            str(cm.exception),
        )

    def test_has_perm_to01(self):
        user = self.login()
        orga = FakeOrganisation.objects.create(user=self.user, name='Xing')

        with self.assertNoException():
            render = Template(
                "{% load creme_core_tags %}"
                "{% has_perm_to view entity as vperm %}{{vperm}}"
                "{% has_perm_to change entity as cperm %}{{cperm}}"
                "{% has_perm_to delete entity as dperm %}{{dperm}}"
                "{% has_perm_to link entity as lperm %}{{lperm}}"
                "{% has_perm_to unlink entity as uperm %}{{uperm}}"
                "{% has_perm_to create entity as aperm %}{{aperm}}"
                "{% has_perm_to create ct as aperm2 %}{{aperm2}}"
                "{% has_perm_to export entity as xperm %}{{xperm}}"
                "{% has_perm_to export ct as xperm2 %}{{xperm2}}"
                "{% has_perm_to access 'creme_core' as app_perm %}{{app_perm}}"
                "{% has_perm_to admin 'creme_core' as adm_perm %}{{adm_perm}}"
            ).render(Context({
                'entity': orga,
                'user':   user,
                'ct':     ContentType.objects.get_for_model(FakeOrganisation),
            }))

        self.assertEqual('True' * 11, render.strip())

    def test_has_perm_to02(self):
        user = self.login(is_superuser=False)
        orga = FakeOrganisation.objects.create(user=self.user, name='Xerces')

        with self.assertNoException():
            render = Template(
                "{% load creme_core_tags %}"
                "{% has_perm_to view entity as vperm %}{{vperm}}"
                "{% has_perm_to change entity as cperm %}{{cperm}}"
                "{% has_perm_to delete entity as dperm %}{{dperm}}"
                "{% has_perm_to link entity as lperm %}{{lperm}}"
                "{% has_perm_to unlink entity as uperm %}{{uperm}}"
                "{% has_perm_to create entity as aperm %}{{aperm}}"
                "{% has_perm_to create ct as aperm2 %}{{aperm2}}"
                "{% has_perm_to export entity as xperm %}{{xperm}}"
                "{% has_perm_to export ct as xperm2 %}{{xperm2}}"
                "{% has_perm_to access 'persons' as app_perm %}{{app_perm}}"
                "{% has_perm_to admin 'persons' as adm_perm %}{{adm_perm}}"
            ).render(Context({
                'entity': orga,
                'user':   user,
                'ct':     ContentType.objects.get_for_model(FakeOrganisation),
            }))

        self.assertEqual('False' * 11, render.strip())

    def test_has_perm_to03(self):
        user = self.login(
            is_superuser=False,
            allowed_apps=['creme_core'],
            creatable_models=[FakeOrganisation],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_ALL,
        )

        orga = FakeOrganisation.objects.create(user=user, name='Amestris')
        self.assertTrue(user.has_perm_to_view(orga))

        with self.assertNoException():
            render = Template(
                "{% load creme_core_tags %}"
                "{% has_perm_to view entity as vperm %}{{vperm}}"
                "{% has_perm_to change entity as cperm %}{{cperm}}"
                "{% has_perm_to delete entity as dperm %}{{dperm}}"
                "{% has_perm_to link entity as lperm %}{{lperm}}"
                "{% has_perm_to unlink entity as uperm %}{{uperm}}"
                "{% has_perm_to create entity as aperm %}{{aperm}}"
                "{% has_perm_to create ct as aperm2 %}{{aperm2}}"
                "{% has_perm_to export entity as xperm %}{{xperm}}"
                "{% has_perm_to export ct as xperm2 %}{{xperm2}}"
                "{% has_perm_to access 'creme_core' as app_perm %}{{app_perm}}"
                "{% has_perm_to admin 'creme_core' as adm_perm %}{{adm_perm}}"
            ).render(Context({
                'entity': orga,
                'user':   user,
                'ct':     ContentType.objects.get_for_model(FakeOrganisation),
            }))

        self.assertEqual(
            'True' + 'False' * 4 + 'True' * 2 + 'False' * 2 + 'True' + 'False',
            render.strip()
        )

    def test_has_perm_to_errors(self):
        with self.assertRaises(TemplateSyntaxError) as cm1:
            Template(
                r'{% load creme_core_tags %}'
                r'{% has_perm_to %}'
            ).render(Context({}))

        self.assertEqual(
            '"has_perm_to" tag requires arguments',
            str(cm1.exception),
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm2:
            Template(
                r'{% load creme_core_tags %}'
                r'{% has_perm_to view as vperm %}'
            ).render(Context({}))

        self.assertEqual(
            '"has_perm_to" tag had invalid arguments: <view as vperm>',
            str(cm2.exception),
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm3:
            Template(
                r'{% load creme_core_tags %}'
                r'{% has_perm_to visualize entity as vperm %}'
            ).render(Context({}))

        self.assertEqual(
            '"has_perm_to" invalid permission tag: "visualize"',
            str(cm3.exception),
        )

    def _assertJsonifyFilter(self, expected, data):
        with self.assertNoException():
            template = Template("{% load creme_core_tags %}{{data|jsonify|safe}}")
            render = template.render(Context({'data': data}))

        with self.assertNoException():
            deserialized = json_load(render.strip())

        self.assertEqual(expected, deserialized)

    def test_jsonify_filter(self):
        self._assertJsonifyFilter('', '')
        self._assertJsonifyFilter('test string', 'test string')

        self._assertJsonifyFilter([1, 2, 3], (1, 2, 3))
        self._assertJsonifyFilter([1, 2, 3], [1, 2, 3])
        self._assertJsonifyFilter(
            {'value': 1, 'label': 'a'},
            {'value': 1, 'label': 'a'},
        )

        self._assertJsonifyFilter([0, 1, 2], (v for v in range(3)))
        self._assertJsonifyFilter(
            [
                {'value': 0, 'label': 'a'},
                {'value': 1, 'label': 'b'},
                {'value': 2, 'label': 'c'},
            ],
            (
                {'value': value, 'label': label}
                for value, label in enumerate(['a', 'b', 'c'])
            ),
        )

        now = datetime(2018, 1, 12, 8, 12, 25, 12345, tzinfo=timezone.utc)

        self._assertJsonifyFilter(
            {
                'a': 12,
                'b': 0.47,
                'c': gettext('User'),
                'd': '2018-01-12',
                'e': '08:12:25.012Z',
                'f': '2018-01-12T08:12:25.012Z',
            },
            {
                'a': 12,
                'b': Decimal('0.47'),
                'c': gettext_lazy('User'),
                'd': now.date(),
                'e': now.time().replace(tzinfo=timezone.utc),
                'f': now,
            },
        )

    def _assertJsonscriptTag(self, expected, data, args=''):
        with self.assertNoException():
            template = Template('{% load creme_core_tags %}{% jsondata data ' + args + ' %}')
            output = template.render(Context({'data': data, 'name': 'script#1'}))

        self.assertHTMLEqual(expected, output)
        # if expected != output:
        #     self.fail('{} != {}'.format(expected, output))  # TODO: if self.maxDiff is None ??

    def _assertJsonscriptNode(self, expected, data, args=''):
        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}'
                '{% blockjsondata ' + args + ' %}' + data + '{% endblockjsondata %}'
            )
            output = template.render(Context({'name': 'script#1'}))

        self.assertHTMLEqual(expected, output)

    def test_jsondata_tag(self):
        # self.maxDiff = None
        self._assertJsonscriptTag('', None)

        self._assertJsonscriptTag('<script type="application/json"><!--  --></script>', '')

        data = '-->'
        self._assertJsonscriptTag(
            r'<script type="application/json"><!-- ' + escapejson(data) + ' --></script>',
            data
        )

        data = '--></script><script'
        self._assertJsonscriptTag(
            r'<script type="application/json"><!-- ' + escapejson(data) + ' --></script>',
            data
        )

        data = '-->&gt;/script&lt;&gt;script'
        self._assertJsonscriptTag(
            r'<script type="application/json"><!-- ' + escapejson(data) + ' --></script>',
            data
        )

        self._assertJsonscriptTag('<script type="application/json"><!-- [] --></script>', [])
        self._assertJsonscriptTag('<script type="application/json"><!-- {} --></script>', {})
        # self._assertJsonscriptTag(
        #     r'<script type="application/json"><!-- '
        #     + escapejson('{"a":12,"b":"-->alert();<script/>"}')
        #     + ' --></script>',
        #     {"a": 12, "b": "-->alert();<script/>"}
        #   )  # TODO: uncomment when order is guaranteed (Python 3.8)
        self._assertJsonscriptTag(
            r'<script type="application/json"><!-- '
            + escapejson('{"b":"-->alert();<script/>"}')
            + ' --></script>',
            {'b': '-->alert();<script/>'}
        )

        # self._assertJsonscriptTag(
        #     r'<script type="application/json"><!-- '
        #     + escapejson('{"a":12,"b":0.47,"c":"' + ugettext('User') + '"}')
        #     + r' --></script>',
        #     {"a": 12, "b": Decimal("0.47"), "c": ugettext_lazy('User')}
        # )  # TODO: uncomment when order is guaranteed (Python 3.8)
        self._assertJsonscriptTag(
            r'<script type="application/json"><!-- {"a":12} --></script>',
            {'a': 12}
        )
        self._assertJsonscriptTag(
            r'<script type="application/json"><!-- {"b":0.47} --></script>',
            {'b': Decimal("0.47")}
        )
        self._assertJsonscriptTag(
            r'<script type="application/json"><!-- '
            + escapejson('{"c":"%s"}' % gettext('User'))
            + r' --></script>',
            {'c': gettext_lazy('User')}
        )

        self._assertJsonscriptTag(
            '<script type="application/json" class="test" name="&lt;script/&gt;">'
            '<!--  -->'
            '</script>',
            '', "class='test' name='<script/>'",
        )

        self._assertJsonscriptTag(
            '<script type="application/json" class="test" name="script#1">'
            '<!--  --></script>',
            '', "class='test' name=name",
        )

    def test_jsondata_node(self):
        # self.maxDiff = None
        self._assertJsonscriptNode(
            '<script type="application/json"><!--  --></script>',
            ''
        )

        data = '-->'
        self._assertJsonscriptNode(
            r'<script type="application/json"><!-- ' + escapejson(data) + ' --></script>',
            data
        )

        data = '--></script><script'
        self._assertJsonscriptNode(
            r'<script type="application/json"><!-- ' + escapejson(data) + ' --></script>',
            data
        )

        data = '-->&gt;/script&lt;&gt;script'
        self._assertJsonscriptNode(
            r'<script type="application/json"><!-- ' + escapejson(data) + ' --></script>',
            data
        )

        self._assertJsonscriptNode('<script type="application/json"><!-- [] --></script>', '[]')
        self._assertJsonscriptNode('<script type="application/json"><!-- {} --></script>', '{}')

        data = '{"a":12,"b":"-->alert();<script/>"}'
        self._assertJsonscriptNode(
            r'<script type="application/json"><!-- ' + escapejson(data) + ' --></script>',
            data
        )

        self._assertJsonscriptNode(
            '<script type="application/json" class="test" name="&lt;script/&gt;">'
            '<!--  --></script>',
            '', "class='test' name='<script/>'",
        )

        self._assertJsonscriptNode(
            '<script type="application/json" class="test" name="script#1">'
            '<!--  --></script>',
            '', "class='test' name=name",
        )

    def test_optionize_model_iterable_filter(self):
        user = self.create_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Amestris')
        orga2 = create_orga(name='Spectre')
        orgas = [orga1, orga2]

        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}{{data|optionize_model_iterable|jsonify|safe}}'
            )
            render = template.render(Context({'data': orgas}))

        with self.assertNoException():
            deserialized = json_load(render.strip())

        self.assertListEqual(
            [[orga1.id, str(orga1)], [orga2.id, str(orga2)]],
            deserialized
        )

        # ---
        with self.assertNoException():
            template = Template(
                "{% load creme_core_tags %}{{data|optionize_model_iterable:'dict'|jsonify|safe}}"
            )
            render = template.render(Context({'data': orgas}))

        with self.assertNoException():
            deserialized = json_load(render.strip())

        self.assertListEqual(
            [
                {'value': orga1.id, 'label': str(orga1)},
                {'value': orga2.id, 'label': str(orga2)},
            ],
            deserialized
        )

    def test_url01(self):
        "No parameter."
        url_name = 'creme_core__delete_entities'

        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}'
                '<a href="{{url_name|url}}">Link</a>'
            )
            render = template.render(Context({'url_name': url_name}))

        self.assertEqual(
            '<a href="{}">Link</a>'.format(reverse(url_name)),
            render.strip(),
        )

    def test_url02(self):
        "One parameter."
        url_name = 'creme_core__delete_entity'
        entity_id = 12

        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}'
                '<a href="{{url_name|url:entity_id}}">Link</a>'
            )
            render = template.render(
                Context({'url_name': url_name, 'entity_id': entity_id})
            )

        self.assertEqual(
            f'<a href="{reverse(url_name, args=(entity_id,))}">Link</a>',
            render.strip(),
        )

    def test_url_join_empty(self):
        with self.assertNoException():
            render2 = Template(
                r'{% load creme_core_tags %}'
                r'{% url_join %}'
            ).render(Context({}))

        self.assertFalse(render2.strip())

    def test_url_join_no_argument(self):
        url = '/creme_core/foobar'

        with self.assertNoException():
            render2 = Template(
                r'{% load creme_core_tags %}'
                r'{% url_join my_url as my_uri %}'
                r'<a href="{{my_uri}}">Link</a>'
            ).render(Context({'my_url': url}))

        self.assertHTMLEqual(f'<a href="{url}">Link</a>', render2.strip())

    def test_url_join_several_arguments(self):
        url = '/creme_core/foobar'
        brick_id1 = 'brick-core-entities'
        brick_id2 = 'brick-core-properties'

        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}'
                '{% url_join my_url brick_id_01=brick_id1 brick_id_02=brick_id2 as my_uri %}'
                '<a href="{{my_uri}}">Link</a>'
            )
            render = template.render(Context(
                {'my_url': url, 'brick_id1': brick_id1, 'brick_id2': brick_id2}
            ))

        self.assertIn(
            render.strip(),
            (
                f'<a href="{url}?brick_id_01={brick_id1}&brick_id_02={brick_id2}">Link</a>',
                f'<a href="{url}?brick_id_02={brick_id2}&brick_id_01={brick_id1}">Link</a>',
            ),
        )

    def test_url_join_error(self):
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_core_tags %}'
                r'{% url_join "/creme_core/foobar" 1 %}'
            ).render(Context({}))

        self.assertEqual(
            '"url_join" takes one & only one positional argument (the base URL)',
            str(cm.exception),
        )

    def test_url_join_list(self):
        "List arguments."
        url = '/creme_core/foobar'
        brick_ids = ['brick-core-entities', 'brick-core-properties']

        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{% url_join my_url brick_id=brick_id as my_uri %}'
                '<a href="{{my_uri}}">Link</a>'
            ).render(Context(
                {'my_url': url, 'brick_id': brick_ids}
            ))

        self.assertEqual(
            f'<a href="{url}?brick_id={brick_ids[0]}&brick_id={brick_ids[1]}">Link</a>',
            render.strip()
        )

    def test_url_join_append_argument(self):
        "Already a GET parameter"
        url = '/creme_core/foobar?arg1=value'
        brick_id = 'brick-core-entities'

        with self.assertNoException():
            template = Template(
                '{% load creme_core_tags %}'
                '{% url_join my_url brick_id=brick_id as my_uri %}'
                '<a href="{{my_uri}}">Link</a>'
            )
            render = template.render(Context({'my_url': url, 'brick_id': brick_id}))

        self.assertEqual(
            f'<a href="{url}&brick_id={brick_id}">Link</a>',
            render.strip()
        )

    def test_url_join_append_list_arg(self):
        "Already a GET parameter + list parameter."
        url = '/creme_core/foobar?arg1=value'
        brick_ids = ['brick-core-entities', 'brick-core-properties']

        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{% url_join my_url brick_id=brick_id as my_uri %}'
                '<a href="{{my_uri}}">Link</a>'
            ).render(
                Context({'my_url': url, 'brick_id': brick_ids})
            )

        self.assertEqual(
            f'<a href="{url}&brick_id={brick_ids[0]}&brick_id={brick_ids[1]}">Link</a>',
            render.strip()
        )

    def test_url_join_escaping(self):
        url = '/creme_core/search'
        search = 'orange & lemons'

        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{% url_join my_url value=search as my_uri %}'
                '<a href="{{my_uri}}">Link</a>'
            ).render(Context({'my_url': url, 'search': search}))

        self.assertEqual(
            '<a href="{}?value={}">Link</a>'.format(url, 'orange+%26+lemons'),
            render.strip(),
        )

    def test_escapecss(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '.foo .bar-label:before {'
                '   content: "{{value|escapecss}}";'
                '}'
            ).render(Context({
                'value': '''foo© '" 2020><''',
            }))

        self.assertEqual(
            r'''.foo .bar-label:before {'''
            r'''   content: "foo© \0027 \0022  2020\003E \003C";'''
            r'''}''',
            render.strip(),
        )
