# -*- coding: utf-8 -*-

from .models import Currency, Vat, Language


to_register = ((Language, 'language'),
               (Currency, 'currency'),
               (Vat,      'vat_value'),
              )
