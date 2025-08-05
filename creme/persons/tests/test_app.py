# from functools import partial
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.menu import CremeEntry
from creme.creme_core.models import EntityFilter, HeaderFilter, UserRole
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from .. import bricks, constants  # workflow
from ..deletors import ContactDeletor, OrganisationDeletor
from ..menu import UserContactEntry
from ..models import Sector
from .base import (
    Contact,
    Organisation,
    _BaseTestCase,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)


class PersonsAppTestCase(BrickTestCaseMixin, _BaseTestCase):
    def test_core_populate(self):
        role = self.get_object_or_fail(UserRole, name=_('Regular user'))
        self.assertIn('persons', role.allowed_apps)

        get_ct = ContentType.objects.get_for_model
        self.assertTrue(role.creatable_ctypes.filter(id=get_ct(Contact).id).exists())
        self.assertTrue(role.creatable_ctypes.filter(id=get_ct(Organisation).id).exists())
        self.assertFalse(role.creatable_ctypes.filter(id=get_ct(Sector).id).exists())

        self.assertTrue(role.exportable_ctypes.filter(id=get_ct(Contact).id).exists())
        self.assertTrue(role.exportable_ctypes.filter(id=get_ct(Organisation).id).exists())
        self.assertFalse(role.exportable_ctypes.filter(id=get_ct(Sector).id).exists())

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
        self.login_as_root()
        response = self.assertGET200(reverse('creme_config__portal'))
        self.get_brick_node(
            self.get_html_tree(response.content),
            brick=bricks.ManagedOrganisationsBrick,
        )

    # def test_transform_target_into_prospect(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     create_orga = partial(Organisation.objects.create, user=user)
    #     source = create_orga(name='Source')
    #     target = create_orga(name='Target')
    #
    #     workflow.transform_target_into_prospect(source, target, user)
    #     self.assertHaveRelation(subject=target, type=constants.REL_SUB_PROSPECT, object=source)
    #
    #     # Do not create duplicate
    #     workflow.transform_target_into_prospect(source, target, user)
    #     self.assertHaveRelation(subject=target, type=constants.REL_SUB_PROSPECT, object=source)

    # def test_transform_target_into_customer(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     create_orga = partial(Organisation.objects.create, user=user)
    #     source = create_orga(name='Source')
    #     target = create_orga(name='Target')
    #
    #     workflow.transform_target_into_customer(source, target, user)
    #     type_id = constants.REL_SUB_CUSTOMER_SUPPLIER
    #     self.assertHaveRelation(subject=target, type=type_id, object=source)
    #
    #     # Do not create duplicate
    #     workflow.transform_target_into_customer(source, target, user)
    #     self.assertHaveRelation(subject=target, type=type_id, object=source)

    def test_user_contact_menu_entry01(self):
        user = self.login_as_persons_user()
        url = user.linked_contact.get_absolute_url()
        self.assertEqual(url, user.get_absolute_url())

        self.add_credentials(user.role, all=['VIEW'])

        entry = UserContactEntry()
        self.assertEqual('persons-user_contact', entry.id)
        self.assertEqual(_("*User's contact*"), entry.label)
        self.assertHTMLEqual(
            f'<a href="{url}">{user}</a>',
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
        user = self.login_as_standard()

        self.assertHTMLEqual(
            f'<span class="ui-creme-navigation-text-entry forbidden">{user}</span>',
            UserContactEntry().render({
                # 'request': self.build_request(user=user),
                'user': user,
            }),
        )

    def test_user_contact_menu_entry03(self):
        "Is staff."
        user = self.login_as_super(is_staff=True)
        self.assertFalse(user.get_absolute_url())

        self.assertHTMLEqual(
            f'<span class="ui-creme-navigation-text-entry forbidden">{user}</span>',
            UserContactEntry().render({
                'user': user,
            }),
        )

    @skipIfCustomContact
    def test_contact_deletor(self):
        user = self.get_root_user()
        contact1 = Contact.objects.create(user=user, first_name='John', last_name='Doe')
        deletor = ContactDeletor()
        with self.assertNoException():
            deletor.check_permissions(user=user, entity=contact1)

        # ---
        other_user = self.create_user()
        with self.assertRaises(ConflictError) as cm:
            deletor.check_permissions(user=user, entity=other_user.linked_contact)

        self.assertEqual(
            _('A user is associated with this contact.'),
            str(cm.exception),
        )

    @skipIfCustomOrganisation
    def test_organisation_deletor(self):
        user = self.get_root_user()
        orga = Organisation.objects.create(user=user, name='Acme')
        deletor = OrganisationDeletor()

        with self.assertNoException():
            deletor.check_permissions(user=user, entity=orga)

    @skipIfCustomOrganisation
    def test_organisation_deletor__one_managed(self):
        deletor = OrganisationDeletor()
        managed = Organisation.objects.get(is_managed=True)

        with self.assertRaises(ConflictError) as cm:
            deletor.check_permissions(user=self.get_root_user(), entity=managed)

        self.assertEqual(
            _('The last managed organisation cannot be deleted.'),
            str(cm.exception),
        )

    @skipIfCustomOrganisation
    def test_organisation_deletor__several_managed(self):
        user = self.get_root_user()
        orga = Organisation.objects.create(user=user, name='Acme', is_managed=True)
        deletor = OrganisationDeletor()

        with self.assertNoException():
            deletor.check_permissions(user=user, entity=orga)
