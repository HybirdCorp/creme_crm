# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import url, include

from .views import (batch_process, blocks, bricks, creme_property, enumerable, entity,
        entity_filter, file_handling, header_filter, index, job, list_view_export,
        mass_import, quick_forms, relation, search, testjs,
       )
from .views.generic import listview


entity_patterns = [
    url(r'^delete/multi[/]?$',                  entity.delete_entities,          name='creme_core__delete_entities'),
    url(r'^delete/(?P<entity_id>\d+)[/]?$',     entity.delete_entity,            name='creme_core__delete_entity'),
    url(r'^delete_related/(?P<ct_id>\d+)[/]?$', entity.delete_related_to_entity, name='creme_core__delete_related_to_entity'),
    url(r'^restore/(?P<entity_id>\d+)[/]?$',    entity.restore_entity,           name='creme_core__restore_entity'),
    url(r'^trash[/]?$',                         entity.trash,                    name='creme_core__trash'),
    url(r'^trash/empty[/]?$',                   entity.empty_trash,              name='creme_core__empty_trash'),

    # TODO: add a view 'creme_core__entities_as_json' (with same features as 'creme_core__entity_as_json', then remove this one
    # TODO: IDs as GET arguments
    url(r'^get_repr/(?P<entities_ids>([\d]+[,]*)+)[/]?$',                            entity.get_creme_entities_repr,  name='creme_core__entities_summaries'),
    url(r'^get_sanitized_html/(?P<entity_id>\d+)/(?P<field_name>[\w-]+)[/]?$',       entity.get_sanitized_html_field, name='creme_core__sanitized_html_field'),
    url(r'^search_n_view[/]?$',                                                      entity.search_and_view,          name='creme_core__search_n_view_entities'),
    url(r'^get_info_fields/(?P<ct_id>\d+)/json[/]?$',                                entity.get_info_fields,          name='creme_core__entity_info_fields'),

    url(r'^edit/inner/(?P<ct_id>\d+)/(?P<id>\d+)/field/(?P<field_name>[\w-]+)[/]?$', entity.inner_edit_field,  name='creme_core__inner_edition'),
    url(r'^edit/bulk/(?P<ct_id>\d+)/(?P<id>\d+(?:,\d+)*)[/]?$',                              entity.bulk_edit_field, name='creme_core__bulk_edit_field_legacy'),  # DEPRECATED # TODO: remove in 1.8
    url(r'^edit/bulk/(?P<ct_id>\d+)/(?P<id>\d+(?:,\d+)*)/field/(?P<field_name>[\w-]+)[/]?$', entity.bulk_edit_field, name='creme_core__bulk_edit_field_legacy'),  # DEPRECATED # TODO: remove in 1.8
    url(r'^update/bulk/(?P<ct_id>\d+)[/]?$',                                         entity.bulk_update_field, name='creme_core__bulk_update'),
    url(r'^update/bulk/(?P<ct_id>\d+)/field/(?P<field_name>[\w-]+)[/]?$',            entity.bulk_update_field, name='creme_core__bulk_update'),

    url(r'^clone[/]*', entity.clone, name='creme_core__clone_entity'),

    url(r'^merge/select_other[/]?$',                            entity.select_entity_for_merge,  name='creme_core__select_entity_for_merge'),
    url(r'^merge/select_other/(?P<entity1_id>\d+)[/]?$',        entity.select_entity_for_merge,  name='creme_core__select_entity_for_merge'),  # DEPRECATED
    url(r'^merge[/]?$',                                         entity.merge,                    name='creme_core__merge_entities'),
    url(r'^merge/(?P<entity1_id>\d+),(?P<entity2_id>\d+)[/]?$', entity.merge,                    name='creme_core__merge_entities'),  # DEPRECATED
]

