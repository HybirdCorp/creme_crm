################################################################################
#
# Copyright (c) 2024-2026 Hybird
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

from .utils import model_verbose_name


# Hint: can be used as __str__() method (see apps.py)
def ct_str(ct):
    model = ct.model_class()
    return ct.model if model is None else model_verbose_name(model)


# Hint: can be used as portable_key() method (see apps.py)
def ct_portable_key(ct):
    return '.'.join(ct.natural_key())


# Hint: can be used as get_portable_key() method for manager (see apps.py)
def get_ct_by_portable_key(manager, key):
    app_label, model_name = key.split('.', 2)

    return manager.get_by_natural_key(app_label=app_label, model=model_name)
