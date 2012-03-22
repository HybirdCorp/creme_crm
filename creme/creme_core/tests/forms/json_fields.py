# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.db.models.query import QuerySet

    from creme_core import autodiscover
    from creme_core.forms.fields import GenericEntityField, RelationEntityField, MultiGenericEntityField, MultiRelationEntityField
    from creme_core.forms.fields import JSONField
    from creme_core.utils import creme_entity_content_types
    from creme_core.models import CremeProperty, CremePropertyType, RelationType
    from creme_core.constants import REL_SUB_HAS
    from creme_core.tests.forms.base import FieldTestCase

    from persons.models import Organisation, Contact, Address
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('JSONFieldTestCase',
           'GenericEntityFieldTestCase', 'MultiGenericEntityFieldTestCase',
           'RelationEntityFieldTestCase', 'MultiRelationEntityFieldTestCase',
          )


class _JSONFieldBaseTestCase(FieldTestCase):
    def create_contact(self, first_name='Eikichi', last_name='Onizuka', ptype=None):
        contact = Contact.objects.create(user=self.user, first_name=first_name, last_name=last_name)

        if ptype:
            CremeProperty.objects.create(type=ptype, creme_entity=contact)

        return contact

    def create_orga(self, name='Onibaku'):
        return Organisation.objects.create(user=self.user, name=name)

    def create_loves_rtype(self, subject_ptype=None, object_ptype=None):
        subject_ptypes = (subject_ptype,) if subject_ptype else ()
        object_ptypes  = (object_ptype,) if object_ptype else ()
        return RelationType.create(('test-subject_loves', 'is loving', (), subject_ptypes),
                                   ('test-object_loves',  'loved by',  (), object_ptypes),
                                  )

    def create_hates_rtype(self):
        return RelationType.create(('test-subject_hates', 'is hating'),
                                   ('test-object_hates',  'hated by')
                                  )

    def create_employed_rtype(self):
        return RelationType.create(('test-subject_employed_by', u'is an employee of', [Contact]),
                                   ('test-object_employed_by',  u'employs',           [Organisation]),
                                  )

    def create_customer_rtype(self):
        return RelationType.create(('test-subject_customer', u'is a customer of', [Contact, Organisation]),
                                   ('test-object_customer',  u'is a supplier of', [Contact, Organisation]),
                                  )

    def create_property_types(self):
        create_ptype = CremePropertyType.create
        return (create_ptype(str_pk='test-prop_strong', text='Is strong'),
                create_ptype(str_pk='test-prop_cute',   text='Is cute')
               )


class JSONFieldTestCase(_JSONFieldBaseTestCase):
    def test_clean_empty_required(self):
        self.assertFieldValidationError(JSONField, 'required', JSONField(required=True).clean, None)

    def test_clean_empty_not_required(self):
        #try:
        with self.assertNoException():
            JSONField(required=False).clean(None)
        #except Exception as e:
            #self.fail(str(e))

    def test_clean_invalid_json(self):
        clean = JSONField(required=True).clean

        self.assertFieldValidationError(JSONField, 'invalidformat', clean, '{"unclosed_dict"')
        self.assertFieldValidationError(JSONField, 'invalidformat', clean, '["unclosed_list",')
        self.assertFieldValidationError(JSONField, 'invalidformat', clean, '["","unclosed_str]')
        self.assertFieldValidationError(JSONField, 'invalidformat', clean, '["" "comma_error"]')

    def test_clean_valid(self):
        #try:
        with self.assertNoException():
            JSONField(required=True).clean('{"ctype":"12","entity":"1"}')
        #except Exception as e:
            #self.fail(str(e))

    def test_format_empty_to_json(self):
        self.assertEqual('""', JSONField().from_python(''))

    def test_format_string_to_json(self):
        self.assertEqual('"this is a string"', JSONField().from_python('this is a string'))

    def test_format_object_to_json(self):
        self.assertEqual('{"ctype": "12", "entity": "1"}',
                         JSONField().from_python({"ctype": "12", "entity": "1"})
                        )


