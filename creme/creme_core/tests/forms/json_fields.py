# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.db.models.query import Q, QuerySet
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.forms.base import FieldTestCase
    from creme.creme_core.forms.fields import (JSONField, GenericEntityField, MultiGenericEntityField,
                                               RelationEntityField, MultiRelationEntityField,
                                               CreatorEntityField, MultiCreatorEntityField,
                                               FilteredEntityTypeField)
    from creme.creme_core.utils import creme_entity_content_types
    from creme.creme_core.models import CremeProperty, CremePropertyType, RelationType, EntityFilter
    from creme.creme_core.constants import REL_SUB_HAS

    from creme.persons.models import Organisation, Contact

    from creme.documents.models import Document
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('JSONFieldTestCase',
           'GenericEntityFieldTestCase', 'MultiGenericEntityFieldTestCase',
           'RelationEntityFieldTestCase', 'MultiRelationEntityFieldTestCase',
           'CreatorEntityFieldTestCase', 'MultiCreatorEntityFieldTestCase',
           'FilteredEntityTypeFieldTestCase',
          )


class _JSONFieldBaseTestCase(FieldTestCase):
    def create_contact(self, first_name='Eikichi', last_name='Onizuka', ptype=None, **kwargs):
        contact = Contact.objects.create(user=self.user, first_name=first_name,
                                         last_name=last_name, **kwargs
                                        )

        if ptype:
            CremeProperty.objects.create(type=ptype, creme_entity=contact)

        return contact

    def create_orga(self, name='Onibaku', **kwargs):
        return Organisation.objects.create(user=self.user, name=name, **kwargs)

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
        with self.assertNoException():
            JSONField(required=False).clean(None)

    def test_clean_invalid_json(self):
        clean = JSONField(required=True).clean

        self.assertFieldValidationError(JSONField, 'invalidformat', clean, '{"unclosed_dict"')
        self.assertFieldValidationError(JSONField, 'invalidformat', clean, '["unclosed_list",')
        self.assertFieldValidationError(JSONField, 'invalidformat', clean, '["","unclosed_str]')
        self.assertFieldValidationError(JSONField, 'invalidformat', clean, '["" "comma_error"]')

    def test_clean_valid(self):
        with self.assertNoException():
            JSONField(required=True).clean('{"ctype":"12","entity":"1"}')

    def test_clean_json_with_type(self):
        clean_json = JSONField(required=True).clean_json

        with self.assertNoException():
            clean_json('{"ctype":"12","entity":"1"}', dict)
            clean_json('125', int)
            clean_json('[125, 126]', list)

    def test_clean_json_invalid_type(self):
        clean = JSONField(required=True).clean_json

        self.assertFieldValidationError(JSONField, 'invalidtype', clean, '["a", "b"]', int)
        self.assertFieldValidationError(JSONField, 'invalidtype', clean, '["a", "b"]', dict)
        self.assertFieldValidationError(JSONField, 'invalidtype', clean, '152', list)

    def test_FMTing_to_json(self):
        self.assertEqual('', JSONField().from_python(''))

        val = 'this is a string'
        self.assertEqual(val, JSONField().from_python(val))

    def test_format_object_to_json(self):
        self.assertEqual('{"ctype": "12", "entity": "1"}',
                         JSONField().from_python({"ctype": "12", "entity": "1"})
                        )

    def test_clean_entity_from_model(self):
        self.login()
        contact = self.create_contact()
        field = JSONField(required=True)

        clean = field._clean_entity_from_model
        self.assertEqual(contact, clean(Contact, contact.pk))

        self.assertFieldValidationError(JSONField, 'doesnotexist', clean, Organisation, contact.pk)
        self.assertFieldValidationError(JSONField, 'doesnotexist', clean, Contact, 10000)

    def test_clean_filtered_entity_from_model(self):
        self.login()
        contact = self.create_contact()
        field = JSONField(required=True)

        clean = field._clean_entity_from_model
        self.assertEqual(contact, clean(Contact, contact.pk, qfilter=Q(pk=contact.pk)))
        self.assertFieldValidationError(JSONField, 'doesnotexist', clean, Contact, contact.pk, ~Q(pk=contact.pk))


