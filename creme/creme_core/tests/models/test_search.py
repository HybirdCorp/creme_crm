from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellRegularField,
)
from creme.creme_core.models import (
    CustomField,
    FakeContact,
    FakeOrganisation,
    FieldsConfig,
    SearchConfigItem,
)

from ..base import CremeTestCase


class SearchConfigItemManagerTestCase(CremeTestCase):
    def test_create_if_needed(self):
        count = SearchConfigItem.objects.count()
        ct = ContentType.objects.get_for_model(FakeContact)
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ct))

        SearchConfigItem.objects.create_if_needed(
            FakeContact, ['first_name', 'last_name'],
        )
        self.assertEqual(count + 1, SearchConfigItem.objects.count())

        sc_item = self.get_alone_element(SearchConfigItem.objects.filter(content_type=ct))
        self.assertEqual(FakeContact, sc_item.content_type.model_class())
        self.assertIsNone(sc_item.role)
        self.assertIs(sc_item.superuser, False)
        self.assertIs(sc_item.all_fields, False)
        self.assertIs(sc_item.disabled, False)

        cells = [*sc_item.cells]
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, 'first_name'),
                EntityCellRegularField.build(FakeContact, 'last_name'),
            ],
            cells,
        )
        self.assertListEqual(cells, [*sc_item.refined_cells])

        self.assertEqual(
            _('Default search configuration for «{model}»').format(model='Test Contact'),
            str(sc_item),
        )

        # ---
        SearchConfigItem.objects.create_if_needed(FakeContact, ['first_name', 'last_name'])
        self.assertEqual(count + 1, SearchConfigItem.objects.count())

    def test_create_if_needed__role(self):
        count = SearchConfigItem.objects.count()

        role = self.get_regular_role()
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

    def test_create_if_needed__super_user(self):
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

    def test_create_if_needed__invalid_field(self):
        "Invalid fields."
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeContact, ['invalid_field', 'first_name'],
        )
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, 'first_name')],
            [*sc_item.cells],
        )

    def test_create_if_needed__invalid_subfield(self):
        "Invalid fields: no subfield."
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeContact, ['last_name__invalid', 'first_name'],
        )
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, 'first_name')],
            [*sc_item.cells],
        )

    def test_create_if_needed__disabled(self):
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeOrganisation, [], disabled=True,
        )
        self.assertTrue(sc_item.disabled)
        self.assertFalse([*sc_item.cells])

    def test_iter_for_models__no_model(self):
        user = self.get_root_user()

        self.assertListEqual([], [*SearchConfigItem.objects.iter_for_models([], user)])

    def test_iter_for_models__1_model__no_config(self):
        "One model, no config in BD."
        user = self.get_root_user()
        self.assertFalse(
            [*SearchConfigItem.objects.iter_for_models([FakeContact], user)],
        )

    def test_iter_for_models__1_model__1_config(self):
        "One model, 1 config in DB."
        user = self.get_root_user()

        created_item = SearchConfigItem.objects.create_if_needed(
            FakeContact, ['first_name', 'last_name'],
        )

        retrieved_item = self.get_alone_element(
            SearchConfigItem.objects.iter_for_models([FakeContact], user)
        )
        self.assertEqual(created_item, retrieved_item)

    def test_iter_for_models__1_model__2_configs(self):
        "One model, 2 configs in DB."
        create_role = self.create_role
        role1 = create_role(name='Basic')
        role2 = create_role(name='CEO')
        role3 = create_role(name='Office lady')

        user = self.create_user(role=role1)

        create_sci = SearchConfigItem.objects.create_if_needed
        create_sci(FakeContact, ['description'], role='superuser')
        create_sci(FakeContact, ['first_name', 'last_name'])
        create_sci(FakeContact, ['first_name'], role=role2)
        created_item = create_sci(FakeContact, ['last_name'], role=role1)  # <===
        create_sci(FakeContact, ['first_name', 'description'], role=role3)

        retrieved_item = self.get_alone_element(
            SearchConfigItem.objects.iter_for_models([FakeContact], user)
        )
        self.assertEqual(created_item, retrieved_item)

    def test_iter_for_models__1_model__2_configs_other(self):
        "One model, 2 configs in DB (other order)."
        role = self.create_role(name='Test')
        user = self.create_user(role=role)

        create_sci = SearchConfigItem.objects.create_if_needed
        sc_item = create_sci(FakeContact, ['last_name'], role=role)
        create_sci(FakeContact, ['first_name', 'last_name'])
        create_sci(FakeContact, ['description'], role='superuser')

        self.assertEqual(
            sc_item,
            next(SearchConfigItem.objects.iter_for_models([FakeContact], user))
        )

    def test_iter_for_models__superuser(self):
        "One model, 2 configs in DB (super-user)."
        user = self.get_root_user()

        create_role = self.create_role
        role1 = create_role(name='CEO')
        role2 = create_role(name='Office lady')

        create_sci = SearchConfigItem.objects.create_if_needed
        create_sci(FakeContact, ['first_name', 'last_name'])
        create_sci(FakeContact, ['first_name'], role=role1)
        sc_item = create_sci(FakeContact, ['last_name'], role='superuser')  # <==
        create_sci(FakeContact, ['first_name', 'description'], role=role2)

        self.assertEqual(
            sc_item,
            next(SearchConfigItem.objects.iter_for_models([FakeContact], user))
        )

    def test_iter_for_models__superuser__other(self):
        "One model, 2 configs in DB (super-user) (other order)."
        user = self.get_root_user()

        create_sci = SearchConfigItem.objects.create_if_needed
        sc_item = create_sci(FakeContact, ['last_name'], role='superuser')
        create_sci(FakeContact, ['first_name', 'last_name'])

        self.assertEqual(
            sc_item,
            next(SearchConfigItem.objects.iter_for_models([FakeContact], user))
        )

    def test_iter_for_models__2_models(self):
        user = self.get_root_user()

        create_sci = SearchConfigItem.objects.create_if_needed
        create_sci(FakeContact, ['last_name'])
        create_sci(FakeOrganisation, ['name'])

        models = [FakeContact, FakeOrganisation]
        self.assertListEqual(
            models,
            [
                sci.content_type.model_class()
                for sci in SearchConfigItem.objects.iter_for_models(models, user)
            ],
        )


