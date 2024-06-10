from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.forms import IntegerField
from django.urls import reverse
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core.models import CustomField, RelationType
from creme.opportunities.constants import REL_SUB_LINKED_CONTACT
from creme.persons.constants import REL_SUB_EMPLOYED_BY
from creme.persons.models import Position
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .base import (
    Contact,
    OpportunitiesBaseTestCase,
    Opportunity,
    Organisation,
    skipIfCustomOpportunity,
)


@skipIfCustomOpportunity
@skipIfCustomContact
@skipIfCustomOrganisation
class RelatedContactTestCase(OpportunitiesBaseTestCase):
    @staticmethod
    def _build_url(opp):
        return reverse('opportunities__create_related_contact', args=(opp.id,))

    def test_create_related_contact01(self):
        "Not employed by the target Organisation."
        user = self.login_as_root_and_get()
        opp, target, emitter = self._create_opportunity_n_organisations(user=user)

        url = self._build_url(opp)
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Create a contact linked to «{opportunity}»').format(opportunity=opp),
            context.get('title'),
        )

        with self.assertNoException():
            employed_field = context['form'].fields['is_employed']

        self.assertEqual(
            _('Is employed by «{}»?').format(target),
            employed_field.label,
        )

        first_name = 'Faye'
        last_name  = 'Valentine'
        response = self.client.post(
            url,
            data={
                'user': user.id,
                'first_name': first_name,
                'last_name': last_name,
            },
        )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertIsNone(contact.position)
        self.assertFalse(contact.full_position)
        self.assertFalse(contact.email)
        self.assertFalse(contact.phone)
        self.assertFalse(contact.mobile)
        self.assertHaveRelation(subject=contact, type=REL_SUB_LINKED_CONTACT, object=opp)
        self.assertHaveNoRelation(subject=contact, type=REL_SUB_EMPLOYED_BY, object=target)

    def test_create_related_contact02(self):
        "Employed by the target Organisation."
        user = self.login_as_root_and_get()
        opp, target, emitter = self._create_opportunity_n_organisations(user=user)

        first_name = 'Faye'
        last_name  = 'Valentine'
        position = Position.objects.first()
        full_position = 'Rogue pilot'
        email = 'faye.valentine@bebop.mrs'
        phone = '123654'
        mobile = '779654'
        response = self.client.post(
            self._build_url(opp),
            data={
                'user': user.id,
                'first_name': first_name,
                'last_name': last_name,

                'position': position.id,
                'full_position': full_position,

                'email': email,
                'phone': phone,
                'mobile': mobile,

                'is_employed': 'on',
            },
        )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertEqual(position, contact.position)
        self.assertEqual(full_position, contact.full_position)
        self.assertEqual(email, contact.email)
        self.assertEqual(phone, contact.phone)
        self.assertEqual(mobile, contact.mobile)
        self.assertHaveRelation(subject=contact, type=REL_SUB_EMPLOYED_BY, object=target)

    def test_create_related_contact03(self):
        "Target is a Contact."
        user = self.login_as_root_and_get()
        opp, target, emitter = self._create_opportunity_n_organisations(user=user, contact=True)

        url = self._build_url(opp)
        response = self.assertGET200(url)
        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('is_employed', fields)

        first_name = 'Faye'
        last_name  = 'Valentine'
        response = self.client.post(
            url,
            data={
                'user': user.id,
                'first_name': first_name,
                'last_name': last_name,
                'is_employed': 'on',  # Should not be used
            },
        )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertHaveNoRelation(contact, type=REL_SUB_EMPLOYED_BY, object=target)

    def test_create_related_contact04(self):
        "No credentials to create the Contact."
        user = self.login_as_standard(
            allowed_apps=('persons', 'opportunities'),
            creatable_models=[Organisation, Opportunity],
        )
        self.add_credentials(user.role, own=['VIEW', 'CHANGE', 'LINK'])

        opp = self._create_opportunity_n_organisations(user=user)[0]
        self.assertContains(
            self.client.get(self._build_url(opp)),
            _('You are not allowed to create: {}').format(Contact._meta.verbose_name),
            status_code=403,
            html=True,
        )

    @parameterized.expand([
        ([Opportunity, Contact],      False),  # No credentials to link the Organisation.
        ([Opportunity, Organisation], False),  # No credentials to link the (future) Contact.
        ([Contact, Organisation],     True),   # No credentials to link the opportunity.
    ])
    def test_create_related_contact_no_link(self, allowed_models, error_403):
        "No credentials to link the Organisation."
        user = self.login_as_standard(
            allowed_apps=('persons', 'opportunities'),
            creatable_models=[Organisation, Contact, Opportunity],
        )

        for model in (Opportunity, Organisation, Contact):
            self.add_credentials(
                user.role,
                own=['VIEW', 'CHANGE', 'LINK'] if model in allowed_models else ['VIEW', 'CHANGE'],
                model=model,
            )

        opp = self._create_opportunity_n_organisations(user=user)[0]
        url = self._build_url(opp)

        if error_403:
            self.assertGET403(url)
        else:
            response = self.assertGET200(url)

            with self.assertNoException():
                fields = response.context['form'].fields

            self.assertNotIn('is_employed', fields)

    def test_create_related_contact_customfields(self):
        "Required CustomFields."
        user = self.login_as_root_and_get()

        create_cf = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(Contact),
        )
        cf1 = create_cf(field_type=CustomField.STR, name='Dogtag')
        cf2 = create_cf(field_type=CustomField.INT, name='Eva number', is_required=True)

        opp, target, emitter = self._create_opportunity_n_organisations(user=user)

        response = self.assertGET200(self._build_url(opp))

        fields = response.context['form'].fields
        self.assertNotIn(f'custom_field-{cf1.id}', fields)

        cf2_f = fields.get(f'custom_field-{cf2.id}')
        self.assertIsInstance(cf2_f, IntegerField)
        self.assertTrue(cf2_f.required)

    def test_create_related_contact_error(self):
        "The relation type is disabled."
        user = self.login_as_root_and_get()
        opp = self._create_opportunity_n_organisations(user=user)[0]

        rtype = self.get_object_or_fail(RelationType, id=REL_SUB_LINKED_CONTACT)
        rtype.enabled = False
        rtype.save()

        try:
            self.assertGET409(self._build_url(opp))
        finally:
            rtype.enabled = True
            rtype.save()
