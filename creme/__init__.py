# -*- coding: utf-8 -*-

import django.dispatch

form_post_save = django.dispatch.Signal(providing_args=["sender", "instance", "created"])

__version__ = '0.10 beta'
