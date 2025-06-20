from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core import workflows
from creme.creme_core.core.entity_filter import condition_handler
from creme.creme_core.core.entity_filter.operators import EndsWithOperator
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.core.workflow import WorkflowConditions
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
    Workflow,
)

from ..base import CremeTestCase


class RelationViewsTestCase(CremeTestCase):
    ADD_FROM_PRED_URL = reverse('creme_core__save_relations')
    SELECTION_URL     = reverse('creme_core__select_entities_to_link')

    # def assertEntiTyHasRelation(self, subject_entity, rtype, object_entity):
    #     self.assertTrue(
    #         subject_entity.relations
    #                       .filter(type=rtype, object_entity=object_entity.id)
    #                       .exists()
    #     )

    @staticmethod
    def _build_add_url(subject):
        return reverse('creme_core__create_relations', args=(subject.id,))

    @staticmethod
    def _build_bulk_add_url(model, *subjects, **kwargs):
        url = reverse(
            'creme_core__create_relations_bulk',
            args=(ContentType.objects.get_for_model(model).id,),
        )

        if kwargs.get('GET', False):
            url += '?' + '&'.join(f'ids={e.id}' for e in subjects)

        return url

    @staticmethod
    def _build_get_ctypes_url(rtype_id):
        return reverse('creme_core__ctypes_compatible_with_rtype', args=(rtype_id,))

    @staticmethod
    def _build_narrowed_add_url(subject, rtype):
        return reverse('creme_core__create_relations', args=(subject.id, rtype.id))

    @staticmethod
    def count_relations(rtype):
        return Relation.objects.filter(type=rtype).count()

    def assertRelationCounts(self, counts):
        assertEqual = self.assertEqual
        rcount = self.count_relations
        for rtype, count in counts:
            assertEqual(count, rcount(rtype))

    def test_get_ctypes_of_relation01(self):
        "No sort."
        self.login_as_root()

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
        self.login_as_root()

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
        self.login_as_root()

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

    def test_get_ctypes_of_relation04(self):
        "Type is disabled => error."
        self.login_as_root()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_customer', 'is a customer of', [FakeContact]),
            ('test-object_customer',  'is a supplier of', [FakeContact, FakeOrganisation]),
        )[0]
        rtype.enabled = False
        rtype.save()

        self.assertGET409(
            self._build_get_ctypes_url(rtype.id),
            data={'fields': ['id', 'unicode']},
        )

    def _create_contact(self, user, first_name='Laharl', last_name='Overlord'):
        return FakeContact.objects.create(
            user=user, first_name=first_name, last_name=last_name,
        )

    def _create_contacts(self, user):
        create_contact = partial(FakeContact.objects.create, user=user)
        return (
            create_contact(first_name='Laharl', last_name='Overlord'),
            create_contact(first_name='Etna',   last_name='Devil'),
        )

    def _create_organisation(self, user, name='Underworld'):
        return FakeOrganisation.objects.create(user=user, name=name)

    def _create_organisations(self, user):
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        return (
            create_orga(name='Underworld'),
            create_orga(name='Heaven'),
        )

    def _create_rtype(self):
        return RelationType.objects.smart_update_or_create(
            ('test-subject_loves', 'is loving'),
            ('test-object_loves',  'is loved by'),
        )[0]

    def _create_rtypes(self):
        create_rtype = RelationType.objects.smart_update_or_create
        return (
            create_rtype(
                ('test-subject_loves', 'is loving'),
                ('test-object_loves',  'is loved by'),
            )[0],
            create_rtype(
                ('test-subject_hates', 'is hating'),
                ('test-object_hates',  'is hated by'),
            )[0],
        )

    def test_add_relations(self):
        user = self.login_as_root_and_get()

        rtype1, rtype2 = self._create_rtypes()
        rtype3 = RelationType.objects.smart_update_or_create(
            ('test-subject_disabled', 'is disabled'),
            ('test-object_disabled',  'whatever'),
        )[0]
        rtype3.enabled = False
        rtype3.save()

        subject = self._create_contact(user=user)
        self.assertFalse(subject.relations.all())

        url = self._build_add_url(subject)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        context = response1.context
        self.assertEqual(
            _('Relationships for «{entity}»').format(entity=subject),
            context.get('title'),
        )
        self.assertEqual(_('Save the relationships'), context.get('submit_label'))

        with self.assertNoException():
            relations_f = context['form'].fields['relations']

        rtype_ids = {*relations_f.allowed_rtypes.values_list('id', flat=True)}
        self.assertIn(rtype1.id, rtype_ids)
        self.assertIn(rtype2.id, rtype_ids)
        self.assertNotIn(rtype3.id, rtype_ids)

        # ---
        object1, object2 = self._create_organisations(user=user)
        response2 = self.client.post(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (rtype1, object1),
                    (rtype2, object2),
                ),
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(2, subject.relations.count())
        # self.assertEntiTyHasRelation(subject, rtype1, object1)
        # self.assertEntiTyHasRelation(subject, rtype2, object2)
        self.assertHaveRelation(subject, rtype1, object1)
        self.assertHaveRelation(subject, rtype2, object2)

    def test_add_relations__not_superuser01(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*')

        subject = CremeEntity.objects.create(user=user)
        self.assertGET200(self._build_add_url(subject))

    def test_add_relations__not_superuser02(self):
        "Credentials problems."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*', all='!LINK')

        subject = CremeEntity.objects.create(user=self.get_root_user())
        self.assertGET403(self._build_add_url(subject))

    def test_add_relations__link_perm(self):
        "Credentials problems (no link credentials)."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*', all='!LINK')

        subject = self._create_contact(user=user)
        unlinkable = CremeEntity.objects.create(user=self.get_root_user())
        self.assertTrue(user.has_perm_to_view(unlinkable))
        self.assertFalse(user.has_perm_to_link(unlinkable))

        rtype1, rtype2 = self._create_rtypes()
        linkable = self._create_organisation(user=user)
        response = self.client.post(
            self._build_add_url(subject),
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (rtype1, linkable),
                    (rtype2, unlinkable),
                ),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='relations',
            errors=_('Some entities are not linkable: {}').format(unlinkable),
        )
        self.assertFalse(subject.relations.all())

    def test_add_relations__duplicates01(self):
        "Duplicates -> error."
        user = self.login_as_root_and_get()

        subject = self._create_contact(user=user)
        rtype1, rtype2 = self._create_rtypes()
        object1, object2 = self._create_organisations(user=user)
        response = self.client.post(
            self._build_add_url(subject),
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (rtype1, object1),
                    (rtype2, object2),
                    (rtype1, object1),
                ),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='relations',
            errors=_('There are duplicates: %(duplicates)s') % {
                'duplicates': f'({rtype1}, {object1})',
            },
        )

    def test_add_relations__duplicates02(self):
        "Do not recreate existing relationships."
        user = self.login_as_root_and_get()
        subject = self._create_contact(user=user)
        rtype1, rtype2 = self._create_rtypes()
        object1, object2 = self._create_organisations(user=user)

        Relation.objects.create(
            user=user,
            subject_entity=subject,
            type=rtype2,
            object_entity=object2,
        )
        response = self.client.post(
            self._build_add_url(subject),
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (rtype1, object1),
                    (rtype2, object2),
                ),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())  # Not 3

    def test_add_relations__circular(self):
        "Cannot link an entity to itself."
        user = self.login_as_root_and_get()

        subject = self._create_contact(user=user)
        rtype = self._create_rtype()
        response = self.client.post(
            self._build_add_url(subject),
            data={
                'relations': self.formfield_value_multi_relation_entity((rtype, subject)),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='relations',
            errors=_('An entity can not be linked to itself: %(entities)s') % {
                'entities': subject,
            },
        )

    def test_add_relations__property_constraints01(self):
        "CremeProperty constraints on subject."
        user = self.login_as_root_and_get()

        subject = self._create_contact(user=user)
        object1 = self._create_organisation(user=user)

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is strong')
        ptype2 = create_ptype(text='Is cool')
        ptype3 = create_ptype(text='Is smart')

        # NB: not ptype3
        create_prop = partial(CremeProperty.objects.create, creme_entity=subject)
        create_prop(type=ptype1)
        create_prop(type=ptype2)

        # Constraint KO & OK
        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_teaches', 'teaches', [FakeContact], [ptype3]),
            ('test-object_teaches', 'is taught by'),
        )[0]
        rtype2 = create_rtype(
            ('test-subject_rules', 'rules', [FakeContact], [ptype1, ptype3]),
            ('test-object_rules',  'is ruled by'),
        )[0]
        rtype3 = create_rtype(
            ('test-subject_hero', 'is the hero of', [FakeContact], [ptype2]),
            ('test-object_hero',  'has a hero which is'),
        )[0]

        url = self._build_add_url(subject)

        # 1 Property needed
        response1 = self.assertPOST200(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity((rtype1, object1)),
            },
        )
        msg = Relation.error_messages['missing_subject_property']
        self.assertFormError(
            response1.context['form'],
            field='relations',
            errors=msg % {
                'entity': subject,
                'property': ptype3,
                'predicate': rtype1.predicate,
            },
        )

        # 2 Properties needed
        response2 = self.assertPOST200(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity((rtype2, object1)),
            },
        )
        self.assertFormError(
            response2.context['form'],
            field='relations',
            errors=msg % {
                'entity': subject,
                'property': ptype3,
                'predicate': rtype2.predicate,
            },
        )

        # OK ---
        response3 = self.client.post(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity((rtype3, object1)),
            },
        )
        self.assertNoFormError(response3)
        self.assertEqual(1, subject.relations.count())

    def test_add_relations__property_constraints02(self):
        "CremeProperty constraints on subject (forbidden types)."
        user = self.login_as_root_and_get()

        subject = self._create_contact(user=user)

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is cool')
        ptype2 = create_ptype(text='Is weak')

        create_prop = partial(CremeProperty.objects.create, creme_entity=subject)
        create_prop(type=ptype1)
        create_prop(type=ptype2)

        # Constraint KO & OK
        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_foobar3', 'rules', [FakeContact], [ptype1], [ptype2]),
            ('test-object_foobar3',  'is ruled by'),
        )[0]
        rtype2 = create_rtype(
            ('test-subject_foobar5', 'is the hero of', [FakeContact], [ptype1]),
            ('test-object_foobar5',  'has a hero which is'),
        )[0]

        url = self._build_add_url(subject)

        # A forbidden Property is used
        object1 = self._create_organisation(user=user)
        response1 = self.assertPOST200(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity((rtype1, object1)),
            },
        )
        self.assertFormError(
            response1.context['form'],
            field='relations',
            errors=Relation.error_messages['refused_subject_property'] % {
                'entity': subject,
                'predicate': rtype1.predicate,
                'property': ptype2,
            },
        )

        # OK ---
        response2 = self.client.post(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity((rtype2, object1)),
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(1, subject.relations.count())

    def test_add_relations__property_constraints03(self):
        "CremeProperty constraints on objects."
        user = self.login_as_root_and_get()

        subject = self._create_organisation(user=user)
        rel_object = self._create_contact(user=user)

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is strong')
        ptype2 = create_ptype(text='Is cool')
        ptype3 = create_ptype(text='Is smart')

        # NB: not ptype3
        create_prop = partial(CremeProperty.objects.create, creme_entity=rel_object)
        create_prop(type=ptype1)
        create_prop(type=ptype2)

        # Constraint KO & OK
        rtype, sym_rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_ruled', 'is ruled by'),
            ('test-object_ruled',  'rules', [FakeContact], [ptype1, ptype3]),
        )

        url = self._build_add_url(subject)

        # Invalid object
        data = {
            'relations': self.formfield_value_multi_relation_entity((rtype, rel_object)),
        }
        response1 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response1.context['form'],
            field='relations',
            errors=Relation.error_messages['missing_subject_property'] % {
                'entity': rel_object,
                'property': ptype3,
                'predicate': sym_rtype.predicate,
            },
        )

        # OK ---
        create_prop(type=ptype3)
        self.assertNoFormError(self.client.post(url, data=data))
        self.assertEqual(1, subject.relations.count())

    def test_add_relations__exclude(self):
        "'exclude' parameter."
        user = self.login_as_root_and_get()

        subject = self._create_contact(user=user)
        rtype1, rtype2 = self._create_rtypes()

        rtype3 = RelationType.objects.smart_update_or_create(
            ('test-subject_disabled', 'is disabled'),
            ('test-object_disabled',  'whatever'),
        )[0]
        rtype3.enabled = False
        rtype3.save()

        object_orga = self._create_organisation(user=user)

        create_sfrt = partial(SemiFixedRelationType.objects.create, real_object=object_orga)
        create_sfrt(predicate=f'Relation #1 to "{object_orga}"', relation_type=rtype1)
        sfrt2 = create_sfrt(predicate=f'Relation #2 to "{object_orga}"', relation_type=rtype2)
        create_sfrt(predicate=f'Relation #3 to "{object_orga}"', relation_type=rtype3)

        response = self.client.get(
            self._build_add_url(subject), data={'exclude': [rtype1.id]},
        )

        with self.assertNoException():
            fields = response.context['form'].fields
            rtypes = fields['relations'].allowed_rtypes
            semifixed_choices = [*fields['semifixed_rtypes'].choices]

        self.assertIn(rtype2, rtypes)
        self.assertNotIn(rtype1, rtypes)
        self.assertNotIn(rtype3, rtypes)

        self.assertListEqual([(sfrt2.id, sfrt2.predicate)], semifixed_choices)

    def test_add_relations__workflow(self):
        user = self.login_as_root_and_get()
        rtype = self._create_rtype()
        ptype = CremePropertyType.objects.create(text='Is a fan')

        subject = self._create_contact(user=user)

        suffix = ' Corp'
        object_orga = self._create_organisation(user=user, name=f'Underworld{suffix}')

        Workflow.objects.create(
            title='Edited Corporations are cool',
            content_type=type(subject),
            trigger=workflows.RelationAddingTrigger(
                subject_model=type(subject),
                rtype=rtype,
                object_model=type(object_orga),
            ),
            conditions=WorkflowConditions().add(
                source=workflows.ObjectEntitySource(model=type(object_orga)),
                conditions=[condition_handler.RegularFieldConditionHandler.build_condition(
                    model=type(object_orga),
                    operator=EndsWithOperator, field_name='name', values=[suffix],
                )],
            ),
            actions=[
                workflows.PropertyAddingAction(
                    entity_source=workflows.SubjectEntitySource(model=type(subject)),
                    ptype=ptype,
                ),
            ],
        )

        self.assertNoFormError(self.client.post(
            self._build_add_url(subject),
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (rtype, object_orga),
                ),
            },
        ))
        self.assertHaveRelation(subject, rtype, object_orga)
        self.assertHasProperty(entity=subject, ptype=ptype)

    def test_add_relations_with_semi_fixed01(self):
        "Only semi fixed."
        user = self.login_as_root_and_get()

        subject = self._create_contact(user=user)
        object1, object2 = self._create_organisations(user=user)
        rtype1, rtype2 = self._create_rtypes()

        # Constraint OK & KO
        create_rtype = RelationType.objects.smart_update_or_create
        rtype3 = create_rtype(
            ('test-subject_foobar3', 'is hating orga',     [FakeContact]),
            ('test-object_foobar3',  '(orga) is hated by', [FakeOrganisation]),
        )[0]
        incompatible_rtype = create_rtype(
            # The subject cannot be a Contact
            ('test-subject_foobar4', 'has fired', [FakeOrganisation]),
            ('test-object_foobar4',  'has been fired by'),
        )[0]
        disabled_rtype = create_rtype(
            ('test-subject_disabled', 'disabled'),
            ('test-object_disabled',  'what ever'),
        )[0]

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(
            predicate='Related to "object1"',
            relation_type=rtype1, real_object=object1,
        )
        sfrt2 = create_sfrt(
            predicate='Related to "object2"',
            relation_type=rtype2, real_object=object2,
        )
        sfrt3 = create_sfrt(
            predicate='Linked to "object2"',
            relation_type=rtype3, real_object=object2,
        )
        create_sfrt(
            predicate='Linked to "object1"',
            relation_type=incompatible_rtype, real_object=object1,
        )  # Should not be proposed
        create_sfrt(
            predicate='Related to "object1" but disabled',
            relation_type=disabled_rtype, real_object=object1,
        )  # Should not be proposed

        disabled_rtype.enabled = False
        disabled_rtype.save()

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
        # self.assertEntiTyHasRelation(subject, rtype1, object1)
        # self.assertEntiTyHasRelation(subject, rtype2, object2)
        self.assertHaveRelation(subject, rtype1, object1)
        self.assertHaveRelation(subject, rtype2, object2)

    def test_add_relations_with_semi_fixed02(self):
        "Semi-fixed & not semi-fixed."
        user = self.login_as_root_and_get()

        subject = self._create_contact(user=user)
        object1, object2 = self._create_organisations(user=user)
        rtype1, rtype2 = self._create_rtypes()

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(
            predicate='Related to "object1"',
            relation_type=rtype1,
            real_object=object1,
        )
        sfrt2 = create_sfrt(
            predicate='Related to "object02"',
            relation_type=rtype2,
            real_object=object2,
        )
        create_sfrt(
            predicate='Related to "subject1"',
            relation_type=rtype2,
            real_object=subject,
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
                'relations': self.formfield_value_multi_relation_entity((rtype1, object1)),
                'semifixed_rtypes': [sfrt2.id],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())
        # self.assertEntiTyHasRelation(subject, rtype1, object1)
        # self.assertEntiTyHasRelation(subject, rtype2, object2)
        self.assertHaveRelation(subject, rtype1, object1)
        self.assertHaveRelation(subject, rtype2, object2)

    def test_add_relations_with_semi_fixed_empty(self):
        "One relationship at least (semi-fixed or not semi-fixed)."
        user = self.login_as_root_and_get()

        subject = self._create_contact(user=user)
        response = self.assertPOST200(self._build_add_url(subject))
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_('You must give one relationship at least.'),
        )

    def test_add_relations_with_semi_fixed_duplicates(self):
        "Collision fixed / not fixed."
        user = self.login_as_root_and_get()

        subject = self._create_contact(user=user)
        object1, object2 = self._create_organisations(user=user)
        rtype1, rtype2 = self._create_rtypes()

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(
            predicate='Related to "object1"',
            relation_type=rtype1, real_object=object1,
        )
        sfrt2 = create_sfrt(
            predicate='Related to "object2"',
            relation_type=rtype2, real_object=object2,
        )

        response = self.client.post(
            self._build_add_url(subject),
            data={
                'relations': self.formfield_value_multi_relation_entity((rtype1, object1)),
                'semifixed_rtypes': [sfrt1.id, sfrt2.id],
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_('There are duplicates: %(duplicates)s') % {
                'duplicates': f'({rtype1}, {object1})',
            },
        )

    def test_add_relations_with_semi_fixed_link_perm(self):
        "Filter not linkable entities."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*', all='!LINK')

        subject = self._create_contact(user=user)
        rtype1, rtype2 = self._create_rtypes()
        unlinkable = CremeEntity.objects.create(user=self.get_root_user())
        object2 = self._create_organisation(user=user)

        create_sfrt = SemiFixedRelationType.objects.create
        create_sfrt(
            predicate='Related to "unlinkable"',
            relation_type=rtype1,
            real_object=unlinkable,  # <===
        )
        sfrt2 = create_sfrt(
            predicate='Related to "object2"',
            relation_type=rtype2,
            real_object=object2,
        )

        response = self.assertGET200(self._build_add_url(subject))

        with self.assertNoException():
            sfrt_field = response.context['form'].fields['semifixed_rtypes']

        self.assertListEqual([(sfrt2.id, sfrt2.predicate)], [*sfrt_field.choices])

    def test_add_relations_with_semi_fixed_property_constraints01(self):
        "CremeProperty constraints on subject."
        user = self.login_as_root_and_get()

        subject = self._create_contact(user=user)
        object1, object2 = self._create_organisations(user=user)

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is strong')
        ptype2 = create_ptype(text='Is cool')

        CremeProperty.objects.create(type=ptype2, creme_entity=subject)

        # Constraint OK & KO
        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_rules', 'rules', [FakeContact], [ptype1]),
            ('test-object_rules',  'is ruled by'),
        )[0]
        rtype2 = create_rtype(
            ('test-subject_hero', 'is the hero of', [FakeContact], [ptype2]),
            ('test-object_hero',  'has a hero which is'),
        )[0]

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(
            predicate='Rules "object1"',
            relation_type=rtype1, real_object=object1,
        )
        sfrt2 = create_sfrt(
            predicate='Is the hero of "object2"',
            relation_type=rtype2, real_object=object2,
        )

        url = self._build_add_url(subject)
        response = self.assertPOST200(url, data={'semifixed_rtypes': [sfrt1.id]})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='semifixed_rtypes',
            errors=Relation.error_messages['missing_subject_property'] % {
                'entity': subject,
                'property': ptype1,
                'predicate': rtype1.predicate,
            },
        )

        response = self.client.post(url, data={'semifixed_rtypes': [sfrt2.id]})
        self.assertNoFormError(response)
        self.assertEqual(1, subject.relations.count())

    def test_add_relations_with_semi_fixed_property_constraints02(self):
        "CremeProperty constraints on subject (forbidden types)."
        user = self.login_as_root_and_get()

        subject1, subject2 = self._create_contacts(user=user)
        object1 = self._create_organisation(user=user)

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is weak')
        ptype2 = create_ptype(text='Is strong')

        create_prop = CremeProperty.objects.create
        create_prop(type=ptype1, creme_entity=subject1)
        create_prop(type=ptype2, creme_entity=subject2)

        # Constraint OK & KO
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_rules', 'rules', [FakeContact], [], [ptype1]),
            ('test-object_rules',  'is ruled by'),
        )[0]

        sfrt = SemiFixedRelationType.objects.create(
            predicate='Rules "object1"',
            relation_type=rtype, real_object=object1,
        )

        response1 = self.assertPOST200(
            self._build_add_url(subject1),
            data={'semifixed_rtypes': [sfrt.id]},
        )
        self.assertFormError(
            response1.context['form'],
            field='semifixed_rtypes',
            errors=Relation.error_messages['refused_subject_property'] % {
                'entity': subject1,
                'predicate': rtype.predicate,
                'property': ptype1,
            },
        )

        # OK ---
        self.assertNoFormError(self.client.post(
            self._build_add_url(subject2),
            data={'semifixed_rtypes': [sfrt.id]},
        ))
        self.assertEqual(1, subject2.relations.count())

    def test_add_relations_narrowedtype01(self):
        user = self.login_as_root_and_get()

        rtype = self._create_rtype()
        subject = self._create_contact(user=user)
        object1, object2 = self._create_organisations(user=user)

        url = self._build_narrowed_add_url(subject, rtype)
        self.assertGET200(url)

        response = self.client.post(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (rtype, object1),
                    (rtype, object2),
                ),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())
        # self.assertEntiTyHasRelation(subject, rtype, object1)
        # self.assertEntiTyHasRelation(subject, rtype, object2)
        self.assertHaveRelation(subject, rtype, object1)
        self.assertHaveRelation(subject, rtype, object2)

    def test_add_relations_narrowedtype02(self):
        "Validation error."
        user = self.login_as_root_and_get()

        subject = self._create_contact(user=user)
        object1, object2 = self._create_organisations(user=user)
        rtype1, rtype2 = self._create_rtypes()

        response = self.client.post(
            self._build_narrowed_add_url(subject, rtype1),
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (rtype1, object1),
                    # RelationType not allowed:
                    (rtype2, object2),
                ),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='relations',
            errors=_(
                'This type of relationship causes a constraint error '
                '(id="%(rtype_id)s").'
            ) % {'rtype_id': rtype2.id},
        )

    def test_add_relations_narrowedtype03(self):
        user = self.login_as_root_and_get()

        allowed_rtype, rtype2 = self._create_rtypes()
        subject = self._create_contact(user=user)
        object1, object2 = self._create_organisations(user=user)

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(
            predicate=f'Related to "{object1}"',
            relation_type=allowed_rtype,
            real_object=object1,
        )
        create_sfrt(
            predicate=f'Related to "{object2}"',
            relation_type=rtype2,
            real_object=object2,
        )

        url = self._build_narrowed_add_url(subject, allowed_rtype)

        with self.assertNoException():
            sfrt_field = self.client.get(url).context['form'].fields['semifixed_rtypes']

        self.assertListEqual([(sfrt1.id, sfrt1.predicate)], [*sfrt_field.choices])

        response = self.client.post(
            url,
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (allowed_rtype, object2),
                ),
                'semifixed_rtypes': [sfrt1.id],
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())
        # self.assertEntiTyHasRelation(subject, allowed_rtype, object1)
        # self.assertEntiTyHasRelation(subject, allowed_rtype, object2)
        self.assertHaveRelation(subject, allowed_rtype, object1)
        self.assertHaveRelation(subject, allowed_rtype, object2)

    def test_add_relations_narrowedtype_internal(self):
        "Internal type => error."
        user = self.login_as_root_and_get()
        subject = self._create_contact(user=user)
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar1', 'is loving'),
            ('test-object_foobar1',  'is loved by'),
            is_internal=True,
        )[0]
        self.assertGET409(self._build_narrowed_add_url(subject, rtype))

    def test_add_relations_narrowedtype_disabled(self):
        "Disabled type => error."
        user = self.login_as_root_and_get()
        subject = self._create_contact(user=user)

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar1', 'is loving'),
            ('test-object_foobar1',  'is loved by'),
        )[0]
        rtype.enabled = False
        rtype.save()

        self.assertGET409(self._build_narrowed_add_url(subject, rtype))

    def test_add_relations_narrowedtype_constraints01(self):
        "ContentType constraints."
        user = self.login_as_root_and_get()
        subject01 = self._create_contact(user=user)
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar1', 'is hiring', [FakeOrganisation]),
            ('test-object_foobar1',  'is hired by'),
        )[0]
        self.assertContains(
            self.client.get(self._build_narrowed_add_url(subject01, rtype)),
            Relation.error_messages['forbidden_subject_ctype'] % {
                'entity': subject01,
                'model': subject01.entity_type,
                'predicate': rtype.predicate,
            },
            status_code=409,
            html=True,
        )

        # OK ---
        subject02 = self._create_organisation(user=user)
        self.assertGET200(self._build_narrowed_add_url(subject02, rtype))

    def test_add_relations_narrowedtype_constraints02(self):
        "CremeProperty constraints."
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is a realm')
        ptype2 = create_ptype(text='Is gentle')
        ptype3 = create_ptype(text='Is nasty')

        subject = self._create_organisation(user=user)

        create_prop = partial(CremeProperty.objects.create, creme_entity=subject)
        create_prop(type=ptype1)
        create_prop(type=ptype3)  # Not ptype2 !

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar1', 'is hiring', [FakeOrganisation], [ptype1, ptype2]),
            ('test-object_foobar1',  'is hired by'),
        )[0]
        url = self._build_narrowed_add_url(subject, rtype)
        self.assertContains(
            self.client.get(url),
            Relation.error_messages['missing_subject_property'] % {
                'entity': subject,
                'property': ptype2,
                'predicate': rtype.predicate,
            },
            status_code=409,
            html=True,
        )

        # OK ---
        create_prop(type=ptype2)
        self.assertGET200(url)

    def test_add_relations_narrowedtype_constraints03(self):
        "Forbidden CremeProperty."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is nasty')

        subject = self._create_organisation(user=user)
        CremeProperty.objects.create(creme_entity=subject, type=ptype)

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar1', 'is hiring', [FakeOrganisation], [], [ptype]),
            ('test-object_foobar1',  'is hired by'),
        )[0]
        self.assertContains(
            self.client.get(self._build_narrowed_add_url(subject, rtype)),
            Relation.error_messages['refused_subject_property'] % {
                'entity': subject,
                'property': ptype,
                'predicate': rtype.predicate,
            },
            status_code=409,
        )

    def _aux_test_add_relations_bulk(self, user):
        self.subject01, self.subject02 = self._create_contacts(user=user)
        self.object01, self.object02 = self._create_organisations(user=user)
        self.rtype01, self.rtype02 = self._create_rtypes()

    def test_add_relations_bulk(self):
        user = self.login_as_root_and_get()
        self._aux_test_add_relations_bulk(user=user)

        rtype3 = RelationType.objects.smart_update_or_create(
            ('test-subject_disabled', 'disabled'),
            ('test-object_disabled',  'what ever'),
        )[0]
        rtype3.enabled = False
        rtype3.save()

        # This relation should not be recreated by the view
        Relation.objects.create(
            user=user,
            subject_entity=self.subject02,
            type=self.rtype02,
            object_entity=self.object02,
        )
        response1 = self.assertGET200(
            self._build_bulk_add_url(CremeEntity, self.subject01, self.subject02, GET=True)
        )
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        context = response1.context
        self.assertEqual(_('Multiple adding of relationships'), context.get('title'))
        self.assertEqual(_('Save the relationships'),           context.get('submit_label'))

        with self.assertNoException():
            relations_f = response1.context['form'].fields['relations']

        rtype_ids = {*relations_f.allowed_rtypes.values_list('id', flat=True)}
        self.assertIn(self.rtype01.id, rtype_ids)
        self.assertIn(self.rtype02.id, rtype_ids)
        self.assertNotIn(rtype3.id, rtype_ids)

        # ---
        response2 = self.client.post(
            self._build_bulk_add_url(CremeEntity),
            data={
                'entities_lbl': 'wtf',
                'relations': self.formfield_value_multi_relation_entity(
                    (self.rtype01, self.object01),
                    (self.rtype02, self.object02),
                ),
                'ids': [self.subject01.id, self.subject02.id],
            },
        )
        self.assertNoFormError(response2)

        self.assertEqual(2, self.subject01.relations.count())
        self.assertHaveRelation(self.subject01, self.rtype01, self.object01)
        self.assertHaveRelation(self.subject01, self.rtype02, self.object02)

        self.assertEqual(2, self.subject02.relations.count())  # And not 3
        self.assertHaveRelation(self.subject02, self.rtype01, self.object01)
        self.assertHaveRelation(self.subject02, self.rtype02, self.object02)

    def test_add_relations_bulk_view_perm(self):
        "Ignore subjects which are not viewable."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*', all='!VIEW')
        self._aux_test_add_relations_bulk(user=user)

        unviewable = CremeEntity.objects.create(user=self.get_root_user())
        self.assertFalse(user.has_perm_to_view(unviewable))

        response1 = self.assertGET200(
            self._build_bulk_add_url(CremeEntity, self.subject01, unviewable, GET=True)
        )

        with self.assertNoException():
            label = response1.context['form'].fields['bad_entities_lbl']

        self.assertEqual(
            _('Entity #{id} (not viewable)').format(id=unviewable.id),
            label.initial,
        )

        response2 = self.client.post(
            self._build_bulk_add_url(CremeEntity),
            data={
                'entities_lbl':     'do not care',
                'bad_entities_lbl': 'do not care',
                'relations':        self.formfield_value_multi_relation_entity(
                    (self.rtype01, self.object01),
                    (self.rtype02, self.object02),
                ),
                'ids': [self.subject01.id, unviewable.id],
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(2, self.subject01.relations.count())
        self.assertEqual(0, unviewable.relations.count())

    def test_add_relations_bulk_link_perm01(self):
        "Ignore subjects which are not linkable."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*', all='!LINK')

        subject = self._create_contact(user=user)

        unlinkable = CremeEntity.objects.create(user=self.get_root_user())
        self.assertTrue(user.has_perm_to_view(unlinkable))
        self.assertFalse(user.has_perm_to_link(unlinkable))

        response = self.assertGET200(
            self._build_bulk_add_url(CremeEntity, subject, unlinkable, GET=True),
        )

        with self.assertNoException():
            label = response.context['form'].fields['bad_entities_lbl']

        self.assertEqual(str(unlinkable), label.initial)

    def test_add_relations_bulk_link_perm02(self):
        "Any object which is not linkable => error."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*', all='!LINK')

        subject = self._create_contact(user=user)
        self.assertGET200(self._build_bulk_add_url(CremeEntity, subject, GET=True))

        unlinkable = CremeEntity.objects.create(user=self.get_root_user())
        rtype = self._create_rtype()
        response = self.assertPOST200(
            self._build_bulk_add_url(CremeEntity),
            data={
                'entities_lbl': 'wtf',
                'relations': self.formfield_value_multi_relation_entity(
                    (rtype, unlinkable),
                ),
                'ids': [subject.id],
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='relations',
            errors=_('Some entities are not linkable: {}').format(unlinkable),
        )

    def test_add_relations_bulk_circular(self):
        "Cannot link an entity to itself."
        user = self.login_as_root_and_get()

        subject1, subject2 = self._create_contacts(user=user)
        rtype1, rtype2 = self._create_rtypes()
        response = self.client.post(
            self._build_bulk_add_url(CremeEntity),
            data={
                'entities_lbl': 'wtf',
                'relations': self.formfield_value_multi_relation_entity(
                    (rtype1, subject1),
                    (rtype2, subject2),
                ),
                'ids': [subject1.id, subject2.id],
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='relations',
            errors=_('An entity can not be linked to itself: %(entities)s') % {
                'entities': f'{subject1}, {subject2}',
            },
        )

    def test_add_relations_bulk_property_constraint(self):
        "CremeProperty constraints on subject."
        user = self.login_as_root_and_get()

        subject = self._create_contact(user=user)
        object1 = self._create_organisation(user=user)

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is strong')
        ptype2 = create_ptype(text='Is cool')

        CremeProperty.objects.create(creme_entity=subject, type=ptype1)

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_teaches', 'teaches', [FakeContact], [ptype2]),
            ('test-object_teaches',  'is taught by'),
        )[0]

        response = self.assertPOST200(
            self._build_bulk_add_url(type(subject)),
            data={
                'relations': self.formfield_value_multi_relation_entity(
                    (rtype, object1),
                ),
                'ids': [subject.id],
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='relations',
            errors=Relation.error_messages['missing_subject_property'] % {
                'entity': subject,
                'property': ptype2,
                'predicate': rtype.predicate,
            },
        )

    def test_add_relations_bulk_with_semi_fixed(self):
        "With SemiFixedRelationType."
        user = self.login_as_root_and_get()
        self._aux_test_add_relations_bulk(user=user)

        # This relation should not be recreated by the view
        Relation.objects.create(
            user=user,
            subject_entity=self.subject02,
            type=self.rtype02,
            object_entity=self.object02,
        )

        sfrt = SemiFixedRelationType.objects.create(
            predicate='Related to "object01"',
            relation_type=self.rtype01,
            real_object=self.object01,
        )

        response = self.client.post(
            self._build_bulk_add_url(FakeContact),
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
        self.assertHaveRelation(self.subject01, self.rtype01, self.object01)
        self.assertHaveRelation(self.subject01, self.rtype02, self.object02)

        self.assertEqual(2, self.subject02.relations.count())  # Not 3 !
        self.assertHaveRelation(self.subject02, self.rtype01, self.object01)
        self.assertHaveRelation(self.subject02, self.rtype02, self.object02)

    def test_add_relations_bulk_narrowed_types(self):
        "Choices of RelationTypes limited by the GUI."
        user = self.login_as_root_and_get()
        self._aux_test_add_relations_bulk(user=user)

        # This relation should not be recreated by the view
        Relation.objects.create(
            user=user,
            subject_entity=self.subject02,
            type=self.rtype02,
            object_entity=self.object02,
        )

        response = self.assertGET200(
            self._build_bulk_add_url(FakeContact, self.subject01, self.subject02, GET=True)
            + f'&rtype={self.rtype01.id}&rtype={self.rtype02.id}'
        )

        with self.assertNoException():
            allowed_rtypes = response.context['form'].fields['relations'].allowed_rtypes

        self.assertCountEqual([self.rtype01, self.rtype02], allowed_rtypes)

        response = self.client.post(
            self._build_bulk_add_url(FakeContact),
            data={
                'entities_lbl': 'wtf',
                'relations': self.formfield_value_multi_relation_entity(
                    (self.rtype01, self.object01),
                    (self.rtype02, self.object02),
                ),
                'ids': [self.subject01.id, self.subject02.id],
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(2, self.subject01.relations.count())
        self.assertHaveRelation(self.subject01, self.rtype01, self.object01)
        self.assertHaveRelation(self.subject01, self.rtype02, self.object02)

        self.assertEqual(2, self.subject02.relations.count())  # Not 3
        self.assertHaveRelation(self.subject02, self.rtype01, self.object01)
        self.assertHaveRelation(self.subject02, self.rtype02, self.object02)

    def _aux_relation_objects_to_link_selection(self):
        self.user = user = self.login_as_root_and_get()

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

        url = self.SELECTION_URL
        response = self.assertGET200(url, data=data)

        try:
            entities = response.context['page_obj']
        except KeyError:
            self.fail(response.content)

        self.assertCountEqual(
            [self.contact01, self.contact02, self.contact03],
            entities.object_list,
        )

        # 'selection'  TODO: test better
        self.assertGET200(url, data={**data, 'selection': 'single'})
        self.assertGET200(url, data={**data, 'selection': 'multiple'})
        self.assertGET404(url, data={**data, 'selection': 'invalid'})

    def test_select_relations_objects02(self):
        "Ignore already linked objects."
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
        self.assertCountEqual(
            [self.contact01, self.contact02],
            response.context['page_obj'].object_list,
        )

    def test_select_relations_objects_properties_constraints01(self):
        "Mandatory properties."
        self._aux_relation_objects_to_link_selection()

        create_ptype = CremePropertyType.objects.create
        ptype01 = create_ptype(text='Is lovable')
        ptype02 = create_ptype(text='Is a girl')

        contact04 = FakeContact.objects.create(
            user=self.user, first_name='Flonne', last_name='Angel',
        )

        # 'contact02' will not be proposed by the list-view
        create_property = CremeProperty.objects.create
        create_property(type=ptype01, creme_entity=self.contact01)
        create_property(type=ptype02, creme_entity=self.contact03)
        create_property(type=ptype01, creme_entity=contact04)
        create_property(type=ptype02, creme_entity=contact04)

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_loving', 'is loving',   [FakeContact]),
            ('test-object_loving',  'is loved by', [FakeContact], [ptype01, ptype02]),
        )[0]

        response = self.assertGET200(
            self.SELECTION_URL,
            data={
                'subject_id':    self.subject.id,
                'rtype_id':      rtype.id,
                'objects_ct_id': self.ct_contact.id,
            },
        )
        self.assertCountEqual(
            [self.contact01, self.contact03, contact04],
            response.context['page_obj'].object_list,
        )

    def test_select_relations_objects_properties_constraints02(self):
        "Forbidden properties."
        self._aux_relation_objects_to_link_selection()

        ptype = CremePropertyType.objects.create(text='Is bad')
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_loving', 'is loving',   [FakeContact]),
            ('test-object_loving',  'is loved by', [FakeContact], [], [ptype]),
        )[0]

        # 'contact01' will not be proposed by the list-view
        CremeProperty.objects.create(type=ptype, creme_entity=self.contact01)

        response = self.assertGET200(
            self.SELECTION_URL,
            data={
                'subject_id':    self.subject.id,
                'rtype_id':      rtype.id,
                'objects_ct_id': self.ct_contact.id,
            },
        )
        contacts = {*response.context['page_obj'].object_list}
        self.assertIn(self.contact02, contacts)
        self.assertIn(self.contact03, contacts)
        self.assertNotIn(self.contact01, contacts)

    def test_select_relations_objects_internal(self):
        "Is internal => error."
        user = self.login_as_root_and_get()

        subject = CremeEntity.objects.create(user=user)
        ct = ContentType.objects.get_for_model(FakeContact)
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving',   [FakeContact]),
            ('test-object_foobar',  'is loved by', [FakeContact]),
            is_internal=True,
        )[0]

        self.assertGET409(
            self.SELECTION_URL,
            data={
                'subject_id':    subject.id,
                'rtype_id':      rtype.id,
                'objects_ct_id': ct.id,
            },
        )

    def test_select_relations_objects_disabled(self):
        "Is disabled => error."
        user = self.login_as_root_and_get()

        subject = CremeEntity.objects.create(user=user)
        ct = ContentType.objects.get_for_model(FakeContact)
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )[0]
        rtype.enabled = False
        rtype.save()

        self.assertGET409(
            self.SELECTION_URL,
            data={
                'subject_id':    subject.id,
                'rtype_id':      rtype.id,
                'objects_ct_id': ct.id,
            },
        )

    def test_select_relations_reload_url(self):
        self._aux_relation_objects_to_link_selection()

        data = {
            'subject_id': self.subject.id,
            'rtype_id': self.rtype.id,
            'objects_ct_id': self.ct_contact.id,
        }

        url = self.SELECTION_URL
        response = self.assertGET200(url, data=data)

        reload_url = response.context['reload_url']
        self.assertEqual(
            self.SELECTION_URL + (
                f'?objects_ct_id={self.ct_contact.id}'
                f'&rtype_id={self.rtype.id}'
                f'&subject_id={self.subject.id}'
            ),
            reload_url,
        )

        try:
            entities = response.context['page_obj']
        except KeyError:
            self.fail(response.content)

        self.assertCountEqual(
            [self.contact01, self.contact02, self.contact03],
            entities.object_list,
        )

        self.assertPOST404(url, data={})  # Missing GET arguments
        self.assertPOST200(reload_url, data={})

    def _aux_add_relations_with_same_type(self, user):
        create_entity = partial(CremeEntity.objects.create, user=user)
        self.subject  = create_entity()
        self.object01 = create_entity()
        self.object02 = create_entity()
        self.rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )[0]

    def test_add_relations_with_same_type(self):
        "No error."
        user = self.login_as_root_and_get()
        self._aux_add_relations_with_same_type(user=user)

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
        self.assertCountEqual(object_ids, [r.object_entity_id for r in relations])

    def test_add_relations_with_same_type__invalid_entity_id(self):
        "An entity does not exist."
        user = self.login_as_root_and_get()
        self._aux_add_relations_with_same_type(user=user)

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

    def test_add_relations_with_same_type__errors01(self):
        "Errors."
        user = self.login_as_root_and_get()
        self._aux_add_relations_with_same_type(user=user)

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

    def test_add_relations_with_same_type__errors02(self):
        "Object ID is not an int."
        self.login_as_root()

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

    def test_add_relations_with_same_type__credentials(self):
        "Credentials errors."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*', all='!LINK')

        create_entity = CremeEntity.objects.create
        forbidden = create_entity(user=self.get_root_user())
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
        relation = self.get_alone_element(Relation.objects.filter(type=rtype))
        self.assertEqual(allowed01, relation.subject_entity)
        self.assertEqual(allowed02, relation.object_entity)

    def test_add_relations_with_same_type__ctype_constraints(self):
        "ContentType constraint errors."
        user = self.login_as_root_and_get()

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

        # Subject is invalid ---
        self.assertPOST(
            409, self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   orga01.id,
                'predicate_id': rtype.id,
                'entities':     [orga02.id],
            },
        )
        self.assertFalse(Relation.objects.filter(type=rtype.id))

        # 1 object is invalid ---
        self.assertPOST(
            409, self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   contact01.id,
                'predicate_id': rtype.id,
                'entities':     [orga01.id, contact02.id],
            },
        )
        self.assertListEqual(
            [orga01.id],
            [*Relation.objects.filter(type=rtype).values_list('object_entity', flat=True)],
        )

    def test_add_relations_with_same_type__properties_constraints01(self):
        "Property constraints."
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.create
        subject_ptype1 = create_ptype(text='Subject property #1')
        subject_ptype2 = create_ptype(text='Subject property #2')
        object_ptype1  = create_ptype(text='Contact property #1')
        object_ptype2  = create_ptype(text='Contact property #2')

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

    def test_add_relations_with_same_type__properties_constraints02(self):
        "Forbidden property constraints."
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.create
        subject_forb_ptype = create_ptype(text='Subject property')
        object_forb_ptype  = create_ptype(text='Contact property')

        create_entity = partial(CremeEntity.objects.create, user=user)
        bad_subject  = create_entity(description='Bad subject')
        good_subject = create_entity(description='Good subject')
        bad_object   = create_entity(description='Bad object')
        good_object  = create_entity(description='Good object')

        CremeProperty.objects.create(type=subject_forb_ptype, creme_entity=bad_subject)
        CremeProperty.objects.create(type=object_forb_ptype, creme_entity=bad_object)

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'manages',       [], [], [subject_forb_ptype]),
            ('test-object_foobar',  'is managed by', [], [], [object_forb_ptype]),
        )[0]

        url = self.ADD_FROM_PRED_URL

        # Subject is invalid ---
        self.assertPOST(409, url, data={
            'subject_id':   bad_subject.id,
            'predicate_id': rtype.id,
            'entities':     [good_object.id],
        })
        self.assertFalse(Relation.objects.filter(type=rtype))

        # 1 object is invalid ---
        self.assertPOST(409, url, data={
            'subject_id':   good_subject.id,
            'predicate_id': rtype.id,
            'entities':     [good_object.id, bad_object.id],
        })
        self.assertCountEqual(
            [good_object.description],
            [rel.object_entity.description for rel in Relation.objects.filter(type=rtype)],
        )

    def test_add_relations_with_same_type__internal(self):
        "Is internal."
        user = self.login_as_root_and_get()

        create_entity = partial(CremeEntity.objects.create, user=user)
        subject  = create_entity()
        object01 = create_entity()
        object02 = create_entity()
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
            is_internal=True,
        )[0]
        self.assertPOST409(
            self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   subject.id,
                'predicate_id': rtype.id,
                'entities':     [object01.id, object02.id],
            },
        )
        self.assertFalse(Relation.objects.filter(type=rtype))

    def test_add_relations_with_same_type__disabled(self):
        "Is disabled."
        user = self.login_as_root_and_get()

        create_entity = partial(CremeEntity.objects.create, user=user)
        subject  = create_entity()
        object01 = create_entity()
        object02 = create_entity()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )[0]
        rtype.enabled = False
        rtype.save()

        self.assertPOST409(
            self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   subject.id,
                'predicate_id': rtype.id,
                'entities':     [object01.id, object02.id],
            },
        )
        self.assertFalse(Relation.objects.filter(type=rtype))

    def test_add_relations_with_same_type__circular(self):
        "Subject is in the objects."
        user = self.login_as_root_and_get()

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

    def test_add_relations_with_same_type__workflow(self):
        user = self.login_as_root_and_get()
        rtype = self._create_rtype()
        ptype = CremePropertyType.objects.create(text='Is a fan')

        subject = self._create_contact(user=user)

        suffix = ' Corp'
        object_orga = self._create_organisation(user=user, name=f'Underworld{suffix}')

        Workflow.objects.create(
            title='Edited Corporations are cool',
            content_type=type(subject),
            trigger=workflows.RelationAddingTrigger(
                subject_model=type(subject),
                rtype=rtype,
                object_model=type(object_orga),
            ),
            conditions=WorkflowConditions().add(
                source=workflows.ObjectEntitySource(model=type(object_orga)),
                conditions=[condition_handler.RegularFieldConditionHandler.build_condition(
                    model=type(object_orga),
                    operator=EndsWithOperator, field_name='name', values=[suffix],
                )],
            ),
            actions=[workflows.PropertyAddingAction(
                entity_source=workflows.SubjectEntitySource(model=type(subject)),
                ptype=ptype,
            )],
        )

        self.assertPOST200(
            self.ADD_FROM_PRED_URL,
            data={
                'subject_id':   subject.id,
                'predicate_id': rtype.id,
                'entities':     object_orga.id,
            },
        )
        self.assertHaveRelation(subject, rtype, object_orga)
        self.assertHasProperty(entity=subject, ptype=ptype)

    def _delete(self, relation):
        return self.client.post(
            reverse('creme_core__delete_relation'),
            data={'id': relation.id},
        )

    def test_delete01(self):
        user = self.login_as_root_and_get()

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
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*', all='!UNLINK')

        allowed   = CremeEntity.objects.create(user=user)
        forbidden = CremeEntity.objects.create(user=self.get_root_user())
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
        user = self.login_as_root_and_get()

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
        self.assertRaises(ConflictError, rtype.is_not_internal_or_die)

        relation = Relation.objects.create(
            user=user, type=rtype,
            subject_entity=subject_entity,
            object_entity=object_entity,
        )
        self.assertEqual(409, self._delete(relation).status_code)
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
        user = self.login_as_standard()
        self.add_credentials(user.role, all='!DELETE')

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
        user = self.login_as_standard()
        self.add_credentials(user.role, all='!UNLINK')

        allowed   = CremeEntity.objects.create(user=user)
        forbidden = CremeEntity.objects.create(user=self.get_root_user())

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
        user = self.login_as_root_and_get()

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
            status=409, subject=subject_entity, rtype=rtype, object=object_entity,
        )
        self.assertStillExists(relation)

    def test_not_copiable_relations01(self):  # DEPRECATED
        user = self.login_as_root_and_get()

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
        self.assertRelationCounts(((rtype1, 1), (rtype2, 1)))

        Relation.objects.create(
            user=user, type=rtype3,
            subject_entity=entity1, object_entity=entity2,
        )
        self.assertRelationCounts(((rtype3, 1), (rtype4, 1)))

        entity1.clone()
        self.assertRelationCounts(((rtype1, 1), (rtype2, 1), (rtype3, 2), (rtype4, 2)))

    def test_not_copiable_relations02(self):  # DEPRECATED
        user = self.login_as_root_and_get()
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

        self.assertRelationCounts(((rtype1, 1), (rtype2, 1), (rtype3, 1), (rtype4, 1)))

        # Contact2 < ---- > Orga
        contact2._copy_relations(contact1)
        self.assertRelationCounts(((rtype1, 2), (rtype2, 2), (rtype3, 2), (rtype4, 2)))

        orga._copy_relations(contact1)
        self.assertRelationCounts(((rtype1, 3), (rtype2, 3), (rtype3, 2), (rtype4, 2)))
