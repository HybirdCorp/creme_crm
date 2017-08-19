# -*- coding: utf-8 -*-

try:
    from django.template import Template, Context

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import SetCredentials, FakeOrganisation

    from ..base import CremeTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class CremeQueryTagsTestCase(CremeTestCase):
    def test_entities_count01(self):
        "Super user"
        user = self.login()

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='O-1')
        create_orga(user=user, name='O-2')

        with self.assertNoException():
            template = Template(r'{% load creme_query %}'
                                r'{% query_entities_count ctype=ct user=user as count %}'
                                r'{{count}}'
                               )
            render = template.render(Context({'user': user,
                                              'ct': orga1.entity_type,
                                             }))

        self.assertEqual('2', render.strip())

    def test_entities_count02(self):
        "Regular user"
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_OWN)

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='O-1')
        create_orga(user=self.other_user, name='O-2')

        with self.assertNoException():
            template = Template(r'{% load creme_query %}'
                                r'{% query_entities_count ctype=ct user=user as count %}'
                                r'{{count}}'
                               )
            render = template.render(Context({'user': user,
                                              'ct': orga1.entity_type,
                                             }))

        self.assertEqual('1', render.strip())
