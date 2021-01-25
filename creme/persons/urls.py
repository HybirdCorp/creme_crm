# -*- coding: utf-8 -*-

from django.urls import re_path  # include

from creme import persons
from creme.creme_core.conf.urls import Swappable, swap_manager

from .views import address, contact, organisation  # crud_relations

urlpatterns = [
    re_path(
        r'^organisation/managed[/]?$',
        organisation.ManagedOrganisationsAdding.as_view(),
        name='persons__orga_set_managed',
    ),
    re_path(
        r'^organisation/not_managed[/]?$',
        organisation.OrganisationUnmanage.as_view(),
        name='persons__orga_unset_managed',
    ),

    # re_path(
    #     r'^(?P<entity_id>\d+)/become_',
    #     include([
    #         re_path(
    #             r'^customer[/]?$',
    #             crud_relations.become_customer, name='persons__become_customer',
    #         ),
    #         re_path(
    #             r'^prospect[/]?$',
    #             crud_relations.become_prospect, name='persons__become_prospect',
    #         ),
    #         re_path(
    #             r'^suspect[/]?$',
    #             crud_relations.become_suspect,  name='persons__become_suspect',
    #         ),
    #         re_path(
    #             r'^inactive_customer[/]?$',
    #             crud_relations.become_inactive, name='persons__become_inactive_customer',
    #         ),
    #         re_path(
    #             r'^supplier[/]?$',
    #             crud_relations.become_supplier, name='persons__become_supplier',
    #         ),
    #     ]),
    # ),

    *swap_manager.add_group(
        persons.contact_model_is_custom,
        Swappable(
            re_path(
                r'^contacts[/]?$',
                contact.ContactsList.as_view(),
                name='persons__list_contacts',
            )
        ),
        Swappable(
            re_path(
                r'^contact/add[/]?$',
                contact.ContactCreation.as_view(),
                name='persons__create_contact',
            ),
        ),
        Swappable(
            re_path(
                r'^contact/add_related/(?P<orga_id>\d+)[/]?$',
                contact.RelatedContactCreation.as_view(),
                name='persons__create_related_contact',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^contact/add_related/(?P<orga_id>\d+)/(?P<rtype_id>[\w-]+)[/]?$',
                contact.RelatedContactCreation.as_view(),
                name='persons__create_related_contact',
            ),
            check_args=(1, 'idxxx'),
        ),
        Swappable(
            re_path(
                r'^contact/edit/(?P<contact_id>\d+)[/]?$',
                contact.ContactEdition.as_view(),
                name='persons__edit_contact',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^contact/edit_names/(?P<contact_id>\d+)[/]?$',
                contact.ContactNamesEdition.as_view(),
                name='persons__edit_contact_names',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^contact/(?P<contact_id>\d+)[/]?$',
                contact.ContactDetail.as_view(),
                name='persons__view_contact',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='persons',
    ).kept_patterns(),

    *swap_manager.add_group(
        persons.organisation_model_is_custom,
        Swappable(
            re_path(
                r'^organisations[/]?$',
                organisation.OrganisationsList.as_view(),
                name='persons__list_organisations',
            )
        ),
        Swappable(
            re_path(
                r'^organisation/add[/]?$',
                organisation.OrganisationCreation.as_view(),
                name='persons__create_organisation',
            ),
        ),
        Swappable(
            re_path(
                r'^organisation/edit/(?P<orga_id>\d+)[/]?$',
                organisation.OrganisationEdition.as_view(),
                name='persons__edit_organisation',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^organisation/(?P<orga_id>\d+)[/]?$',
                organisation.OrganisationDetail.as_view(),
                name='persons__view_organisation',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^leads_customers[/]?$',
                organisation.MyLeadsAndMyCustomersList.as_view(),
                name='persons__leads_customers',
            ),
        ),
        Swappable(
            re_path(
                r'^lead_customer/add[/]?$',
                organisation.CustomerCreation.as_view(),
                name='persons__create_customer',
            ),
        ),
        app_name='persons',
    ).kept_patterns(),

    *swap_manager.add_group(
        persons.address_model_is_custom,
        Swappable(
            re_path(
                r'^address/add/(?P<entity_id>\d+)[/]?$',
                address.AddressCreation.as_view(),
                name='persons__create_address',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^address/add/billing/(?P<entity_id>\d+)[/]?$',
                address.BillingAddressCreation.as_view(),
                name='persons__create_billing_address',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^address/add/shipping/(?P<entity_id>\d+)[/]?$',
                address.ShippingAddressCreation.as_view(),
                name='persons__create_shipping_address',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^address/edit/(?P<address_id>\d+)[/]?$',
                address.AddressEdition.as_view(),
                name='persons__edit_address',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='persons',
    ).kept_patterns(),
]
