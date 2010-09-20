# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin

admin.autodiscover()

import creme_core
creme_core.autodiscover()


urlpatterns = patterns('',
    url(r'^creme_login/$',  'django.contrib.auth.views.login', {'template_name': 'authent/creme_login.html'} , name="creme_login"),
    url(r'^creme_logout/$', 'django.contrib.auth.views.logout_then_login' , name="creme_logout"),
    (r'^', include('creme.creme_core.urls')),

    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),

    (r'^creme_config/',   include('creme.creme_config.urls')),
    (r'^assistants/',     include('creme.assistants.urls')),
    (r'^documents/',      include('creme.documents.urls')),
    (r'^media_managers/', include('creme.media_managers.urls')),
    (r'^graphs/',         include('creme.graphs.urls')),
    (r'^reports/',        include('creme.reports.urls')),
    (r'^activities/',     include('creme.activities.urls')),
    (r'^persons/',        include('creme.persons.urls')),
    (r'^products/',       include('creme.products.urls')),
    (r'^recurrents/',     include('creme.recurrents.urls')),
    (r'^billing/',        include('creme.billing.urls')),
    (r'^emails/',         include('creme.emails.urls')),
    (r'^sms/',            include('creme.sms.urls')),
    (r'^opportunities/',  include('creme.opportunities.urls')),
    (r'^commercial/',     include('creme.commercial.urls')),
    (r'^tickets/',        include('creme.tickets.urls')),
    (r'^projects/',       include('creme.projects.urls')),
    (r'^crudity/',        include('creme.crudity.urls')),

    (r'^admin/(.*)', admin.site.root),

)
