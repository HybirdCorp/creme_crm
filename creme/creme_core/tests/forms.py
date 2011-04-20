# -*- coding: utf-8 -*-

from sys import exc_info
from traceback import format_exception

from django.forms.util import ValidationError
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme.creme_core import autodiscover
from creme.creme_core.forms.fields import JSONField, GenericEntityField, MultiGenericEntityField, RelationEntityField, MultiRelationEntityField
from creme.creme_core.utils import creme_entity_content_types
from creme.creme_core.models import RelationType, CremePropertyType, CremeEntity, CremeProperty
from creme.creme_core.constants import REL_SUB_RELATED_TO, REL_SUB_HAS
from creme.creme_core.tests.base import CremeTestCase

from creme.persons.models import Organisation, Contact, Address
from creme.persons.constants import REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY, REL_SUB_EMPLOYED_BY


def format_stack():
    exc_type, exc_value, exc_traceback = exc_info()
    return ''.join(format_exception(exc_type, exc_value, exc_traceback))

def format_function(func):
    return func.__module__ + '.' + func.__name__.lstrip('<').rstrip('>') + '()' if func else 'None'


class FieldTestCase(CremeTestCase):
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

        if not hasattr(err, 'messages'):
            self.fail('unexpected empty message instead of "%s"\nerror : %s' % (message, stack))

        if message != err.messages[0]:
            self.fail('unexpected message "%s" instead of "%s"\nerror : %s' % (err.messages[0], message, stack))


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
        self.assertEquals(3, len(field.get_ctypes()))
        self.assertEquals(ContentType.objects.get_for_model(Organisation), field.get_ctypes()[0])
        self.assertEquals(ContentType.objects.get_for_model(Contact), field.get_ctypes()[1])
        self.assertEquals(ContentType.objects.get_for_model(Address), field.get_ctypes()[2])

    def test_default_ctypes(self):
        autodiscover()

        field = GenericEntityField()
        self.assertTrue(len(field.get_ctypes()) > 0)
        self.assertEquals(list(creme_entity_content_types()), field.get_ctypes())

    def test_format_object(self):
        self.populate('creme_core', 'persons')

        field = GenericEntityField(models=[Organisation, Contact, Address])
        contact_ctype, contact = get_field_entry_pair(Contact, Contact)

        self.assertEquals('{"ctype": 12, "entity": 1}', field.from_python({"ctype":12, "entity":1}))
        self.assertEquals('{"ctype": %s, "entity": %s}' % (contact_ctype.pk, contact.pk), field.from_python(contact))

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
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', field.clean, "[]")

    def test_clean_invalid_data(self):
        field = GenericEntityField(required=False)
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', field.clean, '{"entity":"1"}')
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', field.clean, '{"ctype":"12"}')
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', field.clean, '{"ctype":"notanumber","entity":"1"}')
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', field.clean, '{"ctype":"12","entity":"notanumber"}')

    # data injection : use a correct content entry (content type and id), but content type not in field list...
    def test_clean_unallowed_ctype(self):
        self.populate('creme_core', 'persons')

        field = GenericEntityField(models=[Organisation, Address])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)

        value = '{"ctype":"%s","entity":"%s"}' % (contact_ctype.pk, contact.pk)

        self.assertFieldValidationError(GenericEntityField, 'ctypenotallowed', field.clean, value)

    # data injection : use a contact id with address content type...
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
        self.assertEquals(3, len(field.get_ctypes()))
        self.assertEquals(ContentType.objects.get_for_model(Organisation), field.get_ctypes()[0])
        self.assertEquals(ContentType.objects.get_for_model(Contact), field.get_ctypes()[1])
        self.assertEquals(ContentType.objects.get_for_model(Address), field.get_ctypes()[2])

    def test_default_ctypes(self):
        autodiscover()

        field = MultiGenericEntityField()
        self.assertTrue(len(field.get_ctypes()) > 0)
        self.assertEquals(list(creme_entity_content_types()), field.get_ctypes())

    def test_format_object(self):
        self.populate('creme_core', 'persons')

        field = MultiGenericEntityField(models=[Organisation, Contact, Address])
        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        organisation_ctype, organisation = get_field_entry_pair(Organisation, Organisation)

        self.assertEquals('[{"ctype": 12, "entity": 1}, {"ctype": 14, "entity": 5}]', field.from_python([{"ctype":12, "entity":1},
                                                                                                         {"ctype":14, "entity":5}]))
        self.assertEquals('[{"ctype": %s, "entity": %s}, {"ctype": %s, "entity": %s}]' % (contact_ctype.pk, contact.pk,
                                                                                          organisation_ctype.pk, organisation.pk), field.from_python([contact, organisation]))

    def test_clean_empty_required(self):
        field = MultiGenericEntityField(required=True)
        self.assertFieldValidationError(MultiGenericEntityField, 'required', field.clean, None)
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
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', field.clean, "{}")

    def test_clean_invalid_data(self):
        field = MultiGenericEntityField(required=False)
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', field.clean, '[{"entity":"1"}]')
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', field.clean, '[{"ctype":"12"}]')
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', field.clean, '[{"ctype":"notanumber","entity":"1"}]')
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', field.clean, '[{"ctype":"12","entity":"notanumber"}]')

    # data injection : a Contact and an Organisation entries. the Contact one is remove (not in field list)
    def test_clean_unallowed_ctype(self):
        self.populate('creme_core', 'persons')

        field = MultiGenericEntityField(models=[Organisation, Address])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        organisation_ctype, organisation = get_field_entry_pair(Organisation, Organisation)

        value = '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (contact_ctype.pk, contact.pk,
                                                                                  organisation_ctype.pk, organisation.pk)

        self.assertFieldValidationError(MultiGenericEntityField, 'ctypenotallowed', field.clean, value)

    # data injection : a Contact and an Organisation entries. the Organisation one is removed (invalid content type)
    def test_clean_unknown_entity(self):
        self.populate('creme_core', 'persons')

        field = MultiGenericEntityField(models=[Organisation, Contact, Address])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        organisation_ctype, contact2 = get_field_entry_pair(Organisation, Contact)

        value = '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (contact_ctype.pk, contact.pk,
                                                                                  organisation_ctype.pk, contact2.pk)

        self.assertFieldValidationError(MultiGenericEntityField, 'doesnotexist', field.clean, value)

    def test_clean_entities(self):
        self.populate('creme_core', 'persons')

        field = MultiGenericEntityField(models=[Organisation, Contact])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        organisation_ctype, organisation = get_field_entry_pair(Organisation, Organisation)

        value = '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (contact_ctype.pk, contact.pk,
                                                                                  organisation_ctype.pk, organisation.pk)

        entities = field.clean(value)

        self.assertEquals(2, len(entities))

        self.assertEquals(contact, entities[0])
        self.assertEquals(organisation, entities[1])


