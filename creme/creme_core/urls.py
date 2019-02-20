# -*- coding: utf-8 -*-

from django.conf import settings
# from django.conf.urls import url, include
from django.urls import re_path, include

from .views import (batch_process, bricks, creme_property, enumerable, entity,
        entity_filter, file_handling, header_filter, index, job, list_view_export,
        mass_import, quick_forms, relation, search, testjs,
       )


entity_patterns = [
    re_path(r'^delete/multi[/]?$',                  entity.delete_entities,          name='creme_core__delete_entities'),
    re_path(r'^delete/(?P<entity_id>\d+)[/]?$',     entity.delete_entity,            name='creme_core__delete_entity'),
    re_path(r'^delete_related/(?P<ct_id>\d+)[/]?$', entity.delete_related_to_entity, name='creme_core__delete_related_to_entity'),
    re_path(r'^restore/(?P<entity_id>\d+)[/]?$',    entity.restore_entity,           name='creme_core__restore_entity'),
    re_path(r'^trash[/]?$',                         entity.Trash.as_view(),          name='creme_core__trash'),
    re_path(r'^trash/empty[/]?$',                   entity.empty_trash,              name='creme_core__empty_trash'),

    # TODO: add a view 'creme_core__entities_as_json'
    #       (with same features as 'creme_core__entity_as_json', then remove this one)
    # TODO: IDs as GET arguments
    re_path(r'^get_repr/(?P<entities_ids>([\d]+[,]*)+)[/]?$',                      entity.get_creme_entities_repr,  name='creme_core__entities_summaries'),
    re_path(r'^get_sanitized_html/(?P<entity_id>\d+)/(?P<field_name>[\w-]+)[/]?$', entity.get_sanitized_html_field, name='creme_core__sanitized_html_field'),
    # url(r'^search_n_view[/]?$',                                                entity.search_and_view,          name='creme_core__search_n_view_entities'),
    re_path(r'^search_n_view[/]?$',                                                entity.SearchAndView.as_view(),  name='creme_core__search_n_view_entities'),
    re_path(r'^get_info_fields/(?P<ct_id>\d+)/json[/]?$',                          entity.get_info_fields,          name='creme_core__entity_info_fields'),

    re_path(r'^edit/inner/(?P<ct_id>\d+)/(?P<id>\d+)/field/(?P<field_name>[\w-]+)[/]?$', entity.InnerEdition.as_view(), name='creme_core__inner_edition'),

    re_path(r'^update/bulk/(?P<ct_id>\d+)[/]?$',                              entity.BulkUpdate.as_view(), name='creme_core__bulk_update'),
    re_path(r'^update/bulk/(?P<ct_id>\d+)/field/(?P<field_name>[\w-]+)[/]?$', entity.BulkUpdate.as_view(), name='creme_core__bulk_update'),

    # re_path(r'^clone[/]*', entity.clone, name='creme_core__clone_entity'),
    re_path(r'^clone[/]*', entity.Clone.as_view(), name='creme_core__clone_entity'),

    # url(r'^merge/select_other[/]?$', entity.select_entity_for_merge,  name='creme_core__select_entity_for_merge'),
    re_path(r'^merge/select_other[/]?$', entity.EntitiesToMergeSelection.as_view(), name='creme_core__select_entity_for_merge'),
    # url(r'^merge[/]?$',              entity.merge,                    name='creme_core__merge_entities'),
    re_path(r'^merge[/]?$',              entity.Merge.as_view(),                    name='creme_core__merge_entities'),

    re_path(r'^restrict_to_superusers[/]?$', entity.restrict_to_superusers, name='creme_core__restrict_entity_2_superusers'),
]

relation_patterns = [
    re_path(r'^add/(?P<subject_id>\d+)[/]?$',                      relation.RelationsAdding.as_view(), name='creme_core__create_relations'),
    re_path(r'^add/(?P<subject_id>\d+)/(?P<rtype_id>[\w-]+)[/]?$', relation.RelationsAdding.as_view(), name='creme_core__create_relations'),

    re_path(r'^add_from_predicate/save[/]?$', relation.add_relations_with_same_type, name='creme_core__save_relations'),

    re_path(r'^add_to_entities/(?P<ct_id>\d+)[/]?$',
        relation.RelationsBulkAdding.as_view(),
        name='creme_core__create_relations_bulk',
    ),

    # url(r'^objects2link[/]?$', relation.select_relations_objects, name='creme_core__select_entities_to_link'),
    re_path(r'^objects2link[/]?$', relation.RelationsObjectsSelectionPopup.as_view(), name='creme_core__select_entities_to_link'),

    re_path(r'^delete[/]?$',         relation.delete,         name='creme_core__delete_relation'),
    re_path(r'^delete/similar[/]?$', relation.delete_similar, name='creme_core__delete_similar_relations'),
    re_path(r'^delete/all[/]?$',     relation.delete_all,     name='creme_core__delete_all_relations'),

    re_path(r'^entity/(?P<entity_id>\d+)/json[/]?$',               relation.json_entity_get,    name='creme_core__entity_as_json'),  # TODO: move to entity_patterns ?
    re_path(r'^entity/(?P<entity_id>\d+)/rtypes/json[/]?$',        relation.json_entity_rtypes, name='creme_core__rtypes_compatible_with_entity'),
    re_path(r'^type/(?P<rtype_id>[\w-]+)/content_types/json[/]?$', relation.json_rtype_ctypes,  name='creme_core__ctypes_compatible_with_rtype'),
]

