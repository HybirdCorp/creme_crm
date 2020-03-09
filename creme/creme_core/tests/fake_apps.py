# -*- coding: utf-8 -*-

already_run = False


def ready():
    global already_run

    if already_run:
        return

    already_run = True

    from ..core.function_field import function_field_registry
    from ..core.imprint import imprint_manager
    from ..gui.bricks import brick_registry
    from ..gui.quick_forms import quickforms_registry
    from ..gui.listview import smart_columns_registry
    from ..gui.mass_import import import_form_registry
    from ..gui.merge import merge_form_registry
    from ..models import CremeEntity
    from ..registry import creme_registry

    from .fake_bricks import FakeAppPortalBrick
    from .fake_constants import FAKE_REL_SUB_EMPLOYED_BY
    from .fake_forms import (
        FakeContactQuickForm, FakeOrganisationQuickForm,
        get_csv_form_builder, get_merge_form_builder,
    )
    from . import fake_function_fields
    from .fake_models import (
        FakeContact, FakeOrganisation, FakeImage,
        FakeActivity, FakeEmailCampaign, FakeMailingList,
        FakeInvoice, FakeInvoiceLine, FakeTicket, FakeRecipe,
    )

    from creme.creme_config.tests.fake_models import FakeConfigEntity

    creme_registry.register_entity_models(
        FakeContact,
        FakeOrganisation,
        FakeImage,
        FakeActivity,
        FakeEmailCampaign,
        FakeMailingList,
        FakeInvoice,
        FakeInvoiceLine,
        FakeConfigEntity,
        FakeTicket,
        FakeRecipe,
    )

    function_field_registry.register(CremeEntity, fake_function_fields.FakeTodosField)

    imprint_manager.register(
        FakeOrganisation, hours=2,
    ).register(
        FakeContact, minutes=60,
    )

    brick_registry.register(
        FakeAppPortalBrick,
    ).register_invalid_models(
        FakeInvoiceLine,  # See creme_config tests
    )

    quickforms_registry.register(
        FakeContact,      FakeContactQuickForm
    ).register(
        FakeOrganisation, FakeOrganisationQuickForm
    )

    smart_columns_registry.register_model(FakeContact) \
                          .register_field('first_name') \
                          .register_field('last_name') \
                          .register_relationtype(FAKE_REL_SUB_EMPLOYED_BY)

    import_form_registry.register(
        FakeContact,      get_csv_form_builder,
    ).register(
        FakeOrganisation, get_csv_form_builder,
    )

    merge_form_registry.register(
        FakeContact,      get_merge_form_builder,
    ).register(
        FakeOrganisation, get_merge_form_builder,
    )
