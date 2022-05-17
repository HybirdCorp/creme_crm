# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    FakeActivity,
    FakeContact,
    FakeImage,
    FakeOrganisation,
    Relation,
    RelationType,
    SemiFixedRelationType,
)

from .base import ViewsTestCase


class RelationViewsTestCase(ViewsTestCase):
    ADD_FROM_PRED_URL = reverse('creme_core__save_relations')
    SELECTION_URL     = reverse('creme_core__select_entities_to_link')

    @staticmethod
    def _build_get_ctypes_url(rtype_id):
        return reverse('creme_core__ctypes_compatible_with_rtype', args=(rtype_id,))

    def test_get_ctypes_of_relation01(self):
        "No sort."
        self.login()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject__JSP01_3', 'is a customer of', [FakeContact]),
            ('test-object__JSP01_4',  'is a supplier of', [FakeContact, FakeOrganisation]),
        )[0]

        response = self.assertGET200(
            self._build_get_ctypes_url(rtype.id),
            data={'fields': ['id', 'unicode']},
        )
        self.assertEqual('application/json', response['Content-Type'])

        json_data = response.json()
        get_ct = ContentType.objects.get_for_model
        self.assertIsList(json_data, length=2)
        self.assertIn(
            [get_ct(FakeContact).id, str(FakeContact._meta.verbose_name)],
            json_data,
        )
        self.assertIn(
            [get_ct(FakeOrganisation).id, str(FakeOrganisation._meta.verbose_name)],
            json_data,
        )

    def test_get_ctypes_of_relation02(self):
        self.login()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar1', 'is loving'),
            ('test-object_foobar1',  'is loved by'),
        )[0]
        response = self.assertGET200(
            self._build_get_ctypes_url(rtype.id),
            data={'fields': ['id']},
        )
        self.assertEqual('application/json', response['Content-Type'])

        json_data = response.json()
        get_ct = ContentType.objects.get_for_model
        self.assertIn([get_ct(FakeContact).id],      json_data)
        self.assertIn([get_ct(FakeOrganisation).id], json_data)
        self.assertIn([get_ct(FakeActivity).id],     json_data)

    def test_get_ctypes_of_relation03(self):
        "'sort' argument."
        self.login()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'foo'),
            ('test-object_foobar',  'bar', [FakeImage, FakeContact]),
        )[0]

        response = self.assertGET200(
            self._build_get_ctypes_url(rtype.id),
            data={
                'fields': ['id', 'unicode'],
                'sort':   'unicode',
            },
        )

        c_vname = str(FakeContact._meta.verbose_name)
        i_vname = str(FakeImage._meta.verbose_name)
        get_ct = ContentType.objects.get_for_model

        expected = [[get_ct(FakeContact).id, c_vname]]
        expected.insert(
            0 if i_vname < c_vname else 1,
            [get_ct(FakeImage).id,  i_vname]
        )
        self.assertEqual(response.json(), expected)

    def _aux_test_add_relations(self, is_superuser=True):
        user = self.login(is_superuser)

        create_contact = partial(FakeContact.objects.create, user=user)
        self.subject01 = create_contact(first_name='Laharl', last_name='Overlord')
        self.subject02 = create_contact(first_name='Etna',   last_name='Devil')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        self.object01 = create_orga(name='orga01')
        self.object02 = create_orga(name='orga02')

        self.ct_id = ContentType.objects.get_for_model(CremeEntity).id

        create_rtype = RelationType.objects.smart_update_or_create
        self.rtype01 = create_rtype(
            ('test-subject_foobar1', 'is loving'),
            ('test-object_foobar1',  'is loved by'),
        )[0]
        self.rtype02 = create_rtype(
            ('test-subject_foobar2', 'is hating'),
            ('test-object_foobar2',  'is hated by'),
        )[0]

    # TODO: use assertRelationCount instead ?
    def assertEntiTyHasRelation(self, subject_entity, rtype, object_entity):
        self.assertTrue(
            subject_entity.relations
                          .filter(type=rtype, object_entity=object_entity.id)
                          .exists()
        )

    @staticmethod
    def _build_add_url(subject):
        return reverse('creme_core__create_relations', args=(subject.id,))

    @staticmethod
    def count_relations(rtype):
        return Relation.objects.filter(type=rtype).count()

    def assert_relation_count(self, counts):
        assertEqual = self.assertEqual
        rcount = self.count_relations
        for rtype, count in counts:
            assertEqual(count, rcount(rtype))

    def test_add_relations01(self):
        self._aux_test_add_relations()

        subject = self.subject01
        self.assertFalse(subject.relations.all())

        url = self._build_add_url(subject)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('Relationships for «{entity}»').format(entity=subject),
            context.get('title'),
        )
        self.assertEqual(_('Save the relationships'), context.get('submit_label'))

        # ---
        response = self.client.post(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (self.rtype01.id, self.object01),
                    (self.rtype02.id, self.object02),
                ),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())
        self.assertEntiTyHasRelation(subject, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(subject, self.rtype02, self.object02)

    def test_add_relations_not_superuser01(self):
        user = self.login(is_superuser=False)
        subject = CremeEntity.objects.create(user=user)
        self.assertGET200(self._build_add_url(subject))

    def test_add_relations_not_superuser02(self):
        "Credentials problems."
        self.login(is_superuser=False)
        self._set_all_creds_except_one(excluded=EntityCredentials.LINK)
        subject = CremeEntity.objects.create(user=self.other_user)
        self.assertGET403(self._build_add_url(subject))

    def test_add_relations03(self):
        "Credentials problems (no link credentials)."
        self._aux_test_add_relations(is_superuser=False)
        self._set_all_creds_except_one(excluded=EntityCredentials.LINK)

        unlinkable = CremeEntity.objects.create(user=self.other_user)
        self.assertTrue(self.user.has_perm_to_view(unlinkable))
        self.assertFalse(self.user.has_perm_to_link(unlinkable))

        response = self.client.post(
            self._build_add_url(self.subject01),
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (self.rtype01.id, self.object01),
                    (self.rtype02.id, unlinkable),
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'relations',
            _('Some entities are not linkable: {}').format(unlinkable),
        )
        self.assertEqual(0, self.subject01.relations.count())

    def test_add_relations04(self):
        "Duplicates -> error."
        self._aux_test_add_relations()

        response = self.client.post(
            self._build_add_url(self.subject01),
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (self.rtype01.id, self.object01),
                    (self.rtype02.id, self.object02),
                    (self.rtype01.id, self.object01),
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'relations',
            _('There are duplicates: %(duplicates)s') % {
                'duplicates': f'({self.rtype01}, {self.object01})',
            },
        )

    def test_add_relations05(self):
        "Do not recreate existing relationships."
        self._aux_test_add_relations()

        Relation.objects.create(
            user=self.user,
            subject_entity=self.subject01,
            type=self.rtype02,
            object_entity=self.object02,
        )
        response = self.client.post(
            self._build_add_url(self.subject01),
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (self.rtype01.id, self.object01),
                    (self.rtype02.id, self.object02),
                ),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(2, self.subject01.relations.count())  # Not 3

    def test_add_relations06(self):
        "Cannot link an entity to itself."
        self._aux_test_add_relations()

        subject = self.subject01
        response = self.client.post(
            self._build_add_url(subject),
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    [self.rtype01.id, subject],
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'relations',
            _('An entity can not be linked to itself : %(entities)s') % {
                'entities': subject,
            },
        )

    def test_add_relations07(self):
        "CremeProperty constraints on subject."
        self._aux_test_add_relations()

        subject = self.subject01

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='Is strong')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='Is cool')
        ptype03 = create_ptype(str_pk='test-prop_foobar03', text='Is smart')

        # NB: not ptype03
        create_prop = partial(CremeProperty.objects.create, creme_entity=subject)
        create_prop(type=ptype01)
        create_prop(type=ptype02)

        # Constraint KO & OK
        create_rtype = RelationType.objects.smart_update_or_create
        rtype03 = create_rtype(
            ('test-subject_foobar3', 'rules', [FakeContact], [ptype01, ptype03]),
            ('test-object_foobar3',  'is ruled by'),
        )[0]
        rtype04 = create_rtype(
            ('test-subject_foobar4', 'is the hero of', [FakeContact], [ptype02]),
            ('test-object_foobar4',  'has a hero which is'),
        )[0]

        url = self._build_add_url(subject)
        response = self.assertPOST200(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    [rtype03.id, self.object01],
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'relations',
            _('«%(subject)s» must have a property in «%(properties)s» '
              'in order to use the relationship «%(predicate)s»') % {
                'subject':    subject,
                'properties': f'{ptype03}/{ptype01}',
                'predicate':  rtype03.predicate,
            },
        )

        response = self.client.post(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    [rtype04.id, self.object01],
                ),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(1, subject.relations.count())

    def test_add_relations08(self):
        "'exclude' parameter."
        self._aux_test_add_relations()

        rtype01 = self.rtype01
        response = self.client.get(
            self._build_add_url(self.subject01), data={'exclude': [rtype01.id]},
        )

        with self.assertNoException():
            rtypes = response.context['form'].fields['relations'].allowed_rtypes

        self.assertIn(self.rtype02, rtypes)
        self.assertNotIn(rtype01, rtypes)

    def test_add_relations_with_semi_fixed01(self):
        "Only semi fixed."
        self._aux_test_add_relations()

        subject = self.subject01

        # Constraint OK & KO
        create_rtype = RelationType.objects.smart_update_or_create
        rtype03 = create_rtype(
            ('test-subject_foobar3', 'is hating orga',     [FakeContact]),
            ('test-object_foobar3',  '(orga) is hated by', [FakeOrganisation]),
        )[0]
        rtype04 = create_rtype(
            # The subject cannot be a Contact
            ('test-subject_foobar4', 'has fired', [FakeOrganisation]),
            ('test-object_foobar4',  'has been fired by'),
        )[0]

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(
            predicate='Related to "object01"',
            relation_type=self.rtype01, object_entity=self.object01,
        )
        sfrt2 = create_sfrt(
            predicate='Related to "object02"',
            relation_type=self.rtype02, object_entity=self.object02,
        )
        sfrt3 = create_sfrt(
            predicate='Linked to "object02"',
            relation_type=rtype03, object_entity=self.object02,
        )
        create_sfrt(
            predicate='Linked to "object01"',
            relation_type=rtype04, object_entity=self.object01,
        )  # Should not be proposed

        url = self._build_add_url(subject)

        with self.assertNoException():
            semifixed_rtypes = self.client.get(url).context['form'].fields['semifixed_rtypes']

        self.assertListEqual(
            [
                (sfrt3.id, sfrt3.predicate),
                (sfrt1.id, sfrt1.predicate),
                (sfrt2.id, sfrt2.predicate),
            ],
            [*semifixed_rtypes.choices],
        )

        self.assertNoFormError(
            self.client.post(url, data={'semifixed_rtypes': [sfrt1.id, sfrt2.id]})
        )
        self.assertEqual(2, subject.relations.count())
        self.assertEntiTyHasRelation(subject, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(subject, self.rtype02, self.object02)

    def test_add_relations_with_semi_fixed02(self):
        "Semi-fixed & not semi-fixed."
        self._aux_test_add_relations()

        subject = self.subject01

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(
            predicate='Related to "object01"',
            relation_type=self.rtype01,
            object_entity=self.object01,
        )
        sfrt2 = create_sfrt(
            predicate='Related to "object02"',
            relation_type=self.rtype02,
            object_entity=self.object02,
        )
        create_sfrt(
            predicate='Related to "subject01"',
            relation_type=self.rtype02,
            object_entity=self.subject01,
        )  # Should not be proposed

        url = self._build_add_url(subject)
        context = self.client.get(url).context

        with self.assertNoException():
            choices = context['form'].fields['semifixed_rtypes'].choices

        self.assertInChoices(value=sfrt1.id, label=str(sfrt1), choices=choices)
        self.assertInChoices(value=sfrt2.id, label=str(sfrt2), choices=choices)

        response = self.client.post(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    [self.rtype01.id, self.object01],
                ),
                'semifixed_rtypes': [sfrt2.id],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())
        self.assertEntiTyHasRelation(subject, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(subject, self.rtype02, self.object02)

    def test_add_relations_with_semi_fixed03(self):
        "One relationship at least (semi-fixed or not semi-fixed)."
        self._aux_test_add_relations()

        response = self.assertPOST200(self._build_add_url(self.subject01))
        self.assertFormError(
            response, 'form', None,
            _('You must give one relationship at least.'),
        )

    def test_add_relations_with_semi_fixed04(self):
        "Collision fixed / not fixed."
        self._aux_test_add_relations()

        subject = self.subject01

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(
            predicate='Related to "object01"',
            relation_type=self.rtype01, object_entity=self.object01,
        )
        sfrt2 = create_sfrt(
            predicate='Related to "object02"',
            relation_type=self.rtype02, object_entity=self.object02,
        )

        response = self.client.post(
            self._build_add_url(subject),
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    [self.rtype01.id, self.object01],
                ),
                'semifixed_rtypes': [sfrt1.id, sfrt2.id],
            },
        )
        self.assertFormError(
            response, 'form', None,
            _('There are duplicates: %(duplicates)s') % {
                'duplicates': f'({self.rtype01}, {self.object01})',
            },
        )

    def test_add_relations_with_semi_fixed05(self):
        "Filter not linkable entities."
        self._aux_test_add_relations(is_superuser=False)
        self._set_all_creds_except_one(excluded=EntityCredentials.LINK)

        unlinkable = CremeEntity.objects.create(user=self.other_user)

        create_sfrt = SemiFixedRelationType.objects.create
        create_sfrt(
            predicate='Related to "unlinkable"',
            relation_type=self.rtype01,
            object_entity=unlinkable,  # <===
        )
        sfrt2 = create_sfrt(
            predicate='Related to "object02"',
            relation_type=self.rtype02,
            object_entity=self.object02,
        )

        response = self.assertGET200(self._build_add_url(self.subject01))

        with self.assertNoException():
            sfrt_field = response.context['form'].fields['semifixed_rtypes']

        self.assertListEqual([(sfrt2.id, sfrt2.predicate)], [*sfrt_field.choices])

    def test_add_relations_with_semi_fixed06(self):
        "CremeProperty constraints on subject."
        self._aux_test_add_relations()

        subject = self.subject01

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='Is strong')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='Is cool')

        CremeProperty.objects.create(type=ptype02, creme_entity=subject)

        # Constraint OK & KO
        create_rtype = RelationType.objects.smart_update_or_create
        rtype03 = create_rtype(
            ('test-subject_foobar3', 'rules', [FakeContact], [ptype01]),
            ('test-object_foobar3',  'is ruled by'),
        )[0]
        rtype04 = create_rtype(
            ('test-subject_foobar4', 'is the hero of', [FakeContact], [ptype02]),
            ('test-object_foobar4',  'has a hero which is'),
        )[0]

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(
            predicate='Rules "object01"',
            relation_type=rtype03, object_entity=self.object01,
        )
        sfrt2 = create_sfrt(
            predicate='Is the hero of "object02"',
            relation_type=rtype04, object_entity=self.object02,
        )

        url = self._build_add_url(subject)
        response = self.assertPOST200(url, data={'semifixed_rtypes': [sfrt1.id]})
        self.assertFormError(
            response, 'form', 'semifixed_rtypes',
            _('«%(subject)s» must have the property «%(property)s» '
              'in order to use the relationship «%(predicate)s»') % {
                'subject':    subject,
                'property':   ptype01,
                'predicate':  rtype03.predicate,
            },
        )

        response = self.client.post(url, data={'semifixed_rtypes': [sfrt2.id]})
        self.assertNoFormError(response)
        self.assertEqual(1, subject.relations.count())

    @staticmethod
    def _build_narrowed_add_url(subject, rtype):
        return reverse('creme_core__create_relations', args=(subject.id, rtype.id))

    def test_add_relations_narrowedtype01(self):
        self._aux_test_add_relations()

        rtype = self.rtype01
        subject = self.subject01
        url = self._build_narrowed_add_url(subject, rtype)
        self.assertGET200(url)

        response = self.client.post(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (rtype.id, self.object01),
                    (rtype.id, self.object02),
                ),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())
        self.assertEntiTyHasRelation(subject, rtype, self.object01)
        self.assertEntiTyHasRelation(subject, rtype, self.object02)

    def test_add_relations_narrowedtype02(self):
        "Validation error."
        self._aux_test_add_relations()

        response = self.client.post(
            self._build_narrowed_add_url(self.subject01, self.rtype01),
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (self.rtype01.id, self.object01),
                    # RelationType not allowed:
                    (self.rtype02.id, self.object02),
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'relations',
            _(
                'This type of relationship causes a constraint error '
                '(id="%(rtype_id)s").'
            ) % {'rtype_id': self.rtype02.id},
        )

    def test_add_relations_narrowedtype03(self):
        self._aux_test_add_relations()

        allowed_rtype = self.rtype01
        subject = self.subject01

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(
            predicate='Related to "object01"',
            relation_type=allowed_rtype,
            object_entity=self.object01,
        )
        create_sfrt(
            predicate='Related to "object02"',
            relation_type=self.rtype02,
            object_entity=self.object02,
        )

        url = self._build_narrowed_add_url(subject, allowed_rtype)

        with self.assertNoException():
            sfrt_field = self.client.get(url).context['form'].fields['semifixed_rtypes']

        self.assertListEqual([(sfrt1.id, sfrt1.predicate)], [*sfrt_field.choices])

        response = self.client.post(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    [allowed_rtype.id, self.object02],
                ),
                'semifixed_rtypes': [sfrt1.id],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())
        self.assertEntiTyHasRelation(subject, allowed_rtype, self.object01)
        self.assertEntiTyHasRelation(subject, allowed_rtype, self.object02)

    def test_add_relations_narrowedtype04(self):
        "Internal type => error."
        user = self.login()
        subject = FakeContact.objects.create(user=user, first_name='Laharl', last_name='Overlord')
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar1', 'is loving'),
            ('test-object_foobar1',  'is loved by'),
            is_internal=True,
        )[0]
        self.assertGET404(self._build_narrowed_add_url(subject, rtype))

    def test_add_relations_narrowedtype05(self):
        "ContentType & CremeProperty constraints on subject."
        user = self.login()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_realm', text='Is a realm')
        ptype2 = create_ptype(str_pk='test-prop_nasty', text='Is nasty')

        subject = FakeOrganisation.objects.create(user=user, name='Netherworld')

        create_prop = partial(CremeProperty.objects.create, creme_entity=subject)
        create_prop(type=ptype1)
        create_prop(type=ptype2)

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar1', 'is hiring', [FakeOrganisation], [ptype1, ptype2]),
            ('test-object_foobar1',  'is hired by'),
        )[0]
        self.assertGET200(self._build_narrowed_add_url(subject, rtype))

    def test_add_relations_narrowedtype06(self):
        "Subject does not respect ContentType constraints => error."
        user = self.login()
        subject = FakeContact.objects.create(
            user=user, first_name='Laharl', last_name='Overlord',
        )
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar1', 'is hiring', [FakeOrganisation]),
            ('test-object_foobar1',  'is hired by'),
        )[0]
        self.assertContains(
            self.client.get(self._build_narrowed_add_url(subject, rtype)),
            _('This type of relationship is not compatible with «{model}».').format(
                model='Test Contact',
            ),
            status_code=409,
            html=True,
        )

    def test_add_relations_narrowedtype07(self):
        "Subject does not respect CremeProperty constraints => error."
        user = self.login()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_realm',  text='Is a realm')
        ptype2 = create_ptype(str_pk='test-prop_gentle', text='Is gentle')
        ptype3 = create_ptype(str_pk='test-prop_nasty',  text='Is nasty')

        subject = FakeOrganisation.objects.create(user=user, name='Netherworld')

        create_prop = partial(CremeProperty.objects.create, creme_entity=subject)
        create_prop(type=ptype1)
        create_prop(type=ptype3)  # Not ptype2 !

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar1', 'is hiring', [FakeOrganisation], [ptype1, ptype2]),
            ('test-object_foobar1',  'is hired by'),
        )[0]
        self.assertContains(
            self.client.get(self._build_narrowed_add_url(subject, rtype)),
            ngettext(
                'This type of relationship needs an entity with this property: {properties}.',
                'This type of relationship needs an entity with these properties: {properties}.',
                number=1
            ).format(properties=ptype2),
            status_code=409,
        )

    @staticmethod
    def _build_bulk_add_url(ct_id, *subjects, **kwargs):
        url = reverse('creme_core__create_relations_bulk', args=(ct_id,))

        if kwargs.get('GET', False):
            url += '?' + '&'.join(f'ids={e.id}' for e in subjects)

        return url

    def test_add_relations_bulk01(self):
        self._aux_test_add_relations()

        # This relation should not be recreated by the view
        Relation.objects.create(
            user=self.user,
            subject_entity=self.subject02,
            type=self.rtype02,
            object_entity=self.object02,
        )
        ct_id = self.ct_id
        response = self.assertGET200(
            self._build_bulk_add_url(ct_id, self.subject01, self.subject02, GET=True)
        )
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(_('Multiple adding of relationships'), context.get('title'))
        self.assertEqual(_('Save the relationships'),           context.get('submit_label'))

        # ---
        response = self.client.post(
            self._build_bulk_add_url(ct_id),
            data={
                'entities_lbl': 'wtf',
                'relations': self.formfield_value_multi_relation_entity(
                    (self.rtype01.id, self.object01),
                    (self.rtype02.id, self.object02),
                ),
                'ids': [self.subject01.id, self.subject02.id],
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(2, self.subject01.relations.count())
        self.assertEntiTyHasRelation(self.subject01, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject01, self.rtype02, self.object02)

        self.assertEqual(2, self.subject02.relations.count())  # And not 3
        self.assertEntiTyHasRelation(self.subject02, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject02, self.rtype02, self.object02)

    def test_add_relations_bulk02(self):
        self._aux_test_add_relations(is_superuser=False)

        unviewable = CremeEntity.objects.create(user=self.other_user)
        self.assertFalse(self.user.has_perm_to_view(unviewable))

        ct_id = self.ct_id
        response = self.assertGET200(
            self._build_bulk_add_url(ct_id, self.subject01, unviewable, GET=True)
        )

        with self.assertNoException():
            label = response.context['form'].fields['bad_entities_lbl']

        self.assertTrue(label.initial)

        response = self.client.post(
            self._build_bulk_add_url(ct_id),
            data={
                'entities_lbl':     'do not care',
                'bad_entities_lbl': 'do not care',
                'relations':        self.formfield_value_multi_relation_entity(
                    (self.rtype01.id, self.object01),
                    (self.rtype02.id, self.object02),
                ),
                'ids': [self.subject01.id, unviewable.id],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(2, self.subject01.relations.count())
        self.assertEqual(0, unviewable.relations.count())

    def test_add_relations_bulk03(self):
        self._aux_test_add_relations(is_superuser=False)

        self._set_all_creds_except_one(excluded=EntityCredentials.LINK)
        unlinkable = CremeEntity.objects.create(user=self.other_user)
        self.assertTrue(self.user.has_perm_to_view(unlinkable))
        self.assertFalse(self.user.has_perm_to_link(unlinkable))

        response = self.assertGET200(
            self._build_bulk_add_url(self.ct_id, self.subject01, unlinkable, GET=True),
        )

        with self.assertNoException():
            label = response.context['form'].fields['bad_entities_lbl']

        self.assertEqual(str(unlinkable), label.initial)

    def test_add_relations_bulk04(self):
        self._aux_test_add_relations(is_superuser=False)

        self.assertGET200(self._build_bulk_add_url(self.ct_id, self.subject01, GET=True))

        self._set_all_creds_except_one(excluded=EntityCredentials.LINK)
        unlinkable = CremeEntity.objects.create(user=self.other_user)

        response = self.assertPOST200(
            self._build_bulk_add_url(self.ct_id),
            data={
                'entities_lbl': 'wtf',
                'relations': self.formfield_value_multi_relation_entity(
                    [self.rtype01.id, unlinkable],
                ),
                'ids': [self.subject01.id],
            },
        )
        self.assertFormError(
            response, 'form', 'relations',
            _('Some entities are not linkable: {}').format(unlinkable),
        )

    def test_add_relations_bulk05(self):
        "Cannot link an entity to itself"
        self._aux_test_add_relations()

        ct_id = self.ct_id
        subject01 = self.subject01
        subject02 = self.subject02
        response = self.client.post(
            self._build_bulk_add_url(ct_id),
            data={
                'entities_lbl': 'wtf',
                'relations': self.formfield_value_multi_relation_entity(
                    (self.rtype01.id, subject01),
                    (self.rtype02.id, subject02),
                ),
                'ids': [subject01.id, subject02.id],
            },
        )
        self.assertFormError(
            response, 'form', 'relations',
            _('An entity can not be linked to itself : %(entities)s') % {
                'entities': f'{subject01}, {subject02}',
            },
        )

    def test_add_relations_bulk06(self):
        "With SemiFixedRelationType"
        self._aux_test_add_relations()

        # This relation should not be recreated by the view
        Relation.objects.create(
            user=self.user,
            subject_entity=self.subject02,
            type=self.rtype02,
            object_entity=self.object02
        )

        sfrt = SemiFixedRelationType.objects.create(
            predicate='Related to "object01"',
            relation_type=self.rtype01,
            object_entity=self.object01,
        )

        response = self.client.post(
            self._build_bulk_add_url(self.ct_id),
            data={
                'entities_lbl': 'wtf',
                'relations': self.formfield_value_multi_relation_entity(
                    [self.rtype02.id, self.object02],
                ),
                'semifixed_rtypes': [sfrt.id],
                'ids': [self.subject01.id, self.subject02.id],
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(2, self.subject01.relations.count())
        self.assertEntiTyHasRelation(self.subject01, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject01, self.rtype02, self.object02)

        self.assertEqual(2, self.subject02.relations.count())  # Not 3 !
        self.assertEntiTyHasRelation(self.subject02, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject02, self.rtype02, self.object02)

    def test_add_relations_bulk07(self):
        "Choices of RelationTypes limited by the GUI."
        self._aux_test_add_relations()

        # This relation should not be recreated by the view
        Relation.objects.create(
            user=self.user,
            subject_entity=self.subject02,
            type=self.rtype02,
            object_entity=self.object02,
        )

        ct_id = self.ct_id
        response = self.assertGET200(
            self._build_bulk_add_url(ct_id, self.subject01, self.subject02, GET=True)
            + f'&rtype={self.rtype01.id}&rtype={self.rtype02.id}'
        )

        with self.assertNoException():
            allowed_rtypes = response.context['form'].fields['relations'].allowed_rtypes

        self.assertSetEqual({self.rtype01, self.rtype02}, {*allowed_rtypes})

        response = self.client.post(
            self._build_bulk_add_url(ct_id),
            data={
                'entities_lbl': 'wtf',
                'relations': self.formfield_value_multi_relation_entity(
                    (self.rtype01.id, self.object01),
                    (self.rtype02.id, self.object02),
                ),
                'ids': [self.subject01.id, self.subject02.id],
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(2, self.subject01.relations.count())
        self.assertEntiTyHasRelation(self.subject01, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject01, self.rtype02, self.object02)

        self.assertEqual(2, self.subject02.relations.count())  # Not 3
        self.assertEntiTyHasRelation(self.subject02, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject02, self.rtype02, self.object02)

    def _aux_relation_objects_to_link_selection(self):
        user = self.login()

        self.subject = CremeEntity.objects.create(user=user)

        create_user = partial(FakeContact.objects.create, user=user)
        self.contact01 = create_user(first_name='Laharl', last_name='Overlord')
        self.contact02 = create_user(first_name='Etna',   last_name='Devil')
        self.contact03 = create_user(first_name='Flone',  last_name='Angel')

        self.orga01 = FakeOrganisation.objects.create(user=user, name='Earth Defense Force')

        self.ct_contact = ContentType.objects.get_for_model(FakeContact)

        self.rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving',   [FakeContact]),
            ('test-object_foobar',  'is loved by', [FakeContact]),
        )[0]

    def test_select_relations_objects01(self):
        self._aux_relation_objects_to_link_selection()

        data = {
            'subject_id': self.subject.id,
            'rtype_id': self.rtype.id,
            'objects_ct_id': self.ct_contact.id,
        }

        response = self.assertGET200(self.SELECTION_URL, data=data)

        try:
            entities = response.context['page_obj']
        except KeyError:
            self.fail(response.content)

        contacts = entities.object_list
        self.assertEqual(3, len(contacts))
        self.assertTrue(all(isinstance(c, FakeContact) for c in contacts))
        self.assertSetEqual({self.contact01, self.contact02, self.contact03}, {*contacts})

        # 'selection'  TODO: test better
        self.assertGET200(self.SELECTION_URL, data={**data, 'selection': 'single'})
        self.assertGET200(self.SELECTION_URL, data={**data, 'selection': 'multiple'})
        self.assertGET404(self.SELECTION_URL, data={**data, 'selection': 'invalid'})

    def test_select_relations_objects02(self):
        self._aux_relation_objects_to_link_selection()

        # 'contact03' will not be proposed by the list-view
        Relation.objects.create(
            user=self.user, type=self.rtype,
            subject_entity=self.subject, object_entity=self.contact03,
        )

        response = self.assertGET200(
            self.SELECTION_URL,
            data={
                'subject_id':    self.subject.id,
                'rtype_id':      self.rtype.id,
                'objects_ct_id': self.ct_contact.id,
            },
        )

        contacts = response.context['page_obj'].object_list
        self.assertEqual(2, len(contacts))
        self.assertSetEqual({self.contact01, self.contact02}, {*contacts})

    def test_select_relations_objects03(self):
        self._aux_relation_objects_to_link_selection()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(str_pk='test-prop_foobar01', text='Is lovable')
        ptype02 = create_ptype(str_pk='test-prop_foobar02', text='Is a girl')

        contact04 = FakeContact.objects.create(
            user=self.user, first_name='Flonne', last_name='Angel',
        )

        # 'contact02' will not be proposed by the list-view
        create_property = CremeProperty.objects.create
        create_property(type=ptype01, creme_entity=self.contact01)
        create_property(type=ptype02, creme_entity=self.contact03)
        create_property(type=ptype01, creme_entity=contact04)
        create_property(type=ptype02, creme_entity=contact04)

        rtype, sym_rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_loving', 'is loving',   [FakeContact]),
            ('test-object_loving',  'is loved by', [FakeContact], [ptype01, ptype02]),
        )

        response = self.assertGET200(
            self.SELECTION_URL,
            data={
                'subject_id':    self.subject.id,
                'rtype_id':      rtype.id,
                'objects_ct_id': self.ct_contact.id,
            },
        )

        contacts = response.context['page_obj'].object_list
        self.assertEqual(3, len(contacts))
        self.assertSetEqual({self.contact01, self.contact03, contact04}, {*contacts})

    def test_select_relations_objects04(self):
        self.login()

        subject = CremeEntity.objects.create(user=self.user)
        ct = ContentType.objects.get_for_model(FakeContact)
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving',   [FakeContact]),
            ('test-object_foobar',  'is loved by', [FakeContact]),
            is_internal=True,
        )[0]

        self.assertGET404(
            self.SELECTION_URL,
            data={
                'subject_id':    subject.id,
                'rtype_id':      rtype.id,
                'objects_ct_id': ct.id,
            },
        )

    def _aux_add_relations_with_same_type(self):
        create_entity = partial(CremeEntity.objects.create, user=self.user)
        self.subject  = create_entity()
        self.object01 = create_entity()
        self.object02 = create_entity()
        self.rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )[0]

    def test_add_relations_with_same_type01(self):
        "No error."
        self.login()
        self._aux_add_relations_with_same_type()

        object_ids = [self.object01.id, self.object02.id]
        self.assertPOST200(
            self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   self.subject.id,
                'predicate_id': self.rtype.id,
                'entities':     object_ids,
            },
        )
        self.assertEqual(2, Relation.objects.filter(type=self.rtype).count())

        relations = self.subject.relations.filter(type=self.rtype)
        self.assertEqual(2, len(relations))
        self.assertSetEqual({*object_ids}, {r.object_entity_id for r in relations})

    def test_add_relations_with_same_type02(self):
        "An entity does not exist."
        self.login()
        self._aux_add_relations_with_same_type()

        self.assertPOST404(
            self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   self.subject.id,
                'predicate_id': self.rtype.id,
                'entities':     [
                    self.object01.id,
                    self.object02.id,
                    self.object02.id + 1,
                ],
            },
        )
        self.assertEqual(2, Relation.objects.filter(type=self.rtype).count())

    def test_add_relations_with_same_type03(self):
        "Errors."
        self.login()
        self._aux_add_relations_with_same_type()

        url = self.ADD_FROM_PRED_URL
        self.assertPOST404(
            url,
            data={
                'subject_id':    self.subject.id,
                'predicate_id': 'IDONOTEXIST',
                'entities':      [self.object01.id],
            },
        )
        self.assertPOST404(
            url,
            data={
                'subject_id':   self.UNUSED_PK,
                'predicate_id': self.rtype.id,
                'entities':     [self.object01.id],
            },
        )
        self.assertPOST404(
            url,
            data={
                'predicate_id': self.rtype.id,
                'entities':     [self.object01.id],
            },
        )
        self.assertPOST404(
            url,
            data={
                'subject_id': self.subject.id,
                'entities':   [self.object01.id],
            },
        )
        self.assertPOST404(
            url,
            data={
                'subject_id':   self.subject.id,
                'predicate_id': self.rtype.id,
            },
        )

    def test_add_relations_with_same_type04(self):
        "Credentials errors."
        user = self.login(is_superuser=False)
        self._set_all_creds_except_one(excluded=EntityCredentials.LINK)

        create_entity = CremeEntity.objects.create
        forbidden = create_entity(user=self.other_user)
        allowed01 = create_entity(user=user)
        allowed02 = create_entity(user=user)

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )[0]

        self.assertFalse(user.has_perm_to_link(forbidden))
        self.assertTrue(user.has_perm_to_link(allowed01))

        self.assertPOST403(
            self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   forbidden.id,
                'predicate_id': rtype.id,
                'entities':     [allowed01.id, allowed02.id],
            },
        )
        self.assertFalse(Relation.objects.filter(type=rtype.id))

        self.assertPOST403(
            self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   allowed01.id,
                'predicate_id': rtype.id,
                'entities':     [forbidden.id, allowed02.id, self.UNUSED_PK],
            },
        )
        relations = Relation.objects.filter(type=rtype)
        self.assertEqual(1, len(relations))

        relation = relations[0]
        self.assertEqual(allowed01, relation.subject_entity)
        self.assertEqual(allowed02, relation.object_entity)

    def test_add_relations_with_same_type05(self):
        "ContentType constraint errors."
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(name='orga01')
        orga02 = create_orga(name='orga02')

        create_contact = partial(FakeContact.objects.create, user=user)
        contact01 = create_contact(first_name='John', last_name='Doe')
        contact02 = create_contact(first_name='Joe',  last_name='Gohn')

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'manages',       [FakeContact]),
            ('test-object_foobar',  'is managed by', [FakeOrganisation]),
        )[0]

        self.assertPOST(
            409, self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   orga01.id,
                'predicate_id': rtype.id,
                'entities':     [orga02.id],
            },
        )
        self.assertFalse(Relation.objects.filter(type=rtype.id))

        self.assertPOST(
            409, self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   contact01.id,
                'predicate_id': rtype.id,
                'entities':     [orga01.id, contact02.id],
            },
        )
        relations = Relation.objects.filter(type=rtype)
        self.assertEqual(1,         len(relations))
        self.assertEqual(orga01.id, relations[0].object_entity_id)

    def test_add_relations_with_same_type06(self):
        "Property constraint."
        user = self.login()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        subject_ptype1 = create_ptype(str_pk='test-prop_subj1', text='Subject property #1')
        subject_ptype2 = create_ptype(str_pk='test-prop_subj2', text='Subject property #2')
        object_ptype1  = create_ptype(str_pk='test-prop_obj1',  text='Contact property #1')
        object_ptype2  = create_ptype(str_pk='test-prop_obj2',  text='Contact property #2')

        create_entity = partial(CremeEntity.objects.create, user=user)
        bad_subject1  = create_entity(description='Bad subject #1')
        bad_subject2  = create_entity(description='Bad subject #2')
        good_subject  = create_entity(description='Good subject')
        bad_object1   = create_entity(description='Bad object #1')
        bad_object2   = create_entity(description='Bad object #2')
        good_object   = create_entity(description='Good object #1')

        create_prop = CremeProperty.objects.create
        create_prop(type=subject_ptype1, creme_entity=good_subject)
        create_prop(type=subject_ptype2, creme_entity=good_subject)
        create_prop(type=object_ptype1, creme_entity=good_object)
        create_prop(type=object_ptype2, creme_entity=good_object)

        create_prop(type=subject_ptype1, creme_entity=bad_subject2)  # only one property
        create_prop(type=object_ptype1,  creme_entity=bad_object2)  # only one property

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'manages',       [], [subject_ptype1, subject_ptype2]),
            ('test-object_foobar',  'is managed by', [], [object_ptype1, object_ptype2]),
        )[0]

        url = self.ADD_FROM_PRED_URL

        # Subject with 0 needed property ---
        self.assertPOST(409, url, data={
            'subject_id':   bad_subject1.id,
            'predicate_id': rtype.id,
            'entities':     [good_object.id],
        })
        self.assertFalse(Relation.objects.filter(type=rtype))

        # Subject with 1 needed property ---
        self.assertPOST(409, url, data={
            'subject_id':   bad_subject2.id,
            'predicate_id': rtype.id,
            'entities':     [good_object.id],
        })
        self.assertFalse(Relation.objects.filter(type=rtype))

        # Objects with 0 & 1 needed property ---
        self.assertPOST(409, self.ADD_FROM_PRED_URL, data={
            'subject_id':   good_subject.id,
            'predicate_id': rtype.id,
            'entities':     [good_object.id, bad_object1.id, bad_object2.id],
        })
        self.assertCountEqual(
            [good_object.description],
            [rel.object_entity.description for rel in Relation.objects.filter(type=rtype)],
        )

    def test_add_relations_with_same_type07(self):
        "Is internal."
        user = self.login()

        create_entity = partial(CremeEntity.objects.create, user=user)
        subject  = create_entity()
        object01 = create_entity()
        object02 = create_entity()
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
            is_internal=True,
        )[0]
        self.assertPOST404(
            self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   subject.id,
                'predicate_id': rtype.id,
                'entities':     [object01.id, object02.id],
            },
        )
        self.assertFalse(Relation.objects.filter(type=rtype))

    def test_add_relations_with_same_type08(self):
        "Subject is in the objects."
        user = self.login()

        create_entity = partial(CremeEntity.objects.create, user=user)
        subject = create_entity()
        object02 = create_entity()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )[0]
        self.assertPOST409(
            self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   subject.id,
                'predicate_id': rtype.id,
                'entities':     [str(object02.id), str(subject.id)],
            },
        )
        self.assertFalse(Relation.objects.filter(type=rtype))

    def test_add_relations_with_same_type09(self):
        "Object ID is not an int."
        self.login()

        response = self.client.post(
            self.ADD_FROM_PRED_URL,
            data={
                'subject_id': '1',
                'predicate_id': 'test-subject_foobar',
                'entities': ['2', 'notanint'],
            },
        )
        self.assertContains(
            response,
            'An ID in the argument "entities" is not an integer.',
            status_code=404,
            html=True,
        )

    def _delete(self, relation):
        return self.client.post(
            reverse('creme_core__delete_relation'),
            data={'id': relation.id},
        )

    def test_delete01(self):
        user = self.login()

        create_entity = partial(CremeEntity.objects.create, user=user)
        subject_entity = create_entity()
        object_entity  = create_entity()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )[0]
        relation = Relation.objects.create(
            subject_entity=subject_entity, type=rtype,
            object_entity=object_entity, user=user,
        )
        sym_relation = relation.symmetric_relation
        self.assertIsNone(rtype.is_not_internal_or_die())

        self.assertEqual(302, self._delete(relation).status_code)
        self.assertFalse(Relation.objects.filter(pk__in=[relation.pk, sym_relation.pk]))

    def test_delete02(self):
        user = self.login(is_superuser=False)

        self._set_all_creds_except_one(excluded=EntityCredentials.UNLINK)

        allowed   = CremeEntity.objects.create(user=user)
        forbidden = CremeEntity.objects.create(user=self.other_user)
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )[0]

        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        relation = create_rel(subject_entity=allowed, object_entity=forbidden)
        self.assertEqual(403, self._delete(relation).status_code)
        self.get_object_or_fail(Relation, pk=relation.pk)

        relation = create_rel(subject_entity=forbidden, object_entity=allowed)
        self.assertEqual(403, self._delete(relation).status_code)
        self.get_object_or_fail(Relation, pk=relation.pk)

    def test_delete03(self):
        "Is internal."
        user = self.login()

        create_entity = partial(CremeEntity.objects.create, user=user)
        subject_entity = create_entity()
        object_entity  = create_entity()

        rtype, sym_rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
            is_internal=True,
        )
        self.assertTrue(rtype.is_internal)
        self.assertTrue(sym_rtype.is_internal)
        self.assertRaises(Http404, rtype.is_not_internal_or_die)

        relation = Relation.objects.create(
            user=user, type=rtype,
            subject_entity=subject_entity,
            object_entity=object_entity,
        )
        self.assertEqual(404, self._delete(relation).status_code)
        self.get_object_or_fail(Relation, pk=relation.pk)

    def assertDeleteSimilar(self, *, status, subject, rtype, object):
        return self.assertPOST(
            status,
            reverse('creme_core__delete_similar_relations'),
            data={
                'subject_id': subject.id if isinstance(subject, CremeEntity) else subject,
                'type':       rtype.id,
                'object_id':  object.id if isinstance(object, CremeEntity) else object,
            },
            follow=True,
        )

    def test_delete_similar01(self):
        user = self.login(is_superuser=False)
        self._set_all_creds_except_one(excluded=EntityCredentials.DELETE)

        create_entity = partial(CremeEntity.objects.create, user=user)
        subject_entity01 = create_entity()
        object_entity01  = create_entity()

        subject_entity02 = create_entity()
        object_entity02  = create_entity()

        create_rt = RelationType.objects.smart_update_or_create
        rtype01 = create_rt(
            ('test-subject_love', 'is loving'),
            ('test-object_love',  'is loved by'),
        )[0]
        rtype02 = create_rt(
            ('test-subject_son', 'is son of'),
            ('test-object_son',  'is parent of'),
        )[0]

        create_rel = partial(
            Relation.objects.create,
            user=user, type=rtype01,
            subject_entity=subject_entity01,
            object_entity=object_entity01,
        )

        # Will be deleted (normally)
        relation01 = create_rel()

        # Won't be deleted (normally)
        relation03 = create_rel(object_entity=object_entity02)
        relation04 = create_rel(subject_entity=subject_entity02)
        relation05 = create_rel(type=rtype02)

        self.assertEqual(8, Relation.objects.count())

        self.assertDeleteSimilar(
            status=404, subject=self.UNUSED_PK,   rtype=rtype01, object=object_entity01,
        )
        self.assertDeleteSimilar(
            status=404, subject=subject_entity01, rtype=rtype01, object=self.UNUSED_PK,
        )

        self.assertDeleteSimilar(
            status=200, subject=subject_entity01, rtype=rtype01, object=object_entity01,
        )
        self.assertDoesNotExist(relation01)
        self.assertEqual(
            3,
            Relation.objects.filter(pk__in=[relation03.pk, relation04.pk, relation05.pk]).count(),
        )

    def test_delete_similar02(self):
        user = self.login(is_superuser=False)
        self._set_all_creds_except_one(excluded=EntityCredentials.UNLINK)

        allowed   = CremeEntity.objects.create(user=user)
        forbidden = CremeEntity.objects.create(user=self.other_user)

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'is loving'),
            ('test-object_love',  'is loved by'),
        )[0]
        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        create_rel(subject_entity=allowed,   object_entity=forbidden)
        create_rel(subject_entity=forbidden, object_entity=allowed)
        self.assertEqual(4, Relation.objects.count())

        self.assertDeleteSimilar(status=403, subject=allowed, rtype=rtype, object=forbidden)
        self.assertEqual(4, Relation.objects.count())

        self.assertDeleteSimilar(status=403, subject=forbidden, rtype=rtype, object=allowed)
        self.assertEqual(4, Relation.objects.count())

    def test_delete_similar03(self):
        "Is internal."
        user = self.login()

        create_entity = partial(CremeEntity.objects.create, user=user)
        subject_entity = create_entity()
        object_entity  = create_entity()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'is loving'),
            ('test-object_love', 'is loved by'),
            is_internal=True,
        )[0]
        relation = Relation.objects.create(
            user=user, type=rtype,
            subject_entity=subject_entity,
            object_entity=object_entity,
        )

        self.assertDeleteSimilar(
            status=404, subject=subject_entity, rtype=rtype, object=object_entity,
        )
        self.assertStillExists(relation)

    def test_not_copiable_relations01(self):
        user = self.login()

        self.assertEqual(0, Relation.objects.count())
        rtype1, rtype2 = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
            is_copiable=False,
        )
        rtype3, rtype4 = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar_copiable', 'is loving'),
            ('test-object_foobar_copiable',  'is loved by'),
        )

        create_entity = CremeEntity.objects.create
        entity1 = create_entity(user=user)
        entity2 = create_entity(user=user)

        Relation.objects.create(
            user=user, type=rtype1,
            subject_entity=entity1, object_entity=entity2,
        )
        self.assert_relation_count(((rtype1, 1), (rtype2, 1)))

        Relation.objects.create(
            user=user, type=rtype3,
            subject_entity=entity1, object_entity=entity2,
        )
        self.assert_relation_count(((rtype3, 1), (rtype4, 1)))

        entity1.clone()
        self.assert_relation_count(((rtype1, 1), (rtype2, 1), (rtype3, 2), (rtype4, 2)))

    def test_not_copiable_relations02(self):
        user = self.login()
        self.assertEqual(0, Relation.objects.count())

        create_rtype = RelationType.objects.smart_update_or_create
        rtype1, rtype2 = create_rtype(
            ('test-subject_foobar_copiable', 'is loving',   [FakeContact, FakeOrganisation]),
            ('test-object_foobar_copiable',  'is loved by', [FakeContact]),
        )
        rtype3, rtype4 = create_rtype(
            ('test-subject_foobar', 'is loving',   [FakeContact]),
            ('test-object_foobar',  'is loved by', [FakeOrganisation]),
        )

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(last_name='Toto')
        contact2 = create_contact(last_name='Titi')

        orga = FakeOrganisation.objects.create(user=user, name='Toto CORP')

        # Contact1 <------> Orga
        Relation.objects.create(
            user=user, type=rtype1,
            subject_entity=contact1,
            object_entity=orga,
        )
        Relation.objects.create(
            user=user, type=rtype3,
            subject_entity=contact1,
            object_entity=orga,
        )

        self.assert_relation_count(((rtype1, 1), (rtype2, 1), (rtype3, 1), (rtype4, 1)))

        # Contact2 < ---- > Orga
        contact2._copy_relations(contact1)
        self.assert_relation_count(((rtype1, 2), (rtype2, 2), (rtype3, 2), (rtype4, 2)))

        orga._copy_relations(contact1)
        self.assert_relation_count(((rtype1, 3), (rtype2, 3), (rtype3, 2), (rtype4, 2)))
