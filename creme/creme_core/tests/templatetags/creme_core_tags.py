# -*- coding: utf-8 -*-

try:
    from django.template import Template, Context
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import SetCredentials
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
