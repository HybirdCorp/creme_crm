# -*- coding: utf-8 -*-

from creme.creme_core.models.currency import Currency
from creme.creme_core.models.i18n import Language

to_register = ((Language, 'language'),
               (Currency, 'currency'),)
