# -*- coding: utf-8 -*-

try:
    from functools import partial
    from json import loads as json_load

    from django.contrib.contenttypes.models import ContentType
    # from django.db.models.fields import FieldDoesNotExist
    from django.template import Template, Context # TemplateSyntaxError
    from django.urls import reverse

    from ..base import CremeTestCase

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    # from creme.creme_core.forms.bulk import _CUSTOMFIELD_FORMAT
    # from creme.creme_core.gui.bulk_update import bulk_update_registry
    from creme.creme_core.models import SetCredentials, FakeOrganisation  # CustomField
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class CremeCoreTagsTestCase(CremeTestCase):
    def test_get_by_index(self):
        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{{xs|get_by_index:0}}#'
                                '{{xs|get_by_index:1}}#'
                                '{{ys|get_by_index:1}}'
                               )
            render = template.render(Context({'xs': [1, 2, 3], 'ys': (4, 5)}))

        self.assertEqual('1#2#5', render.strip())

        template = Template('{% load creme_core_tags %}{{xs|get_by_index:2}}')
        with self.assertRaises(IndexError):
            template.render(Context({'xs': [1, 2]}))

    def test_lt(self):
        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% with xlesser=x|lt:3 xequal=x|lt:2 xgreater=x|lt:1 %}'
                                '{% if xlesser %}True{% endif %}#'
                                '{% if not xequal %}False{% endif %}#'
                                '{% if not xgreater %}False{% endif %}#'
                                '{% if 0|lt:1 %}True{% endif %}'
                                '{% endwith %}'
                               )
            render = template.render(Context({'x': 2}))

        self.assertEqual('True#False#False#True', render.strip())

    def test_lte(self):
        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% with xlesser=x|lte:3 xequal=x|lte:2 xgreater=x|lte:1 %}'
                                '{% if xlesser %}True{% endif %}#'
                                '{% if xequal %}True{% endif %}#'
                                '{% if not xgreater %}False{% endif %}#'
                                '{% if 0|lte:1 %}True{% endif %}'
                                '{% endwith %}'
                               )
            render = template.render(Context({'x': 2}))

        self.assertEqual('True#True#False#True', render.strip())

    def test_gt(self):
        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% with xlesser=x|gt:3 xequal=x|gt:2 xgreater=x|gt:1 %}'
                                '{% if not xlesser %}False{% endif %}#'
                                '{% if not xequal %}False{% endif %}#'
                                '{% if xgreater %}True{% endif %}#'
                                '{% if 4|gt:3 %}True{% endif %}'
                                '{% endwith %}'
                               )
            render = template.render(Context({'x': 2}))

        self.assertEqual('False#False#True#True', render.strip())

    def test_gte(self):
        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% with xlesser=x|gte:3 xequal=x|gte:2 xgreater=x|gte:1 %}'
                                '{% if not xlesser %}False{% endif %}#'
                                '{% if xequal %}True{% endif %}#'
                                '{% if xgreater %}True{% endif %}#'
                                '{% if 4|gte:3 %}True{% endif %}'
                                '{% endwith %}'
                               )
            render = template.render(Context({'x': 2}))

        self.assertEqual('False#True#True#True', render.strip())

    def test_eq(self):
        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% with xlesser=x|eq:3 xequal=x|eq:2 xgreater=x|eq:1 %}'
                                '{% if not xlesser %}False{% endif %}#'
                                '{% if xequal %}True{% endif %}#'
                                '{% if not xgreater %}False{% endif %}#'
                                '{% if 3|eq:3 %}True{% endif %}'
                                '{% endwith %}'
                               )
            render = template.render(Context({'x': 2}))

        self.assertEqual('False#True#False#True', render.strip())

    def test_templatize(self):
        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% templatize "{{columns|length}}" as colspan %}'
                                '<h1>{{colspan}}</h1>'
                               )
            render = template.render(Context({'columns': range(3)}))

        self.assertEqual('<h1>3</h1>', render.strip())

    # TODO: complete with other field types
    def test_print_field(self):
        self.login()
        orga = FakeOrganisation.objects.create(user=self.user, name='<br/>Amestris', url_site='www.amestris.org')

        with self.assertNoException():
            template = Template("{% load creme_core_tags %}"
                                "<ul>"
                                "<li>{% print_field object=entity field='name' %}</li>"
                                "<li>{% print_field object=entity field='url_site' %}</li>"
                                "</ul>"
                               )
            render = template.render(Context({'entity': orga, 'user': self.user}))

        self.assertEqual('<ul>'
                         '<li>&lt;br/&gt;Amestris</li>'
                         '<li><a href="www.amestris.org" target="_blank">www.amestris.org</a></li>'
                         '</ul>',
                         render.strip()
                        )

    def test_has_perm_to01(self):
        self.login()
        orga = FakeOrganisation.objects.create(user=self.user, name='Xing')

        with self.assertNoException():
            template = Template("{% load creme_core_tags %}"
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
                               )
            render = template.render(Context({'entity': orga,
                                              'user':   self.user,
                                              'ct':     ContentType.objects.get_for_model(FakeOrganisation),
                                             }))

        self.assertEqual('True' * 11, render.strip())

    def test_has_perm_to02(self):
        self.login(is_superuser=False)
        orga = FakeOrganisation.objects.create(user=self.user, name='Xerces')

        with self.assertNoException():
            template = Template("{% load creme_core_tags %}"
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
                               )
            render = template.render(Context({'entity': orga,
                                              'user':   self.user,
                                              'ct':     ContentType.objects.get_for_model(FakeOrganisation),
                                             }))

        self.assertEqual('False' * 11, render.strip())

    def test_has_perm_to03(self):
        self.login(is_superuser=False, allowed_apps=['creme_core'], creatable_models=[FakeOrganisation])
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        orga = FakeOrganisation.objects.create(user=self.user, name='Amestris')
        self.assertTrue(self.user.has_perm_to_view(orga))

        with self.assertNoException():
            template = Template("{% load creme_core_tags %}"
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
                               )
            render = template.render(Context({'entity': orga,
                                              'user':   self.user,
                                              'ct':     ContentType.objects.get_for_model(FakeOrganisation),
                                             }))

        self.assertEqual('True' + 'False' * 4 + 'True' * 2 + 'False' * 2 + 'True' + 'False',
                         render.strip()
                        )

    def assertFieldEditorTag(self, render, entity, field_name, block=False):
        # fmt = """<a onclick="creme.blocks.form('/creme_core/entity/edit/inner/%s/%s/field/%s', {blockReloadUrl:""" if block else \
        #       """<a onclick="creme.blocks.form('/creme_core/entity/edit/inner/%s/%s/field/%s', {reloadOnSuccess:"""
        # expected = fmt % (entity.entity_type_id, entity.id, field_name)
        url = reverse('creme_core__inner_edition', args=(entity.entity_type_id, entity.id, field_name))

        if block:
            expected = """<a onclick="creme.blocks.form('{}', {blockReloadUrl:""".format(url)
        else:
            expected = """<a onclick="creme.blocks.form('{}', {reloadOnSuccess:""".format(url)

        self.assertTrue(render.strip().startswith(expected),
                        "{}\n doesn't start with\n {}".format(render.strip(), expected)
                       )

    # def test_get_field_editor01(self):
    #     user = self.login()
    #     orga = FakeOrganisation.objects.create(user=user, name='Amestris')
    #
    #     with self.assertNoException():
    #         template = Template(r"{% load creme_block %}"
    #                             r"{% get_field_editor on regular 'name' for object %}"
    #                            )
    #         render = template.render(Context({'object': orga, 'user': user}))
    #
    #     self.assertFieldEditorTag(render, orga, 'name')

    # def test_get_field_editor02(self):
    #     user = self.login()
    #     orga = FakeOrganisation.objects.create(user=user, name='Amestris')
    #
    #     with self.assertNoException():
    #         template = Template(r"{% load creme_block %}"
    #                             r'{% get_field_editor on regular "name" for object %}'
    #                            )
    #         render = template.render(Context({'object':     orga,
    #                                           'user':       user,
    #                                           'block_name': 'tests-test_block',
    #                                          })
    #                                 )
    #
    #     self.assertFieldEditorTag(render, orga, 'name', block=True)

    # def test_get_field_editor03(self):
    #     self.login()
    #     orga = FakeOrganisation.objects.create(user=self.user, name='Amestris')
    #     orga_field_name = orga.entity_type.model_class()._meta.get_field('name')
    #
    #     with self.assertNoException():
    #         template = Template(r"{% load creme_block %}"
    #                             r"{% get_field_editor on regular field for object %}"
    #                            )
    #         render = template.render(Context({'object': orga, 'user': self.user, 'field': orga_field_name}))
    #
    #     self.assertFieldEditorTag(render, orga, orga_field_name.name)

    # def test_get_field_editor04(self):
    #     user = self.login()
    #     orga = FakeOrganisation.objects.create(user=user, name='Amestris')
    #     custom_field_orga = CustomField.objects.create(name='custom 1',
    #                                                    content_type=orga.entity_type,
    #                                                    field_type=CustomField.STR,
    #                                                   )
    #
    #     with self.assertNoException():
    #         template = Template(r"{% load creme_block %}"
    #                             r"{% get_field_editor on custom custom_field_id for object %}"
    #                            )
    #         render = template.render(Context({'object':          orga,
    #                                           'user':            user,
    #                                           'custom_field_id': custom_field_orga,
    #                                          }
    #                                         )
    #                                 )
    #
    #     self.assertFieldEditorTag(render, orga, _CUSTOMFIELD_FORMAT % custom_field_orga.id)

    # def _unauthorized_get_field_editor(self, orga, unauthorized_tag):
    #     with self.assertNoException():
    #         template = Template(r"{% load creme_block %}" + unauthorized_tag)
    #         render = template.render(Context({'object': orga, 'user': self.user}))
    #
    #     self.assertEqual("", render.strip())

    # def test_get_field_editor05(self):
    #     self.login()
    #     orga = FakeOrganisation.objects.create(user=self.user, name='Amestris')
    #     cdict = {'object': orga, 'user': self.user}
    #
    #     with self.assertRaises(TemplateSyntaxError):  # Invalid field type : Should be 'regular' or 'custom'
    #         Template(r"{% load creme_block %}{% get_field_editor on unknown_type 'name' for object %}")
    #
    #     with self.assertRaises(FieldDoesNotExist):  # Invalid field name for object model
    #         template = Template(r"{% load creme_block %}{% get_field_editor on regular 'unkwnown_field' for object %}")
    #         template.render(Context(cdict))
    #
    #     with self.assertRaises(AttributeError):  # Invalid custom field object for object model
    #         template = Template(r"{% load creme_block %}{% get_field_editor on custom unkwnown_custom for object %}")
    #         template.render(Context(cdict))

    # def test_get_field_editor06(self):
    #     self.login()
    #     orga = FakeOrganisation.objects.create(user=self.user, name='Amestris')
    #     bulk_update_registry.register(FakeOrganisation, exclude=['siren'])
    #
    #     # Not editable
    #     self._unauthorized_get_field_editor(orga, r"{% get_field_editor on regular 'created' for object %}")
    #     self._unauthorized_get_field_editor(orga, r"{% get_field_editor on regular 'modified' for object %}")

    def _assertJsonifyFilter(self, expected, data):
        with self.assertNoException():
            template = Template("{% load creme_core_tags %}{{data|jsonify|safe}}")
            render = template.render(Context({'data': data}))

        # self.assertEqual(expected, render.strip())
        with self.assertNoException():
            deserialized = json_load(render.strip())

        self.assertEqual(expected, deserialized)

    def test_jsonify_filter(self):
        # self._assertJsonifyFilter('""', '')
        # self._assertJsonifyFilter('"test string"', 'test string')
        #
        # self._assertJsonifyFilter('[1,2,3]', (1, 2, 3))
        # self._assertJsonifyFilter('[1,2,3]', [1, 2, 3])
        # self._assertJsonifyFilter('{"value":1,"label":"a"}', {'value': 1, 'label':"a"})
        #
        # self._assertJsonifyFilter('[0,1,2]', (v for v in xrange(3)))
        # self._assertJsonifyFilter('[{"value":0,"label":"a"},{"value":1,"label":"b"},{"value":2,"label":"c"}]',
        #                           ({'value': value, 'label': label} for value, label in enumerate(['a', 'b', 'c']))
        #                          )
        self._assertJsonifyFilter('', '')
        self._assertJsonifyFilter('test string', 'test string')

        self._assertJsonifyFilter([1, 2, 3], (1, 2, 3))
        self._assertJsonifyFilter([1, 2, 3], [1, 2, 3])
        self._assertJsonifyFilter({'value': 1, 'label': 'a'}, {'value': 1, 'label': 'a'})

        self._assertJsonifyFilter([0, 1, 2], (v for v in range(3)))
        self._assertJsonifyFilter([{'value': 0, 'label': 'a'}, {'value': 1, 'label': 'b'}, {'value': 2, 'label': 'c'}],
                                  ({'value': value, 'label': label} for value, label in enumerate(['a', 'b', 'c']))
                                 )

    def test_optionize_model_iterable_filter(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Amestris')
        orga2 = create_orga(name='Spectre')
        orgas = [orga1, orga2]

        with self.assertNoException():
            template = Template("{% load creme_core_tags %}{{data|optionize_model_iterable|jsonify|safe}}")
            render = template.render(Context({'data': orgas}))

        # self.assertEqual('[[{},"{}"],[{},"{}"]]'.format(
        #                         orga1.id, orga1,
        #                         orga2.id, orga2,
        #                     ),
        #                  render.strip()
        #                 )
        with self.assertNoException():
            deserialized = json_load(render.strip())

        self.assertEqual([[orga1.id, str(orga1)], [orga2.id, str(orga2)]],
                         deserialized
                        )

        # ---
        with self.assertNoException():
            template = Template("{% load creme_core_tags %}{{data|optionize_model_iterable:'dict'|jsonify|safe}}")
            render = template.render(Context({'data': orgas}))

        # self.assertEqual(u'[{"value":%d,"label":"%s"},{"value":%d,"label":"%s"}]' % (
        #                          orga1.pk, orga1,
        #                          orga2.pk, orga2,
        #                     ),
        #                  render.strip()
        #                 )
        with self.assertNoException():
            deserialized = json_load(render.strip())

        self.assertEqual([{'value': orga1.id, 'label': str(orga1)},
                          {'value': orga2.id, 'label': str(orga2)},
                         ],
                         deserialized
                        )

    def test_url_join1(self):
        "No GET parameter"
        url = '/creme_core/foobar'

        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% url_join my_url as my_uri %}'
                                '<a href="{{my_uri}}">Link</a>'
                               )
            render = template.render(Context({'my_url': url}))

        self.assertEqual('<a href="{}">Link</a>'.format(url), render.strip())

    def test_url_join2(self):
        "Several arguments"
        url = '/creme_core/foobar'
        brick_id1 = 'brick-core-entities'
        brick_id2 = 'brick-core-properties'

        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% url_join my_url brick_id_01=brick_id1 brick_id_02=brick_id2 as my_uri %}'
                                '<a href="{{my_uri}}">Link</a>'
                               )
            render = template.render(Context({'my_url': url, 'brick_id1': brick_id1, 'brick_id2': brick_id2}))

        self.assertIn(render.strip(),
                      ('<a href="{}?brick_id_01={}&brick_id_02={}">Link</a>'.format(url, brick_id1, brick_id2),
                       '<a href="{}?brick_id_02={}&brick_id_01={}">Link</a>'.format(url, brick_id2, brick_id1),
                      )
                     )

    def test_url_join3(self):
        "List arguments"
        url = '/creme_core/foobar'
        brick_ids = ['brick-core-entities', 'brick-core-properties']

        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% url_join my_url brick_id=brick_id as my_uri %}'
                                '<a href="{{my_uri}}">Link</a>'
                               )
            render = template.render(Context({'my_url': url, 'brick_id': brick_ids}))

        self.assertEqual('<a href="{}?brick_id={}&brick_id={}">Link</a>'.format(url, brick_ids[0], brick_ids[1]),
                         render.strip()
                        )

    def test_url_join4(self):
        "Already a GET parameter"
        url = '/creme_core/foobar?arg1=value'
        brick_id = 'brick-core-entities'

        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% url_join my_url brick_id=brick_id as my_uri %}'
                                '<a href="{{my_uri}}">Link</a>'
                               )
            render = template.render(Context({'my_url': url, 'brick_id': brick_id}))

        self.assertEqual('<a href="{}&brick_id={}">Link</a>'.format(url, brick_id),
                         render.strip()
                        )

    def test_url_join5(self):
        "Already a GET parameter + list paratemeter"
        url = '/creme_core/foobar?arg1=value'
        brick_ids = ['brick-core-entities', 'brick-core-properties']

        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% url_join my_url brick_id=brick_id as my_uri %}'
                                '<a href="{{my_uri}}">Link</a>'
                               )
            render = template.render(Context({'my_url': url, 'brick_id': brick_ids}))

        self.assertEqual('<a href="{}&brick_id={}&brick_id={}">Link</a>'.format(url, brick_ids[0], brick_ids[1]),
                         render.strip()
                        )

    def test_url_join6(self):
        "Escaping"
        url = '/creme_core/search'
        search = 'orange & lemons'

        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% url_join my_url value=search as my_uri %}'
                                '<a href="{{my_uri}}">Link</a>'
                               )
            render = template.render(Context({'my_url': url, 'search': search}))

        self.assertEqual('<a href="{}?value={}">Link</a>'.format(url, 'orange+%26+lemons'),
                         render.strip()
                        )
