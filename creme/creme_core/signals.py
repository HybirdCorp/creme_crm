# -*- coding: utf-8 -*-

from django.dispatch import Signal


pre_merge_related = Signal(providing_args=['other_entity'])
