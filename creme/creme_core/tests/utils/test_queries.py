from datetime import date
from functools import partial

from django.core.serializers.base import SerializationError
from django.db.models import Q
from django.utils.translation import override as override_language

from creme.creme_core.utils.queries import QSerializer

from ..base import CremeTestCase
from ..fake_models import (
    FakeActivity,
    FakeActivityType,
    FakeCivility,
    FakeContact,
    FakeOrganisation,
    FakePosition,
)


class QSerializerTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._civ_backup = [*FakeCivility.objects.all()]
        FakeCivility.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        FakeCivility.objects.all().delete()
        FakeCivility.objects.bulk_create(cls._civ_backup)

    def _assertQEqual(self, model, q1, q2):
        self.assertListEqual(
            [*model.objects.filter(q1)],
            [*model.objects.filter(q2)],
        )

    def _assertQIsOK(self, q, entities, model=None):
        model = model or entities[0].__class__
        self.assertQuerySetEqual(
            model.objects.filter(q), entities, transform=lambda e: e,
        )

    @staticmethod
    def _create_activity_type():
        return FakeActivityType.objects.create(name='Tournament')

    def _create_contacts(self):
        create_pos = FakePosition.objects.create
        self.baker   = create_pos(title='Baker')
        self.boxer   = create_pos(title='Boxer')
        self.fighter = create_pos(title='Fighter')

        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
        self.adrian = create_contact(
            first_name='Adrian', last_name='Velba',
            birthday=date(year=2003, month=3, day=5),
            position=self.fighter,
        )
        self.marianne = create_contact(
            first_name='Marianne', last_name='Velba',
            birthday=date(year=1994, month=6, day=17),
            position=self.baker,
        )
        self.richard = create_contact(
            first_name='Richard',  last_name='Aldana',
            position=self.boxer,
        )

    def test_simple_charfield(self):
        self._create_contacts()

        q1 = Q(last_name=self.adrian.last_name)
        self._assertQIsOK(q1, [self.adrian, self.marianne])

        str_q = QSerializer().dumps(q1)
        self.assertIsInstance(str_q, str)

        q2 = QSerializer().loads(str_q)
        self.assertIsInstance(q2, Q)
        self._assertQEqual(FakeContact, q1, q2)

    def test_two_conditions(self):
        "2 conditions + operator."
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        adrian = create_contact(first_name='Adrian', last_name='Velbà')
        create_contact(first_name='Marianne', last_name='Velbà')
        create_contact(first_name='Richard',  last_name='Aldana')

        q1 = Q(last_name=adrian.last_name, first_name__startswith='Ad')
        self._assertQIsOK(q1, [adrian])

        str_q = QSerializer().dumps(q1)
        self.assertIsInstance(str_q, str)

        q2 = QSerializer().loads(str_q)
        self.assertIsInstance(q2, Q)
        self._assertQEqual(FakeContact, q1, q2)

    def test_and(self):
        self._create_contacts()

        q = Q(last_name=self.adrian.last_name) & Q(first_name__startswith='Ad')
        self._assertQIsOK(q, [self.adrian])

        str_q = QSerializer().dumps(q)
        self._assertQEqual(FakeContact, q, QSerializer().loads(str_q))

    def test_or(self):
        self._create_contacts()

        q = Q(first_name=self.adrian.first_name) | Q(first_name__startswith='Ric')
        self._assertQIsOK(q, [self.richard, self.adrian])

        str_q = QSerializer().dumps(q)
        self._assertQEqual(FakeContact, q, QSerializer().loads(str_q))

    def test_not(self):
        self._create_contacts()

        q = ~Q(first_name=self.adrian.first_name) & Q(last_name=self.adrian.last_name)
        self._assertQIsOK(q, [self.marianne])

        str_q = QSerializer().dumps(q)
        self._assertQEqual(FakeContact, q, QSerializer().loads(str_q))

    def _aux_test_date_field(self):
        self._create_contacts()

        q = Q(birthday__gt=date(year=2000, month=1, day=1))
        self._assertQIsOK(q, [self.adrian])

        str_q = QSerializer().dumps(q)
        self._assertQEqual(FakeContact, q, QSerializer().loads(str_q))

    @override_language('en')
    def test_date_field__en(self):
        self._aux_test_date_field()

    @override_language('fr')
    def test_date_field__fr(self):
        self._aux_test_date_field()

    def _aux_test_datetime_field(self):
        user = self.get_root_user()

        create_dt = partial(self.create_datetime, year=2015, month=2, minute=0)
        create_act = partial(
            FakeActivity.objects.create,
            user=user, type=self._create_activity_type()
        )
        acts = [
            create_act(title='T#1', start=create_dt(day=19, hour=8)),
            create_act(title='T#2', start=create_dt(day=19, hour=12)),
        ]

        q = Q(start__lt=create_dt(day=19, hour=9))
        self._assertQIsOK(q, [acts[0]])

        str_q = QSerializer().dumps(q)
        self._assertQEqual(FakeActivity, q, QSerializer().loads(str_q))

    @override_language('en')
    def test_datetime_field__en(self):
        self._aux_test_datetime_field()

    @override_language('fr')
    def test_datetime_field__fr(self):
        self._aux_test_datetime_field()

    def test_range_integer(self):
        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        create_orga(name='Vallée des rois',     capital=15000)
        o2 = create_orga(name='Paxtown',        capital=5000)
        create_orga(name='Zotis incorporation', capital=200)

        q = Q(capital__range=[1000, 10000])
        self._assertQIsOK(q, [o2])

        str_q = QSerializer().dumps(q)
        self._assertQEqual(FakeOrganisation, q, QSerializer().loads(str_q))

    def test_range_datetime(self):
        user = self.get_root_user()

        create_dt = partial(self.create_datetime, year=2015, month=2, minute=0)
        create_act = partial(
            FakeActivity.objects.create,
            user=user, type=self._create_activity_type()
        )
        acts = [
            create_act(title='T#1', start=create_dt(day=18, hour=8)),
            create_act(title='T#2', start=create_dt(day=19, hour=8)),
            create_act(title='T#3', start=create_dt(day=20, hour=8)),
        ]

        q = Q(
            start__range=(
                create_dt(day=18, hour=9),
                create_dt(day=19, hour=9),
            ),
        )
        self._assertQIsOK(q, [acts[1]])

        str_q = QSerializer().dumps(q)
        # print(str_q)
        self._assertQEqual(FakeActivity, q, QSerializer().loads(str_q))

    def test_fk(self):
        "Value is a model instance."
        self._create_contacts()

        q = Q(position=self.baker)
        self._assertQIsOK(q, [self.marianne])

        qsr = QSerializer()
        str_q = qsr.dumps(q)
        self._assertQEqual(FakeContact, q, qsr.loads(str_q))

    def test_range_fk(self):
        "__in=[...] + model instance."
        self._create_contacts()

        q = Q(position__in=[self.boxer, self.fighter])
        self._assertQIsOK(q, [self.richard, self.adrian])

        qsr = QSerializer()
        str_q = qsr.dumps(q)
        self._assertQEqual(FakeContact, q, qsr.loads(str_q))

    def test_error_subqueryset(self):
        "__in=QuerySet -> error."
        self._create_contacts()

        q = Q(position__in=FakePosition.objects.filter(title__startswith='B'))
        self._assertQIsOK(q, [self.richard, self.marianne])

        qsr = QSerializer()
        self.assertRaises(SerializationError, qsr.dumps, q)

        q = Q(
            position__in=FakePosition.objects
                                     .filter(title__startswith='B')
                                     .values_list('id', flat=True),
        )
        self._assertQIsOK(q, [self.richard, self.marianne])
        self.assertRaises(SerializationError, qsr.dumps, q)
