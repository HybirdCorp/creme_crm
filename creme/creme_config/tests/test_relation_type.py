# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.models import (
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    RelationType,
    SemiFixedRelationType,
)
from creme.creme_core.tests.base import CremeTestCase


class RelationTypeTestCase(CremeTestCase):
    ADD_URL = reverse('creme_config__create_rtype')
    DEL_URL = reverse('creme_config__delete_rtype')

    def setUp(self):  # In CremeConfigTestCase ??
        super().setUp()
        self.login()

    @staticmethod
    def _build_edit_url(rtype):
        return reverse('creme_config__edit_rtype', args=(rtype.id,))

    def test_portal(self):
        response = self.assertGET200(reverse('creme_config__rtypes'))
        self.assertTemplateUsed(response, 'creme_config/portals/relation-type.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

    def test_create01(self):
        url = self.ADD_URL

        context = self.assertGET200(url).context
        self.assertEqual(_('New custom type'),    context.get('title'))
        self.assertEqual(RelationType.save_label, context.get('submit_label'))

        count = RelationType.objects.count()
        subject_pred = 'loves'
        object_pred  = 'is loved by'
        response = self.client.post(
            url,
            data={
                'subject_predicate': subject_pred,
                'object_predicate':  object_pred,

                'subject_is_copiable': 'on',
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(count + 2, RelationType.objects.count())  # 2 freshly created

        rel_type = self.get_object_or_fail(RelationType, predicate=subject_pred)
        self.assertTrue(rel_type.is_custom)
        self.assertTrue(rel_type.is_copiable)
        self.assertFalse(rel_type.minimal_display)
        self.assertFalse(rel_type.subject_ctypes.all())
        self.assertFalse(rel_type.subject_properties.all())

        sym_type = rel_type.symmetric_type
        self.assertEqual(object_pred, sym_type.predicate)
        self.assertFalse(sym_type.is_copiable)
        self.assertFalse(sym_type.minimal_display)
        self.assertFalse(sym_type.subject_ctypes.all())
        self.assertFalse(sym_type.subject_properties.all())

    def test_create02(self):
        create_pt = CremePropertyType.objects.smart_update_or_create
        pt_sub = create_pt(
            str_pk='test-pt_sub', text='has cash',
            subject_ctypes=[FakeOrganisation],
        )
        pt_obj = create_pt(
            str_pk='test-pt_obj', text='need cash',
            subject_ctypes=[FakeContact],
        )

        get_ct = ContentType.objects.get_for_model
        ct_orga = get_ct(FakeOrganisation)
        ct_contact = get_ct(FakeContact)

        subject_pred = 'employs (test version)'
        self.assertFalse(RelationType.objects.filter(predicate=subject_pred))

        response = self.client.post(
            self.ADD_URL,
            data={
                'subject_predicate':  subject_pred,
                'object_predicate':   'is employed by (test version)',

                'subject_ctypes':     [ct_orga.id],
                'object_ctypes':      [ct_contact.id],

                'subject_properties': [pt_sub.id],
                'object_properties':  [pt_obj.id],

                'object_is_copiable': 'on',
            },
        )
        self.assertNoFormError(response)

        rel_type = self.get_object_or_fail(RelationType, predicate=subject_pred)
        self.assertListEqual(
            [ct_orga.id], [ct.id for ct in rel_type.subject_ctypes.all()],
        )

        self.assertListEqual(
            [pt_sub.id], [pt.id for pt in rel_type.subject_properties.all()],
        )

        self.assertFalse(rel_type.is_copiable)
        self.assertFalse(rel_type.minimal_display)

        sym_type = rel_type.symmetric_type
        self.assertTrue(sym_type.is_copiable)
        self.assertFalse(sym_type.minimal_display)
        self.assertEqual([ct_contact.id], [ct.id for ct in sym_type.subject_ctypes.all()])
        self.assertEqual([pt_obj.id],     [pt.id for pt in sym_type.subject_properties.all()])

    def test_create03(self):
        subject_pred = 'loves'
        response = self.client.post(
            self.ADD_URL,
            data={
                'subject_predicate': subject_pred,
                'object_predicate':  'is loved by',

                'subject_min_display': 'on',
            },
        )
        self.assertNoFormError(response)

        rel_type = self.get_object_or_fail(RelationType, predicate=subject_pred)
        self.assertTrue(rel_type.is_custom)
        self.assertFalse(rel_type.is_copiable)
        self.assertTrue(rel_type.minimal_display)

        sym_type = rel_type.symmetric_type
        self.assertFalse(sym_type.is_copiable)
        self.assertFalse(sym_type.minimal_display)

    def test_create04(self):
        subject_pred = 'loves'
        response = self.client.post(
            self.ADD_URL,
            data={
                'subject_predicate': subject_pred,
                'object_predicate':  'is loved by',

                'object_min_display': 'on',
            },
        )
        self.assertNoFormError(response)

        rel_type = self.get_object_or_fail(RelationType, predicate=subject_pred)
        self.assertTrue(rel_type.is_custom)
        self.assertFalse(rel_type.is_copiable)
        self.assertFalse(rel_type.minimal_display)

        sym_type = rel_type.symmetric_type
        self.assertFalse(sym_type.is_copiable)
        self.assertTrue(sym_type.minimal_display)

    def test_edit01(self):
        "Edit a not custom type => error."
        rt = RelationType.objects.smart_update_or_create(
            ('test-subfoo', 'subject_predicate'),
            ('test-objfoo', 'object_predicate'),
            is_custom=False,
        )[0]
        self.assertGET404(self._build_edit_url(rt))

    def test_edit02(self):
        "Edit a custom type."
        rt = RelationType.objects.smart_update_or_create(
            ('test-subfoo', 'subject_predicate'),
            ('test-objfoo', 'object_predicate'),
            is_custom=True,
        )[0]
        url = self._build_edit_url(rt)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(
            pgettext(
                'creme_config-relationship', 'Edit the type «{object}»'
            ).format(object=rt),
            context.get('title'),
        )
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

        # ---
        subject_pred = 'loves'
        object_pred  = 'is loved by'
        response = self.client.post(
            url,
            data={
                'subject_predicate': subject_pred,
                'object_predicate':  object_pred,
            },
        )
        self.assertNoFormError(response)

        rel_type = RelationType.objects.get(pk=rt.id)
        self.assertEqual(subject_pred, rel_type.predicate)
        self.assertEqual(object_pred,  rel_type.symmetric_type.predicate)

    def test_delete01(self):
        rt = RelationType.objects.smart_update_or_create(
            ('test-subfoo', 'subject_predicate'),
            ('test-subfoo', 'object_predicate'),
            is_custom=False,
        )[0]
        self.assertGET405(self.DEL_URL, data={'id': rt.id})

    def test_delete02(self):
        rt, srt = RelationType.objects.smart_update_or_create(
            ('test-subfoo', 'subject_predicate'),
            ('test-subfoo', 'object_predicate'),
            is_custom=True,
        )
        self.assertPOST200(self.DEL_URL, data={'id': rt.id})
        self.assertDoesNotExist(rt)
        self.assertDoesNotExist(srt)


class SemiFixedRelationTypeTestCase(CremeTestCase):
    ADD_URL = reverse('creme_config__create_semifixed_rtype')

    def setUp(self):
        super().setUp()
        self.login()

        self.loves = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving'),
            ('test-object_foobar',  'is loved by'),
        )[0]

        self.iori = FakeContact.objects.create(
            user=self.user, first_name='Iori', last_name='Yoshizuki',
        )

    def test_create01(self):
        url = self.ADD_URL
        self.assertGET200(url)

        predicate = 'Is loving Iori'
        response = self.client.post(
            url,
            data={
                'predicate':     predicate,
                'semi_relation': self.formfield_value_relation_entity(
                    self.loves.id, self.iori,
                ),
            },
        )
        self.assertNoFormError(response)

        semi_fixed_relations = SemiFixedRelationType.objects.all()
        self.assertEqual(1, len(semi_fixed_relations))

        smr = semi_fixed_relations[0]
        self.assertEqual(predicate,  smr.predicate)
        self.assertEqual(self.loves, smr.relation_type)
        self.assertEqual(self.iori,  smr.object_entity.get_real_entity())

    def test_create02(self):
        "Predicate is unique"
        predicate = 'Is loving Iori'
        SemiFixedRelationType.objects.create(
            predicate=predicate,
            relation_type=self.loves,
            object_entity=self.iori,
        )

        itsuki = FakeContact.objects.create(user=self.user, first_name='Itsuki', last_name='Akiba')
        response = self.assertPOST200(
            self.ADD_URL,
            data={
                'predicate':     predicate,
                'semi_relation': self.formfield_value_relation_entity(self.loves.id, itsuki),
            },
        )
        self.assertFormError(
            response, 'form', 'predicate',
            _('%(model_name)s with this %(field_label)s already exists.') % {
                'model_name': _('Semi-fixed type of relationship'),
                'field_label': _('Predicate'),
            },
        )

    def test_create03(self):
        "('relation_type', 'object_entity') => unique together."
        predicate = 'Is loving Iori'
        SemiFixedRelationType.objects.create(
            predicate=predicate,
            relation_type=self.loves,
            object_entity=self.iori,
        )

        url = self.ADD_URL
        predicate += ' (other)'
        response = self.assertPOST200(url, data={'predicate': predicate})
        self.assertFormError(response, 'form', 'semi_relation', _('This field is required.'))

        response = self.assertPOST200(
            url,
            data={
                'predicate':     predicate,
                'semi_relation': self.formfield_value_relation_entity(self.loves.id, self.iori),
            },
        )
        self.assertFormError(
            response, 'form', None,
            _('A semi-fixed type of relationship with this type and this object already exists.'),
        )

    def test_delete(self):
        sfrt = SemiFixedRelationType.objects.create(
            predicate='Is loving Iori',
            relation_type=self.loves,
            object_entity=self.iori,
        )
        self.assertPOST200(
            reverse('creme_config__delete_semifixed_rtype'),
            data={'id': sfrt.id},
        )
        self.assertDoesNotExist(sfrt)
