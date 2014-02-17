# -*- coding: utf-8 -*-

################################################################################
#   This code is derived from the 'currency' function of the module 'locale.py' of the Python2.7 standard library.
#   The function has been modified to take the id of the wanted currency.
#
#    Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011
#    Python Software Foundation.  All rights reserved.
#
#    Copyright (C) 2009-2014  Hybird
#
#    This file is released under the Python License (http://www.opensource.org/licenses/Python-2.0)
################################################################################

import os
import locale
import logging

from django.conf import settings
from django.utils import translation

from creme.creme_config.models import SettingKey, SettingValue

from ..constants import DISPLAY_CURRENCY_LOCAL_SYMBOL
from ..models import Currency

logger = logging.getLogger(__name__)
WINDOWS = 'nt'

if os.name == WINDOWS:
    # Windows list locale code : http://msdn.microsoft.com/en-us/library/39cwe7zf%28vs.71%29.aspx
    LOCALE_MAP = {
        'en': 'english',
        'fr': 'fra',
    }
    def standardized_locale_code(django_code):
        return LOCALE_MAP[django_code]
else:
    def standardized_locale_code(django_code):
        return translation.to_locale(django_code)

#TODO: use an object Formatter in order to avoid multiple queries of SettingKey/SettingValue
def currency(val, currency_or_id=None):
    """Replace a formatted string for an amount.
    @param val Amount as a numeric value.
    @param currency_or_id Instance of creme_core.models.Currency, or an ID of Currency instance.
    """
    LC_MONETARY = locale.LC_MONETARY
    lang = standardized_locale_code(settings.LANGUAGE_CODE)

    try:
        locale.setlocale(LC_MONETARY, (lang, settings.DEFAULT_ENCODING)) #will certainly fail on Windows (because of utf-8)
    except:
        try:
            locale.setlocale(LC_MONETARY, lang)
        except:
            logger.warn('currency(): fail when setting "%s"', lang)
            locale.setlocale(LC_MONETARY, '')

    conv = locale.localeconv()

    sk = SettingKey.objects.get(pk=DISPLAY_CURRENCY_LOCAL_SYMBOL)
    is_local_symbol = SettingValue.objects.get(key=sk).value

    if currency_or_id:
        currency_obj = currency_or_id if isinstance(currency_or_id, Currency) else \
                       Currency.objects.get(pk=currency_id)

        smb = currency_obj.local_symbol if is_local_symbol else currency_obj.international_symbol
    else:
        smb = ''

    # check for illegal values
    digits = conv[not is_local_symbol and 'int_frac_digits' or 'frac_digits']

    s = locale.format('%%.%if' % digits, abs(val), True, monetary=True)
    s = s.decode(locale.getlocale(LC_MONETARY)[1])

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
