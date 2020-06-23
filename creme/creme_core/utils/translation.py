# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2016-2020 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from typing import Type

from django.conf import settings
from django.db.models import Model

if settings.USE_I18N:
    from django.utils.translation import _trans

    def plural(number: int) -> bool:
        return bool(_trans.translation(_trans.get_language()).plural(number))
else:
    def plural(number: int) -> bool:
        return number != 1


# TODO: automatise the creation of plural form for models verbose names
#       (& so use ngettext() instead) ?
def get_model_verbose_name(model: Type[Model], count: int):
    return model._meta.verbose_name_plural if plural(count) else model._meta.verbose_name