relation_patterns = [
    url(r'^add/(?P<subject_id>\d+)[/]?$',                      relation.add_relations,                name='creme_core__create_relations'),
    url(r'^add/(?P<subject_id>\d+)/(?P<rtype_id>[\w-]+)[/]?$', relation.add_relations,                name='creme_core__create_relations'),
    url(r'^add_from_predicate/save[/]?$',                      relation.add_relations_with_same_type, name='creme_core__save_relations'),

    # Beware of the order!!!
    url(r'^add_to_entities/(?P<model_ct_id>\d+)/(?P<relations_types>([-_\w]+[,]*)+)[/]?$', relation.add_relations_bulk, name='creme_core__create_relations_bulk'),  # DEPRECATED
    url(r'^add_to_entities/(?P<model_ct_id>\d+)[/]?$',                                     relation.add_relations_bulk, name='creme_core__create_relations_bulk'),

    url(r'^objects2link[/]?$', relation.select_relations_objects, name='creme_core__select_entities_to_link'),
    url(r'^objects2link/rtype/(?P<rtype_id>[\w-]+)/entity/(?P<subject_id>\d+)/(?P<object_ct_id>\d+)[/]?$',
        relation.objects_to_link_selection, name='creme_core__select_entities_to_link',
       ),  # DEPRECATED
    url(r'^objects2link/rtype/(?P<rtype_id>[\w-]+)/entity/(?P<subject_id>\d+)/(?P<object_ct_id>\d+)/simple[/]?$',
        relation.objects_to_link_selection, {'o2m': True}, name='creme_core__select_entities_to_link',
       ),  # DEPRECATED

    url(r'^delete[/]?$',         relation.delete,         name='creme_core__delete_relation'),
    url(r'^delete/similar[/]?$', relation.delete_similar, name='creme_core__delete_similar_relations'),
    url(r'^delete/all[/]*',      relation.delete_all,     name='creme_core__delete_all_relations'),

    url(r'^entity/(?P<entity_id>\d+)/json[/]?$',               relation.json_entity_get,    name='creme_core__entity_as_json'),  # TODO: move to entity_patterns ?
    url(r'^entity/(?P<entity_id>\d+)/rtypes/json[/]?$',        relation.json_entity_rtypes, name='creme_core__rtypes_compatible_with_entity'),
    url(r'^type/(?P<rtype_id>[\w-]+)/content_types/json[/]?$', relation.json_rtype_ctypes,  name='creme_core__ctypes_compatible_with_rtype'),
]

property_patterns = [
    url(r'^add_to_entities/(?P<ct_id>\d+)[/]?$', creme_property.add_properties_bulk, name='creme_core__add_properties_bulk'),
    url(r'^add/(?P<entity_id>\d+)[/]?$',         creme_property.add_to_entity,       name='creme_core__add_properties'),
    url(r'^delete_from_type[/]?$',               creme_property.delete_from_type,    name='creme_core__remove_property'),

    # Property type
    url(r'^type/add[/]?$',                                creme_property.add_type,        name='creme_core__create_ptype'),
    url(r'^type/(?P<ptype_id>[\w-]+)[/]?$',               creme_property.type_detailview, name='creme_core__ptype'),
    url(r'^type/(?P<ptype_id>[\w-]+)/edit[/]?$',          creme_property.edit_type,       name='creme_core__edit_ptype'),
    url(r'^type/(?P<ptype_id>[\w-]+)/delete[/]?$',        creme_property.delete_type,     name='creme_core__delete_ptype'),
    url(r'^type/(?P<ptype_id>[\w-]+)/reload_bricks[/]?$', creme_property.reload_bricks,   name='creme_core__reload_ptype_bricks'),
    url(r'^type/(?P<ptype_id>[\w-]+)/reload_block/(?P<block_id>[\w\-]+)[/]?$',
        creme_property.reload_block,
        name='creme_core__reload_ptype_blocks',
       ),  # DEPRECATED
]

# DEPRECATED
blocks_patterns = [
    url(r'^relations_block/(?P<entity_id>\d+)[/]?$',                                blocks.reload_relations_block, name='creme_core__reload_relations_block'),
    url(r'^relations_block/(?P<entity_id>\d+)/(?P<relation_type_ids>[\w,-]+)[/]?$', blocks.reload_relations_block, name='creme_core__reload_relations_block'),

    url(r'^(?P<block_id>[\w\-\|]+)/(?P<entity_id>\d+)[/]?$', blocks.reload_detailview, name='creme_core__reload_detailview_blocks'),

    url(r'^home/(?P<block_id>[\w\-\|]+)[/]?$',                      blocks.reload_home,   name='creme_core__reload_home_blocks'),
    url(r'^portal/(?P<block_id>[\w\-\|]+)/(?P<ct_ids>[\d,]+)[/]?$', blocks.reload_portal, name='creme_core__reload_portal_blocks'),

    url(r'^basic/(?P<block_id>[\w\-\|]+)[/]?$', blocks.reload_basic, name='creme_core__reload_blocks'),

    url(r'^set_state/(?P<block_id>[\w\-\|]+)[/]?$', blocks.set_state, name='creme_core__set_block_state'),
]

