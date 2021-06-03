# -*- coding: utf-8 -*-

from django.urls import re_path

from ..views.generic.placeholder import ErrorView
from . import fake_views

urlpatterns = [
    re_path(
        r'^tests/documents[/]?$',
        fake_views.FakeDocumentsList.as_view(),
        name='creme_core__list_fake_documents',
    ),

    re_path(
        r'^tests/images[/]?$',
        fake_views.FakeImagesList.as_view(),
        name='creme_core__list_fake_images',
    ),
    re_path(
        r'^tests/image/(?P<image_id>\d+)[/]?$',
        fake_views.FakeImageDetail.as_view(),
        name='creme_core__view_fake_image',
    ),

    re_path(
        r'^tests/contacts[/]?$',
        fake_views.FakeContactsList.as_view(),
        name='creme_core__list_fake_contacts',
    ),
    re_path(
        r'^tests/contact/add[/]?$',
        fake_views.FakeContactCreation.as_view(),
        name='creme_core__create_fake_contact',
    ),
    re_path(
        r'^tests/contact/edit/(?P<contact_id>\d+)[/]?$',
        fake_views.FakeContactEdition.as_view(),
        name='creme_core__edit_fake_contact',
    ),
    re_path(
        r'^tests/contact/(?P<contact_id>\d+)[/]?$',
        fake_views.FakeContactDetail.as_view(),
        name='creme_core__view_fake_contact',
    ),

    re_path(
        r'^tests/organisations[/]?$',
        fake_views.FakeOrganisationsList.as_view(),
        name='creme_core__list_fake_organisations',
    ),
    re_path(
        r'^tests/organisation/add[/]?$',
        fake_views.FakeOrganisationCreation.as_view(),
        name='creme_core__create_fake_organisation',
    ),
    re_path(
        r'^tests/organisation/edit/(?P<orga_id>\d+)[/]?$',
        fake_views.FakeOrganisationEdition.as_view(),
        name='creme_core__edit_fake_organisation',
    ),
    re_path(
        r'^tests/organisation/(?P<orga_id>\d+)[/]?$',
        fake_views.FakeOrganisationDetail.as_view(),
        name='creme_core__view_fake_organisation',
    ),

    re_path(
        r'^tests/address/add/(?P<entity_id>\d+)[/]?$',
        fake_views.FakeAddressCreation.as_view(),
        name='creme_core__create_fake_address'
    ),
    re_path(
        r'^tests/address/edit/(?P<address_id>\d+)[/]?$',
        fake_views.FakeAddressEdition.as_view(),
        name='creme_core__edit_fake_address'
    ),

    re_path(
        r'^tests/activity/add[/]?$',
        fake_views.FakeActivityCreation.as_view(),
        name='creme_core__create_fake_activity',
    ),
    re_path(
        r'^tests/activity/edit/(?P<activity_id>\d+)[/]?$',
        fake_views.FakeActivityEdition.as_view(),
        name='creme_core__edit_fake_activity',
    ),
    re_path(
        r'^tests/activities[/]?$',
        fake_views.FakeActivitiesList.as_view(),
        name='creme_core__list_fake_activities',
    ),

    re_path(
        r'^tests/e_campaigns[/]?$',
        fake_views.FakeEmailCampaignsList.as_view(),
        name='creme_core__list_fake_ecampaigns',
    ),

    re_path(
        r'^tests/invoices[/]?$',
        fake_views.FakeInvoicesList.as_view(),
        name='creme_core__list_fake_invoices',
    ),
    re_path(
        r'^tests/invoice/(?P<invoice_id>\d+)[/]?$',
        fake_views.FakeInvoiceDetail.as_view(),
        name='creme_core__view_fake_invoice',
    ),

    re_path(
        r'^tests/invoice_lines[/]?$',
        fake_views.FakeInvoiceLinesList.as_view(),
        name='creme_core__list_fake_invoicelines',
    ),

    re_path(
        r'^tests/mailing_lists[/]?$',
        fake_views.FakeMailingListsList.as_view(),
        name='creme_core__list_fake_mlists',
    ),
    re_path(
        r'^tests/mailing_list/(?P<ml_id>\d+)[/]?$',
        fake_views.FakeMailingListDetail.as_view(),
        name='creme_core__view_fake_mlist',
    ),

    re_path(
        r'^tests/whatever/(?P<useless>\d+)[/]?$',
        ErrorView.as_view(message='Custom error message'),
        name='creme_core__fake_removed_view',
    ),
]
