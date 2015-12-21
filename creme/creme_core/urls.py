# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import url, include

from .views import (batch_process, blocks, creme_property, enumerable, entity,
        entity_filter, file_handling, header_filter, index, list_view_export,
        list_view_import, quick_forms, relation, search, testjs,
       )
from .views.generic import listview


entity_patterns = [
    url(r'^delete/multi$',                                                 entity.delete_entities),
    url(r'^delete/(?P<entity_id>\d+)$',                                    entity.delete_entity),
    url(r'^delete_related/(?P<ct_id>\d+)$',                                entity.delete_related_to_entity),
    url(r'^restore/(?P<entity_id>\d+)$',                                   entity.restore_entity),
    url(r'^trash$',                                                        entity.trash),
    url(r'^trash/empty$',                                                  entity.empty_trash),
    url(r'^get_repr/(?P<entities_ids>([\d]+[,]*)+)$',                      entity.get_creme_entities_repr),
    url(r'^get_sanitized_html/(?P<entity_id>\d+)/(?P<field_name>[\w-]+)$', entity.get_sanitized_html_field),
    url(r'^search_n_view$',                                                entity.search_and_view),
    url(r'^get_info_fields/(?P<ct_id>\d+)/json$',                          entity.get_info_fields),
    url(r'^edit/inner/(?P<ct_id>\d+)/(?P<id>\d+)/field/(?P<field_name>[\w-]+)$',            entity.inner_edit_field),
    url(r'^edit/bulk/(?P<ct_id>\d+)/(?P<id>\d+(?:,\d+)*)(/field/(?P<field_name>[\w-]+))?$', entity.bulk_edit_field),
    url(r'^clone',                                                         entity.clone),
    url(r'^merge/select_other/(?P<entity1_id>\d+)$',                       entity.select_entity_for_merge),
    url(r'^merge/(?P<entity1_id>\d+),(?P<entity2_id>\d+)$',                entity.merge),
]

relation_patterns = [
    url(r'^add/(?P<subject_id>\d+)$',                                                                         relation.add_relations),
    url(r'^add/(?P<subject_id>\d+)/(?P<rtype_id>[\w-]+)$',                                                    relation.add_relations),
    url(r'^add_from_predicate/save$',                                                                         relation.add_relations_with_same_type),
    url(r'^add_to_entities/(?P<model_ct_id>\d+)/(?P<relations_types>([-_\w]+[,]*)+)/$',                       relation.add_relations_bulk),#Beware of the order!!!
    url(r'^add_to_entities/(?P<model_ct_id>\d+)/$',                                                           relation.add_relations_bulk),
    # TODO: 'simple' param as GET param ??
    url(r'^objects2link/rtype/(?P<rtype_id>[\w-]+)/entity/(?P<subject_id>\d+)/(?P<object_ct_id>\d+)$',        relation.objects_to_link_selection),
    url(r'^objects2link/rtype/(?P<rtype_id>[\w-]+)/entity/(?P<subject_id>\d+)/(?P<object_ct_id>\d+)/simple$', relation.objects_to_link_selection, {'o2m': True}),
    url(r'^delete$',                                                                                          relation.delete),
    url(r'^delete/similar$',                                                                                  relation.delete_similar),
    url(r'^delete/all',                                                                                       relation.delete_all),
    url(r'^entity/(?P<entity_id>\d+)/json$',                                                                  relation.json_entity_get),
    url(r'^entity/(?P<entity_id>\d+)/rtypes/json$',                                                           relation.json_entity_rtypes),
    url(r'^type/(?P<rtype_id>[\w-]+)/content_types/json$',                                                    relation.json_rtype_ctypes),
]

