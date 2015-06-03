# -*- coding: utf-8 -*-

from django.dispatch import Signal


form_post_save    = Signal(providing_args=['instance', 'created'])
pre_merge_related = Signal(providing_args=['other_entity'])
pre_replace_related = Signal(providing_args=['old_instance', 'new_instance'])
