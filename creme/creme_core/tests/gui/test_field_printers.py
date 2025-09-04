from datetime import date
from decimal import Decimal
from functools import partial
from os.path import basename

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import date_format, number_format
from django.utils.html import escape
from django.utils.timezone import localtime
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.utils.translation import override as override_language
from django.utils.translation import pgettext

from creme.creme_core.core.download import filefield_download_registry
from creme.creme_core.core.entity_filter import operators
from creme.creme_core.core.entity_filter.condition_handler import (
    RegularFieldConditionHandler,
)
from creme.creme_core.gui.field_printers import (
    FieldPrinterRegistry,
    FKPrinter,
    M2MPrinterForHTML,
    M2MPrinterForText,
    ViewTag,
    print_boolean_html,
    print_boolean_text,
    print_choice,
    print_color_html,
    print_date_html,
    print_date_text,
    print_datetime_html,
    print_datetime_text,
    print_decimal_html,
    print_decimal_text,
    print_email_html,
    print_file_html,
    print_image_html,
    print_integer_html,
    print_percent_html,
    print_text_html,
    print_unchecked_url_html,
    print_unsafehtml_html,
    print_url_html,
    simple_print_html,
    simple_print_text,
)
from creme.creme_core.models import (
    CremeEntity,
    EntityFilter,
    FakeActivity,
    FakeContact,
    FakeDocument,
    FakeEmailCampaign,
    FakeFileComponent,
    FakeFolder,
    FakeImage,
    FakeImageCategory,
    FakeInvoiceLine,
    FakeMailingList,
    FakeOrganisation,
    FakePosition,
    FakeProduct,
    FakeReport,
    FakeSector,
    FakeTicket,
    FakeTicketStatus,
)
from creme.creme_core.tests.base import CremeTestCase


