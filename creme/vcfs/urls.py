# -*- coding: utf-8 -*-

from django.urls import re_path

from creme import persons
from creme.creme_core.conf.urls import Swappable, swap_manager

from .views import vcf  # TODO: merge in a views.py ??

urlpatterns = [
    re_path(r'^(?P<contact_id>\d+)/generate_vcf[/]?$', vcf.vcf_export, name='vcfs__export'),

    *swap_manager.add_group(
        lambda:
            persons.contact_model_is_custom()
            or persons.organisation_model_is_custom()
            or persons.address_model_is_custom(),
        Swappable(re_path(r'^vcf[/]?', vcf.vcf_import, name='vcfs__import')),
        app_name='vcfs',
    ).kept_patterns(),
]
