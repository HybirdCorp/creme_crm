# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('commercial.views',
    (r'^$', 'portal.portal'),

    (r'^salesmen$',     'salesman.listview'), #TODO: list_contacts + property
    (r'^salesman/add$', 'salesman.add'),

    (r'^approach/add/(?P<entity_id>\d+)/$', 'commercial_approach.add'),

    #Segments
    (r'^market_segments$',    'market_segment.listview'),
    (r'^market_segment/add$', 'market_segment.add'),

    #Acts
    (r'^acts$',                     'act.listview'),
    (r'^act/add$',                  'act.add'),
    (r'^act/edit/(?P<act_id>\d+)$', 'act.edit'),
    (r'^act/(?P<act_id>\d+)$',      'act.detailview'),

    #Objectives
    (r'^act/(?P<act_id>\d+)/add/objective$',               'act.add_objective'),
    (r'^act/(?P<act_id>\d+)/add/objectives_from_pattern$', 'act.add_objectives_from_pattern'),
    (r'^objective/(?P<objective_id>\d+)/edit$',            'act.edit_objective'),
    (r'^objective/(?P<objective_id>\d+)/incr$',            'act.incr_objective_counter'),

    #Objective patterns
    (r'^objective_patterns$',                            'act.listview_objective_pattern'),
    (r'^objective_pattern/add$',                         'act.add_objective_pattern'),
    (r'^objective_pattern/edit/(?P<objpattern_id>\d+)$', 'act.edit_objective_pattern'),
    (r'^objective_pattern/(?P<objpattern_id>\d+)$',      'act.objective_pattern_detailview'), #TODO: a separated file for pattern ???

    #Pattern component
    (r'^objective_pattern/(?P<objpattern_id>\d+)/add_component$',     'act.add_pattern_component'),
    (r'^objective_pattern/component/(?P<component_id>\d+)/add_child', 'act.add_child_pattern_component'),

    (r'^strategies$',                         'strategy.listview'),
    (r'^strategy/add$',                       'strategy.add'),
    (r'^strategy/edit/(?P<strategy_id>\d+)$', 'strategy.edit'),
    (r'^strategy/(?P<strategy_id>\d+)$',      'strategy.detailview'),

    #Segments
    (r'^strategy/(?P<strategy_id>\d+)/add/segment/$',                      'strategy.add_segment'),
    (r'^strategy/(?P<strategy_id>\d+)/link/segment/$',                     'strategy.link_segment'),
    (r'^strategy/(?P<strategy_id>\d+)/segment/edit/(?P<seginfo_id>\d+)/$', 'strategy.edit_segment'),

    #Assets
    (r'^strategy/(?P<strategy_id>\d+)/add/asset/$', 'strategy.add_asset'),
    (r'^asset/edit/(?P<asset_id>\d+)/$',            'strategy.edit_asset'),

    #Charms
    (r'^strategy/(?P<strategy_id>\d+)/add/charm/$', 'strategy.add_charm'),
    (r'^charm/edit/(?P<charm_id>\d+)/$',            'strategy.edit_charm'),

    #Evaluated organisations
    (r'^strategy/(?P<strategy_id>\d+)/add/organisation/$',                        'strategy.add_evalorga'),
    (r'^strategy/(?P<strategy_id>\d+)/organisation/delete$',                      'strategy.delete_evalorga'),
    (r'^strategy/(?P<strategy_id>\d+)/organisation/(?P<orga_id>\d+)/evaluation$', 'strategy.orga_evaluation'),
    (r'^strategy/(?P<strategy_id>\d+)/organisation/(?P<orga_id>\d+)/synthesis$',  'strategy.orga_synthesis'),

    #Scores & category
    (r'^strategy/(?P<strategy_id>\d+)/set_asset_score$', 'strategy.set_asset_score'),
    (r'^strategy/(?P<strategy_id>\d+)/set_charm_score$', 'strategy.set_charm_score'),
    (r'^strategy/(?P<strategy_id>\d+)/set_segment_cat$', 'strategy.set_segment_category'),

    #Blocks
    (r'^blocks/assets_matrix/(?P<strategy_id>\d+)/(?P<orga_id>\d+)/$',        'strategy.reload_assets_matrix'),
    (r'^blocks/charms_matrix/(?P<strategy_id>\d+)/(?P<orga_id>\d+)/$',        'strategy.reload_charms_matrix'),
    (r'^blocks/assets_charms_matrix/(?P<strategy_id>\d+)/(?P<orga_id>\d+)/$', 'strategy.reload_assets_charms_matrix'),

    (r'^relsellby/edit/(?P<relation_id>\d+)$', 'sell_by_relation.edit'),
)
