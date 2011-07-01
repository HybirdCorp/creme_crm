# -*- coding: utf-8 -*-

from django.http import Http404
from django.core.serializers.json import simplejson
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, Relation, CremeEntity, CremePropertyType, CremeProperty, SetCredentials
from creme_core.tests.views.base import ViewsTestCase

from persons.models import Contact, Organisation
from persons.constants import REL_OBJ_CUSTOMER_SUPPLIER


__all__ = ('RelationViewsTestCase', )


class RelationViewsTestCase(ViewsTestCase):
    def test_get_ctypes_of_relation(self):
        self.login()
        self.populate('creme_core', 'persons')

        response = self.client.get('/creme_core/relation/predicate/%s/content_types/json' % REL_OBJ_CUSTOMER_SUPPLIER,
                                   data={'fields': ['id', 'unicode']}
                                  )
        self.assertEqual(200,               response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        json_data = simplejson.loads(response.content)
        get_ct = ContentType.objects.get_for_model
        self.assertEqual(json_data, [[get_ct(Contact).id,      Contact._meta.verbose_name],
                                     [get_ct(Organisation).id, Organisation._meta.verbose_name]
                                    ]
                        )

    def _aux_test_add_relations(self, is_superuser=True):
        self.login(is_superuser)

        create_entity = CremeEntity.objects.create
        self.subject01 = create_entity(user=self.user)
        self.subject02 = create_entity(user=self.user)
        self.object01  = create_entity(user=self.user)
        self.object02  = create_entity(user=self.user)

        self.ct_id = ContentType.objects.get_for_model(CremeEntity).id

        self.rtype01, srtype01 = RelationType.create(('test-subject_foobar1', 'is loving'),
                                                     ('test-object_foobar1',  'is loved by')
                                                    )
        self.rtype02, srtype02 = RelationType.create(('test-subject_foobar2', 'is hating'),
                                                     ('test-object_foobar2',  'is hated by')
                                                    )

    def assertEntiTyHasRelation(self, subject_entity, rtype, object_entity):
        try:
            relation = subject_entity.relations.get(type=rtype)
        except Exception, e:
            self.fail(str(e))
        else:
            self.assertEqual(object_entity.id, relation.object_entity_id)

    def test_add_relations01(self):
        self._aux_test_add_relations()
        self.assertEqual(0, self.subject01.relations.count())

        url = '/creme_core/relation/add/%s' % self.subject01.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={
                                                'relations': """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                                 {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
                                                                    self.rtype01.id, self.ct_id, self.object01.id,
                                                                    self.rtype02.id, self.ct_id, self.object02.id,
                                                                ),
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(2, self.subject01.relations.count())
        self.assertEntiTyHasRelation(self.subject01, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject01, self.rtype02, self.object02)

    def test_add_relations02(self):
        self.login(is_superuser=False)
        subject = CremeEntity.objects.create(user=self.other_user)
        self.assertEqual(403, self.client.get('/creme_core/relation/add/%s' % subject.id).status_code)

    def test_add_relations03(self):
        self._aux_test_add_relations(is_superuser=False)
        self._set_all_creds_except_one(excluded=SetCredentials.CRED_LINK)

        unlinkable = CremeEntity.objects.create(user=self.other_user)
        self.assert_(unlinkable.can_view(self.user))
        self.failIf(unlinkable.can_link(self.user))

        response = self.client.post('/creme_core/relation/add/%s' % self.subject01.id,
                                    data={
                                            'relations': """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                             {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
                                                                self.rtype01.id, self.ct_id, self.object01.id,
                                                                self.rtype02.id, self.ct_id, unlinkable.id,
                                                            ),
                                         }
                                   )
        try:
            form = response.context['form']
        except Exception, e:
            self.fail('No form in context ? (%s)', str(e))

        if not form.errors:
            self.fail('Not the excepted error in form.')

        self.assertEqual(['relations'], form.errors.keys())
        self.assertEqual(0, self.subject01.relations.count())

    def test_add_relations04(self): #duplicates -> error
        self._aux_test_add_relations()

        response = self.client.post('/creme_core/relation/add/%s' % self.subject01.id,
                                    data={
                                            'relations': """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                             {"rtype":"%s","ctype":"%s","entity":"%s"},
                                                             {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
                                                                self.rtype01.id, self.ct_id, self.object01.id,
                                                                self.rtype02.id, self.ct_id, self.object02.id,
                                                                self.rtype01.id, self.ct_id, self.object01.id,
                                                            ),
                                         }
                                   )
        try:
            form = response.context['form']
        except Exception, e:
            self.fail('No form in context ? (%s)', str(e))

        if not form.errors:
            self.fail('Not the excepted error in form.')

        self.assertEqual(['relations'], form.errors.keys())

    def test_add_relations05(self): #do not recreate existing relations
        self._aux_test_add_relations()

        Relation.objects.create(user=self.user,
                                subject_entity=self.subject01,
                                type=self.rtype02,
                                object_entity=self.object02
                               )
        response = self.client.post('/creme_core/relation/add/%s' % self.subject01.id,
                                    data={
                                            'relations': """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                             {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
                                                                self.rtype01.id, self.ct_id, self.object01.id,
                                                                self.rtype02.id, self.ct_id, self.object02.id,
                                                            ),
                                          }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(2, self.subject01.relations.count()) #and not 3

    def test_add_relations_bulk01(self):
        self._aux_test_add_relations()

        #this relation should not be recreated by the view
        Relation.objects.create(user=self.user,
                                subject_entity=self.subject02,
                                type=self.rtype02,
                                object_entity=self.object02
                               )

        url = '/creme_core/relation/add_to_entities/%s/%s,%s,' % (self.ct_id, self.subject01.id, self.subject02.id)
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={
                                                'entities_lbl': 'wtf',
                                                'relations':    """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                                    {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
                                                                    self.rtype01.id, self.ct_id, self.object01.id,
                                                                    self.rtype02.id, self.ct_id, self.object02.id,
                                                                   ),
                                              })
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        self.assertEqual(2, self.subject01.relations.count())
        self.assertEntiTyHasRelation(self.subject01, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject01, self.rtype02, self.object02)

        self.assertEqual(2, self.subject02.relations.count()) #and not 3
        self.assertEntiTyHasRelation(self.subject02, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject02, self.rtype02, self.object02)

    def test_add_relations_bulk02(self):
        self._aux_test_add_relations(is_superuser=False)

        unviewable = CremeEntity.objects.create(user=self.other_user)
        self.failIf(unviewable.can_view(self.user))

        url = '/creme_core/relation/add_to_entities/%s/%s,%s,' % (self.ct_id, self.subject01.id, unviewable.id)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            label = response.context['form'].fields['bad_entities_lbl']
        except Exception, e:
            self.fail(str(e))

        self.assert_(label.initial)

        response = self.client.post(url, data={
                                                'entities_lbl':     'do not care',
                                                'bad_entities_lbl': 'do not care',
                                                'relations':        """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                                        {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
                                                                            self.rtype01.id, self.ct_id, self.object01.id,
                                                                            self.rtype02.id, self.ct_id, self.object02.id,
                                                                           ),
                                              })
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(2,   self.subject01.relations.count())
        self.assertEqual(0,   unviewable.relations.count())

    def test_add_relations_bulk03(self):
        self._aux_test_add_relations(is_superuser=False)

        self._set_all_creds_except_one(excluded=SetCredentials.CRED_LINK)
        unlinkable = CremeEntity.objects.create(user=self.other_user)
        self.assert_(unlinkable.can_view(self.user))
        self.failIf(unlinkable.can_link(self.user))

        response = self.client.get('/creme_core/relation/add_to_entities/%s/%s,%s,' % (self.ct_id, self.subject01.id, unlinkable.id))
        self.assertEqual(200, response.status_code)

        try:
            label = response.context['form'].fields['bad_entities_lbl']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(unicode(unlinkable), label.initial)

    def test_add_relations_bulk04(self):
        self._aux_test_add_relations(is_superuser=False)

        url = '/creme_core/relation/add_to_entities/%s/%s,' % (self.ct_id, self.subject01.id)
        self.assertEqual(200, self.client.get(url).status_code)

        self._set_all_creds_except_one(excluded=SetCredentials.CRED_LINK)
        unlinkable = CremeEntity.objects.create(user=self.other_user)

        response = self.client.post(url, data={
                                                'entities_lbl': 'wtf',
                                                'relations':    '[{"rtype":"%s","ctype":"%s","entity":"%s"}]' % (
                                                                    self.rtype01.id, self.ct_id, unlinkable.id
                                                                   ),
                                              })
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail('No form in context ? (%s)', str(e))

        if not form.errors:
            self.fail('Not the excepted error in form.')

        self.assertEqual(['relations'], form.errors.keys())

    def test_add_relations_bulk_fixedrtypes01(self):
        self._aux_test_add_relations()

        #this relation should not be recreated by the view
        Relation.objects.create(user=self.user,
                                subject_entity=self.subject02,
                                type=self.rtype02,
                                object_entity=self.object02
                               )

        url = '/creme_core/relation/add_to_entities/%s/%s,%s,/%s,%s,' % (
                    self.ct_id, self.rtype01.id, self.rtype02.id, self.subject01.id, self.subject02.id
                )
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={
                                                'entities_lbl': 'wtf',
                                                'relations':    """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                                    {"rtype":"%s","ctype":"%s","entity":"%s"}]""" % (
                                                                    self.rtype01.id, self.ct_id, self.object01.id,
                                                                    self.rtype02.id, self.ct_id, self.object02.id,
                                                                   ),
                                              })

        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        self.assertEqual(2, self.subject01.relations.count())
        self.assertEntiTyHasRelation(self.subject01, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject01, self.rtype02, self.object02)

        self.assertEqual(2, self.subject02.relations.count()) #and not 3
        self.assertEntiTyHasRelation(self.subject02, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject02, self.rtype02, self.object02)

    def test_add_relations_bulk_fixedrtypes02(self):
        self._aux_test_add_relations()

        url = '/creme_core/relation/add_to_entities/%s/%s/%s,%s,' % (
                    self.ct_id, self.rtype01.id, self.subject01.id, self.subject02.id
                )
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={
                                                'entities_lbl': 'wtf',
                                                'relations': """[{"rtype":"%s","ctype":"%s","entity":"%s"},
                                                                 {"rtype":"%s","ctype":"%s","entity":"%s"}]"""  % (
                                                                self.rtype02.id, self.ct_id, self.object01.id,
                                                                self.rtype02.id, self.ct_id, self.object02.id,
                                                               ),
                                              })
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            self.fail('No form in context ? (%s)', str(e))

        if not form.errors:
            self.fail('Not the excepted error in form.')

        self.assertEqual(['relations'], form.errors.keys())

    def _aux_relation_objects_to_link_selection(self):
        self.populate('creme_core', 'persons')
        self.login()

        self.assertEqual(1, Contact.objects.count())
        self.contact01 = Contact.objects.all()[0] #NB: Fulbert Creme

        self.subject   = CremeEntity.objects.create(user=self.user)
        self.contact02 = Contact.objects.create(user=self.user, first_name='Laharl', last_name='Overlord')
        self.contact03 = Contact.objects.create(user=self.user, first_name='Etna',   last_name='Devil')
        self.orga01    = Organisation.objects.create(user=self.user, name='Earth Defense Force')

        self.ct_contact = ContentType.objects.get_for_model(Contact)

        self.rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving',   [Contact]),
                                                    ('test-object_foobar',  'is loved by', [Contact])
                                                   )

    def test_objects_to_link_selection01(self):
        self._aux_relation_objects_to_link_selection()

        response = self.client.get('/creme_core/relation/objects2link/rtype/%s/entity/%s/%s' % \
                                        (self.rtype.id, self.subject.id, self.ct_contact.id)
                                  )
        self.assertEqual(200, response.status_code)

        try:
            entities = response.context['entities']
        except Exception, e:
            self.fail('%s : %s' % (e.__class__.__name__, str(e)))

        contacts = entities.object_list
        self.assertEqual(3, len(contacts))
        self.assert_(all(isinstance(c, Contact) for c in contacts))
        self.assertEqual(set([self.contact01.id, self.contact02.id, self.contact03.id]),
                         set(c.id for c in contacts)
                        )

    def test_objects_to_link_selection02(self):
        self._aux_relation_objects_to_link_selection()

        #contact03 will not be proposed by the listview
        Relation.objects.create(user=self.user, type=self.rtype, subject_entity=self.subject, object_entity=self.contact03)

        response = self.client.get('/creme_core/relation/objects2link/rtype/%s/entity/%s/%s' % \
                                        (self.rtype.id, self.subject.id, self.ct_contact.id)
                                  )
        self.assertEqual(200, response.status_code)

        contacts = response.context['entities'].object_list
        self.assertEqual(2, len(contacts))
        self.assertEqual(set([self.contact01.id, self.contact02.id]), set(c.id for c in contacts))

    def test_objects_to_link_selection03(self):
        self._aux_relation_objects_to_link_selection()

        ptype01 = CremePropertyType.create(str_pk='test-prop_foobar01', text='Is lovable')
        ptype02 = CremePropertyType.create(str_pk='test-prop_foobar02', text='Is a girl')

        contact04 = Contact.objects.create(user=self.user, first_name='Flonne', last_name='Angel')

        #contact02 will not be proposed by the listview
        create_property = CremeProperty.objects.create
        create_property(type=ptype01, creme_entity=self.contact01)
        create_property(type=ptype02, creme_entity=self.contact03)
        create_property(type=ptype01, creme_entity=contact04)
        create_property(type=ptype02, creme_entity=contact04)

        rtype, sym_rtype = RelationType.create(('test-subject_loving', 'is loving',   [Contact]),
                                               ('test-object_loving',  'is loved by', [Contact], [ptype01, ptype02])
                                              )

        response = self.client.get('/creme_core/relation/objects2link/rtype/%s/entity/%s/%s' % \
                                        (rtype.id, self.subject.id, self.ct_contact.id)
                                  )
        self.assertEqual(200, response.status_code)

        contacts = response.context['entities'].object_list
        self.assertEqual(3, len(contacts))
        self.assertEqual(set([self.contact01.id, self.contact03.id, contact04.id]), set(c.id for c in contacts))

    def test_objects_to_link_selection04(self):
        self.login()

        subject = CremeEntity.objects.create(user=self.user)
        ct_id = ContentType.objects.get_for_model(Contact).id
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving',   [Contact]),
                                               ('test-object_foobar',  'is loved by', [Contact]),
                                               is_internal=True
                                              )

        response = self.client.get('/creme_core/relation/objects2link/rtype/%s/entity/%s/%s' % \
                                        (rtype.id, subject.id, ct_id)
                                  )
        self.assertEqual(404, response.status_code)

    def _aux_add_relations_with_same_type(self):
        self.subject  = CremeEntity.objects.create(user=self.user)
        self.object01 = CremeEntity.objects.create(user=self.user)
        self.object02 = CremeEntity.objects.create(user=self.user)
        self.rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving',),
                                                    ('test-object_foobar',  'is loved by',)
                                                   )

    def test_add_relations_with_same_type01(self): #no errors
        self.login()
        self._aux_add_relations_with_same_type()

        object_ids = [self.object01.id, self.object02.id]
        response = self.client.post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   self.subject.id,
                                            'predicate_id': self.rtype.id,
                                            'entities':     object_ids,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2,   Relation.objects.filter(type=self.rtype.id).count())

        relations = self.subject.relations.filter(type=self.rtype.id)
        self.assertEqual(2, len(relations))
        self.assertEqual(set(object_ids), set(r.object_entity_id for r in relations))

    def test_add_relations_with_same_type02(self): #an entity does not exist
        self.login()
        self._aux_add_relations_with_same_type()

        response = self.client.post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   self.subject.id,
                                            'predicate_id': self.rtype.id,
                                            'entities':     [self.object01.id, self.object02.id, self.object02.id + 1],
                                         }
                                   )
        self.assertEqual(404, response.status_code)
        self.assertEqual(2,   Relation.objects.filter(type=self.rtype.id).count())

    def test_add_relations_with_same_type03(self): #errors
        self.login()
        self._aux_add_relations_with_same_type()
        post = self.client.post

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   self.subject.id,
                                            'predicate_id': 'IDONOTEXIST',
                                            'entities':     [self.object01.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   1024,
                                            'predicate_id': self.rtype.id,
                                            'entities':     [self.object01.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'predicate_id': self.rtype.id,
                                            'entities':     [self.object01.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id': self.subject.id,
                                            'entities':   [self.object01.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   self.subject.id,
                                            'predicate_id': self.rtype.id,
                                         }
                                  ).status_code
                        )

    def test_add_relations_with_same_type04(self): #credentials errors
        self.login(is_superuser=False)
        self._set_all_creds_except_one(excluded=SetCredentials.CRED_LINK)

        forbidden = CremeEntity.objects.create(user=self.other_user)
        allowed01 = CremeEntity.objects.create(user=self.user)
        allowed02 = CremeEntity.objects.create(user=self.user)
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving',),
                                               ('test-object_foobar',  'is loved by',)
                                              )

        post = self.client.post

        self.failIf(forbidden.can_link(self.user))
        self.assert_(allowed01.can_link(self.user))

        self.assertEqual(403, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   forbidden.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [allowed01.id, allowed02.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(0, Relation.objects.filter(type=rtype.id).count())

        self.assertEqual(403, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   allowed01.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [forbidden.id, allowed02.id, 1024],
                                         }
                                  ).status_code
                        )
        relations = Relation.objects.filter(type=rtype.id)
        self.assertEqual(1, len(relations))

        relation = relations[0]
        self.assertEqual(allowed01.id, relation.subject_entity_id)
        self.assertEqual(allowed02.id, relation.object_entity_id)

    def test_add_relations_with_same_type05(self): #ct constraint errors
        self.login()

        orga01    = Organisation.objects.create(user=self.user, name='orga01')
        orga02    = Organisation.objects.create(user=self.user, name='orga02')
        contact01 = Contact.objects.create(user=self.user, first_name='John', last_name='Doe')
        contact02 = Contact.objects.create(user=self.user, first_name='Joe',  last_name='Gohn')

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [Contact]),
                                               ('test-object_foobar',  'is managed by', [Organisation])
                                              )

        post = self.client.post

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   orga01.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [orga02.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(0, Relation.objects.filter(type=rtype.id).count())

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   contact01.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [orga01.id, contact02.id],
                                         }
                                  ).status_code
                        )
        relations = Relation.objects.filter(type=rtype.id)
        self.assertEqual(1,         len(relations))
        self.assertEqual(orga01.id, relations[0].object_entity_id)

    def test_add_relations_with_same_type06(self): #property constraint errors
        self.login()

        subject_ptype = CremePropertyType.create(str_pk='test-prop_foobar01', text='Subject property')
        object_ptype  = CremePropertyType.create(str_pk='test-prop_foobar02', text='Contact property')

        bad_subject  = CremeEntity.objects.create(user=self.user)
        good_subject = CremeEntity.objects.create(user=self.user)
        bad_object   = CremeEntity.objects.create(user=self.user)
        good_object  = CremeEntity.objects.create(user=self.user)

        CremeProperty.objects.create(type=subject_ptype, creme_entity=good_subject)
        CremeProperty.objects.create(type=object_ptype, creme_entity=good_object)

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [], [subject_ptype]),
                                               ('test-object_foobar',  'is managed by', [], [object_ptype])
                                              )

        post = self.client.post

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   bad_subject.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [good_object.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(0, Relation.objects.filter(type=rtype.id).count())

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   good_subject.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [good_object.id, bad_object.id],
                                         }
                                  ).status_code
                        )
        relations = Relation.objects.filter(type=rtype.id)
        self.assertEqual(1,              len(relations))
        self.assertEqual(good_object.id, relations[0].object_entity_id)

    def test_add_relations_with_same_type07(self): #is_internal
        self.login()

        subject  = CremeEntity.objects.create(user=self.user)
        object01 = CremeEntity.objects.create(user=self.user)
        object02 = CremeEntity.objects.create(user=self.user)
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving',),
                                               ('test-object_foobar',  'is loved by',),
                                               is_internal=True
                                              )
        response = self.client.post('/creme_core/relation/add_from_predicate/save',
                                    data={
                                            'subject_id':   subject.id,
                                            'predicate_id': rtype.id,
                                            'entities':     [object01.id, object02.id],
                                         }
                                   )
        self.assertEqual(404, response.status_code)
        self.assertEqual(0,   Relation.objects.filter(type=rtype.id).count())

    def test_delete01(self):
        self.login()

        subject_entity = CremeEntity.objects.create(user=self.user)
        object_entity  = CremeEntity.objects.create(user=self.user)

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving'), ('test-object_foobar',  'is loved by'))
        relation = Relation.objects.create(user=self.user, type=rtype, subject_entity=subject_entity, object_entity=object_entity)
        sym_relation = relation.symmetric_relation
        self.assert_(rtype.is_not_internal_or_die() is None)

        response = self.client.post('/creme_core/relation/delete', data={'id': relation.id})
        self.assertEqual(302, response.status_code)

        self.assertEqual(0, Relation.objects.filter(pk__in=[relation.pk, sym_relation.pk]).count())

    def test_delete02(self):
        self.login(is_superuser=False)

        self._set_all_creds_except_one(excluded=SetCredentials.CRED_UNLINK)

        allowed   = CremeEntity.objects.create(user=self.user)
        forbidden = CremeEntity.objects.create(user=self.other_user)
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving'), ('test-object_foobar', 'is loved by'))

        relation = Relation.objects.create(user=self.user, type=rtype, subject_entity=allowed, object_entity=forbidden)
        self.assertEqual(403, self.client.post('/creme_core/relation/delete', data={'id': relation.id}).status_code)
        self.assertEqual(1,   Relation.objects.filter(pk=relation.pk).count())

        relation = Relation.objects.create(user=self.user, type=rtype, subject_entity=forbidden, object_entity=allowed)
        self.assertEqual(403, self.client.post('/creme_core/relation/delete', data={'id': relation.id}).status_code)
        self.assertEqual(1,   Relation.objects.filter(pk=relation.pk).count())

    def test_delete03(self): #is internal
        self.login()

        subject_entity = CremeEntity.objects.create(user=self.user)
        object_entity  = CremeEntity.objects.create(user=self.user)

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving'), ('test-object_foobar',  'is loved by'), is_internal=True)
        self.assert_(rtype.is_internal)
        self.assert_(sym_rtype.is_internal)
        self.assertRaises(Http404, rtype.is_not_internal_or_die)

        relation = Relation.objects.create(user=self.user, type=rtype, subject_entity=subject_entity, object_entity=object_entity)
        self.assertEqual(404, self.client.post('/creme_core/relation/delete', data={'id': relation.id}).status_code)
        self.assertEqual(1, Relation.objects.filter(pk=relation.pk).count())

    def test_delete_similar01(self):
        self.login()

        subject_entity01 = CremeEntity.objects.create(user=self.user)
        object_entity01  = CremeEntity.objects.create(user=self.user)

        subject_entity02 = CremeEntity.objects.create(user=self.user)
        object_entity02  = CremeEntity.objects.create(user=self.user)

        rtype01, useless = RelationType.create(('test-subject_love', 'is loving'), ('test-object_love', 'is loved by'))
        rtype02, useless = RelationType.create(('test-subject_son',  'is son of'), ('test-object_son',  'is parent of'))

        #will be deleted (normally)
        relation01 = Relation.objects.create(user=self.user, type=rtype01, subject_entity=subject_entity01, object_entity=object_entity01)
        relation02 = Relation.objects.create(user=self.user, type=rtype01, subject_entity=subject_entity01, object_entity=object_entity01)

        #won't be deleted (normally)
        relation03 = Relation.objects.create(user=self.user, type=rtype01, subject_entity=subject_entity01, object_entity=object_entity02) #different object
        relation04 = Relation.objects.create(user=self.user, type=rtype01, subject_entity=subject_entity02, object_entity=object_entity01) #different subject
        relation05 = Relation.objects.create(user=self.user, type=rtype02, subject_entity=subject_entity01, object_entity=object_entity01) #different type

        self.assertEqual(10, Relation.objects.count())

        response = self.client.post('/creme_core/relation/delete/similar',
                                    data={
                                            'subject_id': subject_entity01.id,
                                            'type':       rtype01.id,
                                            'object_id':  object_entity01.id,
                                         }
                                   )
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   Relation.objects.filter(pk__in=[relation01.pk, relation02.pk]).count())
        self.assertEqual(3,   Relation.objects.filter(pk__in=[relation03.pk, relation04.pk, relation05.pk]).count())

    def test_delete_similar02(self):
        self.login(is_superuser=False)
        self._set_all_creds_except_one(excluded=SetCredentials.CRED_UNLINK)

        allowed   = CremeEntity.objects.create(user=self.user)
        forbidden = CremeEntity.objects.create(user=self.other_user)

        rtype, useless = RelationType.create(('test-subject_love', 'is loving'), ('test-object_love', 'is loved by'))
        relation01 = Relation.objects.create(user=self.user, type=rtype, subject_entity=allowed,   object_entity=forbidden)
        relation02 = Relation.objects.create(user=self.user, type=rtype, subject_entity=forbidden, object_entity=allowed)
        self.assertEqual(4, Relation.objects.count())

        response = self.client.post('/creme_core/relation/delete/similar',
                                    data={
                                            'subject_id': allowed.id,
                                            'type':       rtype.id,
                                            'object_id':  forbidden.id,
                                         }
                                   )
        self.assertEqual(403, response.status_code)
        self.assertEqual(4,   Relation.objects.count())

        response = self.client.post('/creme_core/relation/delete/similar',
                                    data={
                                            'subject_id': forbidden.id,
                                            'type':       rtype.id,
                                            'object_id':  allowed.id,
                                         }
                                   )
        self.assertEqual(403, response.status_code)
        self.assertEqual(4,   Relation.objects.count())

    def test_delete_similar03(self): #is internal
        self.login()

        subject_entity = CremeEntity.objects.create(user=self.user)
        object_entity  = CremeEntity.objects.create(user=self.user)
        rtype, useless = RelationType.create(('test-subject_love', 'is loving'), ('test-object_love', 'is loved by'), is_internal=True)
        relation = Relation.objects.create(user=self.user, type=rtype, subject_entity=subject_entity, object_entity=object_entity)

        response = self.client.post('/creme_core/relation/delete/similar',
                                    data={
                                            'subject_id': subject_entity.id,
                                            'type':       rtype.id,
                                            'object_id':  object_entity.id,
                                         }
                                   )
        self.assertEqual(404, response.status_code)
        self.assertEqual(1,   Relation.objects.filter(pk=relation.pk).count())

    #TODO: test other relation views...
