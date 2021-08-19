# -*- coding: utf-8 -*-

from ..core.entity_cell import EntityCellRegularField
from ..forms import base as base_forms
from ..gui.custom_form import EntityCellCustomFormSpecial
from ..models import CustomFormConfigItem, HeaderFilter, RelationType
from . import fake_constants, fake_custom_forms, fake_forms, fake_models


# TODO: use fixture instead ?
def populate():
    create_rtype = RelationType.objects.smart_update_or_create
    create_rtype(
        (
            fake_constants.FAKE_REL_SUB_EMPLOYED_BY,
            'is an employee of',
            [fake_models.FakeContact],
        ), (
            fake_constants.FAKE_REL_OBJ_EMPLOYED_BY,
            'employs',
            [fake_models.FakeOrganisation],
        ),
    )
    create_rtype(
        (
            fake_constants.FAKE_REL_SUB_BILL_ISSUED,
            'issued by',
            [fake_models.FakeInvoice],
        ), (
            fake_constants.FAKE_REL_OBJ_BILL_ISSUED,
            'has issued',
            [fake_models.FakeOrganisation],
        ),
        is_internal=True
    )
    create_rtype(
        (
            fake_constants.FAKE_REL_SUB_BILL_RECEIVED,
            'received by',
            [fake_models.FakeInvoice],
        ), (
            fake_constants.FAKE_REL_OBJ_BILL_RECEIVED,
            'has received',
            [fake_models.FakeOrganisation, fake_models.FakeContact],
        ),
        is_internal=True
    )

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

    create_hf = HeaderFilter.objects.create_if_needed
    create_hf(
        pk='creme_core-hf_fakeimage', name='FakeImage view',
        model=fake_models.FakeImage,
        cells_desc=[(EntityCellRegularField, {'name': 'name'})],
    )
    create_hf(
        pk=fake_constants.DEFAULT_HFILTER_FAKE_CONTACT,
        name='FakeContact view',
        model=fake_models.FakeContact,
        cells_desc=[
            (EntityCellRegularField, {'name': 'last_name'}),
            (EntityCellRegularField, {'name': 'first_name'}),
            (EntityCellRegularField, {'name': 'email'}),
        ],
    )
    create_hf(
        pk=fake_constants.DEFAULT_HFILTER_FAKE_ORGA,
        name='FakeOrganisation view',
        model=fake_models.FakeOrganisation,
        cells_desc=[
            (EntityCellRegularField, {'name': 'name'}),
            (EntityCellRegularField, {'name': 'phone'}),
        ],
    )
    create_hf(
        pk=fake_constants.DEFAULT_HFILTER_FAKE_ACTIVITY,
        name='FakeActivity view',
        model=fake_models.FakeActivity,
        cells_desc=[
            (EntityCellRegularField, {'name': 'title'}),
            (EntityCellRegularField, {'name': 'start'}),
        ],
    )
    create_hf(
        pk=fake_constants.DEFAULT_HFILTER_FAKE_INVLINE,
        name='FakeInvoiceLine view',
        model=fake_models.FakeInvoiceLine,
        cells_desc=[
            (EntityCellRegularField, {'name': 'linked_invoice'}),
            (EntityCellRegularField, {'name': 'item'}),
            (EntityCellRegularField, {'name': 'quantity'}),
        ],
    )
    # NB: do not create for HeaderFilter for FakeMailingList (see views.test_header_filter)

    CustomFormConfigItem.objects.create_if_needed(
        descriptor=fake_custom_forms.FAKEORGANISATION_CREATION_CFORM,
        groups_desc=[
            {
                'name': 'General',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                    (EntityCellRegularField, {'name': 'sector'}),
                    # (
                    #     EntityCellCustomFormSpecial,
                    #     {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    # ),
                ],
            },
        ],
    )
    CustomFormConfigItem.objects.create_if_needed(
        descriptor=fake_custom_forms.FAKEACTIVITY_CREATION_CFORM,
        groups_desc=[
            {
                'name': 'General',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'title'}),
                    (EntityCellRegularField, {'name': 'type'}),
                    # (EntityCellRegularField, {'name': 'minutes'}),  # Not in the default config
                    # (EntityCellRegularField, {'name': 'description'}),  # Excluded
                    # (
                    #     EntityCellCustomFormSpecial,
                    #     {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    # ),  # Should be used in regular populate scripts
                ],
                'layout': base_forms.LAYOUT_DUAL_FIRST,
            }, {
                'name': 'Where & when',
                'cells': [
                    (EntityCellRegularField, {'name': 'place'}),
                    fake_forms.FakeActivityStartSubCell().into_cell(),
                    fake_forms.FakeActivityEndSubCell().into_cell(),
                ],
                'layout': base_forms.LAYOUT_DUAL_SECOND,
            }, {
                'name': 'Custom fields',
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS},
                    ),
                ],
            },
        ],
    )
    CustomFormConfigItem.objects.create_if_needed(
        descriptor=fake_custom_forms.FAKEACTIVITY_EDITION_CFORM,
        groups_desc=[
            {
                'name': 'General',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'title'}),
                    (EntityCellRegularField, {'name': 'type'}),
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    ),
                ],
            }, {
                'name': 'Where & when',
                'cells': [
                    (EntityCellRegularField, {'name': 'place'}),
                    fake_forms.FakeActivityStartSubCell().into_cell(),
                    fake_forms.FakeActivityEndSubCell().into_cell(),
                ],
            },
        ],
    )
