from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from creme.creme_api.tests.utils import CremeAPITestCase, Factory
from creme.creme_core.models import UserRole
from creme.persons import get_contact_model, get_organisation_model

CremeUser = get_user_model()
Contact = get_contact_model()
Organisation = get_organisation_model()


@Factory.register
def role(factory, **kwargs):
    contact_ct = ContentType.objects.get_for_model(Contact)
    orga_ct = ContentType.objects.get_for_model(Organisation)
    data = {
        'name': "Basic",
        'allowed_apps': ['creme_core', 'creme_api', 'persons'],
        'admin_4_apps': ['creme_core', 'creme_api'],
        'creatable_ctypes': [contact_ct.id, orga_ct.id],
        'exportable_ctypes': [contact_ct.id],
    }
    data.update(**kwargs)
    role = UserRole(name=data['name'])
    role.allowed_apps = data['allowed_apps']
    role.admin_4_apps = data['admin_4_apps']
    role.save()
    role.creatable_ctypes.set(data['creatable_ctypes'])
    role.exportable_ctypes.set(data['exportable_ctypes'])
    return role


class CreateRoleTestCase(CremeAPITestCase):
    url_name = 'creme_api__roles-list'
    method = 'post'

    def test_validation__required(self):
        response = self.make_request(data={}, status_code=400)
        self.assertValidationErrors(response, {
            'name': ['required'],
            'allowed_apps': ['required'],
            'admin_4_apps': ['required'],
            'creatable_ctypes': ['required'],
            'exportable_ctypes': ['required'],
        })

    def test_validation__name_unique(self):
        self.factory.role(name="UniqueRoleName")
        data = {
            'name': "UniqueRoleName",
            'allowed_apps': [],
            'admin_4_apps': [],
            'creatable_ctypes': [],
            'exportable_ctypes': [],
        }
        response = self.make_request(data=data, status_code=400)
        self.assertValidationError(response, 'name', ['unique'])

    def test_validation(self):
        contact_ct = ContentType.objects.get_for_model(Contact)
        orga_ct = ContentType.objects.get_for_model(Organisation)
        data = {
            'name': "CEO",
            'allowed_apps': ['creme_core'],
            'admin_4_apps': ['creme_core', 'creme_api', 'persons'],
            'creatable_ctypes': [contact_ct.id, orga_ct.id],
            'exportable_ctypes': [contact_ct.id, orga_ct.id],
        }
        response = self.make_request(data=data, status_code=400)
        self.assertValidationErrors(response, {
            'admin_4_apps': ["admin_4_not_allowed_app", "admin_4_not_allowed_app"],
            'creatable_ctypes': ["not_allowed_ctype", "not_allowed_ctype"],
            'exportable_ctypes': ["not_allowed_ctype", "not_allowed_ctype"],
        })

    def test_create_role(self):
        contact_ct = ContentType.objects.get_for_model(Contact)
        orga_ct = ContentType.objects.get_for_model(Organisation)
        data = {
            'name': "CEO",
            'allowed_apps': ['creme_core', 'creme_api', 'persons'],
            'admin_4_apps': ['creme_core', 'creme_api'],
            'creatable_ctypes': [contact_ct.id, orga_ct.id],
            'exportable_ctypes': [],
        }
        response = self.make_request(data=data, status_code=201)
        role = UserRole.objects.get(id=response.data['id'])
        self.assertPayloadEqual(response, {
            'id': role.id,
            'name': "CEO",
            'allowed_apps': {'creme_core', 'creme_api', 'persons'},
            'admin_4_apps': {'creme_core', 'creme_api'},
            'creatable_ctypes': [contact_ct.id, orga_ct.id],
            'exportable_ctypes': [],
            'credentials': [],
        })
        self.assertEqual(role.name, "CEO")
        self.assertEqual(role.allowed_apps, {'creme_core', 'persons', 'creme_api'})
        self.assertEqual(role.admin_4_apps, {'creme_core', 'creme_api'})
        self.assertEqual(list(role.creatable_ctypes.all()), [contact_ct, orga_ct])
        self.assertEqual(list(role.exportable_ctypes.all()), [])


