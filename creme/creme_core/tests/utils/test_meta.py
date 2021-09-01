# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.utils import translation
from django.utils.translation import gettext as _

from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    FakeActivity,
    FakeContact,
    FakeEmailCampaign,
    FakeImage,
    FakeOrganisation,
    Language,
)
from creme.creme_core.utils import meta

from ..base import CremeTestCase


class MiscTestCase(CremeTestCase):
    def test_is_date_field(self):
        entity = CremeEntity()
        get_field = entity._meta.get_field
        self.assertTrue(meta.is_date_field(get_field('created')))
        self.assertFalse(meta.is_date_field(get_field('user')))

    def test_orderedfield_asc(self):
        ofield1 = meta.OrderedField('name')
        self.assertEqual('name', str(ofield1))
        self.assertEqual('name', ofield1.field_name)
        self.assertTrue(ofield1.order.asc)

        ofield2 = ofield1.reversed()
        self.assertIsInstance(ofield2, meta.OrderedField)
        self.assertIsNot(ofield1, ofield2)
        self.assertEqual('-name', str(ofield2))
        self.assertEqual('name', ofield2.field_name)
        self.assertTrue(ofield2.order.desc)

    def test_orderedfield_desc(self):
        ofield1 = meta.OrderedField('-date')
        self.assertEqual('-date', str(ofield1))
        self.assertEqual('date', ofield1.field_name)
        self.assertTrue(ofield1.order.desc)

        ofield2 = ofield1.reversed()
        self.assertEqual('date', str(ofield2))
        self.assertTrue(ofield2.order.asc)


