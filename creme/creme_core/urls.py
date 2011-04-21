# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, include


entity_patterns = patterns('creme_core.views', #TODO: move delete* to entity.py
    (r'^delete/(?P<entity_id>\d+)$',           'generic.delete.delete_entity'),
    (r'^delete_related/(?P<ct_id>\d+)$',       'generic.delete.delete_related_to_entity'),
    (r'^get_repr/(?P<entity_id>\d+)$',         'entity.get_creme_entity_repr'),
    (r'^json$',                                'entity.get_creme_entity_as_json'),
    (r'^get_info_fields/(?P<ct_id>\d+)/json$', 'entity.get_info_fields'),
)

relation_patterns = patterns('creme_core.views.relation',
    (r'^add/(?P<subject_id>\d+)$',                                                                         'add_relations'),
    (r'^add/(?P<subject_id>\d+)/(?P<relation_type_id>[\w-]+)$',                                            'add_relations'),
    (r'^add_from_predicate/save$',                                                                         'add_relations_with_same_type'),
    (r'^add_to_entities/(?P<model_ct_id>\d+)/(?P<relations_types>([-_\w]+[,]*)+)/(?P<ids>([\d]+[,]*)+)$',  'add_relations_bulk'),#Beware of the order!!!
    (r'^add_to_entities/(?P<model_ct_id>\d+)/(?P<ids>([\d]+[,])+)$',                                       'add_relations_bulk'),
     #TODO: 'simple' param as GET param ??
    (r'^objects2link/rtype/(?P<rtype_id>[\w-]+)/entity/(?P<subject_id>\d+)/(?P<object_ct_id>\d+)$',        'objects_to_link_selection'),
    (r'^objects2link/rtype/(?P<rtype_id>[\w-]+)/entity/(?P<subject_id>\d+)/(?P<object_ct_id>\d+)/simple$', 'objects_to_link_selection', {'o2m': True}),
    (r'^delete$',                                                                                          'delete'),
    (r'^delete/similar$',                                                                                  'delete_similar'),
    (r'^entity/(?P<id>\d+)/json$',                                                                         'json_entity_get'),
    (r'^entity/(?P<id>\d+)/predicates/json$',                                                              'json_entity_predicates'),
    (r'^predicate/(?P<id>[\w-]+)/content_types/json$',                                                     'json_predicate_content_types'),
    (r'^get_predicates_choices_4_ct$',                                                                     'get_predicates_choices_4_ct'),
)

property_patterns = patterns('creme_core.views.creme_property',
#    (r'^add_to_entities$',        'add_to_entities'),
    (r'^add_to_entities/(?P<ct_id>\d+)/(?P<ids>([\d]+[,]*)+)$', 'add_properties_bulk'),
    (r'^get_types$',                                            'get_property_types_for_ct'),#TODO: Remove me?
    (r'^add/(?P<entity_id>\d+)$',                               'add_to_entity'),
)

blocks_patterns = patterns('creme_core.views.blocks',
    (r'^relations_block/(?P<entity_id>\d+)/$',                                'reload_relations_block'),
    (r'^relations_block/(?P<entity_id>\d+)/(?P<relation_type_ids>[\w,-]+)/$', 'reload_relations_block'),
    (r'^(?P<block_id>[\w-]+)/(?P<entity_id>\d+)/$',                           'reload_detailview'), #TODO: change url to detailview/(?P<block_id>[\w-]+)....
    (r'^home/(?P<block_id>[\w-]+)/$',                                         'reload_home'),
    (r'^portal/(?P<block_id>[\w-]+)/(?P<ct_ids>[\d,]+)/$',                    'reload_portal'),
    (r'^basic/(?P<block_id>[\w-]+)/$',                                        'reload_basic'), #most of blocks in creme_config for example
)

#TODO: remove (end views too)
filter_patterns = patterns('creme_core.views.list_view_filter',
    (r'^add/(?P<ct_id>\d+)$',                           'add'),
    (r'^edit/(?P<ct_id>\d+)/(?P<filter_id>\d+)$',       'edit'), #TODO: ct_id useful ????
    (r'^delete$',                                       'delete'),
    (r'^field_has_n_get_fk$',                           'field_has_n_get_fk'),
    (r'^register/(?P<filter_id>\d*)/(?P<ct_id>\d+)$',   'register_in_session'),
    (r'^get_session_filter_id/(?P<ct_id>\d+)$',         'get_session_filter_id'),
    (r'^select_entity_popup/(?P<content_type_id>\d+)$', 'get_list_view_popup_from_ct'),
    (r'^get_4_ct/(?P<content_type_id>\d+)$',            'get_filters_4_ct'),
)

entity_filter_patterns = patterns('creme_core.views.entity_filter',
    (r'^add/(?P<ct_id>\d+)$',                       'add'),
    (r'^edit/(?P<efilter_id>[\w-]+)$',              'edit'),
    (r'^delete$',                                   'delete'),
    (r'^rtype/(?P<rtype_id>[\w-]+)/content_types$', 'get_content_types'),
)

headerfilter_patterns = patterns('creme_core.views.header_filter',
    (r'^add/(?P<content_type_id>\d+)$',      'add'),
    (r'^delete',                             'delete'),
    (r'^edit/(?P<header_filter_id>[\w-]+)$', 'edit'),
    (r'^get_4_ct/(?P<content_type_id>\d+)$', 'get_hfs_4_ct'),
)

creme_core_patterns = patterns('creme_core.views',
    (r'^entity/',        include(entity_patterns)),
    (r'^relation/',      include(relation_patterns)),
    (r'^property/',      include(property_patterns)),
    (r'^blocks/reload/', include(blocks_patterns)),
    (r'^filter/',        include(filter_patterns)), #TODO: remove
    (r'^entity_filter/', include(entity_filter_patterns)),
    (r'^header_filter/', include(headerfilter_patterns)),

    #(r'^edit_js$', 'ajax.edit_js'), #TODO: commented on 5 january 2011 (delete view too)

    (r'^clean/$', 'clean.clean'),

    (r'^list_view/import_csv/(?P<ct_id>\d+)$', 'csv_import.csv_import'),
    (r'^list_view/dl_csv/(?P<ct_id>\d+)$',     'csv_export.dl_listview_as_csv'),

    # Popup helper
    (r'^nothing/$', 'nothing.get_nothing'), #TODO: to be deleted

    #Research
    (r'^search$', 'search.search'),

    (r'^quickforms/(?P<ct_id>\d+)/(?P<count>\d)$', 'quick_forms.add'),

    #Ajax helpers
    #TODO: move to entity.py ?? model.py ??
    (r'^get_fields$',          'ajax.get_fields'),
    (r'^get_custom_fields$',   'ajax.get_custom_fields'),
    (r'^get_function_fields$', 'ajax.get_function_fields'),
)

creme_core_patterns += patterns('creme_core.views.generic',
    (r'^lv_popup/(?P<ct_id>\d+)/(?P<o2m>0|1)$', 'listview.list_view_popup_from_widget'),
    (r'^delete_js$',                            'delete.delete_entities'), #TODO: change url (entity/delete_multi) ??
)

urlpatterns = patterns('creme_core.views',
    (r'^$','index.index'),

    (r'^download_file/(?P<location>.*)$', 'file_handling.download_file'), #TODO : To be replaced

    (r'^creme_core/', include(creme_core_patterns))
)
