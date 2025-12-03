from datetime import datetime, timezone
from decimal import Decimal
from functools import partial
from json import loads as json_load

from django.template import Context, Template, TemplateSyntaxError
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    Currency,
    CustomEntityType,
    FakeContact,
    FakeInvoice,
    FakeOrganisation,
    FakeTicket,
    FieldsConfig,
    Language,
    PinnedEntity,
)
from creme.creme_core.utils.html import escapejson

from ..base import CremeTestCase


class CremeCoreTagsTestCase(CremeTestCase):
    def test_app_verbose_name(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{{"creme_core"|app_verbose_name}}#'
                '{{"creme_config"|app_verbose_name}}#'
                '{{"unknown"|app_verbose_name}}#'
                '{{"unknown"|app_verbose_name:"???"}}'
            ).render(Context())

        self.assertEqual(
            '#'.join([_('Core'), _('General configuration'), '?', '???']),
            render.strip(),
        )

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
            render = Template(
                '{% load creme_core_tags %}'
                '{{x|sub:3}}#{{13|sub:6}}'
            ).render(Context({'x': 5}))

        self.assertEqual('2#7', render.strip())

    def test_mult(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{{x|mult:3}}#{{10|mult:6}}'
            ).render(Context({'x': 5}))

        self.assertEqual('15#60', render.strip())

    def test_idiv(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{{x|idiv:2}}#{{13|idiv:3}}'
            ).render(Context({'x': 5}))

        self.assertEqual('2#4', render.strip())

    def test_mod(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{{x|mod:3}}#{{13|mod:6}}'
            ).render(Context({'x': 5}))

        self.assertEqual('2#1', render.strip())

    def test_has_attr(self):
        with self.assertNoException():
            render = Template(
                "{% load creme_core_tags %}"
                "{% if orga|has_attr:'name' %}OK{% else %}KO{% endif %}#"
                "{% if orga|has_attr:'invalid' %}OK{% else %}KO{% endif %}"
            ).render(Context({'orga': FakeOrganisation(name='Amestris')}))

        self.assertEqual('OK#KO', render.strip())

    def test_format(self):
        with self.assertNoException():
            render = Template(
                "{% load creme_core_tags %}"
                "{{ 'world'|format:'Hello %s' }}"
            ).render(Context())

        self.assertEqual('Hello world', render.strip())

    def test_format_string_brace_named(self):
        with self.assertNoException():
            render = Template(
                "{% load creme_core_tags %}"
                "{% format_string_brace_named 'Hello {first} & {second}' first='Python' second='Django' %}"  # NOQA
            ).render(Context())

        self.assertEqual('Hello Python &amp; Django', render.strip())

    def test_listify(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{% listify email phone as mylist %}'
                '{{mylist|join:","}}'
            ).render(Context({
                'email': 'foo@bar.org',
                'phone': '123-FOOBAR',
            }))

        self.assertEqual('foo@bar.org,123-FOOBAR', render.strip())

    def test_filter_empty(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{{mylist|filter_empty|join:","}}'
            ).render(Context({
                'mylist': ['', 'foo@bar.org', None, '123-FOOBAR', False],
            }))

        self.assertEqual('foo@bar.org,123-FOOBAR', render.strip())

    def test_grouper(self):
        ctxt = Context({'mylist': ['A', 'B', 'C', 'D', 'E', 'F']})

        with self.assertNoException():
            render1 = Template(
                '{% load creme_core_tags %}'
                '{% for couple in mylist|grouper:2 %}{{couple.0}},{{couple.1}}#{% endfor %}'
            ).render(ctxt)

        self.assertEqual('A,B#C,D#E,F#', render1.strip())

        # ---
        with self.assertNoException():
            render2 = Template(
                '{% load creme_core_tags %}'
                '{% for couple in mylist|grouper:3 %}'
                '{{couple.0}},{{couple.1}},{{couple.2}}#'
                '{% endfor %}'
            ).render(ctxt)

        self.assertEqual('A,B,C#D,E,F#', render2.strip())

    def test_range(self):
        with self.assertNoException():
            render1 = Template(
                '{% load creme_core_tags %}'
                '{% for x in 3|range %}{{x}}#{% endfor %}'
            ).render(Context())

        self.assertEqual('0#1#2#', render1.strip())

        # ---
        with self.assertNoException():
            render2 = Template(
                '{% load creme_core_tags %}'
                '{% for x in 4|range:1 %}{{x}}#{% endfor %}'
            ).render(Context())

        self.assertEqual('1#2#3#4#', render2.strip())

    def test_uca_sort(self):
        with self.assertNoException():
            render1 = Template(
                '{% load creme_core_tags %}'
                '{% for word in words|uca_sort %}{{word}},{% endfor %}'
            ).render(Context({'words': ['Éléphant', 'Apple', 'Zebra', 'Element']}))

        self.assertEqual('Apple,Element,Éléphant,Zebra,', render1.strip())

    def test_verbose_models(self):
        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Shop'
        ce_type.plural_name = 'Shops'
        ce_type.save()

        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{% with m=models|verbose_models %}{{m.0}}, {{m.1}}, {{m.2}}{% endwith %}'
            ).render(Context({
                'models': [FakeContact, FakeOrganisation, ce_type.entity_model],
            }))

        self.assertEqual(
            f'Test Contact, Test Organisation, {ce_type.name}', render.strip(),
        )

    def test_templatize(self):
        with self.assertNoException():
            render = Template(
                r'{% load creme_core_tags %}'
                r'{% templatize "{{columns|length}}" as colspan %}'
                r'<h1>{{colspan}}</h1>'
            ).render(Context({'columns': range(3)}))

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

    def test_allowed_str(self):
        root = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=root, name='<em>Amestris</em>')

        with self.assertNoException():
            render1 = Template(
                r'{% load creme_core_tags %}{{orga|allowed_str:user}}'
            ).render(Context({'orga': orga, 'user': root}))

        self.assertEqual('&lt;em&gt;Amestris&lt;/em&gt;', render1)

        # ---
        role = self.create_role(allowed_apps=['creme_core'])
        self.add_credentials(role, own='*')
        user = self.create_user(role=role)

        with self.assertNoException():
            render2 = Template(
                r'{% load creme_core_tags %}{{orga|allowed_str:user}}'
            ).render(Context({'orga': orga, 'user': user}))

        self.assertEqual(_('Entity #{id} (not viewable)').format(id=orga.id), render2)

        # ---
        lang = Language(name='Elfic')

        with self.assertNoException():
            render3 = Template(
                r'{% load creme_core_tags %}{{obj|allowed_str:user}}'
            ).render(Context({'obj': lang, 'user': root}))

        self.assertEqual(lang.name, render3)

    def test_format_amount(self):
        with self.assertNoException():
            render1 = Template(
                r'{% load creme_core_tags %}{{value|format_amount:currency}}'
            ).render(Context({
                'value': Decimal('4.65'),
                'currency': Currency.objects.first(),
            }))

        self.assertIn('4', render1)
        self.assertIn('65', render1)

    # TODO: complete with other field types
    def test_print_field(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(
            user=user, name='<br/>Amestris', url_site='www.amestris.org',
            # email='contact@mestris.org',
        )

        with self.assertNoException():
            render1 = Template(
                "{% load creme_core_tags %}"
                "<ul>"
                "<li>{% print_field object=entity field='name' %}</li>"
                "<li>{% print_field object=entity field='url_site' %}</li>"
                "</ul>"
            ).render(Context({'entity': orga, 'user': user}))

        self.assertHTMLEqual(
            '<ul>'
            '<li>&lt;br/&gt;Amestris</li>'
            '<li><a href="www.amestris.org" target="_blank">www.amestris.org</a></li>'
            '</ul>',
            render1,
        )

        # ---
        with self.assertNoException():
            render2 = Template(
                "{% load creme_core_tags %}"
                "{% print_field object=entity field='url_site' tag=tag %}"
            ).render(Context({
                'entity': orga, 'user': user, 'tag': ViewTag.TEXT_PLAIN,
            }))

        self.assertEqual(orga.url_site, render2.strip())

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_core_tags %}'
                r'{% print_field %}'
            )

        self.assertEqual(
            "'print_field' did not receive value(s) for the argument(s): 'object', 'field'",
            str(cm.exception),
        )

        # ---
        with self.assertRaises(TemplateSyntaxError) as cm:
            Template(
                r'{% load creme_core_tags %}'
                r'{% print_field entity "url_site" %}'
            )

        self.assertEqual(
            "'print_field' received too many positional arguments",
            str(cm.exception),
        )

    def _assertJsonifyFilter(self, expected, data):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}{{data|jsonify|safe}}'
            ).render(Context({'data': data}))

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
                'c': _('User'),
                'd': '2018-01-12',
                'e': '08:12:25.012Z',
                'f': '2018-01-12T08:12:25.012Z',
            },
            {
                'a': 12,
                'b': Decimal('0.47'),
                'c': _('User'),
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

    def _assertBlockjsondata(self, expected, data, args=''):
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
        self._assertJsonscriptTag(
            r'<script type="application/json"><!-- '
            + escapejson('{"a":12,"b":"-->alert();<script/>"}')
            + ' --></script>',
            {'a': 12, 'b': '-->alert();<script/>'},
        )

        self._assertJsonscriptTag(
            r'<script type="application/json"><!-- '
            + escapejson('{"a":12,"b":0.47,"c":"%s"}' % _('User'))
            + r' --></script>',
            {'a': 12, 'b': Decimal('0.47'), 'c': _('User')},
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

    def test_blockjsondata(self):
        # self.maxDiff = None
        self._assertBlockjsondata(
            expected='<script type="application/json"><!--  --></script>',
            data='',
        )

        data = '-->'
        self._assertBlockjsondata(
            expected=r'<script type="application/json"><!-- ' + escapejson(data) + ' --></script>',
            data=data,
        )

        data = '--></script><script'
        self._assertBlockjsondata(
            expected=r'<script type="application/json"><!-- ' + escapejson(data) + ' --></script>',
            data=data,
        )

        data = '-->&gt;/script&lt;&gt;script'
        self._assertBlockjsondata(
            expected=r'<script type="application/json"><!-- ' + escapejson(data) + ' --></script>',
            data=data,
        )

        self._assertBlockjsondata('<script type="application/json"><!-- [] --></script>', '[]')
        self._assertBlockjsondata('<script type="application/json"><!-- {} --></script>', '{}')

        data = '{"a":12,"b":"-->alert();<script/>"}'
        self._assertBlockjsondata(
            expected=r'<script type="application/json"><!-- ' + escapejson(data) + ' --></script>',
            data=data,
        )

        self._assertBlockjsondata(
            expected=(
                '<script type="application/json" class="test" name="&lt;script/&gt;">'
                '<!--  -->'
                '</script>'
            ),
            data='',
            args="class='test' name='<script/>'",
        )

        self._assertBlockjsondata(
            expected=(
                '<script type="application/json" class="test" name="script#1">'
                '<!--  -->'
                '</script>'
            ),
            data='',
            args="class='test' name=name",
        )

        self._assertBlockjsondata(
            expected=(
                '<script type="application/json" name="script#1">'
                '<!--  -->'
                '</script>'
            ),
            data='',
            args="type='ignore-me' name=name",
        )

    def test_optionize_model_iterable_filter(self):
        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Amestris')
        orga2 = create_orga(name='Spectre')
        orgas = [orga1, orga2]

        with self.assertNoException():
            render1 = Template(
                '{% load creme_core_tags %}{{data|optionize_model_iterable|jsonify|safe}}'
            ).render(Context({'data': orgas}))

        with self.assertNoException():
            deserialized = json_load(render1.strip())

        self.assertListEqual(
            [[orga1.id, str(orga1)], [orga2.id, str(orga2)]],
            deserialized,
        )

        # ---
        with self.assertNoException():
            render2 = Template(
                "{% load creme_core_tags %}{{data|optionize_model_iterable:'dict'|jsonify|safe}}"
            ).render(Context({'data': orgas}))

        with self.assertNoException():
            deserialized = json_load(render2.strip())

        self.assertListEqual(
            [
                {'value': orga1.id, 'label': str(orga1)},
                {'value': orga2.id, 'label': str(orga2)},
            ],
            deserialized,
        )

    def test_escape_css(self):
        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '<style>.my_class { content:  "{{content|escapecss}}"; }</style>'
            ).render(Context({'content': '<foobar>'}))

        self.assertEqual(
            r'<style>.my_class { content:  "\003C foobar\003E"; }</style>',
            render.strip(),
        )

    def test_url01(self):
        "No parameter."
        url_name = 'creme_core__delete_entities'

        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '<a href="{{url_name|url}}">Link</a>'
            ).render(Context({'url_name': url_name}))

        self.assertEqual(
            f'<a href="{reverse(url_name)}">Link</a>',
            render.strip(),
        )

    def test_url02(self):
        "One parameter."
        url_name = 'creme_core__delete_entity'
        entity_id = 12

        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '<a href="{{url_name|url:entity_id}}">Link</a>'
            ).render(Context({'url_name': url_name, 'entity_id': entity_id}))

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
            render = Template(
                '{% load creme_core_tags %}'
                '{% url_join my_url brick_id_01=brick_id1 brick_id_02=brick_id2 as my_uri %}'
                '<a href="{{my_uri}}">Link</a>'
            ).render(Context({'my_url': url, 'brick_id1': brick_id1, 'brick_id2': brick_id2}))

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
            ).render(Context({'my_url': url, 'brick_id': brick_ids}))

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
            ).render(Context({'my_url': url, 'brick_id': brick_ids}))

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
            ).render(Context({'value': '''foo© '" 2020><'''}))

        self.assertEqual(
            r'''.foo .bar-label:before {'''
            r'''   content: "foo© \0027 \0022  2020\003E \003C";'''
            r'''}''',
            render.strip(),
        )

    def test_is_field_hidden(self):
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
        )

        user = self.get_root_user()
        contact = FakeContact.objects.create(
            user=user, first_name='Edward', last_name='Elric', phone='123456',
        )

        # With instance ---
        with self.assertNoException():
            render1 = Template(
                '{% load creme_core_tags %}'
                '{% if o|is_field_hidden:"first_name" %}?{% else %}{{o.first_name}}{% endif %}#'
                '{% if o|is_field_hidden:"phone" %}?{% else %}{{o.phone}}{% endif %}'
            ).render(Context({'o': contact}))

        self.assertEqual(f'{contact.first_name}#?', render1.strip())

        # With ContentType ---
        with self.assertNoException():
            render2 = Template(
                '{% load creme_core_tags %}'
                '{% if ctype|is_field_hidden:"first_name" %}?{% else %}First name{% endif %}#'
                '{% if ctype|is_field_hidden:"phone" %}?{% else %}Phone{% endif %}'
            ).render(Context({'ctype': contact.entity_type}))

        self.assertEqual('First name#?', render2.strip())

    def test_get_hidden_fields(self):
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
        )

        user = self.get_root_user()
        contact = FakeContact.objects.create(
            user=user, first_name='Edward', last_name='Elric', phone='123456',
        )
        ctxt = Context({
            'fields_configs': FieldsConfig.LocalCache(),  # See processors
            'obj': contact,
        })

        # With instance ---
        with self.assertNoException():
            render1 = Template(
                '{% load creme_core_tags %}'
                '{% get_hidden_fields obj as hidden_fields %}'
                '{% if "first_name" in hidden_fields %}?{% else %}{{obj.first_name}}{% endif %}#'
                '{% if "phone" in hidden_fields %}?{% else %}{{obj.phone}}{% endif %}'
            ).render(ctxt)

        self.assertEqual(f'{contact.first_name}#?', render1.strip())

        # With ContentType ---
        with self.assertNoException():
            render2 = Template(
                '{% load creme_core_tags %}'
                '{% get_hidden_fields obj.entity_type as hidden_fields %}'
                '{% if "first_name" in hidden_fields %}?{% else %}First name{% endif %}#'
                '{% if "phone" in hidden_fields %}?{% else %}Phone{% endif %}'
            ).render(ctxt)

        self.assertEqual('First name#?', render2.strip())

    def test_inner_edition_uri(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Amestris')

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)

        with self.assertNoException():
            render1 = Template(
                '{% load creme_core_tags %}'
                '{% inner_edition_uri instance=entity cells=cells %}'
            ).render(Context({
                'entity': orga,
                'cells': [build_cell(name='name'), build_cell(name='phone')],
            }))

        self.assertEqual(
            reverse(
                'creme_core__inner_edition',
                args=(orga.entity_type_id, orga.id)
            ) + '?cell=regular_field-name&amp;cell=regular_field-phone',
            render1.strip(),
        )

        # # cell instance + callback URL (DEPRECATED) ---
        # url = orga.get_lv_absolute_url()
        # with self.assertNoException():
        #     render2 = Template(
        #         '{% load creme_core_tags %}'
        #         '{% inner_edition_uri instance=entity cells=cell callback_url=url %}'
        #     ).render(Context({
        #         'entity': orga,
        #         'cell': build_cell(name='name'),
        #         'url': url,
        #     }))
        #
        # self.assertEqual(
        #     reverse(
        #         'creme_core__inner_edition',
        #         args=(orga.entity_type_id, orga.id)
        #     ) + f'?cell=regular_field-name&amp;callback_url={url}',
        #     render2.strip(),
        # )

    def test_get_cloning_info(self):
        user = self.get_root_user()

        # Entity is not clonable ---
        ticket = FakeTicket.objects.create(user=user, title='Golden ticket')

        with self.assertNoException():
            render1 = Template(
                '{% load creme_core_tags %}'
                '{% get_cloning_info entity=entity user=user as cloning %}'
                '{% if not cloning.enabled %}NOPE{% endif %}'
            ).render(Context({'user': user, 'entity': ticket}))

        self.assertEqual('NOPE', render1.strip())

        # OK ---
        contact = FakeContact.objects.create(user=user, first_name='Ryu', last_name='Tadera')

        with self.assertNoException():
            render2 = Template(
                '{% load creme_core_tags %}'
                '{% get_cloning_info entity=entity user=user as cloning %}'
                '{% if cloning.enabled %}'
                '<a class="{% if cloning.allowed %}allowed{% endif %}" href="{{cloning.url}}">'
                'Clone'
                '</a>'
                '{% endif %}'
            ).render(Context({'user': user, 'entity': contact}))

        url = reverse('creme_core__clone_entity')
        self.assertHTMLEqual(
            f'<a class="allowed" href="{url}">Clone</a>',
            render2.strip(),
        )

        # Forbidden ---
        invoice = FakeInvoice.objects.create(user=user, name='Invoice #1', number='00001')

        with self.assertNoException():
            render3 = Template(
                '{% load creme_core_tags %}'
                '{% get_cloning_info entity=entity user=user as cloning %}'
                '{% if cloning.enabled %}'
                '<a class="{% if not cloning.allowed %}forbidden{% endif %}"'
                '   href="{{cloning.url}}"'
                '   data-error="{{cloning.error}}"'
                '>Clone'
                '</a>'
                '{% endif %}'
            ).render(Context({'user': user, 'entity': invoice}))

        self.assertHTMLEqual(
            '<a class="forbidden" href="" '
            '   data-error="an invoice with a number cannot be cloned" '
            '>Clone</a>',
            render3.strip(),
        )

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_get_deletion_info(self):
        user = self.get_root_user()
        ticket = FakeTicket.objects.create(user=user, title='Golden ticket')

        # Entity is not deletable ---
        with self.assertNoException():
            render1 = Template(
                '{% load creme_core_tags %}'
                '{% get_deletion_info entity=entity user=user as deletion %}'
                '{% if not deletion.enabled %}NOPE{% endif %}'
            ).render(Context({'user': user, 'entity': ticket}))

        self.assertEqual('NOPE', render1.strip())

        # Entity not in the trash ---
        contact = FakeContact.objects.create(user=user, first_name='Ryu', last_name='Tadera')

        template = Template(
            '{% load creme_core_tags %}'
            '{% get_deletion_info entity=entity user=user as deletion %}'
            '{% if deletion.enabled %}'
            '<a class="{% if deletion.allowed %}allowed{% endif %}"'
            '   href="{{deletion.url}}"'
            '   data-confirm="{{deletion.confirmation}}"'
            '>{{deletion.label}}'
            '</a>'
            '{% endif %}'
        )
        ctxt = Context({'user': user, 'entity': contact})

        with self.assertNoException():
            render2 = template.render(ctxt)

        self.assertHTMLEqual(
            f'<a class="allowed" '
            f'   href="{contact.get_delete_absolute_url()}" '
            f'   data-confirm="{_("Do you really want to send this entity to the trash?")}" '
            f'>{_("Delete")}</a>',
            render2.strip(),
        )

        # Entity is in the trash ---
        contact.is_deleted = True
        contact.save()

        with self.assertNoException():
            render3 = template.render(ctxt)

        self.assertHTMLEqual(
            f'<a class="allowed" '
            f'   href="{contact.get_delete_absolute_url()}" '
            f'   data-confirm="{_("Do you really want to delete this entity definitely?")}" '
            f'>{_("Delete permanently")}</a>',
            render3.strip(),
        )

        # Forbidden ---
        user_contact = FakeContact.objects.create(
            user=user, first_name='Jin', last_name='Kagemori', is_user=user,
        )

        with self.assertNoException():
            render3 = Template(
                '{% load creme_core_tags %}'
                '{% get_deletion_info entity=entity user=user as deletion %}'
                '{% if deletion.enabled %}'
                '<a class="{% if not deletion.allowed %}forbidden{% endif %}"'
                '   href="{{deletion.url}}"'
                '   data-error="{{deletion.error}}"'
                '>{{deletion.label}}'
                '</a>'
                '{% endif %}'
            ).render(Context({'user': user, 'entity': user_contact}))

        self.assertHTMLEqual(
            f'<a class="forbidden" href="" '
            f'   data-error="A user is associated with this contact." '
            f'>{_("Delete")}</a>',
            render3.strip(),
        )

    @override_settings(PINNED_ENTITIES_SIZE=5)
    def test_is_pinned(self):
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Edward', last_name='Elric')
        contact2 = create_contact(first_name='Alphonse', last_name='Elric')

        PinnedEntity.objects.create(user=user, real_entity=contact1)

        with self.assertNumQueries(2):
            with self.assertNoException():
                render = Template(
                    '{% load creme_core_tags %}'
                    '{{contact1|is_pinned:user}}#{{contact2|is_pinned:user}}'
                    '#{{contact1|is_pinned:user}}'
                ).render(Context({
                    'user': user,
                    'contact1': contact1,
                    'contact2': contact2,
                }))

        self.assertEqual('True#False#True', render.strip())

    @override_settings(PINNED_ENTITIES_SIZE=2)
    def test_has_max_pins(self):
        user1 = self.get_root_user()
        user2 = self.create_user()

        create_contact = partial(FakeContact.objects.create, user=user1)
        contact1 = create_contact(first_name='Edward', last_name='Elric')
        contact2 = create_contact(first_name='Alphonse', last_name='Elric')

        create_pinned = PinnedEntity.objects.create
        create_pinned(real_entity=contact1, user=user1)
        create_pinned(real_entity=contact2, user=user1)
        create_pinned(real_entity=contact1, user=user2)

        with self.assertNoException():
            render = Template(
                '{% load creme_core_tags %}'
                '{{user1|has_max_pins}}#{{user2|has_max_pins}}'
            ).render(Context({
                'user1': user1,
                'user2': user2,
                'contact1': contact1,
                'contact2': contact2,
            }))

        self.assertEqual('True#False', render.strip())