class GenericEntityFieldTestCase(_JSONFieldBaseTestCase):
    FMT = '{"ctype": "%s", "entity": "%s"}'

    def test_models_ctypes(self):
        get_ct = ContentType.objects.get_for_model
        self.assertEqual([get_ct(Organisation), get_ct(Contact), get_ct(Document)],
                         GenericEntityField(models=[Organisation, Contact, Document]).get_ctypes()
                        )

    def test_default_ctypes(self):
        self.autodiscover()

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
        field = GenericEntityField(models=[Organisation, Contact, Document])

        self.assertEqual('{"ctype": 12, "entity": 1}', field.from_python({"ctype": 12, "entity": 1}))
        #self.assertEqual(self.FMT % (contact.entity_type_id, contact.pk),
        self.assertEqual('{"ctype": %s, "entity": %s}' % (contact.entity_type_id, contact.pk),
                         field.from_python(contact)
                        )

    def test_clean_empty_required(self):
        clean = GenericEntityField(required=True).clean
        self.assertFieldValidationError(GenericEntityField, 'required', clean, None)
        self.assertFieldValidationError(GenericEntityField, 'required', clean, "{}")

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            value = GenericEntityField(required=False).clean(None)

        self.assertIsNone(value)

    def test_clean_invalid_json(self):
        self.assertFieldValidationError(GenericEntityField, 'invalidformat',
                                        GenericEntityField(required=False).clean,
                                        '{"ctype":"12","entity":"1"'
                                       )

    def test_clean_invalid_data_type(self):
        clean = GenericEntityField(required=False).clean
        self.assertFieldValidationError(GenericEntityField, 'invalidtype', clean, '"this is a string"')
        self.assertFieldValidationError(GenericEntityField, 'invalidtype', clean, "[]")

    def test_clean_invalid_data(self):
        clean = GenericEntityField(required=False).clean
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', clean, '{"ctype":"notanumber","entity":"1"}')
        self.assertFieldValidationError(GenericEntityField, 'invalidformat', clean, '{"ctype":"12","entity":"notanumber"}')

    def test_clean_unallowed_ctype(self):
        self.login()

        contact = self.create_contact()
        self.assertFieldValidationError(GenericEntityField, 'ctypenotallowed',
                                        GenericEntityField(models=[Organisation, Document]).clean,
                                        self.FMT % (contact.entity_type_id, contact.id)
                                       )

    def test_clean_unknown_entity(self):
        self.login()
        contact = self.create_contact()
        ct_id = ContentType.objects.get_for_model(Document).id #not Contact !!
        self.assertFieldValidationError(GenericEntityField, 'doesnotexist',
                                        GenericEntityField(models=[Organisation, Contact, Document]).clean,
                                        self.FMT % (ct_id, contact.pk)
                                       )

    def test_clean_deleted_entity(self):
        self.login()
        contact = self.create_contact(is_deleted=True)
        self.assertFieldValidationError(GenericEntityField, 'doesnotexist',
                                        GenericEntityField(models=[Organisation, Contact, Document]).clean,
                                        '{"ctype": "%s", "entity": "%s"}' % (contact.entity_type_id, contact.pk)
                                       )

    def test_clean_entity(self):
        self.login()
        contact = self.create_contact()
        field = GenericEntityField(models=[Organisation, Contact, Document])
        self.assertEqual(contact, field.clean(self.FMT % (contact.entity_type_id, contact.pk)))

    def test_clean_incomplete_not_required(self):
        self.login()
        contact = self.create_contact()

        clean = GenericEntityField(models=[Organisation, Contact, Document], required=False).clean
        self.assertFieldValidationError(GenericEntityField, 'ctypenotallowed', clean,
                                        '{"ctype": null}',
                                       )
        self.assertIsNone(clean('{"ctype": "%s"}' % contact.entity_type_id))
        self.assertIsNone(clean('{"ctype": "%s", "entity": null}' % contact.entity_type_id))

    def test_clean_incomplete_required(self):
        "Required -> 'friendly' errors."
        self.login()
        contact = self.create_contact()

        clean = GenericEntityField(models=[Organisation, Contact, Document], required=True).clean
        self.assertFieldValidationError(GenericEntityField, 'ctyperequired', clean,
                                        '{"ctype": null}',
                                       )
        self.assertFieldValidationError(GenericEntityField, 'entityrequired', clean,
                                        '{"ctype": "%s"}' % contact.entity_type_id,
                                       )
        self.assertFieldValidationError(GenericEntityField, 'entityrequired', clean,
                                        '{"ctype": "%s", "entity": null}' % contact.entity_type_id,
                                       )

    def test_autocomplete_property(self):
        field = GenericEntityField()
        self.assertFalse(field.autocomplete)

        field = GenericEntityField(autocomplete=True)
        self.assertTrue(field.autocomplete)

        field.autocomplete = False
        self.assertFalse(field.autocomplete)


class MultiGenericEntityFieldTestCase(_JSONFieldBaseTestCase):
    def test_models_ctypes(self):
        get_ct = ContentType.objects.get_for_model
        models = [Organisation, Contact, Document]
        self.assertEqual([get_ct(model) for model in models],
                         MultiGenericEntityField(models=models).get_ctypes()
                        )

    def test_default_ctypes(self):
        self.autodiscover()

        ctypes = MultiGenericEntityField().get_ctypes()
        self.assertEqual(list(creme_entity_content_types()), ctypes)
        self.assertTrue(ctypes)

    def test_format_object(self):
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        field = MultiGenericEntityField(models=[Organisation, Contact, Document])
        self.assertEqual('[{"ctype": 12, "entity": 1}, {"ctype": 14, "entity": 5}]',
                         field.from_python([{'ctype': 12, 'entity': 1},
                                            {'ctype': 14, 'entity': 5},
                                           ]
                                          )
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
        with self.assertNoException():
            val = MultiGenericEntityField(required=False).clean(None)

        self.assertEqual([], val)

    def test_clean_invalid_json(self):
        clean = MultiGenericEntityField(required=False).clean
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat',
                                        clean, '{"ctype":"12","entity":"1"',
                                       )

    def test_clean_invalid_data_type(self):
        clean = MultiGenericEntityField(required=False).clean
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidtype', clean, '"this is a string"')
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidtype', clean, "{}")

    def test_clean_invalid_data(self):
        clean = MultiGenericEntityField(required=False).clean
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', clean, '[{"ctype":"notanumber","entity":"1"}]')
        self.assertFieldValidationError(MultiGenericEntityField, 'invalidformat', clean, '[{"ctype":"12","entity":"notanumber"}]')

    def test_clean_unallowed_ctype(self):
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        clean = MultiGenericEntityField(models=[Organisation, Document]).clean
        value  = '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (
                        contact.entity_type_id, contact.pk,
                        orga.entity_type_id,    orga.pk
                    )
        self.assertFieldValidationError(MultiGenericEntityField, 'ctypenotallowed', clean, value)

    def test_clean_unknown_entity(self):
        self.login()
        contact1   = self.create_contact()
        contact2   = self.create_contact(first_name='Ryuji', last_name='Danma')
        ct_orga_id = ContentType.objects.get_for_model(Organisation).id

        field = MultiGenericEntityField(models=[Organisation, Contact, Document])
        value = '[{"ctype":"%s","entity":"%s"}, {"ctype":"%s","entity":"%s"}]' % (
                        contact1.entity_type_id, contact1.pk,
                        ct_orga_id,              contact2.pk,
                    )
        self.assertFieldValidationError(MultiGenericEntityField, 'doesnotexist', field.clean, value)

    def test_clean_deleted_entity(self):
        self.login()
        contact = self.create_contact(is_deleted=True)
        field = MultiGenericEntityField(models=[Organisation, Contact, Document])
        self.assertFieldValidationError(MultiGenericEntityField, 'doesnotexist', field.clean,
                                        '[{"ctype":"%s","entity":"%s"}]' % (
                                                contact.entity_type_id, contact.pk
                                            ),
                                       )

    def test_clean_entities(self):
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        field = MultiGenericEntityField(models=[Organisation, Contact])
        self.assertEqual([contact, orga],
                         field.clean('[{"ctype":"%s","entity":"%s"},'
                                     ' {"ctype":"%s","entity":"%s"}]' % (
                                            contact.entity_type_id, contact.pk,
                                            orga.entity_type_id,    orga.pk
                                        )
                                    )
                        )

    def test_clean_duplicates(self):
        "Duplicates are removed"
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        field = MultiGenericEntityField(models=[Organisation, Contact])
        self.assertEqual([contact, orga], # <= contact once
                         field.clean('[{"ctype":"%(contact_ctid)s","entity":"%(contact_id)s"},'
                                     ' {"ctype":"%(orga_ctid)s","entity":"%(orga_id)s"},'
                                     ' {"ctype":"%(contact_ctid)s","entity":"%(contact_id)s"}]'% {
                                            'contact_ctid': contact.entity_type_id,
                                            'contact_id':   contact.pk,
                                            'orga_ctid':    orga.entity_type_id,
                                            'orga_id':      orga.pk,
                                        }
                                    )
                        )

    def test_clean_duplicates_no_unique(self):
        "Duplicates are removed"
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        field = MultiGenericEntityField(models=[Organisation, Contact], unique=False)
        self.assertEqual([contact, orga, contact], # <= contact once
                         field.clean('[{"ctype":"%(contact_ctid)s","entity":"%(contact_id)s"},'
                                     ' {"ctype":"%(orga_ctid)s","entity":"%(orga_id)s"},'
                                     ' {"ctype":"%(contact_ctid)s","entity":"%(contact_id)s"}]'% {
                                            'contact_ctid': contact.entity_type_id,
                                            'contact_id':   contact.pk,
                                            'orga_ctid':    orga.entity_type_id,
                                            'orga_id':      orga.pk,
                                        }
                                    )
                        )

    def test_clean_incomplete_not_required(self):
        "Not required"
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

    def test_clean_incomplete_required(self):
        "Required -> 'friendly' errors :)"
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

    def test_autocomplete_property(self):
        field = MultiGenericEntityField()
        self.assertFalse(field.autocomplete)

        field = MultiGenericEntityField(autocomplete=True)
        self.assertTrue(field.autocomplete)

        field.autocomplete = False
        self.assertFalse(field.autocomplete)


