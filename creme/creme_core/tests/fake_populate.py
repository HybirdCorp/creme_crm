# -*- coding: utf-8 -*-

from ..core.entity_cell import EntityCellRegularField
from ..models import HeaderFilter, RelationType

from . import fake_constants
from . import fake_models


# TODO: use fixture instead ?
def populate():
    create_rtype = RelationType.create
    create_rtype((fake_constants.FAKE_REL_SUB_EMPLOYED_BY, 'is an employee of', [fake_models.FakeContact]),
                 (fake_constants.FAKE_REL_OBJ_EMPLOYED_BY, 'employs',           [fake_models.FakeOrganisation]),
                )
    create_rtype((fake_constants.FAKE_REL_SUB_BILL_ISSUED, 'issued by',  [fake_models.FakeInvoice]),
                 (fake_constants.FAKE_REL_OBJ_BILL_ISSUED, 'has issued', [fake_models.FakeOrganisation]),
                 is_internal=True
                )
    create_rtype((fake_constants.FAKE_REL_SUB_BILL_RECEIVED, 'received by',  [fake_models.FakeInvoice]),
                 (fake_constants.FAKE_REL_OBJ_BILL_RECEIVED, 'has received', [fake_models.FakeOrganisation, fake_models.FakeContact]),
                 is_internal=True
                )

    create_civ = fake_models.FakeCivility.objects.create
    create_civ(title='Madam',  shortcut='Mrs.')
    create_civ(title='Miss',   shortcut='Ms.')
    create_civ(title='Mister', shortcut='Mr.')
    create_civ(title='N/A',    shortcut='')

    create_pos = fake_models.FakePosition.objects.create
    create_pos(title='CEO')
    create_pos(title='Secretary')
    create_pos(title='Technician')

    create_sector = fake_models.FakeSector.objects.create
    create_sector(title='Farming')
    create_sector(title='Industry')
    create_sector(title='Informatic')

    create_cat = fake_models.FakeImageCategory.objects.create
    create_cat(name='Product image')
    create_cat(name='Organisation logo')
    create_cat(name='Contact photograph')

    create_actype = fake_models.FakeActivityType.objects.get_or_create
    create_actype(name='Phone call')
    create_actype(name='Meeting')

    create_hf = HeaderFilter.create
    create_hf(pk='creme_core-hf_fakeimage', name='FakeImage view',
              model=fake_models.FakeImage,
              cells_desc=[(EntityCellRegularField, {'name': 'name'})],
             )
    create_hf(pk='creme_core-hf_fakecontact', name='FakeContact view',
              model=fake_models.FakeContact,
              cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                          (EntityCellRegularField, {'name': 'first_name'}),
                          (EntityCellRegularField, {'name': 'email'}),
                         ],
             )
    create_hf(pk='creme_core-hf_fakeorganisation', name='FakeOrganisation view',
              model=fake_models.FakeOrganisation,
              cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                          (EntityCellRegularField, {'name': 'phone'}),
                         ],
             )
    create_hf(pk='creme_core-hf_fakeactivity', name='FakeActivity view',
              model=fake_models.FakeActivity,
              cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                          (EntityCellRegularField, {'name': 'start'}),
                         ],
             )
    create_hf(pk='creme_core-hf_fakeinvoiceline', name='FakeInvoiceLine view',
              model=fake_models.FakeInvoiceLine,
              cells_desc=[(EntityCellRegularField, {'name': 'linked_invoice'}),
                          (EntityCellRegularField, {'name': 'item'}),
                          (EntityCellRegularField, {'name': 'quantity'}),
                         ],
             )
    # NB: do not create for HeaderFilter for FakeMailingList (see views.test_header_filter)
