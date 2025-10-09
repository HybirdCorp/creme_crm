from datetime import date
from functools import partial
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.utils.timezone import localtime
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from openpyxl import load_workbook

from creme.creme_core.core.entity_cell import (
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.entity_filter.condition_handler import (
    RegularFieldConditionHandler,
)
from creme.creme_core.core.entity_filter.operators import ISTARTSWITH
from creme.creme_core.gui.history import html_history_registry
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    EntityFilter,
    FakeContact,
    FakeEmailCampaign,
    FakeImage,
    FakeInvoice,
    FakeInvoiceLine,
    FakeMailingList,
    FakeOrganisation,
    FieldsConfig,
    FileRef,
    HeaderFilter,
    Language,
    Relation,
    RelationType,
)
from creme.creme_core.models.history import TYPE_EXPORT, HistoryLine
from creme.creme_core.utils.content_type import as_ctype
from creme.creme_core.utils.queries import QSerializer
from creme.creme_core.utils.xlrd_utils import XlrdReader

from ..base import CremeTestCase


class MassExportViewsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ct = ContentType.objects.get_for_model(FakeContact)

    def _build_hf_n_contacts(self, user):
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        self.organisations = organisations = {
            name: create_orga(name=name)
            for name in ('Bebop', 'Swordfish')
        }

        rtype_pilots = RelationType.objects.builder(
            id='test-subject_pilots', predicate='pilots',
        ).symmetric(
            id='test-object_pilots', predicate='is piloted by',
        ).get_or_create()[0]

        create_ptype = CremePropertyType.objects.create
        ptype_beautiful = create_ptype(text='is beautiful')
        ptype_girl      = create_ptype(text='is a girl')

        create_contact = partial(FakeContact.objects.create, user=user)
        self.contacts = contacts = {
            first_name: create_contact(first_name=first_name, last_name=last_name)
            for first_name, last_name in [
                ('Spike', 'Spiegel'),
                ('Jet', 'Black'),
                ('Faye', 'Valentine'),
                ('Edward', 'Wong'),
            ]
        }

        create_rel = partial(
            Relation.objects.create,
            user=user, type=rtype_pilots, object_entity=organisations['Bebop'],
        )
        create_rel(subject_entity=contacts['Jet'])
        create_rel(subject_entity=contacts['Spike'])
        create_rel(subject_entity=contacts['Spike'], object_entity=organisations['Swordfish'])

        create_prop = CremeProperty.objects.create
        create_prop(type=ptype_girl,      creme_entity=contacts['Faye'])
        create_prop(type=ptype_girl,      creme_entity=contacts['Edward'])
        create_prop(type=ptype_beautiful, creme_entity=contacts['Faye'])

        cells = [
            EntityCellRegularField.build(model=FakeContact, name='civility'),
            EntityCellRegularField.build(model=FakeContact, name='last_name'),
            EntityCellRegularField.build(model=FakeContact, name='first_name'),
            EntityCellRelation(model=FakeContact, rtype=rtype_pilots),
            # TODO: EntityCellCustomField
            EntityCellFunctionField.build(
                model=FakeContact, name='get_pretty_properties',
            ),
        ]

        return HeaderFilter.objects.proxy(
            id='test-hf_contact', name='Contact view',
            model=FakeContact, cells=cells,
        ).get_or_create()[0]

    @staticmethod
    def _build_dl_url(ct_or_model, doc_type='csv', header=False,
                      efilter_id=None, hfilter_id=None, **kwargs):
        parameters = '?ct_id={ctid}&type={doctype}{efilter}{hfilter}{header}'.format(
            ctid='' if ct_or_model is None else as_ctype(ct_or_model).id,
            doctype=doc_type,
            header='&header=true' if header else '',
            efilter='' if efilter_id is None else f'&efilter={efilter_id}',
            hfilter='' if hfilter_id is None else f'&hfilter={hfilter_id}',
        )

        if kwargs:
            parameters += f'&{urlencode(kwargs, doseq=True)}'

        return reverse('creme_core__mass_export') + parameters

    def _build_contact_dl_url(self, hfilter_id=None, **kwargs):
        ct = self.ct

        return self._build_dl_url(
            ct_or_model=ct,
            hfilter_id=(
                hfilter_id
                or HeaderFilter.objects
                               .filter(entity_type=ct)
                               .values_list('id', flat=True)
                               .first()
            ),
            **kwargs
        )

    def test_export_error_invalid_doctype(self):
        "Assert doc_type in ('xls', 'csv')."
        self.login_as_root()
        self.assertGET404(self._build_contact_dl_url(doc_type='exe'))

    def test_export_error_invalid_ctype(self):
        self.login_as_root()
        lv_url = FakeContact.get_lv_absolute_url()

        self.assertGET404(self._build_dl_url(ct_or_model=None, list_url=lv_url))

    def test_export_error_invalid_hfilter(self):
        self.login_as_root()
        lv_url = FakeContact.get_lv_absolute_url()
        build_url = partial(self._build_dl_url, ct_or_model=self.ct, list_url=lv_url)

        # HeaderFilter does not exist
        self.assertGET404(build_url())

        # HeaderFilter not given
        self.assertGET404(build_url(hfilter_id=None))

        # Unknown HeaderFilter id
        self.assertGET404(build_url(hfilter_id='test-hf_contact-unknown'))

        # HeaderFilter with wrong content type
        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact_test_invalid_hfilter01',
            name='Contact view', model=FakeContact,
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'created'),
            ],
        ).get_or_create()[0]
        self.assertGET404(build_url(ct_or_model=FakeEmailCampaign, hfilter_id=hf.id))

        # HeaderFilter is not allowed
        private_hf = HeaderFilter.objects.proxy(
            id='test-hf_contact_test_invalid_hfilter02',
            name='Private contact view', model=FakeContact,
            is_custom=True, user=self.create_user(), is_private=True,
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'first_name'),
            ],
        ).get_or_create()[0]
        self.assertGET404(build_url(hfilter_id=private_hf.id))

    def test_export_error_invalid_efilter(self):
        user = self.login_as_root_and_get()
        HeaderFilter.objects.proxy(
            id='test-hf_contact', name='Contact view', model=FakeContact,
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'first_name'),
            ],
        ).get_or_create()

        # EntityFilter does not exist
        self.assertGET404(self._build_contact_dl_url(efilter_id='test-unknown'))

        # EntityFilter with wrong content type
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-hf_orga_test_invalid_efilter',
            name='Cowboys',
            model=FakeOrganisation,  # <===
            user=user, is_custom=False,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='name',
                    operator=ISTARTSWITH, values=['Cowboy'],
                )
            ],
        )
        self.assertGET404(self._build_contact_dl_url(efilter_id=efilter.id,))

        # EntityFilter is not allowed
        private_efilter = EntityFilter.objects.smart_update_or_create(
            'test-hf_contact_test_invalid_efilter',
            name='With Contact mail',
            model=FakeContact,
            is_custom=True, user=self.create_user(), is_private=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='email',
                    operator=ISTARTSWITH, values=['contact'],
                )
            ],
        )
        self.assertGET404(self._build_contact_dl_url(efilter_id=private_efilter.id,))

    def test_list_view_export_header(self):
        user = self.login_as_root_and_get()
        cells = self._build_hf_n_contacts(user=user).cells
        existing_hline_ids = [*HistoryLine.objects.values_list('id', flat=True)]

        response = self.assertGET200(self._build_contact_dl_url(header=True))

        self.assertListEqual(
            [','.join(f'"{hfi.title}"' for hfi in cells)],
            [force_str(line) for line in response.content.splitlines()],
        )
        self.assertFalse(HistoryLine.objects.exclude(id__in=existing_hline_ids))

    def test_xls_export_header(self):
        user = self.login_as_root_and_get()
        cells = self._build_hf_n_contacts(user=user).cells

        response = self.assertGET200(
            self._build_contact_dl_url(doc_type='xls', header=True),
            follow=True,
        )

        result = self.get_alone_element(
            XlrdReader(None, file_contents=b''.join(response.streaming_content))
        )
        self.assertListEqual([hfi.title for hfi in cells], result)

    def test_list_view_export_csv(self):
        user = self.login_as_root_and_get()
        hf = self._build_hf_n_contacts(user=user)
        existing_hline_ids = [*HistoryLine.objects.values_list('id', flat=True)]

        response = self.assertGET200(self._build_contact_dl_url())

        # TODO: sort the relations by their verbose_name ??
        result = response.content.splitlines()
        it = (force_str(line) for line in result)
        self.assertEqual(next(it), ','.join(f'"{hfi.title}"' for hfi in hf.cells))
        self.assertEqual(next(it), '"","Black","Jet","Bebop",""')
        self.assertEqual(next(it), '"","Spiegel","Spike","Bebop/Swordfish",""')
        self.assertEqual(next(it), '"","Valentine","Faye","","is a girl/is beautiful"')
        self.assertEqual(next(it), '"","Wong","Edward","","is a girl"')
        with self.assertRaises(StopIteration):
            next(it)

        # History
        hline = self.get_alone_element(HistoryLine.objects.exclude(id__in=existing_hline_ids))
        self.assertEqual(self.ct,     hline.entity_ctype)
        self.assertEqual(user,        hline.entity_owner)
        self.assertEqual(TYPE_EXPORT, hline.type)

        count = len(result) - 1
        self.assertListEqual(
            [count, hf.name], hline.modifications
        )
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-mass_export">{}<div>',
                _(
                    'Export of «%(counted_instances)s» (view «%(view)s» & filter «%(filter)s»)'
                ) % {
                    'counted_instances': _('{count} {model}').format(
                        count=count,
                        model='Test Contacts',
                    ),
                    'view': hf.name,
                    'filter': pgettext('creme_core-filter', 'All'),
                },
            ),
            html_history_registry.line_explainers([hline], user)[0].render(),
        )

    def test_list_view_export_scsv(self):
        user = self.login_as_root_and_get()
        cells = self._build_hf_n_contacts(user=user).cells

        response = self.assertGET200(self._build_contact_dl_url(doc_type='scsv'))

        # TODO: sort the relations by their verbose_name ??
        it = (force_str(line) for line in response.content.splitlines())
        self.assertEqual(next(it), ';'.join(f'"{hfi.title}"' for hfi in cells))
        self.assertEqual(next(it), '"";"Black";"Jet";"Bebop";""')
        self.assertEqual(next(it), '"";"Spiegel";"Spike";"Bebop/Swordfish";""')
        self.assertEqual(next(it), '"";"Valentine";"Faye";"";"is a girl/is beautiful"')
        self.assertEqual(next(it), '"";"Wong";"Edward";"";"is a girl"')
        with self.assertRaises(StopIteration):
            next(it)

    def test_list_view_export_credentials01(self):
        "'export' credential."
        user = self.login_as_standard()
        self._build_hf_n_contacts(user=user)

        url = self._build_contact_dl_url()
        self.assertGET403(url)

        user.role.exportable_ctypes.set([self.ct])  # Set the 'export' credentials
        self.assertGET200(url)

    def test_list_view_export_credentials02(self):
        "Views credential."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*')
        user.role.exportable_ctypes.set([self.ct])

        other_user = self.get_root_user()

        self._build_hf_n_contacts(user=user)

        contacts = self.contacts
        faye = contacts['Faye']
        faye.user = other_user
        faye.save()
        self.assertFalse(user.has_perm_to_view(faye))
        self.assertTrue(user.has_perm_to_view(contacts['Spike']))

        organisations = self.organisations
        bebop = organisations['Bebop']
        bebop.user = other_user
        bebop.save()
        self.assertFalse(user.has_perm_to_view(bebop))
        self.assertTrue(user.has_perm_to_view(organisations['Swordfish']))

        response = self.assertGET200(self._build_contact_dl_url())
        result = [*map(force_str, response.content.splitlines())]
        self.assertEqual(result[1], '"","Black","Jet","",""')
        self.assertEqual(result[2], '"","Spiegel","Spike","Swordfish",""')
        self.assertEqual(result[3], '"","Wong","Edward","","is a girl"')

    @override_settings(LANGUAGE_CODE='en')
    def test_list_view_export_datetime(self):
        user = self.login_as_root_and_get()

        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact_test_export05', name='Contact view', model=FakeContact,
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'created'),
            ],
        ).get_or_create()[0]

        spike = FakeContact.objects.create(user=user, first_name='Spike', last_name='Spiegel')

        response = self.assertGET200(self._build_contact_dl_url(hfilter_id=hf.id))

        result = [force_str(line) for line in response.content.splitlines()]
        self.assertEqual(2, len(result))
        self.assertEqual(
            '"{}","{}"'.format(
                spike.last_name,
                localtime(spike.created).strftime('%Y-%m-%d %H:%M:%S'),
            ),
            result[1],
        )

    def test_list_view_export_fk_entity(self):
        "FK field on CremeEntity."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*')
        user.role.exportable_ctypes.set([self.ct])

        create_img = FakeImage.objects.create
        spike_face = create_img(
            name='Spike face', user=self.get_root_user(), description="Spike's selfie",
        )
        jet_face = create_img(
            name='Jet face', user=user, description="Jet's selfie",
        )
        self.assertTrue(user.has_perm_to_view(jet_face))
        self.assertFalse(user.has_perm_to_view(spike_face))

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Spike', last_name='Spiegel', image=spike_face)
        create_contact(first_name='Jet',   last_name='Black',   image=jet_face)
        create_contact(first_name='Faye',  last_name='Valentine')

        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact_test_export06', name='Contact view', model=FakeContact,
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'image'),
                (EntityCellRegularField, 'image__description'),
            ],
        ).get_or_create()[0]

        response = self.assertGET200(self._build_contact_dl_url(hfilter_id=hf.id))

        it = (force_str(line) for line in response.content.splitlines())
        next(it)

        self.assertEqual(next(it), '"Black","Jet face","Jet\'s selfie"')

        HIDDEN_VALUE = settings.HIDDEN_VALUE
        self.assertEqual(next(it), f'"Spiegel","{HIDDEN_VALUE}","{HIDDEN_VALUE}"')
        self.assertEqual(next(it), '"Valentine","",""')

    def test_list_view_export_m2m_entities(self):
        "M2M field on CremeEntities."
        user = self.login_as_root_and_get()

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        camp1 = create_camp(name='Camp#1')
        camp2 = create_camp(name='Camp#2')
        create_camp(name='Camp#3')

        create_ml = partial(FakeMailingList.objects.create, user=user)
        camp1.mailing_lists.set([create_ml(name='ML#1'), create_ml(name='ML#2')])
        camp2.mailing_lists.set([create_ml(name='ML#3')])

        hf = HeaderFilter.objects.proxy(
            id='test_hf', name='Campaign view', model=FakeEmailCampaign,
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'mailing_lists__name'),
            ],
        ).get_or_create()[0]

        response = self.assertGET200(self._build_dl_url(
            FakeEmailCampaign,
            list_url=FakeEmailCampaign.get_lv_absolute_url(),
            hfilter_id=hf.id,
        ))
        result = [force_str(line) for line in response.content.splitlines()]
        self.assertEqual(4, len(result))

        self.assertEqual(result[1], '"Camp#1","ML#1/ML#2"')
        self.assertEqual(result[2], '"Camp#2","ML#3"')
        self.assertEqual(result[3], '"Camp#3",""')

    def test_list_view_export_fieldsconfig(self):
        user = self.login_as_root_and_get()
        self._build_hf_n_contacts(user=user)

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('first_name', {FieldsConfig.HIDDEN: True})],
        )

        response = self.assertGET200(self._build_contact_dl_url())

        it = (force_str(line) for line in response.content.splitlines())
        self.assertEqual(
            next(it),
            ','.join(
                f'"{u}"'
                for u in [_('Civility'), _('Last name'), 'pilots', _('Properties')]
            )
        )
        self.assertEqual(next(it), '"","Black","Bebop",""')

    def test_extra_filter(self):
        user = self.login_as_root_and_get()
        self._build_hf_n_contacts(user=user)

        response = self.assertGET200(
            self._build_contact_dl_url(extra_q=QSerializer().dumps(Q(last_name='Wong'))),
        )

        result = [force_str(line) for line in response.content.splitlines()]
        self.assertEqual(2, len(result))
        self.assertEqual('"","Wong","Edward","","is a girl"', result[1])

        # Error
        self.assertGET(400, self._build_contact_dl_url(extra_q='[123]'))

    def test_list_view_export_with_filter01(self):
        user = self.login_as_root_and_get()
        hf = self._build_hf_n_contacts(user=user)
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Red', FakeContact,
            user=user, is_custom=False,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=ISTARTSWITH, values=['Wong'],
                )
            ],
        )

        existing_hline_ids = [*HistoryLine.objects.values_list('id', flat=True)]

        response = self.assertGET200(self._build_contact_dl_url(
            list_url=FakeContact.get_lv_absolute_url(),
            efilter_id=efilter.id
        ))
        result = [force_str(line) for line in response.content.splitlines()]
        self.assertEqual(2, len(result))

        self.assertEqual('"","Wong","Edward","","is a girl"', result[1])

        # History
        hline = self.get_alone_element(HistoryLine.objects.exclude(id__in=existing_hline_ids))
        self.assertListEqual(
            [1, hf.name, efilter.name], hline.modifications,
        )
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-mass_export">{}<div>',
                _('Export of «%(counted_instances)s» (view «%(view)s» & filter «%(filter)s»)') % {
                    'counted_instances': _('{count} {model}').format(
                        count=1,
                        model='Test Contact',
                    ),
                    'view': hf.name,
                    'filter': efilter.name,
                },
            ),
            html_history_registry.line_explainers([hline], user)[0].render(),
        )

    def test_xls_export01(self):
        user = self.login_as_root_and_get()
        cells = self._build_hf_n_contacts(user=user).cells
        existing_fileref_ids = [*FileRef.objects.values_list('id', flat=True)]

        response = self.assertGET200(
            self._build_contact_dl_url(doc_type='xls'), follow=True,
        )

        it = iter(XlrdReader(None, file_contents=b''.join(response.streaming_content)))
        self.assertListEqual(next(it), [hfi.title for hfi in cells])
        self.assertListEqual(next(it), ['', 'Black', 'Jet', 'Bebop', ''])
        self.assertListEqual(next(it), ['', 'Spiegel', 'Spike', 'Bebop/Swordfish', ''])
        self.assertListEqual(next(it), ['', 'Valentine', 'Faye', '', 'is a girl/is beautiful'])
        self.assertListEqual(next(it), ['', 'Wong', 'Edward', '', 'is a girl'])
        with self.assertRaises(StopIteration):
            next(it)

        # FileRef
        fileref = self.get_alone_element(FileRef.objects.exclude(id__in=existing_fileref_ids))
        self.assertTrue(fileref.temporary)
        self.assertEqual('fakecontact.xls', fileref.basename)
        self.assertEqual(user, fileref.user)
        self.assertEqual(_('Mass export'), fileref.description)

        fullpath = Path(fileref.filedata.path)
        self.assertTrue(fullpath.exists(), f'<{fullpath}> does not exists ?!')
        self.assertEqual(Path(settings.MEDIA_ROOT, 'xls'), fullpath.parent)

    @override_settings(LANGUAGE_CODE='fr')
    def test_xls_export02(self):
        "Other CT, other type of fields."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(name='Bebop')
        orga02 = create_orga(
            name='Swordfish', subject_to_vat=False,
            creation_date=date(year=2016, month=7, day=5),
        )

        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cells = [
            build_cell(name='name'),
            build_cell(name='subject_to_vat'),
            build_cell(name='creation_date'),
        ]

        hf = HeaderFilter.objects.proxy(
            id='test-hf_orga', name='Organisation view',
            model=FakeOrganisation, cells=cells,
        ).get_or_create()[0]

        response = self.assertGET200(
            self._build_dl_url(
                FakeOrganisation,
                doc_type='xls',
                list_url=FakeOrganisation.get_lv_absolute_url(),
                hfilter_id=hf.id,
            ),
            follow=True,
        )

        it = iter(XlrdReader(None, file_contents=b''.join(response.streaming_content)))
        self.assertListEqual(next(it), [hfi.title for hfi in cells])
        self.assertListEqual(next(it), [orga01.name, _('Yes'), ''])
        self.assertListEqual(
            next(it),
            [orga02.name, _('No'), orga02.creation_date.strftime('%d/%m/%Y')],
        )
        with self.assertRaises(StopIteration):
            next(it)

    def test_xlsx_export(self):
        user = self.login_as_root_and_get()
        cells = self._build_hf_n_contacts(user=user).cells
        existing_fileref_ids = [*FileRef.objects.values_list('id', flat=True)]

        response = self.assertGET200(
            self._build_contact_dl_url(doc_type='xlsx'), follow=True,
        )
        wb = load_workbook(
            filename=BytesIO(b''.join(response.streaming_content)),
            read_only=True,
        )
        self.assertListEqual(
            [
                [hfi.title for hfi in cells],
                [None, 'Black',     'Jet',    'Bebop',           None],
                [None, 'Spiegel',   'Spike',  'Bebop/Swordfish', None],
                [None, 'Valentine', 'Faye',   None,              'is a girl/is beautiful'],
                [None, 'Wong',      'Edward', None,              'is a girl'],
            ],
            [[tcell.value for tcell in row] for row in wb.active.rows],
        )

        # FileRef
        fileref = self.get_alone_element(FileRef.objects.exclude(id__in=existing_fileref_ids))
        self.assertTrue(fileref.temporary)
        self.assertEqual('fakecontact.xlsx', fileref.basename)
        self.assertEqual(user, fileref.user)
        self.assertEqual(_('Mass export'), fileref.description)

        fullpath = Path(fileref.filedata.path)
        self.assertTrue(fullpath.exists(), f'<{fullpath}> does not exists?!')
        self.assertEqual(Path(settings.MEDIA_ROOT, 'xlsx'), fullpath.parent)

    def test_print_integer01(self):
        "No choices."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        for name, capital in (('Bebop', 1000), ('Swordfish', 20000), ('Redtail', None)):
            create_orga(name=name, capital=capital)

        hf = HeaderFilter.objects.proxy(
            id='test-hf_orga', name='Organisation view', model=FakeOrganisation,
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'capital'),
            ],
        ).get_or_create()[0]

        lv_url = FakeOrganisation.get_lv_absolute_url()
        response = self.assertGET200(
            self._build_dl_url(FakeOrganisation, list_url=lv_url, hfilter_id=hf.id),
            follow=True,
        )

        lines = {force_str(line) for line in response.content.splitlines()}
        self.assertIn('"Bebop","1000"', lines)
        self.assertIn('"Swordfish","20000"', lines)
        self.assertIn('"Redtail",""', lines)

    def test_print_integer02(self):
        "Field with choices."
        user = self.login_as_root_and_get()

        invoice = FakeInvoice.objects.create(
            user=user, name='Invoice', expiration_date=date(year=2012, month=12, day=15),
        )

        create_pline = partial(FakeInvoiceLine.objects.create, user=user, linked_invoice=invoice)
        create_pline(item='Bebop',     discount_unit=FakeInvoiceLine.Discount.PERCENT)
        create_pline(item='Swordfish', discount_unit=FakeInvoiceLine.Discount.AMOUNT)

        hf = HeaderFilter.objects.proxy(
            id='test-hf_fakeinvoiceline', name='InvoiceLine view',
            model=FakeInvoiceLine,
            cells=[
                (EntityCellRegularField, 'item'),
                (EntityCellRegularField, 'discount_unit'),
            ],
        ).get_or_create()[0]
        response = self.assertGET200(
            self._build_dl_url(
                FakeInvoiceLine,
                list_url=FakeInvoiceLine.get_lv_absolute_url(),
                hfilter_id=hf.id,
                sort_key='regular_field-item',
                sort_order='ASC',
            ),
            follow=True,
        )

        lines = {force_str(line) for line in response.content.splitlines()}
        self.assertIn(f'''"Bebop","{_('Percent')}"''',    lines)
        self.assertIn(f'''"Swordfish","{_('Amount')}"''', lines)

    @override_settings(PAGE_SIZES=[10], DEFAULT_PAGE_SIZE_IDX=0)
    def test_quick_search(self):
        user = self.login_as_root_and_get()

        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact_test_quick_search', name='Contact view',
            model=FakeContact,
            cells=[
                (EntityCellRegularField, 'phone'),
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'first_name'),
            ],
        ).get_or_create()[0]

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Spike', last_name='Spiegel',   phone='123233')
        create_contact(first_name='Jet',   last_name='Black',     phone='123455')
        create_contact(first_name='Faye',  last_name='Valentine', phone='678678')

        # ----------------------
        response = self.assertGET200(self._build_contact_dl_url(
            hfilter_id=hf.id, **{'search-regular_field-phone': '123'}
        ))
        self.assertListEqual(
            [
                '"123455","Black","Jet"',
                '"123233","Spiegel","Spike"',
            ],
            # NB: slice to remove the header
            [force_str(line) for line in response.content.splitlines()[1:]],
        )

    @override_settings(PAGE_SIZES=[10], DEFAULT_PAGE_SIZE_IDX=0)
    def test_sorting(self):
        user = self.login_as_root_and_get()

        hf = HeaderFilter.objects.proxy(
            id='test-hf_contact_test_sorting', name='Contact view',
            model=FakeContact,
            cells=[
                (EntityCellRegularField, 'phone'),
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'first_name'),
            ],
        ).get_or_create()[0]

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Spike', last_name='Spiegel',   phone='123233')
        create_contact(first_name='Jet',   last_name='Black',     phone='123455')
        create_contact(first_name='Faye',  last_name='Valentine', phone='678678')

        response = self.assertGET200(self._build_contact_dl_url(
            hfilter_id=hf.id,
            sort_key='regular_field-last_name',
            sort_order='DESC',
            **{'search-regular_field-phone': '123'}
        ))
        self.assertListEqual(
            [
                '"123233","Spiegel","Spike"',
                '"123455","Black","Jet"',
            ],
            # NB: slice to remove the header
            [force_str(line) for line in response.content.splitlines()[1:]],
        )

    def test_distinct(self):
        user = self.login_as_root_and_get()

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        camp1 = create_camp(name='Camp#1')
        camp2 = create_camp(name='Camp#2')
        create_camp(name='Camp#3')

        create_ml = partial(FakeMailingList.objects.create, user=user)

        ml1 = create_ml(name='Bebop staff')
        ml2 = create_ml(name='Mafia staff')

        camp1.mailing_lists.set([ml1, ml2])
        camp2.mailing_lists.set([ml1])

        hf = HeaderFilter.objects.proxy(
            id='test_hf', name='Campaign view', model=FakeEmailCampaign,
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'mailing_lists'),
            ],
        ).get_or_create()[0]

        response = self.assertGET200(self._build_dl_url(
            FakeEmailCampaign,
            hfilter_id=hf.id,
            sort_key='regular_field-name',
            **{'search-regular_field-mailing_lists': 'staff'}
        ))
        self.assertListEqual(
            [
                f'"{camp1.name}","{ml1.name}/{ml2.name}"',  # Only once
                f'"{camp2.name}","{ml1.name}"',
            ],
            # NB: slice to remove the header
            [force_str(line) for line in response.content.splitlines()[1:]],
        )

    def test_no_order(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        c1 = create_contact(first_name='Spike', last_name='Spiegel', phone='123233')
        c2 = create_contact(first_name='Jet',   last_name='Black',   phone='123455')

        create_language = Language.objects.create
        l1 = create_language(name='English')  # code='EN'
        l2 = create_language(name='Japanese')  # code='JP'

        c1.languages.set([l1])
        c2.languages.set([l2])

        hf = HeaderFilter.objects.proxy(
            id='test_hf', name='Not orderable view', model=FakeContact,
            cells=[(EntityCellRegularField, 'languages')],
        ).get_or_create()[0]
        response = self.assertGET200(self._build_contact_dl_url(
            hfilter_id=hf.id,
            # sort_key='regular_field-...',
            sort_order='ASC',
            **{'search-regular_field-phone': '123'}
        ))
        self.assertListEqual(
            [f'"{l1.name}"', f'"{l2.name}"'],
            [force_str(line) for line in response.content.splitlines()[1:]],
        )