class SearchConfigItemTestCase(CremeTestCase):
    def test_all_fields__true(self):
        sc_item = SearchConfigItem.objects.create_if_needed(FakeOrganisation, [])
        self.assertTrue(sc_item.all_fields)
        self.assertListEqual([], [*sc_item.cells])

        sfields = {cell.value for cell in sc_item.refined_cells}
        self.assertIn('name', sfields)
        self.assertIn('sector__title', sfields)
        self.assertIn('address__city', sfields)
        self.assertNotIn('creation_date', sfields)
        self.assertNotIn('sector', sfields)
        self.assertNotIn('address', sfields)

    def test_all_fields__false(self):
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

    def test_cells_property(self):
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

    def test_cells_property__no_field(self):
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

    def test_cells_property__invalid_fields(self):
        "Invalid fields generate None as cells."
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeOrganisation, ['name', 'phone'],
        )

        sc_item.cells = [None]
        sc_item.save()
        self.assertListEqual([], self.refresh(sc_item).json_cells)

    def test_cells_property__disabled(self):
        "Fields + disabled."
        sc_item = SearchConfigItem.objects.create_if_needed(
            FakeOrganisation, ['name', 'phone'], disabled=True,
        )
        build_cell = partial(EntityCellRegularField.build, FakeOrganisation)
        self.assertListEqual(
            [build_cell('name'), build_cell('phone')],
            [*sc_item.cells],
        )

    def test_cells_property__portable(self):
        sc_item = SearchConfigItem.objects.create_if_needed(FakeContact, ['last_name'])

        cfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=FakeContact,
        )
        sc_item.cells = [
            EntityCellRegularField.build(FakeContact, 'last_name'),
            EntityCellCustomField(customfield=cfield),
        ]
        sc_item.save()

        sc_item = self.refresh(sc_item)
        self.assertListEqual(
            [
                {'type': 'regular_field', 'value': 'last_name'},
                {'type': 'custom_field', 'value': str(cfield.uuid)},
            ],
            sc_item.json_cells,
        )
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, 'last_name'),
                EntityCellCustomField(customfield=cfield),
            ],
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