bricks_patterns = [
    url(r'^reload[/]?$',                               bricks.reload_basic,      name='creme_core__reload_bricks'),
    url(r'^reload/detailview/(?P<entity_id>\d+)[/]?$', bricks.reload_detailview, name='creme_core__reload_detailview_bricks'),
    url(r'^reload/home[/]?$',                          bricks.reload_home,       name='creme_core__reload_home_bricks'),
    url(r'^reload/portal[/]?$',                        bricks.reload_portal,     name='creme_core__reload_portal_bricks'),

    url(r'^set_state[/]?$', bricks.set_state, name='creme_core__set_brick_state'),
]

entity_filter_patterns = [
    url(r'^add/(?P<ct_id>\d+)[/]?$',      entity_filter.add,    name='creme_core__create_efilter'),
    url(r'^edit/(?P<efilter_id>.+)[/]?$', entity_filter.edit,   name='creme_core__edit_efilter'),
    url(r'^delete[/]?$',                  entity_filter.delete, name='creme_core__delete_efilter'),

    # TODO: move to relation_patterns/factorise with 'creme_core__ctypes_compatible_with_rtype'
    url(r'^rtype/(?P<rtype_id>[\w-]+)/content_types[/]?$', entity_filter.get_content_types,
        name='creme_core__ctypes_compatible_with_rtype_as_choices',
       ),

    url(r'^get_for_ctype[/]?$', entity_filter.get_for_ctype, name='creme_core__efilters'),
    url(r'^get_for_ctype/(?P<ct_id>\d+)[/]?$',     entity_filter.get_for_ctype,                        name='creme_core__efilters'),  # DEPRECATED
    url(r'^get_for_ctype/(?P<ct_id>\d+)/all[/]?$', entity_filter.get_for_ctype, {'include_all': True}, name='creme_core__efilters_n_all'),  # DEPRECATED
]

headerfilter_patterns = [
    url(r'^add/(?P<content_type_id>\d+)[/]?$',      header_filter.add,           name='creme_core__create_hfilter'),
    url(r'^edit/(?P<header_filter_id>[\w-]+)[/]?$', header_filter.edit,          name='creme_core__edit_hfilter'),
    url(r'^delete[/]*',                             header_filter.delete,        name='creme_core__delete_hfilter'),
    url(r'^get_for_ctype[/]?$',                     header_filter.get_for_ctype, name='creme_core__hfilters'),
    url(r'^get_for_ctype/(?P<ct_id>\d+)[/]?$',      header_filter.get_for_ctype, name='creme_core__hfilters'),  # DEPRECATED
]

enumerable_patterns = [
    url(r'^(?P<ct_id>\d+)/json[/]?$',        enumerable.json_list_enumerable,        name='creme_core__list_enumerable'),
    url(r'^custom/(?P<cf_id>\d+)/json[/]?$', enumerable.json_list_enumerable_custom, name='creme_core__cfield_enums'),

    # TODO: move to entity_filter_patterns
    url(r'^userfilter/json[/]?$', enumerable.json_list_userfilter, name='creme_core__efilter_user_choices'),
]

job_patterns = [
    url(r'^all[/]?$',  job.listview, name='creme_core__jobs'),
    url(r'^info[/]?$', job.get_info, name='creme_core__jobs_info'),

    url(r'^(?P<job_id>\d+)', include([
        url(r'^[/]?$',         job.detailview,                 name='creme_core__job'),
        url(r'^/edit[/]?$',    job.edit,                       name='creme_core__edit_job'),
        url(r'^/delete[/]?$',  job.delete,                     name='creme_core__delete_job'),
        url(r'^/enable[/]?$',  job.enable,                     name='creme_core__enable_job'),
        url(r'^/disable[/]?$', job.enable, {'enabled': False}, name='creme_core__disable_job'),
        url(r'^/reload[/]?$',  job.reload_bricks,              name='creme_core__reload_job_bricks'),
    ])),
]

