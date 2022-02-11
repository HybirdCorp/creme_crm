from datetime import date

from creme.creme_api.tests.utils import CremeAPITestCase, Factory
from creme.persons import get_contact_model

Contact = get_contact_model()


@Factory.register
def contact(factory, **kwargs):
    data = factory.contact_data(**kwargs)
    return Contact.objects.create(**data)


@Factory.register
def contact_data(factory, **kwargs):
    if 'user' not in kwargs:
        kwargs['user'] = factory.user().id

    if 'civility' not in kwargs:
        kwargs['civility'] = factory.civility().id

    if 'position' not in kwargs:
        kwargs['position'] = factory.position().id

    if 'sector' not in kwargs:
        kwargs['sector'] = factory.sector().id

    data = {
        # 'user': None,
        'description': "Description",
        # 'billing_address': None,
        # 'shipping_address': None,
        # 'civility': None,
        'last_name': "Dupont",
        'first_name': "Jean",
        'skype': "jean.dupont",
        'phone': "+330100000000",
        'mobile': "+330600000000",
        'fax': "+330100000001",
        'email': "jean.dupont@provider.com",
        'url_site': "https://www.jean-dupont.provider.com",
        # 'position': None,
        'full_position': "Full position",
        # 'sector': None,
        # 'is_user': None,
        'birthday': "2000-01-01",
    }
    data.update(**kwargs)
    return data


class CreateContactTestCase(CremeAPITestCase):
    url_name = 'creme_api__contacts-list'
    method = 'post'

    def test_validation__required(self):
        response = self.make_request(data={})
        self.assertValidationErrors(response, {
            'last_name': ['required'],
            'user': ['required'],
        })

    def test_create_contact(self):
        user = self.factory.user()
        civility = self.factory.civility()
        position = self.factory.position()
        sector = self.factory.sector()
        data = self.factory.contact_data(
            user=user.id,
            civility=civility.id,
            position=position.id,
            sector=sector.id,
        )
        response = self.make_request(data=data)
        self.assertEqual(response.status_code, 201, response.data)
        contact = Contact.objects.get(id=response.data['id'])
        self.assertResponseEqual(response, 201, {
            **data,
            'id': contact.id,
            'uuid': str(contact.uuid),
            'is_deleted': False,
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'is_user': None,
            'billing_address': None,
            'shipping_address': None,
        })
        self.assertEqual(contact.birthday, date(2000, 1, 1))
        self.assertEqual(contact.description, data['description'])
        self.assertEqual(contact.last_name, data['last_name'])
        self.assertEqual(contact.first_name, data['first_name'])
        self.assertEqual(contact.skype, data['skype'])
        self.assertEqual(contact.phone, data['phone'])
        self.assertEqual(contact.mobile, data['mobile'])
        self.assertEqual(contact.fax, data['fax'])
        self.assertEqual(contact.email, data['email'])
        self.assertEqual(contact.url_site, data['url_site'])
        self.assertEqual(contact.full_position, data['full_position'])