property_patterns = [
    url(r'^add_to_entities/(?P<ct_id>\d+)/$',                               creme_property.add_properties_bulk),
    url(r'^add/(?P<entity_id>\d+)$',                                        creme_property.add_to_entity),
    url(r'^delete_from_type$',                                              creme_property.delete_from_type),
    url(r'^type/add$',                                                      creme_property.add_type),
    url(r'^type/(?P<ptype_id>[\w-]+)$',                                     creme_property.type_detailview),
    url(r'^type/(?P<ptype_id>[\w-]+)/edit$',                                creme_property.edit_type),
    url(r'^type/(?P<ptype_id>[\w-]+)/delete$',                              creme_property.delete_type),
    url(r'^type/(?P<ptype_id>[\w-]+)/reload_block/(?P<block_id>[\w\-]+)/$', creme_property.reload_block),
]

blocks_patterns = [
    url(r'^relations_block/(?P<entity_id>\d+)/$',                                  blocks.reload_relations_block),
    url(r'^relations_block/(?P<entity_id>\d+)/(?P<relation_type_ids>[\w,-]+)/$',   blocks.reload_relations_block),
    url(r'^(?P<block_id>[\w\-\|]+)/(?P<entity_id>\d+)/$',                          blocks.reload_detailview),  # TODO: change url to detailview/(?P<block_id>[\w-]+)....
    url(r'^home/(?P<block_id>[\w\-\|]+)/$',                                        blocks.reload_home),
    url(r'^portal/(?P<block_id>[\w\-\|]+)/(?P<ct_ids>[\d,]+)/$',                   blocks.reload_portal),
    url(r'^basic/(?P<block_id>[\w\-\|]+)/$',                                       blocks.reload_basic),  # Most of blocks in creme_config for example
    url(r'^set_state/(?P<block_id>[\w\-\|]+)/$',                                   blocks.set_state),  # TODO: change url (reload not fit here...)
]

entity_filter_patterns = [
    url(r'^add/(?P<ct_id>\d+)$',                       entity_filter.add),
    url(r'^edit/(?P<efilter_id>.+)$',                  entity_filter.edit),
    url(r'^delete$',                                   entity_filter.delete),
    url(r'^rtype/(?P<rtype_id>[\w-]+)/content_types$', entity_filter.get_content_types),
    url(r'^get_for_ctype/(?P<ct_id>\d+)$',             entity_filter.get_for_ctype),
    url(r'^get_for_ctype/(?P<ct_id>\d+)/all$',         entity_filter.get_for_ctype, {'include_all': True}),
]

headerfilter_patterns = [
    url(r'^add/(?P<content_type_id>\d+)$',      header_filter.add),
    url(r'^delete',                             header_filter.delete),
    url(r'^edit/(?P<header_filter_id>[\w-]+)$', header_filter.edit),
    url(r'^get_for_ctype/(?P<ct_id>\d+)$',      header_filter.get_for_ctype),
]

enumerable_patterns = [
    url(r'^(?P<ct_id>\d+)/json$',          enumerable.json_list_enumerable),
    url(r'^custom/(?P<cf_id>\d+)/json$',   enumerable.json_list_enumerable_custom),
    url(r'^userfilter/json$',              enumerable.json_list_userfilter),
]

creme_core_patterns = [
    url(r'^entity/',        include(entity_patterns)),
    url(r'^relation/',      include(relation_patterns)),
    url(r'^property/',      include(property_patterns)),
    url(r'^blocks/reload/', include(blocks_patterns)),
    url(r'^entity_filter/', include(entity_filter_patterns)),
    url(r'^header_filter/', include(headerfilter_patterns)),
    url(r'^enumerable/',    include(enumerable_patterns)),

    url(r'^list_view/popup/(?P<ct_id>\d+)/(?P<o2m>0|1)$',                     listview.list_view_popup_from_widget),
    url(r'^list_view/import/(?P<ct_id>\d+)$',                                 list_view_import.import_listview),
    url(r'^list_view/download/(?P<ct_id>\d+)/(?P<doc_type>[\w-]+)$',          list_view_export.dl_listview),
    url(r'^list_view/download_header/(?P<ct_id>\d+)/(?P<doc_type>[\w-]+)$',   list_view_export.dl_listview_header),
    url(r'^list_view/batch_process/(?P<ct_id>\d+)$',                          batch_process.batch_process), #TODO: change url (remove 'list_view'...)??
    url(r'^list_view/batch_process/(?P<ct_id>\d+)/get_ops/(?P<field>[\w]+)$', batch_process.get_ops),

    # Search
    url(r'^search$',                                                       search.search),
    url(r'^search/reload_block/(?P<block_id>[\w\-\|]+)/(?P<research>.+)$', search.reload_block),

    url(r'^quickforms/(?P<ct_id>\d+)/(?P<count>\d)$',                 quick_forms.add),
    url(r'^quickforms/from_widget/(?P<ct_id>\d+)/add/(?P<count>\d)$', quick_forms.add_from_widget),
]

