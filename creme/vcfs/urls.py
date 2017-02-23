# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme import persons
from .views import vcf  # TODO: merge in a views.py ??


urlpatterns = [
    url(r'^(?P<contact_id>\d+)/generate_vcf$', vcf.vcf_export, name='vcfs__export'),
]

if not persons.contact_model_is_custom() and not persons.organisation_model_is_custom() and \
   not persons.address_model_is_custom():
    urlpatterns += [
        url(r'^vcf', vcf.vcf_import, name='vcfs__import'),
    ]
