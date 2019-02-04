# -*- coding: utf-8 -*-

from django.conf.urls import url

from ..views.generic.placeholder import ErrorView

from . import fake_views


urlpatterns = [
    # url(r'^tests/documents[/]?$', fake_views.document_listview, name='creme_core__list_fake_documents'),
    url(r'^tests/documents[/]?$', fake_views.FakeDocumentsList.as_view(), name='creme_core__list_fake_documents'),

    # url(r'^tests/images[/]?$',                  fake_views.image_listview, name='creme_core__list_fake_images'),
    url(r'^tests/images[/]?$',                  fake_views.FakeImagesList.as_view(),  name='creme_core__list_fake_images'),
    url(r'^tests/image/(?P<image_id>\d+)[/]?$', fake_views.FakeImageDetail.as_view(), name='creme_core__view_fake_image'),

    # url(r'^tests/contacts[/]?$',                         fake_views.contact_listview,              name='creme_core__list_fake_contacts'),
    url(r'^tests/contacts[/]?$',                         fake_views.FakeContactsList.as_view(),    name='creme_core__list_fake_contacts'),
    url(r'^tests/contact/add[/]?$',                      fake_views.FakeContactCreation.as_view(), name='creme_core__create_fake_contact'),
    url(r'^tests/contact/edit/(?P<contact_id>\d+)[/]?$', fake_views.FakeContactEdition.as_view(),  name='creme_core__edit_fake_contact'),
    url(r'^tests/contact/(?P<contact_id>\d+)[/]?$',      fake_views.FakeContactDetail.as_view(),   name='creme_core__view_fake_contact'),

    # url(r'^tests/organisations[/]?$',                      fake_views.organisation_listview,              name='creme_core__list_fake_organisations'),
    url(r'^tests/organisations[/]?$',                      fake_views.FakeOrganisationsList.as_view(),    name='creme_core__list_fake_organisations'),
    url(r'^tests/organisation/add[/]?$',                   fake_views.FakeOrganisationCreation.as_view(), name='creme_core__create_fake_organisation'),
    url(r'^tests/organisation/edit/(?P<orga_id>\d+)[/]?$', fake_views.FakeOrganisationEdition.as_view(),  name='creme_core__edit_fake_organisation'),
    url(r'^tests/organisation/(?P<orga_id>\d+)[/]?$',      fake_views.FakeOrganisationDetail.as_view(),   name='creme_core__view_fake_organisation'),

    # url(r'^tests/address/legacy_add/(?P<entity_id>\d+)[/]?$',   fake_views.address_add,                   name='creme_core__create_fake_address_legacy'),
    url(r'^tests/address/add/(?P<entity_id>\d+)[/]?$',          fake_views.FakeAddressCreation.as_view(), name='creme_core__create_fake_address'),
    # url(r'^tests/address/legacy_edit/(?P<address_id>\d+)[/]?$', fake_views.address_edit,                  name='creme_core__edit_fake_address_legacy'),
    url(r'^tests/address/edit/(?P<address_id>\d+)[/]?$',        fake_views.FakeAddressEdition.as_view(),  name='creme_core__edit_fake_address'),

    # url(r'^tests/activities[/]?$', fake_views.activity_listview, name='creme_core__list_fake_activities'),
    url(r'^tests/activities[/]?$', fake_views.FakeActivitiesList.as_view(), name='creme_core__list_fake_activities'),

    # url(r'^tests/e_campaigns[/]?$', fake_views.campaign_listview, name='creme_core__list_fake_ecampaigns'),
    url(r'^tests/e_campaigns[/]?$', fake_views.FakeEmailCampaignsList.as_view(), name='creme_core__list_fake_ecampaigns'),

    # url(r'^tests/invoices[/]?$',                    fake_views.invoice_listview,   name='creme_core__list_fake_invoices'),
    url(r'^tests/invoices[/]?$',                    fake_views.FakeInvoicesList.as_view(),  name='creme_core__list_fake_invoices'),
    url(r'^tests/invoice/(?P<invoice_id>\d+)[/]?$', fake_views.FakeInvoiceDetail.as_view(), name='creme_core__view_fake_invoice'),

    # url(r'^tests/invoice_lines[/]?$', fake_views.invoice_lines_listview, name='creme_core__list_fake_invoicelines'),
    url(r'^tests/invoice_lines[/]?$', fake_views.FakeInvoiceLinesList.as_view(), name='creme_core__list_fake_invoicelines'),
    # url(r'^tests/mailing_lists[/]?$', fake_views.mailing_lists_listview, name='creme_core__list_fake_mlists'),
    url(r'^tests/mailing_lists[/]?$', fake_views.FakeMailingListsList.as_view(), name='creme_core__list_fake_mlists'),

    url(r'^tests/whatever/(?P<useless>\d+)[/]?$',
        ErrorView.as_view(message='Custom error message'),
        name='creme_core__fake_removed_view',
       ),
]
