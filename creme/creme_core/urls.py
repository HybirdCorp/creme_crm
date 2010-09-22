# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, include


creme_core_patterns = patterns('creme_core.views',
    (r'^relation/add/(?P<subject_id>\d+)$',                                                                              'relation.add_relations'),
    (r'^relation/add/(?P<subject_id>\d+)/(?P<relation_type_id>[\w-]+)$',                                                 'relation.add_relations'),
    (r'^relation/add/from/predicate/(?P<predicate_id>[\w-]+)/entity/(?P<subject_id>\d+)/(?P<object_ct_id>\d+)$',         'relation.add_relation_from_predicate_n_entity'),
    (r'^relation/add/from/predicate/(?P<predicate_id>[\w-]+)/entity/(?P<subject_id>\d+)/(?P<object_ct_id>\d+)/simple$',  'relation.add_relation_from_predicate_n_entity', {'o2m':True}),
    (r'^relation/add_from_predicate/save$',                                                                              'relation.handle_relation_from_predicate_n_entity'),
    (r'^relation/delete$',                                                                                               'relation.delete'),
    (r'^relation/delete/similar$',                                                                                       'relation.delete_similar'),
    # TODO (refs 293) unused tool. remove it !
    #(r'^relation/entity/select/json$',                                                                                   'relation.json_entity_select'),
    (r'^relation/entity/(?P<id>\d+)/json$',                                                                              'relation.json_entity_get'),
    (r'^relation/entity/(?P<id>\d+)/predicates/json$',                                                                   'relation.json_entity_predicates'),
    (r'^relation/predicate/(?P<id>[\w-]+)/content_types/json$',                                                          'relation.json_predicate_content_types'),
    (r'^relation/add_to_entities/(?P<model_ct_id>\d+)/(?P<ids>([\d]+[,])+)$',                                            'relation.add_relations_bulk'),
    (r'^relation/get_predicates_choices_4_ct$',                                                                          'relation.get_predicates_choices_4_ct'),

    (r'^blocks/reload/relations_block/(?P<entity_id>\d+)/$',                                'blocks.reload_relations_block'),
    (r'^blocks/reload/relations_block/(?P<entity_id>\d+)/(?P<relation_type_ids>[\w,-]+)/$', 'blocks.reload_relations_block'),
    (r'^blocks/reload/(?P<block_id>[\w-]+)/(?P<entity_id>\d+)/$',                           'blocks.reload_detailview'), #TODO: change url to blocks/reload/detailview/....
    (r'^blocks/reload/home/(?P<block_id>[\w-]+)/$',                                         'blocks.reload_home'),
    (r'^blocks/reload/portal/(?P<block_id>[\w-]+)/(?P<ct_ids>[\d,]+)/$',                    'blocks.reload_portal'),
    (r'^blocks/reload/basic/(?P<block_id>[\w-]+)/$',                                        'blocks.reload_basic'), #most of blocks in creme_config for example

    (r'^filter/add/(?P<ct_id>\d+)$',                           'list_view_filter.add'),
    (r'^filter/edit/(?P<ct_id>\d+)/(?P<filter_id>\d+)$',       'list_view_filter.edit'), #ct_id useful ????
    (r'^filter/delete$',                                       'list_view_filter.delete'),
    (r'^filter/getfieldfk/$',                                  'ajax.fieldHasNGetFK'),   #change url ???? move to list_view_filter.py ??
    (r'^filter/register/(?P<filter_id>\d*)/(?P<ct_id>\d+)$',   'list_view_filter.register_in_session'),
    (r'^filter/get_session_filter_id/(?P<ct_id>\d+)$',         'list_view_filter.get_session_filter_id'),
    (r'^filter/select_entity_popup/(?P<content_type_id>\d+)$', 'list_view_filter.get_list_view_popup_from_ct'),
    (r'^filter/get_4_ct/(?P<content_type_id>\d+)$',            'list_view_filter.get_filters_4_ct'),

    (r'^edit_js$', 'ajax.edit_js'),

    (r'^clean/$', 'clean.clean'),

    (r'^property/add_to_entities$',                             'creme_property.add_to_entities'),
    (r'^property/get_types$',                                   'creme_property.get_property_types_for_ct'),
    (r'^property/add/$',                                        'creme_property.add_to_creme_entity'),
    (r'^property/list_for_entity_ct/(?P<creme_entity_id>\d+)$', 'creme_property.list_for_entity_ct'),
    (r'^property/delete$',                                      'creme_property.delete'),

    (r'^header_filter/add/(?P<content_type_id>\d+)$',      'header_filter.add'),
    (r'^header_filter/delete',                             'header_filter.delete'),
    (r'^header_filter/edit/(?P<header_filter_id>[\w-]+)$', 'header_filter.edit'),
    (r'^header_filter/get_4_ct/(?P<content_type_id>\d+)$', 'header_filter.get_hfs_4_ct'),

    #Entities representations
    (r'^entity/get_repr/$',                         'entity.get_entity_repr'),
    (r'^entity/get_repr/(?P<creme_entity_id>\d+)$', 'entity.get_creme_entity_repr'),
    (r'^entity/render$',                            'entity.render_entity'),
    (r'^entity/json$',                              'entity.get_creme_entity_as_json'),

    (r'^list_view/import_csv/(?P<ct_id>\d+)$', 'csv_import.csv_import'),
    (r'^list_view/dl_csv/(?P<ct_id>\d+)$',     'csv_export.dl_listview_as_csv'),

    # Popup helper
    (r'^nothing/$', 'nothing.get_nothing'),

    #Research
    (r'^search$', 'search.search'),

    (r'^quickforms/(?P<ct_id>\d+)/(?P<count>\d)$', 'quick_forms.add'),

    #Ajax helpers
    #TODO: move to entity.py ??
    (r'^get_fields$',         'ajax.get_fields'),
    (r'^get_custom_fields$',  'ajax.get_custom_fields'),
    (r'^get_function_fields', 'ajax.get_function_fields'),

)

creme_core_patterns += patterns('creme_core.views.generic',
    (r'^lv_popup/(?P<ct_id>\d+)/(?P<o2m>0|1)$', 'listview.list_view_popup_from_widget'),
    (r'^delete_js$',                            'delete.delete_entities_js_post'),
)

urlpatterns = patterns('creme_core.views',
    (r'^$','index.index'),

    (r'^download_file/(?P<location>.*)$', 'file_handling.download_file'), #TODO : To be replaced

    (r'^creme_core/', include(creme_core_patterns))
)