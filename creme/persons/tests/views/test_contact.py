from functools import partial

from django.core.exceptions import ValidationError
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CremeUser,
    FieldsConfig,
    Relation,
    RelationType,
)
from creme.persons.constants import (
    REL_OBJ_EMPLOYED_BY,
    REL_SUB_EMPLOYED_BY,
    REL_SUB_MANAGES,
)
from creme.persons.forms.address import AddressesGroup

from ..base import (
    Address,
    Contact,
    Document,
    Organisation,
    _PersonsTestCase,
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)


@skipIfCustomContact
class ContactViewsTestCase(_PersonsTestCase):
    def test_detail_view(self):
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(
            user=user, first_name='Faye', last_name='Valentine',
        )
        response = self.assertGET200(contact.get_absolute_url())
        self.assertTemplateUsed(response, 'persons/view_contact.html')

    def test_list_view(self):
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


@skipIfCustomContact
class ContactCreationTestCase(_PersonsTestCase):
    def test_no_address(self):
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
    def test_addresses(self):
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
    def test_addresses__model_validation__field_error(self):
        """Validation error (custom model validation on Address -- for swapped
        or hooked models); field error.
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
    def test_addresses__model_validation__non_field_error(self):
        "Validation error (custom model validation...); non field-error."
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
    def test_addresses__form_error(self):
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
            self.assertNoFormError(self.client.post(
                url,
                follow=True,
                data={
                    **data,

                    'billing_address-city': b_city,
                },
            ))
        finally:
            AddressesGroup.sub_form_class = original_form

        contact = self.get_object_or_fail(Contact, last_name=last_name, first_name=first_name)
        self.assertIsNone(contact.shipping_address)

        billing_address = contact.billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(b_address, billing_address.address)
        self.assertEqual(b_city,    billing_address.city)

    @skipIfCustomAddress
    def test_addresses__fields_config__required(self):
        self.login_as_root()

        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[('city', {FieldsConfig.REQUIRED: True})],
        )

        response = self.assertGET200(reverse('persons__create_contact'))

        with self.assertNoException():
            fields = response.context['form'].fields
            zipcode_f = fields['billing_address-zipcode']
            city_f = fields['billing_address-city']

        self.assertFalse(zipcode_f.required)
        self.assertTrue(city_f.required)


@skipIfCustomContact
class ContactEditionTestCase(_PersonsTestCase):
    def test_simple(self):
        user = self.login_as_root_and_get()
        first_name = 'Faye'
        contact = Contact.objects.create(
            user=user, first_name=first_name, last_name='Valentine',
        )

        url = contact.get_edit_absolute_url()
        self.assertGET200(url)

        # POST ---
        last_name = 'Spiegel'
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

        contact = self.refresh(contact)
        self.assertEqual(last_name, contact.last_name)
        self.assertIsNone(contact.billing_address)
        self.assertIsNone(contact.shipping_address)

        self.assertRedirects(response, contact.get_absolute_url())

    @skipIfCustomAddress
    def test_addresses(self):
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

    def test_is_user(self):
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

    def test_is_user__hidden_email(self):
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


@skipIfCustomContact
@skipIfCustomOrganisation
class LinkedContactCreationTestCase(_PersonsTestCase):
    @staticmethod
    def _build_add_related_url(orga_id, rtype_id=None):
        kwargs = {'orga_id': orga_id}

        if rtype_id:
            kwargs['rtype_id'] = rtype_id

        return reverse('persons__create_related_contact', kwargs=kwargs)

    def test_fixed_rtype(self):
        "RelationType fixed."
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='Acme')
        url = self._build_add_related_url(orga.id, REL_OBJ_EMPLOYED_BY)
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

    def test_not_fixed_rtype(self):
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
        url = self._build_add_related_url(orga.id)
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

    def test_property_constraint__object(self):
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
            self._build_add_related_url(orga.id),
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

    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_property_constraint__subject(self):
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
            self._build_add_related_url(orga.id),
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

    def test_property_constraint__forbidden(self):
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
            self._build_add_related_url(orga.id),
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

    def test_link_perms(self):
        "No LINK credentials."
        user = self.login_as_persons_user(creatable_models=[Contact])
        self.add_credentials(user.role, own='!LINK')

        orga = Organisation.objects.create(user=user, name='Acme')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        url1 = self._build_add_related_url(orga.id, REL_OBJ_EMPLOYED_BY)
        url2 = self._build_add_related_url(orga.id)
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

    def test_view_perms(self):
        "Cannot VIEW the organisation."
        user = self.login_as_persons_user(creatable_models=[Contact])
        self.add_credentials(user.role, all='*', model=Contact)  # Not Organisation

        orga = Organisation.objects.create(user=user, name='Acme')
        self.assertFalse(user.has_perm_to_view(orga))

        response = self.client.get(self._build_add_related_url(orga.id, REL_OBJ_EMPLOYED_BY))
        self.assertContains(
            response,
            _('You are not allowed to view this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=orga.id),
            ),
            status_code=403,
            html=True,
        )

    def test_link_perms_organisation(self):
        "Cannot LINK the organisation."
        user = self.login_as_persons_user(creatable_models=[Contact])
        self.add_credentials(user.role, all='*',     model=Contact)
        self.add_credentials(user.role, all='!LINK', model=Organisation)

        orga = Organisation.objects.create(user=user, name='Acme')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        self.assertGET403(self._build_add_related_url(orga.id, REL_OBJ_EMPLOYED_BY))

    def test_invalid_rtypes(self):
        "Misc errors."
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Acme')

        build_url = self._build_add_related_url
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

    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_missing_properties(self):
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

        url = self._build_add_related_url(orga.id)
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

    @override_settings(FORMS_RELATION_FIELDS=True)
    def test_forbidden_properties(self):
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
            self._build_add_related_url(orga.id),
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


@skipIfCustomContact
class TransformationIntoUserTestCase(_PersonsTestCase):
    @staticmethod
    def _build_as_user_url(contact):
        return reverse('persons__transform_contact_into_user', args=(contact.id,))

    def test_transform_into_user(self):
        user = self.login_as_root_and_get()
        first_name = 'Spike'
        last_name = 'Spiegel'
        email = 'spike@bebop.mrs'
        contact = Contact.objects.create(
            user=user, first_name=first_name, last_name=last_name, email=email,
        )

        old_contact_count = Contact.objects.count()
        old_user_count    = CremeUser.objects.count()

        url = self._build_as_user_url(contact)
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Transform «{object}» into a user').format(object=contact),
            context1.get('title'),
        )
        self.assertEqual(
            _('Save the user').format(object=contact),
            context1.get('submit_label'),
        )

        with self.assertNoException():
            fields = context1['form'].fields
            # role_f = fields['role']
            email_f = fields['email']

        self.assertIn('username', fields)
        self.assertIn('displayed_name', fields)
        self.assertIn('password_1', fields)
        self.assertIn('password_2', fields)
        self.assertIn('roles', fields)
        self.assertNotIn('last_name', fields)
        self.assertNotIn('first_name', fields)

        # self.assertEqual('*{}*'.format(_('Superuser')), role_f.empty_label)

        self.assertTrue(email_f.required)
        self.assertEqual(email, email_f.initial)
        self.assertEqual(
            _('The email of the Contact will be updated if you change it.'),
            email_f.help_text,
        )

        # ---
        username = 'spikes'
        password = '$33 yo|_| sp4c3 c0wb0Y'
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'username': username,
                # 'displayed_name': ...
                'password_1': password,
                'password_2': password,
                # 'role': ...
                'roles': [],
                'email': email,
            },
        )
        self.assertNoFormError(response2)

        self.assertEqual(old_user_count + 1, CremeUser.objects.count())
        self.assertEqual(old_contact_count, Contact.objects.count())

        contact = self.refresh(contact)
        self.assertEqual(last_name,  contact.last_name)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(email,      contact.email)

        contact_user = contact.is_user
        self.assertIsNotNone(contact_user)
        self.assertEqual(username,   contact_user.username)
        self.assertEqual(last_name,  contact_user.last_name)
        self.assertEqual(first_name, contact_user.first_name)
        self.assertEqual(email,      contact_user.email)
        self.assertFalse(contact_user.displayed_name)
        self.assertTrue(contact_user.is_superuser)
        self.assertIsNone(contact_user.role)
        self.assertFalse(contact_user.roles.all())
        self.assertTrue(contact_user.check_password(password))

        self.assertRedirects(response2, contact.get_absolute_url())

        # Already related to a user ---
        self.assertGET409(url)

    def test_transform_into_user__not_superuser(self):
        user = self.login_as_persons_user(admin_4_apps=['persons'])
        self.add_credentials(user.role, own='*')

        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel', email='spike@bebop.mrs',
        )
        self.assertGET403(self._build_as_user_url(contact))

    def test_transform_into_user__no_email(self):
        user = self.login_as_root_and_get()
        first_name = 'Jet'
        last_name = 'Black'
        contact = Contact.objects.create(
            user=user, first_name=first_name, last_name=last_name,
            # email=...,  # <====
        )
        role = self.create_role(name='Pilot')

        url = self._build_as_user_url(contact)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            email_f = fields['email']
            # role_f = fields['role']
            roles_f = fields['roles']

        self.assertTrue(email_f.required)
        self.assertEqual(
            _('The email of the Contact will be updated.'),
            email_f.help_text,
        )

        # self.assertInChoices(value=role.id, label=role.name, choices=role_f.choices)
        self.assertInChoices(value=role.id, label=role.name, choices=roles_f.choices)

        # ---
        username = 'jet'
        password = 'sp4c3 c0wb0Y'
        displayed_name = 'jetto'
        email = 'jet@bebop.mrs'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'username': username,
                'displayed_name': displayed_name,
                'password_1': password,
                'password_2': password,
                'email': email,
                # 'role': role.id,
                'roles': [role.id],
            },
        ))

        contact = self.refresh(contact)
        self.assertEqual(email, contact.email)

        contact_user = contact.is_user
        self.assertIsNotNone(contact_user)
        self.assertEqual(username,       contact_user.username)
        self.assertEqual(last_name,      contact_user.last_name)
        self.assertEqual(first_name,     contact_user.first_name)
        self.assertEqual(displayed_name, contact_user.displayed_name)
        self.assertEqual(email,          contact_user.email)
        self.assertEqual(role,           contact_user.role)
        self.assertFalse(contact_user.is_superuser)
        self.assertListEqual([role], [*contact_user.roles.all()])

    def test_transform_into_user__no_first_name(self):
        user = self.login_as_root_and_get()
        last_name = 'Valentine'
        email = 'faye@bebop.mrs'
        contact = Contact.objects.create(
            user=user, last_name=last_name, email=email,
            # first_name=...,
        )

        url = self._build_as_user_url(contact)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            first_name_f = response1.context['form'].fields['first_name']

        self.assertTrue(first_name_f.required)
        self.assertEqual(
            _('The first name of the Contact will be updated.'),
            first_name_f.help_text,
        )

        # ---
        password = 'sp4c3 c0wg1rL'
        first_name = 'Faye'
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'username': 'fayev',
                'first_name': first_name,
                'password_1': password,
                'password_2': password,
                'email': 'faye@bebop.mrs',
            },
        ))

        contact = self.refresh(contact)
        self.assertEqual(first_name, contact.first_name)

        contact_user = contact.is_user
        self.assertEqual(last_name,  contact_user.last_name)
        self.assertEqual(first_name, contact_user.first_name)
        self.assertEqual(email,      contact_user.email)

    def test_transform_into_user__password_mismatch(self):
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(
            user=user, last_name='Spiegel',
            first_name='Spike',
            email='spiegel@bebop.mrs',
        )

        response = self.assertPOST200(
            self._build_as_user_url(contact),
            data={
                'username': 'spike',
                'password_1': 'sp4c3 c0wg1rL',
                'password_2': 'not sp4c3 c0wg1rL',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='password_2',
            errors=_("The two password fields didn’t match."),
        )

    def test_transform_into_user__existing_user(self):
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(
            user=user, last_name='Spiegel',
            first_name='Spike',
            email='spiegel@bebop.mrs',
        )

        password = 'sp4c3 c0wg1rL'
        response = self.assertPOST200(
            self._build_as_user_url(contact),
            data={
                'username': 'ROOT',
                'password_1': password,
                'password_2': password,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='username',
            errors=_('A user with that username already exists.'),
        )

    def test_transform_into_user__duplicated_user_email(self):
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(
            user=user, last_name='Spiegel',
            first_name='Spike',
            email=user.email,  # <==
        )

        url = self._build_as_user_url(contact)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            email_f = response1.context['form'].fields['email']

        self.assertTrue(email_f.required)
        self.assertFalse(email_f.initial)
        self.assertEqual(
            _('BEWARE: the email of the Contact is already used by a user & will be updated.'),
            email_f.help_text,
        )

        # ---
        password = 'sp4c3 c0wg1rL'
        data = {
            'username': 'spike',
            'password_1': password,
            'password_2': password,
            'email': user.email,
        }
        response2 = self.assertPOST200(url, data=data)
        self.assertFormError(
            self.get_form_or_fail(response2),
            field='email',
            errors=_('An active user with the same email address already exists.'),
        )

        # ---
        email = 'spiegel@bebop.mrs'
        self.assertNoFormError(self.client.post(
            url, follow=True, data={**data, 'email': email},
        ))
        self.assertEqual(email, self.refresh(contact).email)

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[{
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        }],
    )
    def test_transform_into_user__password_similarity__form_fields(self):
        "Similarity with field in form."
        user = self.login_as_root_and_get()
        contact = Contact.objects.create(
            user=user, last_name='Spiegel',  # first_name=..., email=...,
        )

        username = 'megapilot'
        first_name = 'Spike'
        email = 'spiegel@bebop.mrs'
        url = self._build_as_user_url(contact)

        def assertSimilarityError(password, field_verbose_name):
            response = self.assertPOST200(
                url,
                follow=True,
                data={
                    'username': username,
                    'first_name': first_name,
                    'email': email,

                    'password_1': password,
                    'password_2': password,
                },
            )
            self.assertFormError(
                self.get_form_or_fail(response),
                field='password_2',
                errors=_('The password is too similar to the %(verbose_name)s.') % {
                    'verbose_name': field_verbose_name,
                },
            )

        assertSimilarityError(username,   _('Username'))
        assertSimilarityError(first_name, _('First name'))
        assertSimilarityError(email,      _('Email address'))

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[{
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        }],
    )
    def test_transform_into_user__password_similarity__model_fields(self):
        "Similarity with field not in form."
        user = self.login_as_root_and_get()
        first_name = 'Spike'
        email = 'spiegel@bebop.mrs'
        contact = Contact.objects.create(
            user=user, last_name='Spiegel',
            first_name=first_name,
            email=email,
        )

        username = 'megapilot'
        url = self._build_as_user_url(contact)

        def assertSimilarityError(password, field_verbose_name):
            response = self.assertPOST200(
                url,
                follow=True,
                data={
                    'username': username,

                    'password_1': password,
                    'password_2': password,

                    'email': email,
                },
            )
            self.assertFormError(
                self.get_form_or_fail(response),
                field='password_2',
                errors=_('The password is too similar to the %(verbose_name)s.') % {
                    'verbose_name': field_verbose_name,
                },
            )

        assertSimilarityError(username, _('Username'))
        assertSimilarityError(contact.last_name, _('Last name'))
        assertSimilarityError(first_name, _('First name'))
        assertSimilarityError(email,      _('Email address'))
