# -*- coding: utf-8 -*-

try:
    from datetime import date
    from functools import partial

    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType
    from django.core.serializers.json import simplejson
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import (EntityFilter, EntityFilterCondition,
            EntityFilterVariable, CustomField, RelationType, CremePropertyType)
    from .base import ViewsTestCase

    from creme.documents.models import Document

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('EntityFilterViewsTestCase', )


class EntityFilterViewsTestCase(ViewsTestCase):
    FIELDS_CONDS_FMT       = '[{"field": {"name": "%(name)s"}, "operator": {"id": "%(operator)s"}, "value": %(value)s}]'
    DATE_FIELDS_CONDS_FMT  = '[{"range": {"type": "%(type)s", "start": "%(start)s", "end": "%(end)s"}, "field": "%(name)s"}]'
    CFIELDS_CONDS_FMT      = '[{"field": {"id": "%(cfield)s"}, "operator": {"id": "%(operator)s"}, "value": %(value)s}]'
    DATE_CFIELDS_CONDS_FMT = '[{"field": "%(cfield)s", "range": {"type": "%(type)s"}}]'
    RELATIONS_CONDS_FMT    = '[{"has": true, "rtype": "%s", "ctype": 0, "entity": null}]'
    RELSUBFILTER_CONDS_FMT = '[{"rtype": "%(rtype)s", "has": false, "ctype": %(ct)s, "filter": "%(filter)s"}]'
    PROP_CONDS_FMT         = '[{"has": %(has)s, "ptype": "%(ptype)s"}]'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config')

        EntityFilterCondition.objects.all().delete()
        EntityFilter.objects.all().delete()

        get_ct = ContentType.objects.get_for_model
        cls.ct_contact = get_ct(Contact)
        cls.ct_orga    = get_ct(Organisation)

    def _build_add_url(self, ct):
        return '/creme_core/entity_filter/add/%s' % ct.id

    def _build_get_ct_url(self, rtype):
        return '/creme_core/entity_filter/rtype/%s/content_types' % rtype.id

    def _buid_get_filter(self, ct):
        return '/creme_core/entity_filter/get_for_ctype/%s' % ct.id

    def test_create01(self):
        "Check app credentials"
        self.login(is_superuser=False)

        ct = self.ct_contact
        self.assertFalse(EntityFilter.objects.filter(entity_type=ct).count())

        uri = self._build_add_url(ct)
        self.assertGET403(uri)

        self.role.allowed_apps = ['persons']
        self.role.save()
        response = self.assertGET200(uri)

        with self.assertNoException():
            fields = response.context['form'].fields
            cf_f = fields['customfields_conditions']
            dcf_f = fields['datecustomfields_conditions']

        self.assertEqual('', cf_f.initial)
        self.assertEqual('', dcf_f.initial)
        self.assertEqual(_('No custom field at present.'), cf_f.help_text)
        self.assertEqual(_('No date custom field at present.'), dcf_f.help_text)

        name = 'Filter 01'
        operator = EntityFilterCondition.IEQUALS
        field_name = 'last_name'
        value = 'Ikari'
        response = self.client.post(uri, follow=True,
                                    data={'name':              name,
                                          'use_or':            'False',
                                          'fields_conditions': self.FIELDS_CONDS_FMT % {
                                                                      'operator': operator,
                                                                      'name':     field_name,
                                                                      'value':    '"' + value + '"',
                                                                  },
                                         }
                                   )
        self.assertNoFormError(response)

        efilters = EntityFilter.objects.filter(entity_type=ct)
        self.assertEqual(1, len(efilters))

        efilter = efilters[0]
        self.assertEqual(name, efilter.name)
        self.assertTrue(efilter.is_custom)
        self.assertIsNone(efilter.user)
        self.assertFalse(efilter.use_or)

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(field_name,                                condition.name)
        self.assertEqual({'operator': operator, 'values': [value]}, condition.decoded_value)

    def test_create02(self):
        self.login()
        ct = self.ct_orga

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
        datecfield   = create_cf(name='Last gathering', field_type=CustomField.DATETIME, content_type=ct)

        url = self._build_add_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            cf_f  = fields['customfields_conditions']
            dcf_f = fields['datecustomfields_conditions']
            sb_f  = fields['subfilters_conditions']

        self.assertEqual('', cf_f.initial)
        self.assertEqual('', dcf_f.initial)
        self.assertEqual([subfilter.id], [f.id for f in sb_f.queryset])
        #self.assertEqual(_('(Only integers, strings and decimals for now)'), cf_f.help_text)
        self.assertEqual('', dcf_f.help_text)

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
                                    data={'name':   name,
                                          'user':   self.user.id,
                                          'use_or': 'True',
                                          'fields_conditions':           self.FIELDS_CONDS_FMT % {
                                                                                'operator': field_operator,
                                                                                'name':     field_name,
                                                                                'value':    '"' + field_value + '"',
                                                                            },
                                          'datefields_conditions':       self.DATE_FIELDS_CONDS_FMT % {
                                                                                'type': daterange_type,
                                                                                'start': '',
                                                                                'end': '',
                                                                                'name': date_field_name,
                                                                            },
                                          'customfields_conditions':     self.CFIELDS_CONDS_FMT % {
                                                                                'cfield':   custom_field.id,
                                                                                'operator': cfield_operator,
                                                                                'value':    cfield_value,
                                                                            },
                                          'datecustomfields_conditions': self.DATE_CFIELDS_CONDS_FMT % {
                                                                                'cfield': datecfield.id,
                                                                                'type':   datecfield_rtype,
                                                                            },
                                          'relations_conditions':        self.RELATIONS_CONDS_FMT % rtype.id,
                                          'relsubfilfers_conditions':    self.RELSUBFILTER_CONDS_FMT % {
                                                                                'rtype':  srtype.id,
                                                                                'ct':     self.ct_contact.id,
                                                                                'filter': relsubfilfer.id,
                                                                            },
                                          'properties_conditions':       self.PROP_CONDS_FMT % {
                                                                                'has':   'true',
                                                                                'ptype': ptype.id,
                                                                            },
                                          'subfilters_conditions':       [subfilter.id],
                                         }
                                   )
        self.assertNoFormError(response, status=302)

        efilter = self.get_object_or_fail(EntityFilter, name=name)
        self.assertEqual(self.user.id, efilter.user.id)
        self.assertIs(efilter.use_or, True)

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
        self.assertIs(condition.decoded_value, True)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_SUBFILTER, condition.type)
        self.assertEqual(subfilter.id,                        condition.name)

    def test_create03(self):
        "Date sub-field"
        self.login()

        ct = ContentType.objects.get_for_model(Document)
        name = 'Filter Doc'
        field_name = 'folder__created'
        daterange_type = 'previous_year'
        response = self.client.post(self._build_add_url(ct), follow=True,
                                    data={'name':                  name,
                                          'use_or':                'False',
                                          'datefields_conditions': self.DATE_FIELDS_CONDS_FMT % {
                                                                        'type': daterange_type,
                                                                        'name': field_name,
                                                                        'start': '',
                                                                        'end': '',
                                                                    },
                                         }
                                   )
        self.assertNoFormError(response)

        efilter = self.get_object_or_fail(EntityFilter, entity_type=ct, name=name)

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_DATEFIELD, condition.type)
        self.assertEqual(field_name,                          condition.name)
        self.assertEqual({'name': daterange_type},            condition.decoded_value)

    def test_create04(self):
        "Error: no conditions of any type"
        self.login()

        ct = self.ct_orga
        response = self.client.post(self._build_add_url(ct),
                                    data={'name': 'Filter 01',
                                          'user': self.user.id,
                                          'use_or': 'False',
                                         }
                                   )
        self.assertFormError(response, 'form', field=None, errors=_('The filter must have at least one condition.'))

    def test_create_currentuser_filter(self):
        self.login()

        ct = self.ct_orga
        response = self.client.post(self._build_add_url(ct),
                                    data={'name':   'Filter 01',
                                          'user':   self.user.id,
                                          'use_or': 'True',
                                          'fields_conditions': self.FIELDS_CONDS_FMT % {
                                                                   'operator': EntityFilterCondition.EQUALS,
                                                                   'name':     'user',
                                                                   'value':    '"' + EntityFilterVariable.CURRENT_USER + '"',
                                                               },
                                         }
                                   )

        self.assertNoFormError(response, status=302)

        efilter = self.get_object_or_fail(EntityFilter, name='Filter 01')
        self.assertEqual(self.user.id, efilter.user.id)
        self.assertIs(efilter.use_or, True)

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))
        iter_conds = iter(conditions)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
        self.assertEqual('user',                          condition.name)
        self.assertEqual({'operator': EntityFilterCondition.EQUALS,
                          'values':   [EntityFilterVariable.CURRENT_USER],
                         },
                         condition.decoded_value
                        )

    def test_edit01(self):
        self.login()

        #Can not be a simple subfilter (bad content type)
        relsubfilfer = EntityFilter.create('test-filter01', 'Filter 01', Organisation, is_custom=True)

        subfilter = EntityFilter.create('test-filter02', 'Filter 02', Contact, is_custom=True)

        rtype, srtype = RelationType.create(('test-subject_love', u'Is loving'),
                                            ('test-object_love',  u'Is loved by')
                                           )
        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text=u'Kawaii')

        create_cf = partial(CustomField.objects.create, content_type=self.ct_contact)
        custom_field = create_cf(name='Nickname',      field_type=CustomField.STR)
        datecfield   = create_cf(name='First meeting', field_type=CustomField.DATETIME)

        name = 'Filter 03'
        efilter = EntityFilter.create('test-filter03', name, Contact, is_custom=True)
        cf_cond = EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                            operator=EntityFilterCondition.ICONTAINS,
                                                            value='Ed',
                                                           )
        datecf_cond = EntityFilterCondition.build_4_datecustomfield(custom_field=datecfield,
                                                                    start=date(year=2010, month=1, day=1),
                                                                   )
        efilter.set_conditions(
            [EntityFilterCondition.build_4_field(model=Contact,
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
             cf_cond, datecf_cond,
             EntityFilterCondition.build_4_relation(rtype=rtype, has=True),
             EntityFilterCondition.build_4_relation_subfilter(rtype=srtype, has=True,
                                                              subfilter=relsubfilfer,
                                                             ),
             EntityFilterCondition.build_4_property(ptype, True),
             EntityFilterCondition.build_4_subfilter(subfilter),
            ])

        parent_filter = EntityFilter.create('test-filter04', 'Filter 04', Contact, is_custom=True)
        parent_filter.set_conditions([EntityFilterCondition.build_4_subfilter(efilter)])

        url = '/creme_core/entity_filter/edit/%s' % efilter.id
        response = self.assertGET200(url)

        formfields = response.context['form'].fields
        self.assertEqual(Contact,        formfields['fields_conditions'].model)
        self.assertEqual(Contact,        formfields['relations_conditions'].model)
        self.assertEqual(Contact,        formfields['relsubfilfers_conditions'].model)
        self.assertEqual(Contact,        formfields['properties_conditions'].model)
        self.assertEqual([subfilter.id], [f.id for f in formfields['subfilters_conditions'].queryset])
        self.assertEqual([cf_cond],      formfields['customfields_conditions'].initial)
        self.assertEqual([datecf_cond],  formfields['datecustomfields_conditions'].initial)

        name += ' (edited)'
        field_operator = EntityFilterCondition.IEQUALS
        field_name = 'last_name'
        field_value = 'Ikari'
        date_field_name = 'birthday'
        cfield_operator = EntityFilterCondition.CONTAINS
        cfield_value = 'Vicious'
        datecfield_rtype = 'previous_year'
        response = self.client.post(url, follow=True,
                                    data={'name':                        name,
                                          'use_or':                      'True',
                                          'fields_conditions':           self.FIELDS_CONDS_FMT % {
                                                                                'operator': field_operator,
                                                                                'name':     field_name,
                                                                                'value':    '"' + field_value + '"',
                                                                            },
                                          'datefields_conditions':       self.DATE_FIELDS_CONDS_FMT % {
                                                                                'type':  '',
                                                                                'start': '2011-5-23',
                                                                                'end':   '2012-6-27',
                                                                                'name':   date_field_name,
                                                                            },
                                          'customfields_conditions':     self.CFIELDS_CONDS_FMT % {
                                                                                'cfield':   custom_field.id,
                                                                                'operator': cfield_operator,
                                                                                'value':    '"' + cfield_value + '"',
                                                                            },
                                          'datecustomfields_conditions': self.DATE_CFIELDS_CONDS_FMT % {
                                                                                'cfield': datecfield.id,
                                                                                'type':   datecfield_rtype,
                                                                            },
                                          'relations_conditions':        self.RELATIONS_CONDS_FMT % rtype.id,
                                          'relsubfilfers_conditions':    self.RELSUBFILTER_CONDS_FMT % {
                                                                                'rtype':  srtype.id,
                                                                                'ct':     self.ct_orga.id,
                                                                                'filter': relsubfilfer.id,
                                                                            },
                                          'properties_conditions':       self.PROP_CONDS_FMT % {
                                                                                'has':   'false',
                                                                                'ptype': ptype.id,
                                                                            },
                                          'subfilters_conditions':       [subfilter.id],
                                         }
                                   )
        self.assertNoFormError(response)

        efilter = EntityFilter.objects.get(pk=efilter.id) #refresh
        self.assertEqual(name, efilter.name)
        self.assertIs(efilter.is_custom, True)
        self.assertIsNone(efilter.user)

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
        self.assertEqual({'start': {'year': 2011, 'month': 5, 'day': 23},
                          'end':   {'year': 2012, 'month': 6, 'day': 27},
                         },
                         condition.decoded_value
                        )

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, condition.type)
        self.assertEqual(str(custom_field.id),                  condition.name)
        self.assertEqual({'operator': cfield_operator,
                          'rname':    'customfieldstring',
                          'value':    unicode(cfield_value),
                         },
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
        self.assertIs(condition.decoded_value, False)

        condition = iter_conds.next()
        self.assertEqual(EntityFilterCondition.EFC_SUBFILTER, condition.type)
        self.assertEqual(subfilter.id,                        condition.name)

    def test_edit02(self):
        "Not custom -> can not edit"
        self.login()

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=False)
        self.assertGET403('/creme_core/entity_filter/edit/%s' % efilter.id)

    def test_edit03(self):
        "Can not edit Filter that belongs to another user"
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, user=self.other_user, is_custom=True)
        self.assertGET403('/creme_core/entity_filter/edit/%s' % efilter.id)

    def test_edit04(self):
        "User do not have the app credentials"
        self.login(is_superuser=False)

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, user=self.user, is_custom=True)
        self.assertGET403('/creme_core/entity_filter/edit/%s' % efilter.id)

    def test_edit05(self):
        "Cycle error"
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
                                    data={'name':                     efilter.name,
                                          'use_or':                   'False',
                                          'relsubfilfers_conditions': self.RELSUBFILTER_CONDS_FMT % {
                                                                            'rtype':  rtype.id,
                                                                            'ct':     self.ct_contact.id,
                                                                            'filter': parent_filter.id, #PROBLEM IS HERE !!!
                                                                        },
                                         }
                                   )
        self.assertFormError(response, 'form', field=None, errors=_(u'There is a cycle with a subfilter.'))

    def _delete(self, efilter, **kwargs):
        return self.client.post('/creme_core/entity_filter/delete', data={'id': efilter.id}, **kwargs)

    def test_delete01(self):
        self.login()

        efilter = EntityFilter.create('test-filter01', 'Filter 01', Contact, is_custom=True)
        response = self._delete(efilter, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertRedirects(response, Contact.get_lv_absolute_url())
        self.assertEqual(0, EntityFilter.objects.filter(pk=efilter.id).count())

    def test_delete02(self):
        "Not custom -> can not delete"
        self.login()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, is_custom=False)
        self._delete(efilter)
        self.assertEqual(1, EntityFilter.objects.filter(pk=efilter.id).count())

    def test_delete03(self):
        "Belongs to another user"
        self.login(is_superuser=False)

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=True, user=self.other_user)
        self._delete(efilter)
        self.assertEqual(1, EntityFilter.objects.filter(pk=efilter.id).count())

    def test_delete04(self):
        "Belongs to my team -> ok"
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        my_team = User.objects.create(username='TeamTitan', is_team=True)
        my_team.teammates = [self.user]

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=True, user=my_team)
        self._delete(efilter)
        self.assertEqual(0, EntityFilter.objects.filter(pk=efilter.id).count())

    def test_delete05(self):
        "Belongs to a team (not mine) -> ko"
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        my_team = User.objects.create(username='A-team', is_team=True)
        my_team.teammates = [self.user]

        a_team = User.objects.create(username='TeamTitan', is_team=True)
        a_team.teammates = [self.other_user]

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=True, user=a_team)
        self._delete(efilter)
        self.assertEqual(1, EntityFilter.objects.filter(pk=efilter.id).count())

    def test_delete06(self):
        "Logged as superuser"
        self.login()

        efilter = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=True, user=self.other_user)
        self._delete(efilter)
        self.assertDoesNotExist(efilter)

    def test_delete07(self):
        "Can not delete if used as subfilter"
        self.login()

        efilter01 = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=True)
        efilter02 = EntityFilter.create('test-filter02', 'Filter02', Contact, is_custom=True)
        efilter02.set_conditions([EntityFilterCondition.build_4_subfilter(efilter01)])

        self._delete(efilter01)
        self.assertStillExists(efilter01)

    def test_delete08(self):
        "Can not delete if used as subfilter (for relations)"
        self.login()

        rtype, srtype = RelationType.create(('test-subject_love', u'Is loving'),
                                            ('test-object_love',  u'Is loved by')
                                           )

        efilter01 = EntityFilter.create('test-filter01', 'Filter01', Contact, is_custom=True)
        efilter02 = EntityFilter.create('test-filter02', 'Filter02', Contact, is_custom=True)
        efilter02.set_conditions([EntityFilterCondition.build_4_relation_subfilter(rtype=srtype, has=True, subfilter=efilter01)])

        self._delete(efilter01)
        self.assertStillExists(efilter01)

    def test_get_content_types01(self):
        self.login()

        rtype, srtype = RelationType.create(('test-subject_love', u'Is loving'),
                                            ('test-object_love',  u'Is loved by')
                                           )

        response = self.assertGET200(self._build_get_ct_url(rtype))

        content = simplejson.loads(response.content)
        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 1)
        self.assertTrue(all(len(t) == 2 for t in content))
        self.assertTrue(all(isinstance(t[0], int) for t in content))
        self.assertEqual([0, _(u'All')], content[0])

    def test_get_content_types02(self):
        self.login()

        rtype, srtype = RelationType.create(('test-subject_love', u'Is loving',),
                                            ('test-object_love',  u'Is loved by', (Contact,))
                                           )

        response = self.assertGET200(self._build_get_ct_url(rtype))

        ct = self.ct_contact
        self.assertEqual([[0, _(u'All')], [ct.id, unicode(ct)]],
                         simplejson.loads(response.content)
                        )

    def test_filters_for_ctype01(self):
        self.login()

        response = self.assertGET200(self._buid_get_filter(self.ct_contact))

        content = simplejson.loads(response.content)
        self.assertIsInstance(content, list)
        self.assertFalse(content)

    def test_filters_for_ctype02(self):
        self.login()

        efilter01 = EntityFilter.create('test-filter01', 'Filter 01', Contact)
        efilter02 = EntityFilter.create('test-filter02', 'Filter 02', Contact)
        EntityFilter.create('test-filter03', 'Filter 03', Organisation)

        response = self.assertGET200(self._buid_get_filter(self.ct_contact))
        self.assertEqual([[efilter01.id, 'Filter 01'], [efilter02.id, 'Filter 02']],
                         simplejson.loads(response.content)
                        )

    def test_filters_for_ctype03(self):
        self.login(is_superuser=False)
        self.assertGET403('/creme_core/entity_filter/get_for_ctype/%s' % self.ct_contact.id)

    def test_filters_for_ctype04(self):
        "Include 'All' fake filter"
        self.login()

        efilter01 = EntityFilter.create('test-filter01', 'Filter 01', Contact)
        efilter02 = EntityFilter.create('test-filter02', 'Filter 02', Contact)
        EntityFilter.create('test-filter03', 'Filter 03', Organisation)

        response = self.assertGET200('/creme_core/entity_filter/get_for_ctype/%s/all' % self.ct_contact.id)
        self.assertEqual([['',           _(u'All')],
                          [efilter01.id, 'Filter 01'],
                          [efilter02.id, 'Filter 02'],
                         ],
                         simplejson.loads(response.content)
                        )
