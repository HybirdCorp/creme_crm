# -*- coding: utf-8 -*-

################################################################################
#   This code is derived from the 'currency' function of the module 'locale.py' of the Python2.7 standard library.
#   The function has been modified to take the id of the wanted currency.
#
#    Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011
#    Python Software Foundation.  All rights reserved.
#
#    Copyright (C) 2009-2011  Hybird
#
#    This file is released under the Python License (http://www.opensource.org/licenses/Python-2.0)
################################################################################

import os
import locale

from django.conf import settings
from django.utils import translation

# Windows list locale code : http://msdn.microsoft.com/en-us/library/39cwe7zf%28vs.71%29.aspx
from creme.creme_config.models.setting import SettingKey, SettingValue
from creme.creme_core.constants import DISPLAY_CURRENCY_LOCAL_SYMBOL
from creme.creme_core.models.currency import Currency

WINDOWS = 'nt'

if os.name == WINDOWS:
    LOCALE_MAP = {
        'en': 'english',
        'fr': 'fra',
    }
    def standardized_locale_code(django_code):
        return LOCALE_MAP[django_code]
else:
    def standardized_locale_code(django_code):
        return translation.to_locale(django_code)

def currency(val, currency_id):
    # TODO there still are some windows encoding problems to fix. UTF-8 seems not working properly
    try:
        locale.setlocale(locale.LC_MONETARY, (standardized_locale_code(settings.LANGUAGE_CODE), settings.DEFAULT_ENCODING))
    except:
        locale.setlocale(locale.LC_MONETARY, '')

    conv = locale.localeconv()

    sk = SettingKey.objects.get(pk = DISPLAY_CURRENCY_LOCAL_SYMBOL)
    is_local_symbol =  SettingValue.objects.get(key = sk).value

    if currency_id:
        currency = Currency.objects.get(pk = currency_id)
        smb = currency.local_symbol if is_local_symbol else currency.international_symbol
    else:
        smb = ''

    # check for illegal values
    digits = conv[not is_local_symbol and 'int_frac_digits' or 'frac_digits']

    s = locale.format('%%.%if' % digits, abs(val), True, monetary=True)
    # '<' and '>' are markers if the sign must be inserted between symbol and value
    s = '<' + s + '>'


    precedes = conv[val<0 and 'n_cs_precedes' or 'p_cs_precedes']
    separated = conv[val<0 and 'n_sep_by_space' or 'p_sep_by_space']

    if precedes:
        s = smb + (separated and ' ' or '') + s
    else:
        s = s + (separated and ' ' or '') + smb

    sign_pos = conv[val<0 and 'n_sign_posn' or 'p_sign_posn']
    sign = conv[val<0 and 'negative_sign' or 'positive_sign']

    if sign_pos == 0:
        s = '(' + s + ')'
    elif sign_pos == 1:
        s = sign + s
    elif sign_pos == 2:
        s = s + sign
    elif sign_pos == 3:
        s = s.replace('<', sign)
    elif sign_pos == 4:
        s = s.replace('>', sign)
    else:
        # the default if nothing specified;
        # this should be the most fitting sign position
        s = sign + s

    return s.replace('<', '').replace('>', '')