class RelationEntityFieldTestCase(_JSONFieldBaseTestCase):
    FMT = '{"rtype": "%s", "ctype": "%s", "entity": "%s"}'

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
        self.assertEqual([RelationType.objects.get(pk=REL_SUB_HAS)],
                         list(field.allowed_rtypes)
                        )
        self.assertEqual([REL_SUB_HAS], list(field._get_allowed_rtypes_ids()))
        self.assertEqual([RelationType.objects.get(pk=REL_SUB_HAS)],
                         list(field._get_allowed_rtypes_objects())
                        )

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
        self.assertEqual([RelationType.objects.get(pk=REL_SUB_HAS)],
                         list(field.allowed_rtypes)
                        )
        self.assertEqual([REL_SUB_HAS], list(field._get_allowed_rtypes_ids()))
        self.assertEqual([RelationType.objects.get(pk=REL_SUB_HAS)],
                         list(field._get_allowed_rtypes_objects())
                        )

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
        clean = RelationEntityField(required=False).clean
        self.assertFieldValidationError(RelationEntityField, 'invalidtype', clean, '"this is a string"')
        self.assertFieldValidationError(RelationEntityField, 'invalidtype', clean, '"[]"')

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

        #message changes cause unknown rtype is ignored in allowed list
#        self.assertFieldValidationError(
#                RelationEntityField, 'rtypedoesnotexist',
#                RelationEntityField(allowed_rtypes=[rtype_id1, rtype_id2]).clean,
#                self.FMT % (rtype_id1, contact.entity_type_id, contact.pk)
#            )

        self.assertFieldValidationError(
                RelationEntityField, 'rtypenotallowed',
                RelationEntityField(allowed_rtypes=[rtype_id1, rtype_id2]).clean,
                self.FMT % (rtype_id1, contact.entity_type_id, contact.pk)
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
                self.FMT % (rtype3.id, contact.entity_type_id, contact.pk)
            )

    def test_clean_not_allowed_rtype_queryset(self):
        self.login()
        contact = self.create_contact()

        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]
        rtype3 = RelationType.create(('test-subject_friend', 'is friend of'),
                                     ('test-object_friend', 'has friend')
                                    )[0]

        self.assertFieldValidationError(
                RelationEntityField, 'rtypenotallowed',
                RelationEntityField(allowed_rtypes=RelationType.objects.filter(pk__in=[rtype1.id, rtype2.id])).clean,
                self.FMT % (rtype3.id, contact.entity_type_id, contact.pk)
            )

    def test_clean_ctype_constraint_error(self):
        self.login()
        orga = self.create_orga()

        rtype1 = self.create_employed_rtype()[1]
        rtype2 = self.create_customer_rtype()[1]
        self.assertFieldValidationError(
                RelationEntityField, 'ctypenotallowed',
                RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]).clean,
                self.FMT % (rtype1.id, orga.entity_type_id, orga.id) #<= need a contact
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
                self.FMT % (rtype1.id, ct_contact_id, orga.pk)
            )

    def test_clean_deleted_entity(self):
        self.login()
        orga = self.create_orga(is_deleted=True)
        rtype1 = self.create_employed_rtype()[0]
        rtype2 = self.create_customer_rtype()[0]
        self.assertFieldValidationError(
                RelationEntityField, 'doesnotexist',
                RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]).clean,
                self.FMT % (rtype1.id, orga.entity_type_id, orga.pk)
            )

    def test_clean_relation(self):
        self.login()
        contact = self.create_contact()
        rtype1 = self.create_employed_rtype()[1]
        rtype2 = self.create_customer_rtype()[1]

        field = RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id])
        self.assertEqual((rtype1, contact),
                         field.clean(self.FMT % (rtype1.id, contact.entity_type_id, contact.pk))
                        )

    def test_clean_ctype_without_constraint(self):
        self.login()
        contact = self.create_contact()
        rtype = self.create_loves_rtype()[0]

        field = RelationEntityField(allowed_rtypes=[rtype.id])
        self.assertEqual((rtype, contact),
                         field.clean(self.FMT % (rtype.id, contact.entity_type_id, contact.pk))
                        )

    def test_clean_properties_constraint_error(self):
        self.login()
        subject_ptype, object_ptype = self.create_property_types()
        rtype  = self.create_loves_rtype(subject_ptype=subject_ptype, object_ptype=object_ptype)[0]
        contact = self.create_contact() # <= does not have the property

        self.assertFieldValidationError(RelationEntityField, 'nopropertymatch',
                                        RelationEntityField(allowed_rtypes=[rtype.pk]).clean,
                                        self.FMT % (rtype.pk, contact.entity_type_id, contact.pk)
                                       )

    def test_clean_properties_constraint(self):
        self.login()
        subject_ptype, object_ptype = self.create_property_types()
        rtype  = self.create_loves_rtype(subject_ptype=subject_ptype, object_ptype=object_ptype)[0]
        contact = self.create_contact(ptype=object_ptype) # <= has the property

        field = RelationEntityField(allowed_rtypes=[rtype.pk])
        self.assertEqual((rtype, contact),
                         field.clean(self.FMT % (rtype.pk, contact.entity_type_id, contact.pk))
                        )

    def test_clean_incomplete01(self):
        'Not required'
        self.login()
        rtype  = self.create_loves_rtype()[0]
        contact = self.create_contact()

        clean = RelationEntityField(required=False).clean
        self.assertIsNone(clean('{"rtype": "%s"}' % rtype.id))
        self.assertIsNone(clean('{"rtype": "%s", "ctype": "%s"}' % (rtype.id, contact.entity_type_id)))

    def test_clean_incomplete02(self):
        "Required -> 'friendly' errors."
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

    def test_autocomplete_property(self):
        field = RelationEntityField()
        self.assertFalse(field.autocomplete)

        field = RelationEntityField(autocomplete=True)
        self.assertTrue(field.autocomplete)

        field.autocomplete = False
        self.assertFalse(field.autocomplete)


