# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import timedelta
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.gui.merge import merge_form_registry
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldEnumValue,
    FakeContact,
    FakeImage,
    FakeOrganisation,
    FieldsConfig,
    HistoryLine,
    Language,
    Relation,
    RelationType,
    SetCredentials,
    history,
)

from .base import ViewsTestCase


class MergeViewsTestCase(ViewsTestCase):
    @staticmethod
    def _build_select_url(e1):
        return reverse('creme_core__select_entity_for_merge') + f'?id1={e1.id}'

    @staticmethod
    def _oldify(entity, hours_delta=1):
        mdate = entity.modified - timedelta(hours=hours_delta)
        entity.__class__.objects.filter(pk=entity.pk).update(modified=mdate)

    def test_select_entity_for_merge01(self):
        user = self.login()

        form_factory = merge_form_registry.get(FakeOrganisation)
        self.assertIsNotNone(form_factory)
        self.assertTrue(callable(form_factory))

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Gen-shi-ken')
        orga03 = create_orga(name='Manga Club')

        response = self.assertGET200(self._build_select_url(orga01))

        with self.assertNoException():
            contacts = response.context['page_obj'].object_list

        contacts = {*contacts}
        self.assertIn(orga02, contacts)
        self.assertIn(orga03, contacts)
        self.assertNotIn(orga01, contacts)

    def test_select_entity_for_merge02(self):
        "View credentials"
        user = self.login(is_superuser=False)

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE,
            set_type=SetCredentials.ESET_OWN,
        )
        orga = FakeOrganisation.objects.create(user=self.other_user, name='Genshiken')
        self.assertFalse(user.has_perm_to_view(orga))
        self.assertGET403(self._build_select_url(orga))

    def test_select_entity_for_merge03(self):
        "Edit credentials."
        user = self.login(is_superuser=False)

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_ALL,
        )
        orga = FakeOrganisation.objects.create(user=self.other_user, name='Genshiken')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_change(orga))
        self.assertGET403(self._build_select_url(orga))

    def test_select_entity_for_merge04(self):
        "Unregistered model."
        self.login()
        self.assertIsNone(merge_form_registry.get(FakeImage))

        image = FakeImage.objects.create(user=self.user, name='IMG#1')
        self.assertGET409(self._build_select_url(image))

    def test_merge01(self):
        "2 (fake) Organisations, some relationships duplicates."
        user = self.login()

        create_rtype = RelationType.objects.smart_update_or_create
        rtype01 = create_rtype(
            ('test-subject_member', 'is a member of',  [FakeContact]),
            ('test-object_member',  'has as a member', [FakeOrganisation]),
        )[0]
        rtype02 = create_rtype(
            ('test-subject_sponsors', 'sponsors',        [FakeOrganisation]),
            ('test-object_sponsors',  'is sponsored by', [FakeContact]),
        )[0]
        rtype03 = create_rtype(
            ('test-subject_hight_member', 'is a hight member of',  [FakeContact]),
            ('test-object_hight_member',  'has as a hight member', [FakeOrganisation]),
        )[0]

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype01 = create_ptype(str_pk='test-prop_manga', text='Manga related')
        ptype02 = create_ptype(str_pk='test-prop_anime', text='Anime related')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(
            name='Genshiken',   description='Otaku band.',   phone='8787878',
        )
        orga02 = create_orga(
            name='Gen-shi-ken', description='A great club.', email='genshiken@univ.jp',
        )

        create_contact = partial(FakeContact.objects.create, user=user)
        contact01 = create_contact(first_name='Chika',      last_name='Ogiue')
        contact02 = create_contact(first_name='Souichirou', last_name='Tanaka')

        # contact01 linked with the 2 organisations
        #   -> after merge, we expect only one relation, not 2
        # contact02 should be linked to the merged entity
        create_rel = partial(Relation.objects.create, user=user)
        rel1_1 = create_rel(type=rtype01, subject_entity=contact01, object_entity=orga01)
        rel1_2 = create_rel(type=rtype01, subject_entity=contact01, object_entity=orga02)
        rel1_3 = create_rel(type=rtype01, subject_entity=contact02, object_entity=orga02)

        rel2_1 = create_rel(type=rtype02, subject_entity=orga01, object_entity=contact01)
        rel2_2 = create_rel(type=rtype02, subject_entity=orga02, object_entity=contact01)
        rel2_3 = create_rel(type=rtype02, subject_entity=orga02, object_entity=contact02)

        # contact01 is linked with orga01, too, but not with the same relation-type
        # => Relation must not be deleted
        rel3_1 = create_rel(type=rtype03, subject_entity=contact01, object_entity=orga02)

        # 'prop3 'should be deleted, because orga01 has already a property with the same type
        create_prop = CremeProperty.objects.create
        prop1 = create_prop(type=ptype01, creme_entity=orga01)
        prop2 = create_prop(type=ptype02, creme_entity=orga02)
        prop3 = create_prop(type=ptype01, creme_entity=orga02)

        orga02_hlines = [*HistoryLine.objects.filter(entity=orga02.id)]

        last_hline_id = HistoryLine.objects.order_by('-id')[0].id

        old_modified = orga01.modified
        self._oldify(orga01)
        assert old_modified > self.refresh(orga01).modified

        url = self.build_merge_url(orga01, orga02)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            f_name = fields['name']
            f_email = fields['email']

        self.assertTrue(f_name.required)
        self.assertEqual([orga01.name,  orga02.name,  orga01.name],  f_name.initial)
        # orga01.email is empty
        self.assertEqual([orga01.email, orga02.email, orga02.email], f_email.initial)

        self.assertFalse(fields['capital'].required)

        description = ' '.join([orga01.description, orga02.description])
        response = self.client.post(
            url, follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'name_1':      orga01.name,
                'name_2':      orga02.name,
                'name_merged': orga01.name,  # <======

                'description_1':      orga01.description,
                'description_2':      orga02.description,
                'description_merged': description,  # <======

                'email_1':      '',
                'email_2':      orga02.email,
                'email_merged': orga02.email,  # <======
            },
        )
        self.assertNoFormError(response)
        self.assertRedirects(response, orga01.get_absolute_url())

        self.assertDoesNotExist(orga02)

        new_orga01 = self.refresh(orga01)
        self.assertEqual(orga01.name,  new_orga01.name)
        self.assertEqual(description,  new_orga01.description)
        self.assertEqual(orga02.email, new_orga01.email)

        # Relationships --
        rel1_1 = self.refresh(rel1_1)
        self.assertEqual(contact01.id,  rel1_1.subject_entity_id)
        self.assertEqual(rtype01,       rel1_1.type)
        self.assertEqual(new_orga01.id, rel1_1.object_entity_id)

        rel1_3 = self.assertStillExists(rel1_3)
        self.assertEqual(contact02.id,  rel1_3.subject_entity_id)
        self.assertEqual(rtype01,       rel1_3.type)
        self.assertEqual(new_orga01.id, rel1_3.object_entity_id)
        sym_rel1_3 = rel1_3.symmetric_relation
        self.assertEqual(new_orga01.id, sym_rel1_3.subject_entity_id)
        self.assertEqual(contact02.id,  sym_rel1_3.object_entity_id)

        self.assertStillExists(rel2_1)
        self.assertStillExists(rel2_3)

        # rel2 should have been deleted (no duplicate)
        self.assertDoesNotExist(rel1_2.symmetric_relation)
        self.assertDoesNotExist(rel1_2)

        self.assertDoesNotExist(rel2_2.symmetric_relation)
        self.assertDoesNotExist(rel2_2)

        self.assertRelationCount(1, contact01, rtype01.id, orga01)
        self.assertRelationCount(1, orga01,    rtype02.id, contact01)

        rel3_1 = self.assertStillExists(rel3_1)
        self.assertEqual(contact01.id,  rel3_1.subject_entity_id)
        self.assertEqual(rtype03,       rel3_1.type)
        self.assertEqual(new_orga01.id, rel1_3.object_entity_id)
        sym_rel3_1 = rel3_1.symmetric_relation
        self.assertEqual(new_orga01.id, sym_rel3_1.subject_entity_id)
        self.assertEqual(contact01.id,  sym_rel3_1.object_entity_id)

        # Properties --
        prop1 = self.refresh(prop1)
        self.assertEqual(ptype01,   prop1.type)
        self.assertEqual(orga01.id, prop1.creme_entity_id)

        prop2 = self.refresh(prop2)
        self.assertEqual(ptype02,   prop2.type)
        self.assertEqual(orga01.id, prop2.creme_entity_id)

        # prop3 should have been deleted (no duplicate)
        self.assertDoesNotExist(prop3)

        # History ----
        new_hlines = defaultdict(list)
        for hline in HistoryLine.objects.filter(id__gt=last_hline_id):
            new_hlines[hline.type].append(hline)

        edition_lines = new_hlines[history.TYPE_EDITION]
        self.assertEqual(1, len(edition_lines))
        self.assertEqual(orga01, edition_lines[0].entity.get_real_entity())
        # TODO: complete

        deletion_lines = new_hlines[history.TYPE_DELETION]
        self.assertEqual(1, len(deletion_lines))
        deletion_line = deletion_lines[0]
        self.assertEqual(orga02.entity_type, deletion_line.entity_ctype)
        self.assertEqual(str(orga02),    deletion_line.entity_repr)

        prop_lines = new_hlines[history.TYPE_PROP_ADD]
        self.assertEqual(1, len(prop_lines))
        prop_line = prop_lines[0]
        self.assertEqual(orga01,       prop_line.entity.get_real_entity())
        self.assertEqual([ptype02.id], prop_line.modifications)

        rel_lines = new_hlines[history.TYPE_RELATION]
        self.assertEqual(3, len(rel_lines))

        rel_line1 = next(
            filter(lambda hl: contact02 == hl.entity.get_real_entity(), rel_lines), None
        )
        self.assertIsNotNone(rel_line1)
        self.assertEqual([rtype01.id], rel_line1.modifications)

        rel_line2 = next(
            filter(lambda hl: orga01 == hl.entity.get_real_entity(), rel_lines), None
        )
        self.assertIsNotNone(rel_line2)
        self.assertEqual([rtype02.id], rel_line2.modifications)

        rel_line3 = next(
            filter(lambda hl: contact01 == hl.entity.get_real_entity(), rel_lines), None
        )
        self.assertIsNotNone(rel_line3)
        self.assertEqual([rtype03.id], rel_line3.modifications)

        sym_rel_line_ids = [hl.id for hl in new_hlines[history.TYPE_SYM_RELATION]]
        self.assertEqual(3, len(sym_rel_line_ids))

        sym_rel_line1 = rel_line1.related_line
        self.assertIn(sym_rel_line1.id, sym_rel_line_ids)
        self.assertEqual(orga01,                      sym_rel_line1.entity.get_real_entity())
        self.assertEqual([rtype01.symmetric_type_id], sym_rel_line1.modifications)

        sym_rel_line2 = rel_line2.related_line
        self.assertIn(sym_rel_line2.id, sym_rel_line_ids)
        self.assertEqual(contact02,                   sym_rel_line2.entity.get_real_entity())
        self.assertEqual([rtype02.symmetric_type_id], sym_rel_line2.modifications)

        sym_rel_line3 = rel_line3.related_line
        self.assertIn(sym_rel_line3.id, sym_rel_line_ids)
        self.assertEqual(orga01,                      sym_rel_line3.entity.get_real_entity())
        self.assertEqual([rtype03.symmetric_type_id], sym_rel_line3.modifications)

        self.assertFalse(new_hlines[history.TYPE_CREATION])
        self.assertFalse(new_hlines[history.TYPE_RELATED])
        self.assertFalse(new_hlines[history.TYPE_PROP_DEL])
        self.assertFalse(new_hlines[history.TYPE_RELATION_DEL])
        self.assertFalse(new_hlines[history.TYPE_SYM_REL_DEL])
        self.assertFalse(new_hlines[history.TYPE_AUX_CREATION])
        self.assertFalse(new_hlines[history.TYPE_AUX_EDITION])
        self.assertFalse(new_hlines[history.TYPE_AUX_DELETION])

        for hline in orga02_hlines:
            refreshed_hline = self.assertStillExists(hline)
            self.assertIsNone(refreshed_hline.entity)

    def test_merge02(self):
        "2 Contacts, M2M, foreign key to CremeEntities"
        user = self.login()

        create_img = partial(FakeImage.objects.create, user=user)
        image1 = create_img(name='Kosaka face')
        image2 = create_img(name='Kousaka selfie')
        create_img(name='Genshiken logo')  # Should not be proposed by the form

        create_contact = partial(FakeContact.objects.create, user=user)
        contact01 = create_contact(first_name='Makoto', last_name='Kosaka',  image=image1)
        contact02 = create_contact(first_name='Makoto', last_name='Kousaka', image=image2)

        language1, language2 = Language.objects.all()[:2]
        language3 = Language.objects.create(name='Klingon')  # code='KLN'

        contact01.languages.set([language1])
        contact02.languages.set([language1, language2])

        url = self.build_merge_url(contact01, contact02)
        response = self.assertGET200(url)

        with self.assertNoException():
            f_image = response.context['form'].fields['image']

        self.assertFalse(f_image.required)
        self.assertEqual([image1.id,  image2.id,  image1.id],  f_image.initial)

        self.assertEqual(user, f_image._original_field.user)
        self.assertEqual(FakeImage, f_image._original_field.model)

        response = self.client.post(
            url, follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'first_name_1':      contact01.first_name,
                'first_name_2':      contact02.first_name,
                'first_name_merged': contact01.first_name,

                'last_name_1':      contact01.last_name,
                'last_name_2':      contact02.last_name,
                'last_name_merged': contact01.last_name,

                'languages_1':      [language1.id],
                'languages_2':      [language1.id, language2.id],
                'languages_merged': [language3.id],  # <======

                'image_1':      image1.id,
                'image_2':      image2.id,
                'image_merged': image2.id,
            },
        )
        self.assertNoFormError(response)
        self.assertRedirects(response, contact01.get_absolute_url())

        self.assertDoesNotExist(contact02)

        new_contact01 = self.refresh(contact01)
        self.assertEqual(contact01.first_name, new_contact01.first_name)
        self.assertEqual(contact01.last_name,  new_contact01.last_name)
        self.assertListEqual([language3],      [*new_contact01.languages.all()])
        self.assertEqual(image2,               new_contact01.image)

    def test_merge03(self):
        "Initial values come in priority from the last edited entity."
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Gen-shi-ken')

        old_modified = orga01.modified
        self._oldify(orga02)
        assert old_modified > self.refresh(orga02).modified

        response = self.assertGET200(self.build_merge_url(orga01, orga02))

        with self.assertNoException():
            f_name = response.context['form'].fields['name']

        self.assertListEqual(
            [orga01.name, orga02.name, orga02.name],
            f_name.initial
        )

    def test_merge04(self):
        "Nullable foreign key to CremeEntities."
        user = self.login()
        image = FakeImage.objects.create(user=user, name='Kosaka face')

        create_contact = partial(FakeContact.objects.create, user=user)
        contact01 = create_contact(first_name='Makoto', last_name='Kosaka', image=image)
        contact02 = create_contact(first_name='Makoto', last_name='Kousaka')

        response = self.assertGET200(self.build_merge_url(contact01, contact02))

        with self.assertNoException():
            f_image = response.context['form'].fields['image']

        self.assertEqual(user, f_image._original_field.user)
        self.assertEqual(FakeImage, f_image._original_field.model)

    def test_merge05(self):
        "Unregistered model."
        user = self.login()
        self.assertIsNone(merge_form_registry.get(FakeImage))

        create_image = partial(FakeImage.objects.create, user=user)
        image1 = create_image(name='IMG#1')
        image2 = create_image(name='IMG#2')

        self.assertGET409(self.build_merge_url(image1, image2))

    def test_merge_relations(self):
        "No relationships duplicates."
        user = self.login()

        create_rtype = RelationType.objects.smart_update_or_create
        rtype = create_rtype(
            ('test-subject_member', 'is a member of',  [FakeContact]),
            ('test-object_member',  'has as a member', [FakeOrganisation]),
        )[0]

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(
            name='Genshiken',   description='Otaku band.',   phone='8787878',
        )
        orga02 = create_orga(
            name='Gen-shi-ken', description='A great club.', email='genshiken@univ.jp',
        )

        create_contact = partial(FakeContact.objects.create, user=user)
        contact01 = create_contact(first_name='Chika',      last_name='Ogiue')
        contact02 = create_contact(first_name='Souichirou', last_name='Tanaka')

        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        rel1 = create_rel(subject_entity=contact01, object_entity=orga01)
        rel2 = create_rel(subject_entity=contact02, object_entity=orga02)

        response = self.client.post(
            self.build_merge_url(orga01, orga02),
            follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'name_1':      orga01.name,
                'name_2':      orga02.name,
                'name_merged': orga01.name,
            },
        )
        self.assertNoFormError(response)
        self.assertRedirects(response, orga01.get_absolute_url())

        self.assertDoesNotExist(orga02)

        new_orga01 = self.refresh(orga01)
        self.assertEqual(orga01.name,  new_orga01.name)

        rel1 = self.refresh(rel1)
        self.assertEqual(contact01.id,  rel1.subject_entity_id)
        self.assertEqual(rtype,         rel1.type)
        self.assertEqual(new_orga01.id, rel1.object_entity_id)

        rel2 = self.assertStillExists(rel2)
        self.assertEqual(contact02.id,  rel2.subject_entity_id)
        self.assertEqual(rtype,         rel2.type)
        self.assertEqual(new_orga01.id, rel2.object_entity_id)

        sym_rel2 = rel2.symmetric_relation
        self.assertEqual(new_orga01.id, sym_rel2.subject_entity_id)
        self.assertEqual(contact02.id,  sym_rel2.object_entity_id)

    def test_merge_customfields(self):
        user = self.login()

        create_cf = partial(
            CustomField.objects.create,
            field_type=CustomField.INT,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        cf_01 = create_cf(name='Number of manga')
        cf_02 = create_cf(name='Number of anime')
        cf_03 = create_cf(name='Club', field_type=CustomField.ENUM)
        cf_04 = create_cf(name='Last convention', field_type=CustomField.DATETIME)

        create_evalue = CustomFieldEnumValue.objects.create
        enum_val1_1 = create_evalue(custom_field=cf_03, value='Club Manga')
        create_evalue(custom_field=cf_03, value='Club Anime')

        create_contact = partial(FakeContact.objects.create, user=user)
        contact01 = create_contact(first_name='Makoto', last_name='Kosaka')
        contact02 = create_contact(first_name='Makoto', last_name='Kousaka')

        create_cfval_01 = partial(cf_01.value_class.objects.create, custom_field=cf_01)
        cf_01_value01 = create_cfval_01(entity=contact01, value=500)
        cf_01_value02 = create_cfval_01(entity=contact02, value=510)

        cf_02_value01 = cf_02.value_class.objects.create(
            custom_field=cf_02, entity=contact01, value=100,
        )

        cf_03_value02 = cf_03.value_class(custom_field=cf_03, entity=contact02)
        cf_03_value02.set_value_n_save(enum_val1_1.id)

        url = self.build_merge_url(contact01, contact02)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            f_cf_01 = fields[f'custom_field-{cf_01.id}']
            f_cf_02 = fields[f'custom_field-{cf_02.id}']
            f_cf_03 = fields[f'custom_field-{cf_03.id}']

        self.assertFalse(f_cf_01.required)
        self.assertEqual([500,  510,  500],  f_cf_01.initial)
        self.assertEqual([100,  None, 100],  f_cf_02.initial)
        self.assertEqual([None, enum_val1_1.id, enum_val1_1.id], f_cf_03.initial)

        self.assertEqual(user, f_cf_01._original_field.user)
        self.assertEqual(user, f_cf_02._original_field.user)
        self.assertEqual(user, f_cf_03._original_field.user)

        response = self.client.post(
            url, follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'first_name_1':      contact01.first_name,
                'first_name_2':      contact02.first_name,
                'first_name_merged': contact01.first_name,

                'last_name_1':      contact01.last_name,
                'last_name_2':      contact02.last_name,
                'last_name_merged': contact01.last_name,

                f'custom_field-{cf_01.id}_1': 500,
                f'custom_field-{cf_01.id}_2': 510,
                f'custom_field-{cf_01.id}_merged': 510,

                f'custom_field-{cf_02.id}_1': 100,
                f'custom_field-{cf_02.id}_2': '',
                f'custom_field-{cf_02.id}_merged': '',

                f'custom_field-{cf_03.id}_1': '',
                f'custom_field-{cf_03.id}_2': enum_val1_1.id,
                f'custom_field-{cf_03.id}_merged': enum_val1_1.id,

                f'custom_field-{cf_04.id}_1': '',
                f'custom_field-{cf_04.id}_2': '',
                f'custom_field-{cf_04.id}_merged': '',
            },
        )
        self.assertNoFormError(response)
        self.assertRedirects(response, contact01.get_absolute_url())

        self.assertDoesNotExist(contact02)

        new_contact01 = self.refresh(contact01)
        self.assertEqual(contact01.first_name, new_contact01.first_name)
        self.assertEqual(contact01.last_name,  new_contact01.last_name)

        cf_01_values = cf_01.value_class.objects.filter(
            id__in=(cf_01_value01.id, cf_01_value02.id),
        )
        self.assertEqual(1, len(cf_01_values))

        cf_01_value = cf_01_values[0]
        self.assertEqual(contact01.id, cf_01_value.entity_id)
        self.assertEqual(510, cf_01_value.value)

        self.assertDoesNotExist(cf_02_value01)

        cf_03_values = cf_03.value_class.objects.filter(custom_field=cf_03)
        self.assertEqual(1, len(cf_03_values))

        cf_03_value = cf_03_values[0]
        self.assertEqual(contact01.id, cf_03_value.entity_id)
        self.assertEqual(enum_val1_1, cf_03_value.value)

        self.assertFalse(cf_04.value_class.objects.all())

    def test_error01(self):
        "Try to merge 2 entities with different types."
        user = self.login()

        orga = FakeOrganisation.objects.create(user=user, name='Genshiken')
        contact = FakeContact.objects.create(user=user, first_name='Chika', last_name='Ogiue')

        self.assertGET409(self.build_merge_url(orga, contact))

    def test_error02(self):
        "Required fields."
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Gen-shi-ken')

        # ---
        response1 = self.assertGET200(
            self.build_merge_url(orga01, orga02)
        )
        with self.assertNoException():
            fields = response1.context['form'].fields
            name_f = fields['name']
            phone_f = fields['phone']

        self.assertTrue(name_f.required)
        self.assertFalse(phone_f.required)

        # ---
        response2 = self.assertPOST200(
            self.build_merge_url(orga01, orga02),
            follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                # 'user_merged': user.id,  # <======

                'name_1':      orga01.name,
                'name_2':      orga02.name,
                'name_merged': '',  # <======
            },
        )
        msg = _('This field is required.')
        self.assertFormError(response2, 'form', 'user', msg)
        self.assertFormError(response2, 'form', 'name', msg)

    def test_error03(self):
        "Try to merge an entity with itself (by forging the URL)."
        user = self.login()

        orga = FakeOrganisation.objects.create(user=user, name='Genshiken')
        self.assertGET409(self.build_merge_url(orga, orga))

    def test_perm01(self):
        user = self.login(is_superuser=False)

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE,
            set_type=SetCredentials.ESET_OWN,
        )

        create_orga = FakeOrganisation.objects.create
        orga01 = create_orga(user=user,            name='Genshiken')
        orga02 = create_orga(user=self.other_user, name='Gen-shi-ken')

        can_view = user.has_perm_to_view
        self.assertTrue(can_view(orga01))
        self.assertTrue(user.has_perm_to_change(orga01))

        self.assertFalse(can_view(orga02))
        self.assertFalse(user.has_perm_to_delete(orga02))

        self.assertGET403(self.build_merge_url(orga01, orga02))
        self.assertGET403(self.build_merge_url(orga02, orga01))

    def test_fields_config_hidden(self):
        user = self.login()

        hidden_fname = 'phone'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        create_contact = partial(FakeContact.objects.create, user=user)
        contact01 = create_contact(first_name='Makoto', last_name='Kosaka')
        contact02 = create_contact(first_name='Makoto', last_name='Kousaka')

        url = self.build_merge_url(contact01, contact02)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('last_name', fields)
        self.assertNotIn(hidden_fname, fields)

        response = self.client.post(
            url, follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'first_name_1':      contact01.first_name,
                'first_name_2':      contact02.first_name,
                'first_name_merged': contact01.first_name,

                'last_name_1':      contact01.last_name,
                'last_name_2':      contact02.last_name,
                'last_name_merged': contact01.last_name,
            },
        )
        self.assertNoFormError(response)
        self.assertDoesNotExist(contact02)

        new_contact01 = self.refresh(contact01)
        self.assertEqual(contact01.first_name, new_contact01.first_name)
        self.assertEqual(contact01.last_name,  new_contact01.last_name)

    def test_fields_config_required(self):
        user = self.login()

        fname = 'phone'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(fname, {FieldsConfig.REQUIRED: True})],
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(name='Genshiken',   phone='112233')
        orga02 = create_orga(name='Gen-shi-ken', phone='112234')

        # ---
        response1 = self.assertGET200(
            self.build_merge_url(orga01, orga02)
        )
        with self.assertNoException():
            fields = response1.context['form'].fields
            email_f = fields['email']
            phone_f = fields[fname]

        self.assertFalse(email_f.required)
        self.assertTrue(phone_f.required)

        # ---
        response2 = self.assertPOST200(
            self.build_merge_url(orga01, orga02),
            follow=True,
            data={
                'user_1':      user.id,
                'user_2':      user.id,
                'user_merged': user.id,

                'name_1':      orga01.name,
                'name_2':      orga02.name,
                'name_merged': orga01.name,

                f'{fname}_1': orga01.phone,
                f'{fname}_2': orga02.phone,
                f'{fname}_merged': '',  # <======
            },
        )
        self.assertFormError(response2, 'form', fname, _('This field is required.'))
