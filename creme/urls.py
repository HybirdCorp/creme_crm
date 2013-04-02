# -*- coding: utf-8 -*-

from django.conf.urls import url, patterns, include
from django.conf import settings
#from django.contrib import admin

#admin.autodiscover()

from creme import creme_core
creme_core.autodiscover()


handler500 = 'creme.creme_core.views.exceptions.server_error'

urlpatterns = patterns('',
    url(r'^creme_login/$',  'django.contrib.auth.views.login', {'template_name': 'authent/creme_login.html'} , name="creme_login"),
    url(r'^creme_logout/$', 'django.contrib.auth.views.logout_then_login' , name="creme_logout"),

    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    #NB: in production, configure your web server to statically serve the files in the 'media/static/' dir (and so comment the following line)
    (r'^static_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.GENERATED_MEDIA_DIR}),

    #(r'^admin/(.*)', include(admin.site.urls)),
)

for app_name in settings.INSTALLED_CREME_APPS:
    #regex_url = r'^' if app_name == 'creme_core' else r'^%s/' % app_name
    short_app_name = app_name.split('.')[-1] #eg 'creme.persons'  => 'persons'
    regex_url = r'^' if short_app_name == 'creme_core' else r'^%s/' % short_app_name

    urlpatterns += patterns('', (regex_url, include('%s.urls' % app_name)))