def populate_good_bad_property_entities(user):
    subject_ptype = CremePropertyType.create(str_pk='test-prop_foobar-subject', text='Subject property')
    object_ptype  = CremePropertyType.create(str_pk='test-prop_foobar-object', text='Contact property')

    bad_subject   = CremeEntity.objects.create(user=user)
    good_subject  = CremeEntity.objects.create(user=user)

    bad_object   = CremeEntity.objects.create(user=user)
    good_object  = CremeEntity.objects.create(user=user)

    CremeProperty.objects.create(type=subject_ptype, creme_entity=good_subject)
    CremeProperty.objects.create(type=object_ptype, creme_entity=good_object)

    return ((good_subject, bad_subject), (good_object, bad_object), (subject_ptype, object_ptype))


class RelationEntityFieldTestCase(FieldTestCase):
    def test_rtypes(self):
        autodiscover()
        self.populate('creme_core', 'persons')

        field = RelationEntityField(allowed_rtypes=[REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY])
        self.assertEquals(2, len(field._get_allowed_rtypes_objects()))

        self.assertEquals(RelationType.objects.get(pk=REL_OBJ_CUSTOMER_OF), field._get_allowed_rtypes_objects().get(pk=REL_OBJ_CUSTOMER_OF))
        self.assertEquals(RelationType.objects.get(pk=REL_OBJ_EMPLOYED_BY), field._get_allowed_rtypes_objects().get(pk=REL_OBJ_EMPLOYED_BY))

    def test_default_rtypes(self):
        self.populate('creme_core', 'persons')

        field = RelationEntityField()
        self.assertEquals(2, len(field._get_allowed_rtypes_objects()))

        self.assertEquals(RelationType.objects.get(pk=REL_SUB_RELATED_TO), field._get_allowed_rtypes_objects().get(pk=REL_SUB_RELATED_TO))
        self.assertEquals(RelationType.objects.get(pk=REL_SUB_HAS), field._get_allowed_rtypes_objects().get(pk=REL_SUB_HAS))

    def test_rtypes_property(self):
        self.populate('creme_core', 'persons')

        field = RelationEntityField()
        self.assertEquals(2, len(field.allowed_rtypes))

        self.assertEquals(RelationType.objects.get(pk=REL_SUB_RELATED_TO), field._get_allowed_rtypes_objects().get(pk=REL_SUB_RELATED_TO))
        self.assertEquals(RelationType.objects.get(pk=REL_SUB_HAS), field._get_allowed_rtypes_objects().get(pk=REL_SUB_HAS))

        field.allowed_rtypes = [REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY]

        self.assertEquals(RelationType.objects.get(pk=REL_OBJ_CUSTOMER_OF), field._get_allowed_rtypes_objects().get(pk=REL_OBJ_CUSTOMER_OF))
        self.assertEquals(RelationType.objects.get(pk=REL_OBJ_EMPLOYED_BY), field._get_allowed_rtypes_objects().get(pk=REL_OBJ_EMPLOYED_BY))

    def test_clean_empty_required(self):
        field = RelationEntityField(required=True)
        self.assertFieldValidationError(RelationEntityField, 'required', field.clean, None)
        self.assertFieldValidationError(RelationEntityField, 'required', field.clean, "{}")

    def test_clean_empty_not_required(self):
        field = RelationEntityField(required=False)
        field.clean(None)

    def test_clean_invalid_json(self):
        field = RelationEntityField(required=False)
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', field.clean, '{"rtype":"10", "ctype":"12","entity":"1"')

    def test_clean_invalid_data_type(self):
        field = RelationEntityField(required=False)
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', field.clean, '"this is a string"')
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', field.clean, '"[]"')

    def test_clean_invalid_data(self):
        field = RelationEntityField(required=False)
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', field.clean, '{"ctype":"12","entity":"1"}')
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', field.clean, '{"rtype":"10","entity":"1"}')
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', field.clean, '{"rtype":"10", ctype":"12"}')
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', field.clean, '{"rtype":"notanumber", ctype":"12","entity":"1"}')
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', field.clean, '{"rtype":"10", ctype":"notanumber","entity":"1"}')
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', field.clean, '{"rtype":"10", "ctype":"12","entity":"notanumber"}')

    # data injection : use a correct content entry (content type and id), but relation type not in database...
    def test_clean_unknown_rtype(self):
        self.login()
        Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        field = RelationEntityField(allowed_rtypes=[REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY])
        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        value = '{"rtype":"%s", "ctype":"%s","entity":"%s"}' % (REL_OBJ_CUSTOMER_OF, contact_ctype.pk, contact.pk)

        self.assertFieldValidationError(RelationEntityField, 'rtypedoesnotexist', field.clean, value)

    # data injection : use a correct content entry (content type and id), but content type not in field list...
    def test_clean_not_allowed_rtype(self):
        self.populate('creme_core', 'persons')

        field = RelationEntityField(allowed_rtypes=[REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY])
        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        value = '{"rtype":"%s", "ctype":"%s","entity":"%s"}' % (REL_SUB_RELATED_TO, contact_ctype.pk, contact.pk)

        self.assertFieldValidationError(RelationEntityField, 'rtypenotallowed', field.clean, value)

    # data injection : use a correct address entry not accepted by relation type REL_OBJ_EMPLOYED_BY
    def test_clean_ctype_constraint_error(self):
        self.populate('creme_core', 'persons')

        field = RelationEntityField(allowed_rtypes=[REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY])
        orga_ctype, orga = get_field_entry_pair(Organisation, Organisation)
        value = '{"rtype":"%s", "ctype":"%s","entity":"%s"}' % (REL_OBJ_EMPLOYED_BY, orga_ctype.pk, orga.pk)

        self.assertFieldValidationError(RelationEntityField, 'ctypenotallowed', field.clean, value)

    # data injection : use an organisation id with contact content type. REL_OBJ_EMPLOYED_BY allows contact content type.
    def test_clean_unknown_entity(self):
        self.populate('creme_core', 'persons')

        field = RelationEntityField(allowed_rtypes=[REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY])
        contact_ctype, orga = get_field_entry_pair(Contact, Organisation)
        value = '{"rtype":"%s", "ctype":"%s","entity":"%s"}' % (REL_OBJ_EMPLOYED_BY, contact_ctype.pk, orga.pk)

        self.assertFieldValidationError(RelationEntityField, 'doesnotexist', field.clean, value)

    # TODO : complete this test after form right management refactor.
#    def test_clean_unallowed_entity(self):
#        pass

    def test_clean_relation(self):
        self.populate('creme_core', 'persons')

        field = RelationEntityField(allowed_rtypes=[REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY])
        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        value = '{"rtype":"%s", "ctype":"%s","entity":"%s"}' % (REL_OBJ_EMPLOYED_BY, contact_ctype.pk, contact.pk)

        self.assertEquals((RelationType.objects.get(pk=REL_OBJ_EMPLOYED_BY), contact), field.clean(value))

    def test_clean_ctype_without_constraint(self):
        self.populate('creme_core', 'persons')

        field = RelationEntityField(allowed_rtypes=[REL_SUB_RELATED_TO, REL_SUB_HAS])
        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        value = '{"rtype":"%s", "ctype":"%s","entity":"%s"}' % (REL_SUB_RELATED_TO, contact_ctype.pk, contact.pk)

        self.assertEquals((RelationType.objects.get(pk=REL_SUB_RELATED_TO), contact), field.clean(value))

    # data injection : use a entity with missing property
    def test_clean_properties_constraint_error(self):
        self.login()
        subject, object, properties = populate_good_bad_property_entities(self.user)

        good_object, bad_object = object
        subject_ptype, object_ptype = properties

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [], [subject_ptype]),
                                               ('test-object_foobar',  'is managed by', [], [object_ptype])
                                              )

        field = RelationEntityField(allowed_rtypes=[rtype.pk])
        value = '{"rtype":"%s", "ctype":"%s","entity":"%s"}' % (rtype.pk, bad_object.entity_type.pk, bad_object.pk)

        self.assertFieldValidationError(RelationEntityField, 'nopropertymatch', field.clean, value)

    def test_clean_properties_constraint(self):
        self.login()
        subject, object, properties = populate_good_bad_property_entities(self.user)

        good_object, bad_object = object
        subject_ptype, object_ptype = properties

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [], [subject_ptype]),
                                               ('test-object_foobar',  'is managed by', [], [object_ptype])
                                              )

        field = RelationEntityField(allowed_rtypes=[rtype.pk])
        value = '{"rtype":"%s", "ctype":"%s","entity":"%s"}' % (rtype.pk, good_object.entity_type.pk, good_object.pk)

        self.assertEquals((RelationType.objects.get(pk=rtype.pk), good_object), field.clean(value))

    def test_clean_properties_without_constraint(self):
        self.login()
        subject, object, properties = populate_good_bad_property_entities(self.user)

        good_object, bad_object = object

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [], []),
                                               ('test-object_foobar',  'is managed by', [], [])
                                              )

        field = RelationEntityField(allowed_rtypes=[rtype.pk])
        value = '{"rtype":"%s", "ctype":"%s","entity":"%s"}' % (rtype.pk, bad_object.entity_type.pk, bad_object.pk)

        self.assertEquals((RelationType.objects.get(pk=rtype.pk), bad_object), field.clean(value))