class GenericEntityFieldTestCase(_JSONFieldBaseTestCase):
    def test_models_ctypes(self):
        get_ct = ContentType.objects.get_for_model
        self.assertEqual([get_ct(Organisation), get_ct(Contact), get_ct(Address)],
                         GenericEntityField(models=[Organisation, Contact, Address]).get_ctypes()
                        )

    def test_default_ctypes(self):
        autodiscover()

        ctypes = GenericEntityField().get_ctypes()
        self.assertEqual(list(creme_entity_content_types()), ctypes)
        self.assertTrue(ctypes)

    def test_models_property(self):
        self.login()

        contact = self.create_contact()
        orga = self.create_orga('orga')

        ctype1 = contact.entity_type
        ctype2 = orga.entity_type

        field = GenericEntityField()
        self.assertEqual(list(), field.allowed_models)
        self.assertEqual(list(creme_entity_content_types()), field.get_ctypes())

        field.allowed_models = [Contact, Organisation]
        ctypes = list(field.get_ctypes())
        self.assertEqual(2, len(ctypes))
        self.assertIn(ctype1, ctypes)
        self.assertIn(ctype2, ctypes)

    def test_format_object(self):
        self.login()
        contact = self.create_contact()
        field = GenericEntityField(models=[Organisation, Contact, Address])

        self.assertEqual('{"ctype": 12, "entity": 1}', field.from_python({"ctype": 12, "entity": 1}))
        self.assertEqual('{"ctype": %s, "entity": %s}' % (contact.entity_type_id, contact.pk),
                         field.from_python(contact)
                        )

    def test_clean_empty_required(self):
        clean = GenericEntityField(required=True).clean
        self.assertFieldValidationError(GenericEntityField, 'required', clean, None)
        self.assertFieldValidationError(GenericEntityField, 'required', clean, "{}")

    def test_clean_empty_not_required(self):
        #try:
        with self.assertNoException():
            GenericEntityField(required=False).clean(None)
        #except Exception as e:
            #self.fail(str(e))

    def test_clean_invalid_json(self):
        self.assertFieldValidationError(GenericEntityField, 'invalidformat',
                                        GenericEntityField(required=False).clean,
                                        '{"ctype":"12","entity":"1"'
                                       )

    def test_clean_invalid_data_type(self):
        clean = GenericEntityField(required=False).clean
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', clean, '"this is a string"')
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', clean, "[]")

    def test_clean_invalid_data(self):
        clean = GenericEntityField(required=False).clean
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', clean, '{"ctype":"notanumber","entity":"1"}')
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', clean, '{"ctype":"12","entity":"notanumber"}')

    def test_clean_unallowed_ctype(self):
        self.login()

        contact = self.create_contact()
        self.assertFieldValidationError(GenericEntityField, 'ctypenotallowed',
                                        GenericEntityField(models=[Organisation, Address]).clean,
                                        '{"ctype":"%s","entity":"%s"}' % (contact.entity_type_id, contact.id)
                                       )

    def test_clean_unknown_entity(self):
        self.login()
        contact = self.create_contact()

        ct_id = ContentType.objects.get_for_model(Address).id #not Contact !!
        self.assertFieldValidationError(GenericEntityField, 'doesnotexist',
                                        GenericEntityField(models=[Organisation, Contact, Address]).clean,
                                        '{"ctype":"%s","entity":"%s"}' % (ct_id, contact.pk)
                                       )

    def test_clean_entity(self):
        self.login()
        contact = self.create_contact()

        field = GenericEntityField(models=[Organisation, Contact, Address])
        self.assertEqual(contact, field.clean('{"ctype":"%s","entity":"%s"}' % (contact.entity_type_id, contact.pk)))

    def test_clean_incomplete_not_required(self): #not required
        self.login()
        contact = self.create_contact()

        clean = GenericEntityField(models=[Organisation, Contact, Address], required=False).clean
        self.assertFieldValidationError(GenericEntityField, 'ctypenotallowed', clean,
                                        '{"ctype": null}')
        self.assertIsNone(clean('{"ctype": "%s"}' % contact.entity_type_id))
        self.assertIsNone(clean('{"ctype": "%s", "entity": null}' % contact.entity_type_id))

    def test_clean_incomplete_required(self): #required -> 'friendly' errors :)
        self.login()
        contact = self.create_contact()

        clean = GenericEntityField(models=[Organisation, Contact, Address], required=True).clean
        self.assertFieldValidationError(GenericEntityField, 'ctyperequired', clean,
                                        '{"ctype": null}')
        self.assertFieldValidationError(GenericEntityField, 'entityrequired', clean,
                                        '{"ctype": "%s"}' % contact.entity_type_id)
        self.assertFieldValidationError(GenericEntityField, 'entityrequired', clean,
                                        '{"ctype": "%s", "entity": null}' % contact.entity_type_id)

