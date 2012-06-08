# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('vcfs.views',
    (r'^vcf',                               'vcf.vcf_import'),
    (r'^(?P<contact_id>\d+)/generate_vcf$', 'vcf.vcf_export'),
)
