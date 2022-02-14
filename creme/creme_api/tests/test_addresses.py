from creme.creme_api.tests.utils import Factory
from creme.persons import get_address_model

Address = get_address_model()


@Factory.register
def address(factory, **kwargs):
    data = factory.address_data(**kwargs)
    return Address.objects.create(**data)


@Factory.register
def address_data(factory, **kwargs):
    data = {
        # 'name': "Address name",
        'address': "1 Main Street",
        'po_box': "PO123",
        'zipcode': "ZIP123",
        'city': "City",
        'department': "Dept",
        'state': "State",
        'country': "Country",
        # 'owner': "",
    }
    data.update(**kwargs)
    return data
