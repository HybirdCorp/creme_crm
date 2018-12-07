# -*- coding: utf-8 -*-

from django.conf import settings

from . import models


to_register = (
    (models.Language, 'language'),
    (models.Currency, 'currency'),
    (models.Vat,      'vat_value'),
)

if settings.TESTS_ON:
    from .tests import fake_models, fake_bricks

    to_register += (
        (fake_models.FakeImageCategory, 'fake_img_cat'),
        (fake_models.FakeCivility,      'fake_civility'),
        (fake_models.FakePosition,      'fake_position'),
        (fake_models.FakeSector,        'fake_sector'),
        (fake_models.FakeLegalForm,     'fake_legalform'),
    )

    blocks_to_register = (
        ('creme_core', fake_bricks.FakeAppPortalBrick),
    )
