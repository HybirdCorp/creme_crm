# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth import EntityCredentials
from creme.creme_core.menu import CremeEntry
from creme.creme_core.models import EntityFilter, HeaderFilter, SetCredentials
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from .. import bricks, constants, workflow
from ..menu import UserContactEntry
from .base import Contact, Organisation


class PersonsAppTestCase(CremeTestCase, BrickTestCaseMixin):
    def test_populate(self):
        self.get_relationtype_or_fail(
            constants.REL_SUB_EMPLOYED_BY, [Contact], [Organisation],
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_CUSTOMER_SUPPLIER, [Contact, Organisation], [Contact, Organisation],
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_MANAGES, [Contact], [Organisation],
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_PROSPECT, [Contact, Organisation], [Contact, Organisation],
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_SUSPECT, [Contact, Organisation], [Contact, Organisation],
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_PARTNER, [Contact, Organisation], [Contact, Organisation],
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_INACTIVE, [Contact, Organisation], [Contact, Organisation],
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_SUBSIDIARY, [Organisation], [Organisation],
        )
        self.get_relationtype_or_fail(
            constants.REL_SUB_COMPETITOR, [Contact, Organisation], [Contact, Organisation],
        )

        get_ct = ContentType.objects.get_for_model
        hf_filter = HeaderFilter.objects.filter
        self.assertTrue(hf_filter(entity_type=get_ct(Contact)).exists())
        self.assertTrue(hf_filter(entity_type=get_ct(Organisation)).exists())

        efilter = self.get_object_or_fail(EntityFilter, pk=constants.FILTER_MANAGED_ORGA)
        self.assertFalse(efilter.is_custom)
        self.assertEqual(Organisation, efilter.entity_type.model_class())
        self.assertQuerysetSQLEqual(
            Organisation.objects.filter(is_managed=True),
            efilter.filter(Organisation.objects.all())
        )

    def test_config_portal(self):
        self.login()
        response = self.assertGET200(reverse('creme_config__portal'))
        self.get_brick_node(
            self.get_html_tree(response.content),
            bricks.ManagedOrganisationsBrick.id_,
        )

    def test_transform_target_into_prospect01(self):
        user = self.login()
        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source')
        target = create_orga(name='Target')

        workflow.transform_target_into_prospect(source, target, user)
        self.assertRelationCount(1, target, constants.REL_SUB_PROSPECT, source)

        # Do not create duplicate
        workflow.transform_target_into_prospect(source, target, user)
        self.assertRelationCount(1, target, constants.REL_SUB_PROSPECT, source)

    def test_transform_target_into_customer01(self):
        user = self.login()
        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source')
        target = create_orga(name='Target')

        workflow.transform_target_into_customer(source, target, user)
        self.assertRelationCount(1, target, constants.REL_SUB_CUSTOMER_SUPPLIER, source)

        # Do not create duplicate
        workflow.transform_target_into_prospect(source, target, user)
        self.assertRelationCount(1, target, constants.REL_SUB_CUSTOMER_SUPPLIER, source)

    def test_user_contact_menu_entry01(self):
        user = self.login(is_superuser=False, allowed_apps=['persons'])
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_ALL,
        )

        entry = UserContactEntry()
        self.assertEqual('persons-user_contact', entry.id)
        self.assertEqual(_("*User's contact*"), entry.label)
        self.assertHTMLEqual(
            f'<a href="{user.linked_contact.get_absolute_url()}">{user}</a>',
            entry.render({
                # 'request': self.build_request(user=user),
                'user': user,
            }),
        )

        # ---
        creme_children = [*CremeEntry().children]

        for child in creme_children:
            if isinstance(child, UserContactEntry):
                break
        else:
            self.fail(f'No user entry found in {creme_children}.')

    def test_user_contact_menu_entry02(self):
        user = self.login(is_superuser=False)

        self.assertHTMLEqual(
            f'<span class="ui-creme-navigation-text-entry forbidden">{user}</span>',
            UserContactEntry().render({
                # 'request': self.build_request(user=user),
                'user': user,
            }),
        )
