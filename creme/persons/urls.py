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

    (r'^(?P<entity_id>\d+)/become_customer$',          'crud_relations.become_customer'),
    (r'^(?P<entity_id>\d+)/become_prospect$',          'crud_relations.become_prospect'),
    (r'^(?P<entity_id>\d+)/become_suspect$',           'crud_relations.become_suspect'),
    (r'^(?P<entity_id>\d+)/become_inactive_customer$', 'crud_relations.become_inactive'),
    (r'^(?P<entity_id>\d+)/become_supplier$',          'crud_relations.become_supplier'),

    (r'^address/add/(?P<entity_id>\d+)$',  'address.add'),
    (r'^address/edit/(?P<address_id>\d+)', 'address.edit'),
)
