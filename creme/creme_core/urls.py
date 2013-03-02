# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, include

entity_patterns = patterns('creme_core.views.entity',
    (r'^delete/multi$',                                                 'delete_entities'),
    (r'^delete/(?P<entity_id>\d+)$',                                    'delete_entity'),
    (r'^delete_related/(?P<ct_id>\d+)$',                                'delete_related_to_entity'),
    (r'^restore/(?P<entity_id>\d+)$',                                   'restore_entity'),
    (r'^trash$',                                                        'trash'),
    (r'^trash/empty$',                                                  'empty_trash'),
    (r'^get_repr/(?P<entities_ids>([\d]+[,]*)+)$',                      'get_creme_entities_repr'),
    (r'^json$',                                                         'get_creme_entity_as_json'),
    (r'^search_n_view$',                                                'search_and_view'),
    (r'^get_info_fields/(?P<ct_id>\d+)/json$',                          'get_info_fields'),
    (r'^bulk_update/(?P<ct_id>\d+)/$',                                  'bulk_update'),
    (r'^edit/(?P<ct_id>\d+)/(?P<id>\d+)/field/(?P<field_str>[\w-]+)$',  'edit_field'),
    (r'^get_fields$',                                                   'get_fields'),
    (r'^get_custom_fields$',                                            'get_custom_fields'),
    (r'^get_function_fields$',                                          'get_function_fields'),
    (r'^get_widget/(?P<ct_id>\d+)',                                     'get_widget'),
    (r'^clone',                                                         'clone'),
    (r'^merge/select_other/(?P<entity1_id>\d+)$',                       'select_entity_for_merge'),
    (r'^merge/(?P<entity1_id>\d+),(?P<entity2_id>\d+)$',                'merge'),
)

relation_patterns = patterns('creme_core.views.relation',
    (r'^add/(?P<subject_id>\d+)$',                                                                         'add_relations'),
    (r'^add/(?P<subject_id>\d+)/(?P<relation_type_id>[\w-]+)$',                                            'add_relations'),
    (r'^add_from_predicate/save$',                                                                         'add_relations_with_same_type'),
    (r'^add_to_entities/(?P<model_ct_id>\d+)/(?P<relations_types>([-_\w]+[,]*)+)/$',                       'add_relations_bulk'),#Beware of the order!!!
    (r'^add_to_entities/(?P<model_ct_id>\d+)/$',                                                           'add_relations_bulk'),
     #TODO: 'simple' param as GET param ??
    (r'^objects2link/rtype/(?P<rtype_id>[\w-]+)/entity/(?P<subject_id>\d+)/(?P<object_ct_id>\d+)$',        'objects_to_link_selection'),
    (r'^objects2link/rtype/(?P<rtype_id>[\w-]+)/entity/(?P<subject_id>\d+)/(?P<object_ct_id>\d+)/simple$', 'objects_to_link_selection', {'o2m': True}),
    (r'^delete$',                                                                                          'delete'),
    (r'^delete/similar$',                                                                                  'delete_similar'),
    (r'^delete/all',                                                                                       'delete_all'),
    (r'^entity/(?P<id>\d+)/json$',                                                                         'json_entity_get'),
    (r'^entity/(?P<id>\d+)/predicates/json$',                                                              'json_entity_predicates'),
    (r'^predicate/(?P<id>[\w-]+)/content_types/json$',                                                     'json_predicate_content_types'),
)

property_patterns = patterns('creme_core.views.creme_property',
    (r'^add_to_entities/(?P<ct_id>\d+)/$',  'add_properties_bulk'),
    #(r'^get_types$',                        'get_property_types_for_ct'), #Commented on 21 february 2012
    (r'^add/(?P<entity_id>\d+)$',           'add_to_entity'),
)

blocks_patterns = patterns('creme_core.views.blocks',
    (r'^relations_block/(?P<entity_id>\d+)/$',                                'reload_relations_block'),
    (r'^relations_block/(?P<entity_id>\d+)/(?P<relation_type_ids>[\w,-]+)/$', 'reload_relations_block'),
    (r'^(?P<block_id>[\w-]+)/(?P<entity_id>\d+)/$',                           'reload_detailview'), #TODO: change url to detailview/(?P<block_id>[\w-]+)....
    (r'^home/(?P<block_id>[\w-]+)/$',                                         'reload_home'),
    (r'^portal/(?P<block_id>[\w-]+)/(?P<ct_ids>[\d,]+)/$',                    'reload_portal'),
    (r'^basic/(?P<block_id>[\w-]+)/$',                                        'reload_basic'), #most of blocks in creme_config for example
    (r'^set_state/(?P<block_id>[\w-]+)/$',                                    'set_state'),#TODO: change url (reload not fit here...)
)

entity_filter_patterns = patterns('creme_core.views.entity_filter',
    (r'^add/(?P<ct_id>\d+)$',                       'add'),
    (r'^edit/(?P<efilter_id>[\w-]+)$',              'edit'),
    (r'^delete$',                                   'delete'),
    (r'^rtype/(?P<rtype_id>[\w-]+)/content_types$', 'get_content_types'),
    (r'^get_for_ctype/(?P<ct_id>\d+)$',             'get_for_ctype'),
)

headerfilter_patterns = patterns('creme_core.views.header_filter',
    (r'^add/(?P<content_type_id>\d+)$',      'add'),
    (r'^delete',                             'delete'),
    (r'^edit/(?P<header_filter_id>[\w-]+)$', 'edit'),
    (r'^get_for_ctype/(?P<ct_id>\d+)$',      'get_for_ctype'),
)

creme_core_patterns = patterns('creme_core.views',
    (r'^entity/',        include(entity_patterns)),
    (r'^relation/',      include(relation_patterns)),
    (r'^property/',      include(property_patterns)),
    (r'^blocks/reload/', include(blocks_patterns)),
    (r'^entity_filter/', include(entity_filter_patterns)),
    (r'^header_filter/', include(headerfilter_patterns)),

    (r'^clean/$', 'clean.clean'),

    (r'^list_view/import_csv/(?P<ct_id>\d+)$',    'csv_import.csv_import'),
    (r'^list_view/dl_csv/(?P<ct_id>\d+)$',        'csv_export.dl_listview_as_csv'),
    (r'^list_view/batch_process/(?P<ct_id>\d+)$', 'batch_process.batch_process'), #TODO: change url (remove 'list_view'...)??
    (r'^list_view/batch_process/(?P<ct_id>\d+)/get_ops/(?P<field>[\w]+)$', 'batch_process.get_ops'),

    #Research
    (r'^search$', 'search.search'),

    (r'^quickforms/(?P<ct_id>\d+)/(?P<count>\d)$', 'quick_forms.add'),
    (r'^quickforms/from_widget/(?P<ct_id>\d+)/add/(?P<count>\d)$', 'quick_forms.add_from_widget'),
)

creme_core_patterns += patterns('creme_core.views.generic',
    (r'^lv_popup/(?P<ct_id>\d+)/(?P<o2m>0|1)$', 'listview.list_view_popup_from_widget'), #TODO: change url (list_view/...)
)

urlpatterns = patterns('creme_core.views',
    (r'^$',        'index.home'),
    (r'^my_page$', 'index.my_page'),

    (r'^download_file/(?P<location>.*)$', 'file_handling.download_file'), #TODO : To be replaced

    (r'^creme_core/', include(creme_core_patterns)),

    (r'^test_js$', 'index.test_js'),
    (r'^test_widget/(?P<widget>\w+)$', 'index.test_widget'),
)
