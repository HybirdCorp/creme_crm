from datetime import date
from decimal import Decimal
from functools import partial
from uuid import uuid4

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.formats import number_format
from django.utils.translation import gettext as _
from django.utils.translation import override as override_language

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldInteger,
    EntityFilter,
    FakeContact,
)
from creme.creme_core.models import FakeDocument as FakeCoreDocument
from creme.creme_core.models import FakeEmailCampaign
from creme.creme_core.models import FakeFolder as FakeCoreFolder
from creme.creme_core.models import (
    FakeFolderCategory,
    FakeImage,
    FakeImageCategory,
    FakeInvoice,
    FakeLegalForm,
    FakeMailingList,
    FakeOrganisation,
    FakePosition,
    Relation,
    RelationType,
)
from creme.creme_core.tests.fake_constants import (
    FAKE_REL_OBJ_BILL_ISSUED,
    FAKE_REL_OBJ_EMPLOYED_BY,
)
from creme.reports.constants import (
    RFT_AGG_CUSTOM,
    RFT_AGG_FIELD,
    RFT_CUSTOM,
    RFT_FIELD,
    RFT_FUNCTION,
    RFT_RELATED,
    RFT_RELATION,
)
from creme.reports.models import (
    FakeReportsDocument,
    FakeReportsFolder,
    Field,
    Guild,
)
from creme.reports.tests.base import (
    BaseReportsTestCase,
    Report,
    skipIfCustomReport,
)


