# -*- coding: utf-8 -*-

try:
    from django.db.models.fields import FieldDoesNotExist
    from django.template import Template, Context, TemplateSyntaxError
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.forms.bulk import _CUSTOMFIELD_FORMAT
    from creme.creme_core.gui.bulk_update import bulk_update_registry
    from creme.creme_core.models import SetCredentials, CustomField
    from ..base import CremeTestCase

    from creme.persons.models import Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('CremeCoreTagsTestCase',)


class CremeCoreTagsTestCase(CremeTestCase):
    def test_templatize(self):
        with self.assertNoException():
            template = Template('{% load creme_core_tags %}'
                                '{% templatize "{{columns|length}}" as colspan %}'
                                '<h1>{{colspan}}</h1>'
                               )
            render = template.render(Context({'columns': range(3)}))

        self.assertEqual('<h1>3</h1>', render.strip())

    #TODO: complete with other field types
    def test_print_field(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='<br/>Amestris', url_site='www.amestris.org')

        with self.assertNoException():
            template = Template("{% load creme_core_tags %}"
                                "<ul>"
                                "<li>{% print_field object=entity field='name' %}</li>"
                                "<li>{% print_field object=entity field='url_site' %}</li>"
                                "</ul>"
                               )
            render = template.render(Context({'entity': orga, 'user': self.user}))

        self.assertEqual('<ul><li>&lt;br/&gt;Amestris</li><li><a href="www.amestris.org" target="_blank">www.amestris.org</a></li></ul>',
                         render.strip()
                        )

    def test_has_perm_to01(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Xing')

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
                                              'ct':     ContentType.objects.get_for_model(Organisation),
                                             }))

        self.assertEqual('True' * 11, render.strip())

    def test_has_perm_to02(self):
        self.login(is_superuser=False)
        orga = Organisation.objects.create(user=self.user, name='Xerces')

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
                                              'ct':     ContentType.objects.get_for_model(Organisation),
                                             }))

        self.assertEqual('False' * 11, render.strip())

    def test_has_perm_to03(self):
        self.login(is_superuser=False, allowed_apps=['persons'], creatable_models=[Organisation])
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        orga = Organisation.objects.create(user=self.user, name='Amestris')
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
                                "{% has_perm_to access 'persons' as app_perm %}{{app_perm}}"
                                "{% has_perm_to admin 'persons' as adm_perm %}{{adm_perm}}"
                               )
            render = template.render(Context({'entity': orga,
                                              'user':   self.user,
                                              'ct':     ContentType.objects.get_for_model(Organisation),
                                             }))

        self.assertEqual('True' + 'False' * 4 + 'True' * 2 + 'False' * 2 + 'True' + 'False',
                         render.strip()
                        )

    def assertFieldEditorTag(self, render, entity, field_name, block=False):
        fmt = """<a onclick="creme.blocks.form('/creme_core/entity/edit/inner/%s/%s/field/%s', {blockReloadUrl:""" if block else \
              """<a onclick="creme.blocks.form('/creme_core/entity/edit/inner/%s/%s/field/%s', {reloadOnSuccess:"""
        self.assertTrue(render.strip().startswith(fmt % (entity.entity_type_id, entity.id, field_name)))

    def test_get_field_editor01(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')

        with self.assertNoException():
            template = Template(r"{% load creme_block %}"
                                r"{% get_field_editor on regular 'name' for object %}"
                               )
            render = template.render(Context({'object': orga, 'user': self.user}))

        self.assertFieldEditorTag(render, orga, 'name')

    def test_get_field_editor02(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')

        with self.assertNoException():
            template = Template(r"{% load creme_block %}"
                                r'{% get_field_editor on regular "name" for object %}'
                               )
            render = template.render(Context({'object':     orga,
                                              'user':       self.user,
                                              'block_name': 'tests-test_block',
                                             })
                                    )

        self.assertFieldEditorTag(render, orga, 'name', block=True)

    def test_get_field_editor03(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')
        orga_field_name = orga.entity_type.model_class()._meta.get_field('name')

        with self.assertNoException():
            template = Template(r"{% load creme_block %}"
                                r"{% get_field_editor on regular field for object %}"
                               )
            render = template.render(Context({'object': orga, 'user': self.user, 'field': orga_field_name}))

        self.assertFieldEditorTag(render, orga, orga_field_name.name)

    def test_get_field_editor04(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')
        custom_field_orga = CustomField.objects.create(name='custom 1', content_type=orga.entity_type, field_type=CustomField.STR)

        with self.assertNoException():
            template = Template(r"{% load creme_block %}"
                                r"{% get_field_editor on custom custom_field_id for object %}"
                               )
            render = template.render(Context({'object': orga, 'user': self.user, 'custom_field_id': custom_field_orga}))

        self.assertFieldEditorTag(render, orga, _CUSTOMFIELD_FORMAT % custom_field_orga.id)

    def _unauthorized_get_field_editor(self, orga, unauthorized_tag):
        with self.assertNoException():
            template = Template(r"{% load creme_block %}" + unauthorized_tag)
            render = template.render(Context({'object': orga, 'user': self.user}))

        self.assertEqual("", render.strip())

    def test_get_field_editor05(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')
        cdict = {'object': orga, 'user': self.user}

        with self.assertRaises(TemplateSyntaxError): # invalid field type : Should be 'regular' or 'custom'
            Template(r"{% load creme_block %}{% get_field_editor on unknown_type 'name' for object %}")

        with self.assertRaises(FieldDoesNotExist): # invalid field name for object model
        #with self.assertRaises(TemplateSyntaxError) as cm: # invalid field name for object model
            template = Template(r"{% load creme_block %}{% get_field_editor on regular 'unkwnown_field' for object %}")
            template.render(Context(cdict))

        #self.assertIn('FieldDoesNotExist', str(cm.exception))

        with self.assertRaises(AttributeError): # invalid custom field object for object model
        #with self.assertRaises(TemplateSyntaxError) as cm: # invalid custom field object for object model
            template = Template(r"{% load creme_block %}{% get_field_editor on custom unkwnown_custom for object %}")
            template.render(Context(cdict))

        #self.assertIn('AttributeError', str(cm.exception))

    def test_get_field_editor06(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')
        bulk_update_registry.register(Organisation, exclude=['siren'],)

        self._unauthorized_get_field_editor(orga, r"{% get_field_editor on regular 'created' for object %}") # not editable
        self._unauthorized_get_field_editor(orga, r"{% get_field_editor on regular 'modified' for object %}") # not editable
#        self._unauthorized_get_field_editor(orga, r"{% get_field_editor on regular 'siren' for object %}") # not in bulk update registry

    def _assertJsonifyFilter(self, expected, data):
        with self.assertNoException():
            template = Template("{% load creme_core_tags %}{{data|jsonify|safe}}")
            render = template.render(Context({'data': data}))

        self.assertEqual(expected, render.strip());

    def test_jsonify_filter(self):
        self._assertJsonifyFilter('""', '');
        self._assertJsonifyFilter('"test string"', 'test string');
    
        self._assertJsonifyFilter('[1, 2, 3]', (1, 2, 3));
        self._assertJsonifyFilter('[1, 2, 3]', [1, 2, 3]);
        self._assertJsonifyFilter('{"value": 1, "label": "a"}', {'value': 1, 'label':"a"});
    
        self._assertJsonifyFilter('[0, 1, 2]', (v for v in xrange(3)));
        self._assertJsonifyFilter('[{"value": 0, "label": "a"}, {"value": 1, "label": "b"}, {"value": 2, "label": "c"}]',
                                  ({'value': value, 'label': label} for value, label in enumerate(['a', 'b', 'c'])))

    def test_optionize_model_iterable_filter(self):
        self.login()

        orgas = [Organisation.objects.create(user=self.user, name='Amestris'),
                 Organisation.objects.create(user=self.user, name='Spectre')]

        with self.assertNoException():
            template = Template("{% load creme_core_tags %}{{data|optionize_model_iterable|jsonify|safe}}")
            render = template.render(Context({'data': orgas}))

        self.assertEqual('[[%d, "%s"], [%d, "%s"]]' % (orgas[0].pk, unicode(orgas[0]),
                                                       orgas[1].pk, unicode(orgas[1])), render.strip());

        with self.assertNoException():
            template = Template("{% load creme_core_tags %}{{data|optionize_model_iterable:'dict'|jsonify|safe}}")
            render = template.render(Context({'data': orgas}))

        self.assertEqual("""[{"value": %d, "label": "%s"}, {"value": %d, "label": "%s"}]""" % 
                            (
                             orgas[0].pk, unicode(orgas[0]),
                             orgas[1].pk, unicode(orgas[1])
                            ),
                         render.strip());
