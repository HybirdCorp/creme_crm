# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.creme_core.conf.urls import Swappable, swap_manager

from creme import persons
from .views import vcf  # TODO: merge in a views.py ??


urlpatterns = [
    url(r'^(?P<contact_id>\d+)/generate_vcf[/]?$', vcf.vcf_export, name='vcfs__export'),
]

urlpatterns += swap_manager.add_group(
    lambda: persons.contact_model_is_custom() or
            persons.organisation_model_is_custom() or
            persons.address_model_is_custom(),
    Swappable(url(r'^vcf[/]?', vcf.vcf_import, name='vcfs__import')),
    app_name='vcfs',
).kept_patterns()