property_patterns = [
    re_path(r'^add_to_entities/(?P<ct_id>\d+)[/]?$',
        creme_property.PropertiesBulkAdding.as_view(),
        name='creme_core__add_properties_bulk',
    ),

    re_path(r'^add/(?P<entity_id>\d+)[/]?$', creme_property.PropertiesAdding.as_view(), name='creme_core__add_properties'),
    re_path(r'^delete_from_type[/]?$',       creme_property.delete_from_type,           name='creme_core__remove_property'),

    # Property type
    re_path(r'^type/add[/]?$',                                creme_property.PropertyTypeCreation.as_view(), name='creme_core__create_ptype'),
    re_path(r'^type/(?P<ptype_id>[\w-]+)[/]?$',               creme_property.PropertyTypeDetail.as_view(),   name='creme_core__ptype'),
    re_path(r'^type/(?P<ptype_id>[\w-]+)/edit[/]?$',          creme_property.PropertyTypeEdition.as_view(),  name='creme_core__edit_ptype'),
    re_path(r'^type/(?P<ptype_id>[\w-]+)/delete[/]?$',        creme_property.delete_type,                    name='creme_core__delete_ptype'),
    re_path(r'^type/(?P<ptype_id>[\w-]+)/reload_bricks[/]?$', creme_property.reload_bricks,                  name='creme_core__reload_ptype_bricks'),
]

bricks_patterns = [
    re_path(r'^reload[/]?$',                               bricks.reload_basic,      name='creme_core__reload_bricks'),
    re_path(r'^reload/detailview/(?P<entity_id>\d+)[/]?$', bricks.reload_detailview, name='creme_core__reload_detailview_bricks'),
    re_path(r'^reload/home[/]?$',                          bricks.reload_home,       name='creme_core__reload_home_bricks'),

    re_path(r'^set_state[/]?$', bricks.set_state, name='creme_core__set_brick_state'),
]

entity_filter_patterns = [
    re_path(r'^add/(?P<ct_id>\d+)[/]?$',      entity_filter.EntityFilterCreation.as_view(), name='creme_core__create_efilter'),
    re_path(r'^edit/(?P<efilter_id>.+)[/]?$', entity_filter.EntityFilterEdition.as_view(),  name='creme_core__edit_efilter'),
    re_path(r'^delete[/]?$',                  entity_filter.delete,                         name='creme_core__delete_efilter'),

    # TODO: move to relation_patterns/factorise with 'creme_core__ctypes_compatible_with_rtype'
    re_path(r'^rtype/(?P<rtype_id>[\w-]+)/content_types[/]?$', entity_filter.get_content_types,
        name='creme_core__ctypes_compatible_with_rtype_as_choices',
       ),

    re_path(r'^get_for_ctype[/]?$', entity_filter.get_for_ctype, name='creme_core__efilters'),
]

headerfilter_patterns = [
    re_path(r'^add/(?P<ct_id>\d+)[/]?$',          header_filter.HeaderFilterCreation.as_view(), name='creme_core__create_hfilter'),
    re_path(r'^edit/(?P<hfilter_id>[\w-]+)[/]?$', header_filter.HeaderFilterEdition.as_view(),  name='creme_core__edit_hfilter'),
    re_path(r'^delete[/]?$',                      header_filter.delete,                         name='creme_core__delete_hfilter'),
    re_path(r'^get_for_ctype[/]?$',               header_filter.get_for_ctype,                  name='creme_core__hfilters'),
]

enumerable_patterns = [
    # url(r'^(?P<ct_id>\d+)/json[/]?$',                  enumerable.json_list_enumerable,        name='creme_core__list_enumerable'),
    re_path(r'^(?P<ct_id>\d+)/(?P<field>[\w]+)/json[/]?$', enumerable.ChoicesView.as_view(),       name='creme_core__enumerable_choices'),
    re_path(r'^custom/(?P<cf_id>\d+)/json[/]?$',           enumerable.json_list_enumerable_custom, name='creme_core__cfield_enums'),

    # TODO: move to entity_filter_patterns
    re_path(r'^userfilter/json[/]?$', enumerable.json_list_userfilter, name='creme_core__efilter_user_choices'),
]

