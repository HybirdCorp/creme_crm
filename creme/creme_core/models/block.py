# -*- coding: utf-8 -*-

import warnings

warnings.warn('creme_core.models.block is deprecated ; use creme_core.models.bricks instead.',
              DeprecationWarning
             )

from .bricks import *
