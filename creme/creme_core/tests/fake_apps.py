# -*- coding: utf-8 -*-

already_run = False


def ready():
    global already_run

    if already_run:
        return

    already_run = True

    from creme.creme_config.tests.fake_models import FakeConfigEntity

    from ..core.download import filefield_download_registry
    from ..core.function_field import function_field_registry
    from ..core.imprint import imprint_manager
    from ..gui.bricks import brick_registry
    from ..gui.custom_form import customform_descriptor_registry
    from ..gui.fields_config import fields_config_registry
    from ..gui.icons import icon_registry
    from ..gui.listview import smart_columns_registry
    from ..gui.mass_import import import_form_registry
    from ..gui.menu import menu_registry
    from ..gui.merge import merge_form_registry
    from ..gui.quick_forms import quickforms_registry
    from ..models import CremeEntity
    from ..registry import creme_registry
    from . import (
        fake_custom_forms,
        fake_forms,
        fake_function_fields,
        fake_menu,
        fake_models,
    )
    from .fake_bricks import FakeAppPortalBrick
    from .fake_constants import FAKE_REL_SUB_EMPLOYED_BY

    creme_registry.register_entity_models(
        fake_models.FakeContact,
        fake_models.FakeOrganisation,
        fake_models.FakeDocument,
        fake_models.FakeImage,
        fake_models.FakeActivity,
        fake_models.FakeEmailCampaign,
        fake_models.FakeMailingList,
        fake_models.FakeInvoice,
        fake_models.FakeInvoiceLine,
        fake_models.FakeTicket,
        fake_models.FakeRecipe,
        FakeConfigEntity,
    )

    function_field_registry.register(CremeEntity, fake_function_fields.FakeTodosField)

    fields_config_registry.register_models(
        fake_models.FakeContact,
        fake_models.FakeOrganisation,
        fake_models.FakeDocument,
        # TODO ?
        # fake_models.FakeImage,
        # fake_models.FakeEmailCampaign,
        # fake_models.FakeMailingList,
        # fake_models.FakeInvoice,
        # fake_models.FakeInvoiceLine,
        # fake_models.FakeTicket,
        # fake_models.FakeRecipe,

        # No (see creme_config.tests.test_fields_config.FieldsConfigTestCase.test_edit03)
        # fake_models.FakeActivity,
    )

    icon_registry.register(
        fake_models.FakeContact, 'images/contact_%(size)s.png',
    ).register(
        fake_models.FakeOrganisation, 'images/organisation_%(size)s.png',
    )

    imprint_manager.register(
        fake_models.FakeOrganisation, hours=2,
    ).register(
        fake_models.FakeContact, minutes=60,
    )

    menu_registry.register(
        fake_menu.FakeContactsEntry,
        fake_menu.FakeContactCreationEntry,
        fake_menu.FakeOrganisationsEntry,
        fake_menu.FakeOrganisationCreationEntry,
    )

    brick_registry.register(
        FakeAppPortalBrick,
    ).register_invalid_models(
        fake_models.FakeInvoiceLine,  # See creme_config tests
    )

    customform_descriptor_registry.register(
        fake_custom_forms.FAKEORGANISATION_CREATION_CFORM,

        fake_custom_forms.FAKEACTIVITY_CREATION_CFORM,
        fake_custom_forms.FAKEACTIVITY_EDITION_CFORM,
    )

    quickforms_registry.register(
        fake_models.FakeContact,      fake_forms.FakeContactQuickForm
    ).register(
        fake_models.FakeOrganisation, fake_forms.FakeOrganisationQuickForm
    )

    smart_columns_registry.register_model(
        fake_models.FakeContact
    ).register_field(
        'first_name',
    ).register_field(
        'last_name',
    ).register_relationtype(
        FAKE_REL_SUB_EMPLOYED_BY,
    )

    import_form_registry.register(
        fake_models.FakeContact,      fake_forms.get_csv_form_builder,
    ).register(
        fake_models.FakeOrganisation, fake_forms.get_csv_form_builder,
    )

    merge_form_registry.register(
        fake_models.FakeContact,      fake_forms.get_merge_form_builder,
    ).register(
        fake_models.FakeOrganisation, fake_forms.get_merge_form_builder,
    )

    filefield_download_registry.register(
        model=fake_models.FakeDocument, field_name='filedata',
    )