class MultiGenericEntityFieldTestCase(_JSONFieldBaseTestCase):
    def test_models_ctypes(self):
        get_ct = ContentType.objects.get_for_model
        models = [Organisation, Contact, Address]
        self.assertEqual([get_ct(model) for model in models],
                         MultiGenericEntityField(models=models).get_ctypes()
                        )

    def test_default_ctypes(self):
        autodiscover()

        ctypes = MultiGenericEntityField().get_ctypes()
        self.assertEqual(list(creme_entity_content_types()), ctypes)
        self.assertTrue(ctypes)

    def test_format_object(self):
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        field = MultiGenericEntityField(models=[Organisation, Contact, Address])
        self.assertEqual('[{"ctype": 12, "entity": 1}, {"ctype": 14, "entity": 5}]',
                         field.from_python([{"ctype": 12, "entity": 1}, {"ctype": 14, "entity": 5}])
                        )
        self.assertEqual('[{"ctype": %s, "entity": %s}, {"ctype": %s, "entity": %s}]' % (
                                contact.entity_type_id, contact.pk,
                                orga.entity_type_id,    orga.pk
                            ),
                         field.from_python([contact, orga])
                        )

    def test_clean_empty_required(self):
        clean = MultiGenericEntityField(required=True).clean
        self.assertFieldValidationError(MultiGenericEntityField, 'required', clean, None)
        self.assertFieldValidationError(MultiGenericEntityField, 'required', clean, "[]")

    def test_clean_empty_not_required(self):
        #try:
        with self.assertNoException():
            MultiGenericEntityField(required=False).clean(None)
        #except Exception as e:
            #self.fail(str(e))

    def test_clean_invalid_json(self):
        field = MultiGenericEntityField(required=False)
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', field.clean, '{"ctype":"12","entity":"1"')

    def test_clean_invalid_data_type(self):
        clean = MultiGenericEntityField(required=False).clean
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', clean, '"this is a string"')
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', clean, "{}")

    def test_clean_invalid_data(self):
        clean = MultiGenericEntityField(required=False).clean
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', clean, '[{"ctype":"notanumber","entity":"1"}]')
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', clean, '[{"ctype":"12","entity":"notanumber"}]')

    def test_clean_unallowed_ctype(self):
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        field = MultiGenericEntityField(models=[Organisation, Address])
        value  = '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (
                        contact.entity_type_id, contact.pk,
                        orga.entity_type_id,    orga.pk
                    )
        self.assertFieldValidationError(MultiGenericEntityField, 'ctypenotallowed', field.clean, value)

    def test_clean_unknown_entity(self):
        self.login()
        contact1   = self.create_contact()
        contact2   = self.create_contact(first_name='Ryuji', last_name='Danma')
        ct_orga_id = ContentType.objects.get_for_model(Organisation).id

        field = MultiGenericEntityField(models=[Organisation, Contact, Address])
        value = '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (
                        contact1.entity_type_id, contact1.pk,
                        ct_orga_id,              contact2.pk,
                    )
        self.assertFieldValidationError(MultiGenericEntityField, 'doesnotexist', field.clean, value)

    def test_clean_entities(self):
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        field = MultiGenericEntityField(models=[Organisation, Contact])
        entities = field.clean('[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (
                                    contact.entity_type_id, contact.pk,
                                    orga.entity_type_id,    orga.pk
                                )
                              )
        self.assertEqual(2, len(entities))
        self.assertEqual(set([contact, orga]), set(entities))

    def test_clean_incomplete_not_required(self): #not required
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        clean = MultiGenericEntityField(models=[Organisation, Contact], required=False).clean
        self.assertEqual([], clean('[{"ctype": "%s"}]' % contact.entity_type_id))
        self.assertEqual([], clean('[{"ctype": "%s", "entity": null}]' % contact.entity_type_id))
        self.assertEqual([contact, orga],
                         clean('[{"ctype": "%s"},'
                               ' {"ctype": "%s", "entity": null},'
                               ' {"ctype": "%s", "entity": "%s"},'
                               ' {"ctype": "%s", "entity": "%s"}]' % (
                                     contact.entity_type_id,
                                     contact.entity_type_id,
                                     contact.entity_type_id, contact.pk,
                                     orga.entity_type_id, orga.pk,
                                    )
                              )
                        )

    def test_clean_incomplete_required(self): #required -> 'friendly' errors :)
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        clean = MultiGenericEntityField(models=[Organisation, Contact], required=True).clean
        self.assertFieldValidationError(RelationEntityField, 'required', clean,
                                        '[{"ctype": "%s"}, {"ctype": "%s", "entity": null}]' % (
                                             contact.entity_type_id,
                                             contact.entity_type_id,
                                            )
                                       )
        self.assertEqual([contact, orga],
                         clean('[{"ctype": "%s"},'
                               ' {"ctype": "%s", "entity": null},'
                               ' {"ctype": "%s", "entity": "%s"},'
                               ' {"ctype": "%s", "entity":"%s"}]' % (
                                     contact.entity_type_id,
                                     contact.entity_type_id,
                                     contact.entity_type_id, contact.pk,
                                     orga.entity_type_id, orga.pk,
                                    )
                              )
                        )

