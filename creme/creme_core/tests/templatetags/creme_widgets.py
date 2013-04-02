# -*- coding: utf-8 -*-

try:
    from django.template import Template, Context
    from django.utils.translation import ugettext as _

    from ..base import CremeTestCase

    from creme.persons.models import Organisation
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('CremeWidgetsTagsTestCase',)


class CremeWidgetsTagsTestCase(CremeTestCase):
    def test_widget_entity_hyperlink01(self):
        "Escaping"
        self.login()

        user = self.user
        name = 'NERV'
        orga = Organisation.objects.create(user=user, name=name + '<br/>') #escaping OK ??

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_entity_hyperlink my_entity user %}')
            render = tpl.render(Context({'user': user, 'my_entity': orga}))

        self.assertEqual(render,
                         u'<a href="/persons/organisation/%s">%s</a>' % (
                                orga.id, name + '&lt;br/&gt;'
                            )
                        )

    def test_widget_entity_hyperlink02(self):
        "Credentials"
        self.login(is_superuser=False)

        user = self.user
        orga = Organisation.objects.create(user=self.other_user, name='NERV')
        self.assertFalse(orga.can_view(user))

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_entity_hyperlink orga user %}')
            render = tpl.render(Context({'user': user, 'orga': orga}))

        self.assertEqual(render, _(u'Entity #%s (not viewable)') % orga.id)

    def test_widget_entity_hyperlink03(self):
        "Is deleted"
        self.login()

        user = self.user
        orga = Organisation.objects.create(user=user, name='Seele', is_deleted=True)

        with self.assertNoException():
            tpl = Template(r'{% load creme_widgets %}{% widget_entity_hyperlink my_entity user %}')
            render = tpl.render(Context({'user': user, 'my_entity': orga}))

        self.assertEqual(render, 
                         u'<a href="/persons/organisation/%s" class="is_deleted">%s</a>' % (
                                orga.id, unicode(orga)
                            )
                        )

    #TODO: complete