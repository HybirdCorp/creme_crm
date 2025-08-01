from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from creme.creme_core.models import (
    CremeEntity,
    EntityFilter,
    FakeContact,
    FakeOrganisation,
    FakeTodo,
    FieldsConfig,
)
from creme.creme_core.models.fields import DatePeriodField
from creme.creme_core.utils.date_period import MonthsPeriod, WeeksPeriod

from ..base import CremeTestCase


class ModelFieldsTestCase(CremeTestCase):
    def test_CTypeForeignKey01(self):
        ct = ContentType.objects.get_for_model(FakeContact)
        efilter = EntityFilter.objects.create(
            pk='creme_core-test_fakecontact',
            entity_type=ct,
        )
        self.assertEqual(ct, self.refresh(efilter).entity_type)

    def test_CTypeForeignKey02(self):
        "Set a model class directly."
        with self.assertNoException():
            efilter = EntityFilter.objects.create(
                pk='creme_core-test_fakecontact',
                entity_type=FakeContact,
            )

        self.assertEqual(
            ContentType.objects.get_for_model(FakeContact),
            self.refresh(efilter).entity_type,
        )

    def test_CTypeOneToOneField01(self):
        ct = ContentType.objects.get_for_model(FakeContact)
        fconf = FieldsConfig.objects.create(content_type=ct)
        self.assertEqual(ct, self.refresh(fconf).content_type)

    def test_CTypeOneToOneField02(self):
        "Set a model class directly."
        with self.assertNoException():
            fconf = FieldsConfig.objects.create(content_type=FakeContact)

        self.assertEqual(
            ContentType.objects.get_for_model(FakeContact),
            self.refresh(fconf).content_type,
        )


class DatePeriodFieldTestCase(CremeTestCase):
    def test_ok(self):
        field = DatePeriodField(name='Periodicity')
        self.assertIsNone(field.to_python(None))
        self.assertIsNone(field.to_python({}))
        self.assertIsNone(field.to_python(''))

        # Dict
        self.assertEqual(MonthsPeriod(1), field.to_python({'type': 'months', 'value': 1}))
        self.assertEqual(WeeksPeriod(2),  field.to_python({'type': 'weeks', 'value': 2}))
        self.assertEqual(MonthsPeriod(1), field.get_prep_value({'type': 'months', 'value': 1}))

        # # Str
        # self.assertEqual(MonthsPeriod(1), field.to_python('{"type": "months", "value": 1}'))
        # self.assertEqual(WeeksPeriod(2),  field.to_python('{"type": "weeks", "value": 2}'))
        # self.assertEqual(WeeksPeriod(2),  field.get_prep_value('{"type": "weeks", "value": 2}'))

        # DatePeriod
        period = MonthsPeriod(1)
        self.assertEqual(period, field.to_python(period))

    def test_dict_errors(self):
        field = DatePeriodField(name='Periodicity')

        with self.assertRaises(ValidationError) as cm:
            field.to_python({'a_key': 'a_value'})
        self.assertValidationError(
            error=cm.exception,
            messages="DatePeriodField.to_python(): dict is invalid (missing key 'type')",
        )

        with self.assertRaises(ValidationError) as cm:
            field.to_python({'type': 'invalid', 'value': 1})
        self.assertValidationError(
            error=cm.exception,
            messages="DatePeriodField.to_python(): period is invalid (dict argument)",
        )

    # def test_str_errors(self):
    #     field = DatePeriodField(name='Periodicity')
    #
    #     with self.assertRaises(ValidationError) as cm:
    #         field.to_python('{"a_key": "a_value"}')
    #     self.assertValidationError(
    #         error=cm.exception,
    #         messages="DatePeriodField.to_python(): string is invalid (missing key 'type')",
    #     )
    #
    #     with self.assertRaises(ValidationError) as cm:
    #         field.to_python('{"type": "invalid", "value": 1}')
    #     self.assertValidationError(
    #         error=cm.exception,
    #         messages="DatePeriodField.to_python(): period is invalid (string argument)",
    #     )
    #
    #     with self.assertRaises(ValidationError) as cm:
    #         field.to_python('{"type": "')
    #     self.assertValidationError(
    #         error=cm.exception,
    #         messages=(
    #             "DatePeriodField.to_python(): invalid JSON "
    #             "(Unterminated string starting at: line 1 column 10 (char 9))"
    #         ),
    #     )

    def test_type_error(self):
        field = DatePeriodField(name='Periodicity')

        with self.assertRaises(ValidationError) as cm:
            field.to_python(123)
        self.assertValidationError(
            error=cm.exception,
            messages=(
                "DatePeriodField.to_python(): "
                "value must be None/dict/string/DatePeriod ('int' given)"
            ),
        )

        with self.assertRaises(ValidationError) as cm:
            field.to_python([1, 2, 3])
        self.assertValidationError(
            error=cm.exception,
            messages=(
                "DatePeriodField.to_python(): "
                "value must be None/dict/string/DatePeriod ('list' given)"
            ),
        )


class RealEntityForeignKeyTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.get_ct = get_ct = ContentType.objects.get_for_model
        get_ct(FakeContact)
        get_ct(CremeEntity)

        cls.user = user = cls.get_root_user()
        cls.entity = FakeContact.objects.create(
            user=user, first_name='Ranma', last_name='Saotome',
        )

    def test_basic_get_n_set(self):
        todo = FakeTodo(title='My todo')

        with self.assertNumQueries(0):
            todo.creme_entity = self.entity

        with self.assertNumQueries(0):
            ct = todo.entity_content_type
        self.assertEqual(self.get_ct(FakeContact), ct)

        with self.assertNumQueries(0):
            entity = todo.entity
        self.assertEqual(self.entity, entity)

        with self.assertNoException():
            todo.save()

        # ----
        todo = self.refresh(todo)
        self.assertEqual(self.entity.id, todo.entity_id)
        self.assertEqual(ct.id,          todo.entity_content_type_id)

        with self.assertNumQueries(1):
            creme_entity = todo.creme_entity
        self.assertEqual(self.entity, creme_entity)

    def test_get_with_cache(self):
        todo = FakeTodo.objects.create(title='My todo', creme_entity=self.entity)

        todo = self.refresh(todo)

        with self.assertNumQueries(1):
            todo.creme_entity  # NOQA

        with self.assertNumQueries(0):  # <= cache
            creme_entity = todo.creme_entity

        self.assertEqual(self.entity, creme_entity)

    def test_update_fk_cache(self):
        entity = self.entity
        todo = FakeTodo.objects.create(
            title='My todo',
            entity_id=entity.id,
            entity_content_type=entity.entity_type,
        )

        todo = self.refresh(todo)

        with self.assertNumQueries(1):
            todo.creme_entity  # NOQA

        with self.assertNumQueries(0):  # <= cache
            creme_entity = todo.entity

        self.assertEqual(self.entity, creme_entity)

    def test_fk_cache(self):
        """Do not retrieve real entity if already stored/retrieved in 'entity'
         attribute.
         """
        entity = self.entity
        todo = FakeTodo(
            title='My todo',
            entity=entity,  # <== real entity
            entity_content_type=entity.entity_type,  # Must be set (consistency protection)
        )

        with self.assertNumQueries(0):
            creme_entity = todo.creme_entity

        self.assertEqual(entity, creme_entity)

    def test_missing_ctype01(self):
        "CT not set + base entity set => error."
        todo = FakeTodo(
            title='My todo',
            entity=CremeEntity.objects.get(id=self.entity.id),  # Not real entity...
        )

        with self.assertRaises(ValueError) as error_context:
            todo.creme_entity  # NOQA

        self.assertEqual(
            'The content type is not set while the entity is. '
            'HINT: set both by hand or just use the RealEntityForeignKey setter.',
            error_context.exception.args[0]
        )

    def test_missing_ctype02(self):
        "CT not set + entity ID set => error."
        todo = FakeTodo(title='My todo', entity_id=self.entity.id)

        with self.assertRaises(ValueError) as error_context:
            todo.creme_entity  # NOQA

        self.assertEqual(
            'The content type is not set while the entity is. '
            'HINT: set both by hand or just use the RealEntityForeignKey setter.',
            error_context.exception.args[0]
        )

    def test_cache_for_set01(self):
        "After a '__set__' with a real entity, '__get__' uses no query."
        entity = self.entity
        todo = FakeTodo(title='My todo')

        with self.assertNumQueries(0):
            todo.creme_entity = entity

        with self.assertNumQueries(0):
            creme_entity = todo.creme_entity

        self.assertEqual(entity, creme_entity)

    def test_cache_for_set02(self):
        """After a '__set__' with a real entity, '__get__' uses no query
        (base entity version).
        """
        entity = CremeEntity.objects.get(id=self.entity.id)
        real_entity = entity.get_real_entity()

        todo = FakeTodo(title='My todo')

        with self.assertNumQueries(0):
            todo.creme_entity = entity

        with self.assertNumQueries(0):
            creme_entity = todo.creme_entity

        self.assertEqual(real_entity, creme_entity)

    def test_get_real_entity(self):
        """Set a base entity, so '__get__' uses a query to retrieve the real
        entity.
        """
        entity = self.entity
        todo = FakeTodo(title='My todo')

        base_entity = CremeEntity.objects.get(id=entity.id)

        with self.assertNumQueries(0):
            todo.creme_entity = base_entity

        with self.assertNumQueries(1):
            creme_entity = todo.creme_entity
        self.assertEqual(entity, creme_entity)

        with self.assertNumQueries(0):
            creme_entity2 = todo.creme_entity
        self.assertEqual(entity, creme_entity2)

    def test_set_none01(self):
        entity = self.entity
        todo = FakeTodo(
            title='My todo',
            entity=entity,
            entity_content_type=entity.entity_type,
        )

        todo.creme_entity = None
        self.assertIsNone(todo.entity_id)
        self.assertIsNone(todo.entity_content_type_id)

        with self.assertNumQueries(0):
            creme_entity = todo.creme_entity

        self.assertIsNone(creme_entity)

    def test_set_none02(self):
        "Set None after not None on virtual field (cache invalidation)."
        entity = self.entity.get_real_entity()
        todo = FakeTodo(title='My todo', creme_entity=entity)

        todo.creme_entity = None
        self.assertIsNone(todo.entity_id)
        self.assertIsNone(todo.entity_content_type_id)

        with self.assertNumQueries(0):
            creme_entity = todo.creme_entity

        self.assertIsNone(creme_entity)

    def test_get_none01(self):
        "Get initial None."
        todo = FakeTodo(
            title='My todo',
            # entity=entity,  # Not set
        )

        with self.assertNumQueries(0):
            creme_entity = todo.creme_entity

        self.assertIsNone(creme_entity)

        #  --
        todo.entity = entity = self.entity

        with self.assertRaises(ValueError):
            todo.creme_entity  # NOQA

        # --
        todo.entity_content_type_id = entity.entity_type_id

        with self.assertNumQueries(0):
            creme_entity2 = todo.creme_entity

        self.assertEqual(entity, creme_entity2)

    def test_get_none02(self):
        "Get initial None (explicitly set)."
        todo = FakeTodo(title='My todo', entity=None)

        with self.assertNumQueries(0):
            creme_entity = todo.creme_entity

        self.assertIsNone(creme_entity)

    def test_bad_ctype01(self):
        "Bad CT id + base entity id."
        todo = FakeTodo(
            title='My todo',
            entity_id=self.entity.id,
            # Does not correspond to 'self.entity'
            entity_content_type=self.get_ct(FakeOrganisation),
        )

        with self.assertRaises(FakeOrganisation.DoesNotExist):
            todo.creme_entity  # NOQA

    def test_bad_ctype02(self):
        "Bad CT + base entity."
        todo = FakeTodo(
            title='My todo',
            # Not real entity...
            entity=CremeEntity.objects.get(id=self.entity.id),
            # Does not correspond to 'self.entity'
            entity_content_type=self.get_ct(FakeOrganisation),
        )

        with self.assertRaises(ValueError) as error_context:
            todo.creme_entity  # NOQA

        self.assertEqual(
            'The content type does not match this entity.',
            error_context.exception.args[0]
        )

    def test_change_entity(self):
        "New entity with new CT."
        todo = FakeTodo.objects.create(
            title='My todo',
            creme_entity=self.entity,
        )
        orga = FakeOrganisation.objects.create(user=self.user, name='Tendô no dojo')

        todo = self.refresh(todo)
        todo.creme_entity = orga
        todo.save()

        todo = self.refresh(todo)
        self.assertEqual(orga, todo.creme_entity)
        self.assertEqual(orga.id, todo.entity_id)
        self.assertEqual(FakeOrganisation, todo.entity_content_type.model_class())

    def test_get_prefetch_querysets(self):
        user = self.user

        create_contact = partial(FakeContact.objects.create, user=user)
        akane = create_contact(first_name='Akane', last_name='Tendo')
        ranma = create_contact(first_name='Ranma', last_name='Saotome')

        dojo = FakeOrganisation.objects.create(user=user, name='Tendo no dojo')

        meta = FakeTodo._meta
        with self.assertNoException():
            meta.get_field('entity_content_type')
            meta.get_field('entity')
        self.assertListEqual(['creme_entity'], [f.name for f in meta.private_fields])

        self.assertHasAttr(FakeTodo, 'entity')
        # self.assertHasAttr(FakeTodo, 'entity_content_type') TODO?
        self.assertHasAttr(FakeTodo, 'creme_entity')

        create_todo = FakeTodo.objects.create
        create_todo(creme_entity=akane, title='Todo#1'),
        create_todo(creme_entity=dojo,  title='Todo#2'),
        create_todo(creme_entity=ranma, title='Todo#3'),

        with self.assertNumQueries(3):
            todos = [*FakeTodo.objects.order_by('id').prefetch_related('creme_entity')]
        self.assertEqual(3, len(todos))

        with self.assertNumQueries(0):
            entities = [todo.creme_entity for todo in todos]
        self.assertListEqual([akane, dojo, ranma], entities)

        with self.assertNumQueries(0):
            base_entities = [todo.entity for todo in todos]
        self.assertListEqual([akane, dojo, ranma], base_entities)
