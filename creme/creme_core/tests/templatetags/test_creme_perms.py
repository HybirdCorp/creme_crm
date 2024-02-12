from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template

# from creme.creme_core.auth.entity_credentials import EntityCredentials
# from creme.creme_core.models import SetCredentials
from creme.creme_core.models import FakeContact, FakeOrganisation

from ..base import CremeTestCase, skipIfNotInstalled


class CremePermsTestCase(CremeTestCase):
    def test_filter_has_perm_to_create(self):
        role = self.create_role(
            name='Basic',
            allowed_apps=['creme_core'],
            creatable_models=[FakeOrganisation],
        )
        user = self.create_user(index=0, role=role, password='password')
        get_ct = ContentType.objects.get_for_model

        with self.assertNoException():
            render = Template(
                '{% load creme_perms %}'
                '{{user|has_perm_to_create:ct1}}#'
                '{{user|has_perm_to_create:ct2}}'
            ).render(Context({
                'user': user,
                'ct1': get_ct(FakeOrganisation),
                'ct2': get_ct(FakeContact),
            }))

        self.assertEqual('True#False', render.strip())

    def test_filter_has_perm_to_export(self):
        role = self.create_role(
            name='Basic',
            allowed_apps=['creme_core'],
            exportable_models=[FakeOrganisation],
        )
        user = self.create_user(index=0, role=role, password='password')
        get_ct = ContentType.objects.get_for_model

        with self.assertNoException():
            render = Template(
                '{% load creme_perms %}'
                '{{user|has_perm_to_export:ct1}}#'
                '{{user|has_perm_to_export:ct2}}'
            ).render(Context({
                'user': user,
                'ct1': get_ct(FakeOrganisation),
                'ct2': get_ct(FakeContact),
            }))

        self.assertEqual('True#False', render.strip())

    def test_filter_has_perm_to_view(self):
        role = self.create_role(name='Basic', allowed_apps=['creme_core'])
        # SetCredentials.objects.create(
        #     role=role,
        #     value=EntityCredentials.VIEW,
        #     set_type=SetCredentials.ESET_OWN,
        # )
        self.add_credentials(role, own=['VIEW'])
        user = self.create_user(index=0, role=role, password='password')
        root = self.get_root_user()

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Amestris')
        orga2 = create_orga(user=root, name='Xing')

        with self.assertNoException():
            render = Template(
                '{% load creme_perms %}'
                '{{user|has_perm_to_view:entity1}}#'
                '{{user|has_perm_to_view:entity2}}'
            ).render(Context({
                'entity1': orga1,
                'entity2': orga2,
                'user': user,
            }))

        self.assertEqual('True#False', render.strip())

    def test_filter_has_perm_to_change(self):
        role = self.create_role(name='Basic', allowed_apps=['creme_core'])
        # SetCredentials.objects.create(
        #     role=role,
        #     value=EntityCredentials.CHANGE,
        #     set_type=SetCredentials.ESET_OWN,
        # )
        self.add_credentials(role, own=['CHANGE'])
        user = self.create_user(index=0, role=role, password='password')
        root = self.get_root_user()

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Amestris')
        orga2 = create_orga(user=root, name='Xing')

        with self.assertNoException():
            render = Template(
                '{% load creme_perms %}'
                '{{user|has_perm_to_change:entity1}}#'
                '{{user|has_perm_to_change:entity2}}'
            ).render(Context({
                'entity1': orga1,
                'entity2': orga2,
                'user': user,
            }))

        self.assertEqual('True#False', render.strip())

    def test_filter_has_perm_to_delete(self):
        role = self.create_role(name='Basic', allowed_apps=['creme_core'])
        # SetCredentials.objects.create(
        #     role=role,
        #     value=EntityCredentials.DELETE,
        #     set_type=SetCredentials.ESET_OWN,
        # )
        self.add_credentials(role, own=['DELETE'])

        user = self.create_user(index=0, role=role, password='password')
        root = self.get_root_user()

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Amestris')
        orga2 = create_orga(user=root, name='Xing')

        with self.assertNoException():
            render = Template(
                '{% load creme_perms %}'
                '{{user|has_perm_to_delete:entity1}}#'
                '{{user|has_perm_to_delete:entity2}}'
            ).render(Context({
                'entity1': orga1,
                'entity2': orga2,
                'user': user,
            }))

        self.assertEqual('True#False', render.strip())

    @skipIfNotInstalled('creme.documents')
    def test_filter_has_perm_to_link(self):
        from creme.documents import get_document_model

        role = self.create_role(name='Basic', allowed_apps=['creme_core'])
        # SetCredentials.objects.create(
        #     role=role,
        #     value=EntityCredentials.LINK,
        #     set_type=SetCredentials.ESET_OWN,
        # )
        self.add_credentials(role, own=['LINK'])

        user = self.create_user(index=0, role=role, password='password')
        root = self.get_root_user()

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Amestris')
        orga2 = create_orga(user=root, name='Xing')

        with self.assertNoException():
            render = Template(
                '{% load creme_perms %}'
                '{{user|has_perm_to_link:entity1}}#'
                '{{user|has_perm_to_link:entity2}}#'
                '{{user|has_perm_to_link:ct1}}#'
                '{{user|has_perm_to_link:ct2}}#'
                '{{user|has_perm_to_link:ct3}}'
            ).render(Context({
                'entity1': orga1,
                'entity2': orga2,
                'ct1': orga1.entity_type,
                'ct2': ContentType.objects.get_for_model(FakeContact),
                'ct3': ContentType.objects.get_for_model(get_document_model()),
                'user': user,
            }))

        self.assertEqual('True#False#True#True#False', render.strip())

    def test_filter_has_perm_to_unlink(self):
        role = self.create_role(name='Basic', allowed_apps=['creme_core'])
        # SetCredentials.objects.create(
        #     role=role,
        #     value=EntityCredentials.UNLINK,
        #     set_type=SetCredentials.ESET_OWN,
        # )
        self.add_credentials(role, own=['UNLINK'])

        user = self.create_user(index=0, role=role, password='password')
        root = self.get_root_user()

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Amestris')
        orga2 = create_orga(user=root, name='Xing')

        with self.assertNoException():
            render = Template(
                '{% load creme_perms %}'
                '{{user|has_perm_to_unlink:entity1}}#'
                '{{user|has_perm_to_unlink:entity2}}'
            ).render(Context({
                'entity1': orga1,
                'entity2': orga2,
                'user': user,
            }))

        self.assertEqual('True#False', render.strip())

    def test_filter_has_perm_to_access(self):
        role = self.create_role(name='Basic', allowed_apps=['creme_core'])
        user = self.create_user(index=0, role=role, password='password')

        with self.assertNoException():
            render = Template(
                "{% load creme_perms %}"
                "{{user|has_perm_to_access:'creme_core'}}#"
                "{{user|has_perm_to_access:'persons'}}"
            ).render(Context({'user': user}))

        self.assertEqual('True#False', render.strip())

    def test_filter_has_perm_to_admin(self):
        role = self.create_role(
            name='Basic',
            allowed_apps=['creme_core', 'persons'],
            admin_4_apps=['persons'],
        )
        user = self.create_user(index=0, role=role, password='password')

        with self.assertNoException():
            render = Template(
                "{% load creme_perms %}"
                "{{user|has_perm_to_admin:'persons'}}#"
                "{{user|has_perm_to_admin:'creme_core'}}"
            ).render(Context({'user': user}))

        self.assertEqual('True#False', render.strip())
