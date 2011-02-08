# -*- coding: utf-8 -*-

from imp import find_module

from django.conf import settings


#TODO: use creme_core.utils.imports ???
def autodiscover():
    """Auto-discover in INSTALLED_APPS the creme_core_register.py files."""
    for app in settings.INSTALLED_APPS:
        try:
            find_module("creme_core_register", __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
        except ImportError, e:
            # there is no app creme_config.py, skip it
            continue
        __import__("%s.creme_core_register" % app)
