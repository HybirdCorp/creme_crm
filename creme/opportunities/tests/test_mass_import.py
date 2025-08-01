from django.contrib.contenttypes.models import ContentType
from django.db.models import Max
from django.test.utils import override_settings
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.models import Currency
from creme.creme_core.tests.views.base import MassImportBaseTestCaseMixin
from creme.documents import get_document_model
from creme.opportunities.models import SalesPhase
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
class MassImportTestCase(MassImportBaseTestCaseMixin, OpportunitiesBaseTestCase):
    lvimport_data = {
        'step': 1,
        # 'document': doc.id,
        # has_header

        # 'user':    user.id,
        # 'emitter': emitter1.id,

        # 'name_colselect':            1,
        # 'estimated_sales_colselect': 3,
        # 'made_sales_colselect':      4,

        # 'sales_phase_colselect': 2,
        # 'sales_phase_create':    True,
        # 'sales_phase_defval':    sp5.pk,

        # 'target_persons_organisation_colselect': 5,
        # 'target_persons_organisation_create':    True,
        # 'target_persons_contact_colselect':      6,
        # 'target_persons_contact_create':         True,

        'currency_colselect': 0,

        'reference_colselect':              0,
        'chance_to_win_colselect':          0,
        'expected_closing_date_colselect':  0,
        'closing_date_colselect':           0,
        'origin_colselect':                 0,
        'description_colselect':            0,
        'first_action_date_colselect':      0,

        # 'property_types',
        # 'fixed_relations',
        # 'dyn_relations',
    }

    @skipIfCustomContact
    def test_mass_import01(self):
        user = self.login_as_root_and_get()

        count = Opportunity.objects.count()

        # Opportunity #1
        emitter1 = Organisation.objects.filter(is_managed=True)[0]
        target1  = Organisation.objects.create(user=user, name='Acme')
        sp1 = SalesPhase.objects.create(name='Testphase - test_csv_import01')

        max_order = SalesPhase.objects.aggregate(max_order=Max('order'))['max_order']

        # Opportunity #2
        target2_name = 'Black label society'
        sp2_name = 'IAmNotSupposedToAlreadyExist'
        self.assertFalse(SalesPhase.objects.filter(name=sp2_name))

        # Opportunity #3
        target3 = Contact.objects.create(user=user, first_name='Mike', last_name='Danton')

        # Opportunity #4
        target4_last_name = 'Renegade'

        # Opportunity #5
        sp5 = SalesPhase.objects.all()[1]

        lines = [
            ('Opp01', sp1.name, '1000', '2000', target1.name, ''),
            ('Opp02', sp2_name, '100',  '200',  target2_name, ''),
            ('Opp03', sp1.name, '100',  '200',  '',           target3.last_name),
            ('Opp04', sp1.name, '100',  '200',  '',           target4_last_name),
            ('Opp05', '',       '100',  '200',  target1.name, ''),
            # TODO emitter by name
        ]

        doc = self._build_csv_doc(lines, user=user)
        url = self._build_import_url(Opportunity)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(
            url,
            data={
                'step':     0,
                'document': doc.id,
                # has_header
            },
        ))

        currency = Currency.objects.all()[0]
        response = self.client.post(
            url, follow=True,
            data={
                **self.lvimport_data,
                'document': doc.id,
                'user': user.id,
                'emitter': emitter1.id,

                'name_colselect': 1,
                'estimated_sales_colselect': 3,
                'made_sales_colselect': 4,

                'sales_phase_colselect': 2,
                'sales_phase_subfield': 'name',
                'sales_phase_create': True,
                'sales_phase_defval': sp5.pk,

                'currency_defval': currency.id,

                'target_persons_organisation_colselect': 5,
                'target_persons_organisation_create': True,
                'target_persons_contact_colselect': 6,
                'target_persons_contact_create': True,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self._assertNoResultError(self._get_job_results(job))

        self.assertEqual(count + len(lines), Opportunity.objects.count())

        opp1 = self.get_object_or_fail(Opportunity, name='Opp01')
        self.assertEqual(user, opp1.user)
        self.assertEqual(1000, opp1.estimated_sales)
        self.assertEqual(2000, opp1.made_sales)
        self.assertEqual(1,    SalesPhase.objects.filter(name=sp1.name).count())
        self.assertEqual(sp1,  opp1.sales_phase)
        self.assertEqual(currency, opp1.currency)
        self.assertFalse(opp1.reference)
        self.assertIsNone(opp1.origin)
        self.assertEqual(emitter1, opp1.emitter)
        self.assertEqual(target1,  opp1.target)

        sp2 = self.get_object_or_fail(SalesPhase, name=sp2_name)
        self.assertEqual(max_order + 1, sp2.order)

        opp2 = self.get_object_or_fail(Opportunity, name='Opp02')
        self.assertEqual(user, opp2.user)
        self.assertEqual(100,  opp2.estimated_sales)
        self.assertEqual(200,  opp2.made_sales)
        self.assertEqual(sp2,  opp2.sales_phase)
        self.assertEqual(
            self.get_object_or_fail(Organisation, name=target2_name),
            opp2.target,
        )

        opp3 = self.get_object_or_fail(Opportunity, name='Opp03')
        self.assertEqual(target3, opp3.target)

        opp4 = self.get_object_or_fail(Opportunity, name='Opp04')
        self.assertEqual(
            self.get_object_or_fail(Contact, last_name=target4_last_name),
            opp4.target
        )

        opp5 = self.get_object_or_fail(Opportunity, name='Opp05')
        self.assertEqual(sp5, opp5.sales_phase)

    def test_mass_import02(self):
        "SalesPhase creation forbidden by the user."
        user = self.login_as_root_and_get()

        count = Opportunity.objects.count()

        emitter = Organisation.objects.filter(is_managed=True)[0]
        target1 = Organisation.objects.create(user=user, name='Acme')

        sp1_name = 'IAmNotSupposedToAlreadyExist'
        self.assertFalse(SalesPhase.objects.filter(name=sp1_name))

        lines = [('Opp01', sp1_name, '1000', '2000', target1.name, '')]
        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            self._build_import_url(Opportunity),
            follow=True,
            data={
                **self.lvimport_data,
                'document': doc.id,
                'user': user.id,
                'emitter': emitter.id,

                'name_colselect': 1,
                'estimated_sales_colselect': 3,
                'made_sales_colselect': 4,

                'sales_phase_colselect': 2,
                'sales_phase_subfield': 'name',
                'sales_phase_create': '',  # <=======
                # sales_phase_defval=[...],  # <=======

                'currency_defval': Currency.objects.first().id,

                'target_persons_organisation_colselect': 5,
                'target_persons_organisation_create': True,
                'target_persons_contact_colselect': 6,
                'target_persons_contact_create': True,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        self.assertEqual(count, Opportunity.objects.count())
        self.assertFalse(SalesPhase.objects.filter(name=sp1_name).count())

        result = self.get_alone_element(self._get_job_results(job))
        self.assertIsNone(result.entity)
        # 2 errors: retrieving of SalesPhase failed, creation of Opportunity failed
        self.assertEqual(2, len(result.messages))

        vname = _('Opportunity')
        self.assertListEqual(
            [
                _('No «{model}» has been created.').format(model=vname),
                _('No «{model}» has been updated.').format(model=vname),
                ngettext(
                    '{count} line in the file.',
                    '{count} lines in the file.',
                    1
                ).format(count=1),
            ],
            job.stats,
        )

    def test_mass_import03(self):
        "SalesPhase is required."
        user = self.login_as_root_and_get()

        emitter = Organisation.objects.filter(is_managed=True)[0]
        target  = Organisation.objects.create(user=user, name='Acme')

        lines = [('Opp01', '1000', '2000', target.name)]
        doc = self._build_csv_doc(lines, user=user)
        response = self.assertPOST200(
            self._build_import_url(Opportunity),
            data={
                **self.lvimport_data,
                'document': doc.id,
                'user': user.id,
                'emitter': emitter.id,

                'name_colselect': 1,
                'estimated_sales_colselect': 2,
                'made_sales_colselect': 3,

                'sales_phase_colselect': 0,  # <=======
                'sales_phase_subfield': 'name',
                'sales_phase_create': '',
                # sales_phase_defval=[...],

                'target_persons_organisation_colselect': 4,
                'target_persons_organisation_create': '',
                'target_persons_contact_colselect': 0,
                'target_persons_contact_create': '',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='sales_phase', errors=_('This field is required.'),
        )

    def test_mass_import04(self):
        "Creation of Organisation/Contact is not wanted."
        user = self.login_as_root_and_get()

        count = Opportunity.objects.count()
        emitter = Organisation.objects.filter(is_managed=True)[0]

        orga_name = 'NERV'
        contact_name = 'Ikari'
        lines = [
            ('Opp01', 'SP name', '1000', '2000', orga_name, ''),
            ('Opp02', 'SP name', '1000', '2000', '',        contact_name),
        ]
        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            self._build_import_url(Opportunity),
            follow=True,
            data={
                **self.lvimport_data,
                'document': doc.id,
                'user': user.id,
                'emitter': emitter.id,

                'name_colselect': 1,
                'estimated_sales_colselect': 3,
                'made_sales_colselect': 4,

                'sales_phase_colselect': 2,
                'sales_phase_subfield': 'name',
                'sales_phase_create': True,

                'currency_defval': Currency.objects.first().id,

                'target_persons_organisation_colselect': 5,
                'target_persons_organisation_create': '',  # <===
                'target_persons_contact_colselect': 6,
                'target_persons_contact_create': '',  # <===
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)

        self.assertEqual(count, Opportunity.objects.count())
        self.assertFalse(Organisation.objects.filter(name=orga_name))
        self.assertFalse(Contact.objects.filter(last_name=contact_name))

        # TODO
        # errors = list(form.import_errors)
        # # 4 errors: retrieving of Organisation/Contact failed, creation of Opportunities failed
        # self.assertEqual(4, len(errors))
        # self.assertIn(_('Organisation'), errors[0].message)
        # self.assertIn(_('Contact'),      errors[2].message)

        # self.assertEqual(0, form.imported_objects_count)

    @override_settings(MAX_JOBS_PER_USER=2)
    def test_mass_import05(self):
        "Creation credentials for Organisation & SalesPhase are forbidden."
        user = self.login_as_standard(
            allowed_apps=['persons', 'documents', 'opportunities'],
            creatable_models=[Opportunity, get_document_model()],  # Not Organisation
        )
        role = user.role
        self.add_credentials(role, all='*')

        # TODO: factorise
        emitter = Organisation.objects.filter(is_managed=True)[0]
        doc = self._build_csv_doc(
            [('Opp01', '1000', '2000', 'Acme', 'New phase')],
            user=user,
        )
        url = self._build_import_url(Opportunity)
        data = {
            **self.lvimport_data,
            'document': doc.id,
            'user': user.id,
            'emitter': emitter.id,

            'name_colselect': 1,
            'estimated_sales_colselect': 2,
            'made_sales_colselect': 3,

            'sales_phase_colselect': 5,
            'sales_phase_subfield': 'name',
            'sales_phase_create': True,

            'currency_defval': Currency.objects.first().id,

            'target_persons_organisation_colselect': 4,
            # 'target_persons_organisation_create': True,
            'target_persons_contact_colselect': 0,
            'target_persons_contact_create': '',
        }

        response1 = self.assertPOST200(
            url, data={**data, 'target_persons_organisation_create': True},
        )
        form1 = response1.context['form']
        self.assertFormError(
            form1,
            field='target',
            errors=_(
                'You are not allowed to create: %(model)s'
            ) % {'model': _('Organisation')},
        )
        self.assertFormError(
            form1, field='sales_phase', errors='You can not create instances',
        )

        # ---
        role.admin_4_apps = ['opportunities']
        role.save()
        self.assertNoFormError(self.client.post(url, follow=True, data=data))

        # ---
        role.creatable_ctypes.add(ContentType.objects.get_for_model(Organisation))
        self.assertNoFormError(self.client.post(
            url, follow=True, data={**data, 'target_persons_organisation_create': True},
        ))

    @skipIfCustomOrganisation
    def test_mass_import06(self):
        "Update."
        user = self.login_as_root_and_get()

        opp1, target1, emitter = self._create_opportunity_n_organisations(user=user)
        target2 = Organisation.objects.create(user=user, name='Acme')

        count = Opportunity.objects.count()

        create_phase = SalesPhase.objects.create
        phase1 = create_phase(name='Testphase - test_csv_import06 #1')
        phase2 = create_phase(name='Testphase - test_csv_import06 #2')

        opp1.sales_phase = phase1
        opp1.save()

        doc = self._build_csv_doc(
            [
                # Should be updated
                (opp1.name, '1000', '2000', target2.name, phase1.name),

                # Phase is different => not updated
                (opp1.name, '1000', '2000', target2.name, phase2.name),
            ],
            user=user,
        )
        response = self.client.post(
            self._build_import_url(Opportunity),
            follow=True,
            data={
                **self.lvimport_data,
                'document': doc.id,
                'user': user.id,
                'emitter': emitter.id,

                'key_fields': ['name', 'sales_phase'],

                'name_colselect': 1,
                'estimated_sales_colselect': 2,
                'made_sales_colselect': 3,

                'sales_phase_colselect': 5,
                'sales_phase_subfield': 'name',

                'currency_defval': Currency.objects.first().id,

                'target_persons_organisation_colselect': 4,
                'target_persons_organisation_create': True,
                'target_persons_contact_colselect': 0,
                'target_persons_contact_create': '',
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(count + 1, Opportunity.objects.count())

        with self.assertNoException():
            opp2 = Opportunity.objects.exclude(id=opp1.id).get(name=opp1.name)

        self.assertEqual(target2, opp2.target)

        self._assertNoResultError(self._get_job_results(job))

        opp1 = self.refresh(opp1)
        self.assertEqual(target2, opp1.target)
