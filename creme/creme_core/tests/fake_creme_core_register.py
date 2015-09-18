# -*- coding: utf-8 -*-

# TODO: rename ?? (fake_apps.py + ready() ??)

already_runned = False

def register():
    global already_runned

    if already_runned:
        return

    already_runned = True

    from ..gui import (block_registry, smart_columns_registry, import_form_registry,
            merge_form_registry, quickforms_registry)
    from ..registry import creme_registry

    from .fake_forms import (FakeContactQuickForm, FakeOrganisationQuickForm,
            get_csv_form_builder, get_merge_form_builder)
    from .fake_constants import FAKE_REL_SUB_EMPLOYED_BY
    from .fake_models import (FakeContact, FakeOrganisation, FakeImage, FakeActivity,
            FakeEmailCampaign, FakeMailingList, FakeInvoice, FakeInvoiceLine)


    creme_registry.register_entity_models(FakeContact,
                                          FakeOrganisation,
                                          FakeImage,
                                          FakeActivity,
                                          FakeEmailCampaign,
                                          FakeMailingList,
                                          FakeInvoice,
                                          FakeInvoiceLine,
                                         )

    block_registry.register_invalid_models(FakeInvoiceLine) # see creme_config tests

    reg_qform = quickforms_registry.register
    reg_qform(FakeContact,      FakeContactQuickForm)
    reg_qform(FakeOrganisation, FakeOrganisationQuickForm)

    smart_columns_registry.register_model(FakeContact) \
                        .register_field('first_name') \
                        .register_field('last_name') \
                        .register_relationtype(FAKE_REL_SUB_EMPLOYED_BY)

    reg_csv_form = import_form_registry.register
    reg_csv_form(FakeContact,      get_csv_form_builder)
    reg_csv_form(FakeOrganisation, get_csv_form_builder)


    reg_merge_form = merge_form_registry.register
    reg_merge_form(FakeContact,      get_merge_form_builder)
    reg_merge_form(FakeOrganisation, get_merge_form_builder)
