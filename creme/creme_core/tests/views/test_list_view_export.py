# -*- coding: utf-8 -*-

try:
    from datetime import date
    from functools import partial
    from os.path import dirname, exists, join
    from unittest import skipIf
    from urllib import urlencode

    import html5lib

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Q
    from django.test.utils import override_settings
    from django.urls import reverse
    from django.utils.encoding import force_unicode
    from django.utils.formats import date_format
    from django.utils.timezone import localtime
    from django.utils.translation import ugettext as _

    from .base import ViewsTestCase
    from ..fake_constants import FAKE_PERCENT_UNIT, FAKE_AMOUNT_UNIT
    from ..fake_models import (FakeContact, FakeOrganisation, FakeImage,
            FakeEmailCampaign, FakeMailingList, FakeInvoice, FakeInvoiceLine)
    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.models import (RelationType, Relation, FieldsConfig,
            CremePropertyType, CremeProperty, FileRef,
            HeaderFilter, EntityFilter, EntityFilterCondition)
    from creme.creme_core.models.history import TYPE_EXPORT, HistoryLine
    from creme.creme_core.utils.queries import QSerializer
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))

try:
    from creme.creme_core.backends import export_backend_registry
    from creme.creme_core.utils.xlrd_utils import XlrdReader

    XlsMissing = 'xls' not in export_backend_registry.iterkeys()
except Exception:
    XlsMissing = True


class CSVExportViewsTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        super(CSVExportViewsTestCase, cls).setUpClass()
        cls.ct = ContentType.objects.get_for_model(FakeContact)

        cls._hf_backup = list(HeaderFilter.objects.all())
        HeaderFilter.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        super(CSVExportViewsTestCase, cls).tearDownClass()
        HeaderFilter.objects.all().delete()
        HeaderFilter.objects.bulk_create(cls._hf_backup)

    def _build_hf_n_contacts(self):
        user = self.user

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        self.organisations = organisations = {
                name: create_orga(name=name)
                    for name in ('Bebop', 'Swordfish')
            }

        rtype_pilots = RelationType.create(('test-subject_pilots', 'pilots'),
                                           ('test-object_pilots',  'is piloted by')
                                          )[0]

        create_ptype = CremePropertyType.create
        ptype_beautiful = create_ptype(str_pk='test-prop_beautiful', text='is beautiful')
        ptype_girl      = create_ptype(str_pk='test-prop_girl',      text='is a girl')

        create_contact = partial(FakeContact.objects.create, user=user)
        self.contacts = contacts = {
                first_name: create_contact(first_name=first_name, last_name=last_name)
                        for first_name, last_name in [('Spike', 'Spiegel'),
                                                      ('Jet', 'Black'),
                                                      ('Faye', 'Valentine'),
                                                      ('Edward', 'Wong'),
                                                     ]
            }

        create_rel = partial(Relation.objects.create, user=user, type=rtype_pilots,
                             object_entity=organisations['Bebop']
                            )
        create_rel(subject_entity=contacts['Jet'])
        create_rel(subject_entity=contacts['Spike'])
        create_rel(subject_entity=contacts['Spike'], object_entity=organisations['Swordfish'])

        create_prop = CremeProperty.objects.create
        create_prop(type=ptype_girl,      creme_entity=contacts['Faye'])
        create_prop(type=ptype_girl,      creme_entity=contacts['Edward'])
        create_prop(type=ptype_beautiful, creme_entity=contacts['Faye'])

        cells = [EntityCellRegularField.build(model=FakeContact, name='civility'),
                 EntityCellRegularField.build(model=FakeContact, name='last_name'),
                 EntityCellRegularField.build(model=FakeContact, name='first_name'),
                 EntityCellRelation(model=FakeContact, rtype=rtype_pilots),
                 # TODO: EntityCellCustomField
                 EntityCellFunctionField(FakeContact, func_field=FakeContact.function_fields.get('get_pretty_properties')),
                ]
        hf = HeaderFilter.create(pk='test-hf_contact', name='Contact view',
                                 model=FakeContact, cells_desc=cells,
                                )

        # return cells
        return hf

    @staticmethod
    # def _build_dl_url(ct, doc_type='csv', header=False, list_url='', use_GET=True):
    def _build_dl_url(ct_id, doc_type='csv', header=False, list_url='', hfilter_id=None, **kwargs):
        # if not use_GET:
        #     return reverse('creme_core__dl_listview_header' if header else 'creme_core__dl_listview',
        #                    args=(ct.id, doc_type)
        #                   )
        parameters = '?ct_id={ctid}&type={doctype}&list_url={url}{hfilter}{header}'.format(
                         ctid=ct_id or '',
                         doctype=doc_type,
                         url=list_url,
                         header='&header=true' if header else '',
                         hfilter='&hfilter={}'.format(hfilter_id) if hfilter_id is not None else '',
                        )

        if kwargs:
            parameters += '&{}'.format(urlencode(kwargs, doseq=True))

        return reverse('creme_core__dl_listview') + parameters

    def _build_contact_dl_url(self, list_url=None, hfilter_id=None, **kwargs):
        ct = self.ct

        return self._build_dl_url(
                ct_id=ct.id,
                list_url=list_url or FakeContact.get_lv_absolute_url(),
                hfilter_id=hfilter_id or
                           HeaderFilter.objects.filter(entity_type=ct).values_list('id', flat=True).first(),
                **kwargs
        )

    def test_export_error_invalid_doctype(self):
        "Assert doc_type in ('xls', 'csv')"
        self.login()
        self.assertGET404(self._build_contact_dl_url(doc_type='exe'))

    def test_export_error_invalid_ctype(self):
        self.login()
        lv_url = FakeContact.get_lv_absolute_url()

        self.assertGET404(self._build_dl_url(ct_id=None, list_url=lv_url))

    def test_export_error_invalid_hfilter(self):
        self.login()
        lv_url = FakeContact.get_lv_absolute_url()

        # HeaderFilter does not exist
        self.assertGET404(self._build_dl_url(self.ct.id, list_url=lv_url))

        # HeaderFilter not given
        self.assertGET404(self._build_dl_url(self.ct.id, list_url=lv_url, hfilter_id=''))

        # Unknown HeaderFilter id
        self.assertGET404(self._build_dl_url(self.ct.id, list_url=lv_url,
                                             hfilter_id='test-hf_contact-unknown',
                                            )
                          )

        # HeaderFilter with wrong content type
        hf = HeaderFilter.create(pk='test-hf_contact_test_invalid_hfilter', name='Contact view', model=FakeContact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'created'}),
                                            ],
                                )
        self.assertGET404(self._build_dl_url(ContentType.objects.get_for_model(FakeEmailCampaign).id,
                                             list_url=lv_url,
                                             hfilter_id=hf.id,
                                            )
                         )

    def test_list_view_export_header(self):
        self.login()
        # cells = self._build_hf_n_contacts()
        cells = self._build_hf_n_contacts().cells
        existing_hline_ids = list(HistoryLine.objects.values_list('id', flat=True))

        response = self.assertGET200(self._build_contact_dl_url(header=True))

        self.assertEqual([u','.join(u'"%s"' % hfi.title for hfi in cells)],
                         [force_unicode(line) for line in response.content.splitlines()]
                        )
        self.assertFalse(HistoryLine.objects.exclude(id__in=existing_hline_ids))

        # # Legacy
        # response = self.assertGET200(self._build_dl_url(self.ct.id, header=True, use_GET=False),
        #                              data={'list_url': lv_url}
        #                             )
        # self.assertEqual([u','.join(u'"%s"' % hfi.title for hfi in cells)],
        #                  [force_unicode(line) for line in response.content.splitlines()]
        #                 )

    @skipIf(XlsMissing, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_xls_export_header(self):
        self.login()
        # cells = self._build_hf_n_contacts()
        cells = self._build_hf_n_contacts().cells

        response = self.assertGET200(self._build_contact_dl_url(doc_type='xls', header=True),
                                     follow=True
                                    )

        result = list(XlrdReader(None, file_contents=response.content))
        self.assertEqual(1, len(result))
        self.assertEqual(result[0], [hfi.title for hfi in cells])

    def test_list_view_export01(self):
        "csv"
        user = self.login()
        # cells = self._build_hf_n_contacts()
        hf = self._build_hf_n_contacts()
        existing_hline_ids = list(HistoryLine.objects.values_list('id', flat=True))

        response = self.assertGET200(self._build_contact_dl_url())

        # TODO: sort the relations/properties by they verbose_name ??
        result = response.content.splitlines()
        it = (force_unicode(line) for line in result)
        self.assertEqual(it.next(), u','.join(u'"%s"' % hfi.title for hfi in hf.cells))
        self.assertEqual(it.next(), u'"","Black","Jet","Bebop",""')
        self.assertIn(it.next(), (u'"","Spiegel","Spike","Bebop/Swordfish",""',
                                  u'"","Spiegel","Spike","Swordfish/Bebop",""')
                     )
        self.assertIn(it.next(), (u'"","Valentine","Faye","","is a girl/is beautiful"',
                                  u'"","Valentine","Faye","","is beautiful/is a girl"')
                     )
        self.assertEqual(it.next(), u'"","Wong","Edward","","is a girl"')
        self.assertRaises(StopIteration, it.next)

        # # Legacy
        # response = self.assertGET200(self._build_dl_url(self.ct.id, use_GET=False), data={'list_url': lv_url})
        # self.assertEqual(result, response.content.splitlines())

        # History
        hlines = HistoryLine.objects.exclude(id__in=existing_hline_ids)
        self.assertEqual(1, len(hlines))

        hline = hlines[0]
        self.assertEqual(self.ct,      hline.entity_ctype)
        self.assertEqual(user,         hline.entity_owner)
        self.assertEqual(TYPE_EXPORT,  hline.type)

        count = len(result) - 1
        self.assertEqual([count, hf.name],
                         hline.modifications
                        )
        self.assertEqual([_(u'Export of {counter} «{type}» (view «{view}» & filter «{filter}»)').format(
                                    counter=count,
                                    type='Test Contacts',
                                    view=hf.name,
                                    filter=_(u'All'),
                                ),
                         ],
                         hline.get_verbose_modifications(user),
                        )

    def test_list_view_export02(self):
        "scsv"
        self.login()
        # cells = self._build_hf_n_contacts()
        cells = self._build_hf_n_contacts().cells

        response = self.assertGET200(self._build_contact_dl_url(doc_type='scsv'))

        # TODO: sort the relations/properties by they verbose_name ??
        it = (force_unicode(line) for line in response.content.splitlines())
        self.assertEqual(it.next(), u';'.join(u'"%s"' % hfi.title for hfi in cells))
        self.assertEqual(it.next(), u'"";"Black";"Jet";"Bebop";""')
        self.assertIn(it.next(), (u'"";"Spiegel";"Spike";"Bebop/Swordfish";""',
                                  u'"";"Spiegel";"Spike";"Swordfish/Bebop";""')
                     )
        self.assertIn(it.next(), (u'"";"Valentine";"Faye";"";"is a girl/is beautiful"',
                                  u'"";"Valentine";"Faye";"";"is beautiful/is a girl"')
                     )
        self.assertEqual(it.next(), u'"";"Wong";"Edward";"";"is a girl"')
        self.assertRaises(StopIteration, it.next)

    def test_list_view_export03(self):
        "'export' credential"
        self.login(is_superuser=False)
        self._build_hf_n_contacts()

        url = self._build_contact_dl_url()
        self.assertGET403(url)

        # self.role.exportable_ctypes = [self.ct]  # Set the 'export' credentials
        self.role.exportable_ctypes.set([self.ct])  # Set the 'export' credentials
        self.assertGET200(url)

    def test_list_view_export04(self):
        "Credential"
        user = self.login(is_superuser=False)
        # self.role.exportable_ctypes = [self.ct]
        self.role.exportable_ctypes.set([self.ct])

        self._build_hf_n_contacts()

        contacts = self.contacts
        faye = contacts['Faye']
        faye.user = self.other_user
        faye.save()
        self.assertFalse(user.has_perm_to_view(faye))
        self.assertTrue(user.has_perm_to_view(contacts['Spike']))

        organisations = self.organisations
        bebop = organisations['Bebop']
        bebop.user = self.other_user
        bebop.save()
        self.assertFalse(user.has_perm_to_view(bebop))
        self.assertTrue(user.has_perm_to_view(organisations['Swordfish']))

        response = self.assertGET200(self._build_contact_dl_url())
        result = map(force_unicode, response.content.splitlines())
        self.assertEqual(result[1], '"","Black","Jet","",""')
        self.assertEqual(result[2], '"","Spiegel","Spike","Swordfish",""')
        self.assertEqual(result[3], u'"","Wong","Edward","","is a girl"')

    def test_list_view_export05(self):
        "Datetime field"
        user = self.login()

        hf = HeaderFilter.create(pk='test-hf_contact_test_export05', name='Contact view', model=FakeContact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'created'}),
                                            ],
                                )

        spike = FakeContact.objects.create(user=user, first_name='Spike', last_name='Spiegel')

        response = self.assertGET200(self._build_contact_dl_url(hfilter_id=hf.id))

        result = [force_unicode(line) for line in response.content.splitlines()]
        self.assertEqual(2, len(result))
        self.assertEqual(result[1],
                         u'"{}","{}"'.format(spike.last_name,
                                             date_format(localtime(spike.created), 'DATETIME_FORMAT'),
                                            )
                        )

    def test_list_view_export06(self):
        "FK field on CremeEntity"
        user = self.login(is_superuser=False)
        self.role.exportable_ctypes.set([self.ct])

        create_img = FakeImage.objects.create
        spike_face = create_img(name='Spike face', user=self.other_user, description="Spike's selfie")
        jet_face   = create_img(name='Jet face',   user=user,            description="Jet's selfie")
        self.assertTrue(user.has_perm_to_view(jet_face))
        self.assertFalse(user.has_perm_to_view(spike_face))

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Spike', last_name='Spiegel', image=spike_face)
        create_contact(first_name='Jet',   last_name='Black',   image=jet_face)
        create_contact(first_name='Faye',  last_name='Valentine')

        hf = HeaderFilter.create(pk='test-hf_contact_test_export06', name='Contact view', model=FakeContact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'image'}),
                                             (EntityCellRegularField, {'name': 'image__description'}),
                                            ],
                                )

        response = self.assertGET200(self._build_contact_dl_url(hfilter_id=hf.id))
        it = (force_unicode(line) for line in response.content.splitlines()); it.next()

        self.assertEqual(it.next(), '"Black","Jet face","Jet\'s selfie"')

        HIDDEN_VALUE = settings.HIDDEN_VALUE
        self.assertEqual(it.next(), '"Spiegel","%s","%s"' % (HIDDEN_VALUE, HIDDEN_VALUE))
        self.assertEqual(it.next(), '"Valentine","",""')

    def test_list_view_export07(self):
        "M2M field on CremeEntities"
        user = self.login()

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        camp1 = create_camp(name='Camp#1')
        camp2 = create_camp(name='Camp#2')
        create_camp(name='Camp#3')

        create_ml = partial(FakeMailingList.objects.create, user=user)
        # camp1.mailing_lists = [create_ml(name='ML#1'), create_ml(name='ML#2')]
        # camp2.mailing_lists = [create_ml(name='ML#3')]
        camp1.mailing_lists.set([create_ml(name='ML#1'), create_ml(name='ML#2')])
        camp2.mailing_lists.set([create_ml(name='ML#3')])

        hf = HeaderFilter.create(pk='test_hf', name='Campaign view', model=FakeEmailCampaign,
                                 cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                             (EntityCellRegularField, {'name': 'mailing_lists__name'}),
                                            ],
                                )

        response = self.assertGET200(self._build_dl_url(ContentType.objects.get_for_model(FakeEmailCampaign).id,
                                                        list_url=FakeEmailCampaign.get_lv_absolute_url(),
                                                        hfilter_id=hf.id,
                                                       ),
                                    )
        result = [force_unicode(line) for line in response.content.splitlines()]
        self.assertEqual(4, len(result))

        self.assertEqual(result[1], '"Camp#1","ML#1/ML#2"')
        self.assertEqual(result[2], '"Camp#2","ML#3"')
        self.assertEqual(result[3], '"Camp#3",""')

    def test_list_view_export08(self):
        "FieldsConfig"
        self.login()
        self._build_hf_n_contacts()

        FieldsConfig.create(FakeContact,
                            descriptions=[('first_name', {FieldsConfig.HIDDEN: True})],
                           )

        response = self.assertGET200(self._build_contact_dl_url())

        it = (force_unicode(line) for line in response.content.splitlines())
        self.assertEqual(it.next(),
                         u','.join(u'"%s"' % u for u in [_(u'Civility'),
                                                         _(u'Last name'),
                                                         'pilots',
                                                         _(u'Properties'),
                                                        ]
                                  )
                        )
        self.assertEqual(it.next(), u'"","Black","Bebop",""')

    def test_extra_filter(self):
        self.login()
        self._build_hf_n_contacts()

        response = self.assertGET200(self._build_contact_dl_url(extra_q=QSerializer().dumps(Q(last_name='Wong'))))

        result = [force_unicode(line) for line in response.content.splitlines()]
        self.assertEqual(2, len(result))
        self.assertEqual(u'"","Wong","Edward","","is a girl"', result[1])

    def test_list_view_export_with_filter01(self):
        user = self.login()
        hf = self._build_hf_n_contacts()
        efilter = EntityFilter.create('test-filter01', 'Red', FakeContact,
                                      user=user, is_custom=False,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=FakeContact,
                                                        operator=EntityFilterCondition.ISTARTSWITH,
                                                        name='last_name', values=['Wong'],
                                                    ),
                                                 ],
                                     )

        existing_hline_ids = list(HistoryLine.objects.values_list('id', flat=True))

        url = FakeContact.get_lv_absolute_url()
        # TODO: remove when filter ID is sent to export view as GET arg
        self.assertPOST200(url, data={'filter': efilter.id})

        response = self.assertGET200(self._build_contact_dl_url(list_url=url))
        result = [force_unicode(line) for line in response.content.splitlines()]
        self.assertEqual(2, len(result))

        self.assertEqual(u'"","Wong","Edward","","is a girl"', result[1])

        # History
        hlines = HistoryLine.objects.exclude(id__in=existing_hline_ids)
        self.assertEqual(1, len(hlines))

        hline = hlines[0]
        self.assertEqual([1, hf.name, efilter.name],
                         hline.modifications
                        )
        self.assertEqual([_(u'Export of {counter} «{type}» (view «{view}» & filter «{filter}»)').format(
                                    counter=1,
                                    type='Test Contact',
                                    view=hf.name,
                                    filter=efilter.name,
                                ),
                         ],
                         hline.get_verbose_modifications(user),
                        )

    @skipIf(XlsMissing, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_xls_export01(self):
        self.login()
        # cells = self._build_hf_n_contacts()
        cells = self._build_hf_n_contacts().cells
        existing_fileref_ids = list(FileRef.objects.values_list('id', flat=True))

        response = self.assertGET200(self._build_contact_dl_url(doc_type='xls'),
                                     follow=True,
                                    )

        it = iter(XlrdReader(None, file_contents=response.content))
        self.assertEqual(it.next(), [hfi.title for hfi in cells])
        self.assertEqual(it.next(), ["", "Black", "Jet", "Bebop", ""])
        self.assertIn(it.next(), (["", "Spiegel", "Spike", "Bebop/Swordfish", ""],
                                  ["", "Spiegel", "Spike", "Swordfish/Bebop", ""]))
        self.assertIn(it.next(), (["", "Valentine", "Faye", "", "is a girl/is beautiful"],
                                  ["", "Valentine", "Faye", "", "is beautiful/is a girl"]))
        self.assertEqual(it.next(), ["", "Wong", "Edward", "", "is a girl"])
        self.assertRaises(StopIteration, it.next)

        # FileRef
        filerefs = FileRef.objects.exclude(id__in=existing_fileref_ids)
        self.assertEqual(1, len(filerefs))

        fileref = filerefs[0]
        self.assertTrue(fileref.temporary)
        self.assertEqual(u'fakecontact.xls', fileref.basename)
        # self.assertEqual(user, fileref.user) TODO

        fullpath = fileref.filedata.path
        self.assertTrue(exists(fullpath), '<{}> does not exists ?!'.format(fullpath))
        self.assertEqual(join(settings.MEDIA_ROOT, 'upload', 'xls'), dirname(fullpath))

    @skipIf(XlsMissing, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_xls_export02(self):
        "Other CT, other type of fields"
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(name='Bebop')
        orga02 = create_orga(name='Swordfish', subject_to_vat=False, creation_date=date(year=2016, month=7, day=5))

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [build_cell(name='name'),
                 build_cell(name='subject_to_vat'),
                 build_cell(name='creation_date'),
                ]

        hf = HeaderFilter.create(pk='test-hf_orga', name='Organisation view',
                                 model=FakeOrganisation, cells_desc=cells,
                                )

        response = self.assertGET200(self._build_dl_url(ContentType.objects.get_for_model(FakeOrganisation).id,
                                                        doc_type='xls',
                                                        list_url=FakeOrganisation.get_lv_absolute_url(),
                                                        hfilter_id=hf.id,
                                                       ),
                                     follow=True,
                                    )

        it = iter(XlrdReader(None, file_contents=response.content))
        self.assertEqual(it.next(), [hfi.title for hfi in cells])
        self.assertEqual(it.next(), [orga01.name, _(u'Yes'), ''])
        self.assertEqual(it.next(), [orga02.name, _(u'No'),  date_format(orga02.creation_date, 'DATE_FORMAT')])
        self.assertRaises(StopIteration, it.next)

    def test_print_integer01(self):
        "No choices"
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        for name, capital in (('Bebop', 1000), ('Swordfish', 20000), ('Redtail', None)):
            create_orga(name=name, capital=capital)

        build = partial(EntityCellRegularField.build, model=FakeOrganisation)
        hf = HeaderFilter.create(pk='test-hf_orga', name='Organisation view',
                                 model=FakeOrganisation,
                                cells_desc=[build(name='name'), build(name='capital')],
                                )

        lv_url = FakeOrganisation.get_lv_absolute_url()
        response = self.assertGET200(self._build_dl_url(ContentType.objects.get_for_model(FakeOrganisation).id,
                                                        list_url=lv_url,
                                                        hfilter_id=hf.id,
                                                       ),
                                     follow=True,
                                    )

        lines = {force_unicode(line) for line in response.content.splitlines()}
        self.assertIn(u'"Bebop","1000"', lines)
        self.assertIn(u'"Swordfish","20000"', lines)
        self.assertIn(u'"Redtail",""', lines)

    def test_print_integer02(self):
        "Field with choices"
        user = self.login()

        invoice = FakeInvoice.objects.create(user=user, name='Invoice',
                                             expiration_date=date(year=2012, month=12, day=15),
                                            )

        create_pline = partial(FakeInvoiceLine.objects.create, user=user, linked_invoice=invoice)
        create_pline(item='Bebop',     discount_unit=FAKE_PERCENT_UNIT)
        create_pline(item='Swordfish', discount_unit=FAKE_AMOUNT_UNIT)

        build = partial(EntityCellRegularField.build, model=FakeInvoiceLine)
        hf = HeaderFilter.create(pk='test-hf_fakeinvoiceline', name='InvoiceLine view',
                                 model=FakeInvoiceLine,
                                 cells_desc=[build(name='item'),
                                             build(name='discount_unit'),
                                            ],
                                )

        response = self.assertGET200(self._build_dl_url(ContentType.objects.get_for_model(FakeInvoiceLine).id,
                                                        list_url=FakeInvoiceLine.get_lv_absolute_url(),
                                                        hfilter_id=hf.id,
                                                       ),
                                     follow=True,
                                    )

        lines = {force_unicode(line) for line in response.content.splitlines()}
        self.assertIn(u'"Bebop","%s"' % _(u'Percent'), lines)
        self.assertIn(u'"Swordfish","%s"' % _(u'Amount'), lines)

    # TODO: factorise with ListViewTestCase
    def _get_lv_content(self, response):
        page_tree = html5lib.parse(response.content, namespaceHTMLElements=False)

        content_node = page_tree.find(".//table[@id='list']")
        self.assertIsNotNone(content_node, 'The table id="list" is not found.')

        tbody = content_node.find(".//tbody")
        self.assertIsNotNone(tbody)

        content = []

        for tr_node in tbody.findall('tr'):
            for td_node in tr_node.findall('td'):
                class_attr = td_node.attrib.get('class')

                if class_attr:
                    classes = class_attr.split()

                    if 'lv-cell-content' in classes:
                        div_node = td_node.find(".//div")

                        if div_node is not None:
                            content.append(div_node.text.strip())

        return content

    @override_settings(PAGE_SIZES=[10], DEFAULT_PAGE_SIZE_IDX=0)
    def test_quick_search(self):
        user = self.login()

        hf = HeaderFilter.create(pk='test-hf_contact_test_quick_search', name='Contact view',
                                 model=FakeContact,
                                 cells_desc=[(EntityCellRegularField, {'name': 'phone'}),
                                             (EntityCellRegularField, {'name': 'last_name'}),
                                             (EntityCellRegularField, {'name': 'first_name'}),
                                            ],
                                )

        create_contact = partial(FakeContact.objects.create, user=user)
        spike = create_contact(first_name='Spike', last_name='Spiegel',   phone='123233')
        jet   = create_contact(first_name='Jet',   last_name='Black',     phone='123455')
        faye  = create_contact(first_name='Faye',  last_name='Valentine', phone='678678')

        # Set the current list view state, with the quick search
        lv_url = FakeContact.get_lv_absolute_url()
        response = self.assertPOST200(lv_url,
                                      data={'_search': 1,
                                            'regular_field-phone': '123',
                                           }
                                     )
        content = self._get_lv_content(response)
        self.assertCountOccurrences(spike.last_name, content, count=1)
        self.assertCountOccurrences(jet.last_name, content, count=1)
        self.assertNotIn(faye.last_name, content)

        # ----------------------
        response = self.assertGET200(self._build_contact_dl_url(hfilter_id=hf.id))

        it = (force_unicode(line) for line in response.content.splitlines())
        it.next()  # Header
        self.assertEqual(it.next(), u'"123455","Black","Jet"')
        self.assertEqual(it.next(), u'"123233","Spiegel","Spike"')

        with self.assertRaises(StopIteration):
            it.next()

    def test_distinct(self):
        user = self.login()

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        camp1 = create_camp(name='Camp#1')
        camp2 = create_camp(name='Camp#2')
        camp3 = create_camp(name='Camp#3')

        create_ml = partial(FakeMailingList.objects.create, user=user)

        ml1 = create_ml(name='Bebop staff')
        ml2 = create_ml(name='Mafia staff')

        # camp1.mailing_lists = [ml1, ml2]
        # camp2.mailing_lists = [ml1]
        camp1.mailing_lists.set([ml1, ml2])
        camp2.mailing_lists.set([ml1])

        HeaderFilter.create(pk='test_hf', name='Campaign view', model=FakeEmailCampaign,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                        (EntityCellRegularField, {'name': 'mailing_lists'}),
                                       ],
                           )

        # Set the current list view state, with the quick search
        lv_url = FakeEmailCampaign.get_lv_absolute_url()
        response = self.assertPOST200(lv_url,
                                      data={'regular_field-mailing_lists': 'staff'}
                                     )
        content = self._get_lv_content(response)

        self.assertCountOccurrences(camp1.name, content, count=1)  # Not 2
        self.assertCountOccurrences(camp2.name, content, count=1)
        self.assertNotIn(camp3.name, content)

        # # ------
        # response = self.assertGET200(self._build_dl_url(ContentType.objects.get_for_model(FakeEmailCampaign), use_GET=False),
        #                              data={'list_url': lv_url}
        #                             )
        # result = [force_unicode(line) for line in response.content.splitlines()]
        # self.assertEqual(3, len(result))
        # self.assertEqual(result[1], '"Camp#1","Bebop staff/Mafia staff"')
        # self.assertEqual(result[2], '"Camp#2","Bebop staff"')