@skipIfCustomReport
class ReportTestCase(BaseReportsTestCase):
    def test_clone(self):
        user = self.login_as_root_and_get()
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Mihana family', FakeContact, is_custom=True,
        )
        report = Report.objects.create(
            user=user, name='Contact report', ct=FakeContact, filter=efilter,
        )

        create_field = partial(Field.objects.create, report=report)
        rfield1 = create_field(name='last_name',             order=1, type=RFT_FIELD)
        rfield2 = create_field(name='get_pretty_properties', order=2, type=RFT_FUNCTION)

        cloned_report = self.clone(report)
        self.assertIsInstance(cloned_report, Report)
        self.assertNotEqual(report.id, cloned_report.id)
        self.assertEqual(report.name,   cloned_report.name)
        self.assertEqual(report.ct,     cloned_report.ct)
        self.assertEqual(report.filter, cloned_report.filter)

        rfields = cloned_report.fields.all()
        self.assertEqual(2, len(rfields))

        def check_clone(source_field, cloned_field):
            self.assertNotEqual(source_field.id, cloned_field.id)
            self.assertEqual(source_field.name,       cloned_field.name)
            self.assertEqual(source_field.order,      cloned_field.order)
            self.assertEqual(source_field.type,       cloned_field.type)
            self.assertEqual(source_field.selected,   cloned_field.selected)
            self.assertEqual(source_field.sub_report, cloned_field.sub_report)

        check_clone(rfield1, rfields[0])
        check_clone(rfield2, rfields[1])

    # def test_clone__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #     efilter = EntityFilter.objects.smart_update_or_create(
    #         'test-filter', 'Mihana family', FakeContact, is_custom=True,
    #     )
    #     report = Report.objects.create(
    #         user=user, name='Contact report', ct=FakeContact, filter=efilter,
    #     )
    #
    #     create_field = partial(Field.objects.create, report=report)
    #     rfield1 = create_field(name='last_name',             order=1, type=RFT_FIELD)
    #     rfield2 = create_field(name='get_pretty_properties', order=2, type=RFT_FUNCTION)
    #
    #     cloned_report = report.clone()
    #     self.assertIsInstance(cloned_report, Report)
    #     self.assertNotEqual(report.id, cloned_report.id)
    #     self.assertEqual(report.name,   cloned_report.name)
    #     self.assertEqual(report.ct,     cloned_report.ct)
    #     self.assertEqual(report.filter, cloned_report.filter)
    #
    #     rfields = cloned_report.fields.all()
    #     self.assertEqual(2, len(rfields))
    #
    #     def check_clone(source_field, cloned_field):
    #         self.assertNotEqual(source_field.id, cloned_field.id)
    #         self.assertEqual(source_field.name,       cloned_field.name)
    #         self.assertEqual(source_field.order,      cloned_field.order)
    #         self.assertEqual(source_field.type,       cloned_field.type)
    #         self.assertEqual(source_field.selected,   cloned_field.selected)
    #         self.assertEqual(source_field.sub_report, cloned_field.sub_report)
    #
    #     check_clone(rfield1, rfields[0])
    #     check_clone(rfield2, rfields[1])

    def test_delete_efilter(self):
        "The filter should not be deleted."
        user = self.login_as_root_and_get()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Mihana family', FakeContact, is_custom=True,
        )
        report = self._create_simple_contacts_report(
            user=user, name='My awesome report', efilter=efilter,
        )

        url = reverse('creme_core__delete_efilter', args=(efilter.id,))
        self.assertPOST409(url, follow=True)
        self.assertStillExists(efilter)
        self.assertStillExists(report)

        # AJAX version
        self.assertPOST409(
            url, follow=True, headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        self.assertStillExists(efilter)
        self.assertStillExists(report)


@skipIfCustomReport
class FetchTestCase(BaseReportsTestCase):
    def assertHeaders(self, names, report):
        self.assertEqual(names, [f.name for f in report.get_children_fields_flat()])

    def _aux_fetch_persons(
            self,
            user,
            create_contacts=True,
            create_relations=True,
            report_4_contact=True):
        if create_contacts:
            create_contact = partial(FakeContact.objects.create, user=user)
            self.ned    = create_contact(first_name='Eddard', last_name='Stark')
            self.robb   = create_contact(first_name='Robb',   last_name='Stark')
            self.tyrion = create_contact(first_name='Tyrion', last_name='Lannister')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        self.starks     = create_orga(name='House Stark')
        self.lannisters = create_orga(name='House Lannister')

        if create_contacts and create_relations:
            create_rel = partial(
                Relation.objects.create,
                type_id=FAKE_REL_OBJ_EMPLOYED_BY, user=user,
            )
            create_rel(subject_entity=self.starks, object_entity=self.ned)
            create_rel(subject_entity=self.starks, object_entity=self.robb)
            create_rel(subject_entity=self.lannisters, object_entity=self.tyrion)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Houses', FakeOrganisation, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.ISTARTSWITH,
                    field_name='name', values=['House '],
                ),
            ],
        )

        create_report = partial(Report.objects.create, user=user, filter=None)
        create_field = partial(
            Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD,
        )

        if report_4_contact:
            self.report_contact = report = create_report(
                name='Report on Contacts', ct=self.ct_contact,
            )

            create_field(report=report, name='last_name',  order=1)
            create_field(report=report, name='first_name', order=2)

        self.report_orga = create_report(
            name='Report on Organisations', ct=self.ct_orga, filter=efilter,
        )
        create_field(report=self.report_orga, name='name', order=1)

    def _aux_fetch_documents(self, *, user, efilter=None, selected=True):
        create_field = partial(
            Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD,
        )

        self.folder_report = Report.objects.create(
            name='Folders report', user=user,
            ct=self.ct_folder,
            filter=efilter,
        )
        create_field(report=self.folder_report, name='title',       order=1)
        create_field(report=self.folder_report, name='description', order=2)

        self.doc_report = self._create_simple_documents_report(user=user)
        create_field(
            report=self.doc_report, name='linked_folder__title', order=3,
            sub_report=self.folder_report, selected=selected,
        )

        create_folder = partial(FakeReportsFolder.objects.create, user=user)
        self.folder1 = create_folder(title='Internal')
        self.folder2 = create_folder(title='External', description='Boring description')

        create_doc = partial(FakeReportsDocument.objects.create, user=user)
        self.doc1 = create_doc(title='Doc#1', linked_folder=self.folder1, description='Blablabla')
        self.doc2 = create_doc(title='Doc#2', linked_folder=self.folder2)

    def _aux_fetch_m2m(self):
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.create
        self.ptype1 = create_ptype(text='Important')
        self.ptype2 = create_ptype(text='Not important')

        self.report_camp = report_camp = Report.objects.create(
            user=user, name='Campaign Report', ct=FakeEmailCampaign,
        )
        create_field1 = partial(Field.objects.create, report=report_camp, type=RFT_FIELD)
        create_field1(name='name',                order=1)
        create_field1(name='mailing_lists__name', order=2)

        self.report_ml = report_ml = Report.objects.create(
            user=user,
            name='Campaign ML',
            ct=FakeMailingList,
        )
        create_field2 = partial(Field.objects.create, report=report_ml)
        create_field2(name='name',                  type=RFT_FIELD,    order=1)
        create_field2(name='get_pretty_properties', type=RFT_FUNCTION, order=2)

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        self.camp1 = create_camp(name='Camp#1')
        self.camp2 = create_camp(name='Camp#2')
        self.camp3 = create_camp(name='Camp#3')  # Empty one

        create_ml = partial(FakeMailingList.objects.create, user=user)
        self.ml1 = ml1 = create_ml(name='ML#1')
        self.ml2 = ml2 = create_ml(name='ML#2')
        self.ml3 = ml3 = create_ml(name='ML#3')

        self.camp1.mailing_lists.set([ml1, ml2])
        self.camp2.mailing_lists.set([ml3])

        create_prop = CremeProperty.objects.create
        create_prop(type=self.ptype1, creme_entity=ml1)
        create_prop(type=self.ptype2, creme_entity=ml2)

    def _aux_fetch_related(self, *, user, other_user,
                           select_doc_report=None, invalid_one=False):
        create_report = partial(Report.objects.create, user=user, filter=None)
        self.doc_report = (
            self._create_simple_documents_report(user=user)
            if select_doc_report is not None else
            None
        )
        self.folder_report = create_report(name='Report on folders', ct=self.ct_folder)

        create_field = partial(
            Field.objects.create,
            report=self.folder_report,
            type=RFT_FIELD,
        )
        create_field(name='title', order=1)
        create_field(
            name='fakereportsdocument', order=2,
            type=RFT_RELATED,
            sub_report=self.doc_report, selected=select_doc_report or False,
        )

        if invalid_one:
            create_field(name='invalid', order=3, type=RFT_RELATED)

        create_folder = partial(FakeReportsFolder.objects.create, user=user)
        self.folder1 = create_folder(title='External')
        self.folder2 = create_folder(title='Internal')

        create_doc = partial(FakeReportsDocument.objects.create, user=user)
        self.doc11 = create_doc(
            title='Doc#1-1', linked_folder=self.folder1, description='Boring !',
        )
        self.doc12 = create_doc(
            title='Doc#1-2', linked_folder=self.folder1, user=other_user,
        )
        self.doc21 = create_doc(title='Doc#2-1', linked_folder=self.folder2)

    def _aux_fetch_aggregate(self, invalid_ones=False):
        user = self.login_as_root_and_get()
        self._aux_fetch_persons(user=user, create_contacts=False, report_4_contact=False)

        # Should not be used in aggregate
        self.guild = FakeOrganisation.objects.create(
            name='Guild of merchants', user=user, capital=700,
        )

        create_cf = partial(CustomField.objects.create, content_type=self.ct_orga)
        self.cf = cf = create_cf(name='Gold', field_type=CustomField.INT)
        str_cf = create_cf(name='Motto', field_type=CustomField.STR)

        fmt = '{}__max'.format
        create_field = partial(Field.objects.create, report=self.report_orga)
        create_field(name='capital__sum', order=2, type=RFT_AGG_FIELD)
        create_field(name=fmt(cf.uuid),   order=3, type=RFT_AGG_CUSTOM)

        if invalid_ones:
            # Invalid CustomField id
            create_field(name=fmt(uuid4()), order=4, type=RFT_AGG_CUSTOM)
            # Invalid aggregation
            create_field(name='capital__invalid', order=5, type=RFT_AGG_FIELD)
            # Invalid field (unknown)
            create_field(name='invalid__sum', order=6, type=RFT_AGG_FIELD)
            # Invalid field (bad type)
            create_field(name='name__sum', order=7, type=RFT_AGG_FIELD)
            # Invalid CustomField (bad type)
            create_field(name=fmt(str_cf.uuid), order=8, type=RFT_AGG_CUSTOM)
            # Invalid string
            create_field(name=f'{cf.uuid}__additionalarg__max', order=9, type=RFT_AGG_CUSTOM)

    def _create_contacts_n_images(self, user, other_user):
        create_img = FakeImage.objects.create
        self.ned_face  = create_img(name='Ned face',  user=other_user)
        self.aria_face = create_img(name='Aria face', user=user)

        create_contact = partial(FakeContact.objects.create, user=user)
        self.ned  = create_contact(first_name='Eddard', last_name='Stark', image=self.ned_face)
        self.robb = create_contact(first_name='Robb',   last_name='Stark', user=other_user)
        self.aria = create_contact(first_name='Aria',   last_name='Stark', image=self.aria_face)

        self.efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Starks', FakeContact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name',
                    values=[self.ned.last_name],
                ),
            ],
        )

    def test_regular_field(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        for i in range(5):
            create_contact(last_name=f'Mister {i}')

        create_contact(last_name='Mister X', is_deleted=True)

        report = self._create_simple_contacts_report(user=user, name='Contacts report')
        self.assertListEqual(
            [
                [ln]
                for ln in FakeContact.objects
                                     .filter(is_deleted=False)
                                     .values_list('last_name', flat=True)
            ],
            report.fetch_all_lines(),
        )

    # @override_settings(USE_L10N=True)
    @override_language('en')
    def test_regular_field__complex(self):
        "FK, date, filter, invalid one."
        user = self.login_as_root_and_get()

        self._aux_fetch_persons(
            user=user, report_4_contact=False, create_contacts=False, create_relations=False,
        )

        report = self.report_orga
        create_field = partial(
            Field.objects.create,
            report=report, selected=False, sub_report=None, type=RFT_FIELD,
        )
        create_field(name='user__username',    order=2)
        create_field(name='legal_form__title', order=3)
        create_field(name='creation_date',     order=4)
        create_field(name='invalid',           order=5)
        create_field(name='user__invalid',     order=6)
        create_field(name='dontcare',          order=7, type=1000)

        self.assertEqual(4, len(report.columns))

        starks = self.starks
        starks.legal_form = lform = FakeLegalForm.objects.get_or_create(title='Hord')[0]
        starks.creation_date = date(year=2013, month=9, day=24)
        starks.save()

        username = user.username
        self.assertListEqual(
            [
                [
                    self.lannisters.name,
                    username,
                    '',
                    '',
                ],
                [
                    starks.name,
                    username,
                    lform.title,
                    starks.creation_date.strftime('%Y-%m-%d'),
                ],
            ],
            report.fetch_all_lines(),
        )

    def test_regular_field__view_perms(self):
        "View credentials."
        user = self.login_as_basic_user()
        other_user = self.get_root_user()

        self._aux_fetch_persons(
            user=user, report_4_contact=False, create_contacts=False, create_relations=False,
        )

        Field.objects.create(
            report=self.report_orga, name='image__name',
            order=2, selected=False, sub_report=None, type=RFT_FIELD,
        )

        baratheons = FakeOrganisation.objects.create(user=other_user, name='House Baratheon')
        self.assertFalse(user.has_perm_to_view(baratheons))

        create_img     = FakeImage.objects.create
        starks_img     = create_img(name='Stark emblem',     user=user)
        lannisters_img = create_img(name='Lannister emblem', user=other_user)
        self.assertTrue(user.has_perm_to_view(starks_img))
        self.assertFalse(user.has_perm_to_view(lannisters_img))

        self.starks.image = starks_img
        self.starks.save()

        self.lannisters.image = lannisters_img
        self.lannisters.save()

        fetch_all_lines = self.report_orga.fetch_all_lines
        lines = [
            [baratheons.name,      ''],
            [self.lannisters.name, lannisters_img.name],
            [self.starks.name,     starks_img.name],
        ]
        self.assertEqual(lines, fetch_all_lines())
        self.assertEqual(lines, fetch_all_lines(user=other_user))  # Superuser

        lines.pop(0)
        lines[0][1] = settings.HIDDEN_VALUE  # 'lannisters_img' not visible
        self.assertEqual(lines, fetch_all_lines(user=user))

    def test_fk__sub_report__no_filter(self):
        "Sub report: no sub-filter."
        user = self.login_as_root_and_get()

        self._aux_fetch_documents(user=user)
        self.assertHeaders(['title', 'description', 'title', 'description'], self.doc_report)

        doc1 = self.doc1
        folder2 = self.folder2
        self.assertEqual(
            [
                [doc1.title,      doc1.description, self.folder1.title, ''],
                [self.doc2.title, '',               folder2.title,      folder2.description],
            ],
            self.doc_report.fetch_all_lines(),
        )

    def test_fk__sub_report__filter(self):
        "Sub report: sub-filter."
        user = self.login_as_root_and_get()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Internal folders', FakeReportsFolder,
            is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeReportsFolder,
                    operator=operators.ISTARTSWITH,
                    field_name='title', values=['Inter'],
                ),
            ],
        )

        self._aux_fetch_documents(user=user, efilter=efilter)

        doc1 = self.doc1
        self.assertListEqual(
            [
                [doc1.title,      doc1.description, self.folder1.title, ''],
                [self.doc2.title, '',               '',                 ''],
            ],
            self.doc_report.fetch_all_lines(),
        )

    def test_fk__sub_report__flattened(self):
        "Sub report (flattened)."
        user = self.login_as_root_and_get()
        self._aux_fetch_documents(user=user, selected=False)

        doc1 = self.doc1
        folder2 = self.folder2
        fmt = f"{_('Title')}: %s/{_('Description')}: %s"
        self.assertListEqual(
            [
                [doc1.title,      doc1.description, fmt % (self.folder1.title, '')],
                [self.doc2.title, '',               fmt % (folder2.title, folder2.description)],
            ],
            self.doc_report.fetch_all_lines(),
        )

    def test_fk__no_entity(self):
        "Not Entity, no (sub) attribute."
        user = self.login_as_root_and_get()

        self._aux_fetch_persons(
            user=user, report_4_contact=False, create_contacts=False, create_relations=False,
        )
        starks = self.starks

        starks.legal_form = lform = FakeLegalForm.objects.get_or_create(title='Hord')[0]
        starks.save()

        report = self.report_orga

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        lf_field   = create_field(name='legal_form', order=2)
        user_field = create_field(name='user',       order=3)

        self.assertEqual(_('Legal form'), lf_field.title)
        self.assertEqual(_('Owner user'), user_field.title)

        user_str = str(user)
        self.assertListEqual(
            [
                [self.lannisters.name, '',          user_str],
                [starks.name,          lform.title, user_str],
            ],
            report.fetch_all_lines(),
        )

    def test_fk__depth2(self):
        "FK with depth=2."
        user = self.login_as_root_and_get()

        cat = FakeFolderCategory.objects.create(name='Maps')

        create_folder = partial(FakeCoreFolder.objects.create, user=user)
        folder1 = create_folder(title='Earth maps', category=cat)
        folder2 = create_folder(title="Faye's pix")

        create_doc = partial(FakeCoreDocument.objects.create, user=user)
        doc1 = create_doc(title='Japan map',   linked_folder=folder1)
        doc2 = create_doc(title='Mars city 1', linked_folder=folder2)

        report = Report.objects.create(
            name='Docs report', user=user, ct=FakeCoreDocument,
        )

        create_field = partial(
            Field.objects.create, report=report,
            selected=False, sub_report=None, type=RFT_FIELD,
        )
        create_field(name='title',                   order=1)
        create_field(name='linked_folder__category', order=2)

        self.assertListEqual(
            [
                [doc1.title, cat.name],
                [doc2.title, ''],
            ],
            report.fetch_all_lines(),
        )

    def test_m2m__depth2(self):
        "M2M at <depth=2>."
        user = self.login_as_root_and_get()

        create_cat = FakeImageCategory.objects.create
        cat1 = create_cat(name='Selfie')
        cat2 = create_cat(name='Official')

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='Faye pix')
        img2 = create_img(name='Spike pix')
        img3 = create_img(name='Jet pix')

        img1.categories.set([cat1, cat2])
        img2.categories.set([cat1])

        description = 'Bebop member'
        create_contact = partial(
            FakeContact.objects.create,
            user=user, description=description,
        )
        faye  = create_contact(last_name='Valentine', image=img1)
        spike = create_contact(last_name='Spiegel',   image=img2)
        jet   = create_contact(last_name='Black',     image=img3)
        ed    = create_contact(last_name='Wong')

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Bebop member', FakeContact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='description',
                    values=[description],
                ),
            ],
        )

        report = Report.objects.create(
            name='Contact report', user=user, filter=efilter, ct=self.ct_contact,
        )

        create_field = partial(
            Field.objects.create, report=report,
            selected=False, sub_report=None, type=RFT_FIELD,
        )
        create_field(name='last_name',         order=1)
        create_field(name='image__categories', order=2)

        self.assertListEqual(
            [
                [jet.last_name,   ''],
                [spike.last_name, cat1.name],
                [faye.last_name,  f'{cat2.name}/{cat1.name}'],
                [ed.last_name,    ''],
            ],
            report.fetch_all_lines(),
        )

    def test_m2m__depth2__not_entity(self):
        "M2M at <depth=2>."
        user = self.login_as_root_and_get()

        create_positon = FakePosition.objects.create
        leader    = create_positon(title='Leader')
        side_kick = create_positon(title='Side kick')

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(last_name='Merchants#1', position=leader)
        contact2 = create_contact(last_name='Merchants#2', position=side_kick)
        contact3 = create_contact(last_name='Merchants#3')
        contact4 = create_contact(last_name='Assassin', position=leader)

        create_guild = partial(Guild.objects.create, user=user)
        guild1 = create_guild(name='Guild of merchants')
        guild2 = create_guild(name='Guild of assassins')
        guild3 = create_guild(name='Guild of mercenaries')

        guild1.members.set([contact1, contact2, contact3])
        guild2.members.set([contact4])

        report = Report.objects.create(name='Guilds report', user=user, ct=Guild)

        create_field = partial(
            Field.objects.create,
            report=report, selected=False, sub_report=None, type=RFT_FIELD,
        )
        create_field(name='name',              order=1)
        create_field(name='members__position', order=2)

        self.assertListEqual(
            [
                [guild2.name, leader.title],
                [guild3.name, ''],
                [guild1.name, f'{leader.title}, {side_kick.title}, '],
            ],
            report.fetch_all_lines(),
        )

    def test_m2m__no_sub_report(self):
        user = self.login_as_root_and_get()

        report = Report.objects.create(
            user=user, name='Campaign Report', ct=FakeEmailCampaign,
        )
        create_field = partial(Field.objects.create, report=report)
        create_field(name='name',                type=RFT_FIELD, order=1)
        create_field(name='mailing_lists__name', type=RFT_FIELD, order=2)

        create_camp = partial(FakeEmailCampaign.objects.create, user=user)
        camp1 = create_camp(name='Camp#1')
        camp2 = create_camp(name='Camp#2')

        create_ml = partial(FakeMailingList.objects.create, user=user)
        camp1.mailing_lists.set([create_ml(name='ML#1'), create_ml(name='ML#2')])
        camp2.mailing_lists.set([create_ml(name='ML#3')])

        self.assertHeaders(['name', 'mailing_lists__name'], report)
        self.assertListEqual(
            [
                [camp1.name, 'ML#1, ML#2'],
                [camp2.name, 'ML#3'],
            ],
            report.fetch_all_lines(),
        )

    def test_m2m__sub_report__expanded(self):
        self._aux_fetch_m2m()

        report_camp = self.report_camp
        report_ml = self.report_ml

        name1 = self.camp1.name
        name2 = self.camp2.name
        name3 = self.camp3.name

        ml1 = self.ml1
        ml2 = self.ml2
        ml3 = self.ml3

        ptype1 = self.ptype1
        ptype2 = self.ptype2

        self.assertHeaders(['name', 'mailing_lists__name'], report_camp)
        self.assertListEqual(
            [
                [name1, f'{ml1.name}, {ml2.name}'],
                [name2, ml3.name],
                [name3, ''],
            ],
            report_camp.fetch_all_lines(),
        )

        self.assertListEqual(
            [[ml1.name, ptype1.text], [ml2.name, ptype2.text], [ml3.name, '']],
            report_ml.fetch_all_lines(),
        )

        # Let's go for the sub-report
        rfield = report_camp.fields.get(name='mailing_lists__name')
        rfield.sub_report = report_ml
        rfield.selected = True
        rfield.save()

        self.assertListEqual(
            [ContentType.objects.get_for_model(FakeMailingList)],
            [*rfield.hand.get_linkable_ctypes()],
        )

        report_camp = self.refresh(report_camp)
        self.assertHeaders(['name', 'name', 'get_pretty_properties'], report_camp)
        self.assertListEqual(
            [
                [name1, ml1.name, ptype1.text],
                [name1, ml2.name, ptype2.text],
                [name2, ml3.name, ''],
                [name3, '',       ''],
            ],
            report_camp.fetch_all_lines(),
        )

    def test_m2m__sub_report__not_expanded(self):
        self._aux_fetch_m2m()

        report_camp = self.report_camp

        # Let's go for the sub-report
        rfield = report_camp.fields.get(name='mailing_lists__name')
        rfield.sub_report = self.report_ml
        rfield.selected = False
        rfield.save()

        report_camp = self.refresh(report_camp)
        self.assertHeaders(['name', 'mailing_lists__name'], report_camp)

        fmt = f"{_('Name of the mailing list')}: %s/{_('Properties')}: %s"
        self.assertListEqual(
            [
                [
                    self.camp1.name,
                    '{}, {}'.format(
                        fmt % (self.ml1.name, self.ptype1.text),
                        fmt % (self.ml2.name, self.ptype2.text),
                    ),
                ],
                [self.camp2.name, fmt % (self.ml3.name, '')],
                [self.camp3.name, ''],
            ],
            report_camp.fetch_all_lines(),
        )

    def test_m2m__not_entity(self):
        "Not CremeEntity model."
        user = self.login_as_root_and_get()

        report = self._create_image_report(user=user)

        create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
        rfield1 = create_field(name='categories__name', order=3)
        rfield2 = create_field(name='categories',       order=4)

        self.assertIsNone(rfield1.hand.get_linkable_ctypes())
        self.assertIsNone(rfield2.hand.get_linkable_ctypes())

        self.assertEqual(f"{_('Categories')} - {_('Name')}", rfield1.title)
        self.assertEqual(_('Categories'),                    rfield2.title)

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='Img#1', description='Pretty picture')
        img2 = create_img(name='Img#2')

        create_cat = FakeImageCategory.objects.create
        cat1 = create_cat(name='Photo of contact')
        cat2 = create_cat(name='Photo of product')

        img1.categories.set([cat1, cat2])

        cats_str = f'{cat1.name}, {cat2.name}'
        self.assertListEqual(
            [
                [img1.name, img1.description, cats_str, cats_str],
                [img2.name, '',               '',       ''],
            ],
            report.fetch_all_lines(),
        )

    def test_custom_fields(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        ned  = create_contact(first_name='Eddard', last_name='Stark')
        robb = create_contact(first_name='Robb',   last_name='Stark')
        aria = create_contact(first_name='Aria',   last_name='Stark')

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Starks', FakeContact, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact, field_name='last_name',
                    operator=operators.IEQUALS, values=[ned.last_name],
                ),
            ],
        )

        cf = self._create_cf_int()
        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=ned,  value=190)
        create_cfval(entity=aria, value=150)

        report = Report.objects.create(
            user=user,
            name='Contacts with CField',
            ct=FakeContact,
            filter=efilter,
        )

        create_field = partial(Field.objects.create, report=report)
        create_field(name='first_name', type=RFT_FIELD,  order=1)
        create_field(name=str(cf.uuid), type=RFT_CUSTOM, order=2)
        create_field(name=str(uuid4()), type=RFT_CUSTOM, order=3)

        report = self.refresh(report)
        self.assertEqual(2, len(report.columns))
        self.assertEqual(2, report.fields.count())
        self.assertListEqual(
            [
                [aria.first_name, '150'],
                [ned.first_name,  '190'],
                [robb.first_name, ''],
            ],
            report.fetch_all_lines(),
        )

    def test_custom_fields__in_sub_report(self):
        "In FK, credentials."
        user = self.login_as_basic_user()

        self._create_contacts_n_images(user=user, other_user=self.get_root_user())
        ned_face = self.ned_face
        aria_face = self.aria_face

        cf = CustomField.objects.create(
            content_type=self.ct_image,
            name='Popularity', field_type=CustomField.INT,
        )

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=cf)
        create_cfval(entity=ned_face,  value=190)
        create_cfval(entity=aria_face, value=150)

        create_report = partial(Report.objects.create, user=user, filter=None)
        report_img = create_report(name='Report on Images', ct=self.ct_image)

        create_field = partial(
            Field.objects.create, selected=False, sub_report=None, type=RFT_FIELD,
        )
        create_field(report=report_img, name='name', order=1)
        create_field(report=report_img, name=str(cf.uuid), order=2, type=RFT_CUSTOM)

        report_contact = create_report(
            name='Report on Contacts', ct=self.ct_contact, filter=self.efilter,
        )
        create_field(report=report_contact, name='first_name',  order=1)
        create_field(
            report=report_contact, name='image__name', order=2,
            sub_report=report_img, selected=True,
        )

        lines = [
            [self.aria.first_name, aria_face.name, '150'],
            [self.ned.first_name,  ned_face.name,  '190'],
            [self.robb.first_name, '',             ''],
        ]
        self.assertListEqual(lines, report_contact.fetch_all_lines())

        lines.pop()  # 'robb' is not visible
        ned_line = lines[1]
        ned_line[1] = ned_line[2] = settings.HIDDEN_VALUE  # 'ned_face' is not visible
        self.assertEqual(lines, report_contact.fetch_all_lines(user=user))

    def test_related(self):
        user = self.login_as_basic_user()

        self._aux_fetch_related(
            select_doc_report=None, invalid_one=True, user=user, other_user=self.get_root_user(),
        )

        report = self.refresh(self.folder_report)
        self.assertEqual(2, len(report.columns))

        doc11 = self.doc11
        doc12 = self.doc12
        fetch = report.fetch_all_lines
        lines = [
            [self.folder1.title, f'{doc11}, {doc12}'],
            [self.folder2.title, str(self.doc21)],
        ]
        self.assertEqual(lines, fetch())

        lines[0][1] = str(doc11)
        self.assertEqual(lines, fetch(user=user))

    def test_related__sub_report__expanded(self):
        "Sub-report (expanded)."
        user = self.login_as_basic_user()

        self._aux_fetch_related(
            select_doc_report=True, user=user, other_user=self.get_root_user(),
        )
        folder3 = FakeReportsFolder.objects.create(user=user, title='Empty')

        folder1 = self.folder1
        doc11 = self.doc11
        # Beware: folders are ordered by title
        lines = [
            [folder3.title,      '',               ''],
            [folder1.title,      doc11.title,      doc11.description],
            [folder1.title,      self.doc12.title, ''],
            [self.folder2.title, self.doc21.title, ''],
        ]
        fetch = self.folder_report.fetch_all_lines
        self.assertEqual(lines, fetch())

        lines.pop(2)  # doc12
        self.assertEqual(lines, fetch(user=user))

    def test_related__sub_report__not_expanded(self):
        "Sub-report (not expanded)."
        user = self.login_as_basic_user()

        self._aux_fetch_related(
            select_doc_report=False, user=user, other_user=self.get_root_user(),
        )
        folder3 = FakeReportsFolder.objects.create(user=user, title='Empty')

        folder1 = self.folder1
        doc11 = self.doc11
        fmt = f'{_("Title")}: %s/{_("Description")}: %s'
        doc11_str = fmt % (doc11.title, doc11.description)
        lines = [
            [folder3.title,      ''],
            [folder1.title,      doc11_str + ', ' + fmt % (self.doc12.title, '')],
            [self.folder2.title, fmt % (self.doc21.title, '')],
        ]
        fetch = self.folder_report.fetch_all_lines
        self.assertEqual(lines, fetch())

        lines[1][1] = doc11_str
        self.assertEqual(lines, fetch(user=user))

    def test_function_field(self):
        user = self.login_as_root_and_get()

        self._aux_fetch_persons(
            user=user, report_4_contact=False, create_contacts=False, create_relations=False,
        )

        ptype = CremePropertyType.objects.create(text='I am not dead!')
        CremeProperty.objects.create(type=ptype, creme_entity=self.starks)

        report = self.report_orga
        create_field = partial(
            Field.objects.create,
            report=report,
            selected=False, sub_report=None, type=RFT_FUNCTION,
        )
        create_field(name='get_pretty_properties', order=2)
        create_field(name='invalid_funfield',      order=3)

        report = self.refresh(report)
        self.assertEqual(2, len(report.columns))  # Invalid column is deleted
        self.assertEqual(2, report.fields.count())
        self.assertListEqual(
            [
                [self.lannisters.name, ''],
                [self.starks.name,     ptype.text],
            ],
            report.fetch_all_lines(),
        )

    def test_function_field__sub_report(self):
        user = self.login_as_basic_user()

        self._create_contacts_n_images(user=user, other_user=self.get_root_user())
        ned_face = self.ned_face
        aria_face = self.aria_face

        self.assertFalse(user.has_perm_to_view(ned_face))
        self.assertTrue(user.has_perm_to_view(aria_face))

        create_report = partial(Report.objects.create, user=user, filter=None)
        report_img = create_report(name='Report on Images', ct=self.ct_image)

        create_field = partial(Field.objects.create, type=RFT_FIELD)
        create_field(report=report_img, name='name',                  order=1)
        create_field(report=report_img, name='get_pretty_properties', order=2, type=RFT_FUNCTION)

        report_contact = create_report(
            name='Report on Contacts', ct=self.ct_contact, filter=self.efilter,
        )
        create_field(report=report_contact, name='first_name',  order=1)
        create_field(
            report=report_contact, name='image__name', order=2,
            sub_report=report_img, selected=True,
        )

        ptype = CremePropertyType.objects.create(text='I am waiting the winter')

        create_prop = partial(CremeProperty.objects.create, type=ptype)
        create_prop(creme_entity=aria_face)
        create_prop(creme_entity=ned_face)

        lines = [
            [self.aria.first_name, aria_face.name, ptype.text],
            [self.ned.first_name,  ned_face.name,  ptype.text],
            [self.robb.first_name, '',             ''],
        ]
        self.assertEqual(lines, report_contact.fetch_all_lines())

        lines.pop()  # 'robb' is not visible
        ned_line = lines[1]
        ned_line[1] = ned_line[2] = settings.HIDDEN_VALUE  # 'ned_face' is not visible
        self.assertEqual(lines, report_contact.fetch_all_lines(user=user))

    def test_relation__no_sub_report(self):
        user = self.login_as_basic_user()

        self._aux_fetch_persons(user=user, report_4_contact=False)
        report = self.report_orga

        ned = self.ned
        ned.user = self.get_root_user()
        ned.save()

        create_field = partial(
            Field.objects.create, report=report,
            type=RFT_RELATION, selected=False, sub_report=None,
        )
        create_field(name=FAKE_REL_OBJ_EMPLOYED_BY, order=2)
        create_field(name='invalid',                order=3)

        report = self.refresh(report)
        self.assertEqual(2, len(report.columns))
        self.assertEqual(2, report.fields.count())

        fetch = self.report_orga.fetch_all_lines
        lines = [
            [self.lannisters.name, str(self.tyrion)],
            [self.starks.name,     f'{ned}, {self.robb}'],
        ]
        self.assertEqual(lines, fetch())

        lines[1][1] = str(self.robb)
        self.assertEqual(lines, fetch(user=user))

    def test_relation__sub_report__expanded(self):
        user = self.login_as_basic_user()
        self._aux_fetch_persons(user=user)

        report = self.report_orga
        Field.objects.create(
            report=report, name=FAKE_REL_OBJ_EMPLOYED_BY, order=2,
            type=RFT_RELATION, selected=True, sub_report=self.report_contact,
        )

        self.assertHeaders(['name', 'last_name', 'first_name'], report)

        starks = self.starks
        ned = self.ned
        robb = self.robb
        tyrion = self.tyrion

        robb.user = self.get_root_user()
        robb.save()

        lines = [
            [self.lannisters.name, tyrion.last_name, tyrion.first_name],
            [starks.name,          ned.last_name,    ned.first_name],
            [starks.name,          robb.last_name,   robb.first_name],
        ]
        self.assertEqual(lines, report.fetch_all_lines())

        lines.pop()  # 'robb' line removed
        self.assertEqual(lines, report.fetch_all_lines(user=user))

    def test_relation__sub_report__not_expanded(self):
        "Sub-report (not expanded)."
        user = self.login_as_basic_user()
        self._aux_fetch_persons(user=user)

        ptype = CremePropertyType.objects.create(text='Dwarf')
        CremeProperty.objects.create(type=ptype, creme_entity=self.tyrion)

        report_contact = self.report_contact

        create_field = partial(Field.objects.create, report=report_contact)
        create_field(name='get_pretty_properties', type=RFT_FUNCTION, order=3)
        create_field(
            name='image__name', type=RFT_FIELD, order=4,
            sub_report=self._create_image_report(user=user), selected=True,
        )

        report_orga = self.report_orga
        create_field(
            report=report_orga, name=FAKE_REL_OBJ_EMPLOYED_BY, order=2,
            type=RFT_RELATION, selected=False, sub_report=report_contact,
        )
        self.assertHeaders(['name', FAKE_REL_OBJ_EMPLOYED_BY], report_orga)

        ned = self.ned
        robb = self.robb
        tyrion = self.tyrion

        robb.user = self.get_root_user()
        robb.save()

        ned.image = img = FakeImage.objects.create(
            name='Ned pic', user=user, description='Ned Stark selfie',
        )
        ned.save()

        fmt = (
            f"{_('Last name')}: %s/{_('First name')}: %s/"
            f"{_('Properties')}: %s/{_('Photograph')}: %s"
        )

        ned_str = fmt % (
            ned.last_name,  ned.first_name, '',
            f"{_('Name')}: {img.name}/{_('Description')}: {img.description}",
        )
        lines = [
            [
                self.lannisters.name,
                fmt % (tyrion.last_name, tyrion.first_name, ptype.text, ''),
            ],
            [
                self.starks.name,
                ned_str + ', ' + fmt % (robb.last_name, robb.first_name, '', ''),
            ],
        ]
        self.assertEqual(lines, report_orga.fetch_all_lines())

        lines[1][1] = ned_str
        self.assertEqual(lines, report_orga.fetch_all_lines(user=user))

    def test_relation__sub_report__expanded__filter(self):
        "Sub-report (expanded) with a filter."
        user = self.login_as_root_and_get()
        self._aux_fetch_persons(user=user)
        tyrion = self.tyrion

        tyrion_face = FakeImage.objects.create(name='Tyrion face', user=user)
        tyrion.image = tyrion_face
        tyrion.save()

        ptype = CremePropertyType.objects.create(text='Is a dwarf')
        CremeProperty.objects.create(type=ptype, creme_entity=self.tyrion)

        dwarves_filter = EntityFilter.objects.smart_update_or_create(
            'test-filter_dwarves', 'Dwarves', FakeContact, is_custom=True,
            conditions=[
                condition_handler.PropertyConditionHandler.build_condition(
                    model=FakeContact, ptype=ptype, has=True,
                ),
            ],
        )

        report_contact = self.report_contact
        report_contact.filter = dwarves_filter
        report_contact.save()

        img_report = self._create_image_report(user=user)

        create_field = Field.objects.create
        create_field(
            report=report_contact, name='image__name', order=3,
            type=RFT_FIELD,
            sub_report=img_report, selected=True,
        )

        report = self.report_orga
        create_field(
            report=report, name=FAKE_REL_OBJ_EMPLOYED_BY, order=2,
            type=RFT_RELATION,
            sub_report=self.report_contact, selected=True,
        )

        self.assertListEqual(
            [
                [self.lannisters.name, tyrion.last_name, tyrion.first_name, tyrion_face.name, ''],
                [self.starks.name,     '',               '',                '',               ''],
            ],
            report.fetch_all_lines(),
        )

    def test_relation__sub_report__expanded__several(self):
        "Several expanded sub-reports."
        user = self.login_as_root_and_get()
        self._aux_fetch_persons(user=user)

        tyrion = self.tyrion
        ned = self.ned
        robb = self.robb
        starks = self.starks

        report_orga = self.report_orga
        create_field = partial(Field.objects.create, type=RFT_RELATION)
        create_field(
            report=report_orga, name=FAKE_REL_OBJ_EMPLOYED_BY, order=2,
            sub_report=self.report_contact, selected=True,
        )

        folder = FakeReportsFolder.objects.create(user=user, title='Ned folder')

        create_doc = partial(FakeReportsDocument.objects.create, user=user)
        doc1 = create_doc(title='Sword',  linked_folder=folder, description='Blablabla')
        doc2 = create_doc(title='Helmet', linked_folder=folder)

        rtype = RelationType.objects.get(pk=REL_SUB_HAS)
        doc_report = self._create_simple_documents_report(user=user)
        create_field(
            report=self.report_contact, name=rtype.id, order=3,
            sub_report=doc_report, selected=True,
        )

        create_rel = partial(Relation.objects.create, type=rtype, user=user, subject_entity=ned)
        create_rel(object_entity=doc1)
        create_rel(object_entity=doc2)

        self.assertListEqual(
            [_('Name'), _('Last name'), _('First name'), _('Title'), _('Description')],
            [column.title for column in report_orga.get_children_fields_flat()],
        )
        self.assertListEqual(
            [
                [self.lannisters.name, tyrion.last_name, tyrion.first_name, '', ''],

                # Beware Documents are ordered by title
                [starks.name, ned.last_name, ned.first_name, doc2.title, ''],
                [starks.name, ned.last_name, ned.first_name, doc1.title, doc1.description],

                [starks.name, robb.last_name, robb.first_name, '', ''],
            ],
            report_orga.fetch_all_lines(),
        )

    def test_aggregate(self):
        "Regular field, Custom field (valid & invalid ones)."
        self._aux_fetch_aggregate(invalid_ones=True)

        starks = self.starks
        starks.capital = 500
        starks.save()

        lannisters = self.lannisters
        lannisters.capital = 1000
        lannisters.save()

        create_cfval = partial(CustomFieldInteger.objects.create, custom_field=self.cf)
        create_cfval(entity=starks,     value=100)
        create_cfval(entity=lannisters, value=500)
        create_cfval(entity=self.guild, value=50)  # Should not be used

        report = self.refresh(self.report_orga)
        self.assertEqual(3, len(report.columns))

        self.assertListEqual(
            [
                [lannisters.name, '1500', '500'],
                [starks.name,     '1500', '500'],
            ],
            report.fetch_all_lines(),
        )

    def test_aggregate__manage_none(self):
        "Regular field, Custom field (valid & invalid ones): None replaced by 0."
        self._aux_fetch_aggregate()
        self.assertListEqual(
            [
                [self.lannisters.name, '0', '0'],
                [self.starks.name,     '0', '0'],
            ],
            self.report_orga.fetch_all_lines(),
        )

    def test_aggregate__sub_lines(self):
        "Aggregate in sub-lines (expanded sub-report)."
        user = self.login_as_root_and_get()
        self._aux_fetch_persons(user=user, create_contacts=False, report_4_contact=False)

        report_invoice = Report.objects.create(
            user=user, name='Report on invoices', ct=FakeInvoice,
        )

        create_field = partial(Field.objects.create, selected=False, sub_report=None)
        create_field(report=report_invoice, name='name',           type=RFT_FIELD,     order=1)
        create_field(report=report_invoice, name='total_vat__sum', type=RFT_AGG_FIELD, order=2)

        report = self.report_orga
        create_field(
            report=report, name=FAKE_REL_OBJ_BILL_ISSUED, order=2,
            selected=True, sub_report=report_invoice, type=RFT_RELATION,
        )

        starks = self.starks
        lannisters = self.lannisters

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        guild = create_orga(name='Guild of merchants')
        hord  = create_orga(name='Hord')

        create_invoice = partial(self._create_invoice, target=guild)
        invoice1 = create_invoice(starks,     name='Invoice#1', total_vat=Decimal('100.5'))
        invoice2 = create_invoice(lannisters, name='Invoice#2', total_vat=Decimal('200.5'))
        invoice3 = create_invoice(lannisters, name='Invoice#3', total_vat=Decimal('50.1'))
        create_invoice(hord, name='Invoice#4', total_vat=Decimal('1000'))  # Should not be used

        def fmt_number(n):
            return number_format(n, decimal_pos=2)

        total_lannisters = fmt_number(invoice2.total_vat + invoice3.total_vat)
        total_starks     = fmt_number(invoice1.total_vat)
        self.assertListEqual(
            [
                [lannisters.name, invoice2.name, total_lannisters],
                [lannisters.name, invoice3.name, total_lannisters],
                [starks.name,     invoice1.name, total_starks],
            ],
            report.fetch_all_lines(),
        )

    def test_aggregate__decimal_custom_field(self):
        user = self.login_as_root_and_get()
        self._aux_fetch_persons(user=user, create_contacts=False, report_4_contact=False)

        starks = self.starks
        lannisters = self.lannisters

        cfield = CustomField.objects.create(
            content_type=self.ct_orga,
            name='Gold',
            field_type=CustomField.FLOAT,
        )

        create_cfval = partial(cfield.value_class.objects.create, custom_field=cfield)

        starks_gold = Decimal('100.5')
        create_cfval(entity=starks, value=starks_gold)

        lannisters_gold = Decimal('500.3')
        create_cfval(entity=lannisters, value=lannisters_gold)

        report = self.report_orga
        Field.objects.create(
            report=report, name=f'{cfield.uuid}__sum', type=RFT_AGG_CUSTOM, order=2,
        )

        agg_value = number_format(starks_gold + lannisters_gold, decimal_pos=2)
        self.assertListEqual(
            [
                [lannisters.name, agg_value],
                [starks.name,     agg_value],
            ],
            report.fetch_all_lines(),
        )


