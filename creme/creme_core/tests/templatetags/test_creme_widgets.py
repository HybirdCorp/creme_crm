# -*- coding: utf-8 -*-

try:
    from django.conf import settings
    from django.template import Template, Context

    from ..base import CremeTestCase
    from ..fake_models import FakeOrganisation as Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class CremeWidgetsTagsTestCase(CremeTestCase):
    def test_widget_entity_hyperlink01(self):
        "Escaping"
        user = self.login()

        name = 'NERV'
        orga = Organisation.objects.create(user=user, name=name + '<br/>')  # escaping OK ??

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_entity_hyperlink my_entity user %}')
            render = tpl.render(Context({'user': user, 'my_entity': orga}))

        self.assertEqual(render,
                         u'<a href="/tests/organisation/%s">%s</a>' % (
                                orga.id, name + '&lt;br/&gt;'
                            )
                        )

    def test_widget_entity_hyperlink02(self):
        "Credentials"
        user = self.login(is_superuser=False)

        orga = Organisation.objects.create(user=self.other_user, name='NERV')
        self.assertFalse(user.has_perm_to_view(orga))

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_entity_hyperlink orga user %}')
            render = tpl.render(Context({'user': user, 'orga': orga}))

        self.assertEqual(render, settings.HIDDEN_VALUE)

    def test_widget_entity_hyperlink03(self):
        "Is deleted"
        user = self.login()
        orga = Organisation.objects.create(user=user, name='Seele', is_deleted=True)

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_entity_hyperlink my_entity user %}')
            render = tpl.render(Context({'user': user, 'my_entity': orga}))

        self.assertEqual(render, 
                         u'<a href="/tests/organisation/%s" class="is_deleted">%s</a>' % (
                                orga.id, unicode(orga)
                            )
                        )

    # TODO: complete
