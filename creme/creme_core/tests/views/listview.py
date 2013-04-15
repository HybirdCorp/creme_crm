# -*- coding: utf-8 -*-

try:
    from datetime import date
    from functools import partial

    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import (HeaderFilter, HeaderFilterItem,
                                         EntityFilter, EntityFilterCondition,
                                         RelationType, Relation,
                                         CremePropertyType, CremeProperty,
                                         CustomField, CustomFieldEnumValue)
    from creme.creme_core.utils import safe_unicode
    from .base import ViewsTestCase

    from creme.persons.models import Organisation, Contact

    from creme.billing.models import Invoice, InvoiceStatus, Line, ProductLine, ServiceLine
    from creme.billing.models.line import PRODUCT_LINE_TYPE, SERVICE_LINE_TYPE
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ListViewTestCase', )


class ListViewTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'billing')
        cls.url = Organisation.get_lv_absolute_url()
        cls.ctype = ContentType.objects.get_for_model(Organisation)

    def assertFound(self, x, string): #TODO: in CremeTestCase ??
        idx = string.find(x)
        self.assertNotEqual(-1, idx, '"%s" not found' % x)

        return idx

    def _get_lv_content(self, response): #TODO: slice end too
        content = response.content
        start_idx = content.find('<table id="list"')
        self.assertNotEqual(-1, start_idx)

        return content[start_idx:]

    def _get_entities_set(self, response):
        with self.assertNoException():
            entities_page = response.context['entities']

        return set(entities_page.object_list)

    def _build_hf(self, *args):
        hf = HeaderFilter.create(pk='test-hf_orga', name='Orga view', model=Organisation)
        items = [HeaderFilterItem.build_4_field(model=Organisation, name='name')]
        items.extend(args)
        hf.set_items(items)

    def test_content01(self):
        self.login()
        user = self.user

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        create_contact = partial(Contact.objects.create, user=user)
        spike = create_contact(first_name='Spike', last_name='Spiegel')
        faye  = create_contact(first_name='Faye',  last_name='Valentine')

        #Relation
        rtype = RelationType.create(('test-subject_piloted', 'is piloted by'),
                                    ('test-object_piloted',  'pilots'),
                                   )[0]
        Relation.objects.create(user=user, subject_entity=swordfish,
                                type=rtype, object_entity=spike,
                               )

        #Property
        create_ptype = CremePropertyType.create
        ptype1 = create_ptype(str_pk='test-prop_red',  text='is red')
        ptype2 = create_ptype(str_pk='test-prop_fast', text='is fast')
        CremeProperty.objects.create(type=ptype1, creme_entity=swordfish)

        #CustomField
        cfield = CustomField.objects.create(name='size (m)',
                                            content_type=self.ctype,
                                            field_type=CustomField.INT,
                                           )
        cfield_value = 42
        cfield.get_value_class()(custom_field=cfield, entity=bebop).set_value_n_save(cfield_value)

        self._build_hf(HeaderFilterItem.build_4_relation(rtype=rtype),
                       HeaderFilterItem.build_4_functionfield(func_field=Organisation.function_fields.get('get_pretty_properties')),
                       HeaderFilterItem.build_4_customfield(cfield),
                      )

        response = self.assertGET200(self.url)

        with self.assertNoException():
            orgas_page = response.context['entities']

        orgas_set = set(orgas_page.object_list)
        self.assertIn(bebop,     orgas_set)
        self.assertIn(swordfish, orgas_set)

        content = self._get_lv_content(response)
        bebop_idx = self.assertFound(bebop.name, content)
        swordfish_idx = self.assertFound(swordfish.name, content)
        self.assertGreater(swordfish_idx, bebop_idx) #order

        content = safe_unicode(content)

        self.assertIn(rtype.predicate, content)
        self.assertIn(unicode(spike), content)
        self.assertNotIn(faye.last_name, content)

        self.assertIn(u'<ul><li>%s</li></ul>' % ptype1.text, content)
        self.assertNotIn(ptype2.text, content)

        self.assertIn(cfield.name, content)
        self.assertIn(str(cfield_value), content)

    def test_order01(self): #TODO: test with ajax ?
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        self._build_hf()

        def post(first, second, sort_order=None, sort_field='name'):
            data = {'sort_field': sort_field}
            if sort_order:
                data['sort_order'] = sort_order

            response = self.assertPOST200(self.url, data=data)
            content = self._get_lv_content(response)
            first_idx = self.assertFound(first.name, content)
            second_idx = self.assertFound(second.name, content)
            self.assertLess(first_idx, second_idx)

        post(bebop, swordfish)
        post(swordfish, bebop, '-')
        post(bebop, swordfish, '*') #invalid value
        post(bebop, swordfish, sort_field='unknown') #invalid value

    def test_efilter01(self):
        self.login()
        user = self.user

        create_orga = partial(Organisation.objects.create, user=user)
        bebop   = create_orga(name='Bebop')
        redtail = create_orga(name='Redtail')
        dragons = create_orga(name='Red Dragons')

        self._build_hf()

        efilter = EntityFilter.create('test-filter01', 'Red', Organisation,
                                      user=user, is_custom=False,
                                     )
        efilter.set_conditions([EntityFilterCondition.build_4_field(
                                       model=Organisation,
                                       operator=EntityFilterCondition.ISTARTSWITH,
                                       name='name', values=['Red']
                                      ),
                               ]
                              )

        response = self.assertPOST200(self.url, data={'filter': efilter.id})

        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name, content)
        self.assertIn(redtail.name,  content)
        self.assertIn(dragons.name,  content)

    def test_search_regularfields01(self):
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish',   phone='668899')
        redtail   = create_orga(name='Redtail',     phone='889977')
        dragons   = create_orga(name='Red Dragons', phone='123')

        self._build_hf(HeaderFilterItem.build_4_field(model=Organisation, name='phone'))

        url = self.url
        data = {'_search': 1}
        response = self.assertPOST200(url, data=dict(data, name='Red', phone=''))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,     content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertIn(dragons.name,      content)

        response = self.assertPOST200(url, data=dict(data, name='', phone='88'))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertIn(redtail.name,    content)
        self.assertNotIn(dragons.name, content)

        response = self.assertPOST200(url, data=dict(data, name='Red', phone='88'))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,     content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

        response = self.assertPOST200(url, data={'_search': 0, 'name': '', 'phone': ''})
        content = self._get_lv_content(response)
        self.assertIn(bebop.name,     content)
        self.assertIn(swordfish.name, content)
        self.assertIn(redtail.name,   content)
        self.assertIn(dragons.name,   content)

    def test_search_regularfields02(self):
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop = create_orga(name='Bebop inc', subject_to_vat=False)
        nerv  = create_orga(name='NERV',      subject_to_vat=True)
        seele = create_orga(name='Seele',     subject_to_vat=True)

        self._build_hf(HeaderFilterItem.build_4_field(model=Organisation, name='subject_to_vat'))

        url = self.url
        data = {'_search': 1}
        response = self.assertPOST200(url, data=dict(data, subject_to_vat='1'))
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop, orgas_set)
        self.assertIn(nerv,     orgas_set)
        self.assertIn(seele,    orgas_set)

        response = self.assertPOST200(url, data=dict(data, subject_to_vat='0'))
        orgas_set = self._get_entities_set(response)
        self.assertIn(bebop,    orgas_set)
        self.assertNotIn(nerv,  orgas_set)
        self.assertNotIn(seele, orgas_set)

    def test_search_datefields01(self):
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop',     creation_date=date(year=2075, month=3, day=26))
        swordfish = create_orga(name='Swordfish', creation_date=date(year=2074, month=6, day=5))
        redtail   = create_orga(name='Redtail',   creation_date=date(year=2076, month=7, day=25))
        dragons   = create_orga(name='Red Dragons')

        self._build_hf(HeaderFilterItem.build_4_field(model=Organisation, name='creation_date'))

        url = self.url
        data = {'_search': 1}
        response = self.assertPOST200(url, data=dict(data, creation_date=['1-1-2075']))
        content = self._get_lv_content(response)
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

        response = self.assertPOST200(url, data=dict(data, creation_date=['', '1-1-2075']))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        response = self.assertPOST200(url, data=dict(data, creation_date=['1-1-2074', '31-12-2074']))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

    def test_search_relations01(self):
        self.login()
        user = self.user

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_contact = partial(Contact.objects.create, user=user)
        spike = create_contact(first_name='Spike', last_name='Spiegel')
        faye  = create_contact(first_name='Faye',  last_name='Spiegel')
        jet   = create_contact(first_name='Jet',   last_name='Black')

        rtype = RelationType.create(('test-subject_piloted', 'is piloted by'),
                                    ('test-object_piloted',  'pilots'),
                                   )[0]
        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        create_rel(subject_entity=swordfish, object_entity=spike)
        create_rel(subject_entity=redtail,   object_entity=faye)
        create_rel(subject_entity=bebop,     object_entity=jet)

        self._build_hf(HeaderFilterItem.build_4_relation(rtype=rtype))

        url = self.url
        data = {'_search': 1, 'name': '', rtype.pk: 'Spiege'}
        response = self.assertPOST200(url, data=data)
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertIn(redtail.name,    content)
        self.assertNotIn(dragons.name, content)

        response = self.assertPOST200(url, data=dict(data, name='Swo'))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

    def test_search_customfield01(self):
        "INT"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        cfield = CustomField.objects.create(name='size (m)',
                                            content_type=self.ctype,
                                            field_type=CustomField.INT,
                                           )
        klass = cfield.get_value_class()

        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,     42)
        set_cfvalue(swordfish, 12)
        set_cfvalue(redtail,   4)

        self._build_hf(HeaderFilterItem.build_4_customfield(cfield))

        response = self.assertPOST200(self.url, data={'_search': 1, 'name': '', cfield.pk: '4'})
        content = self._get_lv_content(response)
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

    def test_search_customfield02(self):
        "INT & STR"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_cfield = partial(CustomField.objects.create, content_type=self.ctype)
        cfield1 = create_cfield(name='size (m)',   field_type=CustomField.INT)
        cfield2 = create_cfield(name='color code', field_type=CustomField.STR)

        def set_cfvalue(cfield, entity, value):
            cfield.get_value_class()(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield1, bebop,     42)
        set_cfvalue(cfield1, swordfish, 12)
        set_cfvalue(cfield1, redtail,   4)

        set_cfvalue(cfield2, swordfish, '#ff0000')
        set_cfvalue(cfield2, redtail,   '#050508')

        build_item = HeaderFilterItem.build_4_customfield
        self._build_hf(build_item(cfield1), build_item(cfield2))

        response = self.assertPOST200(self.url, data={'_search': 1,
                                                      'name': '',
                                                      cfield1.pk: '4',
                                                      cfield2.pk: '#05',
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(redtail,      orgas_set)
        self.assertNotIn(dragons,   orgas_set)

    def test_search_customfield03(self):
        "INT & INT"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_cfield = partial(CustomField.objects.create, content_type=self.ctype,
                                field_type=CustomField.INT,
                               )
        cfield1 = create_cfield(name='size (m)')
        cfield2 = create_cfield(name='weight')

        def set_cfvalue(cfield, entity, value):
            cfield.get_value_class()(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield1, bebop,     42)
        set_cfvalue(cfield1, swordfish, 12)
        set_cfvalue(cfield1, redtail,   4)

        set_cfvalue(cfield2, swordfish, 1000)
        set_cfvalue(cfield2, redtail,   2000)

        build_item = HeaderFilterItem.build_4_customfield
        self._build_hf(build_item(cfield1), build_item(cfield2))

        response = self.assertPOST200(self.url, data={'_search': 1,
                                                      'name': '',
                                                      cfield1.pk: '4',
                                                      cfield2.pk: '2000',
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(redtail,      orgas_set)
        self.assertNotIn(dragons,   orgas_set)

    def test_search_customfield04(self):
        "ENUM"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        cfield = CustomField.objects.create(name='Type',
                                            content_type=self.ctype,
                                            field_type=CustomField.ENUM,
                                           )

        create_evalue = CustomFieldEnumValue.objects.create
        type1 = create_evalue(custom_field=cfield, value='Light')
        type2 = create_evalue(custom_field=cfield, value='Heavy')

        klass = cfield.get_value_class()
        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,     type2.id)
        set_cfvalue(swordfish, type1.id)
        set_cfvalue(redtail,   type1.id)

        self._build_hf(HeaderFilterItem.build_4_customfield(cfield))

        response = self.assertPOST200(self.url, data={'_search': 1,
                                                      'name': '',
                                                      cfield.pk: type1.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,   orgas_set)
        self.assertIn(swordfish,  orgas_set)
        self.assertIn(redtail,    orgas_set)
        self.assertNotIn(dragons, orgas_set)

    def test_search_customfield05(self):
        "MULTI_ENUM"
        self.login()
        user = self.user

        create_orga = partial(Organisation.objects.create, user=user)
        bebop    = create_orga(name='Bebop')
        dragons  = create_orga(name='Red Dragons')
        eva01    = create_orga(name='Eva01')
        valkyrie = create_orga(name='Valkyrie')

        cfield = CustomField.objects.create(name='Capabilities',
                                            content_type=self.ctype,
                                            field_type=CustomField.MULTI_ENUM,
                                           )

        create_evalue = CustomFieldEnumValue.objects.create
        can_walk = create_evalue(custom_field=cfield, value='Walk')
        can_fly = create_evalue(custom_field=cfield, value='Fly')

        klass = cfield.get_value_class()
        def set_cfvalue(entity, value):
            klass(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(bebop,     [can_fly.id])
        set_cfvalue(eva01,     [can_walk.id])
        set_cfvalue(valkyrie,  [can_fly.id, can_walk.id])

        self._build_hf(HeaderFilterItem.build_4_customfield(cfield))

        response = self.assertPOST200(self.url, data={'_search': 1,
                                                      'name':    '',
                                                      cfield.pk: can_walk.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,   orgas_set)
        self.assertNotIn(dragons, orgas_set)
        self.assertIn(eva01,      orgas_set)
        self.assertIn(valkyrie,   orgas_set)

    def test_search_customfield06(self):
        "2 x ENUM"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        create_cfield = partial(CustomField.objects.create,
                                content_type=self.ctype, field_type=CustomField.ENUM,
                               )
        cfield_type  = create_cfield(name='Type')
        cfield_color = create_cfield(name='Color')

        create_evalue = CustomFieldEnumValue.objects.create
        type1 = create_evalue(custom_field=cfield_type, value='Light')
        type2 = create_evalue(custom_field=cfield_type, value='Heavy')

        color1 = create_evalue(custom_field=cfield_color, value='Red')
        color2 = create_evalue(custom_field=cfield_color, value='Grey')

        def set_cfvalue(cfield, entity, value):
            cfield.get_value_class()(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield_type,  bebop,     type2.id)
        set_cfvalue(cfield_color, bebop,     color2.id)

        set_cfvalue(cfield_type,  swordfish, type1.id)
        set_cfvalue(cfield_color, swordfish, color1.id)

        set_cfvalue(cfield_type,  redtail,   type1.id)
        set_cfvalue(cfield_color, redtail,   color2.id)

        build_item = HeaderFilterItem.build_4_customfield
        self._build_hf(build_item(cfield_type), build_item(cfield_color))

        response = self.assertPOST200(self.url, data={'_search':       1,
                                                      'name':          '',
                                                      cfield_type.pk:  type1.id,
                                                      cfield_color.pk: color2.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(redtail,      orgas_set)
        self.assertNotIn(dragons,   orgas_set)

    def test_search_customfield07(self):
        "2 x MULTI_ENUM"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        eva02     = create_orga(name='Eva02')
        valkyrie  = create_orga(name='Valkyrie')

        create_cfield = partial(CustomField.objects.create,
                                content_type=self.ctype, field_type=CustomField.MULTI_ENUM,
                               )
        cfield_cap   = create_cfield(name='Capabilities')
        cfield_color = create_cfield(name='Color')

        create_evalue = CustomFieldEnumValue.objects.create
        can_fly  = create_evalue(custom_field=cfield_cap, value='Walk')
        can_walk = create_evalue(custom_field=cfield_cap, value='Fly')

        red    = create_evalue(custom_field=cfield_color, value='Red')
        grey   = create_evalue(custom_field=cfield_color, value='Grey')
        orange = create_evalue(custom_field=cfield_color, value='Orange')

        def set_cfvalue(cfield, entity, value):
            cfield.get_value_class()(custom_field=cfield, entity=entity).set_value_n_save(value)

        set_cfvalue(cfield_cap,   bebop,     [can_fly.id])
        set_cfvalue(cfield_color, bebop,     [grey.id])

        set_cfvalue(cfield_cap,   swordfish, [can_fly.id])
        set_cfvalue(cfield_color, swordfish, [red.id])

        set_cfvalue(cfield_cap,   eva02,     [can_walk.id])
        set_cfvalue(cfield_color, eva02,     [red.id, orange.id])

        set_cfvalue(cfield_cap,   valkyrie,  [can_fly.id, can_walk.id])

        build_item = HeaderFilterItem.build_4_customfield
        self._build_hf(build_item(cfield_cap), build_item(cfield_color))

        response = self.assertPOST200(self.url, data={'_search':       1,
                                                      'name':          '',
                                                      cfield_cap.pk:   can_walk.id,
                                                      cfield_color.pk: red.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(eva02,        orgas_set)
        self.assertNotIn(valkyrie,  orgas_set)

    def test_search_functionfield01(self):
        "Can not search on this FunctionField"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        ptype = CremePropertyType.create(str_pk='test-prop_red',  text='is red')
        CremeProperty.objects.create(type=ptype, creme_entity=swordfish)

        func_field = Organisation.function_fields.get('get_pretty_properties')
        self._build_hf(HeaderFilterItem.build_4_functionfield(func_field))

        response = self.assertPOST200(self.url, data={'_search':       1,
                                                      'name':          '',
                                                      func_field.name: 'red',
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertIn(bebop,     orgas_set)
        self.assertIn(swordfish, orgas_set)

    def test_search_functionfield02(self):
        "billing_LineTypeField"
        self.login()
        user = self.user

        invoice = Invoice.objects.create(user=user, name='Invoice',
                                         expiration_date=date(year=2012, month=12, day=15),
                                         status=InvoiceStatus.objects.all()[0],
                                        )

        create_pline = partial(ProductLine.objects.create, user=user, related_document=invoice)
        pline1 = create_pline(on_the_fly_item='Fly1')
        pline2 = create_pline(on_the_fly_item='Fly2')

        create_sline = partial(ServiceLine.objects.create, user=user, related_document=invoice)
        sline1 = create_sline(on_the_fly_item='Fly3')
        sline2 = create_sline(on_the_fly_item='Fly4')

        func_field = Line.function_fields.get('get_verbose_type')
        self._build_hf(HeaderFilterItem.build_4_functionfield(func_field))

        url = Line.get_lv_absolute_url()
        response = self.assertGET200(url)
        ids = set(l.id for l in self._get_entities_set(response))
        self.assertIn(pline1.id, ids)
        self.assertIn(pline2.id, ids)
        self.assertIn(sline1.id, ids)
        self.assertIn(sline2.id, ids)

        def post(line_type):
            return self.assertPOST200(url, data={'_search':       1,
                                                 'name':          '',
                                                 func_field.name: line_type,
                                                }
                                     )

        response = post(PRODUCT_LINE_TYPE)
        ids = set(l.id for l in self._get_entities_set(response))
        self.assertIn(pline1.id,    ids)
        self.assertIn(pline2.id,    ids)
        self.assertNotIn(sline1.id, ids)
        self.assertNotIn(sline2.id, ids)

        response = post(SERVICE_LINE_TYPE)
        ids = set(l.id for l in self._get_entities_set(response))
        self.assertNotIn(pline1.id, ids)
        self.assertNotIn(pline2.id, ids)
        self.assertIn(sline1.id,    ids)
        self.assertIn(sline2.id,    ids)
