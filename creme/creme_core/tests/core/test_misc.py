# -*- coding: utf-8 -*-

try:
    from datetime import timedelta
    from functools import partial

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.db import models
    from django.test.utils import override_settings
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from ..base import CremeTestCase

    from creme.creme_core.core.batch_process import batch_operator_manager, BatchAction
    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
        EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.core.function_field import FunctionField, FunctionFieldResult, FunctionFieldsManager
    from creme.creme_core.core.imprint import _ImprintManager
    from creme.creme_core.core.job import JobManager
    from creme.creme_core.core.reminder import Reminder, ReminderRegistry, reminder_registry
    from creme.creme_core.core.sandbox import SandboxType, _SandboxTypeRegistry, sandbox_type_registry
    from creme.creme_core.core.setting_key import SettingKey, _SettingKeyRegistry
    from creme.creme_core.creme_jobs import reminder_type
    from creme.creme_core.models import (RelationType, Job, Imprint, Sandbox,
        CustomField, CustomFieldEnumValue, FakeContact, FakeDocument)
    from creme.creme_core.utils.date_period import HoursPeriod
    from creme.creme_core.utils.dates import round_hour
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class FunctionFieldsTestCase(CremeTestCase):
    def test_manager01(self):
        "Constructor with no args, add() & get() methods"
        ffm = FunctionFieldsManager()
        self.assertFalse(list(ffm))

        fname01 = 'name01'
        fname02 = 'name02'

        class TestFunctionField01(FunctionField):
            name         = fname01
            verbose_name = 'Verbose name 01'

        class TestFunctionField02(FunctionField):
            name         = fname02
            verbose_name = 'Verbose name 02'

        ff01 = TestFunctionField01()
        ff02 = TestFunctionField02()

        self.assertIsNone(ffm.get(fname01))

        ffm.add(ff01, ff02)
        self.assertIs(ff01, ffm.get(fname01))
        self.assertIs(ff02, ffm.get(fname02))
        self.assertEqual([ff01, ff02], sorted(ffm, key=lambda ff: ff.name))

    def test_manager02(self):
        "Constructor with args"
        fname01 = 'name01'
        fname02 = 'name02'

        class TestFunctionField01(FunctionField):
            name         = fname01
            verbose_name = 'Verbose name 01'

        class TestFunctionField02(FunctionField):
            name         = fname02
            verbose_name = "Verbose name 02"

        ff01 = TestFunctionField01()
        ff02 = TestFunctionField02()

        ffm = FunctionFieldsManager(ff01, ff02)
        self.assertIs(ff01, ffm.get(fname01))
        self.assertIs(ff02, ffm.get(fname02))
        self.assertEqual([ff01, ff02], sorted(ffm, key=lambda ff: ff.name))

    def test_manager03(self):
        "new() method"
        fname01 = 'name01'
        fname02 = 'name02'

        class TestFunctionField01(FunctionField):
            name         = fname01
            verbose_name = 'Verbose name 01'

        class TestFunctionField02(FunctionField):
            name         = fname02
            verbose_name = 'Verbose name 02'

        ff01 = TestFunctionField01()
        ff02 = TestFunctionField02()

        ffm01 = FunctionFieldsManager(ff01)
        ffm02 = ffm01.new(ff02)

        self.assertIs(ff01, ffm01.get(fname01))
        self.assertIsNone(ffm01.get(fname02))
        self.assertEqual([ff01], list(ffm01))

        self.assertIs(ff01, ffm02.get(fname01))
        self.assertIs(ff02, ffm02.get(fname02))
        self.assertEqual([ff01, ff02], sorted(ffm02, key=lambda ff: ff.name))

    def test_manager04(self):
        "new() method + add() on 'base instance'"
        fname01 = 'name01'
        fname02 = 'name02'

        class TestFunctionField01(FunctionField):
            name         = fname01
            verbose_name = 'Verbose name 01'

        class TestFunctionField02(FunctionField):
            name         = fname02
            verbose_name = 'Verbose name 02'

        ff01 = TestFunctionField01()
        ff02 = TestFunctionField02()

        ffm01 = FunctionFieldsManager()
        ffm02 = ffm01.new(ff02)

        ffm01.add(ff01)  # <== added after new()

        self.assertIs(ff01, ffm01.get(fname01))
        self.assertIsNone(ffm01.get(fname02))
        self.assertEqual([ff01], list(ffm01))

        self.assertIs(ff02, ffm02.get(fname02))
        self.assertIs(ff01, ffm02.get(fname01)) # ok ?
        self.assertEqual([ff01, ff02], sorted(ffm02, key=lambda ff: ff.name))