@skipIfCustomReport
class ReportFieldTestCase(BaseReportsTestCase):
    def test_report_property(self):
        user = self.login_as_root_and_get()
        report = self._build_orga_report(user=user)
        report = self.refresh(report)

        with self.assertNumQueries(1):
            columns = report.columns

        self.assertIsList(columns, length=2)

        field = columns[0]
        self.assertIsInstance(field, Field)
        self.assertEqual('name',     field.name)
        self.assertEqual(_('Name'),  field.title)
        self.assertEqual(RFT_FIELD,  field.type)
        self.assertFalse(field.selected)
        self.assertFalse(field.sub_report)

        with self.assertNumQueries(0):
            f_report = field.report

        self.assertEqual(report, f_report)

    def test_invalid_hands__too_deep(self):
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(user=user)

        rfield = Field.objects.create(
            report=report, type=RFT_FIELD, order=2,
            name='image__categories__name',
        )

        with self.assertLogs(level='WARNING') as logs_manager:
            self.assertIsNone(rfield.hand)
        self.assertIn(
            'Invalid column is deleted '
            '(Invalid field: "image__categories__name" (too deep))',
            logs_manager.output[0],
        )

        self.assertDoesNotExist(rfield)

    def test_invalid_hands__no_entity(self):
        "No entity at depth=1."
        user = self.login_as_root_and_get()
        report = Report.objects.create(
            user=user, name='Report on docs', ct=FakeReportsDocument,
        )

        rfield = Field.objects.create(
            name='linked_folder__parent',
            report=report, type=RFT_FIELD, order=2,
        )

        with self.assertLogs(level='WARNING') as logs_manager:
            self.assertIsNone(rfield.hand)
        self.assertIn(
            'Invalid column is deleted (Invalid field: '
            '"linked_folder__parent" (no entity at depth=1))',
            logs_manager.output[0],
        )

        self.assertDoesNotExist(rfield)
