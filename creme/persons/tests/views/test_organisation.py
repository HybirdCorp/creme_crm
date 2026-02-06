from datetime import date
from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.models import FieldsConfig, Relation, RelationType
from creme.persons import constants

from ..base import (
    Address,
    Organisation,
    _PersonsTestCase,
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)


@skipIfCustomOrganisation
class _OrganisationViewsTestCase(_PersonsTestCase):
    def _build_managed_orga(self, user, name='Bebop'):
        return Organisation.objects.create(user=user, name=name, is_managed=True)


@skipIfCustomOrganisation
class OrganisationViewsTestCase(_OrganisationViewsTestCase):
    def test_detail_view(self):
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='NERV')
        response = self.assertGET200(orga.get_absolute_url())
        self.assertTemplateUsed(response, 'persons/view_organisation.html')

    @skipIfCustomAddress
    def test_edition(self):
        user = self.login_as_root_and_get()

        name = 'Bebop'
        orga = Organisation.objects.create(user=user, name=name)
        url = orga.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        zipcode = '123456'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':                    user.pk,
                'name':                    name,
                'billing_address-zipcode': zipcode,
            },
        )
        self.assertNoFormError(response)
        self.assertRedirects(response, orga.get_absolute_url())

        edited_orga = self.refresh(orga)
        self.assertEqual(name, edited_orga.name)
        self.assertIsNotNone(edited_orga.billing_address)
        self.assertEqual(zipcode, edited_orga.billing_address.zipcode)

    def test_list_view(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')

        response = self.assertGET200(Organisation.get_lv_absolute_url())

        with self.assertNoException():
            orgas_page = response.context['page_obj']

        self.assertEqual(3, orgas_page.paginator.count)  # 3: our 2 orgas + default orga

        orgas_set = {*orgas_page.object_list}
        self.assertIn(nerv, orgas_set)
        self.assertIn(acme, orgas_set)


@skipIfCustomOrganisation
class OrganisationCreationTestCase(_OrganisationViewsTestCase):
    def test_no_address(self):
        user = self.login_as_root_and_get()

        url = reverse('persons__create_organisation')
        self.assertGET200(url)

        count = Organisation.objects.count()
        name = 'Spectre'
        description = 'DESCRIPTION'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':        user.pk,
                'name':        name,
                'description': description,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(count + 1, Organisation.objects.count())

        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertEqual(description, orga.description)
        self.assertIsNone(orga.creation_date)
        self.assertIsNone(orga.billing_address)
        self.assertIsNone(orga.shipping_address)

        self.assertRedirects(response, orga.get_absolute_url())

    @skipIfCustomAddress
    def test_addresses(self):
        "With addresses, creation date."
        user = self.login_as_root_and_get()

        name = 'Bebop'
        creation_date = date(year=2005, month=11, day=5)

        b_address = 'Mars gate'
        b_po_box = 'Mars1233546'
        b_zipcode = '9874541'
        b_city = 'Redsand'
        b_department = 'Great crater'
        b_state = 'State#3'
        b_country = 'Terran federation'

        s_address = 'Mars gate (bis)'
        response = self.client.post(
            reverse('persons__create_organisation'),
            follow=True,
            data={
                'user': user.pk,
                'name': name,
                'creation_date': creation_date,

                'billing_address-address':    b_address,
                'billing_address-po_box':     b_po_box,
                'billing_address-zipcode':    b_zipcode,
                'billing_address-city':       b_city,
                'billing_address-department': b_department,
                'billing_address-state':      b_state,
                'billing_address-country':    b_country,

                'shipping_address-address': s_address,
            },
        )
        self.assertNoFormError(response)

        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertEqual(creation_date, orga.creation_date)

        billing_address = orga.billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(b_address,    billing_address.address)
        self.assertEqual(b_po_box,     billing_address.po_box)
        self.assertEqual(b_zipcode,    billing_address.zipcode)
        self.assertEqual(b_city,       billing_address.city)
        self.assertEqual(b_department, billing_address.department)
        self.assertEqual(b_state,      billing_address.state)
        self.assertEqual(b_country,    billing_address.country)

        self.assertEqual(s_address, orga.shipping_address.address)

        self.assertContains(response, b_address)
        self.assertContains(response, s_address)

    @skipIfCustomAddress
    def test_adresses__hidden_sub_fields(self):
        "FieldsConfig on Address sub-fields."
        user = self.login_as_root_and_get()
        FieldsConfig.objects.create(
            content_type=Address,
            descriptions=[('po_box', {FieldsConfig.HIDDEN: True})],
        )

        response = self.assertGET200(reverse('persons__create_organisation'))

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('name', fields)
        self.assertIn('billing_address-address', fields)
        self.assertNotIn('billing_address-po_box',  fields)

        name = 'Bebop'

        b_address = 'Mars gate'
        b_po_box = 'Mars1233546'
        b_zipcode = '9874541'
        b_city = 'Redsand'
        b_department = 'Great crater'
        b_state = 'State#3'
        b_country = 'Terran federation'

        response = self.client.post(
            reverse('persons__create_organisation'), follow=True,
            data={
                'user': user.pk,
                'name': name,

                'billing_address-address':    b_address,
                'billing_address-po_box':     b_po_box,  # <== should not be used
                'billing_address-zipcode':    b_zipcode,
                'billing_address-city':       b_city,
                'billing_address-department': b_department,
                'billing_address-state':      b_state,
                'billing_address-country':    b_country,
            },
        )
        self.assertNoFormError(response)

        orga = self.get_object_or_fail(Organisation, name=name)
        billing_address = orga.billing_address
        self.assertIsNotNone(billing_address)
        self.assertEqual(b_address,    billing_address.address)
        self.assertEqual(b_zipcode,    billing_address.zipcode)
        self.assertEqual(b_city,       billing_address.city)
        self.assertEqual(b_department, billing_address.department)
        self.assertEqual(b_state,      billing_address.state)
        self.assertEqual(b_country,    billing_address.country)

        self.assertFalse(billing_address.po_box)

    @skipIfCustomAddress
    def test_adresses__hidden_fk(self):
        "FieldsConfig on 'billing_address' FK field."
        self.login_as_root()
        FieldsConfig.objects.create(
            content_type=Organisation,
            descriptions=[('billing_address', {FieldsConfig.HIDDEN: True})],
        )

        response = self.assertGET200(reverse('persons__create_organisation'))

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('name', fields)
        self.assertNotIn('billing_address-address', fields)
        self.assertNotIn('billing_address-po_box',  fields)


class CustomerViewsTestCase(_OrganisationViewsTestCase):
    def test_leads_customers__empty(self):
        user = self.login_as_root_and_get()

        self._build_managed_orga(user=user)
        Organisation.objects.create(user=user, name='Nerv')

        response = self.assertGET200(reverse('persons__leads_customers'))
        ctxt = response.context

        with self.assertNoException():
            orgas_page = ctxt['page_obj']
            title = ctxt['list_title']

        self.assertEqual(0, orgas_page.paginator.count)
        self.assertEqual(
            _('List of my {related_items} & {last_related}').format(
                related_items='{}, {}'.format(_('customers'), _('prospects')),
                last_related=_('suspects'),
            ),
            title,
        )

    def test_leads_customers__managed(self):
        user = self.login_as_root_and_get()

        mng_orga = self._build_managed_orga(user=user)

        create_orga = partial(Organisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')
        fsf  = create_orga(name='FSF')
        evil = create_orga(name='EvilCorp')

        def create_relation(orga, rtype_id):
            Relation.objects.create(
                user=user,
                subject_entity=orga,
                object_entity=mng_orga,
                type_id=rtype_id,
            )

        create_relation(nerv, constants.REL_SUB_CUSTOMER_SUPPLIER)
        create_relation(acme, constants.REL_SUB_PROSPECT)
        create_relation(fsf,  constants.REL_SUB_SUSPECT)

        response = self.client.get(reverse('persons__leads_customers'))
        orgas_page = response.context['page_obj']

        self.assertEqual(3, orgas_page.paginator.count)

        orgas_set = {*orgas_page.object_list}
        self.assertIn(nerv, orgas_set)
        self.assertIn(acme, orgas_set)
        self.assertIn(fsf,  orgas_set)
        self.assertNotIn(evil, orgas_set)

    def test_leads_customers__not_managed(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')
        acme = create_orga(name='Acme')

        Relation.objects.create(
            user=user,
            subject_entity=acme,
            object_entity=nerv,
            type_id=constants.REL_SUB_CUSTOMER_SUPPLIER,
        )

        response = self.client.get(reverse('persons__leads_customers'))
        self.assertEqual(0, response.context['page_obj'].paginator.count)

    def test_leads_customers__disabled_rtype__no_suspect(self):
        self.login_as_root()

        rtype = self.get_object_or_fail(
            RelationType, id=constants.REL_SUB_SUSPECT,
        )
        rtype.enabled = False
        rtype.save()

        try:
            response = self.assertGET200(reverse('persons__leads_customers'))
            ctxt = response.context

            with self.assertNoException():
                title = ctxt['list_title']
        finally:
            rtype.enabled = True
            rtype.save()

        self.assertEqual(
            _('List of my {related_items} & {last_related}').format(
                related_items=_('customers'),
                last_related=_('prospects'),
            ),
            title,
        )

    def test_leads_customers__disabled_rtype__no_prospect(self):
        self.login_as_root()

        rtype = self.get_object_or_fail(
            RelationType, id=constants.REL_SUB_PROSPECT,
        )
        rtype.enabled = False
        rtype.save()

        try:
            response = self.assertGET200(reverse('persons__leads_customers'))
            ctxt = response.context

            with self.assertNoException():
                title = ctxt['list_title']
        finally:
            rtype.enabled = True
            rtype.save()

        self.assertEqual(
            _('List of my {related_items} & {last_related}').format(
                related_items=_('customers'),
                last_related=_('suspects'),
            ),
            title,
        )

    def test_leads_customers__disabled_rtype__only_customer(self):
        self.login_as_root()

        rtypes = [
            *RelationType.objects.filter(
                id__in=[constants.REL_SUB_PROSPECT, constants.REL_SUB_SUSPECT],
            ),
        ]
        for rtype in rtypes:
            rtype.enabled = False
            rtype.save()

        try:
            response = self.assertGET200(reverse('persons__leads_customers'))
            ctxt = response.context

            with self.assertNoException():
                title = ctxt['list_title']
        finally:
            for rtype in rtypes:
                rtype.enabled = True
                rtype.save()

        self.assertEqual(
            _('List of my {related}').format(related=_('customers')),
            title,
        )

    def test_leads_customers__disabled_rtypes(self):
        self.login_as_root()

        rtypes = [
            *RelationType.objects.filter(id__in=[
                constants.REL_SUB_PROSPECT,
                constants.REL_SUB_SUSPECT,
                constants.REL_SUB_CUSTOMER_SUPPLIER,
            ]),
        ]
        for rtype in rtypes:
            rtype.enabled = False
            rtype.save()

        try:
            self.assertGET409(reverse('persons__leads_customers'))
        finally:
            for rtype in rtypes:
                rtype.enabled = True
                rtype.save()

    def test_create_customer(self):
        user = self.login_as_root_and_get()

        managed1 = self.get_object_or_fail(Organisation, is_managed=True)
        managed2 = Organisation.objects.create(user=user, name='Nerv', is_managed=True)

        url = reverse('persons__create_customer')
        context1 = self.assertGET200(url).context

        with self.assertNoException():
            fields = context1['form'].fields
            rtypes_f = fields['customers_rtypes']
            title = context1['title']

        self.assertEqual(_('Relationships'), rtypes_f.label)
        self.assertInChoices(
            value=constants.REL_SUB_CUSTOMER_SUPPLIER,
            label=_('Is a customer'),
            choices=rtypes_f.choices,
        )
        self.assertInChoices(
            value=constants.REL_SUB_PROSPECT,
            label=_('Is a prospect'),
            choices=rtypes_f.choices,
        )
        self.assertInChoices(
            value=constants.REL_SUB_SUSPECT,
            label=_('Is a suspect'),
            choices=rtypes_f.choices,
        )

        self.assertIn('customers_managed_orga', fields)
        self.assertEqual(
            pgettext('persons-related_creation', 'Create a: {}').format(
                f"{_('customer')}, {_('prospect')}, {_('suspect')}"
            ),
            title,
        )

        def post(managed, name):
            post_response = self.client.post(
                url, follow=True,
                data={
                    'user':  user.id,
                    'name':  name,

                    'customers_managed_orga': managed.id,
                    'customers_rtypes': [constants.REL_SUB_SUSPECT],
                },
            )
            self.assertNoFormError(post_response)

            return self.get_object_or_fail(Organisation, name=name)

        # ----
        orga1 = post(managed2, name='Bebop')
        self.assertHaveNoRelation(orga1, constants.REL_SUB_CUSTOMER_SUPPLIER, managed2)
        self.assertHaveNoRelation(orga1, constants.REL_SUB_PROSPECT,          managed2)
        self.assertHaveRelation(orga1, constants.REL_SUB_SUSPECT, managed2)

        self.assertHaveNoRelation(orga1, constants.REL_SUB_CUSTOMER_SUPPLIER, managed1)
        self.assertHaveNoRelation(orga1, constants.REL_SUB_PROSPECT,          managed1)
        self.assertHaveNoRelation(orga1, constants.REL_SUB_SUSPECT,           managed1)

        # ----
        orga2 = post(managed1, name='Red dragons')
        self.assertHaveRelation(subject=orga2, type=constants.REL_SUB_SUSPECT, object=managed1)
        self.assertHaveNoRelation(subject=orga2, type=constants.REL_SUB_SUSPECT, object=managed2)

    def test_create_customer__regular_user(self):
        user = self.login_as_persons_user(creatable_models=[Organisation])
        self.add_credentials(user.role, all='!LINK', own='*')

        managed1 = self.get_object_or_fail(Organisation, is_managed=True)
        self.assertFalse(user.has_perm_to_link(managed1))

        managed2 = Organisation.objects.create(user=user, name='Nerv', is_managed=True)
        self.assertTrue(user.has_perm_to_link(managed2))

        url = reverse('persons__create_customer')
        name = 'Bebop'
        data = {
            'user': user.id,
            'name': name,

            'customers_managed_orga': managed1.id,
            'customers_rtypes': [constants.REL_SUB_SUSPECT],
        }
        response1 = self.assertPOST200(url, follow=True, data=data)
        self.assertFormError(
            response1.context['form'],
            field='customers_managed_orga',
            errors=_('You are not allowed to link this entity: {}').format(managed1),
        )

        # ---
        response2 = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                'user': self.get_root_user().id,  # <==
                'customers_managed_orga': managed2.id,
            },
        )
        self.assertFormError(
            response2.context['form'],
            field='user',
            errors=_(
                'You are not allowed to link with the «{models}» of this user.'
            ).format(models=_('Organisations')),
        )

        # ---
        response3 = self.assertPOST200(
            url, follow=True,
            data={**data, 'customers_managed_orga': managed2.id},
        )
        self.assertNoFormError(response3)

        orga = self.get_object_or_fail(Organisation, name=name)
        self.assertHaveRelation(subject=orga, type=constants.REL_SUB_SUSPECT, object=managed2)

    def test_create_customer__forbidden(self):
        "Can never link."
        user = self.login_as_standard(creatable_models=[Organisation])
        self.add_credentials(user.role, all='!LINK')
        self.assertPOST403(reverse('persons__create_customer'))

    def test_create_customer__disabled_rtype__no_suspect(self):
        self.login_as_root()

        rtype = self.get_object_or_fail(
            RelationType, id=constants.REL_SUB_SUSPECT,
        )
        rtype.enabled = False
        rtype.save()

        try:
            context = self.assertGET200(reverse('persons__create_customer')).context

            with self.assertNoException():
                rtypes_f = context['form'].fields['customers_rtypes']
                title = context['title']
        finally:
            rtype.enabled = True
            rtype.save()

        self.assertEqual(
            pgettext('persons-related_creation', 'Create a: {}').format(
                f"{_('customer')}, {_('prospect')}"
            ),
            title,
        )

        self.assertInChoices(
            value=constants.REL_SUB_CUSTOMER_SUPPLIER,
            label=_('Is a customer'),
            choices=rtypes_f.choices,
        )
        self.assertInChoices(
            value=constants.REL_SUB_PROSPECT,
            label=_('Is a prospect'),
            choices=rtypes_f.choices,
        )
        self.assertNotInChoices(
            value=constants.REL_SUB_SUSPECT, choices=rtypes_f.choices,
        )

    def test_create_customer__disabled_rtypes(self):
        self.login_as_root()

        rtypes = [
            *RelationType.objects.filter(id__in=[
                constants.REL_SUB_PROSPECT,
                constants.REL_SUB_SUSPECT,
                constants.REL_SUB_CUSTOMER_SUPPLIER,
            ]),
        ]
        for rtype in rtypes:
            rtype.enabled = False
            rtype.save()

        try:
            self.assertGET409(reverse('persons__create_customer'))
        finally:
            for rtype in rtypes:
                rtype.enabled = True
                rtype.save()


class ManagedOrganisationViewsTestCase(_OrganisationViewsTestCase):
    def test_set_orga_as_managed(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Bebop')
        orga2 = create_orga(name='Swordfish')
        orga3 = create_orga(name='RedTail')

        url = reverse('persons__orga_set_managed')
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add-popup.html')

        get_ctxt = response1.context.get
        self.assertEqual(_('Add some managed organisations'), get_ctxt('title'))
        self.assertEqual(_('Save the modifications'),         get_ctxt('submit_label'))

        # ---
        response2 = self.client.post(
            url,
            data={'organisations': self.formfield_value_multi_creator_entity(orga1, orga2)},
        )
        self.assertNoFormError(response2)

        self.assertTrue(self.refresh(orga1).is_managed)
        self.assertTrue(self.refresh(orga2).is_managed)
        self.assertFalse(self.refresh(orga3).is_managed)

        # Managed Organisations are excluded
        response3 = self.assertPOST200(
            url,
            data={'organisations': self.formfield_value_multi_creator_entity(orga1)},
        )
        self.assertFormError(
            response3.context['form'],
            field='organisations',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': orga1},
        )

    def test_set_orga_as_managed__regular_user(self):
        self.login_as_persons_user(
            allowed_apps=['creme_core'],
            admin_4_apps=['creme_core'],
        )
        self.assertGET200(reverse('persons__orga_set_managed'))

    def test_set_orga_as_managed__admin_perm(self):
        "Admin permission needed."
        self.login_as_persons_user(
            allowed_apps=['creme_core'],
            # admin_4_apps=['creme_core'],
        )
        self.assertGET403(reverse('persons__orga_set_managed'))

    def test_set_orga_as_not_managed(self):
        user = self.login_as_root_and_get()

        orga1 = self.get_alone_element(Organisation.objects.filter(is_managed=True))
        orga2 = self._build_managed_orga(user=user)

        url = reverse('persons__orga_unset_managed')
        data = {'id': orga2.id}
        self.assertGET405(url)
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertFalse(self.refresh(orga2).is_managed)

        self.assertPOST409(url, data={'id': orga1.id})  # At least 1 managed organisation
        self.assertTrue(self.refresh(orga1).is_managed)
