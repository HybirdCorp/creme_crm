# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.persons import contact_model_is_custom

from creme.opportunities import opportunity_model_is_custom

from . import act_model_is_custom, pattern_model_is_custom, strategy_model_is_custom
from .views import portal, commercial_approach, market_segment, act, strategy


urlpatterns = [
    url(r'^$', portal.portal),

    url(r'^approach/add/(?P<entity_id>\d+)/$', commercial_approach.add),

    # Segments
    url(r'^market_segments$',                           market_segment.listview),
    url(r'^market_segment/add$',                        market_segment.add),
    url(r'^market_segment/edit/(?P<segment_id>\d+)$',   market_segment.edit),
    url(r'^market_segment/delete/(?P<segment_id>\d+)$', market_segment.delete),

    # Objectives & opportunities
    url(r'^act/(?P<act_id>\d+)/add/objective$',               act.add_objective),
    url(r'^act/(?P<act_id>\d+)/add/objectives_from_pattern$', act.add_objectives_from_pattern),
    url(r'^objective/(?P<objective_id>\d+)/edit$',            act.edit_objective),
    url(r'^objective/(?P<objective_id>\d+)/incr$',            act.incr_objective_counter),
    url(r'^objective/(?P<objective_id>\d+)/create_entity$',   act.create_objective_entity),

    # Pattern component
    url(r'^objective_pattern/(?P<objpattern_id>\d+)/add_component$',      act.add_pattern_component),
    url(r'^objective_pattern/component/(?P<component_id>\d+)/add_child',  act.add_child_pattern_component),
    url(r'^objective_pattern/component/(?P<component_id>\d+)/add_parent', act.add_parent_pattern_component),

    # Segments
    url(r'^strategy/(?P<strategy_id>\d+)/add/segment/$',                      strategy.add_segment),
    url(r'^strategy/(?P<strategy_id>\d+)/link/segment/$',                     strategy.link_segment),
    url(r'^strategy/(?P<strategy_id>\d+)/segment/edit/(?P<seginfo_id>\d+)/$', strategy.edit_segment),

    # Assets
    url(r'^strategy/(?P<strategy_id>\d+)/add/asset/$', strategy.add_asset),
    url(r'^asset/edit/(?P<asset_id>\d+)/$',            strategy.edit_asset),

    # Charms
    url(r'^strategy/(?P<strategy_id>\d+)/add/charm/$', strategy.add_charm),
    url(r'^charm/edit/(?P<charm_id>\d+)/$',            strategy.edit_charm),

    # Evaluated organisations
    url(r'^strategy/(?P<strategy_id>\d+)/add/organisation/$',                        strategy.add_evalorga),
    url(r'^strategy/(?P<strategy_id>\d+)/organisation/delete$',                      strategy.delete_evalorga),
    url(r'^strategy/(?P<strategy_id>\d+)/organisation/(?P<orga_id>\d+)/evaluation$', strategy.orga_evaluation),
    url(r'^strategy/(?P<strategy_id>\d+)/organisation/(?P<orga_id>\d+)/synthesis$',  strategy.orga_synthesis),

    # Scores & category
    url(r'^strategy/(?P<strategy_id>\d+)/set_asset_score$', strategy.set_asset_score),
    url(r'^strategy/(?P<strategy_id>\d+)/set_charm_score$', strategy.set_charm_score),
    url(r'^strategy/(?P<strategy_id>\d+)/set_segment_cat$', strategy.set_segment_category),

    # Blocks
    url(r'^blocks/assets_matrix/(?P<strategy_id>\d+)/(?P<orga_id>\d+)/$',        strategy.reload_assets_matrix),
    url(r'^blocks/charms_matrix/(?P<strategy_id>\d+)/(?P<orga_id>\d+)/$',        strategy.reload_charms_matrix),
    url(r'^blocks/assets_charms_matrix/(?P<strategy_id>\d+)/(?P<orga_id>\d+)/$', strategy.reload_assets_charms_matrix),
]

if not contact_model_is_custom():
    from .views import salesman

    urlpatterns += [
        url(r'^salesmen$',     salesman.listview, name='commercial__list_salesmen'),
        url(r'^salesman/add$', salesman.add,      name='commercial__create_salesman'),
    ]

if not act_model_is_custom():
    urlpatterns += [
        url(r'^acts$',                     act.listview,   name='commercial__list_acts'),
        url(r'^act/add$',                  act.add,        name='commercial__create_act'),
        url(r'^act/edit/(?P<act_id>\d+)$', act.edit,       name='commercial__edit_act'),
        url(r'^act/(?P<act_id>\d+)$',      act.detailview, name='commercial__view_act'),
    ]

if not opportunity_model_is_custom():
    urlpatterns += [
        url(r'^act/(?P<act_id>\d+)/add/opportunity$', act.add_opportunity, name='commercial__create_opportunity'),
    ]

if not pattern_model_is_custom():
    urlpatterns += [
        # TODO: a separated file for pattern ???
        url(r'^objective_patterns$',                            act.listview_objective_pattern,   name='commercial__list_patterns'),
        url(r'^objective_pattern/add$',                         act.add_objective_pattern,        name='commercial__create_pattern'),
        url(r'^objective_pattern/edit/(?P<objpattern_id>\d+)$', act.edit_objective_pattern,       name='commercial__edit_pattern'),
        url(r'^objective_pattern/(?P<objpattern_id>\d+)$',      act.objective_pattern_detailview, name='commercial__view_pattern'),
    ]

if not strategy_model_is_custom():
    urlpatterns += [
        url(r'^strategies$',                         strategy.listview,   name='commercial__list_strategies'),
        url(r'^strategy/add$',                       strategy.add,        name='commercial__create_strategy'),
        url(r'^strategy/edit/(?P<strategy_id>\d+)$', strategy.edit,       name='commercial__edit_strategy'),
        url(r'^strategy/(?P<strategy_id>\d+)$',      strategy.detailview, name='commercial__view_strategy'),
    ]
