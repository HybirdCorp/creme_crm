# -*- coding: utf-8 -*-
from django.db.models.fields import FieldDoesNotExist
from django.template.base import TemplateSyntaxError

try:
    from django.template import Template, Context
    from django.contrib.contenttypes.models import ContentType

    from creme_core.gui.bulk_update import bulk_update_registry
    from creme_core.models import SetCredentials, CustomField
    from creme_core.tests.base import CremeTestCase

    from persons.models import Organisation
except Exception as e:
    print 'Error:', e


__all__ = ('CremeCoreTagsTestCase',)


class CremeCoreTagsTestCase(CremeTestCase):
    def test_templatize(self):
        try:
            template = Template('{% load creme_core_tags %}'
                                '{% templatize "{{columns|length}}" as colspan %}'
                                '<h1>{{colspan}}</h1>'
                               )
            render = template.render(Context({'columns': range(3)}))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('<h1>3</h1>', render.strip())

    def test_print_field(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris', url_site='www.amestris.org')

        try:
            template = Template("{% load creme_core_tags %}"
                                "<ul>"
                                "<li>{% print_field object=entity field='name' %}</li>"
                                "<li>{% print_field object=entity field='url_site' %}</li>"
                                "</ul>"
                               )
            render = template.render(Context({'entity': orga, 'user': self.user}))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('<ul><li>Amestris</li><li><a href="www.amestris.org" target="_blank">www.amestris.org</a></li></ul>',
                         render.strip()
                        )

    def test_has_perm_to01(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Xing')

        try:
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
                               )
            render = template.render(Context({'entity': orga,
                                              'user':   self.user,
                                              'ct':     ContentType.objects.get_for_model(Organisation),
                                             }))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('True' * 9, render.strip())

    def test_has_perm_to02(self):
        self.login(is_superuser=False)
        orga = Organisation.objects.create(user=self.user, name='Xerces')

        try:
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
                               )
            render = template.render(Context({'entity': orga,
                                              'user':   self.user,
                                              'ct':     ContentType.objects.get_for_model(Organisation),
                                             }))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('False' * 9, render.strip())

    def test_has_perm_to03(self):
        self.login(is_superuser=False, allowed_apps=['persons'], creatable_models=[Organisation])
        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        orga = Organisation.objects.create(user=self.user, name='Amestris')
        self.assertTrue(orga.can_view(self.user))

        try:
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
                               )
            render = template.render(Context({'entity': orga,
                                              'user':   self.user,
                                              'ct':     ContentType.objects.get_for_model(Organisation),
                                             }))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('True' + 'False' * 4 + 'True' * 2 + 'False' * 2, render.strip())

    def test_get_field_editor01(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')

        try:
            template = Template("{% load creme_block %}"
                                "{% get_field_editor on regular 'name' for object %}"
                            )
            render = template.render(Context({'object': orga, 'user': self.user}))
            self.assertTrue(render.strip().startswith("""<a onclick="creme.utils.innerPopupNReload('/creme_core/entity/edit/%s/field/%s',""" % (orga.id, 'name')))
        except Exception as e:
            self.fail(str(e))

    def test_get_field_editor02(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')

        try:
            template = Template("{% load creme_block %}"
                                """{% get_field_editor on regular "name" for object %}"""
            )
            render = template.render(Context({'object': orga, 'user': self.user}))
            self.assertTrue(render.strip().startswith("""<a onclick="creme.utils.innerPopupNReload('/creme_core/entity/edit/%s/field/%s',""" % (orga.id, 'name')))
        except Exception as e:
            self.fail(str(e))

    def test_get_field_editor03(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')
        orga_field_name = orga.entity_type.model_class()._meta.get_field('name')

        try:
            template = Template("{% load creme_block %}"
                                "{% get_field_editor on regular field for object %}"
            )
            render = template.render(Context({'object': orga, 'user': self.user, 'field': orga_field_name}))
            self.assertTrue(render.strip().startswith("""<a onclick="creme.utils.innerPopupNReload('/creme_core/entity/edit/%s/field/%s',""" % (orga.id, orga_field_name.name)))
        except Exception as e:
            self.fail(str(e))

    def test_get_field_editor04(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')
        custom_field_orga = CustomField.objects.create(name='custom 1', content_type=orga.entity_type, field_type=CustomField.STR)

        try:
            template = Template("{% load creme_block %}"
                                "{% get_field_editor on custom custom_field_id for object %}"
            )
            render = template.render(Context({'object': orga, 'user': self.user, 'custom_field_id': custom_field_orga}))
            self.assertTrue(render.strip().startswith("""<a onclick="creme.utils.innerPopupNReload('/creme_core/entity/edit/%s/field/%s',""" % (orga.id, custom_field_orga.id)))
        except Exception as e:
            self.fail(str(e))

    def _unauthorized_get_field_editor(self, orga, unauthorized_tag):
        try:
            template = Template("{% load creme_block %}" + unauthorized_tag)
            render = template.render(Context({'object': orga, 'user': self.user}))
            self.assertEqual("", render.strip())
        except Exception as e:
            self.fail(str(e))

    def test_get_field_editor05(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')

        with self.assertRaises(TemplateSyntaxError): # invalid field type : Should be 'regular' or 'custom'
            template = Template("{% load creme_block %}" + "{% get_field_editor on unknown_type 'name' for object %}")
            template.render(Context({'object': orga, 'user': self.user}))

        with self.assertRaises(FieldDoesNotExist): # invalid field name for object model
            template = Template("{% load creme_block %}" + "{% get_field_editor on regular 'unkwnown_field' for object %}")
            template.render(Context({'object': orga, 'user': self.user}))

        with self.assertRaises(AttributeError): # invalid custom field object for object model
            template = Template("{% load creme_block %}" + "{% get_field_editor on custom unkwnown_custom for object %}")
            template.render(Context({'object': orga, 'user': self.user}))

    def test_get_field_editor06(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Amestris')
        bulk_update_registry.register((Organisation, ['siren']),)

        self._unauthorized_get_field_editor(orga, "{% get_field_editor on regular 'created' for object %}") # not editable
        self._unauthorized_get_field_editor(orga, "{% get_field_editor on regular 'modified' for object %}") # not editable
        self._unauthorized_get_field_editor(orga, "{% get_field_editor on regular 'siren' for object %}") # not in bulk update registry