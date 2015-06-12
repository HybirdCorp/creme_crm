# -*- coding: utf-8 -*-


from ..models import HeaderFilter
from ..core.entity_cell import EntityCellRegularField

from .fake_models import *
from .fake_constants import *


#TODO: use fixture instead ?
def populate():
    create_rtype = RelationType.create
    create_rtype((FAKE_REL_SUB_EMPLOYED_BY, u'is an employee of', [FakeContact]),
                 (FAKE_REL_OBJ_EMPLOYED_BY, u'employs',           [FakeOrganisation]),
                )
    create_rtype((FAKE_REL_SUB_BILL_ISSUED, u'issued by',  [FakeInvoice]),
                 (FAKE_REL_OBJ_BILL_ISSUED, u'has issued', [FakeOrganisation]),
                 is_internal=True
                )
    create_rtype((FAKE_REL_SUB_BILL_RECEIVED, u'received by',  [FakeInvoice]),
                 (FAKE_REL_OBJ_BILL_RECEIVED, u'has received', [FakeOrganisation, FakeContact]),
                 is_internal=True
                )

    create_civ = FakeCivility.objects.create
    create_civ(title=u'Madam',  shortcut=u'Mrs.')
    create_civ(title=u'Miss',   shortcut=u'Ms.')
    create_civ(title=u'Mister', shortcut=u'Mr.')
    create_civ(title=u'N/A',    shortcut=u'')

    create_pos = FakePosition.objects.create
    create_pos(title=u'CEO')
    create_pos(title=u'Secretary')
    create_pos(title=u'Technician')

    create_sector = FakeSector.objects.create
    create_sector(title=u'Food Industry')
    create_sector(title=u'Industry')
    create_sector(title=u'Informatic')

    create_cat = FakeImageCategory.objects.create
    create_cat(name=u"Product image")
    create_cat(name=u"Organisation logo")
    create_cat(name=u"Contact photograph")

    create_actype = FakeActivityType.objects.get_or_create
    create_actype(name='Phone call')
    create_actype(name='Meeting')

    create_hf = HeaderFilter.create
    create_hf(pk='creme_core-hf_fakeimage', name=u'FakeImage view',
              model=FakeImage,
              cells_desc=[(EntityCellRegularField, {'name': 'name'})],
             )
    create_hf(pk='creme_core-hf_fakecontact', name=u'FakeContact view',
              model=FakeContact,
              cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                          (EntityCellRegularField, {'name': 'first_name'}),
                          (EntityCellRegularField, {'name': 'email'}),
                         ],
             )
    create_hf(pk='creme_core-hf_fakeorganisation', name=u'FakeOrganisation view',
              model=FakeOrganisation,
              cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                          (EntityCellRegularField, {'name': 'phone'}),
                         ],
             )
    create_hf(pk='creme_core-hf_fakeactivity', name='FakeActivity view',
              model=FakeActivity,
              cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                          (EntityCellRegularField, {'name': 'start'}),
                         ],
             )
    create_hf(pk='creme_core-hf_fakeinvoiceline', name='FakeInvoiceLine view',
              model=FakeInvoiceLine,
              cells_desc=[(EntityCellRegularField, {'name': 'invoice'}),
                          (EntityCellRegularField, {'name': 'item'}),
                          (EntityCellRegularField, {'name': 'quantity'}),
                         ],
             )