class RelationEntityFieldTestCase(_JSONFieldBaseTestCase):
    format_str = '{"rtype": "%s", "ctype": "%s", "entity": "%s"}'

    def test_rtypes(self):
        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]

        field = RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id])
        rtypes = list(field._get_allowed_rtypes_objects())
        self.assertEqual(2, len(rtypes))
        self.assertIn(rtype1, rtypes)
        self.assertIn(rtype2, rtypes)

        rtypes_ids = list(field._get_allowed_rtypes_ids())
        self.assertEqual(2, len(rtypes_ids))
        self.assertIn(rtype1.id, rtypes_ids)
        self.assertIn(rtype2.id, rtypes_ids)

    def test_rtypes_queryset(self):
        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]

        field = RelationEntityField(allowed_rtypes=RelationType.objects.filter(pk__in=[rtype1.id, rtype2.id]))
        rtypes = list(field._get_allowed_rtypes_objects())
        self.assertEqual(2, len(rtypes))
        self.assertIn(rtype1, rtypes)
        self.assertIn(rtype2, rtypes)

        rtypes_ids = list(field._get_allowed_rtypes_ids())
        self.assertEqual(2, len(rtypes_ids))
        self.assertIn(rtype1.id, rtypes_ids)
        self.assertIn(rtype2.id, rtypes_ids)

    def test_rtypes_queryset_changes(self):
        rtype2 = self.create_hates_rtype()[0]

        field = RelationEntityField(allowed_rtypes=RelationType.objects.filter(pk__in=["test-subject_loves", rtype2.id]))
        rtypes = list(field._get_allowed_rtypes_objects())
        self.assertEqual(1, len(rtypes))
        self.assertIn(rtype2, rtypes)

        rtype1 = self.create_loves_rtype()[0]

        rtypes_ids = list(field._get_allowed_rtypes_ids())
        self.assertEqual(2, len(rtypes_ids))
        self.assertIn(rtype1.id, rtypes_ids)
        self.assertIn(rtype2.id, rtypes_ids)

        rtype2.delete()

        rtypes_ids = list(field._get_allowed_rtypes_ids())
        self.assertEqual(1, len(rtypes_ids))
        self.assertIn(rtype1.id, rtypes_ids)

    def test_default_rtypes(self):
        self.populate('creme_core')
        self.assertEqual([RelationType.objects.get(pk=REL_SUB_HAS)],
                         list(RelationEntityField()._get_allowed_rtypes_objects())
                        )

    def test_rtypes_property(self):
        self.populate('creme_core')

        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]

        field = RelationEntityField()
        self.assertTrue(isinstance(field.allowed_rtypes, QuerySet))
        self.assertEqual([RelationType.objects.get(pk=REL_SUB_HAS)], list(field.allowed_rtypes))
        self.assertEqual([REL_SUB_HAS], list(field._get_allowed_rtypes_ids()))
        self.assertEqual([RelationType.objects.get(pk=REL_SUB_HAS)], list(field._get_allowed_rtypes_objects()))

        field.allowed_rtypes = [rtype1.id, rtype2.id] # <===
        rtypes = list(field._get_allowed_rtypes_objects())
        self.assertEqual(2, len(rtypes))
        self.assertIn(rtype1, rtypes)
        self.assertIn(rtype2, rtypes)

    def test_rtypes_queryset_property(self):
        self.populate('creme_core')

        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]

        field = RelationEntityField()
        self.assertTrue(isinstance(field.allowed_rtypes, QuerySet))
        self.assertEqual([RelationType.objects.get(pk=REL_SUB_HAS)], list(field.allowed_rtypes))
        self.assertEqual([REL_SUB_HAS], list(field._get_allowed_rtypes_ids()))
        self.assertEqual([RelationType.objects.get(pk=REL_SUB_HAS)], list(field._get_allowed_rtypes_objects()))

        field.allowed_rtypes = RelationType.objects.filter(pk__in=[rtype1.id, rtype2.id]) # <===
        rtypes = list(field._get_allowed_rtypes_objects())
        self.assertEqual(2, len(rtypes))
        self.assertIn(rtype1, rtypes)
        self.assertIn(rtype2, rtypes)

    def test_clean_empty_required(self):
        clean = RelationEntityField(required=True).clean
        self.assertFieldValidationError(RelationEntityField, 'required', clean, None)
        self.assertFieldValidationError(RelationEntityField, 'required', clean, "{}")

    def test_clean_empty_not_required(self):
        self.assertIsNone(RelationEntityField(required=False).clean(None))

    def test_clean_invalid_json(self):
        self.assertFieldValidationError(RelationEntityField, 'invalidformat',
                                        RelationEntityField(required=False).clean,
                                        '{"rtype":"10", "ctype":"12","entity":"1"'
                                       )

    def test_clean_invalid_data_type(self):
        field = RelationEntityField(required=False)
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', field.clean, '"this is a string"')
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', field.clean, '"[]"')

    def test_clean_invalid_data(self):
        clean = RelationEntityField(required=False).clean
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', clean, '{"rtype":"notanumber", ctype":"12","entity":"1"}')
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', clean, '{"rtype":"10", ctype":"notanumber","entity":"1"}')
        self.assertFieldValidationError(RelationEntityField, 'invalidformat', clean, '{"rtype":"10", "ctype":"12","entity":"notanumber"}')

    def test_clean_unknown_rtype(self):
        self.login()
        contact = self.create_contact()

        rtype_id1 = 'test-i_do_not_exist'
        rtype_id2 = 'test-neither_do_i'

        # message changes cause unknown rtype is ignored in allowed list
#        self.assertFieldValidationError(
#                RelationEntityField, 'rtypedoesnotexist',
#                RelationEntityField(allowed_rtypes=[rtype_id1, rtype_id2]).clean,
#                self.format_str % (rtype_id1, contact.entity_type_id, contact.pk)
#            )

        self.assertFieldValidationError(
                RelationEntityField, 'rtypenotallowed',
                RelationEntityField(allowed_rtypes=[rtype_id1, rtype_id2]).clean,
                self.format_str % (rtype_id1, contact.entity_type_id, contact.pk)
            )

    def test_clean_not_allowed_rtype(self):
        self.login()
        contact = self.create_contact()

        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]
        rtype3 = RelationType.create(('test-subject_friend', 'is friend of'), ('test-object_friend', 'has friend'))[0]

        self.assertFieldValidationError(
                RelationEntityField, 'rtypenotallowed',
                RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]).clean,
                self.format_str % (rtype3.id, contact.entity_type_id, contact.pk)
            )

    def test_clean_not_allowed_rtype_queryset(self):
        self.login()
        contact = self.create_contact()

        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]
        rtype3 = RelationType.create(('test-subject_friend', 'is friend of'), ('test-object_friend', 'has friend'))[0]

        self.assertFieldValidationError(
                RelationEntityField, 'rtypenotallowed',
                RelationEntityField(allowed_rtypes=RelationType.objects.filter(pk__in=[rtype1.id, rtype2.id])).clean,
                self.format_str % (rtype3.id, contact.entity_type_id, contact.pk)
            )

    def test_clean_ctype_constraint_error(self):
        self.login()
        orga = self.create_orga()

        rtype1 = self.create_employed_rtype()[1]
        rtype2 = self.create_customer_rtype()[1]
        self.assertFieldValidationError(
                RelationEntityField, 'ctypenotallowed',
                RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]).clean,
                self.format_str % (rtype1.id, orga.entity_type_id, orga.id) #<= need a contact
            )

    def test_clean_unknown_entity(self):
        self.login()
        orga = self.create_orga()

        rtype1 = self.create_employed_rtype()[1]
        rtype2 = self.create_customer_rtype()[1]
        ct_contact_id = ContentType.objects.get_for_model(Contact).id
        self.assertFieldValidationError(
                RelationEntityField, 'doesnotexist',
                RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]).clean,
                self.format_str % (rtype1.id, ct_contact_id, orga.pk)
            )

    def test_clean_relation(self):
        self.login()
        contact = self.create_contact()
        rtype1 = self.create_employed_rtype()[1]
        rtype2 = self.create_customer_rtype()[1]

        field = RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id])
        self.assertEqual((rtype1, contact),
                         field.clean(self.format_str % (rtype1.id, contact.entity_type_id, contact.pk))
                        )

    def test_clean_ctype_without_constraint(self):
        self.login()
        contact = self.create_contact()
        rtype = self.create_loves_rtype()[0]

        field = RelationEntityField(allowed_rtypes=[rtype.id])
        self.assertEqual((rtype, contact),
                         field.clean(self.format_str % (rtype.id, contact.entity_type_id, contact.pk))
                        )

    def test_clean_properties_constraint_error(self):
        self.login()
        subject_ptype, object_ptype = self.create_property_types()
        rtype  = self.create_loves_rtype(subject_ptype=subject_ptype, object_ptype=object_ptype)[0]
        contact = self.create_contact() # <= does not have the property

        self.assertFieldValidationError(RelationEntityField, 'nopropertymatch',
                                        RelationEntityField(allowed_rtypes=[rtype.pk]).clean,
                                        self.format_str % (rtype.pk, contact.entity_type_id, contact.pk)
                                       )

    def test_clean_properties_constraint(self):
        self.login()
        subject_ptype, object_ptype = self.create_property_types()
        rtype  = self.create_loves_rtype(subject_ptype=subject_ptype, object_ptype=object_ptype)[0]
        contact = self.create_contact(ptype=object_ptype) # <= has the property

        field = RelationEntityField(allowed_rtypes=[rtype.pk])
        self.assertEqual((rtype, contact),
                         field.clean(self.format_str % (rtype.pk, contact.entity_type_id, contact.pk))
                        )

    def test_clean_incomplete01(self): #not required
        self.login()
        rtype  = self.create_loves_rtype()[0]
        contact = self.create_contact()

        clean = RelationEntityField(required=False).clean
        self.assertIsNone(clean('{"rtype": "%s"}' % rtype.id))
        self.assertIsNone(clean('{"rtype": "%s", "ctype": "%s"}' % (rtype.id, contact.entity_type_id)))

    def test_clean_incomplete02(self): #required -> 'friendly' errors :)
        self.login()
        rtype  = self.create_loves_rtype()[0]
        contact = self.create_contact()

        clean = RelationEntityField(required=True).clean
        self.assertFieldValidationError(RelationEntityField, 'ctyperequired', clean,
                                        '{"rtype": "%s"}' % rtype.id
                                       )
        self.assertFieldValidationError(RelationEntityField, 'entityrequired', clean,
                                        '{"rtype": "%s", "ctype": "%s"}' % (
                                                rtype.id, contact.entity_type_id
                                            )
                                       )


