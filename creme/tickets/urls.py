# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns

urlpatterns = patterns('tickets.views',
    (r'^$', 'portal.portal'),

    (r'^tickets$',                        'ticket.listview'),
    (r'^ticket/add$',                     'ticket.add'),
    (r'^ticket/edit/(?P<ticket_id>\d+)$', 'ticket.edit'),
    (r'^ticket/(?P<object_id>\d+)$',      'ticket.detailview'),
)

urlpatterns += patterns('creme_core.views',
    (r'^ticket/edit_js/$',                                'ajax.edit_js'),
    (r'^ticket/delete/(?P<object_id>\d+)$',               'generic.delete_entity'),
    (r'^ticket/delete_js/(?P<entities_ids>([\d]+[,])+)$', 'generic.delete_entities_js'),
)
