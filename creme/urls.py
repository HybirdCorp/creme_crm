# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin

admin.autodiscover()

import creme_core
creme_core.autodiscover()


handler500 = 'creme_core.views.exceptions.server_error'

urlpatterns = patterns('',
    url(r'^creme_login/$',  'django.contrib.auth.views.login', {'template_name': 'authent/creme_login.html'} , name="creme_login"),
    url(r'^creme_logout/$', 'django.contrib.auth.views.logout_then_login' , name="creme_logout"),
    (r'^', include('creme_core.urls')),

    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    #NB: in production, configure your web server to statically serve the files in the 'media/static/' dir (and so comment the following line)
    (r'^static_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.GENERATED_MEDIA_DIR}),

    (r'^creme_config/',   include('creme_config.urls')),
    (r'^media_managers/', include('media_managers.urls')),
    (r'^documents/',      include('documents.urls')),
    (r'^assistants/',     include('assistants.urls')),
    (r'^activities/',     include('activities.urls')),
    (r'^persons/',        include('persons.urls')),

    (r'^graphs/',         include('graphs.urls')),
    (r'^reports/',        include('reports.urls')),
    (r'^products/',       include('products.urls')),
    (r'^recurrents/',     include('recurrents.urls')),
    (r'^billing/',        include('billing.urls')),
    (r'^opportunities/',  include('opportunities.urls')),
    (r'^commercial/',     include('commercial.urls')),
    (r'^events/',         include('events.urls')),
    (r'^crudity/',        include('crudity.urls')),
    (r'^emails/',         include('emails.urls')),
    (r'^sms/',            include('sms.urls')),
    (r'^projects/',       include('projects.urls')),
    (r'^tickets/',        include('tickets.urls')),
    (r'^activesync/',     include('activesync.urls')),
    (r'^cti/',            include('cti.urls')),
    (r'^vcfs/',           include('vcfs.urls')),

    (r'^admin/(.*)', include(admin.site.urls)),
)