class MultiRelationEntityFieldTestCase(_JSONFieldBaseTestCase):
    format_str    = '[{"rtype":"%s", "ctype":"%s","entity":"%s"}]'
    format_str_2x = '[{"rtype":"%s", "ctype":"%s", "entity":"%s"},' \
                    ' {"rtype":"%s", "ctype":"%s", "entity":"%s"}]'
    format_str_3x = '[{"rtype":"%s", "ctype":"%s", "entity":"%s"},' \
                    ' {"rtype":"%s", "ctype":"%s", "entity":"%s"},' \
                    ' {"rtype":"%s", "ctype":"%s", "entity":"%s"}]'

    def test_rtypes(self):
        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]

        field = MultiRelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id])
        rtypes = list(field._get_allowed_rtypes_objects())
        self.assertEqual(2, len(rtypes))
        self.assertIn(rtype1, rtypes)
        self.assertIn(rtype2, rtypes)

    def test_rtypes_queryset(self):
        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]

        field = MultiRelationEntityField(allowed_rtypes=RelationType.objects.filter(pk__in=[rtype1.id, rtype2.id]))
        rtypes = list(field._get_allowed_rtypes_objects())
        self.assertEqual(2, len(rtypes))
        self.assertIn(rtype1, rtypes)
        self.assertIn(rtype2, rtypes)

        rtypes_ids = list(field._get_allowed_rtypes_ids())
        self.assertEqual(2, len(rtypes_ids))
        self.assertIn(rtype1.id, rtypes_ids)
        self.assertIn(rtype2.id, rtypes_ids)

    def test_rtypes_queryset_changes(self):
        rtype2 = self.create_hates_rtype()[0]

        field = MultiRelationEntityField(allowed_rtypes=RelationType.objects.filter(pk__in=["test-subject_loves", rtype2.id]))
        rtypes = list(field._get_allowed_rtypes_objects())
        self.assertEqual(1, len(rtypes))
        self.assertIn(rtype2, rtypes)

        rtype1 = self.create_loves_rtype()[0]

        rtypes_ids = list(field._get_allowed_rtypes_ids())
        self.assertEqual(2, len(rtypes_ids))
        self.assertIn(rtype1.id, rtypes_ids)
        self.assertIn(rtype2.id, rtypes_ids)

        rtype2.delete()

        rtypes_ids = list(field._get_allowed_rtypes_ids())
        self.assertEqual(1, len(rtypes_ids))
        self.assertIn(rtype1.id, rtypes_ids)

    def test_default_rtypes(self):
        self.populate('creme_core')
        self.assertEqual([RelationType.objects.get(pk=REL_SUB_HAS)],
                         list(MultiRelationEntityField()._get_allowed_rtypes_objects())
                        )

    def test_clean_empty_required(self):
        clean = MultiRelationEntityField(required=True).clean
        self.assertFieldValidationError(MultiRelationEntityField, 'required', clean, None)
        self.assertFieldValidationError(MultiRelationEntityField, 'required', clean, "[]")

    def test_clean_empty_not_required(self):
        MultiRelationEntityField(required=False).clean(None)

    def test_clean_invalid_json(self):
        field = MultiRelationEntityField(required=False)
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', field.clean, '{"rtype":"10", "ctype":"12","entity":"1"')

    def test_clean_invalid_data_type(self):
        clean = MultiRelationEntityField(required=False).clean
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', clean, '"this is a string"')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', clean, '"{}"')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', clean, '{"rtype":"10", "ctype":"12","entity":"1"}')

    def test_clean_invalid_data(self):
        clean = MultiRelationEntityField(required=False).clean
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', clean, '[{"rtype":"notanumber", ctype":"12","entity":"1"}]')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', clean, '[{"rtype":"10", ctype":"notanumber","entity":"1"}]')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidformat', clean, '[{"rtype":"10", "ctype":"12","entity":"notanumber"}]')

    def test_clean_unknown_rtype(self):
        self.login()
        contact = self.create_contact()

        rtype_id1 = 'test-i_do_not_exist'
        rtype_id2 = 'test-neither_do_i'

        # message changes cause unknown rtype is ignored in allowed list
