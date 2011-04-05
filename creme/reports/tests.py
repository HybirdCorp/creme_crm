# -*- coding: utf-8 -*-

from datetime import datetime
from itertools import chain

from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremePropertyType, CremeProperty, RelationType, Relation
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD, HFI_RELATION, HFI_FUNCTION
from creme_core.constants import REL_SUB_RELATED_TO
from creme_core.tests.base import CremeTestCase

from persons.models import Contact, Organisation

from reports.models import *


class ReportsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'reports')
        self.login()

    def test_report_createview01(self):
        response = self.client.get('/reports/report/add')
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/reports/report/add',
                                    data={
                                            'user': self.user.pk,
                                            'name': 'name',
                                            'ct':   ContentType.objects.get_for_model(Contact).id,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)
        self.assert_(response.context['form'].errors, 'No view or field selected')

    def create_report(self, name):
        ct_id = ContentType.objects.get_for_model(Contact).id

        hf = HeaderFilter.objects.create(pk='test_hf', name='name', entity_type_id=ct_id)
        create_hfi = HeaderFilterItem.objects.create
        create_hfi(pk='hfi1', order=1, name='last_name',             title='Last name',  type=HFI_FIELD,    header_filter=hf, filter_string="last_name__icontains")
        create_hfi(pk='hfi2', order=2, name='user',                  title='User',       type=HFI_FIELD,    header_filter=hf, filter_string="user__username__icontains")
        create_hfi(pk='hfi3', order=3, name='related_to',            title='Related to', type=HFI_RELATION, header_filter=hf, filter_string="", relation_predicat_id=REL_SUB_RELATED_TO)
        create_hfi(pk='hfi4', order=4, name='get_pretty_properties', title='Properties', type=HFI_FUNCTION, header_filter=hf, filter_string="")

        response = self.client.post('/reports/report/add', follow=True,
                                    data={
                                            'user': self.user.pk,
                                            'name': name,
                                            'ct':   ct_id,
                                            'hf':   hf.id,
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        try:
            report = Report.objects.get(name=name)
        except Report.DoesNotExist, e:
            self.fail('report not created ?!')

        return report

    def create_simple_report(self, name):
        ct = ContentType.objects.get_for_model(Contact)
        report = Report.objects.create(name=name, ct=ct, user=self.user)
        field_id=Field.objects.create(name=u'id', title=u'Id', order=1, type=HFI_FIELD)
        report.columns.add(field_id)
        return report

    def create_simple_contact(self):
        return Contact.objects.create(user=self.user)


    def get_field(self, report, field_name):
        try:
            return report.columns.get(name=field_name)
        except Field.DoesNotExist, e:
            self.fail(str(e))

    def test_report_createview02(self):
        name  = 'trinita'
        self.failIf(Report.objects.filter(name=name).exists())

        report  = self.create_report(name)
        columns = list(report.columns.order_by('order'))
        self.assertEqual(4, len(columns))

        field = columns[0]
        self.assertEqual('last_name', field.name)
        self.assertEqual('Last name', field.title)
        self.assertEqual(HFI_FIELD,   field.type)
        self.failIf(field.selected)
        self.failIf(field.report)

        self.assertEqual('user', columns[1].name)

        field = columns[2]
        self.assertEqual(REL_SUB_RELATED_TO, field.name)
        self.assertEqual('Related to',       field.title)
        self.assertEqual(HFI_RELATION,       field.type)
        self.failIf(field.selected)
        self.failIf(field.report)

        field = columns[3]
        self.assertEqual('get_pretty_properties', field.name)
        self.assertEqual('Properties', field.title)
        self.assertEqual(HFI_FUNCTION, field.type)

    def test_report_editview(self):
        report = self.create_report('trinita')

        response = self.client.get('/reports/report/edit/%s' % report.id)
        self.assertEqual(200, response.status_code)

        #TODO: complete this test

    def test_report_change_field_order01(self):
        report = self.create_report('trinita')
        field  = self.get_field(report, 'user')

        self.assertEqual(404, self.client.post('/reports/report/field/change_order').status_code)

        response = self.client.post('/reports/report/field/change_order',
                                    data={
                                            'report_id': report.id,
                                            'field_id':  field.id,
                                            'direction': 'up',
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        mod_report = Report.objects.get(pk=report.id) #seems useless but...
        self.assertEqual(['user', 'last_name', REL_SUB_RELATED_TO, 'get_pretty_properties'],
                         [f.name for f in mod_report.columns.order_by('order')])

    def test_report_change_field_order02(self):
        report = self.create_report('trinita')
        field  = self.get_field(report, 'user')

        response = self.client.post('/reports/report/field/change_order',
                                    data={
                                            'report_id': report.id,
                                            'field_id':  field.id,
                                            'direction': 'down',
                                         }
                                   )
        self.assertEqual(response.status_code, 200)

        mod_report = Report.objects.get(pk=report.id) #seems useless but...
        self.assertEqual(['last_name', REL_SUB_RELATED_TO, 'user', 'get_pretty_properties'],
                         [f.name for f in mod_report.columns.order_by('order')])

    def test_report_change_field_order03(self): #move 'up' the first field -> error
        report = self.create_report('trinita')
        field  = self.get_field(report, 'last_name')

        self.assertEqual(404, self.client.post('/reports/report/field/change_order').status_code)

        response = self.client.post('/reports/report/field/change_order',
                                    data={
                                            'report_id': report.id,
                                            'field_id':  field.id,
                                            'direction': 'up',
                                         }
                                   )
        self.assertEqual(response.status_code, 403)

    def test_report_csv01(self):
        report   = self.create_report('trinita')
        response = self.client.get('/reports/report/%s/csv' % report.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['CONTENT_TYPE'], 'text/html; charset=utf-8')
        self.assertEqual("Last name;User;Related to;Properties\r\n", response.content)

    def create_contacts(self):
        create_contact = Contact.objects.create
        asuka  = create_contact(user=self.user, last_name='Langley',   first_name='Asuka',  birthday=datetime(year=1981, month=7, day=25))
        rei    = create_contact(user=self.user, last_name='Ayanami',   first_name='Rei',    birthday=datetime(year=1981, month=3, day=26))
        misato = create_contact(user=self.user, last_name='Katsuragi', first_name='Misato', birthday=datetime(year=1976, month=8, day=12))
        nerv   = Organisation.objects.create(user=self.user, name='Nerv')

        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text='Kawaii')
        CremeProperty.objects.create(type=ptype, creme_entity=rei)

        Relation.objects.create(user=self.user, type_id=REL_SUB_RELATED_TO,
                                subject_entity=misato, object_entity=nerv)

    def test_report_csv02(self):
        self.create_contacts()
        report   = self.create_report('trinita')
        response = self.client.get('/reports/report/%s/csv' % report.id)
        self.assertEqual(response.status_code, 200)

        content = [s for s in response.content.split('\r\n') if s]
        self.assertEqual(4, len(content))
        self.assertEqual('Last name;User;Related to;Properties',     content[0])
        self.assertEqual('Ayanami;Kirika;;<ul><li>Kawaii</li></ul>', content[1]) #alphabetical ordering ??
        self.assertEqual('Katsuragi;Kirika;Nerv;<ul></ul>',          content[2])
        self.assertEqual('Langley;Kirika;;<ul></ul>',                content[3])

    def test_report_csv03(self): #with date filter
        self.create_contacts()
        report   = self.create_report('trinita')
        response = self.client.get('/reports/report/%s/csv' % report.id,
                                   data={
                                            'field': 'birthday',
                                            'start': datetime(year=1980, month=1, day=1).strftime('%s'),
                                            'end':   datetime(year=2000, month=1, day=1).strftime('%s'),
                                         }
                                  )
        self.assertEqual(response.status_code, 200)

        content = [s for s in response.content.split('\r\n') if s]
        self.assertEqual(3, len(content))
        self.assertEqual('Ayanami;Kirika;;<ul><li>Kawaii</li></ul>', content[1])
        self.assertEqual('Langley;Kirika;;<ul></ul>',                content[2])

    def test_report_csv04(self):
        report = self.create_report('trinita')

        def assert_csv_error(**kwargs):
            response = self.client.get('/reports/report/%s/csv' % report.id, data=kwargs)
            self.assertEqual(response.status_code, 404)

        date_str1 = datetime(year=1980, month=1, day=1).strftime('%s')
        date_str2 = datetime(year=2000, month=1, day=1).strftime('%s')

        #assert_csv_error(field='birthday', start=date_str1, end=date_str2) #this works of course :)
        assert_csv_error(start=date_str1, end=date_str2)    #no 'field'
        assert_csv_error(field='birthday', end=date_str2)   #no 'start'
        assert_csv_error(field='birthday', start=date_str1) #no 'end'
        assert_csv_error(field='birthday', start='poo', end=date_str2)
        assert_csv_error(field='birthday', start=date_str1, end='pee')
        assert_csv_error(field='idontexist', start=date_str1, end=date_str2)
        assert_csv_error(field='first_name', start=date_str1, end=date_str2) #not a datefield

    def test_report_field_add01(self):
        report = self.create_report('trinita')
        url = '/reports/report/%s/field/add' % report.id
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        try:
            form = response.context['form']
            fields_columns = form.fields['columns']
        except KeyError, e:
            self.fail(str(e))

        for i, (fname, fvname) in enumerate(fields_columns.choices):
            if fname == 'last_name': created_index = i; break
        else:
            self.fail('No "last_name" field')

        response = self.client.post(url,
                                    data={
                                            'user': self.user.pk,
                                            'columns_check_%s' % created_index: 'on',
                                            'columns_value_%s' % created_index: 'last_name',
                                            'columns_order_%s' % created_index: 1,
                                         }
                                   )

        self.assertEqual(response.status_code, 200)
        self.assertNoFormError(response)
        self.assertEqual(1, report.columns.count())


    def test_report_fetch01(self):
        report = self.create_simple_report("Contacts report")
        contact_ids = set([str(self.create_simple_contact().id) for i in xrange(10)])

        self.assertEqual(contact_ids, set(chain.from_iterable(report.fetch())))




#TODO: test with subreports, expanding etc...