# class RetrieveContactTestCase(CremeAPITestCase):
#     url_name = 'creme_api__contacts-detail'
#     method = 'get'
#
#     def test_get_contact(self):
#         contact = self.factory.contact()
#         response = self.make_request(to=contact.id)
#         self.assertResponseEqual(response, 200, {
#             'id': contact.id,
#             'contactname': contact.contactname,
#             'last_name': contact.last_name,
#             'first_name': contact.first_name,
#             'email': contact.email,
#             'date_joined': self.to_iso8601(contact.date_joined),
#             'last_login': None,
#             'is_active': True,
#             'time_zone': 'Europe/Paris',
#             'theme': 'icecream'
#         })
#
#
# class UpdateContactTestCase(CremeAPITestCase):
#     url_name = 'creme_api__contacts-detail'
#     method = 'put'
#
#     def test_validation__required(self):
#         contact = self.factory.contact()
#         response = self.make_request(to=contact.id, data={})
#         self.assertValidationErrors(response, {
#             'last_name': ['required'],
#             'user': ['required'],
#         })
#
#     def test_update_contact(self):
#         contact = self.factory.contact()
#
#         data = self.factory.contact_data(last_name="Smith", contactname="Nick")
#         response = self.make_request(to=contact.id, data=data)
#         self.assertResponseEqual(response, 200, {
#             'id': contact.id,
#             'last_name': 'Smith',
#             'first_name': 'John',
#         })
#         contact.refresh_from_db()
#         self.assertEqual(contact.contactname, "Nick")
#         self.assertEqual(contact.last_name, "Smith")
#
#
# class PartialUpdateContactTestCase(CremeAPITestCase):
#     url_name = 'creme_api__contacts-detail'
#     method = 'patch'
#
#     def test_partial_update_contact(self):
#         contact = self.factory.contact()
#         data = {'theme': "chantilly"}
#         response = self.make_request(to=contact.id, data=data)
#         self.assertResponseEqual(response, 200, {
#             'id': contact.id,
#             'contactname': 'john.doe',
#             'last_name': 'Doe',
#             'first_name': 'John',
#             'email': 'john.doe@provider.com',
#             'date_joined': self.to_iso8601(contact.date_joined),
#             'last_login': None,
#             'is_active': True,
#             'is_supercontact': True,
#             'role': None,
#             'time_zone': 'Europe/Paris',
#             'theme': 'chantilly'
#         })
#         contact.refresh_from_db()
#         self.assertEqual(contact.theme, "chantilly")
#
#
# class ListContactTestCase(CremeAPITestCase):
#     url_name = 'creme_api__contacts-list'
#     method = 'get'
#
#     def test_list_contacts(self):
#         fulbert = Contact.objects.get()
#         contact = self.factory.contact(contactname="contact", theme='chantilly')
#         self.assertEqual(Contact.objects.count(), 2)
#
#         response = self.make_request()
#         self.assertResponseEqual(response, 200, [
#             {
#                 'id': fulbert.id,
#                 'contactname': 'root',
#                 'last_name': 'Creme',
#                 'first_name': 'Fulbert',
#                 'email': fulbert.email,
#                 'date_joined': self.to_iso8601(fulbert.date_joined),
#                 'last_login': None,
#                 'is_active': True,
#                 'is_supercontact': True,
#                 'role': None,
#                 'time_zone': 'Europe/Paris',
#                 'theme': 'icecream'
#             },
#             {
#                 'id': contact.id,
#                 'contactname': 'contact',
#                 'last_name': 'Doe',
#                 'first_name': 'John',
#                 'email': 'john.doe@provider.com',
#                 'date_joined': self.to_iso8601(contact.date_joined),
#                 'last_login': None,
#                 'is_active': True,
#                 'is_supercontact': True,
#                 'role': None,
#                 'time_zone': 'Europe/Paris',
#                 'theme': 'chantilly'
#             },
#         ])
#
#
# class DeleteContactTestCase(CremeAPITestCase):
#     url_name = 'creme_api__contacts-delete'
#     method = 'post'
#
#     def test_delete(self):
#         url = reverse('creme_api__contacts-detail', args=[1])
#         response = self.client.delete(url, format='json')
#         self.assertResponseEqual(response, 405)
#
#     def test_validation__required(self):
#         contact = self.factory.contact()
#         response = self.make_request(to=contact.id, data={})
#         self.assertValidationErrors(response, {
#             'transfer_to': ['required']
#         })
#
#     def test_delete_contact(self):
#         team = self.factory.team()
#         contact1 = self.factory.contact(contactname='contact1')
#         contact2 = self.factory.contact(contactname='contact2')
#         contact = self.factory.contact(contact=contact2)
#
#         data = {'transfer_to': contact1.id}
#         response = self.make_request(to=contact2.id, data=data)
#         self.assertResponseEqual(response, 204)
#
#         self.assertFalse(Contact.objects.filter(contactname='contact2').exists())
#         contact.refresh_from_db()
#         self.assertEqual(contact.contact, contact1)
#
#         data = {'transfer_to': team.id}
#         response = self.make_request(to=contact1.id, data=data)
#         self.assertResponseEqual(response, 204)
#
#         self.assertFalse(Contact.objects.filter(contactname='contact1').exists())
#         contact.refresh_from_db()
#         self.assertEqual(contact.contact, team)
