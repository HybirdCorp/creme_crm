# -*- coding: utf-8 -*-

from sys import exc_info
from traceback import format_exception

from creme.creme_core import autodiscover
from creme.creme_core.forms.fields import JSONField, GenericEntityField, MultiGenericEntityField

from creme.creme_core.utils import creme_entity_content_types
from creme.creme_core.management.commands.creme_populate import Command as PopulateCommand

from creme.persons.models.address import Address
from creme.persons.models.contact import Contact
from creme.persons.models.organisation import Organisation

from django.contrib.contenttypes.models import ContentType
from django.forms.util import ValidationError
from django.test import TestCase


def format_stack():
    exc_type, exc_value, exc_traceback = exc_info()
    return ''.join(format_exception(exc_type, exc_value, exc_traceback))

def format_function(func):
    return func.__module__ + '.' + func.__name__.lstrip('<').rstrip('>') + '()' if func else 'None'

class FieldTestCase(TestCase):
    def assertFieldRaises(self, exception, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception, e:
            return (e, format_stack())

        exception_name = exception.__name__ if hasattr(exception, '__name__') else str(exception)
        self.fail("%s not raised" % exception_name)

    def assertFieldValidationError(self, field, key, func, *args, **kwargs):
        err, stack = self.assertFieldRaises(ValidationError, func, *args, **kwargs)
        message = unicode(field().error_messages[key])

        if message != err.messages[0]:
            self.fail('unexpected message "%s" instead of "%s"\nerror : %s' % (err.messages[0], message, stack))

    def populate(self, *args):
        PopulateCommand().handle(application=args)

class JSONFieldTestCase(FieldTestCase):
    def test_clean_empty_required(self):
        field = JSONField(required=True)
        self.assertFieldValidationError(JSONField, 'required', field.clean, None)

    def test_clean_empty_not_required(self):
        field = JSONField(required=False)
        field.clean(None)

    def test_clean_invalid_json(self):
        field = JSONField(required=True)

        self.assertFieldValidationError(JSONField, 'invalidformat', field.clean, '{"unclosed_dict"')
        self.assertFieldValidationError(JSONField, 'invalidformat', field.clean, '["unclosed_list",')
        self.assertFieldValidationError(JSONField, 'invalidformat', field.clean, '["","unclosed_str]')
        self.assertFieldValidationError(JSONField, 'invalidformat', field.clean, '["" "comma_error"]')

    def test_clean_valid(self):
        field = JSONField(required=True)
        field.clean('{"ctype":"12","entity":"1"}')

    def test_format_empty_to_json(self):
        field = JSONField()
        self.assertEquals('""', field.from_python(''))

    def test_format_string_to_json(self):
        field = JSONField()
        self.assertEquals('"this is a string"', field.from_python('this is a string'))

    def test_format_object_to_json(self):
        field = JSONField()
        self.assertEquals('{"ctype": "12", "entity": "1"}', field.from_python({"ctype":"12", "entity":"1"}))


def get_field_entry_pair(ctypemodel, model):
    contact_ctype = ContentType.objects.get_for_model(ctypemodel)
    contact = model.objects.all()[0]
    return (contact_ctype, contact)


class GenericEntityFieldTestCase(FieldTestCase):
    def test_models_ctypes(self):
        field = GenericEntityField(models=[Organisation, Contact, Address])
        self.assertEquals(3, len(field.ctypes))
        self.assertEquals(ContentType.objects.get_for_model(Organisation), field.ctypes[0])
        self.assertEquals(ContentType.objects.get_for_model(Contact), field.ctypes[1])
        self.assertEquals(ContentType.objects.get_for_model(Address), field.ctypes[2])

    def test_default_ctypes(self):
        autodiscover()

        field = GenericEntityField()
        self.assertTrue(len(field.ctypes) > 0)
        self.assertEquals(list(creme_entity_content_types()), field.ctypes)

    def test_clean_empty_required(self):
        field = GenericEntityField(required=True)
        self.assertFieldValidationError(GenericEntityField, 'required', field.clean, None)
        self.assertFieldValidationError(GenericEntityField, 'required', field.clean, "{}")

    def test_clean_empty_not_required(self):
        field = GenericEntityField(required=False)
        field.clean(None)

    def test_clean_invalid_json(self):
        field = GenericEntityField(required=False)
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', field.clean, '{"ctype":"12","entity":"1"')

    def test_clean_invalid_data_type(self):
        field = GenericEntityField(required=False)
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', field.clean, '"this is a string"')

    # data injection : use a correct content entry (content type and id), but content type not in field list...
    def test_clean_unknown_ctype(self):
        self.populate('creme_core', 'persons')

        field = GenericEntityField(models=[Organisation, Address])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)

        value = '{"ctype":"%s","entity":"%s"}' % (contact_ctype.pk, contact.pk)

        self.assertFieldValidationError(GenericEntityField, 'doesnotexist', field.clean, value)

    # data injection : use an content id with address content type...
    def test_clean_unknown_entity(self):
        self.populate('creme_core', 'persons')

        field = GenericEntityField(models=[Organisation, Contact, Address])

        address_ctype, contact = get_field_entry_pair(Address, Contact)

        value = '{"ctype":"%s","entity":"%s"}' % (address_ctype.pk, contact.pk)

        self.assertFieldValidationError(GenericEntityField, 'doesnotexist', field.clean, value)

    # TODO : complete this test after form right management refactor.
    def test_clean_unallowed_entity(self):
        pass

    # data injection : use an content id with address content type...
    def test_clean_entity(self):
        self.populate('creme_core', 'persons')
        field = GenericEntityField(models=[Organisation, Contact, Address])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)

        value = '{"ctype":"%s","entity":"%s"}' % (contact_ctype.pk, contact.pk)

        self.assertEquals(contact, field.clean(value))


