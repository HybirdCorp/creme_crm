from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.forms.widgets import TextInput
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.forms.widgets import Label
from creme.creme_core.gui.quick_forms import quickform_registry
from creme.creme_core.models import Relation
from creme.persons.constants import REL_SUB_EMPLOYED_BY

from ..base import (
    Contact,
    Organisation,
    _BaseTestCase,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)


@skipIfCustomContact
class ContactQuickFormTestCase(_BaseTestCase):
    @staticmethod
    def _build_quickform_url():
        ct = ContentType.objects.get_for_model(Contact)
        return reverse('creme_core__quick_form', args=(ct.id,))

    def test_quickform01(self):
        "1 Contact."
        user = self.login_as_root_and_get()

        contact_count = Contact.objects.count()
        orga_count = Organisation.objects.count()

        models = {*quickform_registry.models}
        self.assertIn(Contact, models)
        self.assertIn(Organisation, models)

        first_name = 'Faye'
        last_name  = 'Valentine'

        url = self._build_quickform_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            orga_f = response.context['form'].fields['organisation']

        self.assertEqual(
            _('If no organisation is found, a new one will be created.'),
            orga_f.help_text,
        )
        self.assertIsInstance(orga_f.widget, TextInput)
        self.assertFalse(isinstance(orga_f.widget, Label))
        self.assertFalse(orga_f.initial)

        response = self.client.post(
            url,
            data={
                'user':        user.id,
                'first_name':  first_name,
                'last_name':   last_name,
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(contact_count + 1, Contact.objects.count())
        self.assertEqual(orga_count,        Organisation.objects.count())
        self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)

    @skipIfCustomOrganisation
    def test_quickform02(self):
        "1 Contact & 1 Organisation created."
        user = self.login_as_persons_user(creatable_models=[Contact, Organisation])
        count = Contact.objects.count()
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        orga_name = 'Bebop'
        self.assertFalse(Organisation.objects.filter(name=orga_name).exists())
        # Not viewable
        existing_orga = Organisation.objects.create(user=self.get_root_user(), name=orga_name)

        first_name = 'Faye'
        last_name = 'Valentine'
        response = self.client.post(
            self._build_quickform_url(),
            data={
                'user':         user.id,
                'first_name':   first_name,
                'last_name':    last_name,
                'organisation': orga_name,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(count + 1, Contact.objects.count())

        orgas = Organisation.objects.filter(name=orga_name)
        self.assertEqual(2, len(orgas))

        created_orga = next(o for o in orgas if o != existing_orga)
        contact = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertHaveRelation(subject=contact, type=REL_SUB_EMPLOYED_BY, object=created_orga)

    @skipIfCustomOrganisation
    def test_quickform03(self):
        "1 Contact created and link with an existing Organisation"
        user = self.login_as_persons_user(creatable_models=[Contact, Organisation])
        count = Contact.objects.count()
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        orga_name = 'Bebop'
        self.assertFalse(Organisation.objects.filter(name=orga_name))

        create_orga = partial(Organisation.objects.create, name=orga_name)
        orga1 = create_orga(user=user)
        orga2 = create_orga(user=self.get_root_user())  # This one cannot be seen by user

        first_name = 'Faye'
        last_name = 'Valentine'
        response = self.client.post(
            self._build_quickform_url(),
            data={
                'user':         user.id,
                'first_name':   first_name,
                'last_name':    last_name,
                'organisation': orga_name,
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(count + 1, Contact.objects.count())
        self.assertEqual(2, Organisation.objects.filter(name=orga_name).count())

        contact = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertHaveRelation(subject=contact, type=REL_SUB_EMPLOYED_BY, object=orga1)
        self.assertHaveNoRelation(subject=contact, type=REL_SUB_EMPLOYED_BY, object=orga2)

    def test_quickform04(self):
        "No permission to create Organisation."
        user = self.login_as_persons_user(creatable_models=[Contact])  # <== not 'Organisation'
        self.add_credentials(user.role, all=['VIEW', 'LINK'])

        orga_name = 'Bebop'
        self.assertFalse(Organisation.objects.filter(name=orga_name).exists())

        contact_count = Contact.objects.count()
        orga_count = Organisation.objects.count()

        url = self._build_quickform_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            orga_f = response1.context['form'].fields['organisation']

        self.assertEqual(
            _('Enter the name of an existing Organisation.'),
            str(orga_f.help_text),
        )

        # ---
        response2 = self.client.post(
            url,
            data={
                'user':         user.id,
                'first_name':   'Faye',
                'last_name':    'Valentine',
                'organisation': orga_name,
            },
        )
        self.assertFormError(
            response2.context['form'],
            field='organisation',
            errors=_('You are not allowed to create an Organisation.'),
        )
        self.assertEqual(contact_count, Contact.objects.count())
        self.assertEqual(orga_count, Organisation.objects.count())

    def test_quickform05(self):
        "No permission to link Organisation"
        user = self.login_as_persons_user(creatable_models=[Contact])
        self.add_credentials(user.role, all=['VIEW'])
        self.add_credentials(user.role, all=['LINK'], model=Contact)

        orga_count = Organisation.objects.count()

        url = self._build_quickform_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            orga_f = response.context['form'].fields['organisation']

        self.assertIsInstance(orga_f.widget, Label)
        self.assertFalse(str(orga_f.help_text))
        self.assertEqual(
            _('You are not allowed to link with an Organisation'),
            orga_f.initial,
        )

        first_name = 'Faye'
        last_name = 'Valentine'
        response = self.client.post(
            url,
            data={
                'user':           user.id,
                'first_name':     first_name,
                'last_name':      last_name,
                'organisation':   'Bebop',
            },
        )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(orga_count, Organisation.objects.count())
        self.assertFalse(Relation.objects.filter(subject_entity=contact))

    def test_quickform06(self):
        "No permission to link Contact in general."
        user = self.login_as_persons_user(creatable_models=[Contact, Organisation])
        self.add_credentials(user.role, all=['VIEW'])
        self.add_credentials(user.role, all=['LINK'], model=Organisation)

        response = self.assertGET200(self._build_quickform_url())

        with self.assertNoException():
            orga_f = response.context['form'].fields['organisation']

        self.assertIsInstance(orga_f.widget, Label)
        self.assertEqual(
            _('You are not allowed to link with a Contact'),
            orga_f.initial,
        )

    def test_quickform07(self):
        "No permission to link Contact with a specific owner."
        user = self.login_as_persons_user(creatable_models=[Contact, Organisation])
        self.add_credentials(user.role, all=['VIEW'])
        self.add_credentials(user.role, all=['LINK'], model=Organisation)
        self.add_credentials(user.role, own=['LINK'], model=Contact)

        url = self._build_quickform_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            orga_f = response1.context['form'].fields['organisation']

        self.assertIsNone(orga_f.initial)

        # ---
        first_name = 'Faye'
        last_name = 'Valentine'
        data = {
            'user':       self.get_root_user().id,
            'first_name': 'Faye',
            'last_name':  'Valentine',
        }
        response2 = self.client.post(url, data={**data, 'organisation': 'Bebop'})
        self.assertFormError(
            response2.context['form'],
            field=None,
            errors=_(
                'You are not allowed to link with the «{models}» of this user.'
            ).format(models=_('Contacts')),
        )

        # ---
        self.assertNoFormError(self.client.post(url, data=data))
        self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)

    @skipIfCustomOrganisation
    def test_quickform08(self):
        "Multiple Organisations found."
        user = self.login_as_root_and_get()

        orga_name = 'Bebop'
        create_orga = partial(Organisation.objects.create, name=orga_name)
        create_orga(user=user)
        create_orga(user=self.create_user())

        response = self.client.post(
            self._build_quickform_url(),
            data={
                'user':         user.id,
                'first_name':   'Faye',
                'last_name':    'Valentine',
                'organisation': orga_name,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='organisation',
            errors=_('Several Organisations with this name have been found.'),
        )

    @skipIfCustomOrganisation
    def test_quickform09(self):
        "Multiple Organisations found, only one linkable (so we use it)."
        user = self.login_as_persons_user(creatable_models=[Contact, Organisation])
        self.add_credentials(user.role, all=['VIEW'], own=['LINK'])

        orga_name = 'Bebop'
        create_orga = partial(Organisation.objects.create, name=orga_name)
        orga1 = create_orga(user=user)
        create_orga(user=self.get_root_user())  # Cannot be linked by user

        first_name = 'Faye'
        last_name = 'Valentine'
        response = self.client.post(
            self._build_quickform_url(),
            data={
                'user':         user.id,
                'first_name':   first_name,
                'last_name':    last_name,
                'organisation': orga_name,
            },
        )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertHaveRelation(subject=contact, type=REL_SUB_EMPLOYED_BY, object=orga1)

    @skipIfCustomOrganisation
    def test_quickform10(self):
        "Multiple Organisations found, but none of them is linkable."
        user = self.login_as_persons_user(creatable_models=[Contact, Organisation])
        self.add_credentials(user.role, all=['VIEW'], own=['LINK'])

        orga_name = 'Bebop'
        other_user = self.get_root_user()

        for i in range(2):
            Organisation.objects.create(user=other_user, name=orga_name)

        response = self.client.post(
            self._build_quickform_url(),
            data={
                'user':         user.id,
                'first_name':   'Faye',
                'last_name':    'Valentine',
                'organisation': orga_name,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='organisation', errors=_('No linkable Organisation found.'),
        )

    def test_quickform11(self):
        "Have to create an Organisations, but can not link to it."
        user = self.login_as_persons_user(creatable_models=[Contact, Organisation])
        self.add_credentials(user.role, all=['VIEW'], own=['LINK'])
        self.add_credentials(user.role, all=['LINK'], model=Contact)

        orga_name = 'Bebop'
        self.assertFalse(Organisation.objects.filter(name=orga_name).exists())

        response = self.client.post(
            self._build_quickform_url(),
            data={
                'user':         self.get_root_user().id,
                'first_name':   'Faye',
                'last_name':    'Valentine',
                'organisation': orga_name,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_(
                'You are not allowed to link with the «{models}» of this user.'
            ).format(models=_('Organisations')),
        )

    @skipIfCustomOrganisation
    def test_quickform12(self):
        "Multiple Organisations found, only one is not deleted (so we use it)."
        user = self.login_as_root_and_get()

        orga_name = 'Bebop'
        create_orga = partial(Organisation.objects.create, name=orga_name, user=user)
        create_orga(is_deleted=True)
        orga2 = create_orga()

        first_name = 'Faye'
        last_name = 'Valentine'
        response = self.client.post(
            self._build_quickform_url(),
            data={
                'user':         user.id,
                'first_name':   first_name,
                'last_name':    last_name,
                'organisation': orga_name,
            },
        )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(
            Contact, first_name=first_name, last_name=last_name,
        )
        self.assertHaveRelation(subject=contact, type=REL_SUB_EMPLOYED_BY, object=orga2)
