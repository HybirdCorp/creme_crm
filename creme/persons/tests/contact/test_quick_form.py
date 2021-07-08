# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.forms.widgets import TextInput
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.forms.widgets import Label
from creme.creme_core.gui.quick_forms import quickforms_registry
from creme.creme_core.models import Relation, SetCredentials
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
        user = self.login()

        contact_count = Contact.objects.count()
        orga_count = Organisation.objects.count()

        models = {*quickforms_registry.models}
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
        user = self.login(is_superuser=False, creatable_models=[Contact, Organisation])
        count = Contact.objects.count()

        create_sc = partial(
            SetCredentials.objects.create,
            role=self.role, set_type=SetCredentials.ESET_OWN,
        )
        create_sc(value=EntityCredentials.VIEW)
        create_sc(value=EntityCredentials.LINK)

        orga_name = 'Bebop'
        self.assertFalse(Organisation.objects.filter(name=orga_name).exists())
        # Not viewable
        existing_orga = Organisation.objects.create(user=self.other_user, name=orga_name)

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
        self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, created_orga)

    @skipIfCustomOrganisation
    def test_quickform03(self):
        "1 Contact created and link with an existing Organisation"
        user = self.login(is_superuser=False, creatable_models=[Contact, Organisation])
        count = Contact.objects.count()

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )

        orga_name = 'Bebop'
        self.assertFalse(Organisation.objects.filter(name=orga_name))

        create_orga = partial(Organisation.objects.create, name=orga_name)
        orga1 = create_orga(user=user)
        orga2 = create_orga(user=self.other_user)  # This one cannot be seen by user

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
        self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, orga1)
        self.assertRelationCount(0, contact, REL_SUB_EMPLOYED_BY, orga2)

    def test_quickform04(self):
        "No permission to create Organisation."
        user = self.login(is_superuser=False, creatable_models=[Contact])  # <== not 'Organisation'

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        orga_name = 'Bebop'
        self.assertFalse(Organisation.objects.filter(name=orga_name).exists())

        contact_count = Contact.objects.count()
        orga_count = Organisation.objects.count()

        url = self._build_quickform_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            orga_f = response.context['form'].fields['organisation']

        self.assertEqual(
            _('Enter the name of an existing Organisation.'),
            str(orga_f.help_text),
        )

        response = self.client.post(
            url,
            data={
                'user':         user.id,
                'first_name':   'Faye',
                'last_name':    'Valentine',
                'organisation': orga_name,
            },
        )
        self.assertFormError(
            response, 'form', 'organisation',
            _('You are not allowed to create an Organisation.'),
        )
        self.assertEqual(contact_count, Contact.objects.count())
        self.assertEqual(orga_count, Organisation.objects.count())

    def test_quickform05(self):
        "No permission to link Organisation"
        user = self.login(is_superuser=False, creatable_models=[Contact])

        create_sc = partial(
            SetCredentials.objects.create,
            role=self.role, set_type=SetCredentials.ESET_ALL,
        )
        create_sc(value=EntityCredentials.VIEW)
        create_sc(value=EntityCredentials.LINK, ctype=Contact)

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
        "No permission to link Contact in general"
        self.login(is_superuser=False, creatable_models=[Contact, Organisation])

        create_sc = partial(
            SetCredentials.objects.create,
            role=self.role, set_type=SetCredentials.ESET_ALL,
        )
        create_sc(value=EntityCredentials.VIEW)
        create_sc(value=EntityCredentials.LINK, ctype=Organisation)

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
        self.login(is_superuser=False, creatable_models=[Contact, Organisation])

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(
            value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL,
        )
        create_sc(
            value=EntityCredentials.LINK, set_type=SetCredentials.ESET_ALL,
            ctype=Organisation,
        )
        create_sc(
            value=EntityCredentials.LINK, set_type=SetCredentials.ESET_OWN,
            ctype=Contact,
        )

        url = self._build_quickform_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            orga_f = response.context['form'].fields['organisation']

        self.assertIsNone(orga_f.initial)

        first_name = 'Faye'
        last_name = 'Valentine'
        data = {
            'user':       self.other_user.id,
            'first_name': 'Faye',
            'last_name':  'Valentine',
        }
        response = self.client.post(url, data={**data, 'organisation': 'Bebop'})
        self.assertFormError(
            response, 'form', None,
            _('You are not allowed to link with the «{models}» of this user.').format(
                models=_('Contacts'),
            )
        )

        self.assertNoFormError(self.client.post(url, data=data))
        self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)

    @skipIfCustomOrganisation
    def test_quickform08(self):
        "Multiple Organisations found."
        user = self.login()

        orga_name = 'Bebop'
        create_orga = partial(Organisation.objects.create, name=orga_name)
        create_orga(user=user)
        create_orga(user=self.other_user)

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
            response, 'form', 'organisation',
            _('Several Organisations with this name have been found.'),
        )

    @skipIfCustomOrganisation
    def test_quickform09(self):
        "Multiple Organisations found, only one linkable (so we use it)."
        user = self.login(is_superuser=False, creatable_models=[Contact, Organisation])

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)
        create_sc(value=EntityCredentials.LINK, set_type=SetCredentials.ESET_OWN)

        orga_name = 'Bebop'
        create_orga = partial(Organisation.objects.create, name=orga_name)
        orga1 = create_orga(user=user)
        create_orga(user=self.other_user)  # Cannot be linked by user

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
        self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, orga1)

    @skipIfCustomOrganisation
    def test_quickform10(self):
        "Multiple Organisations found, but none of them is linkable."
        user = self.login(is_superuser=False, creatable_models=[Contact, Organisation])

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)
        create_sc(value=EntityCredentials.LINK, set_type=SetCredentials.ESET_OWN)

        orga_name = 'Bebop'

        for i in range(2):
            Organisation.objects.create(user=self.other_user, name=orga_name)

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
            response, 'form', 'organisation', _('No linkable Organisation found.'),
        )

    def test_quickform11(self):
        "Have to create an Organisations, but can not link to it."
        self.login(is_superuser=False, creatable_models=[Contact, Organisation])

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)
        create_sc(value=EntityCredentials.LINK, set_type=SetCredentials.ESET_ALL, ctype=Contact)
        create_sc(value=EntityCredentials.LINK, set_type=SetCredentials.ESET_OWN)

        orga_name = 'Bebop'
        self.assertFalse(Organisation.objects.filter(name=orga_name).exists())

        response = self.client.post(
            self._build_quickform_url(),
            data={
                'user':         self.other_user.id,
                'first_name':   'Faye',
                'last_name':    'Valentine',
                'organisation': orga_name,
            },
        )
        self.assertFormError(
            response, 'form', None,
            _(
                'You are not allowed to link with the «{models}» of this user.'
            ).format(models=_('Organisations'))
        )

    @skipIfCustomOrganisation
    def test_quickform12(self):
        "Multiple Organisations found, only one is not deleted (so we use it)."
        user = self.login()

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
        self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, orga2)


@skipIfCustomContact
class ContactNamesEditionTestCase(_BaseTestCase):
    @staticmethod
    def _build_url(contact):
        return reverse('persons__edit_contact_names', args=(contact.id,))

    def test_edit01(self):
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_OWN,
        )

        contact = Contact.objects.create(user=user, first_name='Fay', last_name='Valentin')

        url = self._build_url(contact)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('first_name', fields)
        self.assertIn('last_name',  fields)
        self.assertNotIn('position', fields)

        first_name = contact.first_name + 'e'
        last_name = contact.last_name + 'e'
        response = self.client.post(
            url,
            data={
                'first_name': first_name,
                'last_name': last_name,
            },
        )
        self.assertNoFormError(response)

        contact = self.refresh(contact)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)

    def test_edit02(self):
        "No permission."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,  # No EntityCredentials.CHANGE
            set_type=SetCredentials.ESET_OWN,
        )

        contact = Contact.objects.create(user=user, first_name='Fay', last_name='Valentin')
        self.assertGET403(self._build_url(contact))