class MultiRelationEntityFieldTestCase(_JSONFieldBaseTestCase):
    FMT    = '[{"rtype":"%s", "ctype":"%s","entity":"%s"}]'
    FMT_2x = '[{"rtype":"%s", "ctype":"%s", "entity":"%s"},' \
                    ' {"rtype":"%s", "ctype":"%s", "entity":"%s"}]'
    FMT_3x = '[{"rtype":"%s", "ctype":"%s", "entity":"%s"},' \
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
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidtype', clean, '"this is a string"')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidtype', clean, '"{}"')
        self.assertFieldValidationError(MultiRelationEntityField, 'invalidtype', clean, '{"rtype":"10", "ctype":"12","entity":"1"}')

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

        #message changes cause unknown rtype is ignored in allowed list
#        self.assertFieldValidationError(
#                MultiRelationEntityField, 'rtypedoesnotexist',
#                MultiRelationEntityField(allowed_rtypes=[rtype_id1, rtype_id2]).clean,
#                self.FMT % (rtype_id1, contact.entity_type_id, contact.pk)
#            )

        self.assertFieldValidationError(
                MultiRelationEntityField, 'rtypenotallowed',
                MultiRelationEntityField(allowed_rtypes=[rtype_id1, rtype_id2]).clean,
                self.FMT % (rtype_id1, contact.entity_type_id, contact.pk)
            )

    def test_clean_not_allowed_rtype(self):
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]
        rtype3 = RelationType.create(('test-subject_friend', 'is friend of'),
                                     ('test-object_friend', 'has friend')
                                    )[0]

        self.assertFieldValidationError(
                MultiRelationEntityField, 'rtypenotallowed',
                MultiRelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]).clean,
                self.FMT_2x % (rtype3.id, contact.entity_type_id, contact.pk,
                               rtype3.id, orga.entity_type_id,    orga.pk,
                              )
            )

    def test_clean_not_allowed_rtype_queryset(self):
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()

        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]
        rtype3 = RelationType.create(('test-subject_friend', 'is friend of'),
                                     ('test-object_friend', 'has friend')
                                    )[0]

        self.assertFieldValidationError(
                MultiRelationEntityField, 'rtypenotallowed',
                MultiRelationEntityField(allowed_rtypes=RelationType.objects.filter(pk__in=[rtype1.id, rtype2.id])).clean,
                self.FMT_2x % (rtype3.id, contact.entity_type_id, contact.pk,
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
                self.FMT_2x % (rtype1.id, orga.entity_type_id,    orga.id,  #<= not a contact
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
                self.FMT_2x % (rtype1.id, contact.entity_type_id, orga.pk, #<=== bad ctype !
                               rtype2.id, contact.entity_type_id, contact.pk,
                              )
            )

    def test_clean_deleted_entity(self):
        self.login()
        contact = self.create_contact(is_deleted=True)

        rtype1 = self.create_employed_rtype()[1]
        rtype2 = self.create_customer_rtype()[1]

        self.assertFieldValidationError(
                MultiRelationEntityField, 'doesnotexist',
                MultiRelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]).clean,
                self.FMT % (rtype1.id, contact.entity_type_id, contact.pk)
            )

    def test_clean_relations(self):
        self.login()
        contact = self.create_contact()
        orga = self.create_orga()

        rtype_employed, rtype_employs = self.create_employed_rtype()
        rtype_supplier = self.create_customer_rtype()[1]

        field = MultiRelationEntityField(allowed_rtypes=[rtype_supplier.id, rtype_employs.id, rtype_employed.id])
        self.assertEqual([(rtype_employs, contact), (rtype_supplier, contact), (rtype_employed, orga)],
                         field.clean(self.FMT_3x % (rtype_employs.id,  contact.entity_type_id, contact.pk,
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
                         field.clean(self.FMT_3x % (rtype_employs.id,  contact.entity_type_id, contact.pk,
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
                         field.clean(self.FMT % (rtype.id, contact.entity_type_id, contact.pk))
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
                                        self.FMT_2x % (
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
                         field.clean(self.FMT_2x % (
                                            rtype_constr.pk,    contact.entity_type.pk, contact.pk,
                                            rtype_no_constr.pk, orga.entity_type_id,    orga.pk,
                                        )
                                    )
                        )

    def test_clean_incomplete01(self):
        "Not required"
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

    def test_clean_incomplete02(self):
        "Required -> 'friendly' errors :)"
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

    def test_format_object(self):
        self.login()
        contact = self.create_contact()
        orga    = self.create_orga()
        rtype1 = self.create_loves_rtype()[0]
        rtype2 = self.create_hates_rtype()[0]

        field = MultiRelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id])
        #TODO: assertJSONEqual
        self.assertEqual('[{"entity": %s, "ctype": %s, "rtype": "%s"}, '
                          '{"entity": %s, "ctype": %s, "rtype": "%s"}]' % (
                                contact.id, contact.entity_type_id, rtype1.id,
                                orga.id,    orga.entity_type_id,    rtype2.id,
                            ),
                         field.from_python([(rtype1, contact), (rtype2, orga)])
                        )

    def test_autocomplete_property(self):
        field = MultiRelationEntityField()
        self.assertFalse(field.autocomplete)

        field = MultiRelationEntityField(autocomplete=True)
        self.assertTrue(field.autocomplete)

        field.autocomplete = False
        self.assertFalse(field.autocomplete)


class CreatorEntityFieldTestCase(_JSONFieldBaseTestCase):
    def test_format_object(self):
        self.login()
        contact = self.create_contact()
        from_python = CreatorEntityField(Contact).from_python

        jsonified = str(contact.pk)

        self.assertEqual(jsonified, from_python(jsonified))
        self.assertEqual(jsonified, from_python(contact))
        self.assertEqual(jsonified, from_python(contact.pk))

    def test_qfilter(self):
        self.login()
        contact = self.create_contact()
        qfilter = {'~pk': contact.pk}
        action_url = '/persons/quickforms/from_widget/%s/1' % contact.entity_type_id

        field = CreatorEntityField(Contact)
        self.assertIsNone(field.q_filter)
        self.assertIsNone(field.q_filter_query)
        self.assertNotEqual(field.create_action_url, action_url)

        # set qfilter
        field.q_filter = qfilter
        self.assertEqual(field.q_filter, qfilter)
        self.assertIsNotNone(field.q_filter_query)
        self.assertNotEqual(field.create_action_url, action_url)

        # set creation url
        field.create_action_url = action_url
        self.assertEqual(field.q_filter, qfilter)
        self.assertIsNotNone(field.q_filter_query)
        self.assertEqual(field.create_action_url, action_url)

        # set both qfilter and creation url in constructor
        field = CreatorEntityField(Contact, q_filter=qfilter, create_action_url=action_url)
        self.assertEqual(field.q_filter, qfilter)
        self.assertIsNotNone(field.q_filter_query)
        self.assertEqual(field.create_action_url, action_url)

    def test_format_object_with_qfilter(self):
        self.login()
        contact = self.create_contact()
        qfilter = {'~pk': contact.pk}
        field = CreatorEntityField(Contact, q_filter=qfilter)

        jsonified = str(contact.pk)

        self.assertEqual(jsonified, field.from_python(jsonified))
        self.assertEqual(jsonified, field.from_python(contact))

        with self.assertRaises(ValueError) as error:
            field.from_python(contact.pk)

        self.assertIn(str(error.exception),
                      ("No such entity with id %d." % contact.pk,
                       "No such entity with id %dL." % contact.pk,
                      )
                     )

    def test_format_object_from_other_model(self):
        self.login()
        contact = self.create_contact()
        orga = self.create_orga()
        field = CreatorEntityField(Contact)

        jsonified = str(contact.pk)

        self.assertEqual(jsonified, field.from_python(jsonified))
        self.assertEqual(jsonified, field.from_python(contact))

        with self.assertRaises(ValueError) as error:
            field.from_python(orga.pk)

        self.assertIn(str(error.exception),
                      ("No such entity with id %d." % orga.pk,
                       "No such entity with id %dL." % orga.pk,
                      )
                     )

    def test_invalid_qfilter(self):
        self.login()
        contact = self.create_contact()
        action_url = '/persons/quickforms/from_widget/%s/1' % contact.entity_type_id

        field = CreatorEntityField(Contact)
        qfilter_errors = ("Invalid q_filter ['~pk', %d]" % contact.pk,
                          "Invalid q_filter ['~pk', %dL]" % contact.pk, # do this hack for MySql database that
                                                                        # uses longs and alter json format result
                         )

        # set qfilter property
        field.q_filter = ['~pk', contact.pk]

        with self.assertRaises(ValueError) as error:
            field.q_filter_query()

        self.assertIn(str(error.exception), qfilter_errors)

        # set qfilter in constructor
        field = CreatorEntityField(Contact, q_filter=['~pk', contact.pk], create_action_url=action_url)

        with self.assertRaises(ValueError) as error:
            field.q_filter_query()

        self.assertIn(str(error.exception), qfilter_errors)

    def test_action_buttons_no_custom_quickform(self):
        self.autodiscover()
        self.login()
        contact = self.create_contact()

        field = CreatorEntityField(Contact, required=False)
        field.user = self.user

        from creme.creme_core.gui import quickforms_registry

        self.assertTrue(field.user.has_perm_to_create(Contact))
        self.assertIsNotNone(quickforms_registry.get_form(Contact))

        self.assertEqual(field.widget.actions,
                         [('reset', _(u'Clear'), True, {'title':_(u'Clear'), 'action':'reset', 'value':''}),
                          ('create', _(u'Add'), True, {'title':_(u'Add'), 'url':field.create_action_url})]
                        )

        field.q_filter = {'~pk': contact.pk}

        self.assertEqual(field.widget.actions,
                         [('reset', _(u'Clear'), True, {'title':_(u'Clear'), 'action':'reset', 'value':''})]
                        )

        field = CreatorEntityField(Contact, q_filter={'~pk': contact.pk}, required=False)
        field.user = self.user

        self.assertEqual(field.widget.actions,
                         [('reset', _(u'Clear'), True, {'title':_(u'Clear'), 'action':'reset', 'value':''})]
                        )

    def test_action_buttons_no_user(self):
        self.login()
        field = CreatorEntityField(Contact, required=False)

        self.assertIsNone(field.user)
        self.assertEqual(field.widget.actions,
                         [('reset', _(u'Clear'), True, {'title':_(u'Clear'), 'action':'reset', 'value':''})]
                        )

    def test_action_buttons_required(self):
        self.login()
        field = CreatorEntityField(Contact)

        self.assertIsNone(field.user)
        self.assertTrue(field.required)
        self.assertEqual(field.widget.actions, [])

    def test_action_buttons_no_quickform(self):
        self.login()

        from creme.creme_core.models import CremeEntity
        from creme.creme_core.gui import quickforms_registry

        field = CreatorEntityField(CremeEntity, required=False)
        field.user = self.user

        self.assertTrue(field.user.has_perm_to_create(CremeEntity))
        self.assertIsNone(quickforms_registry.get_form(CremeEntity))
        self.assertEqual(field.widget.actions,
                         [('reset', _(u'Clear'), True, {'title':_(u'Clear'), 'action':'reset', 'value':''})]
                        )

    def test_action_buttons_not_allowed(self):
        self.autodiscover()
        self.login()

        field = CreatorEntityField(Contact, required=False)
        field.user = self.other_user

        from creme.creme_core.gui import quickforms_registry

        self.assertFalse(field.user.has_perm_to_create(Contact))
        self.assertIsNotNone(quickforms_registry.get_form(Contact))

        self.assertEqual(field.widget.actions,
                         [('reset', _(u'Clear'), True, {'title':_(u'Clear'), 'action':'reset', 'value':''}),
                          ('create', _(u'Add'), False, {'title':_(u"Can't add"), 'url':field.create_action_url})]
                        )

    def test_action_buttons_allowed(self):
        self.autodiscover()
        self.login()

        field = CreatorEntityField(Contact, required=False)
        field.user = self.user

        from creme.creme_core.gui import quickforms_registry

        self.assertTrue(field.user.has_perm_to_create(Contact))
        self.assertIsNotNone(quickforms_registry.get_form(Contact))

        self.assertEqual(field.widget.actions,
                         [('reset', _(u'Clear'), True, {'title':_(u'Clear'), 'action':'reset', 'value':''}),
                          ('create', _(u'Add'), True, {'title':_(u'Add'), 'url':field.create_action_url})]
                        )

    def test_create_action_url(self):
        self.login()

        field = CreatorEntityField(Contact)
        self.assertEqual('/creme_core/quickforms/from_widget/%s/add/1' % ContentType.objects.get_for_model(Contact).pk,
                         field.create_action_url
                        )

        field.create_action_url = '/persons/quickforms/from_widget/contact/add/1'
        self.assertEqual('/persons/quickforms/from_widget/contact/add/1', field.create_action_url)

    def test_clean_empty_required(self):
        clean = CreatorEntityField(Contact, required=True).clean
        self.assertFieldValidationError(CreatorEntityField, 'required', clean, None)
        self.assertFieldValidationError(CreatorEntityField, 'required', clean, "")

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            value = CreatorEntityField(Contact, required=False).clean(None)

        self.assertIsNone(value)

    def test_clean_invalid_json(self):
        field = CreatorEntityField(Contact, required=False)
        self.assertFieldValidationError(CreatorEntityField, 'invalidformat', field.clean, '{12')

    def test_clean_invalid_data_type(self):
        clean = CreatorEntityField(Contact, required=False).clean
        self.assertFieldValidationError(CreatorEntityField, 'invalidtype', clean, '[]')
        self.assertFieldValidationError(CreatorEntityField, 'invalidtype', clean, "{}")

    def test_clean_unknown_entity(self):
        self.login()
        contact = self.create_contact()
        orga = self.create_orga()

        self.assertFieldValidationError(CreatorEntityField, 'doesnotexist',
                                        CreatorEntityField(model=Contact).clean,
                                        str(orga.pk)
                                       )
        self.assertFieldValidationError(CreatorEntityField, 'doesnotexist',
                                        CreatorEntityField(model=Organisation).clean,
                                        str(contact.pk)
                                       )

    def test_clean_deleted_entity(self):
        self.login()
        self.assertFieldValidationError(CreatorEntityField, 'doesnotexist',
                                        CreatorEntityField(model=Contact).clean,
                                        str(self.create_contact(is_deleted=True).pk)
                                       )

    def test_clean_filtered_entity(self):
        self.login()
        contact = self.create_contact()

        field = CreatorEntityField(Contact)
        field.q_filter = {'~pk': contact.pk}

        self.assertFieldValidationError(CreatorEntityField, 'doesnotexist', field.clean, str(contact.pk))

        field.q_filter = {'pk': contact.pk}
        self.assertEqual(contact, field.clean(str(contact.pk)))


class MultiCreatorEntityFieldTestCase(_JSONFieldBaseTestCase):
    def test_format_object(self):
        self.login()

        contact = self.create_contact()

        field = MultiCreatorEntityField(Contact)
        from_python = field.from_python

        self.assertEqual(field.value_type, list)

        jsonified = '[%d]' % contact.pk

        self.assertEqual(jsonified, from_python(jsonified))
        self.assertEqual(jsonified, from_python([contact]))
        self.assertEqual(jsonified, from_python([contact.pk]))
        self.assertEqual('', from_python([]))

    def test_format_object_list(self):
        self.login()

        contact = self.create_contact()
        contact2 = self.create_contact()
        contact3 = self.create_contact()

        field = MultiCreatorEntityField(Contact)
        from_python = field.from_python

        self.assertEqual(field.value_type, list)

        jsonified = '[%d, %d, %d]' % (contact.pk, contact2.pk, contact3.pk)

        self.assertEqual(jsonified, from_python(jsonified))
        self.assertEqual(jsonified, from_python([contact, contact2, contact3]))
        self.assertEqual(jsonified, from_python([contact.pk, contact2.pk, contact3.pk]))

    def test_qfilter(self):
        self.login()
        contact = self.create_contact()
        qfilter = {'~pk': contact.pk}
        action_url = '/persons/quickforms/from_widget/%s/1' % contact.entity_type_id

        field = MultiCreatorEntityField(Contact)
        self.assertIsNone(field.q_filter)

        field.q_filter = qfilter
        self.assertIsNotNone(field.q_filter)

        field = MultiCreatorEntityField(Contact, q_filter=qfilter, create_action_url=action_url)
        self.assertIsNotNone(field.q_filter)
        self.assertEqual(field.create_action_url, action_url)

    def test_format_object_with_qfilter(self):
        self.login()

        contact = self.create_contact()
        contact2 = self.create_contact()
        contact3 = self.create_contact()

        qfilter = {'~pk': contact.pk}
        field = MultiCreatorEntityField(Contact, q_filter=qfilter)

        jsonified = '[%d, %d, %d]' % (contact.pk, contact2.pk, contact3.pk)

        self.assertEqual(jsonified, field.from_python(jsonified))
        self.assertEqual(jsonified, field.from_python([contact, contact2, contact3]))
        self.assertEqual('[%d, %d]' % (contact2.pk, contact3.pk), field.from_python([contact2.pk, contact3.pk]))

        with self.assertRaises(ValueError) as error:
            field.from_python([contact.pk, contact2.pk, contact3.pk])

        self.assertIn(str(error.exception),
                      ("One or more entities with ids [%s] doesn't exists." % ', '.join(str(e.id) for e in [contact, contact2, contact3]),
                       "One or more entities with ids [%s] doesn't exists." % 'L, '.join(str(e.id) for e in [contact, contact2, contact3]),
                      )
                     )

    def test_format_object_from_other_model(self):
        self.login()

        contact = self.create_contact()
        contact2 = self.create_contact()
        orga = self.create_orga()

        field = MultiCreatorEntityField(Contact)

        jsonified = '[%d, %d, %d]' % (orga.pk, contact.pk, contact2.pk)

        self.assertEqual(jsonified, field.from_python(jsonified))
        self.assertEqual(jsonified, field.from_python([orga, contact, contact2]))

        with self.assertRaises(ValueError) as error:
            field.from_python([orga.pk, contact.pk, contact2.pk])

        self.assertIn(str(error.exception),
                      ("One or more entities with ids [%s] doesn't exists." % ', '.join(str(e.id) for e in [orga, contact, contact2]),
                       "One or more entities with ids [%s] doesn't exists." % 'L, '.join(str(e.id) for e in [orga, contact, contact2]),
                      )
                     )

    def test_invalid_qfilter(self):
        self.login()
        contact = self.create_contact()
        action_url = '/persons/quickforms/from_widget/%s/1' % contact.entity_type_id

        field = MultiCreatorEntityField(Contact)
        qfilter_errors = ("Invalid q_filter ['~pk', %d]" % contact.pk,
                          "Invalid q_filter ['~pk', %dL]" % contact.pk, # do this hack for MySql database that
                                                                        # uses longs and alter json format result
                         )

        field.q_filter = ['~pk', contact.pk]

        with self.assertRaises(ValueError) as error:
            field.q_filter_query

        self.assertIn(str(error.exception), qfilter_errors)

        field = MultiCreatorEntityField(Contact, q_filter=['~pk', contact.pk], create_action_url=action_url)

        with self.assertRaises(ValueError) as error:
            field.q_filter_query

        self.assertIn(str(error.exception), qfilter_errors)

    def test_create_action_url(self):
        self.login()

        field = MultiCreatorEntityField(Contact)
        self.assertEqual('/creme_core/quickforms/from_widget/%s/add/1' % ContentType.objects.get_for_model(Contact).pk,
                         field.create_action_url
                        )

        field.create_action_url = '/persons/quickforms/from_widget/contact/add/1'
        self.assertEqual('/persons/quickforms/from_widget/contact/add/1', field.create_action_url)

    def test_clean_empty_required(self):
        clean = MultiCreatorEntityField(Contact, required=True).clean
        self.assertFieldValidationError(MultiCreatorEntityField, 'required', clean, None)
        self.assertFieldValidationError(MultiCreatorEntityField, 'required', clean, "")
        self.assertFieldValidationError(MultiCreatorEntityField, 'required', clean, "[]")

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            value = MultiCreatorEntityField(Contact, required=False).clean(None)

        self.assertEquals(value, [])

        with self.assertNoException():
            value = MultiCreatorEntityField(Contact, required=False).clean("[]")

        self.assertEquals(value, [])

    def test_clean_invalid_json(self):
        field = MultiCreatorEntityField(Contact, required=False)
        self.assertFieldValidationError(MultiCreatorEntityField, 'invalidformat', field.clean, '{12')
        self.assertFieldValidationError(MultiCreatorEntityField, 'invalidformat', field.clean, '[12')

    def test_clean_invalid_data_type(self):
        clean = MultiCreatorEntityField(Contact, required=False).clean
        self.assertFieldValidationError(MultiCreatorEntityField, 'invalidtype', clean, '""')
        self.assertFieldValidationError(MultiCreatorEntityField, 'invalidtype', clean, "{}")
        self.assertFieldValidationError(MultiCreatorEntityField, 'invalidtype', clean, "[{}]")

    def test_clean_unknown_entity(self):
        self.login()
        contact = self.create_contact()
        orga = self.create_orga()

        self.assertFieldValidationError(MultiCreatorEntityField, 'doesnotexist',
                                        MultiCreatorEntityField(model=Contact).clean,
                                        '[%d]' % orga.pk
                                       )
        self.assertFieldValidationError(MultiCreatorEntityField, 'doesnotexist',
                                        MultiCreatorEntityField(model=Organisation).clean,
                                        '[%d]' % contact.pk
                                       )

    def test_clean_deleted_entity(self):
        self.login()
        self.assertFieldValidationError(MultiCreatorEntityField, 'doesnotexist',
                                        MultiCreatorEntityField(model=Contact).clean,
                                        '[%d]' % self.create_contact(is_deleted=True).pk
                                       )

    def test_clean_entities(self):
        self.login()
        contact = self.create_contact()
        contact2 = self.create_contact()

        field = MultiCreatorEntityField(Contact)
        self.assertEqual([contact, contact2], field.clean('[%d, %d]' % (contact.pk, contact2.pk)))

    def test_clean_filtered_entities(self):
        self.login()
        contact = self.create_contact()

        field = MultiCreatorEntityField(Contact)
        field.q_filter = {'~pk': contact.pk}

        self.assertFieldValidationError(MultiCreatorEntityField, 'doesnotexist', field.clean, '[%d]' % contact.pk)

        field.q_filter = {'pk': contact.pk}
        self.assertEqual([contact], field.clean('[%d]' % contact.pk))


class FilteredEntityTypeFieldTestCase(_JSONFieldBaseTestCase):
    format_str = '{"ctype": "%s", "efilter": "%s"}'

    @classmethod
    def setUpClass(cls):
        cls.autodiscover()

        get_ct = ContentType.objects.get_for_model
        cls.ct_contact = get_ct(Contact)
        cls.ct_orga    = get_ct(Organisation)

    def test_clean_empty_required(self):
        clean = FilteredEntityTypeField(required=True).clean
        self.assertFieldValidationError(FilteredEntityTypeField, 'required', clean, None)
        self.assertFieldValidationError(FilteredEntityTypeField, 'required', clean, '')

    def test_clean_invalid_json(self):
        field = FilteredEntityTypeField(required=False)
        self.assertFieldValidationError(FilteredEntityTypeField, 'invalidformat', field.clean,
                                        '{"ctype":"10", "efilter":"creme_core-testfilter"'
                                       )

    def test_clean_invalid_data_type(self):
        clean = FilteredEntityTypeField(required=False).clean
        self.assertFieldValidationError(FilteredEntityTypeField, 'invalidtype', clean, '"this is a string"')
        self.assertFieldValidationError(FilteredEntityTypeField, 'invalidtype', clean, '"{}"')
        self.assertFieldValidationError(FilteredEntityTypeField, 'invalidformat', clean, '{"ctype":"not_an_int", "efilter":"creme_core-testfilter"}')

    def test_clean_required_ctype(self):
        self.assertFieldValidationError(FilteredEntityTypeField, 'ctyperequired',
                                        FilteredEntityTypeField(required=True).clean,
                                        self.format_str % ('', '')
                                       )

    def test_clean_unknown_ctype(self):
        self.assertFieldValidationError(FilteredEntityTypeField, 'ctypenotallowed',
                                        FilteredEntityTypeField().clean,
                                        self.format_str % (1024, '')
                                       )

    def test_clean_unallowed_ctype01(self):
        "Allowed ContentTypes given as a list of ContentType instances"
        ctypes = [self.ct_contact]
        error_msg = self.format_str % (self.ct_orga.id, '')

        field = FilteredEntityTypeField(ctypes=ctypes)
        self.assertEqual(ctypes, field.ctypes)

        from creme.creme_core.forms.widgets import FilteredEntityTypeWidget
        self.assertIsInstance(field.widget, FilteredEntityTypeWidget)

        self.assertFieldValidationError(FilteredEntityTypeField, 'ctypenotallowed',
                                        field.clean, error_msg
                                       )

        #use setter
        field = FilteredEntityTypeField()
        field.ctypes = ctypes
        self.assertFieldValidationError(FilteredEntityTypeField, 'ctypenotallowed',
                                        field.clean, error_msg
                                       )

    def test_clean_unallowed_ctype02(self):
        "Allowed ContentTypes given as a list of ID"
        ctypes = [self.ct_contact.id]
        error_msg = self.format_str % (self.ct_orga.id, '')

        self.assertFieldValidationError(FilteredEntityTypeField, 'ctypenotallowed',
                                        FilteredEntityTypeField(ctypes=ctypes).clean,
                                        error_msg
                                       )

        #use setter
        field = FilteredEntityTypeField()
        field.ctypes = ctypes
        self.assertFieldValidationError(FilteredEntityTypeField, 'ctypenotallowed',
                                        field.clean, error_msg
                                       )

    def test_clean_unallowed_ctype03(self):
        "Allowed ContentTypes given as a list of ID & instances"
        ctypes = [self.ct_contact.id, self.ct_orga]

        self.assertFieldValidationError(FilteredEntityTypeField, 'ctypenotallowed',
                                        FilteredEntityTypeField(ctypes=ctypes).clean,
                                        self.format_str % (ContentType.objects.get_for_model(Document).id, '')
                                       )

    def test_clean_unknown_efilter01(self):
        "EntityFilter does not exist"
        self.assertFieldValidationError(FilteredEntityTypeField, 'invalidefilter',
                                        FilteredEntityTypeField().clean,
                                        self.format_str % (self.ct_contact.id, 'idonotexist')
                                       )

    def test_clean_unknown_efilter02(self):
        "Content type does not correspond to EntityFilter"
        efilter = EntityFilter.create('test-filter01', 'Acme', Organisation)
        self.assertFieldValidationError(FilteredEntityTypeField, 'invalidefilter',
                                        FilteredEntityTypeField().clean,
                                        self.format_str % (self.ct_contact.id, efilter.id)
                                       )

    def test_clean_void(self):
        field = FilteredEntityTypeField(required=False)
        self.assertEqual((None, None), field.clean(self.format_str % ('', '')))
        self.assertEqual((None, None), field.clean('{"ctype": "0", "efilter": null}'))

    def test_clean_only_ctype01(self):
        "All element of this ContentType are allowed"
        field = FilteredEntityTypeField()
        self.assertEqual((self.ct_contact, None),
                         field.clean(self.format_str % (self.ct_contact.id, ''))
                        )

    def test_clean_only_ctype02(self):
        "Allowed ContentTypes given as a sequence of instance/id"
        ct_contact = self.ct_contact
        ct_orga    = self.ct_orga

        field = FilteredEntityTypeField([ct_contact, ct_orga.id])
        self.assertEqual((ct_contact, None),
                         field.clean(self.format_str % (ct_contact.id, ''))
                        )
        self.assertEqual((ct_orga, None),
                         field.clean(self.format_str % (ct_orga.id, ''))
                        )

    def test_clean_with_filter01(self):
        efilter = EntityFilter.create('test-filter01', 'John', Contact)
        field = FilteredEntityTypeField()
        ct = self.ct_contact
        self.assertEqual((ct, efilter),
                         field.clean(self.format_str % (ct.id, efilter.id))
                        )
