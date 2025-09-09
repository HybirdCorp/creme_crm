from functools import partial

from django.core.exceptions import ValidationError
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.gui.field_printers import field_printer_registry
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CremeUser,
    FieldsConfig,
    Relation,
    RelationType,
)
from creme.creme_core.tests.base import skipIfCustomUser
from creme.documents.tests.base import skipIfCustomDocument
from creme.persons.constants import (
    REL_OBJ_EMPLOYED_BY,
    REL_SUB_EMPLOYED_BY,
    REL_SUB_MANAGES,
    UUID_FIRST_CONTACT,
)
from creme.persons.forms.address import AddressesGroup
from creme.persons.models import Civility, Position, Sector

from ..base import (
    Address,
    Contact,
    Document,
    Organisation,
    _BaseTestCase,
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)


@skipIfCustomContact
class ContactTestCase(_BaseTestCase):
    @staticmethod
    def _build_addrelated_url(orga_id, rtype_id=None):
        kwargs = {'orga_id': orga_id}

        if rtype_id:
            kwargs['rtype_id'] = rtype_id

        return reverse('persons__create_related_contact', kwargs=kwargs)

    def test_empty_fields(self):
        user = self.login_as_root_and_get()

        with self.assertNoException():
            contact = Contact.objects.create(user=user, last_name='Spiegel')

        self.assertEqual('', contact.first_name)
        self.assertEqual('', contact.description)
        self.assertEqual('', contact.skype)
        self.assertEqual('', contact.phone)
        self.assertEqual('', contact.mobile)
        self.assertEqual('', contact.email)
        self.assertEqual('', contact.url_site)
        self.assertEqual('', contact.full_position)

    def test_unicode(self):
        first_name = 'Spike'
        last_name  = 'Spiegel'
        build_contact = partial(Contact, last_name=last_name)
        self.assertEqual(last_name, str(build_contact()))
        self.assertEqual(last_name, str(build_contact(first_name='')))
        self.assertEqual(
            _('{first_name} {last_name}').format(
                first_name=first_name,
                last_name=last_name,
            ),
            str(build_contact(first_name=first_name))
        )

        captain = Civility.objects.create(title='Captain')  # No shortcut
        self.assertEqual(
            _('{first_name} {last_name}').format(
                first_name=first_name,
                last_name=last_name,
            ),
            str(build_contact(first_name=first_name, civility=captain))
        )

        captain.shortcut = shortcut = 'Cpt'
        captain.save()
        self.assertEqual(
            _('{civility} {first_name} {last_name}').format(
                civility=shortcut,
                first_name=first_name,
                last_name=last_name,
            ),
            str(build_contact(first_name=first_name, civility=captain))
        )

    def test_populated_contact_uuid(self):
        first_contact = Contact.objects.order_by('id').first()
        self.assertIsNotNone(first_contact)

        user = first_contact.is_user
        self.assertIsNotNone(user)

        self.assertUUIDEqual(UUID_FIRST_CONTACT, first_contact.uuid)

    def test_clean_unique_user_email(self):
        user1 = self.create_user(0)
        user2 = self.create_user(1)

        contact2 = user2.linked_contact
        contact2.email = user1.email

        with self.assertRaises(ValidationError) as cm:
            contact2.clean()

        self.assertValidationError(
            cm.exception,
            messages={
                'email': _(
                    'This Contact is related to a user and an active user '
                    'already uses this email address.'
                ),
            },
        )

        # Ignore inactive ---
        user1.is_active = False
        user1.save()

        with self.assertNoException():
            contact2.clean()

        # Ignore own user ---
        contact2.email = user2.email

        with self.assertNoException():
            contact2.clean()

    def test_createview(self):
        user = self.login_as_root_and_get()

        url = reverse('persons__create_contact')
        self.assertGET200(url)

        count = Contact.objects.count()
        first_name = 'Spike'
        last_name  = 'Spiegel'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':       user.pk,
                'first_name': first_name,
                'last_name':  last_name,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(count + 1, Contact.objects.count())

        contact = self.get_object_or_fail(Contact, first_name=first_name)
        self.assertEqual(last_name,  contact.last_name)
        self.assertIsNone(contact.billing_address)
        self.assertIsNone(contact.shipping_address)

        self.assertRedirects(response, contact.get_absolute_url())

    @skipIfCustomAddress
    def test_createview_with_addresses(self):
        user = self.login_as_root_and_get()

        first_name = 'Spike'
        b_address = 'In the Bebop.'
        s_address = 'In the Bebop (bis).'

        url = reverse('persons__create_contact')
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'persons/forms/addresses-block.html')

        with self.assertNoException():
            fields = response1.context['form'].fields

        self.assertIn('billing_address-address', fields)
        self.assertIn('shipping_address-address', fields)
        self.assertNotIn('billing_address-name', fields)
        self.assertNotIn('shipping_address-name', fields)

        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user':       user.pk,
                'first_name': first_name,
                'last_name':  'Spiegel',

                'billing_address-address':  b_address,
                'shipping_address-address': s_address,
            },
        )
        self.assertNoFormError(response2)

        contact = self.get_object_or_fail(Contact, first_name=first_name)
        billing_address = contact.billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(b_address,            billing_address.address)
        self.assertEqual(_('Billing address'), billing_address.name)

        shipping_address = contact.shipping_address
        self.assertIsNotNone(shipping_address)
        self.assertEqual(s_address,             shipping_address.address)
        self.assertEqual(_('Shipping address'), shipping_address.name)

        self.assertContains(response2, b_address)
        self.assertContains(response2, s_address)

    @skipIfCustomAddress
    def test_createview_with_addresses_errors01(self):
        """Validation error (custom model validation on Address
        -- for swapped or hooked models) ; field error.
        """
        user = self.login_as_root_and_get()
        error_msg = 'Please fill the city too'

        def clean_address(this):
            if this.address and not this.city:
                raise ValidationError({
                    'city': ValidationError(error_msg),
                })

        original_clean = Address.clean

        url = reverse('persons__create_contact')

        first_name = 'Spike'
        last_name = 'Spiegel'
        b_address = '7 Corgy street'
        b_city = 'Mars City'
        data = {
            'user': user.pk,
            'first_name': first_name,
            'last_name': last_name,

            'billing_address-address': b_address,
            # 'shipping_address-address': ...,
        }

        try:
            Address.clean = clean_address

            response1 = self.client.post(url, follow=True, data=data)
            self.assertFormError(
                response1.context['form'],
                field='billing_address-city',
                errors=error_msg,
            )

            # ---
            response2 = self.client.post(
                url,
                follow=True,
                data={
                    **data,

                    'billing_address-city': b_city,
                },
            )
            self.assertNoFormError(response2)
        finally:
            Address.clean = original_clean

        contact = self.get_object_or_fail(Contact, last_name=last_name, first_name=first_name)
        self.assertIsNone(contact.shipping_address)

        billing_address = contact.billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(b_address, billing_address.address)
        self.assertEqual(b_city,    billing_address.city)

    @skipIfCustomAddress
    def test_createview_with_addresses_errors02(self):
        "Validation error (custom model validation...) ; non field-error."
        user = self.login_as_root_and_get()
        error_msg = 'Please fill the city too'

        def clean_address(this):
            if this.address and not this.city:
                raise ValidationError(error_msg)

        original_clean = Address.clean

        try:
            Address.clean = clean_address

            response = self.client.post(
                reverse('persons__create_contact'),
                data={
                    'user': user.pk,
                    'first_name': 'Spike',
                    'last_name': 'Spiegel',

                    'billing_address-address': '7 Corgy street',
                    'shipping_address-address': '8 Corgy street',
                },
            )
            self.assertFormError(
                self.get_form_or_fail(response),
                field=None,
                errors=[
                    _('{address_field}: {error}').format(
                        address_field=field,
                        error=error_msg,
                    ) for field in (_('Billing address'), _('Shipping address'))
                ],
            )
        finally:
            Address.clean = original_clean

    @skipIfCustomAddress
    def test_createview_with_addresses_errors03(self):
        "Custom address which raises field error."
        user = self.login_as_root_and_get()
        error_msg = 'Please fill the city too'

        original_form = AddressesGroup.sub_form_class

        class TestForm(original_form):
            def clean_city(this):
                cleaned = this.cleaned_data
                city = cleaned['city']

                if not city and cleaned['address']:
                    raise ValidationError(error_msg)

                return city

        url = reverse('persons__create_contact')

        first_name = 'Spike'
        last_name = 'Spiegel'
        b_address = '7 Corgy street'
        b_city = 'Mars City'
        data = {
            'user': user.pk,
            'first_name': first_name,
            'last_name': last_name,

            'billing_address-address': b_address,
            # 'shipping_address-address': ...,
        }

        try:
            AddressesGroup.sub_form_class = TestForm

            response1 = self.client.post(url, follow=True, data=data)
            self.assertFormError(
                response1.context['form'],
                field='billing_address-city',
                errors=error_msg,
            )

            # ---
            response2 = self.client.post(
                url,
                follow=True,
                data={
                    **data,

                    'billing_address-city': b_city,
                },
            )
            self.assertNoFormError(response2)
        finally:
            AddressesGroup.sub_form_class = original_form

        contact = self.get_object_or_fail(Contact, last_name=last_name, first_name=first_name)
        self.assertIsNone(contact.shipping_address)

        billing_address = contact.billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(b_address, billing_address.address)
        self.assertEqual(b_city,    billing_address.city)

    def test_editview01(self):
        user = self.login_as_root_and_get()
        first_name = 'Faye'
        contact = Contact.objects.create(
            user=user, first_name=first_name, last_name='Valentine',
        )

        url = contact.get_edit_absolute_url()
        self.assertGET200(url)

        last_name = 'Spiegel'
        response = self.assertPOST200(
            url,
            follow=True,
            data={
                'user':       user.pk,
                'first_name': first_name,
                'last_name':  last_name,
            },
        )

        contact = self.refresh(contact)
        self.assertEqual(last_name, contact.last_name)
        self.assertIsNone(contact.billing_address)
        self.assertIsNone(contact.shipping_address)

        self.assertRedirects(response, contact.get_absolute_url())

    @skipIfCustomAddress
    def test_editview_with_addresses(self):
        "Edit addresses."
        user = self.login_as_root_and_get()

        first_name = 'Faye'
        last_name = 'Valentine'
        b_address_value = 'In the Bebop.'
        self.assertPOST200(
            reverse('persons__create_contact'),
            follow=True,
            data={
                'user':       user.pk,
                'first_name': first_name,
                'last_name':  last_name,

                'billing_address-address':  b_address_value,
                'shipping_address-address': 'In the Bebop. (bis)',
            },
        )
        contact = Contact.objects.get(first_name=first_name)
        billing_address_id  = contact.billing_address_id
        shipping_address_id = contact.shipping_address_id

        url = contact.get_edit_absolute_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            address_f = response.context['form'].fields['billing_address-address']

        self.assertEqual(b_address_value, address_f.initial)

        state = 'Solar system'
        country = 'Mars'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,

                'billing_address-state':    state,
                'shipping_address-country': country,
            },
        ))

        contact = self.refresh(contact)
        self.assertEqual(billing_address_id,  contact.billing_address_id)
        self.assertEqual(shipping_address_id, contact.shipping_address_id)

        self.assertEqual(state,   contact.billing_address.state)
        self.assertEqual(country, contact.shipping_address.country)

    def test_editview_is_user01(self):
        "Contact is a user => sync."
        user = self.login_as_root_and_get()
        contact = self.get_object_or_fail(Contact, is_user=user)

        url = contact.get_edit_absolute_url()
        response = self.assertPOST200(
            url,
            follow=True,
            data={
                'user':      user.id,
                'last_name': contact.last_name,
            },
        )
        form = self.get_form_or_fail(response)
        msg = _('This field is required.')
        self.assertFormError(form, field='first_name', errors=msg)
        self.assertFormError(form, field='email',      errors=msg)

        first_name = contact.first_name.lower()
        self.assertNotEqual(first_name, user.first_name)

        last_name = contact.last_name.upper()
        self.assertNotEqual(last_name, user.last_name)

        email = f'{user.first_name}.{user.last_name}@noir.org'
        self.assertNotEqual(email, user.email)

        response = self.client.post(
            url,
            follow=True,
            data={
                'user':       user.id,
                'last_name':  last_name,
                'first_name': first_name,
                'email':      email,
            },
        )
        self.assertNoFormError(response)

        contact = self.refresh(contact)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)
        self.assertEqual(email,      contact.email)

        user = self.refresh(user)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)

    def test_editview_is_user02(self):
        "Contact is a user + field 'email' is hidden (crashed)."
        user = self.login_as_root_and_get()
        contact = self.get_object_or_fail(Contact, is_user=user)

        FieldsConfig.objects.create(
            content_type=Contact,
            descriptions=[('email', {FieldsConfig.HIDDEN: True})],
        )

        url = contact.get_edit_absolute_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('email', fields)

        last_name = user.last_name
        first_name = user.first_name
        email = user.email
        description = 'First contact user'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':        user.id,
                'last_name':   last_name,
                'first_name':  first_name,
                'email':       'useless@dontcare.org',
                'description': description,
            },
        )
        self.assertNoFormError(response)

        contact = self.refresh(contact)
        self.assertEqual(first_name,  contact.first_name)
        self.assertEqual(last_name,   contact.last_name)
        self.assertEqual(email,       contact.email)  # <= no change
        self.assertEqual(description, contact.description)

        user = self.refresh(user)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)  # <= no change

    def test_is_user01(self):
        "Property 'linked_contact'."
        user = self.create_user()

        with self.assertNumQueries(0):
            rel_contact = user.linked_contact

        contact = self.get_object_or_fail(Contact, is_user=user)
        self.assertEqual(contact, rel_contact)

        user = self.refresh(user)  # Clean cache

        with self.assertNumQueries(1):
            user.linked_contact  # NOQA

        with self.assertNumQueries(0):
            user.linked_contact  # NOQA

        self.assertHasAttr(user, 'get_absolute_url')
        self.assertEqual(contact.get_absolute_url(), user.get_absolute_url())

    def test_is_user02(self):
        """Contact.clean() + integrity of User."""
        user = self.login_as_root_and_get()
        contact = user.linked_contact
        last_name = contact.last_name
        first_name = contact.first_name

        contact.email = ''
        contact.first_name = ''
        contact.save()

        user = self.refresh(user)
        self.assertEqual('',         user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual('',         user.email)

        with self.assertRaises(ValidationError) as cm1:
            contact.full_clean()

        self.assertValidationError(
            cm1.exception,
            messages={
                'first_name': _(
                    'This Contact is related to a user and must have a first name.'
                ),
            },
        )

        # ---
        contact.first_name = first_name

        with self.assertRaises(ValidationError) as cm2:
            contact.full_clean()

        self.assertValidationError(
            cm2.exception,
            messages={
                'email': _(
                    'This Contact is related to a user and must have an email address.'
                ),
            },
        )

    def test_listview(self):
        user = self.login_as_root_and_get()

        count = Contact.objects.filter(is_deleted=False).count()

        create_contact = partial(Contact.objects.create, user=user)
        faye    = create_contact(first_name='Faye',    last_name='Valentine')
        spike   = create_contact(first_name='Spike',   last_name='Spiegel')
        vicious = create_contact(first_name='Vicious', last_name='Badguy', is_deleted=True)

        response = self.assertGET200(Contact.get_lv_absolute_url())

        with self.assertNoException():
            contacts_page = response.context['page_obj']

        self.assertEqual(count + 2, contacts_page.paginator.count)

        contacts_set = {*contacts_page.object_list}
        self.assertIn(faye,  contacts_set)
        self.assertIn(spike, contacts_set)
        self.assertNotIn(vicious, contacts_set)

    @skipIfCustomOrganisation
    def test_create_linked_contact01(self):
        "RelationType fixed."
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='Acme')
        url = self._build_addrelated_url(orga.id, REL_OBJ_EMPLOYED_BY)
        response = self.assertGET200(url)
        self.assertEqual(
            _('Create a contact related to «{organisation}»').format(
                organisation=orga,
            ),
            response.context.get('title'),
        )

        # ---
        first_name = 'Bugs'
        last_name = 'Bunny'
        cb_url = orga.get_absolute_url()
        response = self.client.post(
            url,
            follow=True,
            data={
                'user': user.pk,

                'first_name': first_name,
                'last_name':  last_name,

                'callback_url': cb_url,
            },
        )
        self.assertNoFormError(response)
        self.assertRedirects(response, cb_url)

        contact = self.get_object_or_fail(Contact, first_name=first_name)
        self.assertHaveRelation(subject=orga, type=REL_OBJ_EMPLOYED_BY, object=contact)
        self.assertEqual(last_name, contact.last_name)

    @skipIfCustomOrganisation
    def test_create_linked_contact02(self):
        "RelationType not fixed."
        user = self.login_as_root_and_get()

        rtype1 = self.get_object_or_fail(RelationType, id=REL_SUB_EMPLOYED_BY)
        rtype2 = self.get_object_or_fail(RelationType, id=REL_SUB_MANAGES)
        rtype3 = RelationType.objects.builder(
            id='test-subject_employee_month', predicate='is the employee of the month for',
            models=[Contact],
        ).symmetric(
            id='test-object_employee_month', predicate='has the employee of the month',
            models=[Organisation]
        ).get_or_create()[0]
        rtype4 = RelationType.objects.builder(
            id='test-subject_generic', predicate='generic as ***',
        ).symmetric(id='test-object_generic', predicate='other side').get_or_create()[0]
        internal_rtype = RelationType.objects.builder(
            id='test-subject_employee_year', predicate='is the employee of the year for',
            models=[Contact],
            is_internal=True,
        ).symmetric(
            id='test-object_employee_year', predicate='has the employee of the year',
            models=[Organisation],
        ).get_or_create()[0]
        disabled_rtype = RelationType.objects.builder(
            id='test-subject_employee_week', predicate='is the employee of the week for',
            models=[Contact],
            enabled=False,
        ).symmetric(
            id='test-object_employee_week', predicate='has the employee of week year',
            models=[Organisation],
        ).get_or_create()[0]

        orga = Organisation.objects.create(user=user, name='Acme')
        url = self._build_addrelated_url(orga.id)
        response = self.assertGET200(url)

        with self.assertNoException():
            rtype_f = response.context['form'].fields['rtype_for_organisation']

        self.assertEqual(
            _('Status in «{organisation}»').format(organisation=orga),
            rtype_f.label,
        )
        rtype_choices = rtype_f.choices
        self.assertInChoices(value=rtype1.id, label=str(rtype1), choices=rtype_choices)
        self.assertInChoices(value=rtype2.id, label=str(rtype2), choices=rtype_choices)
        self.assertInChoices(value=rtype3.id, label=str(rtype3), choices=rtype_choices)
        self.assertNotInChoices(value=rtype4.id,         choices=rtype_choices)
        self.assertNotInChoices(value=internal_rtype.id, choices=rtype_choices)
        self.assertNotInChoices(value=disabled_rtype.id, choices=rtype_choices)

        # ---
        first_name = 'Bugs'
        last_name = 'Bunny'
        response = self.client.post(
            url, follow=True,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,

                'rtype_for_organisation': rtype1.id,
            },
        )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(subject=orga, type=REL_OBJ_EMPLOYED_BY, object=contact)

    @skipIfCustomOrganisation
    def test_create_linked_contact_property_constraint01(self):
        "Mandatory object's properties."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is mandatory')
        rtype = RelationType.objects.builder(
            id='persons-subject_test_rtype', predicate='RType', models=[Contact],
        ).symmetric(
            id='persons-object_test_rtype', predicate='Rtype sym',
            models=[Organisation], properties=[ptype],
        ).get_or_create()[0]

        orga = Organisation.objects.create(user=user, name='Acme')
        CremeProperty.objects.create(creme_entity=orga, type=ptype)

        first_name = 'Bugs'
        last_name = 'Bunny'
        response = self.assertPOST200(
            self._build_addrelated_url(orga.id),
            follow=True,
            data={
                'user': user.pk,
                'first_name': first_name,
                'last_name': last_name,
                'rtype_for_organisation': rtype.id,
            },
        )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(subject=contact, type=rtype.id, object=orga)

    @skipIfCustomOrganisation
    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_create_linked_contact_property_constraint02(self):
        "Mandatory subject's properties."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is mandatory')
        rtype = RelationType.objects.builder(
            id='persons-subject_test_rtype', predicate='RType',
            models=[Contact], properties=[ptype],
        ).symmetric(
            id='persons-object_test_rtype', predicate='Rtype sym',
            models=[Organisation],
        ).get_or_create()[0]

        orga = Organisation.objects.create(user=user, name='Acme')

        first_name = 'Bugs'
        last_name = 'Bunny'
        response = self.assertPOST200(
            self._build_addrelated_url(orga.id),
            follow=True,
            data={
                'user': user.pk,
                'first_name': first_name,
                'last_name': last_name,

                'property_types': [ptype.id],

                'rtype_for_organisation': rtype.id,
            },
        )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(subject=contact, type=rtype.id, object=orga)
        self.assertCountEqual(
            [ptype], [p.type for p in contact.properties.all()],
        )

    @skipIfCustomOrganisation
    def test_create_linked_contact_property_constraint03(self):
        "Forbidden object's properties."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is forbidden')
        rtype = RelationType.objects.builder(
            id='persons-subject_test_rtype', predicate='RType', models=[Contact],
        ).symmetric(
            id='persons-object_test_rtype', predicate='Rtype sym',
            models=[Organisation], forbidden_properties=[ptype],
        ).get_or_create()[0]

        orga = Organisation.objects.create(user=user, name='Acme')

        first_name = 'Bugs'
        last_name = 'Bunny'
        response = self.assertPOST200(
            self._build_addrelated_url(orga.id),
            follow=True,
            data={
                'user': user.pk,
                'first_name': first_name,
                'last_name': last_name,
                'rtype_for_organisation': rtype.id,
            },
        )
        self.assertNoFormError(response)

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(subject=contact, type=rtype.id, object=orga)

    @skipIfCustomOrganisation
    def test_create_linked_contact_error01(self):
        "No LINK credentials."
        user = self.login_as_persons_user(creatable_models=[Contact])
        self.add_credentials(user.role, own='!LINK')

        orga = Organisation.objects.create(user=user, name='Acme')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        url1 = self._build_addrelated_url(orga.id, REL_OBJ_EMPLOYED_BY)
        url2 = self._build_addrelated_url(orga.id)
        self.assertGET403(url1)
        self.assertGET403(url2)

        # --
        self.add_credentials(user.role, own=['LINK'], model=Organisation)
        self.assertGET403(url1)
        self.assertGET403(url2)

        # --
        self.add_credentials(user.role, own=['LINK'], model=Contact)
        self.assertGET200(url1)
        self.assertGET200(url2)

        # --
        data = {
            'user': self.get_root_user().pk,
            'first_name': 'Bugs',
            'last_name': 'Bunny',
        }
        response1 = self.assertPOST200(url1, follow=True, data=data)
        msg = _(
            'You are not allowed to link with the «{models}» of this user.'
        ).format(models=_('Contacts'))
        self.assertFormError(response1.context['form'], field='user', errors=msg)

        # ---
        response2 = self.assertPOST200(
            url2,
            follow=True,
            data={
                **data,
                'rtype_for_organisation': REL_SUB_EMPLOYED_BY,
            },
        )
        self.assertFormError(response2.context['form'], field='user', errors=msg)

    @skipIfCustomOrganisation
    def test_create_linked_contact_error02(self):
        "Cannot VIEW the organisation."
        user = self.login_as_persons_user(creatable_models=[Contact])
        self.add_credentials(user.role, all='*', model=Contact)  # Not Organisation

        orga = Organisation.objects.create(user=user, name='Acme')
        self.assertFalse(user.has_perm_to_view(orga))

        response = self.client.get(self._build_addrelated_url(orga.id, REL_OBJ_EMPLOYED_BY))
        self.assertContains(
            response,
            _('You are not allowed to view this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=orga.id),
            ),
            status_code=403,
            html=True,
        )

    @skipIfCustomOrganisation
    def test_create_linked_contact_error03(self):
        "Cannot LINK the organisation."
        user = self.login_as_persons_user(creatable_models=[Contact])
        self.add_credentials(user.role, all='*',     model=Contact)
        self.add_credentials(user.role, all='!LINK', model=Organisation)

        orga = Organisation.objects.create(user=user, name='Acme')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        self.assertGET403(self._build_addrelated_url(orga.id, REL_OBJ_EMPLOYED_BY))

    @skipIfCustomOrganisation
    def test_create_linked_contact_error04(self):
        "Misc errors."
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Acme')

        build_url = self._build_addrelated_url
        self.assertGET404(build_url(self.UNUSED_PK, REL_OBJ_EMPLOYED_BY))
        self.assertGET404(build_url(orga.id, 'IDONOTEXIST'))

        rtype1 = RelationType.objects.builder(
            id='persons-subject_test_rtype1', predicate='RType #1', models=[Organisation],
        ).symmetric(
            id='persons-object_test_rtype1', predicate='Rtype sym #1', models=[Contact],
        ).get_or_create()[0]
        self.assertGET200(build_url(orga.id, rtype1.id))

        rtype2 = RelationType.objects.builder(
            id='persons-subject_test_badrtype1', predicate='Bad RType #1',
            models=[Organisation],
        ).symmetric(
            id='persons-object_test_badrtype1', predicate='Bad RType sym #1',
            models=[Document],  # <==
        ).get_or_create()[0]
        self.assertGET409(build_url(orga.id, rtype2.id))

        rtype3 = RelationType.objects.builder(
            id='persons-subject_test_badrtype2', predicate='Bad RType #2',
            models=[Document],  # <==
        ).symmetric(
            id='persons-object_test_badrtype2', predicate='Bad RType sym #2',
            models=[Contact],
        ).get_or_create()[0]
        self.assertGET409(build_url(orga.id, rtype3.id))

        rtype4 = RelationType.objects.builder(
            id='persons-subject_test_badrtype3', predicate='Bad RType #3',
            models=[Organisation],
            is_internal=True,  # <==
        ).symmetric(
            id='persons-object_test_badrtype3', predicate='Bad RType sym #3',
            models=[Contact],
        ).get_or_create()[0]
        self.assertGET409(build_url(orga.id, rtype4.id))

        rtype5 = RelationType.objects.builder(
            id='persons-subject_test_badrtype4', predicate='Bad RType #4',
            models=[Organisation],
            enabled=False,
        ).symmetric(
            id='persons-object_test_badrtype4', predicate='Bad RType sym #4',
            models=[Contact],
        ).get_or_create()[0]
        self.assertGET409(build_url(orga.id, rtype5.id))

    @skipIfCustomOrganisation
    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_create_linked_contact_error05(self):
        "Mandatory properties."
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is mandatory')
        ptype2 = create_ptype(text='Is optional')

        rtype1 = RelationType.objects.builder(
            id='persons-subject_test_rtype1', predicate='RType #1', models=[Contact],
        ).symmetric(
            id='persons-object_test_rtype1', predicate='Rtype sym #1',
            models=[Organisation], properties=[ptype1],
        ).get_or_create()[0]

        orga = Organisation.objects.create(user=user, name='Acme')
        CremeProperty.objects.create(creme_entity=orga, type=ptype2)

        url = self._build_addrelated_url(orga.id)
        first_name = 'Bugs'
        last_name = 'Bunny'
        data = {
            'user': user.pk,
            'first_name': first_name,
            'last_name': last_name,
        }

        # Object constraint
        response1 = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                'rtype_for_organisation': rtype1.id,
            },
        )
        self.assertFormError(
            response1.context['form'],
            field='rtype_for_organisation',
            errors=Relation.error_messages['missing_subject_property'] % {
                'entity': orga,
                'property': ptype1,
                'predicate': rtype1.predicate,
            },
        )

        # Subject constraint
        rtype2 = RelationType.objects.builder(
            id='persons-subject_test_rtype2', predicate='RType #2',
            models=[Contact], properties=[ptype1],
        ).symmetric(
            id='persons-object_test_rtype2', predicate='Rtype sym #2',
            models=[Organisation],
        ).get_or_create()[0]
        response2 = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                'property_types': [ptype2.id],
                'rtype_for_organisation': rtype2.id,
            },
        )
        self.assertFormError(
            response2.context['form'],
            field='rtype_for_organisation',
            errors=Relation.error_messages['missing_subject_property'] % {
                'entity': Contact(last_name=last_name, first_name=first_name),
                'property': ptype1,
                'predicate': rtype2.predicate,
            },
        )

    @skipIfCustomOrganisation
    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_create_linked_contact_error06(self):
        "Forbidden properties (object constraint)."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is forbidden')
        rtype = RelationType.objects.smart_update_or_create(
            ('persons-subject_test_rtype1', 'RType #1',     [Contact]),
            ('persons-object_test_rtype1',  'Rtype sym #1', [Organisation], [], [ptype]),
        )[0]

        orga = Organisation.objects.create(user=user, name='Acme')
        CremeProperty.objects.create(creme_entity=orga, type=ptype)

        response1 = self.assertPOST200(
            self._build_addrelated_url(orga.id),
            follow=True,
            data={
                'user': user.pk,
                'first_name': 'Bugs',
                'last_name': 'Bunny',
                'rtype_for_organisation': rtype.id,
            },
        )
        self.assertFormError(
            response1.context['form'],
            field='rtype_for_organisation',
            errors=_(
                'The entity «%(entity)s» has the property «%(property)s» which is '
                'forbidden by the relationship «%(predicate)s».'
            ) % {
                'entity': orga,
                'property': ptype,
                'predicate': rtype.predicate,
            },
        )

    @skipIfCustomAddress
    def test_clone(self):
        "Addresses & is_user are problematic."
        user = self.login_as_root_and_get()
        naruto = self.get_object_or_fail(Contact, is_user=user)

        create_address = partial(
            Address.objects.create,
            city='Konoha', state='Konoha', zipcode='111',
            country='The land of fire', department="Ninjas' homes",
            owner=naruto,
        )
        naruto.billing_address = create_address(
            name="Naruto's", address='Home', po_box='000',
        )
        naruto.shipping_address = create_address(
            name="Naruto's", address='Home (second entry)', po_box='001',
        )
        naruto.save()

        for i in range(5):
            create_address(name=f'Secret Cave #{i}', address=f'Cave #{i}', po_box='XXX')

        kage_bunshin = self.clone(naruto)
        self.assertEqual(naruto.first_name, kage_bunshin.first_name)
        self.assertEqual(naruto.last_name, kage_bunshin.last_name)
        self.assertIsNone(kage_bunshin.is_user)  # <====

        self.assertEqual(naruto.id, naruto.billing_address.object_id)
        self.assertEqual(naruto.id, naruto.shipping_address.object_id)

        self.assertEqual(kage_bunshin.id, kage_bunshin.billing_address.object_id)
        self.assertEqual(kage_bunshin.id, kage_bunshin.shipping_address.object_id)

        addresses   = [*Address.objects.filter(object_id=naruto.id)]
        c_addresses = [*Address.objects.filter(object_id=kage_bunshin.id)]
        self.assertEqual(7, len(addresses))
        self.assertEqual(7, len(c_addresses))

        addresses_map   = {a.address: a for a in addresses}
        c_addresses_map = {a.address: a for a in c_addresses}
        self.assertEqual(7, len(addresses_map))
        self.assertEqual(7, len(c_addresses_map))

        for ident, address in addresses_map.items():
            address2 = c_addresses_map.get(ident)
            self.assertIsNotNone(address2, ident)
            self.assertAddressOnlyContentEqual(address, address2)

    # @skipIfCustomAddress
    # def test_clone__method(self):  # DEPRECATED
    #     "Addresses & is_user are problematic."
    #     user = self.login_as_root_and_get()
    #     naruto = self.get_object_or_fail(Contact, is_user=user)
    #
    #     create_address = partial(
    #         Address.objects.create,
    #         city='Konoha', state='Konoha', zipcode='111',
    #         country='The land of fire', department="Ninjas' homes",
    #         owner=naruto,
    #     )
    #     naruto.billing_address = create_address(
    #         name="Naruto's", address='Home', po_box='000',
    #     )
    #     naruto.shipping_address = create_address(
    #         name="Naruto's", address='Home (second entry)', po_box='001',
    #     )
    #     naruto.save()
    #
    #     for i in range(5):
    #         create_address(name=f'Secret Cave #{i}', address=f'Cave #{i}', po_box='XXX')
    #
    #     kage_bunshin = naruto.clone()
    #
    #     self.assertEqual(naruto.first_name, kage_bunshin.first_name)
    #     self.assertEqual(naruto.last_name, kage_bunshin.last_name)
    #     self.assertIsNone(kage_bunshin.is_user)  # <====
    #
    #     self.assertEqual(naruto.id, naruto.billing_address.object_id)
    #     self.assertEqual(naruto.id, naruto.shipping_address.object_id)
    #
    #     self.assertEqual(kage_bunshin.id, kage_bunshin.billing_address.object_id)
    #     self.assertEqual(kage_bunshin.id, kage_bunshin.shipping_address.object_id)
    #
    #     addresses   = [*Address.objects.filter(object_id=naruto.id)]
    #     c_addresses = [*Address.objects.filter(object_id=kage_bunshin.id)]
    #     self.assertEqual(7, len(addresses))
    #     self.assertEqual(7, len(c_addresses))
    #
    #     addresses_map   = {a.address: a for a in addresses}
    #     c_addresses_map = {a.address: a for a in c_addresses}
    #     self.assertEqual(7, len(addresses_map))
    #     self.assertEqual(7, len(c_addresses_map))
    #
    #     for ident, address in addresses_map.items():
    #         address2 = c_addresses_map.get(ident)
    #         self.assertIsNotNone(address2, ident)
    #         self.assertAddressOnlyContentEqual(address, address2)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete(self):
        user = self.login_as_root_and_get()
        naruto = Contact.objects.create(user=user, first_name='Naruto', last_name='Uzumaki')
        url = naruto.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            naruto = self.refresh(naruto)

        self.assertIs(naruto.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(naruto)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_is_user01(self):
        "Can not delete if the Contact corresponds to a user."
        user = self.login_as_root_and_get()
        contact = user.linked_contact
        self.assertPOST409(contact.get_delete_absolute_url(), follow=True)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_delete_is_user02(self):
        "Can not trash if the Contact corresponds to a user."
        user = self.login_as_root_and_get()
        contact = user.linked_contact
        self.assertPOST409(contact.get_delete_absolute_url(), follow=True)

    def test_delete_civility01(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        captain = Civility.objects.create(title='Captain')
        harlock = Contact.objects.create(
            user=user, first_name='Harlock', last_name='Matsumoto', civility=captain,
        )

        response = self.client.post(reverse(
            'creme_config__delete_instance', args=('persons', 'civility', captain.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Civility).job
        job.type.execute(job)
        self.assertDoesNotExist(captain)

        harlock = self.assertStillExists(harlock)
        self.assertIsNone(harlock.civility)

    def test_delete_civility02(self):
        "Set to another value."
        user = self.login_as_root_and_get()
        civ2 = Civility.objects.first()
        captain = Civility.objects.create(title='Captain')
        harlock = Contact.objects.create(
            user=user, first_name='Harlock', last_name='Matsumoto', civility=captain,
        )

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('persons', 'civility', captain.id)
            ),
            data={'replace_persons__contact_civility': civ2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Civility).job
        job.type.execute(job)
        self.assertDoesNotExist(captain)

        harlock = self.assertStillExists(harlock)
        self.assertEqual(civ2, harlock.civility)

    def test_delete_position01(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        captain = Position.objects.create(title='Captain')
        harlock = Contact.objects.create(
            user=user, first_name='Harlock', last_name='Matsumoto', position=captain,
        )

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('persons', 'position', captain.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Position).job
        job.type.execute(job)
        self.assertDoesNotExist(captain)

        harlock = self.assertStillExists(harlock)
        self.assertIsNone(harlock.position)

    def test_delete_position02(self):
        "Set to another value."
        user = self.login_as_root_and_get()
        pos2 = Position.objects.first()
        captain = Position.objects.create(title='Captain')
        harlock = Contact.objects.create(
            user=user, first_name='Harlock', last_name='Matsumoto', position=captain,
        )

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('persons', 'position', captain.id),
            ),
            data={'replace_persons__contact_position': pos2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Position).job
        job.type.execute(job)
        self.assertDoesNotExist(captain)

        harlock = self.assertStillExists(harlock)
        self.assertEqual(pos2, harlock.position)

    def test_delete_sector01(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        piracy = Sector.objects.create(title='Piracy')
        harlock = Contact.objects.create(
            user=user, first_name='Harlock', last_name='Matsumoto', sector=piracy,
        )

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('persons', 'sector', piracy.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Sector).job
        job.type.execute(job)
        self.assertDoesNotExist(piracy)

        harlock = self.assertStillExists(harlock)
        self.assertIsNone(harlock.sector)

    def test_delete_sector02(self):
        "Set to another value."
        user = self.login_as_root_and_get()
        sector2 = Sector.objects.first()
        piracy = Sector.objects.create(title='Piracy')
        harlock = Contact.objects.create(
            user=user, first_name='Harlock', last_name='Matsumoto', sector=piracy,
        )

        response = self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('persons', 'sector', piracy.id)
            ),
            data={'replace_persons__contact_sector': sector2.id},
        )
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Sector).job
        job.type.execute(job)
        self.assertDoesNotExist(piracy)

        harlock = self.assertStillExists(harlock)
        self.assertEqual(sector2, harlock.sector)

    @skipIfCustomDocument
    def test_delete_image(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        image = self._create_image(user=user)
        harlock = Contact.objects.create(user=user, last_name='Matsumoto', image=image)

        image.delete()

        self.assertDoesNotExist(image)
        self.assertIsNone(self.refresh(harlock).image)

    def test_user_linked_contact(self):
        first_name = 'Deunan'
        last_name = 'Knut'
        count = Contact.objects.count()
        user = CremeUser.objects.create(
            username='dknut', last_name=last_name, first_name=first_name,
        )
        self.assertEqual(count + 1, Contact.objects.count())

        with self.assertNoException():
            contact = user.linked_contact

        self.assertIsInstance(contact, Contact)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)

    def test_user_linked_contact__team(self):
        user = self.create_user(
            username='dknut', is_team=True, last_name='Knut', first_name='Deunan',
        )

        with self.assertNoException():
            contact = user.linked_contact

        self.assertIsNone(contact)

    def test_user_linked_contact__is_staff(self):
        count = Contact.objects.count()
        user = self.create_user(
            username='dknut', is_staff=True, last_name='Knut', first_name='Deunan',
        )
        self.assertEqual(count, Contact.objects.count())

        with self.assertNoException():
            contact = user.linked_contact

        self.assertIsNone(contact)

    def test_user_delete_is_user(self):
        "Manage Contact.is_user field: Contact is no more related to deleted user."
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        contact = user.linked_contact
        other_contact = other_user.linked_contact

        create_contact = Contact.objects.create
        deunan = create_contact(
            user=user, first_name='Deunan', last_name='Knut',
        )
        briareos = create_contact(
            user=other_user, first_name='Briareos', last_name='Hecatonchires',
        )

        self.assertNoFormError(self.client.post(
            reverse('creme_config__delete_user', args=(other_user.id,)),
            data={'to_user': user.id}
        ))
        self.assertDoesNotExist(other_user)
        self.assertStillExists(contact)

        other_contact = self.assertStillExists(other_contact)
        self.assertIsNone(other_contact.is_user)
        self.assertEqual(user, other_contact.user)

        self.assertStillExists(deunan)
        self.assertEqual(user, self.assertStillExists(briareos).user)

    def test_fk_user_printer01(self):
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

    def test_fk_user_printer02(self):
        "Team."
        user = self.create_user()

        eswat = self.create_team('eswat')
        deunan = Contact.objects.create(user=eswat, first_name='Deunan', last_name='Knut')

        self.assertEqual(
            str(eswat),
            field_printer_registry.get_field_value(
                instance=deunan, field_name='user', user=user, tag=ViewTag.HTML_DETAIL,
            ),
        )

    def test_fk_user_printer03(self):
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

    @skipIfCustomOrganisation
    def test_get_employers(self):
        user = self.login_as_root_and_get()

        create_contact = partial(Contact.objects.create, user=user)
        deunan   = create_contact(first_name='Deunan',   last_name='Knut')
        briareos = create_contact(first_name='Briareos', last_name='Hecatonchires')

        create_orga = partial(Organisation.objects.create, user=user)
        eswat   = create_orga(name='ESWAT')
        olympus = create_orga(name='Olympus')
        deleted = create_orga(name='Deleted', is_deleted=True)
        club    = create_orga(name='Cyborg club')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=deunan,   type_id=REL_SUB_EMPLOYED_BY, object_entity=eswat)
        create_rel(subject_entity=deunan,   type_id=REL_SUB_MANAGES,     object_entity=olympus)
        create_rel(subject_entity=deunan,   type_id=REL_SUB_EMPLOYED_BY, object_entity=deleted)
        create_rel(subject_entity=briareos, type_id=REL_SUB_EMPLOYED_BY, object_entity=club)

        self.assertListEqual(
            [eswat, olympus],
            [*deunan.get_employers()],
        )

    @skipIfCustomUser
    def test_command_create_staffuser(self):
        from django.core.management import call_command

        from creme.creme_core.management.commands.creme_createstaffuser import (
            Command as StaffCommand,
        )

        super_user1 = self.get_alone_element(
            CremeUser.objects.filter(is_superuser=True, is_staff=False)
        )

        # This superuser should not be used
        username2 = 'kirika'
        self.assertLess(username2, super_user1.username)
        CremeUser.objects.create(
            username=username2, email='kirika@noir.jp',
            first_name='Kirika', last_name='Yumura',
            is_superuser=True,
        )

        username = 'staff1'
        first_name = 'John'
        last_name = 'Staffman'
        email = 'staffman@acme.com'

        with self.assertNoException():
            call_command(
                StaffCommand(),
                verbosity=0,
                interactive=False,
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
            )

        user = self.get_object_or_fail(CremeUser, username=username)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)
        self.assertIs(user.is_superuser, True)
        self.assertIs(user.is_staff, True)

        self.assertFalse(Contact.objects.filter(is_user=user))
