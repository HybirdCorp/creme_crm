from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.gui.field_printers import field_printer_registry
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import EntityFilter, HeaderFilter, UserRole

from .. import constants  # workflow
from ..constants import UUID_FIRST_CONTACT
from ..models import Sector
from .base import Contact, Organisation, _PersonsTestCase


class PersonsAppTestCase(_PersonsTestCase):
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

    def test_populated_orga_uuid(self):
        first_orga = Organisation.objects.order_by('id').first()
        self.assertIsNotNone(first_orga)
        self.assertTrue(first_orga.is_managed)
        self.assertUUIDEqual(constants.UUID_FIRST_ORGA, first_orga.uuid)

    def test_populated_contact_uuid(self):
        first_contact = Contact.objects.order_by('id').first()
        self.assertIsNotNone(first_contact)

        user = first_contact.is_user
        self.assertIsNotNone(user)

        self.assertUUIDEqual(UUID_FIRST_CONTACT, first_contact.uuid)

    def test_fk_user_printer(self):
        user = self.create_user()

        deunan = Contact.objects.create(user=user, first_name='Deunan', last_name='Knut')
        kirika = user.linked_contact

        render_field = partial(field_printer_registry.get_field_value, instance=deunan)
        self.assertEqual(
            f'<a href="{kirika.get_absolute_url()}">Kirika Y.</a>',
            render_field(field_name='user', user=user, tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(
            f'<a href="{kirika.get_absolute_url()}" target="_blank">Kirika Y.</a>',
            render_field(field_name='user', user=user, tag=ViewTag.HTML_FORM),
        )
        self.assertEqual(
            '<em>{}</em>'.format(pgettext('persons-is_user', 'None')),
            render_field(field_name='is_user', user=user, tag=ViewTag.HTML_DETAIL),
        )

        self.assertEqual(
            str(user),
            render_field(field_name='user', user=user, tag=ViewTag.TEXT_PLAIN),
        )

    def test_fk_user_printer__team(self):
        user = self.create_user()

        eswat = self.create_team('eswat')
        deunan = Contact.objects.create(user=eswat, first_name='Deunan', last_name='Knut')

        self.assertEqual(
            str(eswat),
            field_printer_registry.get_field_value(
                instance=deunan, field_name='user', user=user, tag=ViewTag.HTML_DETAIL,
            ),
        )

    def test_fk_user_printer__not_viewable(self):
        "Cannot see the contact => fallback to user + no <a>."
        user = self.login_as_persons_user()
        other_user = self.get_root_user()
        self.add_credentials(user.role, own=['VIEW'])

        viewable_contact = user.linked_contact
        self.assertEqual(user, viewable_contact.user)

        forbidden_contact = other_user.linked_contact
        self.assertEqual(other_user, forbidden_contact.user)

        render_field = partial(
            field_printer_registry.get_field_value,
            user=user, field_name='user', tag=ViewTag.HTML_DETAIL,
        )
        self.assertHTMLEqual(
            f'<a href="{viewable_contact.get_absolute_url()}">'
            f'Kirika Y.'
            f'</a>',
            render_field(instance=viewable_contact),
        )
        self.assertEqual(
            _('{first_name} {last_name}.').format(
                first_name=other_user.first_name,
                last_name=other_user.last_name[0],
            ),
            render_field(instance=forbidden_contact),
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
