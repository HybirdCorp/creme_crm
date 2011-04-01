# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui.field_printers import field_printers_registry
from creme_core.models.fields  import PhoneField

from cti.utils import print_phone


creme_registry.register_app('cti', _(u'Computer Telephony Integration'), '/cti')

#field_printers_registry[PhoneField] = print_phone
field_printers_registry.register(PhoneField, print_phone)