creme_core_patterns = [
    url(r'^entity/',        include(entity_patterns)),
    url(r'^relation/',      include(relation_patterns)),
    url(r'^property/',      include(property_patterns)),
    url(r'^blocks/reload/', include(blocks_patterns)),
    url(r'^bricks/',        include(bricks_patterns)),
    url(r'^entity_filter/', include(entity_filter_patterns)),
    url(r'^header_filter/', include(headerfilter_patterns)),
    url(r'^enumerable/',    include(enumerable_patterns)),
    url(r'^job/',           include(job_patterns)),

    url(r'^list_view/popup[/]?$', entity.list_view_popup, name='creme_core__listview_popup'),
    url(r'^list_view/popup/(?P<ct_id>\d+)/(?P<o2m>0|1)[/]?$', listview.list_view_popup_from_widget, name='creme_core__listview_popup'),  # DEPRECATED

    # url(r'^list_view/import/(?P<ct_id>\d+)$', list_view_import.import_listview),  # see mass_import/

    url(r'^list_view/download[/]?$', list_view_export.dl_listview, name='creme_core__dl_listview'),
    url(r'^list_view/download/(?P<ct_id>\d+)/(?P<doc_type>[\w-]+)[/]?$',
        list_view_export.dl_listview, {'header_only': False},
        name='creme_core__dl_listview',
       ),  # DEPRECATED
    # url(r'^list_view/download_header/(?P<ct_id>\d+)/(?P<doc_type>[\w-]+)$', list_view_export.dl_listview_header),
    url(r'^list_view/download_header/(?P<ct_id>\d+)/(?P<doc_type>[\w-]+)[/]?$',
        list_view_export.dl_listview, {'header_only': True},
        name='creme_core__dl_listview_header',
       ),  # DEPRECATED

    url(r'^mass_import/(?P<ct_id>\d+)[/]?$',            mass_import.mass_import,     name='creme_core__mass_import'),
    url(r'^mass_import/dl_errors/(?P<job_id>\d+)[/]?$', mass_import.download_errors, name='creme_core__dl_mass_import_errors'),

    # TODO: change url (remove 'list_view'...)?? (then group other "list_view/" URLs)
    url(r'^list_view/batch_process/(?P<ct_id>\d+)[/]?$',                          batch_process.batch_process, name='creme_core__batch_process'),
    url(r'^list_view/batch_process/(?P<ct_id>\d+)/get_ops/(?P<field>[\w]+)[/]?$', batch_process.get_ops,       name='creme_core__batch_process_ops'),

    # Search
    url(r'^search[/]?$',              search.search,       name='creme_core__search'),
    url(r'^search/light[/]?$',        search.light_search, name='creme_core__light_search'),
    url(r'^search/reload_brick[/]?$', search.reload_brick, name='creme_core__reload_search_brick'),
    url(r'^search/reload_block/(?P<block_id>[\w\-\|]+)/(?P<research>.+)[/]?$', search.reload_block, name='creme_core__reload_search_block'),  # DEPRECATED

    url(r'^quickforms/(?P<ct_id>\d+)/(?P<count>\d)[/]?$',                  quick_forms.add,             name='creme_core__quick_forms'),
    # url(r'^quickforms/from_widget/(?P<ct_id>\d+)/add/(?P<count>\d)$', quick_forms.add_from_widget),
    url(r'^quickforms/from_widget/(?P<ct_id>\d+)/add/(?P<count>\d)*[/]?$', quick_forms.add_from_widget, name='creme_core__quick_form'),  # TODO: remove 'count' in creme1.8
]

urlpatterns = [
    url(r'^$',            index.home,    name='creme_core__home'),
    url(r'^my_page[/]?$', index.my_page, name='creme_core__my_page'),

    # TODO : To be replaced
    url(r'^download_file/(?P<location>.*)$', file_handling.download_file, name='creme_core__dl_file'),

    url(r'^creme_core/', include(creme_core_patterns)),

    url(r'^test_http_response[/]?$',               testjs.test_http_response, name='creme_core__test_http_response'),
    url(r'^test_js[/]?$',                          testjs.test_js,            name='creme_core__test_js'),
    url(r'^test_widget(/|/(?P<widget>\w+)[/]?)?$', testjs.test_widget,        name='creme_core__test_widget'),
]

