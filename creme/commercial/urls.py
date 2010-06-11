# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns

urlpatterns = patterns('commercial.views',
    (r'^$', 'portal.portal'),

    (r'^salesmen$',     'salesman.listview'), #TODO: list_contacts + property
    (r'^salesman/add$', 'salesman.add'),

    (r'^acts$',                     'act.listview'),
    (r'^act/add$',                  'act.add'),
    (r'^act/edit/(?P<act_id>\d+)$', 'act.edit'),
    (r'^act/(?P<object_id>\d+)$',   'act.detailview'),

    (r'^approach/add/(?P<entity_id>\d+)/$',            'commercial_approach.add'),
    (r'^approaches/reload/home/$',                     'commercial_approach.reload_home_approaches'),
    (r'^approaches/reload/(?P<entity_id>\d+)/$',       'commercial_approach.reload_approaches'),
    (r'^approaches/reload/portal/(?P<ct_id>[\d,]+)/$', 'commercial_approach.reload_portal_approaches'),

    (r'^/relsellby/edit/(?P<relation_id>\d+)$', 'sell_by_relation.edit'),
)

urlpatterns += patterns('creme_core.views',
    (r'^act/edit_js/$',                                'ajax.edit_js'),
    (r'^act/delete/(?P<object_id>\d+)$',               'generic.delete_entity'),
    (r'^act/delete_js/(?P<entities_ids>([\d]+[,])+)$', 'generic.delete_entities_js'),
)