class RetrieveRoleTestCase(CremeAPITestCase):
    url_name = 'creme_api__roles-detail'
    method = 'get'

    def test_retrieve_role(self):
        contact_ct = ContentType.objects.get_for_model(Contact)
        orga_ct = ContentType.objects.get_for_model(Organisation)
        role = self.factory.role()

        response = self.make_request(to=role.id, status_code=200)
        self.assertPayloadEqual(response, {
            'id': role.id,
            'name': "Basic",
            'allowed_apps': {'creme_core', 'creme_api', 'persons'},
            'admin_4_apps': {'creme_core', 'creme_api'},
            'creatable_ctypes': [contact_ct.id, orga_ct.id],
            'exportable_ctypes': [contact_ct.id],
            'credentials': [],
        })


class UpdateRoleTestCase(CremeAPITestCase):
    url_name = 'creme_api__roles-detail'
    method = 'put'

    def test_validation__required(self):
        role = self.factory.role()
        response = self.make_request(to=role.id, data={}, status_code=400)
        self.assertValidationErrors(response, {
            'name': ['required'],
            'allowed_apps': ['required'],
            'admin_4_apps': ['required'],
            'creatable_ctypes': ['required'],
            'exportable_ctypes': ['required'],
        })

    def test_validation(self):
        contact_ct = ContentType.objects.get_for_model(Contact)
        orga_ct = ContentType.objects.get_for_model(Organisation)
        role = self.factory.role()
        data = {
            'name': "CEO",
            'allowed_apps': ['creme_core'],
            'admin_4_apps': ['creme_core', 'persons'],
            'creatable_ctypes': [contact_ct.id],
            'exportable_ctypes': [orga_ct.id],
        }
        response = self.make_request(to=role.id, data=data, status_code=400)
        self.assertValidationErrors(response, {
            'admin_4_apps': ["admin_4_not_allowed_app"],
            'creatable_ctypes': ["not_allowed_ctype"],
            'exportable_ctypes': ["not_allowed_ctype"],
        })

    def test_update_role(self):
        contact_ct = ContentType.objects.get_for_model(Contact)
        orga_ct = ContentType.objects.get_for_model(Organisation)
        role = self.factory.role()
        data = {
            'name': "CEO",
            'allowed_apps': ['creme_core', 'persons'],
            'admin_4_apps': ['creme_core', 'persons'],
            'creatable_ctypes': [contact_ct.id],
            'exportable_ctypes': [orga_ct.id],
        }
        response = self.make_request(to=role.id, data=data, status_code=200)
        self.assertPayloadEqual(response, {
            'id': role.id,
            'name': "CEO",
            'allowed_apps': {'creme_core', 'persons'},
            'admin_4_apps': {'creme_core', 'persons'},
            'creatable_ctypes': [contact_ct.id],
            'exportable_ctypes': [orga_ct.id],
            'credentials': [],
        })
        role.refresh_from_db()
        self.assertEqual(role.name, "CEO")
        self.assertEqual(role.allowed_apps, {'creme_core', 'persons'})
        self.assertEqual(role.admin_4_apps, {'creme_core', 'persons'})
        self.assertEqual(list(role.creatable_ctypes.all()), [contact_ct])
        self.assertEqual(list(role.exportable_ctypes.all()), [orga_ct])


