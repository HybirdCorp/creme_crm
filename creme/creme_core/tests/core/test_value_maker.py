from datetime import date
from decimal import Decimal

from django.utils.formats import date_format, number_format
from django.utils.timezone import localtime, now
from django.utils.translation import gettext as _

from creme.creme_core.core.value_maker import (
    BooleanMaker,
    DateMaker,
    DateTimeMaker,
    DecimalMaker,
    IntegerMaker,
    NoneMaker,
    StringMaker,
    ValueMakerRegistry,
    value_maker_registry,
)

from ..base import CremeTestCase


class ValueMakerTestCase(CremeTestCase):
    def test_none(self):
        self.assertEqual('', NoneMaker.type_id)

        with self.assertNoException():
            maker = NoneMaker.from_dict({})
        self.assertIsNone(maker.make())
        self.assertEqual('', maker.render())

    def test_int(self):
        self.assertEqual('int', IntegerMaker.type_id)

        value1 = 42
        maker1 = IntegerMaker(value1)
        self.assertEqual(value1, maker1.make())
        self.assertDictEqual({'type': 'int', 'value': value1}, maker1.to_dict())
        self.assertEqual(number_format(value1, force_grouping=True), maker1.render())

        # Other value ---
        value2 = 1280
        maker2 = IntegerMaker(value2)
        self.assertEqual(value2, maker2.make())
        self.assertDictEqual({'type': 'int', 'value': value2}, maker2.to_dict())
        self.assertEqual(number_format(value2, force_grouping=True), maker2.render())

        # Errors ---
        with self.assertRaises(ValueError):
            IntegerMaker('not_int')

        # Equals
        self.assertNotEqual(maker1, maker2)
        self.assertEqual(maker1, IntegerMaker(value1))
        self.assertNotEqual(maker1, BooleanMaker(value1))
        self.assertNotEqual(maker1, NoneMaker())

    def test_int__from_dict(self):
        value1 = 42
        with self.assertNoException():
            maker1 = IntegerMaker.from_dict({'value': value1, 'whatever': 125})
        self.assertEqual(value1, maker1.make())
        self.assertDictEqual({'type': 'int', 'value': value1}, maker1.to_dict())

        # Other value ---
        value2 = 128
        maker2 = IntegerMaker.from_dict({'value': value2})
        self.assertEqual(value2, maker2.make())
        self.assertDictEqual({'type': 'int', 'value': value2}, maker2.to_dict())

        # Errors ---
        with self.assertRaises(KeyError):
            IntegerMaker.from_dict({})
        with self.assertRaises(KeyError):
            IntegerMaker.from_dict({'invalid': 12})
        with self.assertRaises(ValueError):
            IntegerMaker.from_dict({'value': 'not_int'})

    def test_bool(self):
        self.assertEqual('bool', BooleanMaker.type_id)

        maker1 = BooleanMaker(True)
        self.assertIs(maker1.make(), True)
        self.assertDictEqual({'type': 'bool', 'value': True}, maker1.to_dict())
        self.assertEqual(_('Yes'), maker1.render())

        # Other value ---
        maker2 = BooleanMaker(False)
        self.assertIs(maker2.make(), False)
        self.assertDictEqual({'type': 'bool', 'value': False}, maker2.to_dict())
        self.assertEqual(_('No'), maker2.render())

        self.assertDictEqual(
            {'type': 'bool', 'value': True}, BooleanMaker(13).to_dict(),
        )

        # Equals
        self.assertNotEqual(maker1, maker2)
        self.assertEqual(maker1, BooleanMaker(True))
        self.assertNotEqual(maker1, NoneMaker())

    def test_bool__from_dict(self):
        with self.assertNoException():
            maker1 = BooleanMaker.from_dict({'value': True, 'whatever': '123'})
        self.assertIs(maker1.make(), True)
        self.assertDictEqual({'type': 'bool', 'value': True}, maker1.to_dict())

        # Other value ---
        maker2 = BooleanMaker.from_dict({'value': False})
        self.assertIs(maker2.make(), False)
        self.assertDictEqual({'type': 'bool', 'value': False}, maker2.to_dict())

        # Errors ---
        with self.assertRaises(KeyError):
            BooleanMaker.from_dict({})

        with self.assertRaises(KeyError):
            BooleanMaker.from_dict({'invalid': True})

    def test_decimal(self):
        self.assertEqual('decimal', DecimalMaker.type_id)

        str_value1 = '3.14'
        value1 = Decimal(str_value1)
        maker1 = DecimalMaker(str_value1)
        self.assertEqual(value1, maker1.make())
        self.assertDictEqual({'type': 'decimal', 'value': str_value1}, maker1.to_dict())
        self.assertEqual(number_format(value1, force_grouping=True), maker1.render())

        # Other value ---
        str_value2 = '1.23'
        maker2 = DecimalMaker(str_value2)
        self.assertEqual(Decimal(str_value2), maker2.make())
        self.assertDictEqual({'type': 'decimal', 'value': str_value2}, maker2.to_dict())

        # Decimal ---
        str_value3 = '4.56'
        dec_value = Decimal(str_value3)
        maker3 = DecimalMaker(dec_value)
        self.assertEqual(dec_value, maker3.make())
        self.assertDictEqual({'type': 'decimal', 'value': str_value3}, maker3.to_dict())

        # Errors ---
        with self.assertRaises(ValueError):
            DecimalMaker('not_number')

        # Equals ---
        self.assertNotEqual(maker1, maker2)
        self.assertEqual(maker1, DecimalMaker(str_value1))
        self.assertNotEqual(maker1, NoneMaker())

    def test_decimal__from_dict(self):
        str_value1 = '3.14'
        with self.assertNoException():
            maker1 = DecimalMaker.from_dict({'value': str_value1})
        self.assertEqual(Decimal(str_value1), maker1.make())
        self.assertDictEqual({'type': 'decimal', 'value': str_value1}, maker1.to_dict())

        # Other value
        str_value2 = '1.23'
        maker2 = DecimalMaker.from_dict({'value': str_value2})
        self.assertEqual(Decimal(str_value2), maker2.make())
        self.assertDictEqual({'type': 'decimal', 'value': str_value2}, maker2.to_dict())

        # Errors ---
        with self.assertRaises(KeyError):
            DecimalMaker.from_dict({})

        with self.assertRaises(KeyError):
            DecimalMaker.from_dict({'invalid': 'whatever'})

        with self.assertRaises(ValueError):
            DecimalMaker.from_dict({'value': 'not_number'})

    def test_str(self):
        self.assertEqual('str', StringMaker.type_id)

        value = 'Hello world'
        maker1 = StringMaker(value)
        self.assertEqual(value, maker1.make())
        self.assertDictEqual({'type': 'str', 'value': value}, maker1.to_dict())
        self.assertEqual(value, maker1.render())

        # Errors ---
        with self.assertRaises(KeyError):
            StringMaker.from_dict({})

        with self.assertRaises(KeyError):
            StringMaker.from_dict({'invalid': 'Hi'})

        # Equals ---
        self.assertEqual(maker1, StringMaker(value))
        self.assertNotEqual(maker1, StringMaker('Other string'))
        self.assertNotEqual(maker1, NoneMaker())

    def test_str__from_dict(self):
        value = 'Hello world'
        with self.assertNoException():
            maker1 = StringMaker.from_dict({'value': value})
        self.assertEqual(value, maker1.make())
        self.assertDictEqual({'type': 'str', 'value': value}, maker1.to_dict())

        # Errors ---
        with self.assertRaises(KeyError):
            StringMaker.from_dict({})

        with self.assertRaises(KeyError):
            StringMaker.from_dict({'invalid': 'Hi'})

    def test_date__fixed(self):
        self.assertEqual('date', DateMaker.type_id)

        date_obj = date(year=2026, month=3, day=28)
        with self.assertNoException():
            maker = DateMaker.from_date(date_obj)

        self.assertIsInstance(maker, DateMaker)
        self.assertEqual(date_obj, maker.make())
        self.assertDictEqual({'type': 'date', 'value': '2026-03-28'}, maker.to_dict())
        self.assertEqual(date_format(date_obj, 'DATE_FORMAT'), maker.render())

        # Equals ---
        self.assertEqual(maker, DateMaker.from_date(date_obj))
        self.assertNotEqual(
            maker, DateMaker.from_date(date(year=2026, month=3, day=29)),
        )
        self.assertNotEqual(maker, NoneMaker())

    def test_date__today(self):
        self.assertEqual('date', DateMaker.type_id)

        with self.assertNoException():
            maker1 = DateMaker.from_operator('today')

        self.assertIsInstance(maker1, DateMaker)
        self.assertEqual(date.today(), maker1.make())
        self.assertDictEqual({'type': 'date', 'op': 'today'}, maker1.to_dict())

        # Error ---
        with self.assertRaises(ValueError) as exc_mng:
            DateMaker.from_operator('invalid')
        self.assertEqual(
            'DateMaker: available operator is "today"', str(exc_mng.exception),
        )

    def test_date__from_dict__fixed(self):
        str_value1 = '2026-03-28'
        with self.assertNoException():
            maker1 = DateMaker.from_dict({'value': str_value1})
        self.assertEqual(date(year=2026, month=3, day=28), maker1.make())
        self.assertDictEqual({'type': 'date', 'value': str_value1}, maker1.to_dict())

        # Other value ---
        str_value2 = '2027-04-27'
        maker2 = DateMaker.from_dict({'value': str_value2})
        self.assertEqual(date(year=2027, month=4, day=27), maker2.make())
        self.assertDictEqual({'type': 'date', 'value': str_value2}, maker2.to_dict())

        # Errors ---
        with self.assertRaises(ValueError):
            DateMaker.from_dict({})

        with self.assertRaises(ValueError):
            DateMaker.from_dict({'value': True})

        with self.assertRaises(ValueError) as exc_mng1:
            DateMaker.from_dict({'invalid': 'Hi'})
        self.assertEqual(
            'DateMaker: available keys are: value, op',
            str(exc_mng1.exception),
        )

        with self.assertRaises(ValueError) as exc_mng2:
            DateMaker.from_dict({'value': 'not_date'})
        self.assertStartsWith(str(exc_mng2.exception), 'DateMaker:')

    def test_date__from_dict__today(self):
        with self.assertNoException():
            maker1 = DateMaker.from_dict({'op': 'today'})
        self.assertEqual(date.today(), maker1.make())
        self.assertDictEqual({'type': 'date', 'op': 'today'}, maker1.to_dict())

        # Error ---
        with self.assertRaises(ValueError) as exc_mng:
            DateMaker.from_dict({'op': 'invalid'})
        self.assertEqual(
            'DateMaker: available operator is "today"',
            str(exc_mng.exception),
        )

    def test_datetime__fixed(self):
        self.assertEqual('datetime', DateTimeMaker.type_id)

        dt = self.create_datetime(
            year=2026, month=5, day=28,
            hour=13, minute=15, second=46, microsecond=987000,
            utc=True,
        )
        with self.assertNoException():
            maker = DateTimeMaker.from_datetime(dt)
        self.assertIsInstance(maker, DateTimeMaker)
        self.assertEqual(dt, maker.make())
        self.assertDictEqual(
            {'type': 'datetime', 'value': '2026-05-28T13:15:46.987000Z'},
            maker.to_dict(),
        )
        self.assertEqual(date_format(localtime(dt), 'DATETIME_FORMAT'), maker.render())

        # Equals ---
        self.assertEqual(maker, DateTimeMaker.from_datetime(dt))
        self.assertNotEqual(
            maker,
            DateTimeMaker.from_datetime(self.create_datetime(
                year=2026, month=5,
                day=29,  # <==
                hour=13, minute=15, second=46, microsecond=987000,
                utc=True,
            )),
        )
        self.assertNotEqual(maker, NoneMaker())

    def test_datetime__now(self):
        with self.assertNoException():
            maker1 = DateTimeMaker.from_operator('now')
        self.assertIsInstance(maker1, DateTimeMaker)
        self.assertDatetimesAlmostEqual(now(), maker1.make())
        self.assertDictEqual({'type': 'datetime', 'op': 'now'}, maker1.to_dict())

        # Error
        with self.assertRaises(ValueError) as exc_mng:
            DateTimeMaker.from_operator('invalid')
        self.assertEqual(
            'DateTimeMaker: available operator is "now"', str(exc_mng.exception),
        )

    def test_datetime__from_dict__fixed(self):
        str_value1 = '2026-03-17T16:22:03.458000Z'
        with self.assertNoException():
            maker1 = DateTimeMaker.from_dict({'value': str_value1})
        self.assertEqual(
            self.create_datetime(
                year=2026, month=3, day=17,
                hour=16, minute=22, second=3, microsecond=458000,
                utc=True,
            ),
            maker1.make(),
        )
        self.assertDictEqual(
            {'type': 'datetime', 'value': str_value1}, maker1.to_dict(),
        )

        # Errors ---
        with self.assertRaises(ValueError):
            DateTimeMaker.from_dict({})

        with self.assertRaises(ValueError):
            DateTimeMaker.from_dict({'value': True})

        with self.assertRaises(ValueError) as exc_mng1:
            DateTimeMaker.from_dict({'invalid': 'Hi'})
        self.assertEqual(
            'DateTimeMaker: available keys are: value, op',
            str(exc_mng1.exception),
        )

        with self.assertRaises(ValueError) as exc_mng2:
            DateTimeMaker.from_dict({'value': 'not_datetime'})
        self.assertStartsWith(str(exc_mng2.exception), 'DateTimeMaker:')

    def test_datetime__from_dict__now(self):
        with self.assertNoException():
            maker1 = DateTimeMaker.from_dict({'op': 'now'})
        self.assertDatetimesAlmostEqual(now(), maker1.make())
        self.assertDictEqual({'type': 'datetime', 'op': 'now'}, maker1.to_dict())

        # Error ---
        with self.assertRaises(ValueError) as exc_mng:
            DateTimeMaker.from_dict({'op': 'invalid'})
        self.assertEqual(
            'DateTimeMaker: available operator is "now"',
            str(exc_mng.exception),
        )

    def test_registry__empty(self):
        registry = ValueMakerRegistry()

        with self.assertNoLogs():
            self.assertIsInstance(registry.get_maker({}), NoneMaker)

        with self.assertLogs(level='WARNING'):
            self.assertIsInstance(
                registry.get_maker({'type': 'int', 'value': 2}), NoneMaker,
            )

    def test_registry__ok(self):
        registry = ValueMakerRegistry().register(IntegerMaker, BooleanMaker)
        self.assertIsInstance(registry.get_maker({}), NoneMaker)

        int_value = 28
        int_maker = registry.get_maker({'type': 'int', 'value': int_value})
        self.assertIsInstance(int_maker, IntegerMaker)
        self.assertEqual(int_value, int_maker.make())

        bool_maker = registry.get_maker({'type': 'bool', 'value': True})
        self.assertIsInstance(bool_maker, BooleanMaker)
        self.assertEqual(True, bool_maker.make())

    def test_registry__global(self):
        self.assertIsInstance(value_maker_registry, ValueMakerRegistry)
        self.assertIsInstance(
            value_maker_registry.get_maker({'type': 'int', 'value': 42}),
            IntegerMaker,
        )
        self.assertIsInstance(
            value_maker_registry.get_maker({'type': 'bool', 'value': True}),
            BooleanMaker,
        )
