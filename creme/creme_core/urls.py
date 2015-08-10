# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import patterns, include


entity_patterns = patterns('creme.creme_core.views.entity',
    (r'^delete/multi$',                                                 'delete_entities'),
    (r'^delete/(?P<entity_id>\d+)$',                                    'delete_entity'),
    (r'^delete_related/(?P<ct_id>\d+)$',                                'delete_related_to_entity'),
    (r'^restore/(?P<entity_id>\d+)$',                                   'restore_entity'),
    (r'^trash$',                                                        'trash'),
    (r'^trash/empty$',                                                  'empty_trash'),
    (r'^get_repr/(?P<entities_ids>([\d]+[,]*)+)$',                      'get_creme_entities_repr'),
    (r'^search_n_view$',                                                'search_and_view'),
    (r'^get_info_fields/(?P<ct_id>\d+)/json$',                          'get_info_fields'),
    (r'^edit/inner/(?P<ct_id>\d+)/(?P<id>\d+)/field/(?P<field_name>[\w-]+)$',            'inner_edit_field'),
    (r'^edit/bulk/(?P<ct_id>\d+)/(?P<id>\d+(?:,\d+)*)(/field/(?P<field_name>[\w-]+))?$', 'bulk_edit_field'),
    (r'^clone',                                                         'clone'),
    (r'^merge/select_other/(?P<entity1_id>\d+)$',                       'select_entity_for_merge'),
    (r'^merge/(?P<entity1_id>\d+),(?P<entity2_id>\d+)$',                'merge'),
)

relation_patterns = patterns('creme.creme_core.views.relation',
    (r'^add/(?P<subject_id>\d+)$',                                                                         'add_relations'),
    (r'^add/(?P<subject_id>\d+)/(?P<rtype_id>[\w-]+)$',                                                    'add_relations'),
    (r'^add_from_predicate/save$',                                                                         'add_relations_with_same_type'),
    (r'^add_to_entities/(?P<model_ct_id>\d+)/(?P<relations_types>([-_\w]+[,]*)+)/$',                       'add_relations_bulk'),#Beware of the order!!!
    (r'^add_to_entities/(?P<model_ct_id>\d+)/$',                                                           'add_relations_bulk'),
     #TODO: 'simple' param as GET param ??
    (r'^objects2link/rtype/(?P<rtype_id>[\w-]+)/entity/(?P<subject_id>\d+)/(?P<object_ct_id>\d+)$',        'objects_to_link_selection'),
    (r'^objects2link/rtype/(?P<rtype_id>[\w-]+)/entity/(?P<subject_id>\d+)/(?P<object_ct_id>\d+)/simple$', 'objects_to_link_selection', {'o2m': True}),
    (r'^delete$',                                                                                          'delete'),
    (r'^delete/similar$',                                                                                  'delete_similar'),
    (r'^delete/all',                                                                                       'delete_all'),
    (r'^entity/(?P<entity_id>\d+)/json$',                                                                  'json_entity_get'),
    (r'^entity/(?P<entity_id>\d+)/rtypes/json$',                                                           'json_entity_rtypes'),
    (r'^type/(?P<rtype_id>[\w-]+)/content_types/json$',                                                    'json_rtype_ctypes'),
)

property_patterns = patterns('creme.creme_core.views.creme_property',
    (r'^add_to_entities/(?P<ct_id>\d+)/$',                               'add_properties_bulk'),
    (r'^add/(?P<entity_id>\d+)$',                                        'add_to_entity'),
    (r'^delete_from_type$',                                              'delete_from_type'),
    (r'^type/add$',                                                      'add_type'),
    (r'^type/(?P<ptype_id>[\w-]+)$',                                     'type_detailview'),
    (r'^type/(?P<ptype_id>[\w-]+)/edit$',                                'edit_type'),
    (r'^type/(?P<ptype_id>[\w-]+)/delete$',                              'delete_type'),
    (r'^type/(?P<ptype_id>[\w-]+)/reload_block/(?P<block_id>[\w\-]+)/$', 'reload_block'),
)

blocks_patterns = patterns('creme.creme_core.views.blocks',
    (r'^relations_block/(?P<entity_id>\d+)/$',                                  'reload_relations_block'),
    (r'^relations_block/(?P<entity_id>\d+)/(?P<relation_type_ids>[\w,-]+)/$',   'reload_relations_block'),
    (r'^(?P<block_id>[\w\-\|]+)/(?P<entity_id>\d+)/$',                          'reload_detailview'), #TODO: change url to detailview/(?P<block_id>[\w-]+)....
    (r'^home/(?P<block_id>[\w\-\|]+)/$',                                        'reload_home'),
    (r'^portal/(?P<block_id>[\w\-\|]+)/(?P<ct_ids>[\d,]+)/$',                   'reload_portal'),
    (r'^basic/(?P<block_id>[\w\-\|]+)/$',                                       'reload_basic'), #most of blocks in creme_config for example
    (r'^set_state/(?P<block_id>[\w\-\|]+)/$',                                   'set_state'),#TODO: change url (reload not fit here...)
)

entity_filter_patterns = patterns('creme.creme_core.views.entity_filter',
    (r'^add/(?P<ct_id>\d+)$',                       'add'),
    #(r'^edit/(?P<efilter_id>[\w-]+)$',              'edit'),
    (r'^edit/(?P<efilter_id>.+)$',                  'edit'),
    (r'^delete$',                                   'delete'),
    (r'^rtype/(?P<rtype_id>[\w-]+)/content_types$', 'get_content_types'),
    (r'^get_for_ctype/(?P<ct_id>\d+)$',             'get_for_ctype'),
    (r'^get_for_ctype/(?P<ct_id>\d+)/all$',         'get_for_ctype', {'include_all': True}),
)