class PartialUpdateRoleTestCase(CremeAPITestCase):
    url_name = 'creme_api__roles-detail'
    method = 'patch'

    def test_validation__name_unique(self):
        self.factory.role(name="UniqueRoleName")
        role = self.factory.role(name="OtherName")
        data = {
            'name': "UniqueRoleName",
        }
        response = self.make_request(to=role.id, data=data, status_code=400)
        self.assertValidationError(response, 'name', ['unique'])

    def test_validation(self):
        role = self.factory.role()
        data = {
            'allowed_apps': ['creme_core'],
        }
        response = self.make_request(to=role.id, data=data, status_code=400)
        self.assertValidationErrors(response, {
            'admin_4_apps': ["admin_4_not_allowed_app"],
            'creatable_ctypes': ["not_allowed_ctype", "not_allowed_ctype"],
            'exportable_ctypes': ["not_allowed_ctype"],
        })

    def test_partial_update_role(self):
        contact_ct = ContentType.objects.get_for_model(Contact)
        orga_ct = ContentType.objects.get_for_model(Organisation)
        role = self.factory.role()

        data = {
            'name': "CEO",
        }
        response = self.make_request(to=role.id, data=data, status_code=200)
        self.assertPayloadEqual(response, {
            'id': role.id,
            'name': "CEO",
            'allowed_apps': {'creme_core', 'persons', 'creme_api'},
            'admin_4_apps': {'creme_core', 'creme_api'},
            'creatable_ctypes': [contact_ct.id, orga_ct.id],
            'exportable_ctypes': [contact_ct.id],
            'credentials': [],
        })
        role.refresh_from_db()
        self.assertEqual(role.name, "CEO")
        self.assertEqual(role.allowed_apps, {'creme_core', 'persons', 'creme_api'})
        self.assertEqual(role.admin_4_apps, {'creme_core', 'creme_api'})
        self.assertEqual(list(role.creatable_ctypes.all()), [contact_ct, orga_ct])
        self.assertEqual(list(role.exportable_ctypes.all()), [contact_ct])

        data = {
            'allowed_apps': ['creme_core', 'persons', 'creme_api'],
            'exportable_ctypes': [contact_ct.id, orga_ct.id],
        }
        response = self.make_request(to=role.id, data=data, status_code=200)
        self.assertPayloadEqual(response, {
            'id': role.id,
            'name': "CEO",
            'allowed_apps': {'creme_core', 'persons', 'creme_api'},
            'admin_4_apps': {'creme_core', 'creme_api'},
            'creatable_ctypes': [contact_ct.id, orga_ct.id],
            'exportable_ctypes': [contact_ct.id, orga_ct.id],
            'credentials': [],
        })
        role.refresh_from_db()
        self.assertEqual(role.name, "CEO")
        self.assertEqual(role.allowed_apps, {'creme_core', 'persons', 'creme_api'})
        self.assertEqual(role.admin_4_apps, {'creme_core', 'creme_api'})
        self.assertEqual(list(role.creatable_ctypes.all()), [contact_ct, orga_ct])
        self.assertEqual(list(role.exportable_ctypes.all()), [contact_ct, orga_ct])


class ListRoleTestCase(CremeAPITestCase):
    url_name = 'creme_api__roles-list'
    method = 'get'

    def test_list_roles(self):
        contact_ct = ContentType.objects.get_for_model(Contact)
        orga_ct = ContentType.objects.get_for_model(Organisation)
        role1 = self.factory.role(name='Role #1')
        role2 = self.factory.role(name='Role #2')

        response = self.make_request(status_code=200)
        self.assertPayloadEqual(response, [
            {
                'id': role1.id,
                'name': "Role #1",
                'allowed_apps': {'creme_core', 'persons', 'creme_api'},
                'admin_4_apps': {'creme_core', 'creme_api'},
                'creatable_ctypes': [contact_ct.id, orga_ct.id],
                'exportable_ctypes': [contact_ct.id],
                'credentials': [],
            },
            {
                'id': role2.id,
                'name': "Role #2",
                'allowed_apps': {'creme_core', 'persons', 'creme_api'},
                'admin_4_apps': {'creme_core', 'creme_api'},
                'creatable_ctypes': [contact_ct.id, orga_ct.id],
                'exportable_ctypes': [contact_ct.id],
                'credentials': [],
            }
        ])


class DeleteRoleTestCase(CremeAPITestCase):
    url_name = 'creme_api__roles-detail'
    method = 'delete'

    def test_delete_role__protected(self):
        role = self.factory.role()
        self.factory.user(role=role)
        self.make_request(to=role.id, status_code=403)

    def test_delete_role(self):
        role = self.factory.role()
        self.make_request(to=role.id, status_code=204)
        self.assertFalse(UserRole.objects.filter(id=role.id).exists())
