# -*- coding: utf-8 -*-

try:
    from datetime import date, timedelta
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.utils.timezone import now

    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
        EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.models import (EntityFilter, EntityFilterCondition,
            HeaderFilter, RelationType, Relation, CremePropertyType, CremeProperty,
            CustomField, CustomFieldEnumValue)
    from creme.creme_core.utils import safe_unicode
    from creme.creme_core.tests.base import skipIfNotInstalled
    from .base import ViewsTestCase

    from creme.persons.models import Organisation, Contact, Civility

    from creme.activities.models import Activity, ActivityType
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ListViewTestCase', )


class ListViewTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        ViewsTestCase.setUpClass()

        cls.populate('creme_core', 'creme_config', 'billing')
        cls.url = Organisation.get_lv_absolute_url()
        cls.ctype = ContentType.objects.get_for_model(Organisation)
        Civility.objects.all().delete()

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
        cells = [EntityCellRegularField.build(model=Organisation, name='name')]
        cells.extend(args)
        return HeaderFilter.create(pk='test-hf_orga', name='Orga view',
                                   model=Organisation, cells_desc=cells,
                                  )

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

        hf = self._build_hf(EntityCellRelation(rtype=rtype),
                            #EntityCellFunctionField(func_field=Organisation.function_fields.get('get_pretty_properties')),
                            EntityCellFunctionField.build(Organisation, 'get_pretty_properties'),
                            EntityCellCustomField(cfield),
                           )

        #response = self.assertGET200(self.url)
        response = self.assertPOST200(self.url, data={'hfilter': hf.id})

        with self.assertNoException():
            ctxt = response.context
            hfilters = ctxt['header_filters']
            orgas_page = ctxt['entities']

        with self.assertNoException():
            sel_hf = hfilters.selected

        self.assertIsInstance(sel_hf, HeaderFilter)
        self.assertEqual(sel_hf.id, hf.id)

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

        def post(first, second, sort_order='', sort_field='name'):
            response = self.assertPOST200(self.url,
                                          data={'sort_field': sort_field,
                                                'sort_order': sort_order,
                                               }
                                         )
            content = self._get_lv_content(response)
            first_idx = self.assertFound(first.name, content)
            second_idx = self.assertFound(second.name, content)
            self.assertLess(first_idx, second_idx)

        post(bebop, swordfish)
        post(swordfish, bebop, '-')
        post(bebop, swordfish, '*') #invalid value
        post(bebop, swordfish, sort_field='unknown') #invalid value

    def test_order02_prelude(self):
        "Sort by ForeignKey"
        #NB: the DatabaseError cannot be rollbacked here in the test context,
        #    so we cannot do this test in test_order02, because it cause an error.
        try:
            bool(Contact.objects.order_by('image'))
        except:
            pass
        else:
            self.fail('ORM bug has been fixed ?! => reactivate FK on CremeEntity sorting')

    def test_order02(self):
        "Sort by ForeignKey"
        self.login()

        create_civ = Civility.objects.create
        mister = create_civ(title='Mister')
        miss   = create_civ(title='Miss')
        self.assertLess(mister.id, miss.id)

        create_contact = partial(Contact.objects.create, user=self.user)
        spike = create_contact(first_name='Spike',  last_name='Spiegel',   civility=mister)
        faye  = create_contact(first_name='Faye',   last_name='Valentine', civility=miss)
        ed    = create_contact(first_name='Edward', last_name='Wong')

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=Contact)

        build_cell = partial(EntityCellRegularField.build, model=Contact)
        cell_image    = build_cell(name='image')
        cell_img_name = build_cell(name='image__name')
        cell_civ      = build_cell(name='civility')
        cell_civ_name = build_cell(name='civility__title')

        self.assertTrue(cell_civ.sortable)
        #self.assertFalse(cell_image.sortable)
        self.assertTrue(cell_image.sortable)
        self.assertTrue(cell_img_name.sortable)
        self.assertTrue(cell_civ_name.sortable)

        hf.cells = [build_cell(name='last_name'),
                    cell_image, cell_img_name, cell_civ, cell_civ_name,
                   ]
        hf.save()

        url = Contact.get_lv_absolute_url()

        #---------------------------------------------------------------------
        response = self.assertPOST200(url, data={'hfilter': hf.id})

        with self.assertNoException():
            selected_hf = response.context['header_filters'].selected

        self.assertEqual(hf, selected_hf)

        #---------------------------------------------------------------------
        #FK on CremeEntity we just check that it does not crash
        self.assertPOST200(url, data={'sort_field': 'image'})

        #---------------------------------------------------------------------

        def post(field_name, reverse, *contacts):
            response = self.assertPOST200(url,
                                          data={'sort_field': field_name,
                                                'sort_order': '-' if reverse else '',
                                               }
                                         )
            content = self._get_lv_content(response)
            indices = [self.assertFound(c.last_name, content)
                        for c in contacts
                      ]
            self.assertEqual(indices, sorted(indices))

            return content

        #NB: it seems that NULL are not ordered in the same way on different DB engines
        #post('civility', False, ed, spike, faye) #Beware: sorting is done by id
        content = post('civility', False, spike, faye) #Beware: sorting is done by id
        self.assertFound(ed.last_name, content)

        #post('civility', True, faye, spike, ed)
        post('civility', True, faye, spike)
        #post('civility__title', False, ed, faye, spike)
        post('civility__title', False, faye, spike)
        #post('civility__title', True, spike, faye, ed)
        post('civility__title', True, spike, faye)

    @skipIfNotInstalled('creme.emails')
    def test_order03(self):
        "Unsortable fields: ManyToMany, FunctionFields"
        from creme.emails.models import EmailCampaign
        self.login()

        #bug on ORM with M2M happens only if there is at least one entity
        EmailCampaign.objects.create(user=self.user, name='Camp01')

        fname = 'mailing_lists'
        func_field_name = 'get_pretty_properties'
        HeaderFilter.create(pk='test-hf_camp', name='Campaign view', model=EmailCampaign,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                        (EntityCellRegularField, {'name': fname}),
                                        (EntityCellFunctionField, {'func_field_name': func_field_name}),
                                       ]
                           )

        url = EmailCampaign.get_lv_absolute_url()
        #we just check that it does not crash
        self.assertPOST200(url, data={'sort_field': fname})
        self.assertPOST200(url, data={'sort_field': func_field_name})

    def test_order04(self):
        "Ordering = '-fieldname'"
        self.assertTrue('-start', Activity._meta.ordering[0])
        self.login()

        act_type = ActivityType.objects.create(pk='creme_core-lvtest1', name='Karate session',
                                               default_day_duration=1, default_hour_duration="00:15:00",
                                               is_custom=True,
                                              )

        create_act = partial(Activity.objects.create, user=self.user, type=act_type)
        act1 = create_act(title='Act#1', start=now())
        act2 = create_act(title='Act#2', start=act1.start + timedelta(hours=1))

        HeaderFilter.create(pk='test-hf_act', name='Activity view',
                            model=Activity,
                            cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                                        (EntityCellRegularField, {'name': 'start'}),
                                       ],
                           )

        response = self.assertPOST200(Activity.get_lv_absolute_url())
        content = self._get_lv_content(response)
        first_idx  = self.assertFound(act2.title, content)
        second_idx = self.assertFound(act1.title, content)
        self.assertLess(first_idx, second_idx)

        with self.assertNoException():
            lvs = response.context['list_view_state']
            sort_field = lvs.sort_field
            sort_order = lvs.sort_order

        self.assertEqual('start', sort_field)
        self.assertEqual('-',     sort_order)

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

        self._build_hf(EntityCellRegularField.build(model=Organisation, name='phone'))

        url = self.url
        #data = {'_search': 1}

        def build_data(name='', phone='', search=1):
            return {'_search': 1,
                    'regular_field-name': name,
                    'regular_field-phone': phone,
                   }

        #response = self.assertPOST200(url, data=dict(data, name='Red', phone=''))
        response = self.assertPOST200(url, data=build_data('Red'))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,     content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertIn(dragons.name,      content)

        #response = self.assertPOST200(url, data=dict(data, name='', phone='88'))
        response = self.assertPOST200(url, data=build_data('', '88'))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertIn(redtail.name,    content)
        self.assertNotIn(dragons.name, content)

        #response = self.assertPOST200(url, data=dict(data, name='Red', phone='88'))
        response = self.assertPOST200(url, data=build_data('Red', '88'))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,     content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

        #response = self.assertPOST200(url, data={'_search': 0, 'name': '', 'phone': ''})
        response = self.assertPOST200(url, data=build_data(search=0))
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

        hf = self._build_hf(EntityCellRegularField.build(model=Organisation, name='subject_to_vat'))
        url = self.url
        data = {'hfilter': hf.id, '_search': 1}
        #response = self.assertPOST200(url, data=dict(data, subject_to_vat='1'))
        response = self.assertPOST200(url, data=dict(data, **{'regular_field-subject_to_vat': '1'}))
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop, orgas_set)
        self.assertIn(nerv,     orgas_set)
        self.assertIn(seele,    orgas_set)

        #response = self.assertPOST200(url, data=dict(data, subject_to_vat='0'))
        response = self.assertPOST200(url, data=dict(data, **{'regular_field-subject_to_vat': '0'}))
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

        hf = self._build_hf(EntityCellRegularField.build(model=Organisation, name='creation_date'))

        url = self.url
        #data = {'_search': 1}

        build_data = lambda cdate: {'hfilter': hf.id, '_search': 1, 'regular_field-creation_date': cdate}

        #response = self.assertPOST200(url, data=dict(data, creation_date=['1-1-2075']))
        response = self.assertPOST200(url, data=build_data(['1-1-2075']))
        content = self._get_lv_content(response)
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

        #response = self.assertPOST200(url, data=dict(data, creation_date=['', '1-1-2075']))
        response = self.assertPOST200(url, data=build_data(['', '1-1-2075']))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        #response = self.assertPOST200(url, data=dict(data, creation_date=['1-1-2074', '31-12-2074']))
        response = self.assertPOST200(url, data=build_data(['1-1-2074', '31-12-2074']))
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

    def test_search_datetimefields01(self):
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')

        def set_created(orga, dt):
            Organisation.objects.filter(pk=orga.id).update(created=dt)

        create_dt = partial(self.create_datetime, utc=True)
        set_created(bebop,     create_dt(year=2075, month=3, day=26))
        set_created(swordfish, create_dt(year=2074, month=6, day=5))
        set_created(redtail,   create_dt(year=2076, month=7, day=25))

        hf = self._build_hf(EntityCellRegularField.build(model=Organisation, name='created'))

        url = self.url
        #data = {'_search': 1}
        def post(created):
            response = self.assertPOST200(url, data={'hfilter': hf.id,
                                                     '_search': 1,
                                                     'regular_field-created': created,
                                                    }
                                         )
            return  self._get_lv_content(response)

        #response = self.assertPOST200(url, data=dict(data, created=['1-1-2075']))
        #content = self._get_lv_content(response)
        content = post(['1-1-2075'])
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)

        #response = self.assertPOST200(url, data=dict(data, created=['', '1-1-2075']))
        #content = self._get_lv_content(response)
        content = post(['', '1-1-2075'])
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)

        #response = self.assertPOST200(url, data=dict(data, created=['1-1-2074', '31-12-2074']))
        #content = self._get_lv_content(response)
        content = post(['1-1-2074', '31-12-2074'])
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)

    def test_search_fk(self):
        self.login()

        create_civ = Civility.objects.create
        mister = create_civ(title='Mister')
        miss   = create_civ(title='Miss')
        self.assertLess(mister.id, miss.id)

        img_faye = self.create_image(ident=1)
        img_ed   = self.create_image(ident=2)

        create_contact = partial(Contact.objects.create, user=self.user)
        spike = create_contact(first_name='Spike',  last_name='Spiegel',   civility=mister)
        faye  = create_contact(first_name='Faye',   last_name='Valentine', civility=miss, image=img_faye)
        ed    = create_contact(first_name='Edward', last_name='Wong',                     image=img_ed)

        hf = HeaderFilter.create(pk='test-hf_contact', name='Order02 view', model=Contact)

        build_cell = partial(EntityCellRegularField.build, model=Contact)
        cell_image    = build_cell(name='image')
        cell_img_name = build_cell(name='image__name')
        cell_civ      = build_cell(name='civility')
        cell_civ_name = build_cell(name='civility__title')

        self.assertTrue(cell_civ.has_a_filter)
        self.assertTrue(cell_civ_name.has_a_filter)
        self.assertTrue(cell_img_name.has_a_filter)
        self.assertTrue(cell_image.has_a_filter)
        self.assertEqual('image__name__icontains', cell_img_name.filter_string)
        self.assertEqual('image__header_filter_search_field__icontains',
                         cell_image.filter_string
                        )

        hf.cells = [build_cell(name='last_name'),
                    cell_image, cell_img_name, cell_civ, cell_civ_name,
                   ]
        hf.save()

        url = Contact.get_lv_absolute_url()

        #---------------------------------------------------------------------
        response = self.assertPOST200(url, data={'hfilter': hf.id})

        with self.assertNoException():
            selected_hf = response.context['header_filters'].selected

        self.assertEqual(hf, selected_hf)

        #---------------------------------------------------------------------
        data = {'_search': 1}
        #response = self.assertPOST200(url, data=dict(data, civility=mister.id))
        response = self.assertPOST200(url, data=dict(data, **{'regular_field-civility': mister.id}))
        content = self._get_lv_content(response)
        self.assertIn(spike.last_name,   content)
        self.assertNotIn(faye.last_name, content)
        self.assertNotIn(ed.last_name,   content)

        #---------------------------------------------------------------------
        #response = self.assertPOST200(url, data=dict(data, civility__title='iss'))
        response = self.assertPOST200(url, data=dict(data, **{'regular_field-civility__title': 'iss'}))
        content = self._get_lv_content(response)
        self.assertNotIn(spike.last_name, content)
        self.assertIn(faye.last_name,     content)
        self.assertNotIn(ed.last_name,    content)

        #---------------------------------------------------------------------
        #response = self.assertPOST200(url, data=dict(data, image__name=img_ed.name))*
        response = self.assertPOST200(url, data=dict(data, **{'regular_field-image__name': img_ed.name}))
        content = self._get_lv_content(response)
        self.assertNotIn(spike.last_name, content)
        self.assertNotIn(faye.last_name,  content)
        self.assertIn(ed.last_name,       content)

        #---------------------------------------------------------------------
        #response = self.assertPOST200(url, data=dict(data, image=img_ed.name))
        response = self.assertPOST200(url, data=dict(data, **{'regular_field-image': img_ed.name}))
        content = self._get_lv_content(response)
        self.assertNotIn(spike.last_name, content)
        self.assertNotIn(faye.last_name,  content)
        self.assertIn(ed.last_name,       content)

    @skipIfNotInstalled('creme.emails')
    def test_search_m2mfields01(self):
        from creme.emails.models import EmailCampaign

        self.login()
        hf = HeaderFilter.create(pk='test-hf_camp', name='Campaign view',
                                 model=EmailCampaign,
                                )
        build_cell = partial(EntityCellRegularField.build, model=EmailCampaign)

        cell_m2m = build_cell(name='mailing_lists')
        self.assertFalse(cell_m2m.has_a_filter)
        self.assertEqual('', cell_m2m.filter_string)

        hf.cells = [build_cell(name='name'), cell_m2m]
        hf.save()

        #we just check that it does not crash
        self.assertPOST200(EmailCampaign.get_lv_absolute_url(),
                           data={'_search':       1,
                                 #'mailing_lists': 'MLname',
                                 'regular_field-mailing_lists': 'MLname',
                                }
                          )

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

        hf = self._build_hf(EntityCellRelation(rtype=rtype))

        url = self.url
        #data = {'_search': 1, 'name': '', rtype.pk: 'Spiege'}
        data = {'hfilter': hf.id, '_search': 1, 'name': '', 'relation-%s' % rtype.pk: 'Spiege'}
        response = self.assertPOST200(url, data=data)
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertIn(redtail.name,    content)
        self.assertNotIn(dragons.name, content)

        #response = self.assertPOST200(url, data=dict(data, name='Swo'))
        #content = self._get_lv_content(response)
        data['regular_field-name'] = 'Swo'
        content = self._get_lv_content(self.assertPOST200(url, data=data))
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

        hf = self._build_hf(EntityCellCustomField(cfield))

        #response = self.assertPOST200(self.url, data={'_search': 1, 'name': '', cfield.pk: '4'})
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield.pk: '4',
                                                     }
                                     )
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

        hf = self._build_hf(EntityCellCustomField(cfield1), EntityCellCustomField(cfield2))

        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      #'name': '',
                                                      #cfield1.pk: '4',
                                                      #cfield2.pk: '#05',
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield1.pk: '4',
                                                      'custom_field-%s' % cfield2.pk: '#05',
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

        hf = self._build_hf(EntityCellCustomField(cfield1),
                            EntityCellCustomField(cfield2),
                           )
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      #'name': '',
                                                      #cfield1.pk: '4',
                                                      #cfield2.pk: '2000',
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield1.pk: '4',
                                                      'custom_field-%s' % cfield2.pk: '2000',
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

        hf = self._build_hf(EntityCellCustomField(cfield))
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      #'name': '',
                                                      #cfield.pk: type1.id,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield.pk: type1.id,
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

        hf = self._build_hf(EntityCellCustomField(cfield))
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      #'name':    '',
                                                      #cfield.pk: can_walk.id,
                                                      'regular_field-name':    '',
                                                      'custom_field-%s' % cfield.pk: can_walk.id,
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

        hf = self._build_hf(EntityCellCustomField(cfield_type),
                            EntityCellCustomField(cfield_color),
                           )
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search':       1,
                                                      #'name':          '',
                                                      #cfield_type.pk:  type1.id,
                                                      #cfield_color.pk: color2.id,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield_type.pk:  type1.id,
                                                      'custom_field-%s' % cfield_color.pk: color2.id,
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

        hf = self._build_hf(EntityCellCustomField(cfield_cap),
                            EntityCellCustomField(cfield_color),
                           )
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search':       1,
                                                      #'name':          '',
                                                      #cfield_cap.pk:   can_walk.id,
                                                      #cfield_color.pk: red.id,
                                                      'regular_field-name': '',
                                                      'custom_field-%s' % cfield_cap.pk:   can_walk.id,
                                                      'custom_field-%s' % cfield_color.pk: red.id,
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertNotIn(bebop,     orgas_set)
        self.assertNotIn(swordfish, orgas_set)
        self.assertIn(eva02,        orgas_set)
        self.assertNotIn(valkyrie,  orgas_set)

    def test_search_customfield08(self):
        "DATETIME"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')
        redtail   = create_orga(name='Redtail')
        dragons   = create_orga(name='Red Dragons')

        cfield = CustomField.objects.create(name='First flight',
                                            content_type=self.ctype,
                                            field_type=CustomField.DATETIME,
                                           )
        create_cf_value = partial(cfield.get_value_class().objects.create, custom_field=cfield)
        create_dt = partial(self.create_datetime, utc=True)
        create_cf_value(entity=bebop,     value=create_dt(year=2075, month=3, day=26))
        create_cf_value(entity=swordfish, value=create_dt(year=2074, month=6, day=5))
        create_cf_value(entity=redtail,   value=create_dt(year=2076, month=7, day=25))

        hf = self._build_hf(EntityCellCustomField(cfield))

        def post(dates):
            #response = self.assertPOST200(self.url, data={'_search': 1, cfield.pk: dates})
            response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                          '_search': 1,
                                                          'custom_field-%s' % cfield.pk: dates,
                                                         }
                                         )
            return self._get_lv_content(response)

        content = post(['2075-1-1'])
        self.assertIn(bebop.name,        content)
        self.assertNotIn(swordfish.name, content)
        self.assertIn(redtail.name,      content)
        self.assertNotIn(dragons.name,   content)

        content = post(['', '1-1-2075'])
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

        content = post(['1-1-2074', '31-12-2074'])
        self.assertNotIn(bebop.name,   content)
        self.assertIn(swordfish.name,  content)
        self.assertNotIn(redtail.name, content)
        self.assertNotIn(dragons.name, content)

    def test_search_customfield09(self):
        "2 x DATETIME"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop      = create_orga(name='Bebop')
        swordfish  = create_orga(name='Swordfish')
        redtail    = create_orga(name='Redtail')
        hammerhead = create_orga(name='HammerHead')
        dragons    = create_orga(name='Red Dragons')

        create_cfield = partial(CustomField.objects.create, content_type=self.ctype,
                                field_type=CustomField.DATETIME,
                               )
        cfield_flight = create_cfield(name='First flight')
        cfield_blood  = create_cfield(name='First blood')

        create_cf_value = partial(cfield_flight.get_value_class().objects.create)
        create_dt = partial(self.create_datetime, utc=True)
        create_cf_value(entity=bebop,      custom_field=cfield_flight, value=create_dt(year=2075, month=3, day=26))
        create_cf_value(entity=swordfish,  custom_field=cfield_flight, value=create_dt(year=2074, month=6, day=5))
        create_cf_value(entity=redtail,    custom_field=cfield_flight, value=create_dt(year=2076, month=7, day=25))
        create_cf_value(entity=hammerhead, custom_field=cfield_flight, value=create_dt(year=2074, month=7, day=6))

        create_cf_value(entity=swordfish,  custom_field=cfield_blood, value=create_dt(year=2074, month=6, day=8))
        create_cf_value(entity=hammerhead, custom_field=cfield_blood, value=create_dt(year=2075, month=7, day=6))

        hf = self._build_hf(EntityCellCustomField(cfield_flight),
                            EntityCellCustomField(cfield_blood),
                           )
        response = self.assertPOST200(self.url, data={'hfilter': hf.id,
                                                      '_search': 1,
                                                      #cfield_flight.pk: ['1-1-2074', '31-12-2074'],
                                                      #cfield_blood.pk:  ['',         '1-1-2075'],
                                                      'custom_field-%s' % cfield_flight.pk: ['1-1-2074', '31-12-2074'],
                                                      'custom_field-%s' % cfield_blood.pk:  ['',         '1-1-2075'],
                                                     })
        content = self._get_lv_content(response)
        self.assertNotIn(bebop.name,      content)
        self.assertIn(swordfish.name,     content)
        self.assertNotIn(redtail.name,    content)
        self.assertNotIn(hammerhead.name, content)
        self.assertNotIn(dragons.name,    content)

    def test_search_functionfield01(self):
        "Can not search on this FunctionField"
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        ptype = CremePropertyType.create(str_pk='test-prop_red',  text='is red')
        CremeProperty.objects.create(type=ptype, creme_entity=swordfish)

        func_field = Organisation.function_fields.get('get_pretty_properties')
        self._build_hf(EntityCellFunctionField(func_field))

        response = self.assertPOST200(self.url, data={'_search':       1,
                                                      #'name':          '',
                                                      #func_field.name: 'red',
                                                      'regular_field-name': '',
                                                      'function_field-%s' % func_field.name: 'red',
                                                     }
                                     )
        orgas_set = self._get_entities_set(response)
        self.assertIn(bebop,     orgas_set)
        self.assertIn(swordfish, orgas_set)

    @skipIfNotInstalled('creme.billing')
    def test_search_functionfield02(self):
        "billing_LineTypeField"
        from creme.billing.constants import PRODUCT_LINE_TYPE, SERVICE_LINE_TYPE
        from creme.billing.models import Invoice, InvoiceStatus, Line, ProductLine, ServiceLine

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
        self._build_hf(EntityCellFunctionField(func_field))

        url = Line.get_lv_absolute_url()
        response = self.assertGET200(url)
        ids = set(l.id for l in self._get_entities_set(response))
        self.assertIn(pline1.id, ids)
        self.assertIn(pline2.id, ids)
        self.assertIn(sline1.id, ids)
        self.assertIn(sline2.id, ids)

        def post(line_type):
            return self.assertPOST200(url, data={'_search':       1,
                                                 #'name':          '',
                                                 #func_field.name: line_type,
                                                 'regular_field-name': '',
                                                 'function_field-%s' % func_field.name: line_type,
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