class FieldInfoTestCase(CremeTestCase):
    def test_field_info01(self):
        "Simple field"
        fi = meta.FieldInfo(FakeContact, 'first_name')

        self.assertEqual(FakeContact, fi.model)
        self.assertEqual(1, len(fi))
        self.assertIs(True, bool(fi))

        with self.assertNoException():
            base_field = fi[0]

        self.assertEqual(FakeContact._meta.get_field('first_name'), base_field)

        self.assertEqual(
            FakeOrganisation._meta.get_field('name'),
            meta.FieldInfo(FakeOrganisation, 'name')[0],
        )

        # FK
        self.assertEqual(
            FakeContact._meta.get_field('image'),
            meta.FieldInfo(FakeContact, 'image')[0],
        )

    def test_field_info02(self):
        "depth > 1"
        fi = meta.FieldInfo(FakeContact, 'image__name')

        self.assertEqual(2, len(fi))
        self.assertEqual(FakeContact._meta.get_field('image'), fi[0])
        self.assertEqual(FakeImage._meta.get_field('name'), fi[1])

        self.assertEqual(f'{_("Photograph")} - {_("Name")}', fi.verbose_name)

        with self.assertNoException():
            fi_as_list = [*meta.FieldInfo(FakeContact, 'image__user__username')]

        self.assertListEqual(
            [
                FakeContact._meta.get_field('image'),
                FakeImage._meta.get_field('user'),
                get_user_model()._meta.get_field('username'),
            ],
            fi_as_list
        )

    def test_field_info03(self):
        "Invalid fields."
        with self.assertRaises(FieldDoesNotExist):
            meta.FieldInfo(FakeContact, 'invalid')

        with self.assertRaises(FieldDoesNotExist):
            meta.FieldInfo(FakeContact, 'image__invalid')

        with self.assertRaises(FieldDoesNotExist):
            meta.FieldInfo(FakeContact, 'invalid__invalidtoo')

    def test_field_info_slice01(self):
        "Start"
        fi = meta.FieldInfo(FakeContact, 'image__user__username')

        with self.assertNoException():
            sub_fi = fi[1:]  # Image.user__username

        self.assertIsInstance(sub_fi, meta.FieldInfo)
        self.assertEqual(FakeImage, sub_fi.model)
        self.assertEqual(2, len(sub_fi))
        self.assertEqual(FakeImage._meta.get_field('user'), sub_fi[0])
        self.assertEqual(get_user_model()._meta.get_field('username'), sub_fi[1])

        empty_sub_fi = fi[3:]
        self.assertEqual(FakeContact, empty_sub_fi.model)
        self.assertEqual(0, len(empty_sub_fi))
        self.assertIs(False, bool(empty_sub_fi))

    def test_field_info_slice02(self):
        "Stop (no start)."
        fi = meta.FieldInfo(FakeContact, 'image__user__username')

        with self.assertNoException():
            sub_fi = fi[:2]  # Contact.image__user__username

        self.assertIsInstance(sub_fi, meta.FieldInfo)
        self.assertEqual(FakeContact, sub_fi.model)
        self.assertEqual(2, len(sub_fi))
        self.assertEqual(FakeContact._meta.get_field('image'), sub_fi[0])
        self.assertEqual(FakeImage._meta.get_field('user'), sub_fi[1])

    def test_field_info_slice03(self):
        "Negative start."
        fi = meta.FieldInfo(FakeContact, 'image__user__username')

        with self.assertNoException():
            sub_fi = fi[-1:]  # User.username

        User = get_user_model()
        self.assertEqual(User, sub_fi.model)
        self.assertEqual(1, len(sub_fi))
        self.assertEqual(User._meta.get_field('username'), sub_fi[0])

    def test_field_info_slice04(self):
        "'very' negative start."
        fi = meta.FieldInfo(FakeContact, 'image__user__username')

        with self.assertNoException():
            sub_fi = fi[-4:]  # No change (Contact.image__user__username)

        self.assertEqual(FakeContact, sub_fi.model)
        self.assertEqual(3, len(sub_fi))
        self.assertEqual(FakeContact._meta.get_field('image'), sub_fi[0])
        self.assertEqual(FakeImage._meta.get_field('user'), sub_fi[1])
        self.assertEqual(get_user_model()._meta.get_field('username'), sub_fi[2])

    def test_field_info_slice05(self):
        "Big start"
        fi = meta.FieldInfo(FakeContact, 'image__user')

        with self.assertNoException():
            sub_fi = fi[5:]  # Empty

        self.assertEqual(FakeContact, sub_fi.model)
        self.assertFalse(sub_fi)

    def test_field_info_slice06(self):
        "Step is forbidden"
        fi = meta.FieldInfo(FakeContact, 'image__user')

        with self.assertRaises(ValueError):
            _ = fi[::0]

        with self.assertRaises(ValueError):
            _ = fi[::2]

    def test_field_info_get_value01(self):
        FieldInfo = meta.FieldInfo

        user = get_user_model().objects.create(username='alphonse')
        al = FakeContact.objects.create(user=user, first_name='Alphonse', last_name='Elric')

        self.assertEqual(
            al.first_name,
            FieldInfo(FakeContact, 'first_name').value_from(al),
        )
        self.assertEqual(user, FieldInfo(FakeContact, 'user').value_from(al))
        self.assertEqual(
            user.username,
            FieldInfo(FakeContact, 'user__username').value_from(al),
        )

        # Other model
        ptype = CremePropertyType.objects.create(text='Is the hero', is_custom=True)
        prop = CremeProperty(type=ptype, creme_entity=al)
        self.assertEqual(
            ptype.text,
            FieldInfo(CremeProperty, 'type__text').value_from(prop)
        )
        self.assertEqual(
            al.entity_type.model,
            FieldInfo(CremeProperty, 'creme_entity__entity_type__model').value_from(prop),
        )

        with self.assertRaises(ValueError):
            FieldInfo(CremeProperty, 'type__text').value_from(al)  # 'al' is not a CremeProperty

        self.assertIsNone(FieldInfo(FakeContact, 'sector').value_from(al))
        self.assertIsNone(FieldInfo(FakeContact, 'sector__title').value_from(al))

    def test_field_info_get_value02(self):
        "ManyToManyField."
        FieldInfo = meta.FieldInfo

        user = get_user_model().objects.create(username='alphonse')
        al = FakeContact.objects.create(user=user, first_name='Alphonse', last_name='Elric')

        self.assertEqual([], FieldInfo(FakeContact, 'languages').value_from(al))
        # self.assertEqual([], FieldInfo(FakeContact, 'languages__code').value_from(al))
        self.assertEqual([], FieldInfo(FakeContact, 'languages__name').value_from(al))

        # ----
        create_language = Language.objects.create
        l1 = create_language(name='English')  # code='EN'
        create_language(name='French')  # code='FRA'
        l3 = create_language(name='Japanese')  # code='JP'

        al.languages.set([l1, l3])
        self.assertListEqual(
            [l1, l3],
            FieldInfo(FakeContact, 'languages').value_from(al),
        )
        self.assertListEqual(
            [l1.name, l3.name],
            FieldInfo(FakeContact, 'languages__name').value_from(al),
        )

    # TODO: test mtom1__mtom2


class ModelFieldEnumeratorTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._lang = translation.get_language()
        cls._translation_deactivated = False

    def tearDown(self):
        super().tearDown()

        if self._translation_deactivated:
            translation.activate(self._lang)
            self._translation_deactivated = False

    def _deactivate_translation(self):  # TODO: decorator ?? in CremeTestCase ?
        translation.deactivate_all()
        self._translation_deactivated = True

    def test_field_enumerator01(self):
        self._deactivate_translation()

        expected = [
            ('created',                    _('Creation date')),
            ('description',                _('Description')),
            ('header_filter_search_field', 'header filter search field'),
            ('id',                         'ID'),
            ('is_deleted',                 'is deleted'),
            ('modified',                   _('Last modification')),
            ('uuid',                       'uuid'),
        ]
        enum1 = meta.ModelFieldEnumerator(CremeEntity)
        self.assertEqual(CremeEntity, enum1.model)

        choices = enum1.choices()
        self.assertEqual(expected, choices, choices)

        # choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=True).choices()
        choices = meta.ModelFieldEnumerator(CremeEntity, only_leaves=True).choices()
        self.assertEqual(expected, choices, choices)

        # choices = meta.ModelFieldEnumerator(CremeEntity, only_leafs=False).choices()
        choices = meta.ModelFieldEnumerator(CremeEntity, only_leaves=False).choices()
        self.assertListEqual(
            [
                ('created',                    _('Creation date')),
                ('description',                _('Description')),
                ('entity_type',                'entity type'),
                ('header_filter_search_field', 'header filter search field'),
                ('id',                         'ID'),
                ('is_deleted',                 'is deleted'),
                ('modified',                   _('Last modification')),
                ('user',                       _('Owner user')),
                ('sandbox',                    'sandbox'),
                ('uuid',                       'uuid'),
            ],
            choices, choices,
        )

    def test_field_enumerator02(self):
        "Filter, exclude (simple)."
        self._deactivate_translation()

        expected = [
            ('created',     _('Creation date')),
            ('description', _('Description')),
            ('modified',    _('Last modification')),
        ]
        choices = meta.ModelFieldEnumerator(CremeEntity).filter(viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(CremeEntity).exclude(viewable=False).choices()
        self.assertEqual(expected, choices, choices)

        expected = [
            ('created',     _('Creation date')),
            ('description', _('Description')),
            ('modified',    _('Last modification')),
            ('user',        _('Owner user')),
        ]
        choices = meta.ModelFieldEnumerator(
            # CremeEntity, only_leafs=False,
            CremeEntity, only_leaves=False,
        ).filter(viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(
            # CremeEntity, only_leafs=False,
            CremeEntity, only_leaves=False,
        ).exclude(viewable=False).choices()
        self.assertEqual(expected, choices, choices)

    def test_field_enumerator03(self):
        "depth = 1."
        self._deactivate_translation()

        fs = partial('[{user}] - {field}'.format, user=_('Owner user'))
        expected = [
            ('created',     _('Creation date')),
            ('description', _('Description')),
            ('modified',    _('Last modification')),

            ('user__email',     fs(field=_('Email address'))),
            ('user__last_name', fs(field=_('Last name'))),
            ('user__username',  fs(field=_('Username'))),
        ]
        self.assertListEqual(
            expected,
            # meta.ModelFieldEnumerator(CremeEntity, deep=1)
            meta.ModelFieldEnumerator(CremeEntity, depth=1)
                .filter(viewable=True).choices()
        )
        self.assertListEqual(
            expected,
            # meta.ModelFieldEnumerator(CremeEntity, deep=1, only_leafs=True)
            meta.ModelFieldEnumerator(CremeEntity, depth=1, only_leaves=True)
                .filter(viewable=True).choices()
        )
        self.assertListEqual(
            [
                ('created',     _('Creation date')),
                ('description', _('Description')),
                ('modified',    _('Last modification')),
                ('user',        _('Owner user')),  # <===

                ('user__email',     fs(field=_('Email address'))),
                ('user__last_name', fs(field=_('Last name'))),
                ('user__username',  fs(field=_('Username'))),
            ],
            # meta.ModelFieldEnumerator(CremeEntity, deep=1, only_leafs=False)
            meta.ModelFieldEnumerator(CremeEntity, depth=1, only_leaves=False)
                .filter(viewable=True).choices()
        )

    def test_field_enumerator04(self):
        "Filter with function, exclude."
        self._deactivate_translation()

        self.assertListEqual(
            [('modified', _('Last modification'))],
            # meta.ModelFieldEnumerator(CremeEntity, deep=1)
            #     .filter(lambda f, depth: f.name.endswith('ied'), viewable=True)
            meta.ModelFieldEnumerator(CremeEntity, depth=1)
                .filter(lambda model, field, depth: field.name.endswith('ied'), viewable=True)
                .choices(),
        )
        self.assertListEqual(
            [('description', _('Description'))],
            # meta.ModelFieldEnumerator(CremeEntity, deep=0)
            #     .exclude(lambda f, depth: f.name.endswith('ed'), viewable=False)
            meta.ModelFieldEnumerator(CremeEntity, depth=0)
                .exclude(lambda model, field, depth: field.name.endswith('ed'), viewable=False)
                .choices(),
        )

    def test_field_enumerator05(self):
        "Other ContentType."
        self._deactivate_translation()

        expected = [
            ('created',     _('Creation date')),
            ('description', _('Description')),
            ('modified',    _('Last modification')),
            ('name',        _('Name of the campaign')),
        ]
        choices = meta.ModelFieldEnumerator(FakeEmailCampaign).filter(viewable=True).choices()
        self.assertEqual(expected, choices, choices)

        choices = meta.ModelFieldEnumerator(
            # FakeEmailCampaign, only_leafs=False
            FakeEmailCampaign, only_leaves=False,
        ).filter(
            # (lambda f, depth: f.get_internal_type() != 'ForeignKey'),
            (lambda model, field, depth: field.get_internal_type() != 'ForeignKey'),
            viewable=True,
        ).choices()
        expected.append(('mailing_lists', _('Related mailing lists')))
        self.assertEqual(expected, choices, choices)

    def test_field_enumerator06(self):
        "Filter/exclude : multiple conditions + field true attributes."
        self._deactivate_translation()

        expected = [
            ('birthday',     _('Birthday')),
            ('civility',     _('Civility')),
            ('description',  _('Description')),
            ('email',        _('Email address')),
            ('first_name',   _('First name')),
            ('is_a_nerd',    _('Is a Nerd')),
            ('last_name',    _('Last name')),
            ('sector',       _('Line of business')),
            ('loves_comics', _('Loves comics')),
            ('mobile',       _('Mobile')),
            ('user',         _('Owner user')),
            ('phone',        _('Phone number')),
            ('image',        _('Photograph')),
            ('position',     _('Position')),
            ('languages',    _('Spoken language(s)')),
            ('url_site',     _('Web Site')),
        ]

        enum1 = meta.ModelFieldEnumerator(
            # FakeContact, only_leafs=False,
            FakeContact, only_leaves=False,
        ).filter(editable=True, viewable=True)
        self.assertEqual(FakeContact, enum1.model)

        choices1 = enum1.choices()
        self.assertEqual(expected, choices1, choices1)

        choices2 = meta.ModelFieldEnumerator(
            # FakeContact, only_leafs=False,
            FakeContact, only_leaves=False,
        ).exclude(editable=False, viewable=False).choices()
        self.assertEqual(expected, choices2, choices2)

    def test_field_enumerator07(self):
        "Ordering of FKs."
        self._deactivate_translation()

        choices = meta.ModelFieldEnumerator(
            # FakeActivity, deep=1, only_leafs=False,
            FakeActivity, depth=1, only_leaves=False,
        ).filter(viewable=True).choices()
        fs = '[{}] - {}'.format
        type_lbl = _('Activity type')
        user_lbl = _('Owner user')
        self.assertListEqual(
            [
                ('type',            type_lbl),
                ('created',         _('Creation date')),
                ('description',     _('Description')),
                ('end',             _('End')),
                ('modified',        _('Last modification')),
                ('minutes',         _('Minutes')),
                ('user',            user_lbl),
                ('place',           _('Place')),
                ('start',           _('Start')),
                ('title',           _('Title')),

                ('type__name',      fs(type_lbl, _('Name'))),

                ('user__email',     fs(user_lbl, _('Email address'))),
                ('user__last_name', fs(user_lbl, _('Last name'))),
                ('user__username',  fs(user_lbl, _('Username'))),
            ],
            choices, choices,
        )

    def test_field_enumerator08(self):
        "'depth' argument."
        self._deactivate_translation()

        choices = meta.ModelFieldEnumerator(
            # FakeActivity, deep=1, only_leafs=False,
            FakeActivity, depth=1, only_leaves=False,
        ).filter(
            # (lambda f, depth: not depth or f.name == 'name'),
            (lambda model, field, depth: not depth or field.name == 'name'),
            viewable=True,
        ).choices()

        type_lbl = _('Activity type')
        self.assertListEqual(
            [
                ('type',        type_lbl),
                ('created',     _('Creation date')),
                ('description', _('Description')),
                ('end',         _('End')),
                ('modified',    _('Last modification')),
                ('minutes',     _('Minutes')),
                ('user',        _('Owner user')),
                ('place',       _('Place')),
                ('start',       _('Start')),
                ('title',       _('Title')),

                ('type__name', f'[{type_lbl}] - {_("Name")}'),
            ],
            choices, choices,
        )

    def test_field_enumerator09(self):
        "Translation activated."
        choices = {
            # *meta.ModelFieldEnumerator(FakeActivity, deep=1, only_leafs=False)
            *meta.ModelFieldEnumerator(FakeActivity, depth=1, only_leaves=False)
                 .filter(viewable=True)
                 .choices(),
        }
        fs = '[{}] - {}'.format
        type_lbl = _('Activity type')
        user_lbl = _('Owner user')
        self.assertSetEqual(
            {
                ('type',        type_lbl),
                ('created',     _('Creation date')),
                ('description', _('Description')),
                ('end',         _('End')),
                ('modified',    _('Last modification')),
                ('minutes',     _('Minutes')),
                ('user',        user_lbl),
                ('start',       _('Start')),
                ('title',       _('Title')),
                ('place',       _('Place')),

                ('type__name', fs(type_lbl, _('Name'))),

                ('user__email',     fs(user_lbl, _('Email address'))),
                ('user__last_name', fs(user_lbl, _('Last name'))),
                ('user__username',  fs(user_lbl, _('Username'))),
            },
            choices, choices,
        )


class OrderTestCase(CremeTestCase):
    def test_asc(self):
        self.assertIs(meta.Order().asc,      True)
        self.assertIs(meta.Order(True).asc,  True)
        self.assertIs(meta.Order(False).asc, False)

    def test_desc(self):
        self.assertIs(meta.Order().desc,      False)
        self.assertIs(meta.Order(False).desc, True)

    def test_str(self):
        self.assertEqual('ASC', str(meta.Order()))
        self.assertEqual('DESC', str(meta.Order(False)))

    def test_prefix(self):
        self.assertEqual('', meta.Order().prefix)
        self.assertEqual('-', meta.Order(False).prefix)

    def test_from_string01(self):
        order1 = meta.Order.from_string('ASC')
        self.assertIsInstance(order1, meta.Order)
        self.assertEqual('ASC', str(order1))

        order2 = meta.Order.from_string('DESC')
        self.assertEqual('DESC', str(order2))

    def test_from_string02(self):
        from_string = meta.Order.from_string

        with self.assertRaises(ValueError):
            from_string('INVALID')

        with self.assertRaises(ValueError):
            from_string('')

        with self.assertRaises(ValueError):
            from_string('', required=True)

        with self.assertRaises(ValueError):
            from_string(None)

    def test_from_string_not_required(self):
        order1 = meta.Order.from_string('', required=False)
        self.assertIsInstance(order1, meta.Order)
        self.assertEqual('ASC', str(order1))

        order2 = meta.Order.from_string(None, required=False)
        self.assertEqual('ASC', str(order2))

    def test_reverse(self):
        order1 = meta.Order(True)
        order1.reverse()
        self.assertFalse(order1.asc)

        order2 = meta.Order(False)
        order2.reverse()
        self.assertTrue(order2.asc)

    def test_reversed(self):
        order1 = meta.Order(True)
        order2 = order1.reversed()
        self.assertIsInstance(order2, meta.Order)
        self.assertIsNot(order1, order2)
        self.assertTrue(order1.asc)
        self.assertFalse(order2.asc)

        self.assertTrue(meta.Order(False).reversed().asc)

    # TODO
    # def test_equal(self, other):
    #     pass
