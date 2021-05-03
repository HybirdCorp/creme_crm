# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.models import FieldsConfig, SearchConfigItem, UserRole

from ..base import CremeTestCase
from ..fake_models import FakeContact, FakeOrganisation


class SearchConfigTestCase(CremeTestCase):
    # def test_create_if_needed(self):  # DEPRECATED
    #     count = SearchConfigItem.objects.count()
    #     ct = ContentType.objects.get_for_model(FakeContact)
    #     self.assertFalse(SearchConfigItem.objects.filter(content_type=ct))
    #
    #     SearchConfigItem.create_if_needed(FakeContact, ['first_name', 'last_name'])
    #     self.assertEqual(count + 1, SearchConfigItem.objects.count())
    #
    #     sc_items = SearchConfigItem.objects.filter(content_type=ct)
    #     self.assertEqual(1, len(sc_items))
    #
    #     sc_item = sc_items[0]
    #     self.assertEqual(FakeContact, sc_item.content_type.model_class())
    #     self.assertIsNone(sc_item.role)
    #     self.assertIs(sc_item.superuser, False)
    #     self.assertEqual('first_name,last_name', sc_item.field_names)
    #     self.assertIs(sc_item.all_fields, False)
    #     self.assertIs(sc_item.disabled, False)
    #
    #     sfields = sc_item.searchfields
    #     self.assertEqual(2, len(sfields))
    #
    #     fn_field = sfields[0]
    #     self.assertEqual('first_name',     fn_field.name)
    #     self.assertEqual(_('First name'), fn_field.verbose_name)
    #     self.assertEqual(_('First name'), str(fn_field))
    #
    #     ln_field = sfields[1]
    #     self.assertEqual('last_name',     ln_field.name)
    #     self.assertEqual(_('Last name'), ln_field.verbose_name)
    #     self.assertEqual(_('Last name'), str(ln_field))
    #
    #     self.assertEqual(
    #         _('Default search configuration for «{model}»').format(model='Test Contact'),
    #         str(sc_item)
    #     )
    #
    #     SearchConfigItem.create_if_needed(FakeContact, ['first_name', 'last_name'])
    #     self.assertEqual(count + 1, SearchConfigItem.objects.count())

    def test_manager_create_if_needed01(self):
        count = SearchConfigItem.objects.count()
        ct = ContentType.objects.get_for_model(FakeContact)
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ct))

        SearchConfigItem.objects.create_if_needed(
            FakeContact, ['first_name', 'last_name'],
        )
        self.assertEqual(count + 1, SearchConfigItem.objects.count())

        sc_items = SearchConfigItem.objects.filter(content_type=ct)
        self.assertEqual(1, len(sc_items))

        sc_item = sc_items[0]
        self.assertEqual(FakeContact, sc_item.content_type.model_class())
        self.assertIsNone(sc_item.role)
        self.assertIs(sc_item.superuser, False)
        # self.assertEqual('first_name,last_name', sc_item.field_names)
        self.assertIs(sc_item.all_fields, False)
        self.assertIs(sc_item.disabled, False)

        # sfields = sc_item.searchfields
        # self.assertEqual(2, len(sfields))
        #
        # fn_field = sfields[0]
        # self.assertEqual('first_name',    fn_field.name)
        # self.assertEqual(_('First name'), fn_field.verbose_name)
        # self.assertEqual(_('First name'), str(fn_field))
        #
        # ln_field = sfields[1]
        # self.assertEqual('last_name',    ln_field.name)
        # self.assertEqual(_('Last name'), ln_field.verbose_name)
        # self.assertEqual(_('Last name'), str(ln_field))

        cells = [*sc_item.cells]
        self.assertEqual(2, len(cells))

        fn_cell = cells[0]
        self.assertIsInstance(fn_cell, EntityCellRegularField)
        self.assertEqual(FakeContact,     fn_cell.model)
        self.assertEqual('first_name',    fn_cell.value)

        self.assertEqual('last_name',  cells[1].value)

        self.assertListEqual(cells, [*sc_item.refined_cells])

        self.assertEqual(
            _('Default search configuration for «{model}»').format(model='Test Contact'),
            str(sc_item)
        )

        SearchConfigItem.objects.create_if_needed(FakeContact, ['first_name', 'last_name'])
        self.assertEqual(count + 1, SearchConfigItem.objects.count())

    def test_manager_create_if_needed02(self):
        "With a role."
        self.login()
        count = SearchConfigItem.objects.count()

        role = self.role
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeOrganisation, ['name'], role=role,
        )
        self.assertIsInstance(sc_item, SearchConfigItem)

        self.assertEqual(count + 1, SearchConfigItem.objects.count())

        self.assertEqual(FakeOrganisation, sc_item.content_type.model_class())
        self.assertEqual(role, sc_item.role)
        self.assertFalse(sc_item.superuser)

        self.assertEqual(
            _('Search configuration of «{role}» for «{model}»').format(
                role=role,
                model='Test Organisation',
            ),
            str(sc_item),
        )

    def test_manager_create_if_needed03(self):
        "For super users."
        self.login()

        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeOrganisation, ['name'], role='superuser',
        )

        self.assertEqual(FakeOrganisation, sc_item.content_type.model_class())
        self.assertIsNone(sc_item.role)
        self.assertTrue(sc_item.superuser)

        self.assertEqual(
            _('Search configuration of super-users for «{model}»').format(
                model='Test Organisation',
            ),
            str(sc_item),
        )

    def test_manager_create_if_needed04(self):
        "Invalid fields."
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeContact, ['invalid_field', 'first_name'],
        )

        # sfields = sc_item.searchfields
        # self.assertEqual(1, len(sfields))
        # self.assertEqual('first_name', sfields[0].name)
        cells = [*sc_item.cells]
        self.assertEqual(1, len(cells))
        self.assertEqual('first_name', cells[0].value)

    def test_manager_create_if_needed05(self):
        "Invalid fields : no subfield."
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeContact, ['last_name__invalid', 'first_name'],
        )

        # sfields = sc_item.searchfields
        # self.assertEqual(1, len(sfields))
        # self.assertEqual('first_name', sfields[0].name)
        cells = [*sc_item.cells]
        self.assertEqual(1, len(cells))
        self.assertEqual('first_name', cells[0].value)

    def test_manager_create_if_needed06(self):
        "Disabled."
        self.login()

        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeOrganisation, [], disabled=True,
        )
        self.assertTrue(sc_item.disabled)
        # self.assertFalse(sc_item.field_names)
        self.assertFalse([*sc_item.cells])

    def test_allfields01(self):
        "True."
        sc_item = SearchConfigItem.objects.create_if_needed(FakeOrganisation, [])
        self.assertTrue(sc_item.all_fields)
        self.assertListEqual([], [*sc_item.cells])

        # sfields = {sf.name for sf in sc_item.searchfields}
        sfields = {cell.value for cell in sc_item.refined_cells}
        self.assertIn('name', sfields)
        self.assertIn('sector__title', sfields)
        self.assertIn('address__city', sfields)
        self.assertNotIn('creation_date', sfields)
        self.assertNotIn('sector', sfields)
        self.assertNotIn('address', sfields)

    def test_allfields02(self):
        "False."
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeOrganisation, ['name', 'phone'],
        )
        self.assertFalse(sc_item.all_fields)

    # TODO ??
    # def test_searchfields01(self):
    #     "Invalid field are deleted automatically."
    #     sc_item = SearchConfigItem.objects.create_if_needed(
    #         FakeOrganisation, ['name', 'phone'],
    #     )
    #
    #     sc_item.field_names += ',invalid'
    #     sc_item.save()
    #
    #     sc_item = self.refresh(sc_item)  # No cache any more
    #
    #     self.assertEqual(['name', 'phone'], [sf.name for sf in sc_item.searchfields])
    #     self.assertEqual('name,phone', sc_item.field_names)
    #
    # def test_searchfields02(self):
    #     "Invalid field are deleted automatically => if no more valid field, all are used"
    #     sc_item = SearchConfigItem.objects.create_if_needed(
    #         FakeOrganisation, ['name', 'phone'],
    #     )
    #     sc_item.field_names = 'invalid01,invalid02'
    #     sc_item.save()
    #
    #     sc_item = self.refresh(sc_item)  # No cache anymore
    #
    #     sfields = {sf.name for sf in sc_item.searchfields}
    #     self.assertIn('name', sfields)
    #     self.assertIn('capital', sfields)
    #     self.assertNotIn('created', sfields)
    #
    #     self.assertTrue(sc_item.all_fields)
    #     self.assertIsNone(sc_item.field_names)

    # def test_searchfields_setter01(self):
    #     sc_item = SearchConfigItem.objects.create_if_needed(
    #         FakeOrganisation, ['name', 'phone'],
    #     )
    #
    #     sc_item.searchfields = ['capital', 'email', 'invalid']
    #     sc_item.save()
    #
    #     sc_item = self.refresh(sc_item)
    #     self.assertListEqual(['capital', 'email'], [sf.name for sf in sc_item.searchfields])
    #     self.assertFalse(sc_item.all_fields)
    #
    #     sc_item.searchfields = []
    #     self.assertIsNone(sc_item.field_names)
    #     self.assertTrue(sc_item.all_fields)
    def test_cells_property01(self):
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeOrganisation, ['name', 'phone'],
        )

        build_cell = partial(EntityCellRegularField.build, FakeOrganisation)
        cell1 = build_cell('capital')
        cell2 = build_cell('email')
        sc_item.cells = [cell1, cell2, None]
        sc_item.save()

        sc_item = self.refresh(sc_item)
        self.assertListEqual([cell1, cell2], [*sc_item.cells])
        self.assertFalse(sc_item.all_fields)

        sc_item.cells = []
        self.assertListEqual([], sc_item.json_cells)
        self.assertTrue(sc_item.all_fields)

    # def test_searchfields_setter02(self):
    #     "No fields"
    #     sc_item = SearchConfigItem.objects.create_if_needed(
    #         FakeOrganisation, ['name', 'phone'],
    #     )
    #
    #     sc_item.searchfields = []
    #     sc_item.save()
    #     self.assertIsNone(self.refresh(sc_item).field_names)
    #     self.assertTrue(sc_item.all_fields)
    #
    #     sc_item.searchfields = ['name']
    #     self.assertListEqual(['name'], [sf.name for sf in sc_item.searchfields])
    #     self.assertFalse(sc_item.all_fields)
    def test_cells_property02(self):
        "No fields"
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeOrganisation, ['name', 'phone'],
        )

        sc_item.cells = []
        sc_item.save()
        self.assertListEqual([], self.refresh(sc_item).json_cells)
        self.assertTrue(sc_item.all_fields)

        cell = EntityCellRegularField.build(FakeOrganisation, 'name')
        sc_item.cells = [cell]
        self.assertListEqual([cell], [*sc_item.cells])
        self.assertFalse(sc_item.all_fields)

    # def test_searchfields_setter03(self):
    #     "Invalid fields."
    #     sc_item = SearchConfigItem.objects.create_if_needed(
    #         FakeOrganisation, ['name', 'phone'],
    #     )
    #
    #     sc_item.searchfields = ['invalid']
    #     sc_item.save()
    #     self.assertIsNone(self.refresh(sc_item).field_names)
    def test_cells_property03(self):
        "Invalid fields generate None as cells."
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeOrganisation, ['name', 'phone'],
        )

        sc_item.cells = [None]
        sc_item.save()
        self.assertListEqual([], self.refresh(sc_item).json_cells)

    # def test_searchfields_setter04(self):
    #     "Fields + disabled."
    #     sc_item = SearchConfigItem.objects.create_if_needed(
    #         FakeOrganisation, ['name', 'phone'], disabled=True,
    #     )
    #     self.assertListEqual(
    #         ['name', 'phone'], [sf.name for sf in sc_item.searchfields]
    #     )
    def test_cells_property04(self):
        "Fields + disabled."
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeOrganisation, ['name', 'phone'], disabled=True,
        )
        build_cell = partial(EntityCellRegularField.build, FakeOrganisation)
        self.assertListEqual(
            [build_cell('name'), build_cell('phone')],
            [*sc_item.cells],
        )

    def test_refined_cells(self):
        "FieldsConfig."
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('first_name', {FieldsConfig.HIDDEN: True})],
        )

        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeContact, ['first_name', 'last_name'],
        )
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, 'last_name')],
            [*self.refresh(sc_item).refined_cells],
        )

    # def test_get_4_models01(self):  # DEPRECATED
    #     "No model."
    #     user = self.create_user()
    #
    #     configs = SearchConfigItem.get_4_models([], user)
    #     self.assertListEqual([], [*configs])

    # def test_get_4_models02(self):  # DEPRECATED
    #     "One model, 2 configs in DB."
    #     self.login()
    #
    #     create_role = UserRole.objects.create
    #     role2 = create_role(name='CEO')
    #     role3 = create_role(name='Office lady')
    #
    #     create = SearchConfigItem.objects.create_if_needed
    #     create(FakeContact, ['description'], role='superuser')
    #     create(FakeContact, ['first_name', 'last_name'])
    #     create(FakeContact, ['first_name'], role=role2)
    #     sc_item = create(FakeContact, ['last_name'], role=self.role)  # <===
    #     create(FakeContact, ['first_name', 'description'], role=role3)
    #
    #     configs = [*SearchConfigItem.get_4_models([FakeContact], self.other_user)]
    #     self.assertEqual(1, len(configs))
    #     self.assertEqual(sc_item, configs[0])

    def test_manager_get_for_models01(self):
        "No model"
        user = self.create_user()

        self.assertListEqual([], [*SearchConfigItem.objects.iter_for_models([], user)])

    def test_manager_get_for_models02(self):
        "One model, no config in BD."
        user = self.create_user()

        configs = [*SearchConfigItem.objects.iter_for_models([FakeContact], user)]
        self.assertEqual(1, len(configs))

        sc_item = configs[0]
        self.assertIsInstance(sc_item, SearchConfigItem)
        self.assertEqual(FakeContact, sc_item.content_type.model_class())
        self.assertIsNone(sc_item.role)
        self.assertFalse(sc_item.superuser)
        self.assertTrue(sc_item.all_fields)
        self.assertIsNone(sc_item.pk)

    def test_manager_get_for_models03(self):
        "One model, 1 config in DB."
        user = self.create_user()

        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeContact, ['first_name', 'last_name'],
        )

        configs = [*SearchConfigItem.objects.iter_for_models([FakeContact], user)]
        self.assertEqual(1, len(configs))
        self.assertEqual(sc_item, configs[0])

    def test_manager_get_for_models04(self):
        "One model, 2 configs in DB."
        self.login()

        create_role = UserRole.objects.create
        role2 = create_role(name='CEO')
        role3 = create_role(name='Office lady')

        create = SearchConfigItem.objects.create_if_needed
        create(FakeContact, ['description'], role='superuser')
        create(FakeContact, ['first_name', 'last_name'])
        create(FakeContact, ['first_name'], role=role2)
        sc_item = create(FakeContact, ['last_name'], role=self.role)  # <===
        create(FakeContact, ['first_name', 'description'], role=role3)

        configs = [*SearchConfigItem.objects.iter_for_models([FakeContact], self.other_user)]
        self.assertEqual(1, len(configs))
        self.assertEqual(sc_item, configs[0])

    def test_manager_get_for_models05(self):
        "One model, 2 configs in DB (other order)."
        self.login()

        create = SearchConfigItem.objects.create_if_needed
        sc_item = create(FakeContact, ['last_name'], role=self.role)
        create(FakeContact, ['first_name', 'last_name'])
        create(FakeContact, ['description'], role='superuser')

        self.assertEqual(
            sc_item,
            next(SearchConfigItem.objects.iter_for_models([FakeContact], self.other_user))
        )

    def test_manager_get_for_models06(self):
        "One model, 2 configs in DB (super-user)."
        user = self.create_user()

        create_role = UserRole.objects.create
        role2 = create_role(name='CEO')
        role3 = create_role(name='Office lady')

        create = SearchConfigItem.objects.create_if_needed
        create(FakeContact, ['first_name', 'last_name'])
        create(FakeContact, ['first_name'], role=role2)
        sc_item = create(FakeContact, ['last_name'], role='superuser')  # <==
        create(FakeContact, ['first_name', 'description'], role=role3)

        self.assertEqual(
            sc_item,
            next(SearchConfigItem.objects.iter_for_models([FakeContact], user))
        )

    def test_manager_get_for_models07(self):
        "One model, 2 configs in DB (super-user) (other order)."
        user = self.create_user()

        create = SearchConfigItem.objects.create_if_needed
        sc_item = create(FakeContact, ['last_name'], role='superuser')
        create(FakeContact, ['first_name', 'last_name'])

        self.assertEqual(
            sc_item,
            next(SearchConfigItem.objects.iter_for_models([FakeContact], user))
        )

    def test_manager_get_for_models08(self):
        "2 models."
        user = self.create_user()

        configs = [
            *SearchConfigItem.objects
                             .iter_for_models([FakeContact, FakeOrganisation], user)
        ]
        self.assertEqual(2, len(configs))
        self.assertEqual(FakeContact,      configs[0].content_type.model_class())
        self.assertEqual(FakeOrganisation, configs[1].content_type.model_class())
