# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('persons.views',
    (r'^$', 'portal.portal'),

    (r'^contacts$',                                                            'contact.listview'),
    (r'^contact/add$',                                                         'contact.add'),
    (r'^contact/add_with_relation/(?P<orga_id>\d+)$',                          'contact.add_with_relation'),
    (r'^contact/add_with_relation/(?P<orga_id>\d+)/(?P<predicate_id>[\w-]+)$', 'contact.add_with_relation'),
    (r'^contact/edit/(?P<contact_id>\d+)$',                                    'contact.edit'),
    (r'^contact/(?P<contact_id>\d+)$',                                         'contact.detailview'),

    (r'^organisations$',                              'organisation.listview'),
    (r'^organisation/add$',                           'organisation.add'),
    (r'^organisation/edit/(?P<organisation_id>\d+)$', 'organisation.edit'),
    (r'^organisation/(?P<organisation_id>\d+)$',      'organisation.detailview'),
    (r'^leads_customers$',                            'organisation.list_my_leads_my_customers'),

    (r'^(?P<entity_id>\d+)/become_customer/(?P<mngd_orga_id>\d+)$',          'crud_relations.become_customer'),
    (r'^(?P<entity_id>\d+)/become_prospect/(?P<mngd_orga_id>\d+)$',          'crud_relations.become_prospect'),
    (r'^(?P<entity_id>\d+)/become_suspect/(?P<mngd_orga_id>\d+)$',           'crud_relations.become_suspect'),
    (r'^(?P<entity_id>\d+)/become_inactive_customer/(?P<mngd_orga_id>\d+)$', 'crud_relations.become_inactive'),
    (r'^(?P<entity_id>\d+)/become_supplier/(?P<mngd_orga_id>\d+)$',          'crud_relations.become_supplier'),

    (r'^address/from_organisation$',         'address.get_org_addresses'), #TODO: still useful ??
    (r'^address/add$',                       'address.add'), #TODO: NOT USED (specify Organisation or Contact ??)
    (r'^address/delete$',                    'address.delete'),
    (r'^address/edit/(?P<address_id>\d+)',   'address.edit'),
    (r'^address/ip_add/(?P<entity_id>\d+)$', 'address.ipopup_add_adress'),
)

urlpatterns += patterns('creme_core.views',
    (r'^contact/edit_js/$',                                'ajax.edit_js'),
    (r'^contact/delete/(?P<object_id>\d+)$',               'generic.delete_entity'),
    (r'^contact/delete_js/(?P<entities_ids>([\d]+[,])+)$', 'generic.delete_entities_js'),

    (r'^organisation/edit_js/$',                                'ajax.edit_js'),
    (r'^organisation/delete/(?P<object_id>\d+)$',               'generic.delete_entity'),
    (r'^organisation/delete_js/(?P<entities_ids>([\d]+[,])+)$', 'generic.delete_entities_js'),
)
