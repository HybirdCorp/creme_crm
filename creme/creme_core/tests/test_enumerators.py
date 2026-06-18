from decimal import Decimal
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.db.models import ForeignKey
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import override as override_language

from creme.creme_core import enumerators
from creme.creme_core.core.entity_filter import EF_CREDENTIALS
from creme.creme_core.core.enumerable import enumerable_registry
from creme.creme_core.models import (
    CremeUser,
    EntityFilter,
    FakeContact,
    FakeImage,
    FakeInvoiceLine,
    FakeOrganisation,
    FakeReport,
    FakeSector,
    HistoryLine,
    Vat,
)
from creme.creme_core.models.custom_field import (
    CustomField,
    CustomFieldEnumValue,
)
from creme.creme_core.models.fields import (
    CTypeForeignKey,
    EntityCTypeForeignKey,
)

from .base import CremeTestCase


class MiscEnumeratorsTestCase(CremeTestCase):
    def test_content_type_enumerator(self):
        user = self.get_root_user()
        ctype_fk = HistoryLine._meta.get_field('entity_ctype')
        self.assertIsInstance(ctype_fk, ForeignKey)
        self.assertEqual(ContentType, ctype_fk.related_model)

        e = enumerators.ContentTypeEnumerator(ctype_fk)

        with self.assertLogs(level='CRITICAL') as logs_manager:
            choices = e.choices(user)
        self.assertListEqual(
            [{'value': 0, 'label': _('Error (please contact your administrator)')}],
            choices,
        )
        self.assertIn(
            'use an EntityCTypeForeignKey if you reference only CremeEntities',
            logs_manager.output[0],
        )

        # TODO: need a fake model with a ForeignKey(ContentType, ...)
        self.assertEqual(
            enumerators.ContentTypeEnumerator,
            # enumerable_registry._enums_4_models.get(ContentType)
            enumerable_registry._enums_4_models[ContentType],
        )

    def test_entity_enumerator(self):
        role = self.create_role(allowed_apps=['creme_core'])
        self.add_credentials(role, own=['VIEW'])

        user = self.create_user(role=role)

        create_img = FakeImage.objects.create
        img1 = create_img(name='Lizard', user=user)
        img2 = create_img(name='Flower', user=user)
        img3 = create_img(name='Img #3', user=self.get_root_user())

        self.assertTrue(user.has_perm_to_view(img1))
        self.assertTrue(user.has_perm_to_view(img2))
        self.assertFalse(user.has_perm_to_view(img3))

        e = enumerators.EntityEnumerator(FakeContact._meta.get_field('image'))
        self.assertListEqual(
            [
                {'value': img2.id, 'label': img2.name},
                {'value': img1.id, 'label': img1.name},
            ],
            e.choices(user),
        )

        self.assertEqual(('header_filter_search_field',), e.search_fields)
        self.assertListEqual(
            [{'value': img2.id, 'label': img2.name}],
            e.choices(user, term='Flow'),
        )

        # # Hard coded behaviour for entity (remove in the future)
        # self.assertIsInstance(
        #     EnumerableRegistry().enumerator_by_fieldname(model=FakeContact, field_name='image'),
        #     enumerators.EntityEnumerator,
        # )

    def test_minion_enumerator(self):
        user = self.get_root_user()
        sector1, sector2 = FakeSector.objects.all()[:2]
        dis_sector = FakeSector.objects.create(title='Horses', disabled=now())

        e = enumerators.MinionEnumerator(FakeContact._meta.get_field('sector'))
        choices = e.choices(user)
        self.assertEqual(len(choices), FakeSector.objects.count())
        self.assertIn({'value': sector1.id, 'label': sector1.title}, choices)
        self.assertIn({'value': sector2.id, 'label': sector2.title}, choices)
        self.assertIn(
            {'value': dis_sector.id, 'label': _('{} (disabled)').format(dis_sector.title)},
            choices,
        )

        # ---
        self.assertListEqual(
            [{'value': sector1.id, 'label': sector1.title}],
            e.choices(user, term=sector1.title[:-1]),
        )

    @override_language('en')
    def test_vat_enumerator(self):
        user = self.get_root_user()
        enum = enumerators.VatEnumerator(FakeInvoiceLine._meta.get_field('vat_value'))

        self.assertListEqual(
            [{'label': str(vat), 'value': vat.pk} for vat in Vat.objects.order_by('value')],
            [*enum.choices(user)],
        )

        vat_200 = self.get_object_or_fail(Vat, value=Decimal('20.00'))
        vat_212 = self.get_object_or_fail(Vat, value=Decimal('21.20'))

        # SQLite seems to compare the floating value so '20' will match '20.00' only
        if connection.vendor == 'sqlite':
            self.assertListEqual(
                [{'label': '20.00 %', 'value': vat_200.pk}],
                [*enum.choices(user, term='20')],
            )
        # The other databases are using a native decimal value so '20' will match
        # both '20.00' & '21.20'
        else:
            self.assertListEqual(
                [
                    {'label': '20.00 %', 'value': vat_200.pk},
                    {'label': '21.20 %', 'value': vat_212.pk},
                ],
                [*enum.choices(user, term='20')],
            )

        # ---
        dis_vat = Vat.objects.create(value=Decimal('50.00'), disabled=now())
        self.assertIn(
            {'label': _('{} (disabled)').format(dis_vat), 'value': dis_vat.pk},
            [*enum.choices(user)],
        )

    def test_customfield_enumerator(self):
        user = self.get_root_user()

        cfield = CustomField.objects.create(
            content_type=FakeContact, name='Languages', field_type=CustomField.ENUM,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        lang_A = create_evalue(value='C')
        lang_B = create_evalue(value='Python')
        lang_C = create_evalue(value='Rust')

        enum = enumerators.CustomFieldEnumerator(cfield)
        self.assertListEqual(
            [
                {'label': 'C',      'value': lang_A.pk},
                {'label': 'Python', 'value': lang_B.pk},
                {'label': 'Rust',   'value': lang_C.pk},
            ],
            enum.choices(user),
        )

        self.assertListEqual(
            [{'label': 'Rust', 'value': lang_C.pk}],
            enum.choices(user, term='Ru'),
        )

        self.assertListEqual(
            [
                {'label': 'C',      'value': lang_A.pk},
                {'label': 'Python', 'value': lang_B.pk},
            ],
            enum.choices(user, limit=2),
        )

        self.assertListEqual(
            [
                {'label': 'C',    'value': lang_A.pk},
                {'label': 'Rust', 'value': lang_C.pk},
            ],
            enum.choices(user, only=[lang_A.pk, lang_C.pk]),
        )


class UserEnumeratorsTestCase(CremeTestCase):
    def test_simple(self):
        user = self.get_root_user()
        other_user = self.create_user()

        # Alphabetically-first user (__str__, not username)
        first_user = self.create_user(
            username='noir', email='chloe@noir.jp',
            first_name='Chloe', last_name='Noir',
        )
        self.assertGreater(str(user), str(first_user))

        team = self.create_team('Team#1', user, other_user)

        inactive = CremeUser.objects.create(username='deunan', is_active=False)

        e = enumerators.UserEnumerator(FakeContact._meta.get_field('user'))
        choices = e.choices(user)
        self.assertIsList(choices)

        first_choice = choices[0]
        self.assertIsInstance(first_choice, dict)
        self.assertIn('value', first_choice)

        def find_user_dict(u):
            user_as_dicts = [
                (i, c) for i, c in enumerate(choices) if c['value'] == u.id
            ]
            self.assertEqual(1, len(user_as_dicts))
            return user_as_dicts[0]

        user_index, user_dict = find_user_dict(user)
        self.assertDictEqual(
            {'value': user.pk, 'label': str(user)},
            user_dict,
        )

        other_index, other_dict = find_user_dict(other_user)
        self.assertEqual(
            {'value': other_user.pk, 'label': str(other_user)},
            other_dict,
        )

        first_index, first_dict = find_user_dict(first_user)
        self.assertDictEqual(
            {'value': first_user.pk, 'label': str(first_user)},
            first_dict,
        )

        self.assertGreater(other_index, user_index)
        self.assertGreater(user_index,  first_index)

        self.assertDictEqual(
            {'value': team.pk, 'label': team.username, 'group': _('Teams')},
            find_user_dict(team)[1],
        )
        self.assertEqual(
            {
                'value': inactive.pk,
                'label': str(inactive),
                'group': _('Inactive users'),
            },
            find_user_dict(inactive)[1]
        )

    def test_limit(self):
        user = self.get_root_user()

        # Alphabetically-first user (__str__, not username)
        user2 = self.create_user(
            username='noir', email='chloe@noir.jp',
            first_name='Chloe', last_name='Noir',
        )
        self.assertLess(str(user2), str(user))

        enum = enumerators.UserEnumerator(FakeContact._meta.get_field('user'))

        all_choices = enum.choices(user)

        self.assertListEqual(all_choices[:2], enum.choices(user, limit=2))
        self.assertListEqual(all_choices, enum.choices(user, limit=100))

    def test_only(self):
        user = self.get_root_user()
        user2 = self.create_user()

        enum = enumerators.UserEnumerator(FakeContact._meta.get_field('user'))

        self.assertListEqual(
            [{'value': user2.pk, 'label': str(user2)}],
            enum.choices(user, only=[user2.pk]),
        )

    def test_term(self):
        user = self.get_root_user()

        # Alphabetically-first user (__str__, not username)
        first_user = self.create_user(
            username='noir', email='chloe@noir.jp',
            first_name='Chloe', last_name='Noir',
        )
        self.assertLess(str(first_user), str(user))

        enum = enumerators.UserEnumerator(FakeContact._meta.get_field('user'))
        self.assertListEqual(
            [str(first_user)],
            [c['label'] for c in enum.choices(user, term='noir')]
        )
        self.assertListEqual(
            [str(user)],
            [c['label'] for c in enum.choices(user, term=user.username)],
        )


class EntityFilterEnumeratorTestCase(CremeTestCase):
    def test_simple(self):
        user = self.get_root_user()

        create_filter = EntityFilter.objects.create
        efilter1 = create_filter(
            id='test-filter01',
            name='Filter 01',
            entity_type=FakeContact,
            is_custom=True,
        )
        efilter2 = create_filter(
            id='test-filter02',
            name='Filter 02',
            entity_type=FakeOrganisation,
            is_custom=True, user=user, is_private=True,
        )
        efilter3 = create_filter(
            id='test-filter03',
            name='Filter 01',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,  # <==
        )

        e = enumerators.EntityFilterEnumerator(FakeReport._meta.get_field('efilter'))
        choices = e.choices(user)
        self.assertIsList(choices)

        first_choice = choices[0]
        self.assertIsInstance(first_choice, dict)
        self.assertIn('value', first_choice)

        def find_efilter_dict(efilter):
            return self.get_alone_element(
                [c for c in choices if c['value'] == efilter.id]
            )

        self.assertDictEqual(
            {
                'value': efilter1.pk,
                'label': efilter1.name,
                'help': '',
                'group': 'Test Contact',
            },
            find_efilter_dict(efilter1),
        )
        self.assertDictEqual(
            {
                'value': efilter2.pk,
                'label': efilter2.name,
                'help': _('Private ({})').format(user),
                'group': 'Test Organisation',
            },
            find_efilter_dict(efilter2),
        )
        self.assertFalse([c for c in choices if c['value'] == efilter3.id])

    def test_only(self):
        user = self.get_root_user()

        create_efilter = partial(
            EntityFilter.objects.create, entity_type=FakeContact, is_custom=True,
        )
        efilter1 = create_efilter(id='test-filter01', name='Filter 01')
        create_efilter(id='test-filter02', name='Filter 02')
        efilter3 = create_efilter(id='test-filter03', name='Filter 03')

        enum = enumerators.EntityFilterEnumerator(FakeReport._meta.get_field('efilter'))
        self.assertListEqual(
            [{
                'value': efilter1.pk,
                'label': efilter1.name,
                'group': str(efilter1.entity_type),
                'help': '',
            }],
            enum.choices(user, only=['test-filter01']),
        )
        self.assertListEqual(
            [
                {
                    'value': efilter1.pk,
                    'label': efilter1.name,
                    'group': str(efilter1.entity_type),
                    'help': '',
                }, {
                    'value': efilter3.pk,
                    'label': efilter3.name,
                    'group': str(efilter3.entity_type),
                    'help': '',
                },
            ],
            enum.choices(user, only=['test-filter01', 'test-filter03']),
        )

    def test_limit(self):
        user = self.get_root_user()

        create_efilter = EntityFilter.objects.create
        create_efilter(
            id='test-filter01',
            name='Filter 01',
            entity_type=FakeContact,
            is_custom=True,
        )
        create_efilter(
            id='test-filter02',
            name='Filter 02',
            entity_type=FakeOrganisation,
            is_custom=True, user=user, is_private=True,
        )
        create_efilter(
            id='test-filter03',
            name='Filter 01',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,  # <==
        )

        enum = enumerators.EntityFilterEnumerator(FakeReport._meta.get_field('efilter'))
        all_choices = enum.choices(user)
        self.assertListEqual(all_choices[:2], enum.choices(user, limit=2))
        self.assertListEqual(all_choices, enum.choices(user, limit=100))

    def test_term(self):
        user = self.get_root_user()

        create_efilter = EntityFilter.objects.create
        create_efilter(
            id='test-filter01',
            name='Filter 01',
            entity_type=FakeContact,
            is_custom=True,
        )
        create_efilter(
            id='test-filter02',
            name='Filter 02',
            entity_type=FakeContact,
            is_custom=True, user=user, is_private=True,
        )
        create_efilter(
            id='test-filter03',
            name='Filter 03',
            entity_type=FakeContact,
            is_custom=True,
        )

        enum = enumerators.EntityFilterEnumerator(FakeReport._meta.get_field('efilter'))
        self.assertListEqual(
            ['Filter 01', 'Filter 02', 'Filter 03'],
            [c['label'] for c in enum.choices(user, term='Filter')],
        )
        self.assertListEqual(
            ['Filter 03'],
            [c['label'] for c in enum.choices(user, term='03')],
        )


class CTypeForeignKeyEnumeratorTestCase(CremeTestCase):
    def test_no_allowed_models_attr(self):
        user = self.get_root_user()
        enum = enumerators.CTypeForeignKeyEnumerator(
            ForeignKey(  # <===
                ContentType, on_delete=models.CASCADE, verbose_name='Type of resource',
            )
        )

        with self.assertLogs(level='CRITICAL') as logs_manager:
            choices = enum.choices(user)

        self.assertListEqual(
            [{'value': 0, 'label': _('Error (please contact your administrator)')}],
            choices,
        )
        self.assertIn(
            'This enumerator is made to be used with CTypeForeignKey.',
            logs_manager.output[0],
        )

        # To_python
        get_ct = ContentType.objects.get_for_model
        contact_ct = get_ct(FakeContact)
        orga_ct    = get_ct(FakeOrganisation)
        self.assertListEqual(
            [], enum.to_python(user, values=[contact_ct.pk]),
        )
        self.assertListEqual(
            [], enum.to_python(user, values=[contact_ct.pk, orga_ct.pk]),
        )

    def test_empty_allowed_models(self):
        user = self.get_root_user()
        enum = enumerators.CTypeForeignKeyEnumerator(CTypeForeignKey(
            verbose_name='Type of resource',
            # allowed_models=_registered_models,  # <===
        ))

        with self.assertLogs(level='CRITICAL') as logs_manager:
            choices = enum.choices(user)

        self.assertListEqual(
            [{'value': 0, 'label': _('Error (please contact your administrator)')}],
            choices,
        )
        self.assertIn(
            'seems to be a CTypeForeignKey without narrowed models',
            logs_manager.output[0],
        )

        # To_python
        get_ct = ContentType.objects.get_for_model
        self.assertListEqual(
            [],
            enum.to_python(
                user,
                values=[get_ct(FakeContact).pk, get_ct(FakeOrganisation).pk],
            ),
        )

    def test_allowed_models__list(self):
        user = self.get_root_user()
        enum = enumerators.CTypeForeignKeyEnumerator(CTypeForeignKey(
            verbose_name='Type of the resource',
            allowed_models=[FakeContact, FakeOrganisation, FakeImage],
        ))

        get_ct = ContentType.objects.get_for_model
        contact_ct = get_ct(FakeContact)
        orga_ct    = get_ct(FakeOrganisation)

        contact_choice = {'label': 'Test Contact',      'value': contact_ct.pk}
        img_choice     = {'label': 'Test Image',        'value': get_ct(FakeImage).pk}
        orga_choice    = {'label': 'Test Organisation', 'value': orga_ct.pk}

        self.assertListEqual(
            [contact_choice, img_choice, orga_choice], enum.choices(user),
        )

        # Term
        self.assertListEqual([orga_choice], enum.choices(user, term='Orga'))
        self.assertListEqual([contact_choice], enum.choices(user, term='conta'))

        # Only
        self.assertListEqual(
            [contact_choice, orga_choice],
            enum.choices(user, only=[contact_ct.pk, orga_ct.pk]),
        )
        with self.assertLogs(level='WARNING'):
            self.assertListEqual(
                [], enum.choices(user, only=[contact_ct.pk, 'not_int']),
            )

        # Limit
        self.assertListEqual(
            [contact_choice, img_choice],  # orga_choice
            enum.choices(user, limit=2),
        )

        # To_python
        self.assertListEqual(
            [contact_ct], enum.to_python(user, values=[contact_ct.pk]),
        )
        self.assertListEqual(
            [contact_ct],
            enum.to_python(user, values=[get_ct(FakeReport).id, contact_ct.pk]),
        )

    def test_allowed_models__callable(self):
        def allowed_models_func():
            return [FakeContact, FakeOrganisation]

        enum = enumerators.CTypeForeignKeyEnumerator(CTypeForeignKey(
            verbose_name='Type of the resource',
            allowed_models=allowed_models_func,
        ))
        get_ct = ContentType.objects.get_for_model
        self.assertListEqual(
            [
                {'label': 'Test Contact',      'value': get_ct(FakeContact).pk},
                {'label': 'Test Organisation', 'value': get_ct(FakeOrganisation).pk},
            ],
            enum.choices(self.get_root_user()),
        )

    def test_allowed_models__entities(self):
        enum = enumerators.CTypeForeignKeyEnumerator(EntityCTypeForeignKey(
            verbose_name='Type of the resource',
        ))

        choices = enum.choices(self.get_root_user())
        get_ct = ContentType.objects.get_for_model
        self.assertIn(
            {'label': 'Test Contact', 'value': get_ct(FakeContact).pk},
            choices,
        )
        self.assertIn(
            {'label': 'Test Organisation', 'value': get_ct(FakeOrganisation).pk},
            choices,
        )

    # def test_entity_ctypefk_enumerator(self):  # DEPRECATED
    #     user = self.user
    #     with self.assertWarns(DeprecationWarning):
    #         enum = enumerators.EntityCTypeForeignKeyEnumerator(
    #           FakeReport._meta.get_field('ctype'))
    #     all_choices = ctype_choices(entity_ctypes())
    #
    #     get_ct = ContentType.objects.get_for_model
    #     contact_ct = get_ct(FakeContact)
    #     orga_ct    = get_ct(FakeOrganisation)
    #
    #     self.assertListEqual(
    #         [{'label': label, 'value': ct_id} for ct_id, label in all_choices],
    #         enum.choices(user),
    #     )
    #     self.assertListEqual(
    #         [{'label': 'Test Contact', 'value': contact_ct.pk}],
    #         enum.choices(user, term='test contact'),
    #     )
    #     self.assertListEqual(
    #         [{'label': label, 'value': ct_id} for ct_id, label in all_choices[:2]],
    #         enum.choices(user, limit=2),
    #     )
    #     self.assertListEqual(
    #         [
    #             {'label': 'Test Contact', 'value': contact_ct.pk},
    #             {'label': 'Test Organisation', 'value': orga_ct.pk},
    #         ],
    #         enum.choices(user, only=[contact_ct.pk, orga_ct.pk]),
    #     )
    #
    #     # To_python
    #     self.assertListEqual(
    #         [contact_ct], enum.to_python(user, values=[contact_ct.pk]),
    #     )
