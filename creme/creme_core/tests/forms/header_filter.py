## -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from .base import FieldTestCase
    from creme.creme_core.forms.header_filter import HeaderFilterItemsField
    from creme.creme_core.models.header_filter import (HeaderFilterItem,
            HFI_FIELD, HFI_RELATION, HFI_CUSTOM, HFI_FUNCTION)
    from creme.creme_core.models import RelationType, CustomField

    from creme.persons.models import Contact
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('HeaderFilterItemsFieldTestCase',)


class HeaderFilterItemsFieldTestCase(FieldTestCase):
    @classmethod
    def setUpClass(cls):
        cls.ct_contact = ContentType.objects.get_for_model(Contact)

    def test_clean_empty_required(self):
        clean = HeaderFilterItemsField(required=True, content_type=self.ct_contact).clean
        self.assertFieldValidationError(HeaderFilterItemsField, 'required', clean, None)
        self.assertFieldValidationError(HeaderFilterItemsField, 'required', clean, '')

    def test_clean_empty_not_required(self):
        field = HeaderFilterItemsField(required=False, content_type=self.ct_contact)

        with self.assertNoException():
            value = field.clean(None)

        self.assertEqual([], value)

    def test_clean_invalid_choice(self):
        field = HeaderFilterItemsField(content_type=self.ct_contact)
        self.assertFieldValidationError(HeaderFilterItemsField, 'invalid', field.clean,
                                        'rfield-first_name,rfield-unknown'
                                       )

    def test_ok01(self):
        "One regular field"
        field = HeaderFilterItemsField(content_type=self.ct_contact)
        items = field.clean('rfield-first_name')
        self.assertEqual(1, len(items))

        hfitem = items[0]
        self.assertIsInstance(hfitem, HeaderFilterItem)
        self.assertEqual('first_name',            hfitem.name)
        self.assertEqual(HFI_FIELD,               hfitem.type)
        self.assertEqual('first_name__icontains', hfitem.filter_string)
        self.assertIsNone(hfitem.order)
        self.assertIs(hfitem.is_hidden, False)

    def test_ok02(self):
        "All types of columns"
        loves = RelationType.create(('test-subject_love', u'Is loving'),
                                    ('test-object_love',  u'Is loved by')
                                   )[0]
        customfield = CustomField.objects.create(name=u'Size (cm)',
                                                 field_type=CustomField.INT,
                                                 content_type=self.ct_contact,
                                                )
        funcfield = Contact.function_fields.get('get_pretty_properties')

        field = HeaderFilterItemsField(content_type=self.ct_contact)
        items = field.clean('rtype-%s,rfield-last_name,ffield-%s,cfield-%s,rfield-first_name' % (
                                    loves.id, funcfield.name, customfield.id,
                                )
                           )
        self.assertEqual([(loves.id,            HFI_RELATION),
                          ('last_name',         HFI_FIELD),
                          (funcfield.name,      HFI_FUNCTION),
                          (str(customfield.id), HFI_CUSTOM),
                          ('first_name',        HFI_FIELD),
                        ],
                        [(item.name, item.type) for item in items]
                       )
