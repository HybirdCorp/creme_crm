# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.core.deletion import (
    REPLACERS_MAP,
    FixedValueReplacer,
    SETReplacer,
)
from creme.creme_core.models import (
    FakeCivility,
    FakeContact,
    FakeDocument,
    FakeDocumentCategory,
    FakeOrganisation,
    FakeSector,
    FakeTicket,
    FakeTicketPriority,
)

from ..base import CremeTestCase


class DeletionTestCase(CremeTestCase):
    def test_replacer_by_fixed_value01(self):
        civ = FakeCivility.objects.create(title='Kun')

        model_field = FakeContact._meta.get_field('civility')
        replacer1 = FixedValueReplacer(model_field=model_field, value=civ)
        self.assertEqual(model_field, replacer1.model_field)
        self.assertEqual(civ, replacer1._fixed_value)

        serialized = {
            'ctype': ContentType.objects.get_for_model(FakeContact).natural_key(),
            'field': 'civility',
            'pk':    civ.pk,
        }
        self.assertEqual(serialized, replacer1.as_dict())

        replacer2 = FixedValueReplacer.from_dict(serialized)
        self.assertIsInstance(replacer2, FixedValueReplacer)
        self.assertEqual(model_field,    replacer2.model_field)
        self.assertEqual(civ,            replacer2.get_value())

        self.assertEqual(
            _('In «{model} - {field}», replace by «{new}»').format(
                model='Test Contact',
                field=_('Civility'),
                new=civ.title,
            ),
            str(replacer1),
        )

    def test_replacer_by_fixed_value02(self):
        "<None> value + other ContentType."
        model_field = FakeOrganisation._meta.get_field('sector')
        replacer1 = FixedValueReplacer(model_field=model_field, value=None)

        serialized = {
            'ctype': ContentType.objects.get_for_model(FakeOrganisation).natural_key(),
            'field': 'sector',
        }
        self.assertEqual(serialized, replacer1.as_dict())

        replacer2 = FixedValueReplacer.from_dict(serialized)
        self.assertIsInstance(replacer2, FixedValueReplacer)
        self.assertEqual(model_field, replacer2.model_field)
        self.assertIsNone(replacer2.get_value())

        self.assertEqual(
            _('Empty «{model} - {field}»').format(
                model='Test Organisation',
                field=_('Sector'),
            ),
            str(replacer1),
        )

    def test_replacer_by_fixed_value03(self):
        "Explicit & implicit values."
        self.assertEqual(
            _('Empty «{model} - {field}»').format(
                model='Test Contact',
                field=_('Civility'),
            ),
            str(FixedValueReplacer(
                model_field=FakeContact._meta.get_field('civility')
            )),
        )

        sector = FakeSector.objects.create(title='Ninja')
        self.assertEqual(
            _('In «{model} - {field}», replace by «{new}»').format(
                model='Test Organisation',
                field=_('Sector'),
                new=sector.title,
            ),
            str(FixedValueReplacer(
                model_field=FakeOrganisation._meta.get_field('sector'),
                value=sector,
            ))
        )

    def test_replacer_by_fixed_value04(self):
        "ManyToMany."
        cat = FakeDocumentCategory.objects.create(name='PNGs')
        m2m = FakeDocument._meta.get_field('categories')

        self.assertEqual(
            _('In «{model} - {field}», replace by «{new}»').format(
                model='Test Document',
                field=_('Categories'),
                new=cat.name,
            ),
            str(FixedValueReplacer(model_field=m2m, value=cat)),
        )

        self.assertEqual(
            _('Remove from «{model} - {field}»').format(
                model='Test Document',
                field=_('Categories'),
            ),
            str(FixedValueReplacer(model_field=m2m)),
        )

    def test_replacer_for_SET(self):
        self.assertFalse(FakeTicketPriority.objects.filter(name='Deleted'))

        model_field = FakeTicket._meta.get_field('priority')
        replacer1 = SETReplacer(model_field=model_field)
        self.assertEqual(model_field, replacer1.model_field)

        value = replacer1.get_value()
        self.assertIsInstance(value, FakeTicketPriority)
        self.assertEqual('Deleted', value.name)

        serialized = {
            'ctype': ContentType.objects.get_for_model(FakeTicket).natural_key(),
            'field': 'priority',
        }
        self.assertEqual(serialized, replacer1.as_dict())

        replacer2 = SETReplacer.from_dict(serialized)
        self.assertIsInstance(replacer2, SETReplacer)
        self.assertEqual(model_field,    replacer2.model_field)
        self.assertEqual(value,          replacer2.get_value())

        self.assertEqual(
            _('In «{model} - {field}», replace by a fallback value').format(
                model='Test Ticket',
                field=_('Priority'),
            ),
            str(replacer1),
        )

    def test_registry01(self):
        "FixedValueReplacer."
        sector = FakeSector.objects.first()

        field1 = FakeOrganisation._meta.get_field('sector')
        field2 = FakeContact._meta.get_field('sector')
        replacer1 = FixedValueReplacer(model_field=field1, value=None)
        replacer2 = FixedValueReplacer(model_field=field2, value=sector)

        get_ct = ContentType.objects.get_for_model
        serialized = [
            [
                'fixed_value',
                {
                    'ctype': get_ct(FakeOrganisation).natural_key(),
                    'field': 'sector',
                },
            ], [
                'fixed_value',
                {
                    'ctype': get_ct(FakeContact).natural_key(),
                    'field': 'sector',
                    'pk': sector.pk,
                },
            ],
        ]
        self.assertEqual(
            serialized,
            REPLACERS_MAP.serialize([replacer1, replacer2])
        )

        replacers = REPLACERS_MAP.deserialize(serialized)
        self.assertIsList(replacers, length=2)

        d_replacer1 = replacers[0]
        self.assertIsInstance(d_replacer1, FixedValueReplacer)
        self.assertEqual(field1, d_replacer1.model_field)
        self.assertIsNone(d_replacer1.get_value())

        d_replacer2 = replacers[1]
        self.assertIsInstance(d_replacer2, FixedValueReplacer)
        self.assertEqual(field2, d_replacer2.model_field)
        self.assertEqual(sector, d_replacer2.get_value())

    def test_registry02(self):
        "SETReplacer."
        field = FakeTicket._meta.get_field('priority')
        replacer = SETReplacer(model_field=field)

        serialized = [
            [
                'SET',
                {
                    'ctype': ContentType.objects.get_for_model(FakeTicket).natural_key(),
                    'field': 'priority',
                },
            ],
        ]
        self.assertEqual(serialized, REPLACERS_MAP.serialize([replacer]))

        replacers = REPLACERS_MAP.deserialize(serialized)
        self.assertIsList(replacers, length=1)

        d_replacer = replacers[0]
        self.assertIsInstance(d_replacer, SETReplacer)
        self.assertEqual(field, d_replacer.model_field)