class MultiGenericEntityFieldTestCase(FieldTestCase):
    def test_models_ctypes(self):
        field = MultiGenericEntityField(models=[Organisation, Contact, Address])
        self.assertEquals(3, len(field.ctypes))
        self.assertEquals(ContentType.objects.get_for_model(Organisation), field.ctypes[0])
        self.assertEquals(ContentType.objects.get_for_model(Contact), field.ctypes[1])
        self.assertEquals(ContentType.objects.get_for_model(Address), field.ctypes[2])

    def test_default_ctypes(self):
        autodiscover()

        field = MultiGenericEntityField()
        self.assertTrue(len(field.ctypes) > 0)
        self.assertEquals(list(creme_entity_content_types()), field.ctypes)

    def test_clean_empty_required(self):
        field = MultiGenericEntityField(required=True)
        self.assertFieldValidationError(MultiGenericEntityField, 'required', field.clean, None)
        self.assertFieldValidationError(MultiGenericEntityField, 'required', field.clean, "{}")
        self.assertFieldValidationError(MultiGenericEntityField, 'required', field.clean, "[]")

    def test_clean_empty_not_required(self):
        field = MultiGenericEntityField(required=False)
        field.clean(None)

    def test_clean_invalid_json(self):
        field = MultiGenericEntityField(required=False)
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', field.clean, '{"ctype":"12","entity":"1"')

    def test_clean_invalid_data_type(self):
        field = MultiGenericEntityField(required=False)
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', field.clean, '"this is a string"')

    # data injection : a Contact and an Organisation entries. the Contact one is remove (not in field list)
    def test_clean_unknown_ctype(self):
        self.populate('creme_core', 'persons')

        field = MultiGenericEntityField(models=[Organisation, Address])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        organisation_ctype, organisation = get_field_entry_pair(Organisation, Organisation)

        value = '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (contact_ctype.pk, contact.pk,
                                                                                  organisation_ctype.pk, organisation.pk)

        entities = field.clean(value)

        self.assertEquals(1, len(entities))
        self.assertEquals(organisation, entities[0])

    # data injection : a Contact and an Organisation entries. the Organisation one is removed (invalid content type)
    def test_clean_unknown_entity(self):
        self.populate('creme_core', 'persons')

        field = MultiGenericEntityField(models=[Organisation, Contact, Address])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        organisation_ctype, contact2 = get_field_entry_pair(Organisation, Contact)

        value = '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (contact_ctype.pk, contact.pk,
                                                                                  organisation_ctype.pk, contact2.pk)

        entities = field.clean(value)

        self.assertEquals(1, len(entities))
        self.assertEquals(contact, entities[0])

    # data injection : two Contact entries, removed (not in field list).
    # so the result list is empty and cause validation error.
    def test_clean_all_unknown_ctype_required(self):
        self.populate('creme_core', 'persons')

        field = MultiGenericEntityField(models=[Organisation, Address], required=True)

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)

        value = '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (contact_ctype.pk, contact.pk,
                                                                                  contact_ctype.pk, contact.pk)

        self.assertFieldValidationError(MultiGenericEntityField, 'required', field.clean, value)

    # data injection : two Contact entries, removed (not in field list).
    def test_clean_all_unknown_ctype_not_required(self):
        self.populate('creme_core', 'persons')

        field = MultiGenericEntityField(models=[Organisation, Address], required=False)

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)

        value = '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (contact_ctype.pk, contact.pk,
                                                                                  contact_ctype.pk, contact.pk)

        entities = field.clean(value)

        self.assertEquals(0, len(entities))

