from ..core.entity_cell import EntityCellRegularField
from ..models import CustomFormConfigItem, HeaderFilter, RelationType
from . import fake_constants, fake_custom_forms, fake_models


# TODO: use fixture instead ?
def populate():
    create_builder = RelationType.objects.builder
    create_builder(
        id=fake_constants.FAKE_REL_SUB_EMPLOYED_BY,
        predicate='is an employee of',
        models=[fake_models.FakeContact],
    ).symmetric(
        id=fake_constants.FAKE_REL_OBJ_EMPLOYED_BY,
        predicate='employs',
        models=[fake_models.FakeOrganisation],
    ).get_or_create()
    create_builder(
        id=fake_constants.FAKE_REL_SUB_BILL_ISSUED,
        predicate='issued by',
        models=[fake_models.FakeInvoice],
        is_internal=True,
    ).symmetric(
        id=fake_constants.FAKE_REL_OBJ_BILL_ISSUED,
        predicate='has issued',
        models=[fake_models.FakeOrganisation],
    ).get_or_create()
    create_builder(
        id=fake_constants.FAKE_REL_SUB_BILL_RECEIVED,
        predicate='received by',
        models=[fake_models.FakeInvoice],
        is_internal=True,
    ).symmetric(
        id=fake_constants.FAKE_REL_OBJ_BILL_RECEIVED,
        predicate='has received',
        models=[fake_models.FakeOrganisation, fake_models.FakeContact],
    ).get_or_create()

    create_civ = fake_models.FakeCivility.objects.get_or_create
    create_civ(title='Madam',  shortcut='Mrs.')
    create_civ(title='Miss',   shortcut='Ms.')
    create_civ(title='Mister', shortcut='Mr.')
    create_civ(title='N/A',    shortcut='')

    create_pos = fake_models.FakePosition.objects.get_or_create
    create_pos(title='CEO')
    create_pos(title='Secretary')
    create_pos(title='Technician')

    create_sector = fake_models.FakeSector.objects.get_or_create
    create_sector(title='Farming')
    create_sector(title='Industry')
    create_sector(title='Software')

    create_img_cat = fake_models.FakeImageCategory.objects.get_or_create
    create_img_cat(name='Product image')
    create_img_cat(name='Organisation logo')
    create_img_cat(name='Contact photograph')

    create_actype = fake_models.FakeActivityType.objects.get_or_create
    create_actype(name='Phone call')
    create_actype(name='Meeting')

    create_status = fake_models.FakeTicketStatus.objects.get_or_create
    create_status(id=1, defaults={'name': 'Open',   'is_custom': False})
    create_status(id=2, defaults={'name': 'Closed', 'is_custom': False})
    create_status(id=3, defaults={'name': 'Invalid'})

    create_priority = fake_models.FakeTicketPriority.objects.get_or_create
    create_priority(id=1, defaults={'name': 'High',   'is_custom': False})
    create_priority(id=2, defaults={'name': 'Medium', 'is_custom': False})
    create_priority(id=3, defaults={'name': 'Low',    'is_custom': False})

    create_todo_cat = fake_models.FakeTodoCategory.objects.get_or_create
    create_todo_cat(name='Enhancement')
    create_todo_cat(name='Fix')
    create_todo_cat(name='Help wanted')

    HeaderFilter.objects.proxy(
        id='creme_core-hf_fakeimage', name='FakeImage view',
        model=fake_models.FakeImage,
        cells=[(EntityCellRegularField, 'name')],
    ).get_or_create()
    HeaderFilter.objects.proxy(
        id=fake_constants.DEFAULT_HFILTER_FAKE_CONTACT,
        name='FakeContact view',
        model=fake_models.FakeContact,
        cells=[
            (EntityCellRegularField, 'last_name'),
            (EntityCellRegularField, 'first_name'),
            (EntityCellRegularField, 'email'),
        ],
    ).get_or_create()
    HeaderFilter.objects.proxy(
        id=fake_constants.DEFAULT_HFILTER_FAKE_ORGA,
        name='FakeOrganisation view',
        model=fake_models.FakeOrganisation,
        cells=[
            (EntityCellRegularField, 'name'),
            (EntityCellRegularField, 'phone'),
        ],
    ).get_or_create()
    HeaderFilter.objects.proxy(
        id=fake_constants.DEFAULT_HFILTER_FAKE_ACTIVITY,
        name='FakeActivity view',
        model=fake_models.FakeActivity,
        cells=[
            (EntityCellRegularField, 'title'),
            (EntityCellRegularField, 'start'),
        ],
    ).get_or_create()
    HeaderFilter.objects.proxy(
        id=fake_constants.DEFAULT_HFILTER_FAKE_INVLINE,
        name='FakeInvoiceLine view',
        model=fake_models.FakeInvoiceLine,
        cells=[
            (EntityCellRegularField, 'linked_invoice'),
            (EntityCellRegularField, 'item'),
            (EntityCellRegularField, 'quantity'),
        ],
    ).get_or_create()
    # NB: do not create for HeaderFilter for FakeMailingList (see views.test_header_filter)

    CustomFormConfigItem.objects.create_if_needed(
        descriptor=fake_custom_forms.FAKEORGANISATION_CREATION_CFORM,
    )
    CustomFormConfigItem.objects.create_if_needed(
        descriptor=fake_custom_forms.FAKEORGANISATION_EDITION_CFORM,
    )
    CustomFormConfigItem.objects.create_if_needed(
        descriptor=fake_custom_forms.FAKEACTIVITY_CREATION_CFORM,
    )
    CustomFormConfigItem.objects.create_if_needed(
        descriptor=fake_custom_forms.FAKEACTIVITY_EDITION_CFORM,
    )