if settings.TESTS_ON:
    from .tests import fake_views

    urlpatterns += [
        url(r'^tests/documents[/]?$', fake_views.document_listview, name='creme_core__list_fake_documents'),
        # url(r'^tests/document/add[/]?$',                  'fake_views.document_add',        name='creme_core__create_fake_document'),
        # url(r'^tests/document/edit/(?P<doc_id>\d+)[/]?$', 'fake_views.document_edit',       name='creme_core__edit_fake_document'),
        # url(r'^tests/document/(?P<doc_id>\d+)[/]?$',      'fake_views.document_detailview', name='creme_core__view_fake_document'),

        url(r'^tests/images[/]?$',                  fake_views.image_listview, name='creme_core__list_fake_images'),
        # url(r'^tests/image/add[/]?$',                    'fake_views.image_add',  name='creme_core__create_fake_image'),
        # url(r'^tests/image/edit/(?P<image_id>\d+)[/]?$', 'fake_views.image_edit', name='creme_core__edit_fake_image'),
        url(r'^tests/image/(?P<image_id>\d+)[/]?$', fake_views.image_detailview, name='creme_core__view_fake_image'),

        url(r'^tests/contacts[/]?$',                         fake_views.contact_listview,   name='creme_core__list_fake_contacts'),
        url(r'^tests/contact/add[/]?$',                      fake_views.contact_add,        name='creme_core__create_fake_contact'),
        url(r'^tests/contact/edit/(?P<contact_id>\d+)[/]?$', fake_views.contact_edit,       name='creme_core__edit_fake_contact'),
        url(r'^tests/contact/(?P<contact_id>\d+)[/]?$',      fake_views.contact_detailview, name='creme_core__view_fake_contact'),

        url(r'^tests/organisations[/]?$',                      fake_views.organisation_listview,   name='creme_core__list_fake_organisations'),
        url(r'^tests/organisation/add[/]?$',                   fake_views.organisation_add,        name='creme_core__create_fake_organisation'),
        url(r'^tests/organisation/edit/(?P<orga_id>\d+)[/]?$', fake_views.organisation_edit,       name='creme_core__edit_fake_organisation'),
        url(r'^tests/organisation/(?P<orga_id>\d+)[/]?$',      fake_views.organisation_detailview, name='creme_core__view_fake_organisation'),

        url(r'^tests/address/add/(?P<entity_id>\d+)[/]?$',   fake_views.address_add,  name='creme_core__create_fake_address'),
        url(r'^tests/address/edit/(?P<address_id>\d+)[/]?$', fake_views.address_edit, name='creme_core__edit_fake_address'),

        url(r'^tests/activities[/]?$', fake_views.activity_listview, name='creme_core__list_fake_activities'),
        # url(r'^tests/activity/add[/]?$',                  'fake_views.activity_add',        name='creme_core__create_fake_activity'),
        # url(r'^tests/activity/edit/(?P<act_id>\d+)[/]?$', 'fake_views.activity_edit',       name='creme_core__edit_fake_activity'),
        # url(r'^tests/activity/(?P<act_id>\d+)[/]?$',      'fake_views.activity_detailview', name='creme_core__view_fake_activity'),

        url(r'^tests/e_campaigns[/]?$', fake_views.campaign_listview, name='creme_core__list_fake_ecampaigns'),
        # url(r'^tests/e_campaign/add[/]?$',                       'fake_views.campaign_add',        name='creme_core__create_fake_ecampaign'),
        # url(r'^tests/e_campaign/edit/(?P<campaign_id>\d+)[/]?$', 'fake_views.campaign_edit',       name='creme_core__edit_fake_ecampaign'),
        # url(r'^tests/e_campaign/(?P<campaign_id>\d+)[/]?$',      'fake_views.campaign_detailview', name='creme_core__view_fake_ecampaign'),

        url(r'^tests/invoices[/]?$',                    fake_views.invoice_listview, name='creme_core__list_fake_invoices'),
        # url(r'^tests/invoice/add[/]?$',                      'fake_views.invoice_add',  name='creme_core__create_fake_invoice'),
        # url(r'^tests/invoice/edit/(?P<invoice_id>\d+)[/]?$', 'fake_views.invoice_edit', name='creme_core__edit_fake_invoice'),
        url(r'^tests/invoice/(?P<invoice_id>\d+)[/]?$', fake_views.invoice_detailview, name='creme_core__view_fake_invoice'),

        url(r'^tests/invoice_lines[/]?$', fake_views.invoice_lines_listview, name='creme_core__list_fake_invoicelines'),
    ]
