# -*- coding: utf-8 -*-

from django.conf import settings

from .models import Currency, Vat, Language


to_register = ((Language, 'language'),
               (Currency, 'currency'),
               (Vat,      'vat_value'),
              )


if settings.TESTS_ON:
    from .tests import fake_models
    to_register += ((fake_models.FakeImageCategory, 'fake_img_cat'),
                    (fake_models.FakeCivility,      'fake_civility'),
                    (fake_models.FakePosition,      'fake_position'),
                    (fake_models.FakeSector,        'fake_sector'),
                    (fake_models.FakeLegalForm,     'fake_legalform'),
                   )