job_patterns = [
    re_path(r'^all[/]?$',             job.Jobs.as_view(),      name='creme_core__jobs'),
    re_path(r'^mine[/]?$',            job.MyJobs.as_view(),    name='creme_core__my_jobs'),
    re_path(r'^info[/]?$',            job.get_info,            name='creme_core__jobs_info'),
    re_path(r'^(?P<job_id>\d+)[/]?$', job.JobDetail.as_view(), name='creme_core__job'),

    re_path(r'^(?P<job_id>\d+)/', include([
        re_path(r'^edit[/]?$',    job.JobEdition.as_view(),       name='creme_core__edit_job'),
        re_path(r'^delete[/]?$',  job.delete,                     name='creme_core__delete_job'),
        re_path(r'^enable[/]?$',  job.enable,                     name='creme_core__enable_job'),
        re_path(r'^disable[/]?$', job.enable, {'enabled': False}, name='creme_core__disable_job'),
        re_path(r'^reload[/]?$',  job.reload_bricks,              name='creme_core__reload_job_bricks'),
    ])),
]

creme_core_patterns = [
    re_path(r'^entity/',        include(entity_patterns)),
    re_path(r'^relation/',      include(relation_patterns)),
    re_path(r'^property/',      include(property_patterns)),
    re_path(r'^bricks/',        include(bricks_patterns)),
    re_path(r'^entity_filter/', include(entity_filter_patterns)),
    re_path(r'^header_filter/', include(headerfilter_patterns)),
    re_path(r'^enumerable/',    include(enumerable_patterns)),
    re_path(r'^job/',           include(job_patterns)),

    # url(r'^list_view/popup[/]?$', entity.list_view_popup, name='creme_core__listview_popup'),
    re_path(r'^list_view/popup[/]?$', entity.EntitiesListPopup.as_view(), name='creme_core__listview_popup'),

    re_path(r'^list_view/download[/]?$', list_view_export.dl_listview, name='creme_core__dl_listview'),

    re_path(r'^mass_import/', include([
        re_path(r'^(?P<ct_id>\d+)[/]?$',            mass_import.mass_import,     name='creme_core__mass_import'),
        re_path(r'^dl_errors/(?P<job_id>\d+)[/]?$', mass_import.download_errors, name='creme_core__dl_mass_import_errors'),
    ])),

    # TODO: change url (remove 'list_view'...)?? (then group other "list_view/" URLs)
    re_path(r'^list_view/batch_process/(?P<ct_id>\d+)[/]?$',                          batch_process.batch_process, name='creme_core__batch_process'),
    re_path(r'^list_view/batch_process/(?P<ct_id>\d+)/get_ops/(?P<field>[\w]+)[/]?$', batch_process.get_ops,       name='creme_core__batch_process_ops'),

    # Search
    re_path(r'^search[/]?$', search.Search.as_view(), name='creme_core__search'),
    re_path(r'^search/', include([
        re_path(r'^light[/]?$',        search.light_search, name='creme_core__light_search'),
        re_path(r'^reload_brick[/]?$', search.reload_brick, name='creme_core__reload_search_brick'),
    ])),

    re_path(r'^quickforms/', include([
        # url(r'^(?P<ct_id>\d+)/(?P<count>\d)[/]?$',   quick_forms.add,             name='creme_core__quick_forms'),
        re_path(r'^from_widget/(?P<ct_id>\d+)/add[/]?$', quick_forms.QuickCreation.as_view(), name='creme_core__quick_form'),  # TODO: change the URL
    ])),
]

urlpatterns = [
    re_path(r'^$',            index.Home.as_view(),   name='creme_core__home'),
    re_path(r'^my_page[/]?$', index.MyPage.as_view(), name='creme_core__my_page'),

    # TODO: To be replaced
    re_path(r'^download_file/(?P<location>.*)$', file_handling.download_file, name='creme_core__dl_file'),

    re_path(r'^creme_core/', include(creme_core_patterns)),

    re_path(r'^test_http_response[/]?$',               testjs.test_http_response, name='creme_core__test_http_response'),
    re_path(r'^test_js[/]?$',                          testjs.test_js,            name='creme_core__test_js'),
    re_path(r'^test_widget(/|/(?P<widget>\w+)[/]?)?$', testjs.test_widget,        name='creme_core__test_widget'),
]

if settings.TESTS_ON:
    from .tests import fake_urls

    urlpatterns += fake_urls.urlpatterns