class BatchOperatorTestCase(CremeTestCase):
    def test_upper(self):
        op = batch_operator_manager.get(models.CharField, 'upper')
        self.assertFalse(op.need_arg)
        self.assertEqual('GALLY', op('gally'))

    def test_lower(self):
        op = batch_operator_manager.get(models.CharField, 'lower')
        self.assertFalse(op.need_arg)
        self.assertEqual('gally', op('GALLY'))

    def test_title(self):
        op = batch_operator_manager.get(models.CharField, 'title')
        self.assertFalse(op.need_arg)
        self.assertEqual('Gally', op('gally'))

    def test_prefix(self):
        op = batch_operator_manager.get(models.CharField, 'prefix')
        self.assertTrue(op.need_arg)
        self.assertEqual('My Gally', op('Gally', 'My '))

    def test_suffix(self):
        op = batch_operator_manager.get(models.CharField, 'suffix')
        self.assertTrue(op.need_arg)
        self.assertEqual('Gally my love', op('Gally', ' my love'))

    def test_remove_substring(self):
        op = batch_operator_manager.get(models.CharField, 'rm_substr')
        self.assertTrue(op.need_arg)
        fieldval = 'Gally the battle angel'
        self.assertEqual('Gally the angel', op(fieldval, 'battle '))
        self.assertEqual(fieldval, op(fieldval, 'evil '))

    def test_remove_start(self):
        op = batch_operator_manager.get(models.CharField, 'rm_start')
        self.assertTrue(op.need_arg)
        self.assertEqual('Gally', op('GGGally', 2))
        self.assertEqual('',      op('Gally',   op.cast('10')))

    def test_remove_end(self):
        op = batch_operator_manager.get(models.CharField, 'rm_end')
        self.assertTrue(op.need_arg)
        self.assertEqual('Gally', op('Gallyyy', 2))
        self.assertEqual('',      op('Gally',   op.cast('10')))

    def test_add_int(self):
        op = batch_operator_manager.get(models.IntegerField, 'add_int')
        self.assertEqual(3, op(1, 2))
        self.assertEqual(5, op(4, op.cast('1')))

    def test_substract_int(self):
        op = batch_operator_manager.get(models.IntegerField, 'sub_int')
        self.assertEqual(1, op(3, 2))
        self.assertEqual(3, op(4, op.cast('1')))

    def test_multiply_int(self):
        op = batch_operator_manager.get(models.IntegerField, 'mul_int')
        self.assertEqual(6, op(3, 2))
        self.assertEqual(8, op(2, op.cast('4')))

    def test_divide_int(self):
        op = batch_operator_manager.get(models.IntegerField, 'div_int')
        self.assertEqual(3, op(6, 2))
        self.assertEqual(2, op(9, op.cast('4')))

    def test_operators01(self):
        ops = {(op_name, unicode(op)) for op_name, op in batch_operator_manager.operators(models.CharField)}
        self.assertIn(('upper', _('To upper case')), ops)
        self.assertIn(('lower', _('To lower case')), ops)
        self.assertNotIn('add_int', (e[0] for e in ops))

    def test_operators02(self):
        ops = {(op_name, unicode(op)) for op_name, op in batch_operator_manager.operators(models.IntegerField)}
        self.assertIn(('add_int', _('Add')), ops)
        self.assertNotIn('prefix', (e[0] for e in ops))

    def test_operators03(self):
        ops = {(op_name, unicode(op)) for op_name, op in batch_operator_manager.operators()}
        self.assertIn(('mul_int', _('Multiply')), ops)
        self.assertIn(('suffix',  _('Suffix')), ops)