class MultiRelationEntityFieldTestCase(FieldTestCase):
    def test_rtypes(self):
        autodiscover()
        self.populate('creme_core', 'persons')

        field = MultiRelationEntityField(allowed_rtypes=[REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY])
        self.assertEquals(2, len(field._get_allowed_rtypes_objects()))

        self.assertEquals(RelationType.objects.get(pk=REL_OBJ_CUSTOMER_OF), field._get_allowed_rtypes_objects().get(pk=REL_OBJ_CUSTOMER_OF))
        self.assertEquals(RelationType.objects.get(pk=REL_OBJ_EMPLOYED_BY), field._get_allowed_rtypes_objects().get(pk=REL_OBJ_EMPLOYED_BY))

    def test_default_rtypes(self):
        self.populate('creme_core', 'persons')

        field = MultiRelationEntityField()
        self.assertTrue(2, len(field._get_allowed_rtypes_objects()))

        self.assertEquals(RelationType.objects.get(pk=REL_SUB_RELATED_TO), field._get_allowed_rtypes_objects().get(pk=REL_SUB_RELATED_TO))
        self.assertEquals(RelationType.objects.get(pk=REL_SUB_HAS), field._get_allowed_rtypes_objects().get(pk=REL_SUB_HAS))

    def test_clean_empty_required(self):
        field = MultiRelationEntityField(required=True)
        self.assertFieldValidationError(MultiRelationEntityField, 'required', field.clean, None)
        self.assertFieldValidationError(MultiRelationEntityField, 'required', field.clean, "[]")

    def test_clean_empty_not_required(self):
        field = MultiRelationEntityField(required=False)
        field.clean(None)

    def test_clean_invalid_json(self):
        field = MultiRelationEntityField(required=False)
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', field.clean, '{"rtype":"10", "ctype":"12","entity":"1"')

    def test_clean_invalid_data_type(self):
        field = MultiRelationEntityField(required=False)
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', field.clean, '"this is a string"')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', field.clean, '"{}"')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', field.clean, '{"rtype":"10", "ctype":"12","entity":"1"}')

    def test_clean_invalid_data(self):
        field = MultiRelationEntityField(required=False)
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', field.clean, '[{"ctype":"12","entity":"1"}]')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', field.clean, '[{"rtype":"10","entity":"1"}]')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', field.clean, '[{"rtype":"10", ctype":"12"}]')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', field.clean, '[{"rtype":"notanumber", ctype":"12","entity":"1"}]')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', field.clean, '[{"rtype":"10", ctype":"notanumber","entity":"1"}]')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', field.clean, '[{"rtype":"10", "ctype":"12","entity":"notanumber"}]')

    # data injection : use a correct content entry (content type and id), but content type not in field list...
    def test_clean_unknown_rtype(self):
        self.login()
        Contact.objects.create(user=self.user, first_name='Casca', last_name='Miura')

        field = MultiRelationEntityField(allowed_rtypes=[REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY])
        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        value = '[{"rtype":"%s", "ctype":"%s","entity":"%s"}]' % (REL_OBJ_CUSTOMER_OF, contact_ctype.pk, contact.pk)

        self.assertFieldValidationError(RelationEntityField, 'rtypedoesnotexist', field.clean, value)

    # data injection : use a correct content entry (content type and id), but content type not in field list...
    def test_clean_not_allowed_rtype(self):
        self.populate('creme_core', 'persons')

        field = MultiRelationEntityField(allowed_rtypes=[REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        orga_ctype, orga = get_field_entry_pair(Organisation, Organisation)

        value = '[{"rtype":"%s", "ctype":"%s","entity":"%s"},{"rtype":"%s", "ctype":"%s","entity":"%s"}]' % (REL_SUB_RELATED_TO, contact_ctype.pk, contact.pk,
                                                                                                             REL_SUB_HAS, orga_ctype.pk, orga.pk)

        self.assertFieldValidationError(RelationEntityField, 'rtypenotallowed', field.clean, value)

    # data injection : use a correct address entry not accepted by relation type REL_OBJ_EMPLOYED_BY
    def test_clean_ctype_constraint_error(self):
        self.populate('creme_core', 'persons')

        field = MultiRelationEntityField(allowed_rtypes=[REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        orga_ctype, orga = get_field_entry_pair(Organisation, Organisation)

        value = '[{"rtype":"%s", "ctype":"%s","entity":"%s"},{"rtype":"%s", "ctype":"%s","entity":"%s"}]' % (REL_OBJ_EMPLOYED_BY, orga_ctype.pk, orga.pk,
                                                                                                             REL_OBJ_CUSTOMER_OF, contact_ctype.pk, contact.pk)

        self.assertFieldValidationError(MultiRelationEntityField, 'ctypenotallowed', field.clean, value)

    # data injection : use an organisation id with contact content type. REL_OBJ_EMPLOYED_BY allows contact content type.
    def test_clean_unknown_entity(self):
        self.populate('creme_core', 'persons')

        field = MultiRelationEntityField(allowed_rtypes=[REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        orga_ctype, orga = get_field_entry_pair(Organisation, Organisation)

        value = '[{"rtype":"%s", "ctype":"%s","entity":"%s"},{"rtype":"%s", "ctype":"%s","entity":"%s"}]' % (REL_OBJ_EMPLOYED_BY, contact_ctype.pk, orga.pk,
                                                                                                             REL_OBJ_CUSTOMER_OF, contact_ctype.pk, contact.pk)

        self.assertFieldValidationError(MultiRelationEntityField, 'doesnotexist', field.clean, value)

#    # TODO : complete this test after form right management refactor.
#    def test_clean_unallowed_entity(self):
#        pass

    def test_clean_relations(self):
        self.populate('creme_core', 'persons')

        field = MultiRelationEntityField(allowed_rtypes=[REL_OBJ_CUSTOMER_OF, REL_OBJ_EMPLOYED_BY, REL_SUB_EMPLOYED_BY])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        orga_ctype, orga = get_field_entry_pair(Organisation, Organisation)

        value = """[{"rtype":"%s", "ctype":"%s","entity":"%s"},
                    {"rtype":"%s", "ctype":"%s","entity":"%s"},
                    {"rtype":"%s", "ctype":"%s","entity":"%s"}]""" % (REL_OBJ_EMPLOYED_BY, contact_ctype.pk, contact.pk,
                                                                      REL_OBJ_CUSTOMER_OF, contact_ctype.pk, contact.pk,
                                                                      REL_SUB_EMPLOYED_BY, orga_ctype.pk, orga.pk)

        relations = field.clean(value)

        self.assertEquals(3, len(relations))

        self.assertEquals((RelationType.objects.get(pk=REL_OBJ_EMPLOYED_BY), contact), relations[0])
        self.assertEquals((RelationType.objects.get(pk=REL_OBJ_CUSTOMER_OF), contact), relations[1])
        self.assertEquals((RelationType.objects.get(pk=REL_SUB_EMPLOYED_BY), orga), relations[2])

    def test_clean_ctype_without_constraint(self):
        self.populate('creme_core', 'persons')

        field = MultiRelationEntityField(allowed_rtypes=[REL_SUB_RELATED_TO, REL_SUB_HAS])

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        orga_ctype, orga = get_field_entry_pair(Organisation, Organisation)

        value = """[{"rtype":"%s", "ctype":"%s","entity":"%s"},
                    {"rtype":"%s", "ctype":"%s","entity":"%s"},
                    {"rtype":"%s", "ctype":"%s","entity":"%s"}]""" % (REL_SUB_RELATED_TO, contact_ctype.pk, contact.pk,
                                                                      REL_SUB_HAS, contact_ctype.pk, contact.pk,
                                                                      REL_SUB_RELATED_TO, orga_ctype.pk, orga.pk)

        relations = field.clean(value)

        self.assertEquals(3, len(relations))

        self.assertEquals((RelationType.objects.get(pk=REL_SUB_RELATED_TO), contact), relations[0])
        self.assertEquals((RelationType.objects.get(pk=REL_SUB_HAS), contact), relations[1])
        self.assertEquals((RelationType.objects.get(pk=REL_SUB_RELATED_TO), orga), relations[2])


    # data injection : use a entity with missing property
    def test_clean_properties_constraint_error(self):
        self.login()
        self.populate('creme_core', 'persons')

        subject, object, properties = populate_good_bad_property_entities(self.user)

        good_object, bad_object = object
        subject_ptype, object_ptype = properties

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [], [subject_ptype]),
                                               ('test-object_foobar',  'is managed by', [], [object_ptype])
                                              )

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        orga_ctype, orga = get_field_entry_pair(Organisation, Organisation)

        field = MultiRelationEntityField(allowed_rtypes=[rtype.pk, REL_SUB_RELATED_TO, REL_SUB_HAS])

        value = """[{"rtype":"%s", "ctype":"%s","entity":"%s"},
                    {"rtype":"%s", "ctype":"%s","entity":"%s"},
                    {"rtype":"%s", "ctype":"%s","entity":"%s"}]""" % (rtype.pk, bad_object.entity_type.pk, bad_object.pk,
                                                                      REL_SUB_HAS, contact_ctype.pk, contact.pk,
                                                                      REL_SUB_RELATED_TO, orga_ctype.pk, orga.pk)

        self.assertFieldValidationError(RelationEntityField, 'nopropertymatch', field.clean, value)

    def test_clean_properties_constraint(self):
        self.login()
        self.populate('creme_core', 'persons')

        subject, object, properties = populate_good_bad_property_entities(self.user)

        good_object, bad_object = object
        subject_ptype, object_ptype = properties

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [], [subject_ptype]),
                                               ('test-object_foobar',  'is managed by', [], [object_ptype])
                                              )

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        orga_ctype, orga = get_field_entry_pair(Organisation, Organisation)

        field = MultiRelationEntityField(allowed_rtypes=[rtype.pk, REL_SUB_RELATED_TO, REL_SUB_HAS])

        value = """[{"rtype":"%s", "ctype":"%s","entity":"%s"},
                    {"rtype":"%s", "ctype":"%s","entity":"%s"},
                    {"rtype":"%s", "ctype":"%s","entity":"%s"}]""" % (rtype.pk, good_object.entity_type.pk, good_object.pk,
                                                                      REL_SUB_HAS, contact_ctype.pk, contact.pk,
                                                                      REL_SUB_RELATED_TO, orga_ctype.pk, orga.pk)

        relations = field.clean(value)

        self.assertEquals(3, len(relations))

        self.assertEquals((RelationType.objects.get(pk=rtype.pk), good_object), relations[0])
        self.assertEquals((RelationType.objects.get(pk=REL_SUB_HAS), contact), relations[1])
        self.assertEquals((RelationType.objects.get(pk=REL_SUB_RELATED_TO), orga), relations[2])

    def test_clean_properties_without_constraint(self):
        self.login()
        self.populate('creme_core', 'persons')

        subject, object, properties = populate_good_bad_property_entities(self.user)

        good_object, bad_object = object

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [], []),
                                               ('test-object_foobar',  'is managed by', [], [])
                                              )

        contact_ctype, contact = get_field_entry_pair(Contact, Contact)
        orga_ctype, orga = get_field_entry_pair(Organisation, Organisation)

        field = MultiRelationEntityField(allowed_rtypes=[rtype.pk, REL_SUB_RELATED_TO, REL_SUB_HAS])

        value = """[{"rtype":"%s", "ctype":"%s","entity":"%s"},
                    {"rtype":"%s", "ctype":"%s","entity":"%s"},
                    {"rtype":"%s", "ctype":"%s","entity":"%s"},
                    {"rtype":"%s", "ctype":"%s","entity":"%s"}]""" % (rtype.pk, bad_object.entity_type.pk, bad_object.pk,
                                                                      rtype.pk, good_object.entity_type.pk, good_object.pk,
                                                                      REL_SUB_HAS, contact_ctype.pk, contact.pk,
                                                                      REL_SUB_RELATED_TO, orga_ctype.pk, orga.pk)

        relations = field.clean(value)

        self.assertEquals(4, len(relations))

        self.assertEquals((RelationType.objects.get(pk=rtype.pk), bad_object), relations[0])
        self.assertEquals((RelationType.objects.get(pk=rtype.pk), good_object), relations[1])
        self.assertEquals((RelationType.objects.get(pk=REL_SUB_HAS), contact), relations[2])
        self.assertEquals((RelationType.objects.get(pk=REL_SUB_RELATED_TO), orga), relations[3])
