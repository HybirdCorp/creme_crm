# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.gui import block_registry
from creme.creme_core.registry import creme_registry

from .blocks import favorite_persons_block


creme_registry.register_app('mobile', _(u'Mobile'), credentials=creme_registry.CRED_NONE) # mandatory to get our own URLs

block_registry.register(favorite_persons_block)
