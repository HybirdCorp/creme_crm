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
        self.login_as_root()

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
        self.assertFalse(rel_type.subject_forbidden_properties.all())

        sym_type = rel_type.symmetric_type
        self.assertEqual(object_pred, sym_type.predicate)
        self.assertFalse(sym_type.is_copiable)
        self.assertFalse(sym_type.minimal_display)
        self.assertFalse(sym_type.subject_ctypes.all())
        self.assertFalse(sym_type.subject_properties.all())
        self.assertFalse(sym_type.subject_forbidden_properties.all())

    def test_create02(self):
        "Property types (mandatory & forbidden)."
        create_pt = CremePropertyType.objects.smart_update_or_create
        pt_sub = create_pt(
            # str_pk='test-pt_sub',
            text='has cash',
            subject_ctypes=[FakeOrganisation],
        )
        pt_obj = create_pt(
            # str_pk='test-pt_obj',
            text='need cash',
            subject_ctypes=[FakeContact],
        )

        # forbidden_pt_sub = create_pt(str_pk='test-pt_forb_sub', text='is greedy')
        # forbidden_pt_obj = create_pt(str_pk='test-pt_forb_obj', text='is shy')
        forbidden_pt_sub = create_pt(text='is greedy')
        forbidden_pt_obj = create_pt(text='is shy')

        subject_pred = 'employs (test version)'
        self.assertFalse(RelationType.objects.filter(predicate=subject_pred))

        get_ct = ContentType.objects.get_for_model
        data = {
            'subject_predicate': subject_pred,
            'object_predicate': 'is employed by (test version)',

            'subject_ctypes': [get_ct(FakeOrganisation).id],
            'object_ctypes': [get_ct(FakeContact).id],

            'subject_properties': [pt_sub.id],
            'object_properties': [pt_obj.id],

            # 'subject_forbidden_properties': [forbidden_pt_sub.id],
            # 'object_forbidden_properties': [forbidden_pt_obj.id],

            'object_is_copiable': 'on',
        }
        # Error ---
        response1 = self.client.post(
            self.ADD_URL,
            data={
                **data,
                'subject_forbidden_properties': [forbidden_pt_sub.id, pt_sub.id],
                'object_forbidden_properties':  [forbidden_pt_obj.id, pt_obj.id],
            },
        )
        form = response1.context['form']
        msg = _(
            'These property types cannot be mandatory and forbidden at the '
            'same time: %(properties)s'
        )
        self.assertFormError(
            form,
            field='subject_forbidden_properties',
            errors=msg % {'properties': pt_sub.text},
        )
        self.assertFormError(
            form,
            field='object_forbidden_properties',
            errors=msg % {'properties': pt_obj.text},
        )

        # OK ---
        response2 = self.client.post(
            self.ADD_URL,
            data={
                **data,
                'subject_forbidden_properties': [forbidden_pt_sub.id],
                'object_forbidden_properties':  [forbidden_pt_obj.id],
            },
        )
        self.assertNoFormError(response2)

        rel_type = self.get_object_or_fail(RelationType, predicate=subject_pred)
        self.assertListEqual([FakeOrganisation], [*rel_type.subject_models])
        self.assertCountEqual([pt_sub], rel_type.subject_properties.all())
        self.assertCountEqual(
            [forbidden_pt_sub], rel_type.subject_forbidden_properties.all(),
        )

        self.assertFalse(rel_type.is_copiable)
        self.assertFalse(rel_type.minimal_display)

        sym_type = rel_type.symmetric_type
        self.assertTrue(sym_type.is_copiable)
        self.assertFalse(sym_type.minimal_display)
        self.assertListEqual([FakeContact], [*sym_type.subject_models])
        self.assertCountEqual([pt_obj], sym_type.subject_properties.all())
        self.assertCountEqual(
            [forbidden_pt_obj], sym_type.subject_forbidden_properties.all(),
        )

    def test_create_minimal_display_subject(self):
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

    def test_create_minimal_display_object(self):
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

    def test_edit(self):
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

    def test_edit_error01(self):
        "Edit a not custom type."
        rt = RelationType.objects.smart_update_or_create(
            ('test-subfoo', 'subject_predicate'),
            ('test-objfoo', 'object_predicate'),
            is_custom=False,
        )[0]
        self.assertGET404(self._build_edit_url(rt))

    def test_edit_error02(self):
        "Edit a disabled type."
        rt = RelationType.objects.smart_update_or_create(
            ('test-subfoo', 'subject_predicate'),
            ('test-objfoo', 'object_predicate'),
            is_custom=True,
        )[0]
        rt.enabled = False
        rt.save()

        self.assertGET404(self._build_edit_url(rt))

    def test_disable01(self):
        rt = RelationType.objects.smart_update_or_create(
            ('test-subject_foo', 'subject_predicate'),
            ('test-object_foo', 'object_predicate'),
        )[0]

        url = reverse('creme_config__disable_rtype', args=(rt.id,))
        self.assertGET405(url)

        self.assertPOST200(url)

        rt = self.refresh(rt)
        self.assertFalse(rt.enabled)
        self.assertFalse(rt.symmetric_type.enabled)

        self.assertPOST404(reverse('creme_config__disable_rtype', args=('test-subject_bar',)))

    def test_disable02(self):
        "Disable internal type => error."
        rt = RelationType.objects.smart_update_or_create(
            ('test-subject_foo', 'subject_predicate'),
            ('test-object_foo', 'object_predicate'),
            is_internal=True,
        )[0]

        self.assertPOST409(reverse('creme_config__disable_rtype', args=(rt.id,)))

    def test_enable(self):
        rt, srt = RelationType.objects.smart_update_or_create(
            ('test-subfoo', 'subject_predicate'),
            ('test-objfoo', 'object_predicate'),
        )
        rt.enabled = False
        rt.save()
        srt.enabled = False
        srt.save()

        url = reverse('creme_config__enable_rtype', args=(rt.id,))
        self.assertGET405(url)

        self.assertPOST200(url)

        rt = self.refresh(rt)
        self.assertTrue(rt.enabled)
        self.assertTrue(rt.symmetric_type.enabled)

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
        self.user = self.login_as_root_and_get()

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
        iori = self.iori
        response = self.client.post(
            url,
            data={
                'predicate':     predicate,
                'semi_relation': self.formfield_value_relation_entity(self.loves, iori),
            },
        )
        self.assertNoFormError(response)

        smr = self.get_alone_element(SemiFixedRelationType.objects.all())
        self.assertEqual(predicate,  smr.predicate)
        self.assertEqual(self.loves, smr.relation_type)
        self.assertEqual(iori.entity_type, smr.object_ctype)
        self.assertEqual(iori, smr.object_entity.get_real_entity())
        self.assertEqual(iori, smr.real_object)

    def test_create02(self):
        "Predicate is unique."
        predicate = 'Is loving Iori'
        SemiFixedRelationType.objects.create(
            predicate=predicate,
            relation_type=self.loves,
            real_object=self.iori,
        )

        itsuki = FakeContact.objects.create(user=self.user, first_name='Itsuki', last_name='Akiba')
        response = self.assertPOST200(
            self.ADD_URL,
            data={
                'predicate':     predicate,
                'semi_relation': self.formfield_value_relation_entity(self.loves, itsuki),
            },
        )
        self.assertFormError(
            response.context['form'],
            field='predicate',
            errors=_('%(model_name)s with this %(field_label)s already exists.') % {
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
            real_object=self.iori,
        )

        url = self.ADD_URL
        predicate += ' (other)'
        response1 = self.assertPOST200(url, data={'predicate': predicate})
        self.assertFormError(
            response1.context['form'],
            field='semi_relation',
            errors=_('This field is required.'),
        )

        # ---
        response2 = self.assertPOST200(
            url,
            data={
                'predicate':     predicate,
                'semi_relation': self.formfield_value_relation_entity(self.loves, self.iori),
            },
        )
        self.assertFormError(
            response2.context['form'],
            field=None,
            errors=_(
                'A semi-fixed type of relationship with this type and this object already exists.'
            ),
        )

    def test_edit01(self):
        predicate = 'Is loving Iori'
        sfrt = SemiFixedRelationType.objects.create(
            predicate=predicate,
            relation_type=self.loves,
            real_object=self.iori,
        )

        url = reverse('creme_config__edit_semifixed_rtype', args=(sfrt.id,))
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields

        self.assertNotIn('semi_relation', fields)
        self.assertNotIn('relation_type', fields)
        self.assertNotIn('object_entity', fields)

        predicate += ' very much'
        self.assertNoFormError(self.client.post(url, data={'predicate': predicate}))
        self.assertEqual(predicate, self.refresh(sfrt).predicate)

    def test_edit02(self):
        "The relation type is disabled => error."
        rtype = self.loves
        rtype.enabled = False
        rtype.save()

        sfrt = SemiFixedRelationType.objects.create(
            predicate='Is loving Iori',
            relation_type=rtype,
            real_object=self.iori,
        )
        self.assertGET404(
            reverse('creme_config__edit_semifixed_rtype', args=(sfrt.id,))
        )

    def test_delete(self):
        sfrt = SemiFixedRelationType.objects.create(
            predicate='Is loving Iori',
            relation_type=self.loves,
            real_object=self.iori,
        )
        self.assertPOST200(
            reverse('creme_config__delete_semifixed_rtype'),
            data={'id': sfrt.id},
        )
        self.assertDoesNotExist(sfrt)
