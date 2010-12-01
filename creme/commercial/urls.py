# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('commercial.views',
    (r'^$', 'portal.portal'),

    (r'^salesmen$',     'salesman.listview'), #TODO: list_contacts + property
    (r'^salesman/add$', 'salesman.add'),

    (r'^approach/add/(?P<entity_id>\d+)/$', 'commercial_approach.add'),

    (r'^acts$',                     'act.listview'),
    (r'^act/add$',                  'act.add'),
    (r'^act/edit/(?P<act_id>\d+)$', 'act.edit'),
    (r'^act/(?P<act_id>\d+)$',      'act.detailview'),

    (r'^strategies$',                         'strategy.listview'),
    (r'^strategy/add$',                       'strategy.add'),
    (r'^strategy/edit/(?P<strategy_id>\d+)$', 'strategy.edit'),
    (r'^strategy/(?P<strategy_id>\d+)$',      'strategy.detailview'),

    #Segments
    (r'^strategy/(?P<strategy_id>\d+)/add/segment/$', 'strategy.add_segment'),
    (r'^segment/edit/(?P<segment_id>\d+)/$',          'strategy.edit_segment'),
    (r'^segment/delete$',                             'strategy.delete_segment'),

    #Assets
    (r'^strategy/(?P<strategy_id>\d+)/add/asset/$', 'strategy.add_asset'),
    (r'^asset/edit/(?P<asset_id>\d+)/$',            'strategy.edit_asset'),
    (r'^asset/delete$',                             'strategy.delete_asset'),

    #Charms
    (r'^strategy/(?P<strategy_id>\d+)/add/charm/$', 'strategy.add_charm'),
    (r'^charm/edit/(?P<charm_id>\d+)/$',            'strategy.edit_charm'),
    (r'^charm/delete$',                             'strategy.delete_charm'),

    #Evaluated organisations
    (r'^strategy/(?P<strategy_id>\d+)/add/organisation/$',             'strategy.add_evalorga'),
    (r'^strategy/(?P<strategy_id>\d+)/organisation/delete$',           'strategy.delete_evalorga'),
    (r'^strategy/(?P<strategy_id>\d+)/organisation/(?P<orga_id>\d+)$', 'strategy.orga_evaluation'),

    #Scores
    (r'^strategy/(?P<strategy_id>\d+)/set_asset_score$', 'strategy.set_asset_score'),
    (r'^strategy/(?P<strategy_id>\d+)/set_charm_score$', 'strategy.set_charm_score'),

    #Blocks
    (r'^blocks/assets_matrix/(?P<strategy_id>\d+)/(?P<orga_id>\d+)/$', 'strategy.reload_assets_matrix'),
    (r'^blocks/charms_matrix/(?P<strategy_id>\d+)/(?P<orga_id>\d+)/$', 'strategy.reload_charms_matrix'),

    (r'^relsellby/edit/(?P<relation_id>\d+)$', 'sell_by_relation.edit'),
)

urlpatterns += patterns('creme_core.views',
    (r'^act/edit_js/$',                                'ajax.edit_js'),
    (r'^act/delete/(?P<object_id>\d+)$',               'generic.delete_entity'),
    (r'^act/delete_js/(?P<entities_ids>([\d]+[,])+)$', 'generic.delete_entities_js'),

    (r'^strategy/delete/(?P<object_id>\d+)$',               'generic.delete_entity'),
    (r'^strategy/delete_js/(?P<entities_ids>([\d]+[,])+)$', 'generic.delete_entities_js'),
)
