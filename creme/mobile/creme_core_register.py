# -*- coding: utf-8 -*-

from creme.creme_core.gui import block_registry

from .blocks import favorite_persons_block


block_registry.register(favorite_persons_block)
