# -*- coding: utf-8 -*-

try:
    from django.http import Http404
    from django.core.serializers.json import simplejson
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import (RelationType, Relation, SemiFixedRelationType, CremeEntity,
                                   CremePropertyType, CremeProperty, SetCredentials)
    from creme_core.tests.views.base import ViewsTestCase

    from persons.models import Contact, Organisation
    from persons.constants import REL_OBJ_CUSTOMER_SUPPLIER
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('RelationViewsTestCase', )


class RelationViewsTestCase(ViewsTestCase):
    format_str    = '[{"rtype": "%s", "ctype": "%s", "entity": "%s"}]'
    format_str_2x = '[{"rtype": "%s", "ctype": "%s", "entity": "%s"},' \
                    ' {"rtype": "%s", "ctype": "%s", "entity": "%s"}]'
    format_str_3x = '[{"rtype": "%s", "ctype": "%s", "entity": "%s"},' \
                    ' {"rtype": "%s", "ctype": "%s", "entity": "%s"},' \
                    ' {"rtype": "%s", "ctype": "%s", "entity": "%s"}]'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons')

    def test_get_ctypes_of_relation(self):
        self.login()

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

        self.rtype01 = RelationType.create(('test-subject_foobar1', 'is loving'),
                                           ('test-object_foobar1',  'is loved by')
                                          )[0]
        self.rtype02 = RelationType.create(('test-subject_foobar2', 'is hating'),
                                           ('test-object_foobar2',  'is hated by')
                                          )[0]

    def assertEntiTyHasRelation(self, subject_entity, rtype, object_entity):
        self.assertTrue(subject_entity.relations
                                      .filter(type=rtype, object_entity=object_entity.id)
                                      .exists()
                       )
    def _build_add_url(self, subject):
        return '/creme_core/relation/add/%s' % subject.id

    def test_add_relations01(self):
        self._aux_test_add_relations()

        subject = self.subject01
        self.assertFalse(subject.relations.all())

        url = self._build_add_url(subject)
        self.assertEqual(200, self.client.get(url).status_code)

        ct_id = self.ct_id
        response = self.client.post(url, data={'relations': self.format_str_2x % (
                                                                self.rtype01.id, ct_id, self.object01.id,
                                                                self.rtype02.id, ct_id, self.object02.id,
                                                              ),
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())
        self.assertEntiTyHasRelation(subject, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(subject, self.rtype02, self.object02)

    def test_add_relations02(self): #creds problems
        self.login(is_superuser=False)
        subject = CremeEntity.objects.create(user=self.other_user)
        self.assertEqual(403, self.client.get(self._build_add_url(subject)).status_code)

    def test_add_relations03(self): #creds problems (no link credentials)
        self._aux_test_add_relations(is_superuser=False)
        self._set_all_creds_except_one(excluded=SetCredentials.CRED_LINK)

        unlinkable = CremeEntity.objects.create(user=self.other_user)
        self.assertTrue(unlinkable.can_view(self.user))
        self.assertFalse(unlinkable.can_link(self.user))

        ct_id = self.ct_id
        response = self.client.post(self._build_add_url(self.subject01),
                                    data={'relations': self.format_str_2x % (
                                                                self.rtype01.id, ct_id, self.object01.id,
                                                                self.rtype02.id, ct_id, unlinkable.id,
                                                            ),
                                         }
                                   )
        self.assertFormError(response, 'form', 'relations', [_(u'Some entities are not linkable: %s') % unlinkable])
        self.assertEqual(0, self.subject01.relations.count())

    def test_add_relations04(self): #duplicates -> error
        self._aux_test_add_relations()

        ct_id = self.ct_id
        response = self.client.post(self._build_add_url(self.subject01),
                                    data={'relations': self.format_str_3x % (
                                                            self.rtype01.id, ct_id, self.object01.id,
                                                            self.rtype02.id, ct_id, self.object02.id,
                                                            self.rtype01.id, ct_id, self.object01.id,
                                                        ),
                                         }
                                   )
        self.assertFormError(response, 'form', 'relations',
                             [_(u'There are duplicates: %s') % (u'(%s, %s)' % (self.rtype01, self.object01))]
                            )

    def test_add_relations05(self): #do not recreate existing relations
        self._aux_test_add_relations()

        Relation.objects.create(user=self.user,
                                subject_entity=self.subject01,
                                type=self.rtype02,
                                object_entity=self.object02
                               )
        ct_id = self.ct_id
        response = self.client.post(self._build_add_url(self.subject01),
                                    data={'relations': self.format_str_2x % (
                                                            self.rtype01.id, ct_id, self.object01.id,
                                                            self.rtype02.id, ct_id, self.object02.id,
                                                        ),
                                          }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(2, self.subject01.relations.count()) #and not 3

    def test_add_relations06(self): #can not link an entity to itself
        self._aux_test_add_relations()

        subject = self.subject01
        response = self.client.post(self._build_add_url(subject),
                                    data={'relations': self.format_str % (
                                                            self.rtype01.id, self.ct_id, subject.id
                                                        ),
                                         }
                                   )
        self.assertFormError(response, 'form', 'relations',
                             [_(u'An entity can not be linked to itself : %s') % subject]
                            )

    def test_add_relations_with_semi_fixed01(self): #only semi fixed
        self._aux_test_add_relations()

        subject = self.subject01

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(predicate='Related to "object01"',
                            relation_type=self.rtype01, object_entity=self.object01,
                           )
        sfrt2 = create_sfrt(predicate='Related to "object02"',
                            relation_type=self.rtype02, object_entity=self.object02,
                           )

        url = self._build_add_url(subject)

        with self.assertNoException():
            semifixed_rtypes = self.client.get(url).context['form'].fields['semifixed_rtypes']

        self.assertEqual([(sfrt1.id, sfrt1.predicate), (sfrt2.id, sfrt2.predicate)],
                         list(semifixed_rtypes.choices)
                        )

        response = self.client.post(url, data={'semifixed_rtypes': [sfrt1.id, sfrt2.id]})
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())
        self.assertEntiTyHasRelation(subject, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(subject, self.rtype02, self.object02)

    def test_add_relations_with_semi_fixed02(self): #semi-fixed & not semi-fixed
        self._aux_test_add_relations()

        subject = self.subject01

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(predicate='Related to "object01"',
                            relation_type=self.rtype01, object_entity=self.object01,
                           )
        sfrt2 = create_sfrt(predicate='Related to "object02"',
                            relation_type=self.rtype02, object_entity=self.object02,
                           )
        sfrt3 = create_sfrt(predicate='Related to "subject01"',
                            relation_type=self.rtype02, object_entity=self.subject01,
                           ) #should not be proposed

        url = self._build_add_url(subject)
        context = self.client.get(url).context

        with self.assertNoException():
            field_sfrt = context['form'].fields['semifixed_rtypes']

        self.assertEqual(set([sfrt1.id, sfrt2.id]),
                         set(pk for pk, sfrt in field_sfrt.choices)
                        )

        response = self.client.post(url, data={'relations': self.format_str % (
                                                                self.rtype01.id,
                                                                self.ct_id,
                                                                self.object01.id,
                                                             ),
                                               'semifixed_rtypes': [sfrt2.id],
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())
        self.assertEntiTyHasRelation(subject, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(subject, self.rtype02, self.object02)

    def test_add_relations_with_semi_fixed03(self): #one raltions at leats (semi-fixed or not semi-fixed)
        self._aux_test_add_relations()

        response = self.client.post(self._build_add_url(self.subject01))
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', None, [_(u'You must give one relationship at least.')])

    def test_add_relations_with_semi_fixed04(self): #collision fixed / not fixed
        self._aux_test_add_relations()

        subject = self.subject01

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(predicate='Related to "object01"',
                            relation_type=self.rtype01, object_entity=self.object01,
                           )
        sfrt2 = create_sfrt(predicate='Related to "object02"',
                            relation_type=self.rtype02, object_entity=self.object02,
                           )

        response = self.client.post(self._build_add_url(subject),
                                    data={'relations': self.format_str % (
                                                            self.rtype01.id, self.ct_id, self.object01.id,
                                                        ),
                                          'semifixed_rtypes': [sfrt1.id, sfrt2.id],
                                         }
                                   )
        self.assertFormError(response, 'form', None,
                             [_(u'There are duplicates: %s') % (u'(%s, %s)' % (self.rtype01, self.object01))]
                            )

    def test_add_relations_with_semi_fixed05(self): #filter not linkable entities
        self._aux_test_add_relations(is_superuser=False)
        self._set_all_creds_except_one(excluded=SetCredentials.CRED_LINK)

        unlinkable = CremeEntity.objects.create(user=self.other_user)

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(predicate='Related to "unlinkable"',
                            relation_type=self.rtype01, object_entity=unlinkable, # <===
                           )
        sfrt2 = create_sfrt(predicate='Related to "object02"',
                            relation_type=self.rtype02, object_entity=self.object02,
                           )

        response = self.client.get('/creme_core/relation/add/%s' % self.subject01.id)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            sfrt_field = response.context['form'].fields['semifixed_rtypes']

        self.assertEqual([(sfrt2.id, sfrt2.predicate)], list(sfrt_field.choices))

    def _build_narrowed_add_url(self, subject, rtype):
        return '/creme_core/relation/add/%s/%s' % (subject.id, rtype.id)

    def test_add_relations_narrowedtype01(self):
        self._aux_test_add_relations()

        rtype = self.rtype01
        subject = self.subject01
        url = self._build_narrowed_add_url(subject, rtype)
        self.assertEqual(200, self.client.get(url).status_code)

        ct_id = self.ct_id
        response = self.client.post(url, data={'relations': self.format_str_2x % (
                                                                rtype.id, ct_id, self.object01.id,
                                                                rtype.id, ct_id, self.object02.id,
                                                             ),
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())
        self.assertEntiTyHasRelation(subject, rtype, self.object01)
        self.assertEntiTyHasRelation(subject, rtype, self.object02)

    def test_add_relations_narrowedtype02(self): #validation error
        self._aux_test_add_relations()

        ct_id = self.ct_id
        response = self.client.post(self._build_narrowed_add_url(self.subject01, self.rtype01),
                                    data={'relations': self.format_str_2x % (
                                                                self.rtype01.id, ct_id, self.object01.id,
                                                                self.rtype02.id, ct_id, self.object02.id, #rtype not allowed
                                                            ),
                                         }
                                   )
        self.assertFormError(response, 'form', 'relations', [_(u'This type of relationship causes a constraint error.')])

    def test_add_relations_narrowedtype03(self):
        self._aux_test_add_relations()

        allowed_rtype = self.rtype01
        subject = self.subject01

        create_sfrt = SemiFixedRelationType.objects.create
        sfrt1 = create_sfrt(predicate='Related to "object01"',
                            relation_type=allowed_rtype, object_entity=self.object01,
                           )
        sfrt2 = create_sfrt(predicate='Related to "object02"',
                            relation_type=self.rtype02, object_entity=self.object02,
                           )

        url = self._build_narrowed_add_url(subject, allowed_rtype)

        with self.assertNoException():
            sfrt_field = self.client.get(url).context['form'].fields['semifixed_rtypes']

        self.assertEqual([(sfrt1.id, sfrt1.predicate)], list(sfrt_field.choices))

        response = self.client.post(url, data={'relations': self.format_str % (
                                                                allowed_rtype.id, self.ct_id, self.object02.id,
                                                              ),
                                                'semifixed_rtypes': [sfrt1.id],
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(2, subject.relations.count())
        self.assertEntiTyHasRelation(subject, allowed_rtype, self.object01)
        self.assertEntiTyHasRelation(subject, allowed_rtype, self.object02)

    def _build_bulk_add_url(self, ct_id, *subjects):
        return '/creme_core/relation/add_to_entities/%(ct_id)s/?%(sub_ids)s&persist=ids' % {
                        'ct_id':   ct_id,
                        'sub_ids': ''.join('ids=%s&' % subject.id for subject in subjects),
                    }

    def test_add_relations_bulk01(self):
        self._aux_test_add_relations()

        #this relation should not be recreated by the view
        Relation.objects.create(user=self.user,
                                subject_entity=self.subject02,
                                type=self.rtype02,
                                object_entity=self.object02
                               )
        ct_id = self.ct_id
        url = self._build_bulk_add_url(ct_id, self.subject01, self.subject02)
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'entities_lbl': 'wtf',
                                               'relations':    self.format_str_2x % (
                                                                    self.rtype01.id, ct_id, self.object01.id,
                                                                    self.rtype02.id, ct_id, self.object02.id,
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
        self.assertFalse(unviewable.can_view(self.user))

        url = self._build_bulk_add_url(self.ct_id, self.subject01, unviewable)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            label = response.context['form'].fields['bad_entities_lbl']

        self.assertTrue(label.initial)

        ct_id = self.ct_id
        response = self.client.post(url, data={'entities_lbl':     'do not care',
                                               'bad_entities_lbl': 'do not care',
                                               'relations':        self.format_str_2x % (
                                                                        self.rtype01.id, ct_id, self.object01.id,
                                                                        self.rtype02.id, ct_id, self.object02.id,
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
        self.assertTrue(unlinkable.can_view(self.user))
        self.assertFalse(unlinkable.can_link(self.user))

        response = self.client.get(self._build_bulk_add_url(self.ct_id, self.subject01, unlinkable))
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            label = response.context['form'].fields['bad_entities_lbl']

        self.assertEqual(unicode(unlinkable), label.initial)

    def test_add_relations_bulk04(self):
        self._aux_test_add_relations(is_superuser=False)

        url =  self._build_bulk_add_url(self.ct_id, self.subject01)
        self.assertEqual(200, self.client.get(url).status_code)

        self._set_all_creds_except_one(excluded=SetCredentials.CRED_LINK)
        unlinkable = CremeEntity.objects.create(user=self.other_user)

        response = self.client.post(url, data={'entities_lbl': 'wtf',
                                               'relations':    self.format_str % (
                                                                    self.rtype01.id, self.ct_id, unlinkable.id
                                                                ),
                                              })
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'relations', [_(u'Some entities are not linkable: %s') % unlinkable])

    def test_add_relations_bulk05(self):  #can not link an entity to itself
        self._aux_test_add_relations()

        ct_id = self.ct_id
        subject01 = self.subject01
        subject02 = self.subject02
        response = self.client.post(self._build_bulk_add_url(ct_id, subject01, subject02),
                                    data={'entities_lbl': 'wtf',
                                          'relations':    self.format_str_2x % (
                                                                self.rtype01.id, ct_id, subject01.id,
                                                                self.rtype02.id, ct_id, subject02.id,
                                                            ),
                                         }
                                   )
        self.assertFormError(response, 'form', 'relations',
                             [_(u'An entity can not be linked to itself : %s') % (
                                    '%s, %s' % (subject01, subject02)
                                  )
                             ]
                            )

    def test_add_relations_bulk_with_semifixed01(self):
        self._aux_test_add_relations()

        #this relation should not be recreated by the view
        Relation.objects.create(user=self.user,
                                subject_entity=self.subject02,
                                type=self.rtype02,
                                object_entity=self.object02
                               )

        sfrt = SemiFixedRelationType.objects.create(predicate='Related to "object01"',
                                                    relation_type=self.rtype01,
                                                    object_entity=self.object01,
                                                   )

        response = self.client.post(self._build_bulk_add_url(self.ct_id, self.subject01, self.subject02),
                                    data={'entities_lbl':     'wtf',
                                          'relations':        self.format_str % (
                                                                  self.rtype02.id, self.ct_id, self.object02.id,
                                                                ),
                                          'semifixed_rtypes': [sfrt.id],
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertEqual(2, self.subject01.relations.count())
        self.assertEntiTyHasRelation(self.subject01, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject01, self.rtype02, self.object02)

        self.assertEqual(2, self.subject02.relations.count()) #and not 3
        self.assertEntiTyHasRelation(self.subject02, self.rtype01, self.object01)
        self.assertEntiTyHasRelation(self.subject02, self.rtype02, self.object02)

    def test_add_relations_bulk_fixedrtypes01(self):
        self._aux_test_add_relations()

        #this relation should not be recreated by the view
        Relation.objects.create(user=self.user,
                                subject_entity=self.subject02,
                                type=self.rtype02,
                                object_entity=self.object02
                               )

        url = '/creme_core/relation/add_to_entities/%s/%s,%s,/?ids=%s&ids=%s&persist=ids' % (
                    self.ct_id, self.rtype01.id, self.rtype02.id, self.subject01.id, self.subject02.id
                )
        self.assertEqual(200, self.client.get(url).status_code)

        ct_id = self.ct_id
        response = self.client.post(url, data={'entities_lbl': 'wtf',
                                               'relations':    self.format_str_2x % (
                                                                    self.rtype01.id, ct_id, self.object01.id,
                                                                    self.rtype02.id, ct_id, self.object02.id,
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

        url = '/creme_core/relation/add_to_entities/%s/%s/?ids=%s&ids=%s&persist=ids' % (
                    self.ct_id, self.rtype01.id, self.subject01.id, self.subject02.id
                )
        self.assertEqual(200, self.client.get(url).status_code)

        ct_id = self.ct_id
        response = self.client.post(url, data={'entities_lbl': 'wtf',
                                               'relations': self.format_str_2x % (
                                                                self.rtype02.id, ct_id, self.object01.id,
                                                                self.rtype02.id, ct_id, self.object02.id,
                                                               ),
                                              })
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'relations', [_(u'This type of relationship causes a constraint error.')])

    def _aux_relation_objects_to_link_selection(self):
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

    def _build_selection_url(self, rtype, subject, ct):
        return '/creme_core/relation/objects2link/rtype/%s/entity/%s/%s' % (
                    rtype.id,
                    subject.id,
                    ct.id
                )

    def test_objects_to_link_selection01(self):
        self._aux_relation_objects_to_link_selection()

        response = self.client.get(self._build_selection_url(self.rtype, self.subject, self.ct_contact))
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            entities = response.context['entities']

        contacts = entities.object_list
        self.assertEqual(3, len(contacts))
        self.assertTrue(all(isinstance(c, Contact) for c in contacts))
        self.assertEqual(set([self.contact01, self.contact02, self.contact03]), set(contacts))

    def test_objects_to_link_selection02(self):
        self._aux_relation_objects_to_link_selection()

        #contact03 will not be proposed by the listview
        Relation.objects.create(user=self.user, type=self.rtype, subject_entity=self.subject, object_entity=self.contact03)

        response = self.client.get(self._build_selection_url(self.rtype, self.subject, self.ct_contact))
        self.assertEqual(200, response.status_code)

        contacts = response.context['entities'].object_list
        self.assertEqual(2, len(contacts))
        self.assertEqual(set([self.contact01, self.contact02]), set(contacts))

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

        response = self.client.get(self._build_selection_url(rtype, self.subject, self.ct_contact))
        self.assertEqual(200, response.status_code)

        contacts = response.context['entities'].object_list
        self.assertEqual(3, len(contacts))
        self.assertEqual(set([self.contact01, self.contact03, contact04]), set(contacts))

    def test_objects_to_link_selection04(self):
        self.login()

        subject = CremeEntity.objects.create(user=self.user)
        ct = ContentType.objects.get_for_model(Contact)
        rtype = RelationType.create(('test-subject_foobar', 'is loving',   [Contact]),
                                    ('test-object_foobar',  'is loved by', [Contact]),
                                    is_internal=True
                                   )[0]

        self.assertEqual(404, self.client
                                  .get(self._build_selection_url(rtype, subject, ct))
                                  .status_code
                        )

    def _aux_add_relations_with_same_type(self):
        self.subject  = CremeEntity.objects.create(user=self.user)
        self.object01 = CremeEntity.objects.create(user=self.user)
        self.object02 = CremeEntity.objects.create(user=self.user)
        self.rtype = RelationType.create(('test-subject_foobar', 'is loving',),
                                         ('test-object_foobar',  'is loved by',)
                                        )[0]

    def test_add_relations_with_same_type01(self): #no errors
        self.login()
        self._aux_add_relations_with_same_type()

        object_ids = [self.object01.id, self.object02.id]
        response = self.client.post('/creme_core/relation/add_from_predicate/save',
                                    data={'subject_id':   self.subject.id,
                                          'predicate_id': self.rtype.id,
                                          'entities':     object_ids,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2,   Relation.objects.filter(type=self.rtype).count())

        relations = self.subject.relations.filter(type=self.rtype)
        self.assertEqual(2, len(relations))
        self.assertEqual(set(object_ids), set(r.object_entity_id for r in relations))

    def test_add_relations_with_same_type02(self): #an entity does not exist
        self.login()
        self._aux_add_relations_with_same_type()

        response = self.client.post('/creme_core/relation/add_from_predicate/save',
                                    data={'subject_id':   self.subject.id,
                                          'predicate_id': self.rtype.id,
                                          'entities':     [self.object01.id,
                                                           self.object02.id,
                                                           self.object02.id + 1,
                                                          ],
                                         }
                                   )
        self.assertEqual(404, response.status_code)
        self.assertEqual(2,   Relation.objects.filter(type=self.rtype).count())

    def test_add_relations_with_same_type03(self): #errors
        self.login()
        self._aux_add_relations_with_same_type()

        def post_status(**data):
            return self.client .post('/creme_core/relation/add_from_predicate/save', data=data).status_code

        self.assertEqual(404, post_status(subject_id=self.subject.id,
                                          predicate_id='IDONOTEXIST',
                                          entities=[self.object01.id],
                                         )
                        )
        self.assertEqual(404, post_status(subject_id=1024,
                                          predicate_id=self.rtype.id,
                                          entities=[self.object01.id]
                                         )
                        )
        self.assertEqual(404, post_status(predicate_id=self.rtype.id,
                                          entities=[self.object01.id],
                                         )
                        )
        self.assertEqual(404, post_status(subject_id=self.subject.id,
                                          entities=[self.object01.id],
                                         )
                        )
        self.assertEqual(404, post_status(subject_id=self.subject.id,
                                          predicate_id=self.rtype.id,
                                         )
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

        self.assertFalse(forbidden.can_link(self.user))
        self.assertTrue(allowed01.can_link(self.user))

        self.assertEqual(403, post('/creme_core/relation/add_from_predicate/save',
                                    data={'subject_id':   forbidden.id,
                                          'predicate_id': rtype.id,
                                          'entities':     [allowed01.id, allowed02.id],
                                         }
                                  ).status_code
                        )
        self.assertFalse(Relation.objects.filter(type=rtype.id))

        self.assertEqual(403, post('/creme_core/relation/add_from_predicate/save',
                                    data={'subject_id':   allowed01.id,
                                          'predicate_id': rtype.id,
                                          'entities':     [forbidden.id, allowed02.id, 1024],
                                         }
                                  ).status_code
                        )
        relations = Relation.objects.filter(type=rtype)
        self.assertEqual(1, len(relations))

        relation = relations[0]
        self.assertEqual(allowed01, relation.subject_entity)
        self.assertEqual(allowed02, relation.object_entity)

    def test_add_relations_with_same_type05(self): #ct constraint errors
        self.login()

        orga01    = Organisation.objects.create(user=self.user, name='orga01')
        orga02    = Organisation.objects.create(user=self.user, name='orga02')
        contact01 = Contact.objects.create(user=self.user, first_name='John', last_name='Doe')
        contact02 = Contact.objects.create(user=self.user, first_name='Joe',  last_name='Gohn')

        rtype = RelationType.create(('test-subject_foobar', 'manages',       [Contact]),
                                    ('test-object_foobar',  'is managed by', [Organisation])
                                   )[0]

        post = self.client.post

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={'subject_id':   orga01.id,
                                          'predicate_id': rtype.id,
                                          'entities':     [orga02.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(0, Relation.objects.filter(type=rtype.id).count())

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={'subject_id':   contact01.id,
                                          'predicate_id': rtype.id,
                                          'entities':     [orga01.id, contact02.id],
                                         }
                                  ).status_code
                        )
        relations = Relation.objects.filter(type=rtype)
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
                                    data={'subject_id':   bad_subject.id,
                                          'predicate_id': rtype.id,
                                          'entities':     [good_object.id],
                                         }
                                  ).status_code
                        )
        self.assertEqual(0, Relation.objects.filter(type=rtype).count())

        self.assertEqual(404, post('/creme_core/relation/add_from_predicate/save',
                                    data={'subject_id':   good_subject.id,
                                          'predicate_id': rtype.id,
                                          'entities':     [good_object.id, bad_object.id],
                                         }
                                  ).status_code
                        )
        relations = Relation.objects.filter(type=rtype)
        self.assertEqual(1,              len(relations))
        self.assertEqual(good_object.id, relations[0].object_entity_id)

    def test_add_relations_with_same_type07(self): #is_internal
        self.login()

        subject  = CremeEntity.objects.create(user=self.user)
        object01 = CremeEntity.objects.create(user=self.user)
        object02 = CremeEntity.objects.create(user=self.user)
        rtype = RelationType.create(('test-subject_foobar', 'is loving',),
                                    ('test-object_foobar',  'is loved by',),
                                    is_internal=True
                                   )[0]
        response = self.client.post('/creme_core/relation/add_from_predicate/save',
                                    data={'subject_id':   subject.id,
                                          'predicate_id': rtype.id,
                                          'entities':     [object01.id, object02.id],
                                         }
                                   )
        self.assertEqual(404, response.status_code)
        self.assertEqual(0,   Relation.objects.filter(type=rtype).count())

    def test_delete01(self):
        self.login()

        subject_entity = CremeEntity.objects.create(user=self.user)
        object_entity  = CremeEntity.objects.create(user=self.user)

        rtype = RelationType.create(('test-subject_foobar', 'is loving'), ('test-object_foobar',  'is loved by'))[0]
        relation = Relation.objects.create(user=self.user, type=rtype, subject_entity=subject_entity, object_entity=object_entity)
        sym_relation = relation.symmetric_relation
        self.assertIsNone(rtype.is_not_internal_or_die())

        response = self.client.post('/creme_core/relation/delete', data={'id': relation.id})
        self.assertEqual(302, response.status_code)
        self.assertEqual(0,   Relation.objects.filter(pk__in=[relation.pk, sym_relation.pk]).count())

    def test_delete02(self):
        self.login(is_superuser=False)

        self._set_all_creds_except_one(excluded=SetCredentials.CRED_UNLINK)

        allowed   = CremeEntity.objects.create(user=self.user)
        forbidden = CremeEntity.objects.create(user=self.other_user)
        rtype = RelationType.create(('test-subject_foobar', 'is loving'), ('test-object_foobar', 'is loved by'))[0]

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

        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'is loving'),
                                               ('test-object_foobar',  'is loved by'),
                                               is_internal=True
                                              )
        self.assertTrue(rtype.is_internal)
        self.assertTrue(sym_rtype.is_internal)
        self.assertRaises(Http404, rtype.is_not_internal_or_die)

        relation = Relation.objects.create(user=self.user, type=rtype, subject_entity=subject_entity, object_entity=object_entity)
        self.assertEqual(404, self.client.post('/creme_core/relation/delete', data={'id': relation.id}).status_code)
        self.assertEqual(1,   Relation.objects.filter(pk=relation.pk).count())

    def test_delete_similar01(self):
        self.login()
        user = self.user

        subject_entity01 = CremeEntity.objects.create(user=user)
        object_entity01  = CremeEntity.objects.create(user=user)

        subject_entity02 = CremeEntity.objects.create(user=user)
        object_entity02  = CremeEntity.objects.create(user=user)

        rtype01 = RelationType.create(('test-subject_love', 'is loving'), ('test-object_love', 'is loved by'))[0]
        rtype02 = RelationType.create(('test-subject_son',  'is son of'), ('test-object_son',  'is parent of'))[0]

        #will be deleted (normally)
        create_rel = Relation.objects.create
        relation01 = create_rel(user=user, type=rtype01, subject_entity=subject_entity01, object_entity=object_entity01)
        relation02 = create_rel(user=user, type=rtype01, subject_entity=subject_entity01, object_entity=object_entity01)

        #won't be deleted (normally)
        relation03 = create_rel(user=user, type=rtype01, subject_entity=subject_entity01, object_entity=object_entity02) #different object
        relation04 = create_rel(user=user, type=rtype01, subject_entity=subject_entity02, object_entity=object_entity01) #different subject
        relation05 = create_rel(user=user, type=rtype02, subject_entity=subject_entity01, object_entity=object_entity01) #different type

        self.assertEqual(10, Relation.objects.count())

        response = self.client.post('/creme_core/relation/delete/similar',
                                    data={'subject_id': subject_entity01.id,
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

        rtype = RelationType.create(('test-subject_love', 'is loving'), ('test-object_love', 'is loved by'))[0]
        relation01 = Relation.objects.create(user=self.user, type=rtype, subject_entity=allowed,   object_entity=forbidden)
        relation02 = Relation.objects.create(user=self.user, type=rtype, subject_entity=forbidden, object_entity=allowed)
        self.assertEqual(4, Relation.objects.count())

        response = self.client.post('/creme_core/relation/delete/similar',
                                    data={'subject_id': allowed.id,
                                          'type':       rtype.id,
                                          'object_id':  forbidden.id,
                                         }
                                   )
        self.assertEqual(403, response.status_code)
        self.assertEqual(4,   Relation.objects.count())

        response = self.client.post('/creme_core/relation/delete/similar',
                                    data={'subject_id': forbidden.id,
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

        rtype = RelationType.create(('test-subject_love', 'is loving'),
                                    ('test-object_love', 'is loved by'),
                                    is_internal=True
                                   )[0]
        relation = Relation.objects.create(user=self.user, type=rtype,
                                           subject_entity=subject_entity, object_entity=object_entity
                                          )

        response = self.client.post('/creme_core/relation/delete/similar',
                                    data={'subject_id': subject_entity.id,
                                          'type':       rtype.id,
                                          'object_id':  object_entity.id,
                                         }
                                   )
        self.assertEqual(404, response.status_code)
        self.assertEqual(1,   Relation.objects.filter(pk=relation.pk).count())

    def _aux_test_delete_all(self):
        self.assertEqual(0, Relation.objects.count())
        create_entity = CremeEntity.objects.create
        subject01 = self.subject01 = create_entity(user=self.user)
        object01  = create_entity(user=self.user)
        object02  = create_entity(user=self.other_user)

        rtype01 = RelationType.create(('test-subject_foobar1', 'is loving'),
                                      ('test-object_foobar1',  'is loved by')
                                     )[0]
        rtype02 = RelationType.create(('test-subject_foobar2', 'is loving'),
                                      ('test-object_foobar2',  'is loved by')
                                     )[0]
        rtype03 = RelationType.create(('test-subject_foobar3', 'is loving'),
                                      ('test-object_foobar3',  'is loved by'),
                                      is_internal=True
                                     )[0]

        create_rel = Relation.objects.create
        create_rel(type=rtype01, subject_entity=subject01, object_entity=object01, user=self.user)
        create_rel(type=rtype02, subject_entity=subject01, object_entity=object01, user=self.user)
        create_rel(type=rtype03, subject_entity=subject01, object_entity=object01, user=self.user)#internal

        create_rel(type=rtype01, subject_entity=subject01, object_entity=object02, user=self.other_user)
        create_rel(type=rtype02, subject_entity=subject01, object_entity=object02, user=self.other_user)
        create_rel(type=rtype03, subject_entity=subject01, object_entity=object02, user=self.other_user)#internal

    def test_delete_all01(self):
        self.login()
        self._aux_test_delete_all()
        self.assertEqual(12, Relation.objects.count())

        url = '/creme_core/relation/delete/all'
        self.assertEqual(404, self.client.post(url).status_code)

        response = self.client.post(url, data={'subject_id': self.subject01.id})
        self.assertEqual(200, response.status_code)
        self.assertEqual(4, Relation.objects.count())
        self.assertFalse(0, Relation.objects.filter(type__is_internal=False))

    def test_delete_all02(self):
        self.login(is_superuser=False)
        self._set_all_creds_except_one(excluded=SetCredentials.CRED_UNLINK)
        self._aux_test_delete_all()

        response = self.client.post('/creme_core/relation/delete/all',
                                    data={'subject_id': self.subject01.id}
                                   )
        self.assertEqual(403,   response.status_code)
        self.assertEqual(4 + 4, Relation.objects.count())#4 internals and 4 the user can't unlink because there are not his

    #TODO: test other relation views...