class BatchActionTestCase(CremeTestCase):
    def test_changed01(self):
        baction = BatchAction(FakeContact, 'first_name', 'upper', value='')
        haruhi = FakeContact(first_name='Haruhi', last_name='Suzumiya')
        self.assertTrue(baction(haruhi))
        self.assertEqual('HARUHI', haruhi.first_name)

    def test_changed02(self):
        baction = BatchAction(FakeContact, 'last_name', 'rm_substr', value='Foobar')
        first_name = 'Haruhi'
        last_name = 'Suzumiya'
        haruhi = FakeContact(first_name=first_name, last_name=last_name)
        self.assertFalse(baction(haruhi))
        self.assertEqual(last_name,  haruhi.last_name)
        self.assertEqual(first_name, haruhi.first_name)

    def test_cast(self):
        baction = BatchAction(FakeContact, 'last_name', 'rm_start', value='3')
        haruhi = FakeContact(first_name='Haruhi', last_name='Suzumiya')
        baction(haruhi)
        self.assertEqual('umiya', haruhi.last_name)

    def test_null_field(self):
        baction = BatchAction(FakeContact, 'first_name', 'upper', value='')
        haruhi = FakeContact(first_name=None, last_name='Suzumiya')
        self.assertFalse(baction(haruhi))
        self.assertIsNone(haruhi.first_name)

    def test_operand_error(self):
        with self.assertRaises(BatchAction.ValueError) as cm:
            BatchAction(FakeContact, 'last_name', 'rm_start', value='three')  # Not int

        self.assertEqual(_(u'%(operator)s : %(message)s.') % {
                                'operator': _(u'Remove the start (N characters)'),
                                'message':  _(u'enter a whole number'),
                            },
                         unicode(cm.exception)
                        )

        with self.assertRaises(BatchAction.ValueError) as cm:
            BatchAction(FakeContact, 'last_name', 'rm_end', value='-3')  # Not positive

        self.assertEqual(_(u'%(operator)s : %(message)s.') % {
                                'operator': _(u'Remove the end (N characters)'),
                                'message':  _(u'enter a positive number'),
                            },
                         unicode(cm.exception)
                        )

    def test_unicode01(self):
        baction = BatchAction(FakeContact, 'first_name', 'upper', value='')
        self.assertEqual(_(u'%(field)s ➔ %(operator)s') % {
                                'field':    _(u'First name'),
                                'operator': _(u'To upper case'),
                            },
                         unicode(baction)
                        )

    def test_unicode02(self):
        "With argument"
        value = 'Foobarbaz'
        baction = BatchAction(FakeContact, 'last_name', 'rm_substr', value=value)
        self.assertEqual(_(u'%(field)s ➔ %(operator)s: «%(value)s»') % {
                                'field':    _(u'Last name'),
                                'operator': _(u'Remove a sub-string'),
                                'value':    value,
                            },
                         unicode(baction)
                        )


class EntityCellTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super(EntityCellTestCase, cls).setUpClass()

        cls.contact_ct = ContentType.objects.get_for_model(FakeContact)

    def test_build_4_field01(self):
        field_name = 'first_name'
        cell = EntityCellRegularField.build(model=FakeContact, name=field_name)
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_name,      cell.value)
        self.assertEqual(_(u'First name'), cell.title)
        self.assertIs(cell.has_a_filter, True)
        self.assertIs(cell.editable, True)
        self.assertIs(cell.sortable, True)
        self.assertIs(cell.is_multiline, False)
        self.assertEqual('first_name__icontains', cell.filter_string)

    def test_build_4_field02(self):
        "Date field"
        cell = EntityCellRegularField.build(model=FakeContact, name='birthday')
        self.assertEqual('birthday__range', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_field03(self):
        "Boolean field"
        cell = EntityCellRegularField.build(model=FakeContact, name='is_a_nerd')
        self.assertEqual('is_a_nerd__creme-boolean', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

    def test_build_4_field04(self):
        "ForeignKey"
        cell = EntityCellRegularField.build(model=FakeContact, name='position')
        self.assertEqual('position', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

        cell = EntityCellRegularField.build(model=FakeContact, name='image')
        self.assertEqual('image__header_filter_search_field__icontains',
                         cell.filter_string
                        )
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

    def test_build_4_field05(self):
        "Basic ForeignKey subfield"
        cell = EntityCellRegularField.build(model=FakeContact, name='position__title')
        self.assertEqual('position__title__icontains', cell.filter_string)

        cell = EntityCellRegularField.build(model=FakeContact, name='image__name')
        self.assertEqual('image__name__icontains', cell.filter_string)

    def test_build_4_field06(self):
        "Date ForeignKey subfield"
        cell = EntityCellRegularField.build(model=FakeContact, name='image__created')
        self.assertEqual(u'%s - %s' % (_('Photograph'), _('Creation date')), cell.title)
        self.assertEqual('image__created__range', cell.filter_string)

    def test_build_4_field07(self):
        "ForeignKey subfield is a FK"
        cell = EntityCellRegularField.build(model=FakeDocument, name='linked_folder__category')

        self.assertTrue(cell.has_a_filter)
        self.assertEqual('linked_folder__category', cell.filter_string)

    def test_build_4_field08(self):
        "ManyToMany"
        cell = EntityCellRegularField.build(model=FakeContact, name='languages')
        self.assertTrue(cell.has_a_filter)
        self.assertFalse(cell.sortable)
        self.assertTrue(cell.is_multiline)
        self.assertEqual('languages', cell.filter_string)

        cell = EntityCellRegularField.build(model=FakeContact, name='languages__name')
        self.assertTrue(cell.has_a_filter)
        self.assertFalse(cell.sortable)
        self.assertTrue(cell.is_multiline)
        self.assertEqual('languages__name__icontains', cell.filter_string)

    def test_build_4_field_errors(self):
        build = partial(EntityCellRegularField.build, model=FakeContact)
        self.assertIsNone(build(name='unknown_field'))
        self.assertIsNone(build(name='user__unknownfield'))

    def test_build_4_customfield01(self):
        "INT CustomField"
        name = u'Size (cm)'
        customfield = CustomField.objects.create(name=name, field_type=CustomField.INT,
                                                 content_type=self.contact_ct
                                                )

        cell = EntityCellCustomField(customfield)
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(str(customfield.id), cell.value)
        self.assertEqual(name,                cell.title)
        self.assertIs(cell.has_a_filter, True)
        self.assertIs(cell.editable,     False)
        self.assertIs(cell.sortable,     False)
        self.assertIs(cell.is_multiline, False)
        self.assertEqual('customfieldinteger__value__icontains', cell.filter_string)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,           cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW,   cell.header_listview_css_class)

        cell = EntityCellCustomField.build(FakeContact, customfield.id)
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(str(customfield.id), cell.value)

        self.assertIsNone(EntityCellCustomField.build(FakeContact, 1000))

    def test_build_4_customfield02(self):
        "FLOAT CustomField"
        customfield = CustomField.objects.create(name=u'Weight', field_type=CustomField.FLOAT,
                                                 content_type=self.contact_ct
                                                )

        cell = EntityCellCustomField(customfield)
        self.assertEqual('customfieldfloat__value__icontains', cell.filter_string)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,         cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_customfield03(self):
        "DATE CustomField"
        customfield = CustomField.objects.create(name=u'Day', field_type=CustomField.DATETIME,
                                                 content_type=self.contact_ct
                                                )

        cell = EntityCellCustomField(customfield)
        self.assertEqual('customfielddatetime__value__range', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_customfield04(self):
        "BOOL CustomField"
        customfield = CustomField.objects.create(name=u'Is fun ?', field_type=CustomField.BOOL,
                                                 content_type=self.contact_ct
                                                )

        cell = EntityCellCustomField(customfield)
        self.assertEqual('customfieldboolean__value__creme-boolean', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_customfield05(self):
        "ENUM CustomField"
        customfield = CustomField.objects.create(name='Eva', field_type=CustomField.ENUM,
                                                 content_type=self.contact_ct
                                                )

        create_enumvalue = partial(CustomFieldEnumValue.objects.create, custom_field=customfield)
        create_enumvalue(value='Eva-00')
        create_enumvalue(value='Eva-01')

        cell = EntityCellCustomField(customfield)
        self.assertEqual('customfieldenum__value__exact',      cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_customfield06(self):
        "MULTI_ENUM CustomField"
        customfield = CustomField.objects.create(name='Eva', field_type=CustomField.MULTI_ENUM,
                                                 content_type=self.contact_ct
                                                )

        create_enumvalue = partial(CustomFieldEnumValue.objects.create, custom_field=customfield)
        create_enumvalue(value='Eva-00')
        create_enumvalue(value='Eva-01')

        cell = EntityCellCustomField(customfield)
        self.assertEqual('customfieldmultienum__value__exact', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_relation(self):
        loves = RelationType.create(('test-subject_love', u'Is loving'),
                                    ('test-object_love',  u'Is loved by')
                                   )[0]
        cell = EntityCellRelation(model=FakeContact, rtype=loves)
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(FakeContact,     cell.model)
        self.assertEqual(str(loves.id),   cell.value)
        self.assertEqual(loves.predicate, cell.title)
        self.assertIs(cell.has_a_filter, True)
        self.assertIs(cell.editable,     False)
        self.assertIs(cell.sortable,     False)
        self.assertIs(cell.is_multiline, True)
        self.assertEqual('',    cell.filter_string)
        self.assertEqual(loves, cell.relation_type)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_functionfield01(self):
        name = 'get_pretty_properties'
        funfield = FakeContact.function_fields.get(name)
        self.assertIsNotNone(funfield)

        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(name,            cell.value)
        self.assertEqual(unicode(funfield.verbose_name), cell.title)
        self.assertIs(cell.has_a_filter, True)  # TODO: test with a non-filterable FunctionField
        self.assertIs(cell.editable,     False)
        self.assertIs(cell.sortable,     False)
        self.assertIs(cell.is_hidden,    False)
        self.assertIs(cell.is_multiline, True)
        self.assertEqual('', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        cell = EntityCellFunctionField.build(FakeContact, func_field_name=name)
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(name, cell.value)

        self.assertIsNone(EntityCellFunctionField.build(FakeContact, func_field_name='invalid'))

    def test_build_4_functionfield02(self):
        class PhoneFunctionField(FunctionField):
            name         = 'phone_or_mobile'
            verbose_name = 'Phone or mobile'

            def __call__(self, entity, user):
                return FunctionFieldResult(entity.phone or entity.mobile)

        funfield = PhoneFunctionField()
        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)
        self.assertEqual(funfield.name,         cell.value)
        self.assertEqual(funfield.verbose_name, cell.title)
        self.assertFalse(cell.is_multiline)


class SettingKeyTestCase(CremeTestCase):
    def test_01(self):
        sk1 = SettingKey('creme_core-test_sk_string',
                         description=u'Page title',
                         app_label='creme_core',
                         type=SettingKey.STRING,
                         blank=True,
                        )
        sk2 = SettingKey('creme_core-test_sk_int',
                         description=u'Page size',
                         app_label='creme_core',
                         type=SettingKey.INT, hidden=False,
                        )
        sk3 = SettingKey('creme_core-test_sk_bool',
                         description=u'Page hidden',
                         app_label='creme_core',
                         type=SettingKey.BOOL,
                        )

        registry = _SettingKeyRegistry()
        registry.register(sk1, sk2, sk3)

        # ------
        with self.assertNoException():
            sk = registry[sk1.id]
        self.assertEqual(sk1, sk)

        self.assertEqual(sk2, registry[sk2.id])
        self.assertEqual(sk3, registry[sk3.id])

        # ------
        all_key_ids = {sk.id for sk in registry}
        self.assertIn(sk1.id, all_key_ids)
        self.assertIn(sk2.id, all_key_ids)
        self.assertIn(sk3.id, all_key_ids)

        # ------
        registry.unregister(sk1, sk3)

        self.assertEqual(sk2, registry[sk2.id])

        with self.assertRaises(KeyError):
            registry[sk1.id]

        with self.assertRaises(KeyError):
            registry[sk3.id]

        all_key_ids = {sk.id for sk in registry}
        self.assertIn(sk2.id, all_key_ids)
        self.assertNotIn(sk1.id, all_key_ids)
        self.assertNotIn(sk3.id, all_key_ids)

        with self.assertNoException():
            registry.unregister(sk3)


class ReminderTestCase(CremeTestCase):
    def test_empty(self):
        registry = ReminderRegistry()

        self.assertFalse(list(registry))
        self.assertFalse(list(registry.itervalues()))

    # def test_register_legacy(self):
    #     registry = ReminderRegistry()
    #
    #     class TestReminder1(Reminder):
    #         id = Reminder.generate_id('creme_core', 'ReminderTestCase_test_register_legacy_1')
    #
    #     class TestReminder2(Reminder):
    #         id = Reminder.generate_id('creme_core', 'ReminderTestCase_test_register_legacy_2')
    #
    #     reminder1 = TestReminder1()
    #     reminder2 = TestReminder2()
    #     registry.register(reminder1)
    #     registry.register(reminder2)
    #     self.assertEqual({(reminder1.id, reminder1),
    #                       (reminder2.id, reminder2),
    #                      },
    #                      set(registry)
    #                     )
    #     self.assertEqual({reminder1, reminder2}, set(registry.itervalues()))
    #
    #     # --
    #     registry.unregister(reminder1)
    #     self.assertEqual([reminder2], list(registry.itervalues()))
    #
    #     with self.assertNoException():
    #         registry.unregister(reminder1)

    def test_register(self):
        registry = ReminderRegistry()

        class TestReminder1(Reminder):
            id = Reminder.generate_id('creme_core', 'ReminderTestCase_test_register_1')

        class TestReminder2(Reminder):
            id = Reminder.generate_id('creme_core', 'ReminderTestCase_test_register_2')

        registry.register(TestReminder1)
        registry.register(TestReminder2)

        items = dict(registry)
        self.assertEqual(2, len(items))
        self.assertIsInstance(items[TestReminder1.id], TestReminder1)
        self.assertIsInstance(items[TestReminder2.id], TestReminder2)

        self.assertEqual({TestReminder1, TestReminder2},
                         {r.__class__ for r in registry.itervalues()}
                        )

        # --
        registry.unregister(TestReminder1)
        self.assertEqual([TestReminder2],
                         [r.__class__ for r in registry.itervalues()]
                        )

        with self.assertNoException():
            registry.unregister(TestReminder1)


class JobManagerTestCase(CremeTestCase):
    def setUp(self):
        super(JobManagerTestCase, self).setUp()
        self.reminders = []

    def tearDown(self):
        super(JobManagerTestCase, self).tearDown()

        for reminder in self.reminders:
            reminder_registry.unregister(reminder)

    def _register_reminder(self, reminder):
        reminder_registry.register(reminder)
        self.reminders.append(reminder)

    @override_settings(PSEUDO_PERIOD=1)
    def test_next_wake_up01(self):
        "PSEUDO_PERIODIC job"
        rounded_hour = round_hour(now())
        job = Job.objects.get(type_id=reminder_type.id)

        # self.assertEqual(rounded_hour, job.reference_run)
        if job.reference_run != rounded_hour:
            job.reference_run = rounded_hour
            job.save()

        self.assertEqual(HoursPeriod(value=1), job.real_periodicity)

        next_wakeup = JobManager()._next_wakeup

        next_hour = rounded_hour + timedelta(hours=1)
        self.assertEqual(next_hour, next_wakeup(job))

        job.reference_run = rounded_hour - timedelta(hours=1)  # should not be used because "rounded_hour" is given
        self.assertEqual(next_hour, next_wakeup(job, reference_run=rounded_hour))

    @override_settings(PSEUDO_PERIOD=1)
    def test_next_wake_up02(self):
        "PSEUDO_PERIODIC job + reminder return a wake up date before the new security period"
        rounded_hour = round_hour(now())
        job = Job.objects.get(type_id=reminder_type.id)

        wake_up = rounded_hour + timedelta(minutes=20)

        class TestReminder(Reminder):
            id = Reminder.generate_id('creme_core', 'test_jobmanager_1')

            def next_wakeup(self, now_value):
                return wake_up

        # self._register_reminder(TestReminder())
        self._register_reminder(TestReminder)
        self.assertEqual(wake_up, JobManager()._next_wakeup(job))

    @override_settings(PSEUDO_PERIOD=1)
    def test_next_wake_up03(self):
        "PSEUDO_PERIODIC job + reminder return a wake up date after the new security period"
        rounded_hour = round_hour(now())
        job = Job.objects.get(type_id=reminder_type.id)

        class TestReminder(Reminder):
            id = Reminder.generate_id('creme_core', 'test_jobmanager_2')

            def next_wakeup(self, now_value):
                return rounded_hour + timedelta(minutes=70)

        # self._register_reminder(TestReminder())
        self._register_reminder(TestReminder)

        self.assertEqual(rounded_hour + timedelta(hours=1),
                         JobManager()._next_wakeup(job)
                        )


class SandboxTestCase(CremeTestCase):
    def test_registry01(self):
        name = 'Test sandbox #1'

        class TestSandboxType1(SandboxType):
            id = SandboxType.generate_id('creme_core', 'test1')
            verbose_name = name

        sandbox_type_registry.register(TestSandboxType1)  # TODO: unregister in tearDown ?

        sandbox = Sandbox(type_id=TestSandboxType1.id)

        st_type = sandbox.type
        self.assertIsInstance(st_type, TestSandboxType1)
        self.assertEqual(name, st_type.verbose_name)

    def test_registry02(self):
        registry = _SandboxTypeRegistry()

        st_id = SandboxType.generate_id('creme_core', 'test2')

        class TestSandboxType2_2(SandboxType):
            id = st_id
            verbose_name = 'Test sandbox #2'

        class TestSandboxType2_3(SandboxType):
            id = st_id
            verbose_name = 'Test sandbox #3'

        registry.register(TestSandboxType2_2)

        with self.assertRaises(_SandboxTypeRegistry.Error):
            registry.register(TestSandboxType2_3)

        sandbox1 = Sandbox(type_id=TestSandboxType2_2.id)
        self.assertIsInstance(registry.get(sandbox1), TestSandboxType2_2)

        class TestSandboxType2_4(SandboxType):  # Not registered
            id = SandboxType.generate_id('creme_core', 'unknown')
            verbose_name = 'Test sandbox #4'

        sandbox2 = Sandbox(type_id=TestSandboxType2_4.id)
        # TODO: assertLogs
        self.assertIsNone(registry.get(sandbox2))

    def test_sandbox_data(self):
        user = self.login()
        fmt = u'Restricted to "{}"'

        class TestSandboxType3(SandboxType):
            id = SandboxType.generate_id('creme_core', 'test3')

            @property
            def verbose_name(self):
                return fmt.format(self.sandbox.user)

        sandbox_type_registry.register(TestSandboxType3)  # TODO: unregister in tearDown ?

        sandbox = Sandbox(type_id=TestSandboxType3.id, user=user)
        self.assertEqual(fmt.format(user), sandbox.type.verbose_name)


class ImprintManagerTestCase(CremeTestCase):
    def test_register_n_get(self):
        manager = _ImprintManager()
        self.assertIsNone(manager.get_granularity(FakeContact))

        manager.register(FakeContact, minutes=60)
        self.assertEqual(timedelta(minutes=60), manager.get_granularity(FakeContact))

        manager.register(FakeDocument, hours=2)
        self.assertEqual(timedelta(hours=2), manager.get_granularity(FakeDocument))

    def test_double_registering(self):
        manager = _ImprintManager()
        manager.register(FakeContact, minutes=60)

        with self.assertRaises(manager.RegistrationError):
            manager.register(FakeContact, minutes=90)

    def test_create01(self):
        manager = _ImprintManager()
        manager.register(FakeContact, minutes=60)

        user = self.login()
        willy = FakeContact.objects.create(user=user, first_name='Willy', last_name='Wonka')
        self.assertFalse(Imprint.objects.all())

        imprint = manager.create_imprint(entity=willy, user=user)
        self.assertIsInstance(imprint, Imprint)
        self.assertIsNotNone(imprint.id)
        self.assertDatetimesAlmostEqual(now(), imprint.date)
        self.assertEqual(imprint.entity.get_real_entity(), willy)
        self.assertEqual(imprint.user, user)

    def test_create02(self):
        "Delay is not passed"
        manager = _ImprintManager()
        manager.register(FakeContact, minutes=60)

        user = self.login()
        willy = FakeContact.objects.create(user=user, first_name='Willy', last_name='Wonka')

        imprint1 = Imprint.objects.create(entity=willy, user=user)
        self.assertIsNone(manager.create_imprint(entity=willy, user=user))

        # Other entity
        charlie = FakeContact.objects.create(user=user, first_name='Charlie', last_name='Bucket')
        self.assertIsNotNone(manager.create_imprint(entity=charlie, user=user))

        # Other user
        other_user = self.other_user
        imprint3 = manager.create_imprint(entity=willy, user=other_user)
        self.assertIsNotNone(imprint3)
        self.assertEqual(imprint3.user, other_user)

        # With older imprint
        Imprint.objects.filter(id=imprint1.id).update(date=now() - timedelta(minutes=59))
        self.assertIsNone(manager.create_imprint(entity=willy, user=user))

    def test_create03(self):
        "Delay_is passed"
        manager = _ImprintManager()
        manager.register(FakeContact, minutes=30)

        user = self.login()
        willy = FakeContact.objects.create(user=user, first_name='Willy', last_name='Wonka')

        imprint1 = Imprint.objects.create(entity=willy, user=user)
        Imprint.objects.filter(id=imprint1.id).update(date=now() - timedelta(minutes=31))

        self.assertIsNotNone(manager.create_imprint(entity=willy, user=user))

    def test_create04(self):
        "Model not registered"
        manager = _ImprintManager()
        manager.register(FakeDocument, minutes=60)

        user = self.login()
        willy = FakeContact.objects.create(user=user, first_name='Willy', last_name='Wonka')

        self.assertIsNone(manager.create_imprint(entity=willy, user=user))
