from functools import partial

from django.db.models.query_utils import Q

import creme.creme_core.forms.listview as lv_forms
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.models import FieldsConfig
from creme.creme_core.tests.base import CremeTestCase
from creme.persons.forms.listview import AddressFKField

from ..base import Address, Organisation, skipIfCustomAddress


@skipIfCustomAddress
class AddressFKFieldTestCase(CremeTestCase):
    # NB: keep as example
    # def test_search_field(self):
    #     self.login(create_orga=False)
    #
    #     field = AddressFKField(
    #         cell=EntityCellRegularField.build(model=Organisation, name='billing_address'),
    #         user=self.user,
    #     )
    #
    #     expected_choices = [
    #         {'value': '',                    'label': _('All')},
    #         {'value': lv_form.NULL,          'label': _('* is empty *')},
    #         {'value': AddressFKField.FILLED, 'label': _('* filled *')},
    #     ]
    #     self.assertEqual(expected_choices, field.choices)
    #
    #     widget = field.widget
    #     self.assertIsInstance(widget, lv_form.SelectLVSWidget)
    #     self.assertEqual(expected_choices, widget.choices)
    #
    #     to_python = field.to_python
    #     self.assertEqual(Q(), to_python(value=''))
    #     self.assertEqual(Q(), to_python(value=None))
    #     self.assertEqual(Q(), to_python(value='invalid'))
    #
    #     create_orga = partial(Organisation.objects.create, user=self.user)
    #     orga1 = create_orga(name='Orga without address')
    #     orga2 = create_orga(name='Orga with empty address')
    #     orga3 = create_orga(name='Orga with blank address')
    #     orga4 = create_orga(name='Orga with address #1')
    #     orga5 = create_orga(name='Orga with address #2')
    #     orga6 = create_orga(name='Orga with empty address with a name')
    #     orga_ids = [orga1.id, orga2.id, orga3.id, orga4.id, orga5.id, orga6.id]
    #
    #     create_address = Address.objects.create
    #     addr2 = create_address(address='',                    owner=orga2)
    #     addr3 = create_address(address='   ',                 owner=orga3)
    #     addr4 = create_address(address='  42 Towel street  ', owner=orga4)
    #     addr5 = create_address(city='Neo-tokyo',              owner=orga5)
    #     addr6 = create_address(name='Billing',                owner=orga6)
    #
    #     orga2.billing_address = addr2; orga2.save()
    #     orga3.billing_address = addr3; orga3.save()
    #     orga4.billing_address = addr4; orga4.save()
    #     orga5.billing_address = addr5; orga5.save()
    #     orga6.billing_address = addr6; orga6.save()
    #
    #     # NULL ---
    #     self.assertSetEqual(
    #         {orga1, orga2, orga3, orga6},
    #         set(Organisation.objects.filter(id__in=orga_ids)
    #                                 .filter(to_python(value=lv_form.NULL))
    #            )
    #     )
    #
    #     # NOT NULL ---
    #     self.assertSetEqual(
    #         {orga4, orga5},
    #         set(Organisation.objects.filter(id__in=orga_ids)
    #                                 .filter(to_python(value=AddressFKField.FILLED))
    #            )
    #     )
    def test_search_field(self):
        user = self.login_as_root_and_get()

        field = AddressFKField(
            cell=EntityCellRegularField.build(model=Organisation, name='billing_address'),
            user=user,
        )
        self.assertIsInstance(field.widget, lv_forms.TextLVSWidget)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=''))
        self.assertEqual(Q(), to_python(value=None))

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Orga without address')
        orga2 = create_orga(name='Orga with empty address')
        orga3 = create_orga(name='Orga with address #1')
        orga4 = create_orga(name='Orga with address #2')
        orga5 = create_orga(name='Orga with address #3 (not OK)')
        orga6 = create_orga(name='Orga with named address')
        orga_ids = [orga1.id, orga2.id, orga3.id, orga4.id, orga5.id, orga6.id]

        def create_billing_address(owner, **kwargs):
            owner.billing_address = Address.objects.create(owner=owner, **kwargs)
            owner.save()

        create_billing_address(address='',                owner=orga2)
        create_billing_address(address='42 Towel street', owner=orga3)
        create_billing_address(city='TowelCity',          owner=orga4)
        create_billing_address(address='42 Fish street',  owner=orga5)
        create_billing_address(name='Towel',              owner=orga6)

        self.assertCountEqual(
            [orga3, orga4],
            Organisation.objects
                        .filter(id__in=orga_ids)
                        .filter(to_python(value='towel')),
        )

    def test_search_field__hidden(self):
        "Ignore hidden fields."
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[('city', {FieldsConfig.HIDDEN: True})],
        )

        field = AddressFKField(
            cell=EntityCellRegularField.build(model=Organisation, name='billing_address'),
            user=user,
        )

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Orga without address')
        orga2 = create_orga(name='Orga with empty address')
        orga3 = create_orga(name='Orga with address #1')
        orga4 = create_orga(name='Orga with address #2 (hidden field)')
        orga5 = create_orga(name='Orga with address #3 (not OK)')
        orga6 = create_orga(name='Orga with named address')
        orga_ids = [orga1.id, orga2.id, orga3.id, orga4.id, orga5.id, orga6.id]

        def create_billing_address(owner, **kwargs):
            owner.billing_address = Address.objects.create(owner=owner, **kwargs)
            owner.save()

        create_billing_address(address='',                owner=orga2)
        create_billing_address(address='42 Towel street', owner=orga3)
        create_billing_address(city='TowelCity',          owner=orga4)
        create_billing_address(address='42 Fish street',  owner=orga5)
        create_billing_address(name='Towel',              owner=orga6)

        self.assertListEqual(
            [orga3],
            [
                *Organisation.objects
                             .filter(id__in=orga_ids)
                             .filter(field.to_python(value='towel')),
            ],
        )
