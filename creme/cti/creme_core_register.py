# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.registry import creme_registry
from creme.creme_core.gui.field_printers import field_printers_registry
from creme.creme_core.models.fields  import PhoneField

from creme.cti.utils import print_phone


creme_registry.register_app('cti', _(u'Computer Telephony Integration'), '/cti')

field_printers_registry.register(PhoneField, print_phone)