headerfilter_patterns = patterns('creme.creme_core.views.header_filter',
    (r'^add/(?P<content_type_id>\d+)$',      'add'),
    (r'^delete',                             'delete'),
    (r'^edit/(?P<header_filter_id>[\w-]+)$', 'edit'),
    (r'^get_for_ctype/(?P<ct_id>\d+)$',      'get_for_ctype'),
)

enumerable_patterns = patterns('creme.creme_core.views.enumerable',
    (r'^(?P<ct_id>\d+)/json$',          'json_list_enumerable'),
    (r'^custom/(?P<cf_id>\d+)/json$',   'json_list_enumerable_custom'),
    (r'^userfilter/json$',              'json_list_userfilter'),
)

creme_core_patterns = patterns('creme.creme_core.views',
    (r'^entity/',        include(entity_patterns)),
    (r'^relation/',      include(relation_patterns)),
    (r'^property/',      include(property_patterns)),
    (r'^blocks/reload/', include(blocks_patterns)),
    (r'^entity_filter/', include(entity_filter_patterns)),
    (r'^header_filter/', include(headerfilter_patterns)),
    (r'^enumerable/',    include(enumerable_patterns)),

    (r'^list_view/popup/(?P<ct_id>\d+)/(?P<o2m>0|1)$',                     'generic.listview.list_view_popup_from_widget'),
    (r'^list_view/import/(?P<ct_id>\d+)$',                                 'list_view_import.import_listview'),
    (r'^list_view/download/(?P<ct_id>\d+)/(?P<doc_type>[\w-]+)$',          'list_view_export.dl_listview'),
    (r'^list_view/download_header/(?P<ct_id>\d+)/(?P<doc_type>[\w-]+)$',   'list_view_export.dl_listview_header'),
    (r'^list_view/batch_process/(?P<ct_id>\d+)$',                          'batch_process.batch_process'), #TODO: change url (remove 'list_view'...)??
    (r'^list_view/batch_process/(?P<ct_id>\d+)/get_ops/(?P<field>[\w]+)$', 'batch_process.get_ops'),

    #Research
    (r'^search$',                                                       'search.search'),
    (r'^search/reload_block/(?P<block_id>[\w\-\|]+)/(?P<research>.+)$', 'search.reload_block'),

    (r'^quickforms/(?P<ct_id>\d+)/(?P<count>\d)$', 'quick_forms.add'),
    (r'^quickforms/from_widget/(?P<ct_id>\d+)/add/(?P<count>\d)$', 'quick_forms.add_from_widget'),
)

#creme_core_patterns += patterns('creme.creme_core.views.generic',
    #(r'^lv_popup/(?P<ct_id>\d+)/(?P<o2m>0|1)$', 'listview.list_view_popup_from_widget'),
#)

urlpatterns = patterns('creme.creme_core.views',
    (r'^$',        'index.home'),
    (r'^my_page$', 'index.my_page'),

    (r'^download_file/(?P<location>.*)$', 'file_handling.download_file'), #TODO : To be replaced

    (r'^creme_core/', include(creme_core_patterns)),

    (r'^test_http_response[/]?$',           'testjs.test_http_response'),
    (r'^test_js[/]?$',                      'testjs.test_js'),
    (r'^test_widget(/|/(?P<widget>\w+))?$', 'testjs.test_widget'),
)

if settings.TESTS_ON:
    urlpatterns += patterns('creme.creme_core.tests.fake_views',
        (r'^tests/images$',                        'image_listview'),
        #(r'^tests/image/add$',                    'image_add'),
        #(r'^tests/image/edit/(?P<image_id>\d+)$', 'image_edit'),
        #(r'^tests/image/(?P<image_id>\d+)$',      'image_detailview'),

        (r'^tests/contacts$',                           'contact_listview'),
        (r'^tests/contact/add$',                        'contact_add'),
        (r'^tests/contact/edit/(?P<contact_id>\d+)$',   'contact_edit'),
        (r'^tests/contact/(?P<contact_id>\d+)$',        'contact_detailview'),

        (r'^tests/organisations$',                      'organisation_listview'),
        (r'^tests/organisation/add$',                   'organisation_add'),
        (r'^tests/organisation/edit/(?P<orga_id>\d+)$', 'organisation_edit'),
        (r'^tests/organisation/(?P<orga_id>\d+)$',      'organisation_detailview'),

        (r'^tests/address/add/(?P<entity_id>\d+)$',     'address_add'),
        (r'^tests/address/edit/(?P<address_id>\d+)',    'address_edit'),

        (r'^tests/activities$',                    'activity_listview'),
        #(r'^tests/activity/add$',                  'activity_add'),
        #(r'^tests/activity/edit/(?P<act_id>\d+)$', 'activity_edit'),
        #(r'^tests/activity/(?P<act_id>\d+)$',      'activity_detailview'),

        (r'^tests/e_campaigns$',                          'campaign_listview'),
        #(r'^tests/e_campaign/add$',                       'campaign_add'),
        #(r'^tests/e_campaign/edit/(?P<campaign_id>\d+)$', 'campaign_edit'),
        #(r'^tests/e_campaign/(?P<campaign_id>\d+)$',      'campaign_detailview'),

        (r'^tests/invoices$',                          'invoice_listview'),
        #(r'^tests/invoice/add$',                       'invoice_add'),
        #(r'^tests/invoice/edit/(?P<invoice_id>\d+)$',  'invoice_edit'),
        (r'^tests/invoice/(?P<invoice_id>\d+)$',       'invoice_detailview'),

        (r'^tests/invoice_lines$', 'invoice_lines_listview'),
    )