#        self.assertFieldValidationError(
#                MultiRelationEntityField, 'rtypedoesnotexist',
#                MultiRelationEntityField(allowed_rtypes=[rtype_id1, rtype_id2]).clean,
#                self.format_str % (rtype_id1, contact.entity_type_id, contact.pk)
#            )

        self.assertFieldValidationError(
                MultiRelationEntityField, 'rtypenotallowed',
                MultiRelationEntityField(allowed_rtypes=[rtype_id1, rtype_id2]).clean,
                self.format_str % (rtype_id1, contact.entity_type_id, contact.pk)
            )

    def test_clean_not_allowed_rtype(self):
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]
        rtype3 = RelationType.create(('test-subject_friend', 'is friend of'), ('test-object_friend', 'has friend'))[0]

        self.assertFieldValidationError(
                MultiRelationEntityField, 'rtypenotallowed',
                MultiRelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]).clean,
                self.format_str_2x % (rtype3.id, contact.entity_type_id, contact.pk,
                                      rtype3.id, orga.entity_type_id,    orga.pk,
                                     )
            )

    def test_clean_not_allowed_rtype_queryset(self):
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]
        rtype3 = RelationType.create(('test-subject_friend', 'is friend of'), ('test-object_friend', 'has friend'))[0]

        self.assertFieldValidationError(
                MultiRelationEntityField, 'rtypenotallowed',
                MultiRelationEntityField(allowed_rtypes=RelationType.objects.filter(pk__in=[rtype1.id, rtype2.id])).clean,
                self.format_str_2x % (rtype3.id, contact.entity_type_id, contact.pk,
                                      rtype3.id, orga.entity_type_id,    orga.pk,
                                     )
            )

    def test_clean_ctype_constraint_error(self):
        self.login()
        contact = self.create_contact()
        orga = self.create_orga()

        rtype1 = self.create_employed_rtype()[1]
        rtype2 = self.create_customer_rtype()[1]

        self.assertFieldValidationError(
                MultiRelationEntityField, 'ctypenotallowed',
                MultiRelationEntityField(allowed_rtypes=[rtype2.id, rtype1.id]).clean,
                self.format_str_2x % (rtype1.id, orga.entity_type_id,    orga.id,  #<= not a contact
                                      rtype2.id, contact.entity_type_id, contact.id,
                                     )
            )

    def test_clean_unknown_entity(self):
        self.login()
        contact = self.create_contact()
        orga = self.create_orga()

        rtype1 = self.create_employed_rtype()[1]
        rtype2 = self.create_customer_rtype()[1]

        self.assertFieldValidationError(
                MultiRelationEntityField, 'doesnotexist',
                MultiRelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]).clean,
                self.format_str_2x % (rtype1.id, contact.entity_type_id, orga.pk, #<=== bad ctype !
                                      rtype2.id, contact.entity_type_id, contact.pk,
                                     )
            )

    def test_clean_relations(self):
        self.login()
        contact = self.create_contact()
        orga = self.create_orga()

        rtype_employed, rtype_employs = self.create_employed_rtype()
        rtype_supplier = self.create_customer_rtype()[1]

        field = MultiRelationEntityField(allowed_rtypes=[rtype_supplier.id, rtype_employs.id, rtype_employed.id])
        self.assertEqual([(rtype_employs, contact), (rtype_supplier, contact), (rtype_employed, orga)],
                         field.clean(self.format_str_3x % (rtype_employs.id,  contact.entity_type_id, contact.pk,
                                                           rtype_supplier.id, contact.entity_type_id, contact.pk,
                                                           rtype_employed.id, orga.entity_type_id,    orga.pk
                                                          )
                                    )
                        )

    def test_clean_relations_queryset(self):
        self.login()
        contact = self.create_contact()
        orga = self.create_orga()

        rtype_employed, rtype_employs = self.create_employed_rtype()
        rtype_supplier = self.create_customer_rtype()[1]

        field = MultiRelationEntityField(allowed_rtypes=RelationType.objects.filter(pk__in=[rtype_supplier.id, rtype_employs.id, rtype_employed.id]))
        self.assertEqual([(rtype_employs, contact), (rtype_supplier, contact), (rtype_employed, orga)],
                         field.clean(self.format_str_3x % (rtype_employs.id,  contact.entity_type_id, contact.pk,
                                                           rtype_supplier.id, contact.entity_type_id, contact.pk,
                                                           rtype_employed.id, orga.entity_type_id,    orga.pk
                                                          )
                                    )
                        )

    def test_clean_ctype_without_constraint(self):
        self.login()
        contact = self.create_contact()
        rtype = self.create_loves_rtype()[0]

        field = MultiRelationEntityField(allowed_rtypes=[rtype.id])
        self.assertEqual([(rtype, contact)],
                         field.clean(self.format_str % (rtype.id, contact.entity_type_id, contact.pk))
                        )

    def test_clean_properties_constraint_error(self):
        self.login()
        subject_ptype, object_ptype = self.create_property_types()

        rtype_constr    = self.create_loves_rtype(subject_ptype=subject_ptype, object_ptype=object_ptype)[0]
        rtype_no_constr = self.create_hates_rtype()[0]

        contact = self.create_contact() # <= does not have the property
        orga = self.create_orga()

        self.assertFieldValidationError(MultiRelationEntityField, 'nopropertymatch',
                                        MultiRelationEntityField(allowed_rtypes=[rtype_constr.pk, rtype_no_constr.pk]).clean,
                                        self.format_str_2x % (
                                                rtype_constr.pk,    contact.entity_type.pk, contact.pk,
                                                rtype_no_constr.pk, orga.entity_type_id,    orga.pk,
                                            )
                                       )

    def test_clean_properties_constraint(self):
        self.login()
        subject_ptype, object_ptype = self.create_property_types()

        rtype_constr    = self.create_loves_rtype(subject_ptype=subject_ptype, object_ptype=object_ptype)[0]
        rtype_no_constr = self.create_hates_rtype()[0]

        contact = self.create_contact(ptype=object_ptype) # <= has the property
        orga = self.create_orga()

        field = MultiRelationEntityField(allowed_rtypes=[rtype_constr.pk, rtype_no_constr.pk])
        self.assertEqual([(rtype_constr, contact), (rtype_no_constr, orga)],
                         field.clean(self.format_str_2x % (
                                            rtype_constr.pk,    contact.entity_type.pk, contact.pk,
                                            rtype_no_constr.pk, orga.entity_type_id,    orga.pk,
                                        )
                                    )
                        )

    def test_clean_incomplete01(self): #not required
        self.login()
        rtype  = self.create_loves_rtype()[0]
        contact = self.create_contact()

        clean = MultiRelationEntityField(required=False, allowed_rtypes=[rtype.id]).clean
        self.assertEqual([], clean('[{"rtype": "%s"}]' % rtype.id))
        self.assertEqual([], clean('[{"rtype": "%s", "ctype": "%s"}]' % (rtype.id, contact.entity_type_id)))
        self.assertEqual([(rtype, contact)],
                         clean('[{"rtype": "%s", "ctype": "%s"},'
                               ' {"rtype": "%s", "ctype": "%s", "entity":"%s"},'
                               ' {"rtype": "%s"}]' % (
                                     rtype.id, contact.entity_type_id,
                                     rtype.id, contact.entity_type_id, contact.id,
                                     rtype.id,
                                    )
                              )
                        )

    def test_clean_incomplete02(self): #required -> 'friendly' errors :)
        self.login()
        rtype  = self.create_loves_rtype()[0]
        contact = self.create_contact()

        clean = MultiRelationEntityField(required=True, allowed_rtypes=[rtype.id]).clean
        self.assertFieldValidationError(RelationEntityField, 'required', clean,
                                        '[{"rtype": "%s", "ctype": "%s"}, {"rtype": "%s"}]' % (
                                             rtype.id, contact.entity_type_id,
                                             rtype.id,
                                            )
                                       )
        self.assertEqual([(rtype, contact)],
                         clean('[{"rtype": "%s", "ctype": "%s"},'
                               ' {"rtype": "%s", "ctype": "%s", "entity":"%s"},'
                               ' {"rtype": "%s"}]' % (
                                     rtype.id, contact.entity_type_id,
                                     rtype.id, contact.entity_type_id, contact.id,
                                     rtype.id,
                                    )
                              )
                        )
