from creme.creme_api.tests.utils import CremeAPITestCase, Factory
from creme.persons.models import StaffSize


@Factory.register
def staff_size(factory, **kwargs):
    data = factory.staff_size_data(**kwargs)
    return StaffSize.objects.create(**data)


@Factory.register
def staff_size_data(factory, **kwargs):
    kwargs.setdefault('size', '1 - 10')
    return kwargs


class CreateStaffSizeTestCase(CremeAPITestCase):
    url_name = 'creme_api__staff_sizes-list'
    method = 'post'

    def test_validation__required(self):
        response = self.make_request(data={}, status_code=400)
        self.assertValidationErrors(response, {
            'size': ['required'],
        })

    def test_create_staff_size(self):
        data = self.factory.staff_size_data()
        response = self.make_request(data=data, status_code=201)
        staff_size = StaffSize.objects.get(id=response.data['id'])
        self.assertPayloadEqual(response, {
            'id': staff_size.id,
            'size': '1 - 10',
        })
        self.assertEqual(staff_size.size, '1 - 10')


class RetrieveStaffSizeTestCase(CremeAPITestCase):
    url_name = 'creme_api__staff_sizes-detail'
    method = 'get'

    def test_retrieve_staff_size(self):
        staff_size = self.factory.staff_size()
        response = self.make_request(to=staff_size.id, status_code=200)
        self.assertPayloadEqual(response, {
            'id': staff_size.id,
            'size': '1 - 10',
        })


class UpdateStaffSizeTestCase(CremeAPITestCase):
    url_name = 'creme_api__staff_sizes-detail'
    method = 'put'

    def test_update_staff_size(self):
        staff_size = self.factory.staff_size()
        response = self.make_request(to=staff_size.id, data={
            'size': '1 - 100',
        }, status_code=200)
        self.assertPayloadEqual(response, {
            'id': staff_size.id,
            'size': '1 - 100',
        })
        staff_size.refresh_from_db()
        self.assertEqual(staff_size.size, '1 - 100')


class PartialUpdateStaffSizeTestCase(CremeAPITestCase):
    url_name = 'creme_api__staff_sizes-detail'
    method = 'patch'

    def test_partial_update_staff_size(self):
        staff_size = self.factory.staff_size()
        response = self.make_request(to=staff_size.id, data={
            'size': '1 - 1000',
        }, status_code=200)
        self.assertPayloadEqual(response, {
            'id': staff_size.id,
            'size': '1 - 1000',
        })
        staff_size.refresh_from_db()
        self.assertEqual(staff_size.size, '1 - 1000')


class ListStaffSizeTestCase(CremeAPITestCase):
    url_name = 'creme_api__staff_sizes-list'
    method = 'get'

    def test_list_staff_sizes(self):
        StaffSize.objects.all().delete()
        staff_size1 = self.factory.staff_size(size="1 - 10")
        staff_size2 = self.factory.staff_size(size="10 - 20")
        response = self.make_request(status_code=200)
        self.assertPayloadEqual(response, [
            {'id': staff_size1.id, 'size': "1 - 10"},
            {'id': staff_size2.id, 'size': "10 - 20"},
        ])


class DeleteStaffSizeTestCase(CremeAPITestCase):
    url_name = 'creme_api__staff_sizes-detail'
    method = 'delete'

    def test_delete_staff_size(self):
        staff_size = self.factory.staff_size()
        self.make_request(to=staff_size.id, status_code=204)
        self.assertFalse(StaffSize.objects.filter(id=staff_size.id).exists())
