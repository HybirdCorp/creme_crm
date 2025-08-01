from functools import partial

from django.db.models import CharField, ForeignKey, IntegerField

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.entity_cell import (
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.function_field import FunctionField
from creme.creme_core.core.sorter import (
    AbstractCellSorter,
    CellSorterRegistry,
    EntityForeignKeySorter,
    Order,
    QuerySorter,
    QuerySortInfo,
    RegularFieldSorter,
    VoidSorter,
)
from creme.creme_core.function_fields import PropertiesField
from creme.creme_core.models import (
    CremeEntity,
    FakeActivity,
    FakeCivility,
    FakeContact,
    FakeDocument,
    FakeEmailCampaign,
    FakeInvoice,
    FakeOrganisation,
    FakeSector,
    HistoryLine,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.utils.db import get_indexed_ordering


class QuerySorterTestCase(CremeTestCase):
    def test_order_sql(self):
        def get_sql(queryset):
            return queryset.query.get_compiler('default').as_sql()[0]

        self.assertEqual(('name',), FakeOrganisation._meta.ordering)

        self.assertRegex(
            get_sql(FakeOrganisation.objects.all()),
            r'ORDER BY .creme_core_fakeorganisation.\..name. ASC( NULLS FIRST)?$'
        )

        # Check that order by 'id' does not use cremeentity.id,
        # but fakeorganisation.cremeentity_ptr_id
        self.assertRegex(
            get_sql(FakeOrganisation.objects.order_by('id')),
            r'ORDER BY .creme_core_fakeorganisation.\..cremeentity_ptr_id. ASC( NULLS FIRST)?$'
        )
        self.assertRegex(
            get_sql(FakeOrganisation.objects.order_by('name', 'id')),
            r'ORDER BY '
            r'.creme_core_fakeorganisation.\..name. ASC( NULLS FIRST)?\, '
            r'.creme_core_fakeorganisation.\..cremeentity_ptr_id. ASC( NULLS FIRST)?$'
        )

    def test_pretty(self):
        registry = CellSorterRegistry()
        ps = registry.pretty()
        self.assertIsInstance(ps, str)
        self.assertIn("""CellSorterRegistry:
  [EntityCellRegularField.type_id="regular_field"]:
    RegularFieldSorterRegistry:
      Field types:
        [django.db.models.fields.AutoField]:
          RegularFieldSorter
        [django.db.models.fields.BooleanField]:
          RegularFieldSorter
        [django.db.models.fields.DecimalField]:
          RegularFieldSorter
        [django.db.models.fields.FloatField]:
          RegularFieldSorter
        [django.db.models.fields.IntegerField]:
          RegularFieldSorter
        [django.db.models.fields.CharField]:
          RegularFieldSorter
        [django.db.models.fields.TextField]:
          RegularFieldSorter
        [django.db.models.fields.DateField]:
          RegularFieldSorter
        [django.db.models.fields.TimeField]:
          RegularFieldSorter
        [django.db.models.fields.related.ForeignKey]:
          ForeignKeySorterRegistry:
            Models:
              [creme.creme_core.models.entity.CremeEntity]:
                EntityForeignKeySorter
        [django.db.models.fields.CommaSeparatedIntegerField]:
          VoidSorter
        [creme.creme_core.models.fields.DatePeriodField]:
          VoidSorter
      Fields:
        (empty)
  [EntityCellFunctionField.type_id="function_field"]:
    FunctionFieldSorterRegistry""", ps)

    def test_regularfield_default_oneorder_01(self):
        "Ordering: natural ordering key."
        sorter = QuerySorter(CellSorterRegistry())

        field_name1 = 'name'
        field_name2 = 'email'
        self.assertEqual((field_name1,), FakeOrganisation._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [
            build_cell(name=field_name2),
            build_cell(name=field_name1),  # meta._meta.ordering[0]
        ]

        key = cells[1].key
        sortinfo1 = sorter.get(model=FakeOrganisation, cells=cells, cell_key=key, order=Order())
        self.assertIsInstance(sortinfo1, QuerySortInfo)

        self.assertEqual((field_name1, 'cremeentity_ptr_id'), sortinfo1.field_names)
        self.assertEqual(key,   sortinfo1.main_cell_key)
        self.assertEqual('ASC', str(sortinfo1.main_order))

        # Fast mode -------------------
        sortinfo2 = sorter.get(
            model=FakeOrganisation, cells=cells, cell_key=key,
            order=Order(),
            fast_mode=True,
        )
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), sortinfo2.field_names)

        # DESC -------------------
        sortinfo3 = sorter.get(
            model=FakeOrganisation, cells=cells, cell_key=key, order=Order(False),
        )
        self.assertEqual(('-' + field_name1, '-cremeentity_ptr_id'), sortinfo3.field_names)
        self.assertEqual(key, sortinfo3.main_cell_key)
        self.assertTrue(sortinfo3.main_order.desc)

    def test_regularfield_default_oneorder_02(self):
        "Ordering: add a not natural ordering key."
        sorter = QuerySorter()
        field_name1 = 'name'
        field_name2 = 'email'

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name=field_name2), build_cell(name=field_name1)]

        key = cells[0].key
        sort_info = sorter.get(model=FakeOrganisation, cells=cells, cell_key=key)
        self.assertEqual(
            (field_name2, field_name1, 'cremeentity_ptr_id'),
            sort_info.field_names,
        )
        self.assertEqual(key, sort_info.main_cell_key)
        self.assertTrue(sort_info.main_order.asc)

    def test_regularfield_default_oneorder_03(self):
        "Empty cell key => fallback on natural model ordering."
        sorter = QuerySorter(cell_sorter_registry=CellSorterRegistry())

        field_name1 = 'name'
        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        main_cell = build_cell(name=field_name1)
        cells = [build_cell(name='email'), main_cell]

        sort_info = sorter.get(
            model=FakeOrganisation, cells=cells, cell_key=None, order=None,
        )
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), sort_info.field_names)
        self.assertEqual(main_cell.key, sort_info.main_cell_key)
        self.assertTrue(sort_info.main_order.asc)

    def test_regularfield_default_oneorder_04(self):
        "Invalid cell key => fallback on natural model ordering."
        sorter = QuerySorter()

        field_name1 = 'name'
        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name=field_name1), build_cell(name='email')]

        sort_info = sorter.get(model=FakeOrganisation, cells=cells, cell_key='invalid')
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), sort_info.field_names)
        self.assertEqual(cells[0].key, sort_info.main_cell_key)
        self.assertTrue(sort_info.main_order.asc)

    def test_regularfield_default_oneorder_05(self):
        "Cell is not displayed => fallback on basic ordering."
        sorter = QuerySorter()

        field_name1 = 'name'
        field_name2 = 'phone'

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        unused_cell = EntityCellRegularField.build(model=FakeOrganisation, name='email')
        main_cell = build_cell(name=field_name1)  # NB: meta.ordering[0]
        cells1 = [build_cell(name=field_name2), main_cell]

        sortinfo1 = sorter.get(model=FakeOrganisation, cells=cells1, cell_key=unused_cell.key)
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), sortinfo1.field_names)
        self.assertEqual(main_cell.key, sortinfo1.main_cell_key)
        self.assertTrue(sortinfo1.main_order.asc)

        # Natural ordering not displayed ---------------
        cells2 = [build_cell(name=field_name2), build_cell(name='sector')]

        sortinfo2 = sorter.get(model=FakeOrganisation, cells=cells2, cell_key=unused_cell.key)
        # TODO ? Use index
        self.assertEqual(('cremeentity_ptr_id',), sortinfo2.field_names)
        self.assertIsNone(sortinfo2.main_cell_key)  # TODO: Fallback on first column ?
        self.assertTrue(sortinfo2.main_order.asc)

    def test_regularfield_default_oneorder_06(self):
        "Ordering: add a not natural ordering key (FK to CremeEntity)."
        sorter = QuerySorter()

        field_name1 = 'title'
        field_name2 = 'linked_folder'
        self.assertEqual((field_name1,), FakeDocument._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=FakeDocument)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        key = cells[1].key
        sortinfo = sorter.get(model=FakeDocument, cells=cells, cell_key=key)
        self.assertEqual(
            (
                f'{field_name2}__header_filter_search_field',
                field_name1,
                'cremeentity_ptr_id',
            ),
            sortinfo.field_names,
        )

        self.assertEqual(cells[1].key, sortinfo.main_cell_key)
        self.assertTrue(sortinfo.main_order.asc)

    def test_regularfield_default_oneorder_07(self):
        "Ordering: add a not natural ordering key (FK to CremeModel)."
        self.assertEqual(('order',), FakeSector._meta.ordering)

        sorter = QuerySorter()

        field_name1 = 'name'
        field_name2 = 'sector'
        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        key = cells[1].key
        sort_info = sorter.get(model=FakeOrganisation, cells=cells, cell_key=key)
        self.assertEqual(
            (f'{field_name2}__order', field_name1, 'cremeentity_ptr_id'),
            sort_info.field_names
        )
        self.assertEqual(key,   sort_info.main_cell_key)
        self.assertTrue(sort_info.main_order.asc)

    def test_regularfield_default_oneorder_08(self):
        "Natural ordering field not in cells."
        sorter = QuerySorter()

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name='phone'), build_cell(name='email')]

        key = cells[0].key
        sort_info1 = sorter.get(model=FakeOrganisation, cells=cells, cell_key=key)
        self.assertEqual(('phone', 'cremeentity_ptr_id'), sort_info1.field_names)
        self.assertEqual(key, sort_info1.main_cell_key)
        self.assertTrue(sort_info1.main_order.asc)

        # Initial
        sort_info2 = sorter.get(model=FakeOrganisation, cells=cells, cell_key=None)
        self.assertEqual(('cremeentity_ptr_id',), sort_info2.field_names)

    def test_regularfield_default_twoorders_01(self):
        "meta.ordering: 2 fields."
        sorter = QuerySorter()

        field_name1 = 'first_name'
        field_name2 = 'last_name'
        self.assertEqual((field_name2, field_name1), FakeContact._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        key = cells[0].key
        sort_info1 = sorter.get(model=FakeContact, cells=cells, cell_key=key)
        self.assertEqual(
            (field_name1, field_name2, 'cremeentity_ptr_id'),
            sort_info1.field_names,
        )
        self.assertEqual(key, sort_info1.main_cell_key)
        self.assertTrue(sort_info1.main_order.asc)

        # DESC -----------------------------
        sort_info2 = sorter.get(
            model=FakeContact, cells=cells, cell_key=key, order=Order(False),
        )
        self.assertEqual(
            (f'-{field_name1}', f'-{field_name2}', '-cremeentity_ptr_id'),
            sort_info2.field_names
        )
        self.assertEqual(key, sort_info2.main_cell_key)
        self.assertTrue(sort_info2.main_order.desc)

    def test_regularfield_default_twoorders_02(self):
        "Add not natural ordering."
        sorter = QuerySorter()
        field_name1 = 'first_name'
        field_name2 = 'last_name'
        field_name3 = 'phone'

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [
            build_cell(name=field_name1),
            build_cell(name=field_name2),
            build_cell(name=field_name3),
        ]

        key = cells[2].key
        sort_info1 = sorter.get(model=FakeContact, cells=cells, cell_key=key)
        self.assertEqual(
            (field_name3, field_name2, field_name1, 'cremeentity_ptr_id'),
            sort_info1.field_names,
        )

        # DESC ------------------
        sort_info2 = sorter.get(
            model=FakeContact, cells=cells, cell_key=key, order=Order(False),
        )
        self.assertEqual(
            ('-' + field_name3, field_name2, field_name1, '-cremeentity_ptr_id'),
            sort_info2.field_names,
        )

    def test_regularfield_default_twoorders_03(self):
        "Add invalid order."
        sorter = QuerySorter()

        field_name1 = 'first_name'
        field_name2 = 'last_name'

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        sort_info = sorter.get(model=FakeContact, cells=cells, cell_key='invalid')
        self.assertEqual(
            (field_name2, field_name1, 'cremeentity_ptr_id'),
            sort_info.field_names,
        )
        # Fallback to (first) natural ordering field
        self.assertEqual(cells[1].key, sort_info.main_cell_key)
        self.assertTrue(sort_info.main_order.asc)

    def test_regularfield_default_twoorders_04(self):
        sorter = QuerySorter()

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [build_cell(name='phone'), build_cell(name='email')]

        sort_info = sorter.get(model=FakeContact, cells=cells, cell_key=None)
        self.assertEqual(('cremeentity_ptr_id',), sort_info.field_names)
        self.assertIsNone(sort_info.main_cell_key)  # Fallback to (first) natural ordering field
        self.assertTrue(sort_info.main_order.asc)

    def test_regularfield_default_twoorders_05(self):
        "One natural ordering field not in cells."
        sorter = QuerySorter()

        self.assertEqual(('name', '-expiration_date'), FakeInvoice._meta.ordering)
        self.assertIsNone(get_indexed_ordering(FakeInvoice, ['name', '-expiration_date']))

        field_name1 = 'name'

        build_cell = partial(EntityCellRegularField.build, model=FakeInvoice)
        cells = [
            build_cell(name='number'),
            build_cell(name=field_name1),
            # Not expiration_date
        ]

        sort_info = sorter.get(model=FakeInvoice, cells=cells, cell_key=None)
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), sort_info.field_names)
        self.assertEqual(cells[1].key, sort_info.main_cell_key)  # First natural order
        self.assertTrue(sort_info.main_order.asc)

    def test_regularfield_default_twoorders_06(self):
        "One natural ordering field not in cells, but a smart index exists."
        sorter = QuerySorter()

        field_name1 = 'last_name'

        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [build_cell(name='email'), build_cell(name=field_name1)]

        sort_info = sorter.get(model=FakeContact, cells=cells, cell_key=None)
        self.assertEqual(cells[1].key,   sort_info.main_cell_key)  # First natural order
        self.assertTrue(sort_info.main_order.asc)

    def test_regularfield_default_descorder_01(self):
        "Natural ordering is DESC."
        sorter = QuerySorter()

        field_name1 = 'start'
        field_name2 = 'title'
        self.assertEqual(('-' + field_name1,), FakeActivity._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=FakeActivity)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        key = cells[0].key
        sort_info1 = sorter.get(model=FakeActivity, cells=cells, cell_key=key)
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), sort_info1.field_names)
        self.assertEqual(key,   sort_info1.main_cell_key)
        self.assertEqual('ASC', str(sort_info1.main_order))

        # DESC ------------
        sort_info2 = sorter.get(
            model=FakeActivity, cells=cells, cell_key=key, order=Order(False),
        )
        self.assertEqual(
            ('-' + field_name1, '-cremeentity_ptr_id'),
            sort_info2.field_names,
        )
        self.assertEqual(key,    sort_info2.main_cell_key)
        self.assertEqual('DESC', str(sort_info2.main_order))

    def test_regularfield_default_descorder_02(self):
        "Natural ordering is DESC => Empty GET/POST => DESC."
        sorter = QuerySorter()

        field_name1 = 'start'
        field_name2 = 'title'

        build_cell = partial(EntityCellRegularField.build, model=FakeActivity)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        key = cells[0].key
        sort_info = sorter.get(
            model=FakeActivity, cells=cells, cell_key=None, order=None,
        )
        self.assertEqual(
            ('-' + field_name1, '-cremeentity_ptr_id'),
            sort_info.field_names,
        )
        self.assertEqual(key, sort_info.main_cell_key)
        self.assertTrue(sort_info.main_order.desc)

    def test_regularfield_default_descorder_03(self):
        "Natural ordering is DESC + another field."
        sorter = QuerySorter()
        field_name1 = 'start'
        field_name2 = 'place'  # Not unique (see below)

        build_cell = partial(EntityCellRegularField.build, model=FakeActivity)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        key = cells[1].key
        sort_info1 = sorter.get(
            model=FakeActivity, cells=cells, cell_key=key, order=None,
        )
        self.assertEqual(
            (field_name2, '-' + field_name1, 'cremeentity_ptr_id'),
            sort_info1.field_names,
        )
        self.assertEqual(key, sort_info1.main_cell_key)
        self.assertTrue(sort_info1.main_order.asc)

        # DESC ------------------------------
        sort_info2 = sorter.get(
            model=FakeActivity, cells=cells, cell_key=key, order=Order(False)
        )
        self.assertEqual(
            (
                '-' + field_name2,
                '-' + field_name1,
                '-cremeentity_ptr_id',
            ),
            sort_info2.field_names,
        )
        self.assertEqual(key, sort_info2.main_cell_key)
        self.assertTrue(sort_info2.main_order.desc)

        # FAST MODE
        sort_info3 = sorter.get(
            model=FakeActivity, cells=cells, cell_key=key, fast_mode=True,
        )
        self.assertEqual(
            (field_name2, 'cremeentity_ptr_id'),
            sort_info3.field_names,
        )

    def test_regularfield_default_twoordersdesc(self):
        "meta.ordering: 2 fields (one is DESC)."
        sorter = QuerySorter()

        field_name1 = 'name'
        field_name2 = 'expiration_date'
        self.assertEqual((field_name1, '-' + field_name2), FakeInvoice._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=FakeInvoice)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        key = cells[0].key
        sortinfo1 = sorter.get(model=FakeInvoice, cells=cells, cell_key=key)
        self.assertEqual(
            (field_name1, '-' + field_name2, 'cremeentity_ptr_id'),
            sortinfo1.field_names,
        )
        self.assertEqual(key, sortinfo1.main_cell_key)
        self.assertTrue(sortinfo1.main_order.asc)

        # DESC -----------------------------
        sortinfo2 = sorter.get(
            model=FakeInvoice, cells=cells, cell_key=key, order=Order(False),
        )
        self.assertEqual(
            ('-' + field_name1, field_name2, '-cremeentity_ptr_id'),
            sortinfo2.field_names,
        )
        self.assertEqual(key, sortinfo2.main_cell_key)
        self.assertTrue(sortinfo2.main_order.desc)

    def test_regularfield_registry_argument(self):
        class MyFKRegistry(CellSorterRegistry):
            def get_field_name(this, cell):
                return cell.value + '_id'

        sorter = QuerySorter(MyFKRegistry())

        field_name1 = 'title'
        field_name2 = 'linked_folder'
        self.assertEqual((field_name1,), FakeDocument._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=FakeDocument)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        key = cells[1].key
        sort_info = sorter.get(model=FakeDocument, cells=cells, cell_key=key)
        self.assertEqual(
            (
                field_name2 + '_id',  # not '__header_filter_search_field'
                field_name1,
                'cremeentity_ptr_id',
            ),
            sort_info.field_names,
        )
        self.assertEqual(cells[1].key, sort_info.main_cell_key)
        self.assertTrue(sort_info.main_order.asc)

    def test_regularfield_register_fieldtype(self):
        "Register model field type."
        sorter = QuerySorter()

        fields_registry = sorter.registry[EntityCellRegularField.type_id]
        self.assertIsInstance(
            fields_registry.sorter_4_model_field_type(IntegerField),
            RegularFieldSorter,
        )

        fields_registry.register_model_field_type(
            type=IntegerField, sorter_cls=VoidSorter,
        )
        self.assertIsInstance(
            fields_registry.sorter_4_model_field_type(IntegerField),
            VoidSorter,
        )
        self.assertIsInstance(
            fields_registry.sorter_4_model_field_type(CharField),
            RegularFieldSorter,
        )

        field_name1 = 'name'
        field_name2 = 'capital'

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]
        sort_info = sorter.get(model=FakeOrganisation, cells=cells, cell_key=cells[1].key)
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), sort_info.field_names)

    def test_regularfield_register_field(self):
        "Register model field."
        sorter = QuerySorter()

        fields_registry = sorter.registry[EntityCellRegularField.type_id]
        self.assertIsNone(
            fields_registry.sorter_4_model_field(
                model=FakeInvoice, field_name='issuing_date',
            )
        )

        fields_registry.register_model_field(
            model=FakeInvoice, field_name='issuing_date', sorter_cls=VoidSorter,
        )
        self.assertIsInstance(
            fields_registry.sorter_4_model_field(
                model=FakeInvoice, field_name='issuing_date',
            ),
            VoidSorter,
        )
        field_name1 = 'issuing_date'
        field_name2 = 'expiration_date'

        build_cell = partial(EntityCellRegularField.build, model=FakeInvoice)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]
        sort_info = sorter.get(model=FakeInvoice, cells=cells, cell_key=cells[0].key)
        self.assertEqual(
            ('-expiration_date', '-cremeentity_ptr_id'),
            sort_info.field_names,
        )

    def test_regularfield_default_not_sortable01(self):
        "DatePeriodField is not sortable."
        sorter = QuerySorter()

        field_name1 = 'name'
        field_name2 = 'periodicity'

        build_cell = partial(EntityCellRegularField.build, model=FakeInvoice)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        sort_info = sorter.get(
            model=FakeInvoice, cells=cells, cell_key=cells[1].key, order=Order(),
        )
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), sort_info.field_names)
        self.assertEqual(cells[0].key, sort_info.main_cell_key)
        self.assertTrue(sort_info.main_order.asc)

    def test_regularfield_default_not_sortable02(self):
        "ManyToManyField is not sortable."
        registry = CellSorterRegistry()
        sorter = QuerySorter()

        field_name1 = 'name'
        field_name2 = 'mailing_lists'

        build_cell = partial(EntityCellRegularField.build, model=FakeEmailCampaign)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]
        self.assertEqual(field_name1, registry.get_field_name(cells[0]))
        self.assertIsNone(registry.get_field_name(cells[1]))

        sort_info1 = sorter.get(
            model=FakeEmailCampaign, cells=cells,
            cell_key=cells[1].key, order=Order(),
        )
        self.assertEqual((field_name1, 'cremeentity_ptr_id'), sort_info1.field_names)
        self.assertEqual(cells[0].key, sort_info1.main_cell_key)
        self.assertTrue(sort_info1.main_order.asc)

        # Sub-field ---
        cell3 = build_cell(name='mailing_lists__user')
        self.assertIsNone(registry.get_field_name(cell3))

        sort_info2 = sorter.get(
            model=FakeEmailCampaign, cells=[cell3],
            cell_key=cell3.key, order=Order(),
        )
        self.assertEqual(('cremeentity_ptr_id',), sort_info2.field_names)
        self.assertIsNone(sort_info2.main_cell_key)

    def test_regularfield_default_autofield(self):
        "AutoField is sortable."
        cell = EntityCellRegularField.build(model=HistoryLine, name='id')
        self.assertEqual('id', CellSorterRegistry().get_field_name(cell))

    def test_register_related_model(self):
        sorter = QuerySorter()

        fk_registry = sorter.registry[
            EntityCellRegularField.type_id
        ].sorter_4_model_field_type(ForeignKey)
        efk_registry = fk_registry.sorter(CremeEntity)
        self.assertIsInstance(efk_registry, EntityForeignKeySorter)

        class MyEntityForeignKeySorter(AbstractCellSorter):
            def get_field_name(self, cell):
                return f'{cell.value}__created'

        efk_registry = fk_registry.register(
            model=CremeEntity,
            sorter_cls=MyEntityForeignKeySorter,
        )
        self.assertIsInstance(efk_registry.sorter(CremeEntity), MyEntityForeignKeySorter)
        self.assertIsNone(efk_registry.sorter(FakeSector))

        field_name1 = 'title'
        field_name2 = 'linked_folder'
        build_cell = partial(EntityCellRegularField.build, model=FakeDocument)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        sort_info = sorter.get(
            model=FakeDocument, cells=cells, cell_key=cells[1].key,
        )
        self.assertEqual(
            (
                f'{field_name2}__created',
                field_name1,
                'cremeentity_ptr_id',
            ),
            sort_info.field_names,
        )

    # def test_customfield(self):  TODO

    def test_functionfield01(self):
        "Function field are not sortable by default."
        sorter = QuerySorter()

        field_name = 'name'
        cells = [
            EntityCellRegularField.build(model=FakeOrganisation, name=field_name),
            EntityCellFunctionField.build(
                model=FakeContact, name='get_pretty_properties',
            ),
        ]

        sort_info = sorter.get(
            model=FakeInvoice, cells=cells, cell_key=cells[1].key, order=Order(),
        )
        self.assertEqual((field_name, 'cremeentity_ptr_id'), sort_info.field_names)
        self.assertEqual(cells[0].key, sort_info.main_cell_key)
        self.assertTrue(sort_info.main_order.asc)

    def test_functionfield02(self):
        "Register a function field."
        class PhoneFunctionField(FunctionField):
            name = 'phone_or_mobile'
            verbose_name = 'Phone or mobile'

            # def __call__(self, entity, user):
            #     return self.result_type(entity.phone or entity.mobile)

        function_field1 = PropertiesField()
        function_field2 = PhoneFunctionField()

        class PropertySorter(AbstractCellSorter):
            def get_field_name(this, cell):
                return 'created'  # NB: it has no sense, it's just for testing purposes...

        sorter = QuerySorter()
        ffield_registry = sorter.registry[EntityCellFunctionField.type_id]
        self.assertIsNone(ffield_registry.sorter(function_field1))

        ffield_registry.register(
            ffield=function_field1, sorter_cls=PropertySorter,
        )
        self.assertIsInstance(ffield_registry.sorter(function_field1), PropertySorter)

        cells = [
            EntityCellRegularField.build(model=FakeOrganisation, name='name'),
            EntityCellFunctionField(model=FakeOrganisation, func_field=function_field1),
            EntityCellFunctionField(model=FakeOrganisation, func_field=function_field2),
        ]

        prop_key = cells[1].key
        sort_info1 = sorter.get(model=FakeOrganisation, cells=cells, cell_key=prop_key)
        self.assertEqual(
            ('created', 'name', 'cremeentity_ptr_id'),
            sort_info1.field_names,
        )
        self.assertEqual(prop_key, sort_info1.main_cell_key)
        self.assertTrue(sort_info1.main_order.asc)

        # ---
        sort_info2 = sorter.get(
            model=FakeOrganisation, cells=cells, cell_key=cells[2].key,
        )
        self.assertEqual(
            ('name', 'cremeentity_ptr_id'), sort_info2.field_names,
        )

    def test_functionfield03(self):
        "<sorter_class> attribute."
        class PhoneSorter(AbstractCellSorter):
            def get_field_name(this, cell):
                return 'modified'  # NB: it has no sense, it's just for testing purposes...

        class PhoneFunctionField(FunctionField):
            name = 'phone_or_mobile'
            verbose_name = 'Phone or mobile'
            sorter_class = PhoneSorter

            # def __call__(self, entity, user):
            #     return self.result_type(entity.phone or entity.mobile)

        function_field = PhoneFunctionField()
        sorter = QuerySorter()

        cells = [
            EntityCellRegularField.build(model=FakeOrganisation, name='name'),
            EntityCellFunctionField(model=FakeOrganisation, func_field=function_field),
        ]

        key = cells[1].key
        sort_info = sorter.get(model=FakeOrganisation, cells=cells, cell_key=key)
        self.assertEqual(
            ('modified', 'name', 'cremeentity_ptr_id'), sort_info.field_names,
        )
        self.assertEqual(key, sort_info.main_cell_key)
        self.assertTrue(sort_info.main_order.asc)

    def test_relation(self):
        "EntityCellRelation are not sortable."
        sorter = QuerySorter()

        field_name = 'name'
        cells = [
            EntityCellRegularField.build(model=FakeOrganisation, name=field_name),
            EntityCellRelation.build(model=FakeOrganisation,     name=REL_SUB_HAS),
        ]

        sortinfo = sorter.get(
            model=FakeInvoice, cells=cells,
            cell_key=cells[1].key, order=Order(),
        )
        self.assertEqual((field_name, 'cremeentity_ptr_id'), sortinfo.field_names)
        self.assertEqual(cells[0].key, sortinfo.main_cell_key)
        self.assertTrue(sortinfo.main_order.asc)

    def test_not_entity(self):
        sorter = QuerySorter(CellSorterRegistry())

        model = FakeCivility
        field_name1 = 'title'
        field_name2 = 'shortcut'
        self.assertEqual(('title',), model._meta.ordering)

        build_cell = partial(EntityCellRegularField.build, model=FakeCivility)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        key = cells[0].key
        get_sortinfo = partial(sorter.get, model=model, cells=cells, cell_key=key)
        sort_info1 = get_sortinfo(order=Order())
        self.assertIsInstance(sort_info1, QuerySortInfo)

        self.assertEqual((field_name1, 'id'), sort_info1.field_names)
        self.assertEqual(key,   sort_info1.main_cell_key)
        self.assertEqual('ASC', str(sort_info1.main_order))

        # DESC ---
        sort_info2 = get_sortinfo(order=Order(False))
        self.assertEqual(('-' + field_name1, '-id'), sort_info2.field_names)
        self.assertEqual(key, sort_info2.main_cell_key)
        self.assertTrue(sort_info2.main_order.desc)

    def test_key_already_unique(self):
        sorter = QuerySorter()
        model = FakeActivity
        field_name1 = 'start'
        field_name2 = 'title'

        self.assertTrue(model._meta.get_field(field_name2).unique)

        build_cell = partial(EntityCellRegularField.build, model=model)
        cells = [build_cell(name=field_name1), build_cell(name=field_name2)]

        key = cells[1].key
        get_sortinfo = partial(sorter.get, model=model, cells=cells, cell_key=key)

        sort_info1 = get_sortinfo(order=None)
        self.assertEqual(
            (field_name2, '-' + field_name1),
            sort_info1.field_names,
        )
        self.assertEqual(key, sort_info1.main_cell_key)
        self.assertTrue(sort_info1.main_order.asc)

        # DESC ------------------------------
        sort_info2 = get_sortinfo(order=Order(False))
        self.assertEqual(
            ('-' + field_name2, '-' + field_name1),
            sort_info2.field_names,
        )
        self.assertEqual(key, sort_info2.main_cell_key)
        self.assertTrue(sort_info2.main_order.desc)

        # FAST MODE ------------------------------
        sort_info3 = get_sortinfo(fast_mode=True)
        self.assertEqual((field_name2,), sort_info3.field_names)

        # FAST MODE + DESC ------------------------------
        sort_info4 = get_sortinfo(fast_mode=True, order=Order(False))
        self.assertEqual(('-' + field_name2,), sort_info4.field_names)
