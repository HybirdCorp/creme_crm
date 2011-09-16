# -*- coding: utf-8 -*-

try:
    from datetime import date

    from django.core.serializers.json import simplejson
    from django.utils.translation import ugettext as _
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import EntityFilter, EntityFilterCondition, CustomField, RelationType, CremePropertyType
    from creme_core.tests.views.base import ViewsTestCase

    from persons.models import Contact, Organisation
except Exception, e:
    print 'Error:', e


__all__ = ('EntityFilterViewsTestCase', )


class EntityFilterViewsTestCase(ViewsTestCase):
    def setUp(self):
        self.populate('creme_config')

    def test_create01(self): #check app credentials
        self.login(is_superuser=False)

        ct = ContentType.objects.get_for_model(Contact)
        self.failIf(EntityFilter.objects.filter(entity_type=ct).count())

        uri = '/creme_core/entity_filter/add/%s' % ct.id
        self.assertEqual(404, self.client.get(uri).status_code)

        self.role.allowed_apps = ['persons']
        self.role.save()
        self.assertEqual(200, self.client.get(uri).status_code)

        name = 'Filter 01'
        operator = EntityFilterCondition.IEQUALS
        field_name = 'last_name'
        value = 'Ikari'
        response = self.client.post(uri, follow=True,
                                    data={
                                            'name':       name,
                                            'fields_conditions': '[{"operator": "%(operator)s", "name": "%(name)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]' % {
                                                                        'operator': operator,
                                                                        'name':     field_name,
                                                                        'value':    value,
                                                                    },
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        efilters = EntityFilter.objects.filter(entity_type=ct)
        self.assertEqual(1, len(efilters))

        efilter = efilters[0]
        self.assertEqual(name, efilter.name)
        self.assert_(efilter.is_custom)
        self.assert_(efilter.user is None)
        self.failIf(efilter.use_or)

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(field_name,                                condition.name)
        self.assertEqual({'operator': operator, 'values': [value]}, condition.decoded_value)

    def test_create02(self):
        self.login()
        ct = ContentType.objects.get_for_model(Organisation)

        #Can not be a simple subfilter (bad content type)
        relsubfilfer = EntityFilter.create('test-filter01', 'Filter 01', Contact, is_custom=True)

        subfilter = EntityFilter.create('test-filter02', 'Filter 02', Organisation, is_custom=True)
        subfilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                      operator=EntityFilterCondition.GT,
                                                                      name='capital', values=[10000]
                                                                     )
                                 ])

        rtype, srtype = RelationType.create(('test-subject_love', u'Is loving'),
                                            ('test-object_love',  u'Is loved by')
                                           )
        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text=u'Kawaii')

        create_cf = CustomField.objects.create
        custom_field = create_cf(name='Profits',        field_type=CustomField.INT,  content_type=ct)
        datecfield   = create_cf(name='Last gathering', field_type=CustomField.DATE, content_type=ct)

        url = '/creme_core/entity_filter/add/%s' % ct.id
        form = self.client.get(url).context['form']
        self.assertEqual([subfilter.id], [f.id for f in form.fields['subfilters_conditions'].queryset])

        name = 'Filter 03'
        field_operator = EntityFilterCondition.CONTAINS
        field_name = 'name'
        field_value = 'NERV'
        date_field_name = 'creation_date'
        daterange_type = 'current_year'
        cfield_operator = EntityFilterCondition.GT
        cfield_value = 10000
        datecfield_rtype = 'previous_quarter'
        response = self.client.post(url,
                                    data={
                                            'name':   name,
                                            'user':   self.user.id,
                                            'use_or': True,
                                            'fields_conditions':             '[{"operator": "%(operator)s", "name": "%(name)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]' % {
                                                                                     'operator': field_operator,
                                                                                     'name':     field_name,
                                                                                     'value':    field_value,
                                                                                },
                                            'datefields_conditions':        '[{"range": {"type": "%(type)s", "start": "", "end": ""}, "field": "%(name)s"}]' % {
                                                                                    'type': daterange_type,
                                                                                    'name': date_field_name,
                                                                                },
                                            'customfields_conditions':      '[{"field": "%(cfield)s", "operator": "%(operator)s", "value": "%(value)s"}]' % {
                                                                                    'cfield':   custom_field.id,
                                                                                    'operator': cfield_operator,
                                                                                    'value':    cfield_value,
                                                                                },
                                            'datecustomfields_conditions':  '[{"field": "%(cfield)s", "range": {"type": "%(type)s"}}]' % {
                                                                                    'cfield': datecfield.id,
                                                                                    'type':   datecfield_rtype,
                                                                                },
                                            'relations_conditions':         '[{"has": true, "rtype": "%s", "ctype": "0", "entity": null}]' % (rtype.id),
                                            'relsubfilfers_conditions':     '[{"rtype": "%(rtype)s", "has": false, "ctype": "%(ct)s", "filter": "%(filter)s"}]' % {
                                                                                    'rtype':  srtype.id,
                                                                                    'ct':     ContentType.objects.get_for_model(Contact).id,
                                                                                    'filter': relsubfilfer.id,
                                                                                },
                                            'properties_conditions':        '[{"has": true, "ptype":"%s"}]' % (ptype.id),
                                            'subfilters_conditions':        [subfilter.id],
                                         }
                                   )
        self.assertNoFormError(response)

        try:
            efilter = EntityFilter.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(self.user.id, efilter.user.id)
        self.assert_(efilter.use_or)

        conditions = efilter.conditions.order_by('id')
        self.assertEqual(8, len(conditions))
        iter_conds = iter(conditions)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_FIELD,                       condition.type)
        self.assertEqual(field_name,                                            condition.name)
        self.assertEqual({'operator': field_operator, 'values': [field_value]}, condition.decoded_value)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual(date_field_name,                     condition.name)
        self.assertEqual({'name': daterange_type},            condition.decoded_value)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(custom_field.id),                  condition.name)
        self.assertEqual({'operator': cfield_operator, 'rname': 'customfieldinteger', 'value': unicode(cfield_value)},
                         condition.decoded_value
                        )

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_DATECUSTOMFIELD, condition.type)
        self.assertEqual(str(datecfield.id),                        condition.name)
        self.assertEqual({'rname': 'customfielddatetime', 'name': datecfield_rtype},
                         condition.decoded_value
                        )

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_RELATION, condition.type)
        self.assertEqual(rtype.id,                           condition.name)
        self.assertEqual({'has': True},                      condition.decoded_value)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_RELATION_SUBFILTER, condition.type)
        self.assertEqual(srtype.id,                                    condition.name)
        self.assertEqual({'has': False, 'filter_id': relsubfilfer.id}, condition.decoded_value)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_PROPERTY, condition.type)
        self.assertEqual(ptype.id,                           condition.name)
        self.assert_(condition.decoded_value is True)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_SUBFILTER, condition.type)
        self.assertEqual(subfilter.id,                        condition.name)

    def test_create03(self): #error: no conditions of any type
        self.login()

        ct = ContentType.objects.get_for_model(Organisation)
        response = self.client.post('/creme_core/entity_filter/add/%s' % ct.id,
                                    data={
                                            'name': 'Filter 01',
                                            'user': self.user.id,
                                         }
                                   )
        self.assertFormError(response, 'form', field=None, errors=_('The filter must have at least one condition.'))

    def test_edit01(self):
        self.login()

        #Can not be a simple subfilter (bad content type)
        relsubfilfer = EntityFilter.create('test-filter01', 'Filter 01', Organisation, is_custom=True)

        subfilter = EntityFilter.create('test-filter02', 'Filter 02', Contact, is_custom=True)

        rtype, srtype = RelationType.create(('test-subject_love', u'Is loving'),
                                            ('test-object_love',  u'Is loved by')
                                           )
        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text=u'Kawaii')

        create_cf = CustomField.objects.create
        contact_ct = ContentType.objects.get_for_model(Contact)
        custom_field = create_cf(name='Nickname',      field_type=CustomField.STR,  content_type=contact_ct)
        datecfield   = create_cf(name='First meeting', field_type=CustomField.DATE, content_type=contact_ct)

        name = 'Filter 03'
        efilter = EntityFilter.create('test-filter03', name, Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.CONTAINS,
                                                                    name='first_name', values=['Atom']
                                                                   ),
                                EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='description', values=[False]
                                                                   ),
                                EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                                   start=date(year=2001, month=1, day=1),
                                                                   end=date(year=2010, month=12, day=31),
                                                                  ),
                                EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                                          operator=EntityFilterCondition.ICONTAINS,
                                                                          value='Ed'
                                                                         ),
                                EntityFilterCondition.build_4_datecustomfield(custom_field=datecfield,
                                                                              start=date(year=2010, month=1, day=1),
                                                                             ),
                                EntityFilterCondition.build_4_relation(rtype=rtype, has=True),
                                EntityFilterCondition.build_4_relation_subfilter(rtype=srtype, has=True, subfilter=relsubfilfer),
                                EntityFilterCondition.build_4_property(ptype, True),
                                EntityFilterCondition.build_4_subfilter(subfilter),
                               ])

        parent_filter = EntityFilter.create('test-filter04', 'Filter 04', Contact, is_custom=True)
        parent_filter.set_conditions([EntityFilterCondition.build_4_subfilter(efilter)])

        url = '/creme_core/entity_filter/edit/%s' % efilter.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        formfields = response.context['form'].fields
        self.assertEqual(Contact,        formfields['fields_conditions'].model)
        self.assertEqual(Contact,        formfields['relations_conditions'].model)
        self.assertEqual(Contact,        formfields['relsubfilfers_conditions'].model)
        self.assertEqual(Contact,        formfields['properties_conditions'].model)
        self.assertEqual([subfilter.id], [f.id for f in formfields['subfilters_conditions'].queryset])

        name += ' (edited)'
        field_operator = EntityFilterCondition.IEQUALS
        field_name = 'last_name'
        field_value = 'Ikari'
        date_field_name = 'birthday'
        cfield_operator = EntityFilterCondition.CONTAINS
        cfield_value = 'Vicious'
        datecfield_rtype = 'previous_year'
        response = self.client.post(url, follow=True,
                                    data={
                                            'name':                          name,
                                            'fields_conditions':             '[{"operator": "%(operator)s", "name": "%(name)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]' % {
                                                                                     'operator': field_operator,
                                                                                     'name':     field_name,
                                                                                     'value':    field_value,
                                                                                 },
                                            'datefields_conditions':        '[{"range": {"type": "", "start": "2011-5-23", "end": "2012-6-27"}, "field": "%s"}]' % date_field_name,
                                            'customfields_conditions':      '[{"field": "%(cfield)s", "operator": "%(operator)s", "value": "%(value)s"}]' % {
                                                                                    'cfield':   custom_field.id,
                                                                                    'operator': cfield_operator,
                                                                                    'value':    cfield_value,
                                                                                },
                                            'datecustomfields_conditions':  '[{"field": "%(cfield)s", "range": {"type": "%(type)s"}}]' % {
                                                                                    'cfield': datecfield.id,
                                                                                    'type':   datecfield_rtype,
                                                                                },
                                            'relations_conditions':         '[{"has": true, "rtype": "%s", "ctype": "0", "entity": null}]' % rtype.id,
                                            'relsubfilfers_conditions':     '[{"rtype": "%(rtype)s", "has": false, "ctype": "%(ct)s", "filter": "%(filter)s"}]' % {
                                                                                    'rtype':  srtype.id,
                                                                                    'ct':     ContentType.objects.get_for_model(Organisation).id,
                                                                                    'filter': relsubfilfer.id,
                                                                                },
                                            'properties_conditions':        '[{"has": false, "ptype": "%s"}]' % ptype.id,
                                            'subfilters_conditions':        [subfilter.id],
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        efilter = EntityFilter.objects.get(pk=efilter.id) #refresh
        self.assertEqual(name, efilter.name)
        self.assert_(efilter.is_custom)
        self.assert_(efilter.user is None)

        conditions = efilter.conditions.order_by('id')
        self.assertEqual(8, len(conditions))
        iter_conds = iter(conditions)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_FIELD,                       condition.type)
        self.assertEqual(field_name,                                            condition.name)
        self.assertEqual({'operator': field_operator, 'values': [field_value]}, condition.decoded_value)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual(date_field_name,                     condition.name)
        self.assertEqual({'start': {'year': 2011, u'month': 5, 'day': 23}, 'end': {'year': 2012, 'month': 6, 'day': 27}},
                         condition.decoded_value
                        )

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(custom_field.id),                  condition.name)
        self.assertEqual({'operator': cfield_operator, 'rname': 'customfieldstring', 'value': unicode(cfield_value)},
                         condition.decoded_value
                        )

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_DATECUSTOMFIELD, condition.type)
        self.assertEqual(str(datecfield.id),                        condition.name)
        self.assertEqual({'rname': 'customfielddatetime', 'name': datecfield_rtype},
                         condition.decoded_value
                        )

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_RELATION, condition.type)
        self.assertEqual(rtype.id,                           condition.name)
        self.assertEqual({'has': True},                      condition.decoded_value)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_RELATION_SUBFILTER, condition.type)
        self.assertEqual(srtype.id,                                    condition.name)
        self.assertEqual({'has': False, 'filter_id': relsubfilfer.id}, condition.decoded_value)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_PROPERTY, condition.type)
        self.assertEqual(ptype.id,                           condition.name)
        self.assert_(condition.decoded_value is False)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_SUBFILTER, condition.type)
        self.assertEqual(subfilter.id,                        condition.name)

    def test_edit02(self): #not custom -> can not edit
        self.login()

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=False)
        self.assertEqual(404, self.client.get('/creme_core/entity_filter/edit/%s' % efilter.id).status_code)

    def test_edit03(self): #can not edit Filter that belongs to another user
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, user=self.other_user, is_custom=True)
        self.assertEqual(404, self.client.get('/creme_core/entity_filter/edit/%s' % efilter.id).status_code)

    def test_edit04(self): #user do not have the app credentials
        self.login(is_superuser=False)

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, user=self.user, is_custom=True)
        self.assertEqual(404, self.client.get('/creme_core/entity_filter/edit/%s' % efilter.id).status_code)

    def test_edit05(self): #cycle error
        self.login()

        rtype, srtype = RelationType.create(('test-subject_love', u'Is loving'),
                                            ('test-object_love',  u'Is loved by')
                                           )

        efilter = EntityFilter.create('test-filter01', 'Filter 01', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='first_name', values=['Misato']
                                                                   )
                               ])

        parent_filter = EntityFilter.create('test-filter02', 'Filter 02', Contact, is_custom=True)
        parent_filter.set_conditions([EntityFilterCondition.build_4_subfilter(efilter)])

        response = self.client.post('/creme_core/entity_filter/edit/%s' % efilter.id, follow=True,
                                    data={
                                            'name':                     efilter.name,
                                            'relsubfilfers_conditions': '[{"rtype": "%(rtype)s", "has": false, "ctype": "%(ct)s", "filter": "%(filter)s"}]' % {
                                                                                'rtype':  rtype.id,
                                                                                'ct':     ContentType.objects.get_for_model(Contact).id,
                                                                                'filter': parent_filter.id, #PROBLEM IS HERE !!!
                                                                            },
                                         }
                                   )
        self.assertFormError(response, 'form', field=None, errors=_(u'There is a cycle with a subfilter.'))

    def test_delete01(self):
        self.login()

        efilter = EntityFilter.create('test-filter01', 'Filter 01', Contact, is_custom=True)
        response = self.client.post('/creme_core/entity_filter/delete', data={'id': efilter.id}, follow=True)
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assert_(response.redirect_chain[-1][0].endswith(Contact.get_lv_absolute_url()))
        self.assertEqual(0, EntityFilter.objects.filter(pk=efilter.id).count())

    def test_delete02(self): #not custom -> can not delete
        self.login()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, is_custom=False)
        self.client.post('/creme_core/entity_filter/delete', data={'id': efilter.id})
        self.assertEqual(1, EntityFilter.objects.filter(pk=efilter.id).count())

    def test_delete03(self): #belongs to another user
        self.login(is_superuser=False)

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=True, user=self.other_user)
        self.client.post('/creme_core/entity_filter/delete', data={'id': efilter.id})
        self.assertEqual(1, EntityFilter.objects.filter(pk=efilter.id).count())

    def test_delete04(self): #belongs to my team -> ok
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        my_team = User.objects.create(username='TeamTitan', is_team=True)
        my_team.teammates = [self.user]

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=True, user=my_team)
        self.client.post('/creme_core/entity_filter/delete', data={'id': efilter.id})
        self.assertEqual(0, EntityFilter.objects.filter(pk=efilter.id).count())

    def test_delete05(self): #belongs to a team (not mine) -> ko
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        a_team = User.objects.create(username='TeamTitan', is_team=True)
        a_team.teammates = [self.other_user]

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=True, user=a_team)
        self.client.post('/creme_core/entity_filter/delete', data={'id': efilter.id})
        self.assertEqual(1, EntityFilter.objects.filter(pk=efilter.id).count())

    def test_delete06(self): #logged as superuser
        self.login()

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=True, user=self.other_user)
        self.client.post('/creme_core/entity_filter/delete', data={'id': efilter.id})
        self.failIf(EntityFilter.objects.filter(pk=efilter.id).count())

    def test_delete07(self): #can not delete if used as subfilter
        self.login()

        efilter01 = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=True)
        efilter02 = EntityFilter.create('test-filter02', 'Filter02', Contact, is_custom=True)
        efilter02.set_conditions([EntityFilterCondition.build_4_subfilter(efilter01)])

        self.client.post('/creme_core/entity_filter/delete', data={'id': efilter01.id})
        self.assert_(EntityFilter.objects.filter(pk=efilter01.id).exists())

    def test_delete08(self): #can not delete if used as subfilter (for relations)
        self.login()

        rtype, srtype = RelationType.create(('test-subject_love', u'Is loving'),
                                            ('test-object_love',  u'Is loved by')
                                           )

        efilter01 = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=True)
        efilter02 = EntityFilter.create('test-filter02', 'Filter02', Contact, is_custom=True)
        efilter02.set_conditions([EntityFilterCondition.build_4_relation_subfilter(rtype=srtype, has=True, subfilter=efilter01)])

        self.client.post('/creme_core/entity_filter/delete', data={'id': efilter01.id})
        self.assert_(EntityFilter.objects.filter(pk=efilter01.id).exists())

    def test_get_content_types01(self):
        self.login()

        rtype, srtype = RelationType.create(('test-subject_love', u'Is loving'),
                                            ('test-object_love',  u'Is loved by')
                                           )

        response = self.client.get('/creme_core/entity_filter/rtype/%s/content_types' % rtype.id)
        self.assertEqual(200, response.status_code)

        content = simplejson.loads(response.content)
        self.assert_(isinstance(content, list))
        self.assert_(len(content) > 1)
        self.assert_(all(len(t) == 2 for t in content))
        self.assert_(all(isinstance(t[0], int) for t in content))
        self.assertEqual([0, _(u'All')], content[0])

    def test_get_content_types02(self):
        self.login()

        rtype, srtype = RelationType.create(('test-subject_love', u'Is loving',),
                                            ('test-object_love',  u'Is loved by', (Contact,))
                                           )

        response = self.client.get('/creme_core/entity_filter/rtype/%s/content_types' % rtype.id)
        self.assertEqual(200, response.status_code)

        ct = ContentType.objects.get_for_model(Contact)
        self.assertEqual([[0, _(u'All')], [ct.id, unicode(ct)]],
                         simplejson.loads(response.content)
                        )

    def test_filters_for_ctype01(self):
        self.login()

        ct = ContentType.objects.get_for_model(Contact)
        response = self.client.get('/creme_core/entity_filter/get_for_ctype/%s' % ct.id)
        self.assertEqual(200, response.status_code)

        content = simplejson.loads(response.content)
        self.assert_(isinstance(content, list))
        self.failIf(content)

    def test_filters_for_ctype02(self):
        self.login()

        efilter01 = EntityFilter.create('test-filter01', 'Filter 01', Contact)
        efilter02 = EntityFilter.create('test-filter02', 'Filter 02', Contact)
        efilter03 = EntityFilter.create('test-filter03', 'Filter 03', Organisation)

        ct = ContentType.objects.get_for_model(Contact)
        response = self.client.get('/creme_core/entity_filter/get_for_ctype/%s' % ct.id)
        self.assertEqual(200, response.status_code)
        self.assertEqual([[efilter01.id, 'Filter 01'], [efilter02.id, 'Filter 02']],
                         simplejson.loads(response.content)
                        )

    def test_filters_for_ctype03(self):
        self.login(is_superuser=False)

        ct = ContentType.objects.get_for_model(Contact)
        response = self.client.get('/creme_core/entity_filter/get_for_ctype/%s' % ct.id)
        self.assertEqual(403, response.status_code)