@override_settings(CELL_SIZE=3)
class FieldsPrintersTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.build_user()

    def test_simple_print_html(self):
        c = FakeContact()
        user = self.user
        field = c._meta.get_field('first_name')
        self.assertEqual(
            '',
            simple_print_html(instance=c, value=None, user=user, field=field)
        )

        value = 'Rei'
        self.assertEqual(
            value,
            simple_print_html(instance=c, value=value, user=user, field=field),
        )

        self.assertEqual(
            '&lt;b&gt;Rei&lt;b&gt;',
            simple_print_html(instance=c, value='<b>Rei<b>', user=user, field=field),
        )

    def test_simple_print_txt(self):
        c = FakeContact()
        user = self.user
        field = c._meta.get_field('first_name')
        self.assertEqual(
            '',
            simple_print_text(instance=c, value=None, user=user, field=field),
        )

        value = 'Rei'
        self.assertEqual(
            value,
            simple_print_text(instance=c, value=value, user=user, field=field),
        )

    def test_print_choice(self):
        user = self.user
        field = FakeInvoiceLine._meta.get_field('discount_unit')

        line1 = FakeInvoiceLine(discount_unit=FakeInvoiceLine.Discount.PERCENT)
        self.assertEqual(
            _('Percent'),
            print_choice(instance=line1, value='whatever', user=user, field=field),
        )

        line2 = FakeInvoiceLine(discount_unit=FakeInvoiceLine.Discount.AMOUNT)
        self.assertEqual(
            _('Amount'),
            print_choice(instance=line2, value='whatever', user=user, field=field),
        )

        line3 = FakeInvoiceLine(discount_unit=None)
        self.assertEqual(
            '',
            print_choice(instance=line3, value='whatever', user=user, field=field),
        )

    def _aux_print_integer_html01(self):
        o = FakeOrganisation()
        user = self.user
        field = o._meta.get_field('capital')
        self.assertEqual(
            '',
            print_integer_html(instance=o, value=None, user=user, field=field)
        )

        value = 1234
        self.assertEqual(
            number_format(value, force_grouping=True),
            print_integer_html(instance=o, value=value, user=user, field=field)
        )

    @override_settings(USE_THOUSAND_SEPARATOR=True)
    def test_print_integer_html01(self):
        return self._aux_print_integer_html01()

    @override_settings(USE_THOUSAND_SEPARATOR=False)
    def test_print_integer_html02(self):
        return self._aux_print_integer_html01()

    def test_print_decimal_html(self):
        line = FakeInvoiceLine()
        user = self.user
        field = line._meta.get_field('discount')
        self.assertEqual(
            '',
            print_decimal_html(instance=line, value=None, user=user, field=field)
        )

        value = Decimal('1234.56')
        self.assertEqual(
            number_format(value, force_grouping=True),
            print_decimal_html(instance=line, value=value, user=user, field=field)
        )

    def test_print_decimal_text(self):
        line = FakeInvoiceLine()
        user = self.user
        field = line._meta.get_field('discount')
        self.assertEqual(
            '',
            print_decimal_text(instance=line, value=None, user=user, field=field)
        )

        value = Decimal('1234.56')
        self.assertEqual(
            number_format(value),
            print_decimal_text(instance=line, value=value, user=user, field=field)
        )

    def test_print_boolean_html(self):
        c = FakeContact()
        user = self.user
        field = c._meta.get_field('is_a_nerd')
        self.assertEqual(
            '',
            print_boolean_html(instance=c, value=None, user=user, field=field)
        )

        self.assertEqual(
            '<input type="checkbox" checked disabled/>{}'.format(_('Yes')),
            print_boolean_html(instance=c, value=True, user=user, field=field)
        )
        self.assertEqual(
            '<input type="checkbox" disabled/>{}'.format(_('No')),
            print_boolean_html(instance=c, value=False, user=user, field=field)
        )

    def test_print_boolean_text(self):
        c = FakeContact()
        user = self.user
        field = c._meta.get_field('is_a_nerd')
        self.assertEqual(
            '',
            print_boolean_text(instance=c, value=None, user=user, field=field)
        )

        self.assertEqual(
            _('Yes'),
            print_boolean_text(instance=c, value=True, user=user, field=field)
        )
        self.assertEqual(
            _('No'),
            print_boolean_text(instance=c, value=False, user=user, field=field)
        )

    def test_print_url_html(self):
        o = FakeOrganisation()
        user = self.user
        field = o._meta.get_field('url_site')
        self.assertEqual(
            '',
            print_url_html(instance=o, value=None, user=user, field=field)
        )

        url1 = 'http://www.wikipedia.org'
        self.assertEqual(
            f'<a href="{url1}" target="_blank">{url1}</a>',
            print_url_html(instance=o, value=url1, user=user, field=field)
        )

        url2 = '</a><script>Muhaha</script>'
        self.assertEqual(
            '<a href="{url}" target="_blank">{url}</a>'.format(url=escape(url2)),
            print_url_html(instance=o, value=url2, user=user, field=field)
        )

    def test_print_unchecked_url_html(self):
        o = FakeContact()
        user = self.user
        field = o._meta.get_field('url_site')
        self.assertEqual(
            '',
            print_unchecked_url_html(instance=o, value=None, user=user, field=field)
        )

        url1 = 'http://www.wikipedia.org'
        self.assertEqual(
            f'<a href="{url1}" target="_blank">{url1}</a>',
            print_unchecked_url_html(instance=o, value=url1, user=user, field=field)
        )

        url2 = '</a><script>Muhaha</script>'
        self.assertEqual(
            '<a href="{href}" target="_blank">{url}</a>'.format(
                url=escape(url2), href=escape('//' + url2),
            ),
            print_unchecked_url_html(instance=o, value=url2, user=user, field=field)
        )

        url3 = 'www.wikipedia.org'
        self.assertEqual(
            f'<a href="//{url3}" target="_blank">{url3}</a>',
            print_unchecked_url_html(instance=o, value=url3, user=user, field=field)
        )

    def test_print_date_html(self):
        c = FakeContact()
        user = self.user
        field = c._meta.get_field('birthday')
        self.assertEqual(
            '', print_date_html(instance=c, value=None, user=user, field=field),
        )

        value = date(year=2019, month=8, day=21)

        with override_language('en'):
            self.assertEqual(
                date_format(value, 'DATE_FORMAT'),
                print_date_html(instance=c, value=value, user=user, field=field),
            )

    def test_print_date_text(self):
        c = FakeContact()
        user = self.user
        field = c._meta.get_field('birthday')
        self.assertEqual('', print_date_text(instance=c, value=None, user=user, field=field))

        value = date(year=2019, month=8, day=21)

        with override_language('en'):
            self.assertEqual(
                value.strftime('%Y-%m-%d'),
                print_date_text(instance=c, value=value, user=user, field=field),
            )

    def test_print_datetime_html(self):
        a = FakeActivity()
        user = self.user
        field = a._meta.get_field('start')
        self.assertEqual(
            '', print_datetime_html(instance=a, value=None, user=user, field=field),
        )

        value = self.create_datetime(year=2019, month=8, day=21, hour=11, minute=30)

        with override_language('en'):
            self.assertHTMLEqual(
                '<span class="datetime-field" title="{seconds}">{dt}</span>'.format(
                    seconds=_('Seconds: {}').format(value.second),
                    dt=date_format(value, 'DATETIME_FORMAT'),
                ),
                print_datetime_html(instance=a, value=value, user=user, field=field),
            )

    def test_print_datetime_text(self):
        a = FakeActivity()
        user = self.user
        field = a._meta.get_field('start')
        self.assertEqual('', print_datetime_text(instance=a, value=None, user=user, field=field))

        value = self.create_datetime(year=2019, month=8, day=21, hour=11, minute=30)

        with override_language('en'):
            self.assertEqual(
                value.strftime('%Y-%m-%d %H:%M:%S'),
                print_datetime_text(instance=a, value=value, user=user, field=field),
            )

    def test_print_email_html(self):
        c = FakeContact()
        user = self.user
        field = c._meta.get_field('email')
        self.assertEqual(
            '', print_email_html(instance=c, value=None, user=user, field=field),
        )

        value1 = 'contact@foo.bar'
        self.assertEqual(
            f'<a href="mailto:{value1}">{value1}</a>',
            print_email_html(instance=c, value=value1, user=user, field=field)
        )

        value2 = '</a><script>Muhahaha</script>contact@foo.bar'
        self.assertEqual(
            '<a href="mailto:{email}">{email}</a>'.format(email=escape(value2)),
            print_email_html(instance=c, value=value2, user=user, field=field)
        )

    def test_print_text_html(self):
        c = FakeContact()
        user = self.user
        field = c._meta.get_field('description')
        self.assertEqual('', print_text_html(instance=c, value=None, user=user, field=field))

        text = 'See you <b>space</b> cowboy...\nThe real folk blues: www.bebop.org'

        with override_settings(URLIZE_TARGET_BLANK=True):
            p1 = print_text_html(instance=c, user=user, field=field, value=text)

        self.assertHTMLEqual(
            '<p>See you &lt;b&gt;space&lt;/b&gt; cowboy...<br>The real folk blues: '
            '<a target="_blank" rel="noopener noreferrer" href="http://www.bebop.org">'
            'www.bebop.org'
            '</a>'
            '</p>',
            p1,
        )

        with override_settings(URLIZE_TARGET_BLANK=False):
            p2 = print_text_html(instance=c, user=user, field=field, value=text)

        self.assertEqual(
            '<p>See you &lt;b&gt;space&lt;/b&gt; cowboy...<br>The real folk blues: '
            '<a href="http://www.bebop.org">www.bebop.org</a>'
            '</p>',
            p2,
        )

    def test_print_percent_html(self):
        from creme.creme_core.models.fields import IntegerPercentField

        instance = CremeEntity()
        user = self.user
        field = IntegerPercentField()

        self.assertEqual(
            '', print_percent_html(instance=instance, value=None, user=user, field=field),
        )

        self.assertHTMLEqual(
            '<span class="percent-value">0</span>&nbsp;<span class="percent-marker">%</span>',
            print_percent_html(instance=instance, value=0, user=user, field=field),
        )
        self.assertHTMLEqual(
            '<span class="percent-value">57</span>&nbsp;<span class="percent-marker">%</span>',
            print_percent_html(instance=instance, value=57, user=user, field=field),
        )

    def test_print_color_html(self):
        status = FakeTicketStatus()
        user = self.user
        field = status._meta.get_field('color')
        self.assertEqual('', print_color_html(instance=status, value='', user=user, field=field))

        color = '112233'
        self.assertHTMLEqual(
            f'<span style="background:#{color};">{color}</span>',
            print_color_html(instance=status, value=color, user=user, field=field),
        )

    def test_print_unsafehtml_html(self):
        c = FakeContact()
        user = self.user
        field = c._meta.get_field('description')
        self.assertEqual(
            '', print_unsafehtml_html(instance=c, value=None, user=user, field=field),
        )

        self.assertEqual(
            '<p>&lt;p&gt;See you space cowboy...&lt;/p&gt;</p>',
            print_unsafehtml_html(
                instance=c, user=user, field=field,
                value='<p>See you space cowboy...</p>',
            ),
        )

    def test_print_file_html01(self):
        "Not image."
        user = self.get_root_user()
        folder = FakeFolder.objects.create(user=user, title='TestGui')

        file_name = 'FieldsPrintersTestCase_test_print_file_html01.txt'
        file_path = self.create_uploaded_file(file_name=file_name, dir_name='gui')
        doc1 = FakeDocument.objects.create(
            user=user,
            linked_folder=folder,
            filedata=file_path,
        )
        self.assertHTMLEqual(
            '<a href="{url}">{label}</a>'.format(
                url=reverse(
                    'creme_core__download',
                    args=(
                        doc1.entity_type_id,
                        doc1.id,
                        'filedata',
                    )
                ),
                label=_('Download «{file}»').format(file=file_name),
            ),
            print_file_html(
                instance=doc1,
                value=doc1.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            ),
        )

        # ---
        doc2 = FakeDocument.objects.create(
            user=user,
            linked_folder=folder,
        )
        self.assertEqual(
            '',
            print_file_html(
                instance=doc2,
                value=doc2.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            ),
        )

    @override_settings(ALLOWED_IMAGES_EXTENSIONS=['gif', 'png', 'jpg'])
    def test_print_file_html02(self):
        "Image."
        user = self.get_root_user()
        folder = FakeFolder.objects.create(user=user, title='TestGui')

        file_name = 'add_16.png'
        file_path = self.create_uploaded_file(
            file_name=file_name, dir_name='gui',
            content=[settings.CREME_ROOT, 'static', 'chantilly', 'images', file_name],
        )

        doc1 = FakeDocument.objects.create(
            user=user,
            linked_folder=folder,
            filedata=file_path,
        )
        self.assertHTMLEqual(
            """<a class="image-file" onclick="creme.dialogs.image('{url}').open();">
                <img src="{url}" alt="{label}" />
            </a>""".format(
                url=reverse(
                    'creme_core__download',
                    args=(
                        doc1.entity_type_id,
                        doc1.id,
                        'filedata',
                    )
                ),
                label=_('Download «{file}»').format(file=basename(file_path)),
            ),
            print_file_html(
                instance=doc1,
                value=doc1.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            ),
        )

        # ---
        doc2 = FakeDocument.objects.create(
            user=user,
            linked_folder=folder,
        )
        self.assertHTMLEqual(
            '',
            print_file_html(
                instance=doc2,
                value=doc2.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            ),
        )

    @override_settings(ALLOWED_IMAGES_EXTENSIONS=['gif', 'jpg'])  # Not 'png'
    def test_print_file_html03(self):
        "Not allowed image extensions."
        user = self.get_root_user()
        folder = FakeFolder.objects.create(user=user, title='TestGui')

        file_name = 'add_16.png'
        file_path = self.create_uploaded_file(
            file_name=file_name, dir_name='gui',
            content=[settings.CREME_ROOT, 'static', 'chantilly', 'images', file_name],
        )

        doc = FakeDocument.objects.create(
            user=user,
            linked_folder=folder,
            filedata=file_path,
        )
        self.assertHTMLEqual(
            '<a href="{url}">{label}</a>'.format(
                url=reverse(
                    'creme_core__download',
                    args=(
                        doc.entity_type_id,
                        doc.id,
                        'filedata',
                    )
                ),
                label=_('Download «{file}»').format(file=basename(file_path)),
            ),
            print_file_html(
                instance=doc,
                value=doc.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            ),
        )

    def test_print_file_html04(self):
        "Field not registered for download."
        user = self.get_root_user()

        file_name = 'FieldsPrintersTestCase_test_print_file_html04.txt'
        file_path = self.create_uploaded_file(file_name=file_name, dir_name='gui')
        comp = FakeFileComponent(filedata=file_path)

        with self.assertRaises(filefield_download_registry.InvalidField):
            filefield_download_registry.get(
                user=user,
                instance=comp,
                field_name='filedata',
            )

        self.assertEqual(
            f'creme_core-tests/gui/{file_name}',
            print_file_html(
                instance=comp,
                value=comp.filedata,
                user=user,
                field=FakeFileComponent._meta.get_field('filedata'),
            ),
        )

    @override_settings(ALLOWED_IMAGES_EXTENSIONS=['gif', 'png', 'jpg'])
    def test_print_image_html(self):
        user = self.get_root_user()
        folder = FakeFolder.objects.create(user=user, title='TestGui')

        file_path = self.create_uploaded_file(
            file_name='my_super_name.PNG',  # Notice extension in caps
            dir_name='gui',
            content=[settings.CREME_ROOT, 'static', 'chantilly', 'images', 'add_16.png'],
        )

        doc1 = FakeDocument.objects.create(
            user=user,
            linked_folder=folder,
            filedata=file_path,
        )
        self.assertHTMLEqual(
            """<a class="image-file" onclick="creme.dialogs.image('{url}').open();">
                <img src="{url}" alt="{label}" />
            </a>""".format(
                url=reverse(
                    'creme_core__download',
                    args=(
                        doc1.entity_type_id,
                        doc1.id,
                        'filedata',
                    )
                ),
                label=_('Download «{file}»').format(file=basename(file_path)),
            ),
            print_image_html(
                instance=doc1,
                value=doc1.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            ),
        )

        # ---
        doc2 = FakeDocument.objects.create(
            user=user,
            linked_folder=folder,
        )
        self.assertHTMLEqual(
            '',
            print_image_html(
                instance=doc2,
                value=doc2.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            ),
        )

    def test_fk_printer_html01(self):
        user = self.get_root_user()

        c = FakeContact()
        field1 = c._meta.get_field('sector')

        printer = FKPrinter(
            none_printer=FKPrinter.print_fk_null_html,
            default_printer=simple_print_html,
        )

        self.assertEqual('', printer(instance=c, value=None, user=user, field=field1))

        sector = FakeSector.objects.first()
        self.assertEqual(
            str(sector), printer(instance=c, value=sector, user=user, field=field1),
        )

        # entity without specific handler ---
        img = FakeImage.objects.create(user=user, name='Img#1')
        field2 = c._meta.get_field('image')
        self.assertEqual(str(img), printer(instance=c, value=img, user=user, field=field2))

        # null_label ---
        field3 = c._meta.get_field('is_user')
        self.assertEqual(
            '<em>{}</em>'.format(pgettext('persons-is_user', 'None')),
            printer(instance=c, value=None, user=user, field=field3),
        )

    def test_fk_printer_html__creme_entity(self):
        user = self.get_root_user()
        c = FakeContact()
        field = c._meta.get_field('image')

        printer = FKPrinter(
            none_printer=FKPrinter.print_fk_null_html,
            default_printer=simple_print_html,
        ).register(CremeEntity, FKPrinter.print_fk_entity_html)

        img = FakeImage.objects.create(user=user, name='Img#1')
        self.assertHTMLEqual(
            f'<a href="{img.get_absolute_url()}" target="_self">{img}</a>',
            printer(instance=c, value=img, user=user, field=field),
        )

    def test_fk_printer_html__content_type01(self):
        self.assertHasAttr(FakeContact, 'get_lv_absolute_url')

        user = self.get_root_user()
        report = FakeReport(ctype=FakeContact)
        field = report._meta.get_field('ctype')

        printer = FKPrinter(
            none_printer=FKPrinter.print_fk_null_html,
            default_printer=simple_print_html,
        ).register(ContentType, FKPrinter.print_fk_contenttype_html)

        url = reverse('creme_core__list_fake_contacts')
        self.assertHTMLEqual(
            f'<a href="{url}">Test Contacts</a>',
            printer(instance=report, value=report.ctype, user=user, field=field),
        )

    def test_fk_printer_html__content_type02(self):
        "Model without related list-view."
        self.assertHasNoAttr(FakeTicket, 'get_lv_absolute_url')

        printer = FKPrinter(
            none_printer=FKPrinter.print_fk_null_html,
            default_printer=simple_print_html,
        ).register(ContentType, FKPrinter.print_fk_contenttype_html)

        report = FakeReport(ctype=FakeTicket)
        self.assertEqual(
            'Test Tickets',
            printer(
                instance=report, value=report.ctype,
                user=self.get_root_user(),
                field=report._meta.get_field('ctype'),
            ),
        )

    def test_fk_printer_html__content_type03(self):
        "No app perm."
        user = self.create_user(
            role=self.create_role(name='No core', allowed_apps=['documents']),
        )

        printer = FKPrinter(
            none_printer=FKPrinter.print_fk_null_html,
            default_printer=simple_print_html,
        ).register(ContentType, FKPrinter.print_fk_contenttype_html)

        report = FakeReport(ctype=FakeContact)
        self.assertEqual(
            'Test Contacts',
            printer(
                instance=report, value=report.ctype, user=user,
                field=report._meta.get_field('ctype'),
            ),
        )

    def test_fk_printer_html__entity_filter(self):
        user = self.get_root_user()

        printer = FKPrinter(
            none_printer=FKPrinter.print_fk_null_html,
            default_printer=simple_print_html,
        ).register(
            model=EntityFilter, printer=FKPrinter.print_fk_efilter_html,
        )

        name = 'Nerv'
        desc1 = 'important'
        desc2 = 'beware'
        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-ef_orga', name='My filter',
            model=FakeOrganisation,
            is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.STARTSWITH,
                    field_name='name', values=[name],
                ),
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.CONTAINS,
                    field_name='description', values=[desc1, desc2],
                ),
            ],
        )

        r = FakeReport()
        field = r._meta.get_field('efilter')
        fmt_value = _('«{enum_value}»').format
        self.assertHTMLEqual(
            '<div class="entity_filter-summary">'
            '  <a href="{url}">{name}</a>'
            '  <ul>'
            '    <li>{cond1}</li>'
            '    <li>{cond2}</li>'
            '  </ul>'
            '</div>'.format(
                url=efilter.get_absolute_url(),
                name=efilter.name,
                cond1=_('«{field}» starts with {values}').format(
                    field=_('Name'),
                    values=fmt_value(enum_value=name),
                ),
                cond2=_('«{field}» contains {values}').format(
                    field=_('Description'),
                    values=_('{first} or {last}').format(
                        first=fmt_value(enum_value=desc1),
                        last=fmt_value(enum_value=desc2),
                    ),
                ),
            ),
            printer(instance=r, value=efilter, user=user, field=field),
        )

    def test_fk_printer_text01(self):
        user = self.get_root_user()

        printer = FKPrinter(
            none_printer=lambda *args, **kwargs: '',
            default_printer=simple_print_text,
        )

        c = FakeContact()
        field1 = c._meta.get_field('sector')

        self.assertEqual(
            '',
            printer(instance=c, value=None, user=user, field=field1),
        )

        sector = FakeSector.objects.first()
        self.assertEqual(
            str(sector),
            printer(instance=c, value=sector, user=user, field=field1),
        )

        # entity (credentials OK)
        img = FakeImage.objects.create(user=user, name='Img#1')
        field2 = c._meta.get_field('image')
        self.assertEqual(
            str(img),
            printer(instance=c, value=img, user=user, field=field2),
        )

    def test_fk_printer_text02(self):
        "No view credentials."
        user = self.login_as_standard()

        printer = FKPrinter(
            none_printer=lambda *args, **kwargs: '',
            default_printer=simple_print_text,
        ).register(
            model=CremeEntity, printer=FKPrinter.print_fk_entity_html,
        )

        c = FakeContact()
        img = FakeImage.objects.create(user=user, name='Img#1')
        field = c._meta.get_field('image')
        self.assertEqual(
            settings.HIDDEN_VALUE,
            printer(instance=c, value=img, user=user, field=field),
        )

    def test_many2many_printer_html01(self):
        user = self.get_root_user()
        img = FakeImage.objects.create(user=user, name='My img')
        field = img._meta.get_field('categories')

        printer = M2MPrinterForHTML(
            default_printer=M2MPrinterForHTML.printer_simple,
            default_enumerator=M2MPrinterForHTML.enumerator_all,
        )

        self.assertEqual(
            '', printer(instance=img, value=img.categories, user=user, field=field),
        )

        img.categories.set([
            FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')
        ])
        self.assertHTMLEqual(
            '<ul class="limited-list"><li>A</li><li>B</li><li>C</li></ul>',
            printer(instance=img, value=img.categories, user=user, field=field),
        )

        with self.settings(CELL_SIZE=1):
            message = ngettext(
                '{count} more element', '{count} more elements', 2,
            ).format(count=2)

            self.assertHTMLEqual(
                f'<ul class="limited-list">'
                f' <li>A</li>'
                f' <li><span class="more-elements">{message}</span></li>'
                f'</ul>',
                printer(instance=img, value=img.categories, user=user, field=field),
            )

    def test_many2many_printer_html02(self):
        "Entity without specific handler."
        user = self.get_root_user()
        prod = FakeProduct.objects.create(user=user, name='Bebop')
        field = prod._meta.get_field('images')

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='My img#1')
        img2 = create_img(name='My img#2')
        prod.images.set([img1, img2])

        printer = M2MPrinterForHTML(
            default_printer=M2MPrinterForHTML.printer_simple,
            default_enumerator=M2MPrinterForHTML.enumerator_all,
        )
        self.assertHTMLEqual(
            f'<ul class="limited-list"><li>{img1}</li><li>{img2}</li></ul>',
            printer(instance=prod, value=prod.images, user=user, field=field),
        )

    def test_many2many_printer_html03(self):
        "Entity printer."
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

        prod = FakeProduct.objects.create(user=user, name='Bebop')
        field = prod._meta.get_field('images')

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='My img#1')
        img2 = create_img(name='My img#2', user=self.get_root_user())
        img3 = create_img(name='My img#3', is_deleted=True)
        prod.images.set([img1, img2, img3])

        printer = M2MPrinterForHTML(
            default_printer=M2MPrinterForHTML.printer_simple,
            default_enumerator=M2MPrinterForHTML.enumerator_all,
        ).register(
            CremeEntity,
            # TODO: test is_deleted too (other enumerator)
            printer=M2MPrinterForHTML.printer_entity,
            enumerator=M2MPrinterForHTML.enumerator_entity,
        )
        self.assertHTMLEqual(
            f'<ul class="limited-list">'
            f' <li><a target="_blank" href="{img1.get_absolute_url()}">{img1}</a></li>'
            f' <li>{settings.HIDDEN_VALUE}</li>'
            f'</ul>',
            printer(instance=prod, value=prod.images, user=user, field=field),
        )

    def test_many2many_printer_text01(self):
        user = self.get_root_user()

        printer = M2MPrinterForText(
            default_printer=M2MPrinterForText.printer_simple,
            default_enumerator=M2MPrinterForText.enumerator_all,
        )

        img = FakeImage.objects.create(user=user, name='My img')
        field = img._meta.get_field('categories')

        self.assertEqual(
            '',
            printer(instance=img, value=img.categories, user=user, field=field)
        )

        img.categories.set([
            FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')
        ])
        self.assertHTMLEqual(
            'A/B/C',
            printer(instance=img, value=img.categories, user=user, field=field)
        )

    def test_many2many_printer_text02(self):
        "Entity printer."
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

        printer = M2MPrinterForText(
            default_printer=M2MPrinterForText.printer_simple,
            default_enumerator=M2MPrinterForText.enumerator_all,
        ).register(
            CremeEntity,
            printer=M2MPrinterForText.printer_entity,
            enumerator=M2MPrinterForText.enumerator_entity,
        )

        prod = FakeProduct.objects.create(user=user, name='Bebop')
        field = prod._meta.get_field('images')

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='My img#1')
        img2 = create_img(name='My img#2', user=self.get_root_user())
        img3 = create_img(name='My img#3', is_deleted=True)
        prod.images.set([img1, img2, img3])

        self.assertEqual(
            f'{img1}/{settings.HIDDEN_VALUE}',
            printer(instance=prod, value=prod.images, user=user, field=field),
        )

    def test_registry(self):
        "Default."
        user = self.get_root_user()
        registry = FieldPrinterRegistry()

        sector = FakeSector.objects.all()[0]
        img = FakeImage.objects.create(user=user, name='Mars pix')
        o = FakeOrganisation(
            user=user, name='Mars', url_site='www.mars.info', sector=sector,
            image=img,
        )

        render_field = partial(registry.get_field_value, instance=o, user=user)
        self.assertEqual(o.name, render_field(field_name='name', tag=ViewTag.HTML_DETAIL))
        self.assertEqual(o.name, render_field(field_name='name', tag=ViewTag.TEXT_PLAIN))

        self.assertHTMLEqual(
            '<a href="{url}" target="_blank">{url}</a>'.format(url=o.url_site),
            render_field(field_name='url_site', tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(o.url_site, render_field(field_name='url_site', tag=ViewTag.TEXT_PLAIN))

        self.assertEqual(sector.title, render_field(field_name='sector', tag=ViewTag.HTML_DETAIL))
        self.assertEqual(sector.title, render_field(field_name='sector', tag=ViewTag.TEXT_PLAIN))

        self.assertEqual(
            sector.title, render_field(field_name='sector__title', tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(
            sector.title, render_field(field_name='sector__title', tag=ViewTag.TEXT_PLAIN),
        )

        self.assertEqual(
            f'<a href="{img.get_absolute_url()}" target="_self">{img.name}</a>',
            render_field(field_name='image', tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(
            f'<a href="{img.get_absolute_url()}" target="_blank">{img.name}</a>',
            render_field(field_name='image', tag=ViewTag.HTML_FORM),
        )
        self.assertEqual(img.name, render_field(field_name='image', tag=ViewTag.TEXT_PLAIN))

    def test_registry_printers_for_field_type(self):
        "Default."

        def print_integer(*, value, **kwargs):
            return f'#{str(value)}'

        registry = FieldPrinterRegistry().register_model_field_type(
            type=models.IntegerField,
            printer=print_integer,
            tags=ViewTag.HTML_FORM,
        )
        get_printers = registry.printers_for_field_type
        printers1 = [*get_printers(type=models.IntegerField, tags=ViewTag.HTML_FORM)]
        self.assertEqual(1, len(printers1))
        self.assertIs(print_integer, printers1[0])

        printers2 = [*get_printers(type=models.ForeignKey, tags='html*')]
        self.assertEqual(3, len(printers2))
        self.assertIsInstance(printers2[0], FKPrinter)

    def test_registry_register_model_field_type(self):
        "Register by field types, different outputs..."
        user = self.get_root_user()

        print_charfield_html_args = []
        print_charfield_csv_args = []
        print_integerfield_html_args = []

        def print_charfield_html(*, instance, value, user, field):
            print_charfield_html_args.append((instance, value, user, field))
            return f'<span>{value}</span>'

        def print_charfield_csv(*, instance, value, user, field):
            print_charfield_csv_args.append((instance, value, user, field))
            return f'«{value}»'

        def print_integerfield_html(*, instance, value, user, field):
            print_integerfield_html_args.append((instance, value, user, field))
            return f'<span data-type="integer">{value}</span>'

        registry: FieldPrinterRegistry = FieldPrinterRegistry(
        ).register_model_field_type(
            type=models.CharField, printer=print_charfield_html, tags='html*',
        ).register_model_field_type(
            type=models.CharField, printer=print_charfield_csv, tags='text*',
        ).register_model_field_type(
            type=models.IntegerField, printer=print_integerfield_html, tags='html*',
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='NERV', capital=1234)
        orga2 = create_orga(name='Seele')

        render_field = partial(registry.get_field_value, user=user, tag=ViewTag.HTML_DETAIL)
        get_field = FakeOrganisation._meta.get_field

        self.assertEqual(
            '<span>NERV</span>',
            render_field(instance=orga1, field_name='name'),
        )
        self.assertListEqual(
            [(orga1, orga1.name, user, get_field('name'))],
            print_charfield_html_args,
        )

        self.assertEqual(
            '<span>Seele</span>',
            render_field(instance=orga2, field_name='name'),
        )

        self.assertEqual(
            '«NERV»',
            render_field(instance=orga1, field_name='name', tag=ViewTag.TEXT_PLAIN),
        )
        self.assertListEqual(
            [(orga1, orga1.name, user, get_field('name'))],
            print_charfield_csv_args,
        )

        self.assertEqual(
            '<span data-type="integer">1234</span>',
            render_field(instance=orga1, field_name='capital'),
        )
        self.assertListEqual(
            [(orga1, orga1.capital, user, get_field('capital'))],
            print_integerfield_html_args,
        )

    def test_registry_register_model_field(self):
        user = self.get_root_user()

        print_lastname_html_args = []

        def print_charfield_html(*, instance, value, user, field):
            return f'<span>{value}</span>'

        def print_lastname_html(*, instance, value, user, field):
            print_lastname_html_args.append((instance, value, user, field))
            return f'<span class="lastname">{value}</span>'

        def print_charfield_csv(*, instance, value, user, field):
            return f'«{value}»'

        registry = FieldPrinterRegistry(
        ).register_model_field_type(
            type=models.CharField, printer=print_charfield_html, tags=ViewTag.HTML_DETAIL,
        ).register_model_field(
            model=FakeContact, field_name='last_name', printer=print_lastname_html, tags='html*',
        ).register_model_field_type(
            type=models.CharField, printer=print_charfield_csv, tags=[ViewTag.TEXT_PLAIN],
        )

        rei = FakeContact(first_name='Rei', last_name='Ayanami')

        self.assertEqual(
            f'<span>{rei.first_name}</span>',
            registry.get_field_value(
                instance=rei, field_name='first_name', user=user, tag=ViewTag.HTML_DETAIL,
            ),
        )

        self.assertEqual(
            f'<span class="lastname">{rei.last_name}</span>',
            registry.get_field_value(
                instance=rei, field_name='last_name', user=user, tag=ViewTag.HTML_DETAIL,
            ),
        )
        self.assertListEqual(
            [(rei, rei.last_name, user, FakeContact._meta.get_field('last_name'))],
            print_lastname_html_args,
        )

        with self.assertRaises(FieldDoesNotExist):
            registry.register_model_field(
                model=FakeContact, field_name='unknown', printer=print_lastname_html,
                tags=ViewTag.HTML_DETAIL,
            )

    def test_registry_print_choice(self):
        user = self.user

        registry = FieldPrinterRegistry()
        render_field = partial(
            registry.get_field_value, user=user, field_name='discount_unit',
        )

        l1 = FakeInvoiceLine(discount_unit=FakeInvoiceLine.Discount.PERCENT)
        expected1 = _('Percent')
        self.assertEqual(expected1, render_field(instance=l1, tag=ViewTag.HTML_DETAIL))
        self.assertEqual(expected1, render_field(instance=l1, tag=ViewTag.TEXT_PLAIN))

        l2 = FakeInvoiceLine(discount_unit=FakeInvoiceLine.Discount.AMOUNT)
        expected2 = _('Amount')
        self.assertEqual(expected2, render_field(instance=l2, tag=ViewTag.HTML_DETAIL))
        self.assertEqual(expected2, render_field(instance=l2, tag=ViewTag.TEXT_PLAIN))

        l3 = FakeInvoiceLine(discount_unit=None)
        self.assertEqual('', render_field(instance=l3, tag=ViewTag.HTML_DETAIL))
        self.assertEqual('', render_field(instance=l3, tag=ViewTag.TEXT_PLAIN))

    def test_registry_register_choice_printer01(self):
        user = self.user

        registry = FieldPrinterRegistry()

        def print_choices_html(*, instance, value, user, field):
            return '<em>{}</em>'.format(getattr(instance, f'get_{field.name}_display')())

        def print_choices_csv(*, instance, value, user, field):
            return getattr(instance, f'get_{field.name}_display')().upper()

        registry.register_choice_printer(
            print_choices_html, tags=[ViewTag.HTML_DETAIL, ViewTag.HTML_LIST],
        ).register_choice_printer(
            print_choices_csv, tags=ViewTag.TEXT_PLAIN,
        )

        line = FakeInvoiceLine(discount_unit=FakeInvoiceLine.Discount.PERCENT)
        label = _('Percent')
        self.assertEqual(
            f'<em>{label}</em>',
            registry.get_field_value(
                instance=line, field_name='discount_unit', user=user,
                tag=ViewTag.HTML_DETAIL,
            ),
        )
        self.assertEqual(
            label.upper(),
            registry.get_field_value(
                instance=line, field_name='discount_unit', user=user,
            ),
        )

    def test_registry_register_choice_printer02(self):
        "Register choice-printer for specific field."
        user = self.user
        registry = FieldPrinterRegistry()

        def print_discount_html(*, instance, value, user, field):
            return '<em>{}</em>'.format(getattr(instance, f'get_{field.name}_display')())

        registry.register_model_field(
            model=FakeInvoiceLine,
            field_name='discount_unit',
            tags=ViewTag.HTML_DETAIL,
            printer=print_discount_html,
        )

        line = FakeInvoiceLine(discount_unit=FakeInvoiceLine.Discount.PERCENT)
        label = _('Percent')
        self.assertEqual(
            f'<em>{label}</em>',
            registry.get_field_value(
                instance=line, field_name='discount_unit', user=user,
                tag=ViewTag.HTML_DETAIL,
            ),
        )
        self.assertEqual(
            label,
            registry.get_field_value(
                instance=line, field_name='discount_unit', user=user,
            ),
        )  # printer not used (other tag)

        camp = FakeEmailCampaign(status=FakeEmailCampaign.Status.SENT_OK)
        self.assertEqual(
            'Sent',
            registry.get_field_value(
                instance=camp, field_name='status', user=user,
                tag=ViewTag.HTML_DETAIL,
            ),
        )  # printer not used (other field)

    def test_registry_numeric(self):
        user = self.get_root_user()
        field_printer_registry = FieldPrinterRegistry()

        # Integer
        capital = 12345

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Hawk', capital=capital)
        orga2 = create_orga(name='God hand')

        render_f = partial(field_printer_registry.get_field_value, user=user)
        self.assertEqual(str(capital), render_f(instance=orga1, field_name='capital'))
        self.assertEqual('',           render_f(instance=orga2, field_name='capital'))

        # Decimal & integer with choices
        line1 = FakeInvoiceLine(
            item='Swords',  quantity='3.00', unit_price='125.6',
            discount_unit=FakeInvoiceLine.Discount.PERCENT,
        )
        dec_format = partial(number_format)
        self.assertEqual(dec_format('3.00'),  render_f(instance=line1, field_name='quantity'))
        self.assertEqual(dec_format('125.6'), render_f(instance=line1, field_name='unit_price'))

    @override_settings(URLIZE_TARGET_BLANK=True)
    def test_registry_textfield(self):
        "Test TexField: link => target='_blank'."
        user = self.get_root_user()
        field_printer_registry = FieldPrinterRegistry()

        hawk = FakeOrganisation.objects.create(
            user=user, name='Hawk',
            description='A powerful army.\nOfficial site: www.hawk-troop.org',
        )
        self.assertHTMLEqual(
            '<p>A powerful army.<br>'
            'Official site: '
            '<a target="_blank" rel="noopener noreferrer" href="http://www.hawk-troop.org">'
            'www.hawk-troop.org'
            '</a>'
            '</p>',
            field_printer_registry.get_field_value(
                instance=hawk, field_name='description', user=user, tag=ViewTag.HTML_DETAIL,
            ),
        )

    def test_registry_booleanfield(self):
        "Boolean Field."
        user = self.get_root_user()
        field_printer_registry = FieldPrinterRegistry()

        create_contact = partial(FakeContact.objects.create, user=user)
        casca = create_contact(first_name='Casca', last_name='Mylove', is_a_nerd=False)
        judo  = create_contact(first_name='Judo',  last_name='Doe',    is_a_nerd=True)

        render_field = partial(
            field_printer_registry.get_field_value,
            user=user, field_name='is_a_nerd', tag=ViewTag.HTML_DETAIL,
        )
        self.assertEqual(
            '<input type="checkbox" disabled/>' + _('No'),
            render_field(instance=casca),
        )
        self.assertEqual(
            '<input type="checkbox" checked disabled/>' + _('Yes'),
            render_field(instance=judo),
        )

        self.assertEqual(_('No'), render_field(instance=casca, tag=ViewTag.TEXT_PLAIN))
        self.assertEqual(_('Yes'), render_field(instance=judo, tag=ViewTag.TEXT_PLAIN))

    def test_registry_fk(self):
        "ForeignKey."
        user = self.get_root_user()

        field_printer_registry = FieldPrinterRegistry(
        ).register_model_field_type(
            type=models.ForeignKey,
            printer=FKPrinter(
                none_printer=FKPrinter.print_fk_null_html,
                default_printer=simple_print_html,
            ).register(
                CremeEntity, FKPrinter.print_fk_entity_html,
            ),
            tags=ViewTag.HTML_DETAIL,
        ).register_model_field_type(
            type=models.ForeignKey,
            printer=FKPrinter(
                none_printer=FKPrinter.print_fk_null_html,
                default_printer=simple_print_html,
            ).register(
                CremeEntity, partial(FKPrinter.print_fk_entity_html, target='_blank'),
            ),
            tags=ViewTag.HTML_FORM,
        )

        create_cat = FakeImageCategory.objects.create
        cat1 = create_cat(name='Photo of contact')
        cat2 = create_cat(name='Photo of product')

        img = FakeImage.objects.create(
            name="Casca's face", user=user, description="Casca's selfie",
        )
        img.categories.set([cat1, cat2])

        create_contact = partial(FakeContact.objects.create, user=user)
        casca = create_contact(
            first_name='Casca', last_name='Mylove',
            position=FakePosition.objects.create(title='Warrior<script>'),
            image=img,
        )
        judo = create_contact(first_name='Judo', last_name='Doe')

        escaped_title = 'Warrior&lt;script&gt;'

        render_field = partial(
            field_printer_registry.get_field_value,
            user=user, instance=casca, tag=ViewTag.HTML_DETAIL
        )

        self.assertEqual(casca.last_name, render_field(field_name='last_name'))
        self.assertEqual(
            casca.last_name, render_field(field_name='last_name', tag=ViewTag.TEXT_PLAIN),
        )

        self.assertEqual(casca.first_name, render_field(field_name='first_name'))
        self.assertEqual(escaped_title,    render_field(field_name='position'))

        self.assertEqual(escaped_title, render_field(field_name='position__title'))
        self.assertEqual(
            casca.position.title,
            render_field(field_name='position__title', tag=ViewTag.TEXT_PLAIN),
        )

        # FK: with & without customised null_label
        self.assertEqual('', render_field(instance=judo, field_name='position'))
        self.assertEqual(
            '', render_field(instance=judo, field_name='position', tag=ViewTag.TEXT_PLAIN),
        )
        self.assertEqual(
            '<em>{}</em>'.format(pgettext('persons-is_user', 'None')),
            render_field(field_name='is_user'),
        )

        # Null_label not used in TEXT backend
        self.assertEqual('', render_field(field_name='is_user', tag=ViewTag.TEXT_PLAIN))

        self.assertHTMLEqual(
            f'<a href="{img.get_absolute_url()}" target="_self">{escape(img)}</a>',
            render_field(field_name='image', tag=ViewTag.HTML_DETAIL),
        )
        self.assertHTMLEqual(
            f'<a href="{img.get_absolute_url()}" target="_blank">{escape(img)}</a>',
            render_field(field_name='image', tag=ViewTag.HTML_FORM),
        )
        self.assertEqual(
            str(casca.image), render_field(field_name='image', tag=ViewTag.TEXT_PLAIN),
        )

        self.assertEqual(
            '<p>Casca&#x27;s selfie</p>',
            render_field(field_name='image__description'),
        )
        self.assertEqual(
            casca.image.description,
            render_field(field_name='image__description', tag=ViewTag.TEXT_PLAIN),
        )

        local_dt = localtime(casca.created)
        self.assertHTMLEqual(
            '<span class="datetime-field" title="{seconds}">{dt}</span>'.format(
                seconds=_('Seconds: {}').format(local_dt.second),
                dt=date_format(local_dt, 'DATETIME_FORMAT'),
            ),
            render_field(field_name='created'),
        )

        self.assertEqual(
            f'<ul class="limited-list"><li>{cat1.name}</li><li>{cat2.name}</li></ul>',
            render_field(field_name='image__categories'),
        )
        self.assertEqual(
            f'{cat1.name}/{cat2.name}',
            render_field(field_name='image__categories', tag=ViewTag.TEXT_PLAIN),
        )
        # TODO: test ImageField

        self.assertEqual('', render_field(instance=judo, field_name='position__title'))
        self.assertEqual('', render_field(instance=judo, field_name='image'))
        self.assertEqual('', render_field(instance=judo, field_name='image__description'))
        self.assertEqual('', render_field(instance=judo, field_name='image__categories'))

        # depth = 2
        self.assertEqual(str(user), render_field(field_name='image__user'))

        # depth = 3
        self.assertEqual(user.username, render_field(field_name='image__user__username'))

    def test_registry_m2m01(self):
        user = self.get_root_user()
        registry = FieldPrinterRegistry()

        img = FakeImage.objects.create(user=user, name='My img')
        img.categories.set([
            FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')
        ])

        render_field = partial(
            registry.get_field_value, instance=img, user=user, tag=ViewTag.HTML_DETAIL,
        )
        self.assertHTMLEqual(
            '<ul class="limited-list"><li>A</li><li>B</li><li>C</li></ul>',
            render_field(field_name='categories'),
        )
        self.assertEqual('A/B/C', render_field(field_name='categories', tag=ViewTag.TEXT_PLAIN))

        self.assertHTMLEqual(
            '<ul class="limited-list"><li>A</li><li>B</li><li>C</li></ul>',
            render_field(field_name='categories__name'),
        )
        self.assertEqual(
            'A/B/C',
            render_field(field_name='categories__name', tag=ViewTag.TEXT_PLAIN),
        )

        # Truncated render ---
        with self.settings(CELL_SIZE=2):
            message = ngettext(
                '{count} more element', '{count} more elements', 1,
            ).format(count=1)
            self.assertHTMLEqual(
                f'<ul class="limited-list">'
                f' <li>A</li>'
                f' <li>B</li>'
                f' <li><span class="more-elements">{message}</span></li>'
                f'</ul>',
                render_field(field_name='categories__name'),
            )

            self.assertEqual(
                'A/B/C',
                render_field(field_name='categories__name', tag=ViewTag.TEXT_PLAIN),
            )

    def test_registry_m2m02(self):
        "Empty sub-values."
        user1 = self.get_root_user()
        user2 = self.create_user(0, theme='')
        team = self.create_team('Team17', user1, user2)

        registry = FieldPrinterRegistry()
        theme1 = settings.THEMES[0][1]
        self.assertHTMLEqual(
            theme1,
            registry.get_field_value(
                instance=team, field_name='teammates_set__theme', user=user1,
                tag=ViewTag.HTML_DETAIL,
            ),
        )
        self.assertEqual(
            theme1,
            registry.get_field_value(
                instance=team, field_name='teammates_set__theme', user=user1,
            ),
        )

    def test_registry_m2m_entity01(self):
        user = self.get_root_user()
        registry = FieldPrinterRegistry()

        create_ml = partial(FakeMailingList.objects.create, user=user)
        ml1 = create_ml(name='Swimsuits', description='Best swimsuits of this year')
        ml2 = create_ml(name='Hats')  # Notice that description is empty

        camp = FakeEmailCampaign.objects.create(user=user, name='Summer 2020')
        camp.mailing_lists.set([ml1, ml2])

        render_field = partial(registry.get_field_value, instance=camp, user=user)

        self.assertHTMLEqual(
            f'<ul class="limited-list"><li>{ml2.name}</li><li>{ml1.name}</li></ul>',
            render_field(field_name='mailing_lists__name', tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(
            f'{ml2.name}/{ml1.name}',
            render_field(field_name='mailing_lists__name', tag=ViewTag.TEXT_PLAIN),
        )

        self.assertHTMLEqual(
            f'<p>{ml1.description}</p>',
            render_field(field_name='mailing_lists__description', tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(
            ml1.description,
            render_field(field_name='mailing_lists__description', tag=ViewTag.TEXT_PLAIN),
        )

    def test_registry_m2m_entity02(self):
        "Credentials."
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

        create_ml = FakeMailingList.objects.create
        ml1 = create_ml(user=user, name='Swimsuits')
        ml2 = create_ml(user=self.get_root_user(), name='Hats')

        camp = FakeEmailCampaign.objects.create(user=user, name='Summer 2020')
        camp.mailing_lists.set([ml1, ml2])

        registry = FieldPrinterRegistry()
        self.assertHTMLEqual(
            f'<ul class="limited-list"><li>{settings.HIDDEN_VALUE}</li><li>{ml1.name}</li></ul>',
            registry.get_field_value(
                instance=camp, field_name='mailing_lists__name', user=user,
                tag=ViewTag.HTML_DETAIL,
            ),
        )
        self.assertEqual(
            f'{settings.HIDDEN_VALUE}/{ml1.name}',
            registry.get_field_value(
                instance=camp, field_name='mailing_lists__name', user=user,
            ),
        )

    def test_registry_m2m_entity03(self):
        "Deleted entity."
        user = self.get_root_user()

        create_ml = partial(FakeMailingList.objects.create, user=user)
        ml1 = create_ml(name='Swimsuits')
        ml2 = create_ml(name='Hats', is_deleted=True)

        camp = FakeEmailCampaign.objects.create(user=user, name='Summer 2020')
        camp.mailing_lists.set([ml1, ml2])

        registry = FieldPrinterRegistry()
        self.assertHTMLEqual(
            ml1.name,
            registry.get_field_value(
                instance=camp, field_name='mailing_lists__name', user=user,
                tag=ViewTag.HTML_DETAIL,
            ),
        )
        self.assertEqual(
            ml1.name,
            registry.get_field_value(
                instance=camp, field_name='mailing_lists__name', user=user,
            ),
        )

    def test_registry_credentials(self):
        user = self.login_as_standard(allowed_apps=['creme_core'])
        self.add_credentials(user.role, own='*')

        field_printer_registry = FieldPrinterRegistry()

        create_img = FakeImage.objects.create
        casca_face = create_img(
            name='Casca face', user=self.get_root_user(), description="Casca's selfie",
        )
        judo_face = create_img(
            name='Judo face',  user=user, description="Judo's selfie"
        )
        self.assertTrue(user.has_perm_to_view(judo_face))
        self.assertFalse(user.has_perm_to_view(casca_face))

        create_contact = partial(FakeContact.objects.create, user=user)
        casca = create_contact(first_name='Casca', last_name='Mylove', image=casca_face)
        judo  = create_contact(first_name='Judo',  last_name='Doe',    image=judo_face)

        render_field = partial(
            field_printer_registry.get_field_value, user=user, tag=ViewTag.HTML_DETAIL,
        )
        self.assertHTMLEqual(
            f'<a href="{judo_face.get_absolute_url()}" target="_self">{judo_face}</a>',
            render_field(instance=judo, field_name='image')
        )
        self.assertEqual(
            '<p>Judo&#x27;s selfie</p>',
            render_field(instance=judo, field_name='image__description')
        )

        HIDDEN_VALUE = settings.HIDDEN_VALUE
        self.assertEqual(
            HIDDEN_VALUE, render_field(instance=casca, field_name='image'),
        )
        self.assertEqual(
            HIDDEN_VALUE, render_field(instance=casca, field_name='image__description'),
        )
        self.assertEqual(
            HIDDEN_VALUE, render_field(instance=casca, field_name='image__categories'),
        )

        self.assertEqual(
            HIDDEN_VALUE,
            render_field(instance=casca, field_name='image', tag=ViewTag.TEXT_PLAIN),
        )
        self.assertEqual(
            HIDDEN_VALUE,
            render_field(instance=casca, field_name='image__description', tag=ViewTag.TEXT_PLAIN),
        )
        self.assertEqual(
            HIDDEN_VALUE,
            render_field(instance=casca, field_name='image__categories', tag=ViewTag.TEXT_PLAIN),
        )

    @override_settings(
        CSS_DEFAULT_LISTVIEW='field-default',
        CSS_NUMBER_LISTVIEW='field-number',
        CSS_TEXTAREA_LISTVIEW='field-long_text',
        CSS_DEFAULT_HEADER_LISTVIEW='header-default',
        CSS_DATE_HEADER_LISTVIEW='header-date',
    )
    def test_registry_css(self):
        registry = FieldPrinterRegistry()
        get_css = registry.get_listview_css_class_for_field
        get_header_css = registry.get_header_listview_css_class_for_field

        self.assertEqual('field-default',   get_css(models.CharField))
        self.assertEqual('field-number',    get_css(models.IntegerField))
        self.assertEqual('field-number',    get_css(models.DecimalField))
        self.assertEqual('field-long_text', get_css(models.TextField))

        self.assertEqual('header-default', get_header_css(models.CharField))
        self.assertEqual('header-default', get_header_css(models.IntegerField))
        self.assertEqual('header-date',    get_header_css(models.DateField))

        integer_css = 'field-integer'
        integer_header = 'header-integer'
        registry.register_listview_css_class(
            field=models.IntegerField,
            css_class=integer_css,
            header_css_class=integer_header,
        )
        self.assertEqual(integer_css,    get_css(models.IntegerField))
        self.assertEqual('field-number', get_css(models.DecimalField))

        self.assertEqual('header-default', get_header_css(models.CharField))
        self.assertEqual(integer_header,   get_header_css(models.IntegerField))

    # TODO: test image_size()
    # TODO: test print_duration()