urlpatterns = [
    url(r'^$',        index.home),
    url(r'^my_page$', index.my_page),

    url(r'^download_file/(?P<location>.*)$', file_handling.download_file), # TODO : To be replaced

    url(r'^creme_core/', include(creme_core_patterns)),

    url(r'^test_http_response[/]?$',           testjs.test_http_response),
    url(r'^test_js[/]?$',                      testjs.test_js),
    url(r'^test_widget(/|/(?P<widget>\w+))?$', testjs.test_widget),
]

if settings.TESTS_ON:
    from .tests import fake_views

    urlpatterns += [
        url(r'^tests/documents$',                  fake_views.document_listview),
        #(r'^tests/document/add$',                  'document_add'),
        #(r'^tests/document/edit/(?P<doc_id>\d+)$', 'document_edit'),
        #(r'^tests/document/(?P<doc_id>\d+)$',      'document_detailview'),

        url(r'^tests/images$',                     fake_views.image_listview),
        #(r'^tests/image/add$',                    'image_add'),
        #(r'^tests/image/edit/(?P<image_id>\d+)$', 'image_edit'),
        url(r'^tests/image/(?P<image_id>\d+)$',    fake_views.image_detailview),

        url(r'^tests/contacts$',                         fake_views.contact_listview),
        url(r'^tests/contact/add$',                      fake_views.contact_add),
        url(r'^tests/contact/edit/(?P<contact_id>\d+)$', fake_views.contact_edit),
        url(r'^tests/contact/(?P<contact_id>\d+)$',      fake_views.contact_detailview),

        url(r'^tests/organisations$',                      fake_views.organisation_listview),
        url(r'^tests/organisation/add$',                   fake_views.organisation_add),
        url(r'^tests/organisation/edit/(?P<orga_id>\d+)$', fake_views.organisation_edit),
        url(r'^tests/organisation/(?P<orga_id>\d+)$',      fake_views.organisation_detailview),

        url(r'^tests/address/add/(?P<entity_id>\d+)$',     fake_views.address_add),
        url(r'^tests/address/edit/(?P<address_id>\d+)',    fake_views.address_edit),

        url(r'^tests/activities$',                  fake_views.activity_listview),
        #(r'^tests/activity/add$',                  'activity_add'),
        #(r'^tests/activity/edit/(?P<act_id>\d+)$', 'activity_edit'),
        #(r'^tests/activity/(?P<act_id>\d+)$',      'activity_detailview'),

        url(r'^tests/e_campaigns$',                        fake_views.campaign_listview),
        #(r'^tests/e_campaign/add$',                       'campaign_add'),
        #(r'^tests/e_campaign/edit/(?P<campaign_id>\d+)$', 'campaign_edit'),
        #(r'^tests/e_campaign/(?P<campaign_id>\d+)$',      'campaign_detailview'),

        url(r'^tests/invoices$',                        fake_views.invoice_listview),
        #(r'^tests/invoice/add$',                       'invoice_add'),
        #(r'^tests/invoice/edit/(?P<invoice_id>\d+)$',  'invoice_edit'),
        url(r'^tests/invoice/(?P<invoice_id>\d+)$',     fake_views.invoice_detailview),

        url(r'^tests/invoice_lines$', fake_views.invoice_lines_listview),
    ]
