# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.db import models
    from django.utils.translation import ugettext as _

    from creme.creme_core.core.function_field import FunctionField, FunctionFieldsManager
    from creme.creme_core.core.batch_process import batch_operator_manager, BatchAction
    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.models import RelationType, CustomField, CustomFieldEnumValue
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('FunctionFieldsTestCase', 'BatchOperatorTestCase',
           'BatchActionTestCase', 'EntityCellTestCase')


class FunctionFieldsTestCase(CremeTestCase):
    def test_manager01(self): #constructor with no args, add() & get() methods
        ffm = FunctionFieldsManager()
        self.assertFalse(list(ffm))

        fname01 = "name01"
        fname02 = "name02"

        class TestFunctionField01(FunctionField):
            name         = fname01
            verbose_name = "Verbose name 01"

        class TestFunctionField02(FunctionField):
            name         = fname02
            verbose_name = "Verbose name 02"

        ff01 = TestFunctionField01()
        ff02 = TestFunctionField02()

        self.assertIsNone(ffm.get(fname01))

        ffm.add(ff01, ff02)
        self.assertIs(ff01, ffm.get(fname01))
        self.assertIs(ff02, ffm.get(fname02))
        self.assertEqual([ff01, ff02], sorted(ffm, key=lambda ff: ff.name))

    def test_manager02(self): #constructor with args
        fname01 = "name01"
        fname02 = "name02"

        class TestFunctionField01(FunctionField):
            name         = fname01
            verbose_name = "Verbose name 01"

        class TestFunctionField02(FunctionField):
            name         = fname02
            verbose_name = "Verbose name 02"

        ff01 = TestFunctionField01()
        ff02 = TestFunctionField02()

        ffm = FunctionFieldsManager(ff01, ff02)
        self.assertIs(ff01, ffm.get(fname01))
        self.assertIs(ff02, ffm.get(fname02))
        self.assertEqual([ff01, ff02], sorted(ffm, key=lambda ff: ff.name))

    def test_manager03(self): #new() method
        fname01 = "name01"
        fname02 = "name02"

        class TestFunctionField01(FunctionField):
            name         = fname01
            verbose_name = "Verbose name 01"

        class TestFunctionField02(FunctionField):
            name         = fname02
            verbose_name = "Verbose name 02"

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

    def test_manager04(self): #new() method + add() on "base instance"
        fname01 = "name01"
        fname02 = "name02"

        class TestFunctionField01(FunctionField):
            name         = fname01
            verbose_name = "Verbose name 01"

        class TestFunctionField02(FunctionField):
            name         = fname02
            verbose_name = "Verbose name 02"

        ff01 = TestFunctionField01()
        ff02 = TestFunctionField02()

        ffm01 = FunctionFieldsManager()
        ffm02 = ffm01.new(ff02)

        ffm01.add(ff01) # <== added after new()

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
        baction = BatchAction(Contact, 'first_name', 'upper', value='')
        haruhi = Contact(first_name='Haruhi', last_name='Suzumiya')
        self.assertTrue(baction(haruhi))
        self.assertEqual('HARUHI', haruhi.first_name)

    def test_changed02(self):
        baction = BatchAction(Organisation, 'name', 'rm_substr', value='Foobar')
        name = 'SOS no Dan'
        sos = Organisation(name=name)
        self.assertFalse(baction(sos))
        self.assertEqual(name, sos.name)

    def test_cast(self):
        baction = BatchAction(Contact, 'last_name', 'rm_start', value='3')
        haruhi = Contact(first_name='Haruhi', last_name='Suzumiya')
        baction(haruhi)
        self.assertEqual('umiya', haruhi.last_name)

    def test_null_field(self):
        baction = BatchAction(Contact, 'first_name', 'upper', value='')
        haruhi = Contact(first_name=None, last_name='Suzumiya')
        self.assertFalse(baction(haruhi))
        self.assertIsNone(haruhi.first_name)

    def test_operand_error(self):
        with self.assertRaises(BatchAction.ValueError) as cm:
            BatchAction(Contact, 'last_name', 'rm_start', value='three') #not int

        self.assertEqual(_('%(operator)s : %(message)s.') % {
                                'operator': _('Remove the start (N characters)'),
                                'message':  _('enter a whole number'),
                            },
                         unicode(cm.exception)
                        )

        with self.assertRaises(BatchAction.ValueError) as cm:
            BatchAction(Contact, 'last_name', 'rm_end', value='-3') #not positive

        self.assertEqual(_('%(operator)s : %(message)s.') % {
                                'operator': _('Remove the end (N characters)'),
                                'message':  _('enter a positive number'),
                            },
                         unicode(cm.exception)
                        )


class EntityCellTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()

        get_ct = ContentType.objects.get_for_model #TODO: inline
        cls.contact_ct = get_ct(Contact)
        #cls.orga_ct    = get_ct(Organisation)

    def test_build_4_field01(self):
        field_name = 'first_name'
        cell = EntityCellRegularField.build(model=Contact, name=field_name)
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_name,      cell.value)
        self.assertEqual(_('First name'), cell.title)
        self.assertIs(cell.has_a_filter, True)
        self.assertIs(cell.editable, True)
        self.assertIs(cell.sortable, True)
        self.assertEqual('first_name__icontains', cell.filter_string)

    def test_build_4_field02(self):
        "Date field"
        cell = EntityCellRegularField.build(model=Contact, name='birthday')
        self.assertEqual('birthday__range', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_field03(self):
        "Boolean field"
        cell = EntityCellRegularField.build(model=Organisation, name='subject_to_vat')
        self.assertEqual('subject_to_vat__creme-boolean', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

    def test_build_4_field04(self):
        "ForeignKey"
        cell = EntityCellRegularField.build(model=Contact, name='position')
        self.assertEqual('position', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

        cell = EntityCellRegularField.build(model=Contact, name='image')
        self.assertEqual('image__header_filter_search_field__icontains',
                         cell.filter_string
                        )
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

    def test_build_4_field05(self):
        "Basic ForeignKey subfield"
        cell = EntityCellRegularField.build(model=Contact, name='position__title')
        self.assertEqual('position__title__icontains', cell.filter_string)

        cell = EntityCellRegularField.build(model=Contact, name='image__name')
        self.assertEqual('image__name__icontains', cell.filter_string)

    def test_build_4_field06(self):
        "Date ForeignKey subfield"
        cell = EntityCellRegularField.build(model=Contact, name='image__created')
        self.assertEqual(u'%s - %s' % (_('Photograph'), _('Creation date')), cell.title)
        self.assertEqual('image__created__range', cell.filter_string)

    def test_build_4_field07(self):
        "ManyToMany"
        cell = EntityCellRegularField.build(model=Contact, name='language')
        self.assertIs(cell.has_a_filter, False)
        self.assertIs(cell.sortable, False)

        cell = EntityCellRegularField.build(model=Contact, name='language__name')
        self.assertIs(cell.has_a_filter, False)

    def test_build_4_field_errors(self):
        build = partial(EntityCellRegularField.build, model=Contact)
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
        self.assertEqual('customfieldinteger__value__icontains', cell.filter_string)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,         cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        cell = EntityCellCustomField.build(Contact, customfield.id)
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(str(customfield.id), cell.value)

        self.assertIsNone(EntityCellCustomField.build(Contact, 1000))

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
                                   ) [0]
        cell = EntityCellRelation(rtype=loves)
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(str(loves.id),   cell.value)
        self.assertEqual(loves.predicate, cell.title)
        self.assertIs(cell.has_a_filter, True)
        self.assertIs(cell.editable,     False)
        self.assertIs(cell.sortable,     False)
        self.assertEqual('',    cell.filter_string)
        self.assertEqual(loves, cell.relation_type)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_functionfield(self):
        name = 'get_pretty_properties'
        funfield = Contact.function_fields.get(name)
        self.assertIsNotNone(funfield)

        cell = EntityCellFunctionField(func_field=funfield)
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(name,            cell.value)
        self.assertEqual(unicode(funfield.verbose_name), cell.title)
        self.assertIs(cell.has_a_filter, True) #TODO: test with a non-filterable FunctionField
        self.assertIs(cell.editable,     False)
        self.assertIs(cell.sortable,     False)
        self.assertIs(cell.is_hidden,    False)
        self.assertEqual('', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        cell = EntityCellFunctionField.build(Contact, func_field_name=name)
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(name, cell.value)

        self.assertIsNone(EntityCellFunctionField.build(Contact, func_field_name='invalid'))
