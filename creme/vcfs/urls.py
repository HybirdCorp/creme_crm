# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.persons import (contact_model_is_custom, organisation_model_is_custom,
        address_model_is_custom)
from .views import vcf #TODO: merge in a views.py ??


urlpatterns = [
    url(r'^(?P<contact_id>\d+)/generate_vcf$', vcf.vcf_export),
]

if not contact_model_is_custom() and not organisation_model_is_custom() and \
   not address_model_is_custom():
    urlpatterns += [
        url(r'^vcf', vcf.vcf_import, name='vcfs__import'),
    ]
