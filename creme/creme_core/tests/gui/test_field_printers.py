# -*- coding: utf-8 -*-

from datetime import date
from decimal import Decimal
from functools import partial
from os.path import basename

from django.conf import settings
from django.db import models
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import date_format, number_format
from django.utils.html import escape
from django.utils.timezone import localtime
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.download import filefield_download_registry
from creme.creme_core.core.entity_filter import operators
from creme.creme_core.core.entity_filter.condition_handler import (
    RegularFieldConditionHandler,
)
# from creme.creme_core.gui.field_printers import print_integer, print_decimal, M2MPrinter
from creme.creme_core.gui.field_printers import (
    FKPrinter,
    M2MPrinterForHTML,
    _FieldPrintersRegistry,
    print_boolean_csv,
    print_boolean_html,
    print_choice,
    print_date,
    print_datetime,
    print_decimal_csv,
    print_decimal_html,
    print_email_html,
    print_file_html,
    print_foreignkey_csv,
    print_foreignkey_html,
    print_image_html,
    print_integer_html,
    print_many2many_csv,
    print_text_html,
    print_unsafehtml_html,
    print_url_html,
    simple_print_csv,
    simple_print_html,
)
from creme.creme_core.models import (
    CremeEntity,
    CremeUser,
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
    SetCredentials,
)
# from ..fake_constants import FAKE_AMOUNT_UNIT, FAKE_PERCENT_UNIT
from creme.creme_core.tests.base import CremeTestCase


class FieldsPrintersTestCase(CremeTestCase):
    def test_simple_print_html(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('first_name')
        self.assertEqual(
            '',
            simple_print_html(c, fval=None, user=user, field=field)
        )

        value = 'Rei'
        self.assertEqual(
            value,
            simple_print_html(c, value, user, field),
        )

        self.assertEqual(
            '&lt;b&gt;Rei&lt;b&gt;',
            simple_print_html(c, '<b>Rei<b>', user, field),
        )

    def test_simple_print_csv(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('first_name')
        self.assertEqual(
            '',
            simple_print_csv(c, fval=None, user=user, field=field),
        )

        value = 'Rei'
        self.assertEqual(
            value,
            simple_print_csv(c, value, user, field),
        )

    def test_print_choice(self):
        user = CremeUser()
        field = FakeInvoiceLine._meta.get_field('discount_unit')

        # line1 = FakeInvoiceLine(discount_unit=FAKE_PERCENT_UNIT)
        line1 = FakeInvoiceLine(discount_unit=FakeInvoiceLine.Discount.PERCENT)
        self.assertEqual(
            _('Percent'),
            print_choice(line1, fval='whatever', user=user, field=field),
        )

        # line2 = FakeInvoiceLine(discount_unit=FAKE_AMOUNT_UNIT)
        line2 = FakeInvoiceLine(discount_unit=FakeInvoiceLine.Discount.AMOUNT)
        self.assertEqual(
            _('Amount'),
            print_choice(line2, fval='whatever', user=user, field=field),
        )

        line3 = FakeInvoiceLine(discount_unit=None)
        self.assertEqual(
            '',
            print_choice(line3, fval='whatever', user=user, field=field),
        )

    # def test_print_integer01(self):  # DEPRECATED
    #     o = FakeOrganisation()
    #     user = CremeUser()
    #     field = o._meta.get_field('capital')
    #     self.assertEqual(
    #         '',
    #         print_integer(o, fval=None, user=user, field=field)
    #     )
    #     self.assertEqual(
    #         '1234',
    #         print_integer(o, fval=1234, user=user, field=field)
    #     )

    # def test_print_integer02(self):  # DEPRECATED
    #     "Choices."
    #     l1 = FakeInvoiceLine(discount_unit=FAKE_PERCENT_UNIT)
    #     user = CremeUser()
    #     field = type(l1)._meta.get_field('discount_unit')
    #     self.assertEqual(
    #         _('Percent'),
    #         print_integer(l1, fval=None, user=user, field=field)
    #     )
    #
    #     l2 = FakeInvoiceLine(discount_unit=FAKE_AMOUNT_UNIT)
    #     self.assertEqual(
    #         _('Amount'),
    #         print_integer(l2, fval=None, user=user, field=field)
    #     )

    def _aux_print_integer_html01(self):
        o = FakeOrganisation()
        user = CremeUser()
        field = o._meta.get_field('capital')
        self.assertEqual(
            '',
            print_integer_html(o, fval=None, user=user, field=field)
        )

        value = 1234
        self.assertEqual(
            number_format(value, use_l10n=True, force_grouping=True),
            print_integer_html(o, fval=value, user=user, field=field)
        )

    @override_settings(USE_THOUSAND_SEPARATOR=True)
    def test_print_integer_html01(self):
        return self._aux_print_integer_html01()

    @override_settings(USE_THOUSAND_SEPARATOR=False)
    def test_print_integer_html02(self):
        return self._aux_print_integer_html01()

    # def test_print_decimal(self):  # DEPRECATED
    #     line = FakeInvoiceLine()
    #     user = CremeUser()
    #     field = line._meta.get_field('discount')
    #     self.assertEqual(
    #         '',
    #         print_decimal(line, fval=None, user=user, field=field)
    #     )
    #
    #     value = Decimal('1234.56')
    #     self.assertEqual(
    #         number_format(value, use_l10n=True),
    #         print_decimal(line, fval=value, user=user, field=field)
    #     )

    def test_print_decimal_html(self):
        line = FakeInvoiceLine()
        user = CremeUser()
        field = line._meta.get_field('discount')
        self.assertEqual(
            '',
            print_decimal_html(line, fval=None, user=user, field=field)
        )

        value = Decimal('1234.56')
        self.assertEqual(
            number_format(value, use_l10n=True, force_grouping=True),
            print_decimal_html(line, fval=value, user=user, field=field)
        )

    def test_print_decimal_csv(self):
        line = FakeInvoiceLine()
        user = CremeUser()
        field = line._meta.get_field('discount')
        self.assertEqual(
            '',
            print_decimal_csv(line, fval=None, user=user, field=field)
        )

        value = Decimal('1234.56')
        self.assertEqual(
            number_format(value, use_l10n=True),
            print_decimal_csv(line, fval=value, user=user, field=field)
        )

    def test_print_boolean_html(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('is_a_nerd')
        self.assertEqual(
            '',
            print_boolean_html(c, None, user, field)
        )

        self.assertEqual(
            '<input type="checkbox" checked disabled/>{}'.format(_('Yes')),
            print_boolean_html(c, True, user, field)
        )
        self.assertEqual(
            '<input type="checkbox" disabled/>{}'.format(_('No')),
            print_boolean_html(c, False, user, field)
        )

    def test_print_boolean_csv(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('is_a_nerd')
        self.assertEqual(
            '',
            print_boolean_csv(c, None, user, field)
        )

        self.assertEqual(
            _('Yes'),
            print_boolean_csv(c, True, user, field)
        )
        self.assertEqual(
            _('No'),
            print_boolean_csv(c, False, user, field)
        )

    def test_print_url_html(self):
        o = FakeOrganisation()
        user = CremeUser()
        field = o._meta.get_field('url_site')
        self.assertEqual(
            '',
            print_url_html(o, fval=None, user=user, field=field)
        )

        url1 = 'www.wikipedia.org'
        self.assertEqual(
            f'<a href="{url1}" target="_blank">{url1}</a>',
            print_url_html(o, fval=url1, user=user, field=field)
        )

        url2 = '</a><script>Muhaha</script>'
        self.assertEqual(
            '<a href="{url}" target="_blank">{url}</a>'.format(url=escape(url2)),
            print_url_html(o, fval=url2, user=user, field=field)
        )

    def test_print_date(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('birthday')
        self.assertEqual('', print_date(c, None, user, field))

        value = date(year=2019, month=8, day=21)
        self.assertEqual(
            date_format(value, 'DATE_FORMAT'),
            print_date(c, value, user, field)
        )

    def test_print_datetime(self):
        a = FakeActivity()
        user = CremeUser()
        field = a._meta.get_field('start')
        self.assertEqual('', print_datetime(a, None, user, field))

        value = self.create_datetime(year=2019, month=8, day=21, hour=11, minute=30)
        self.assertEqual(
            date_format(value, 'DATETIME_FORMAT'),  # TODO: localtime() ??
            print_datetime(a, value, user, field)
        )

    def test_print_email_html(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('email')
        self.assertEqual('', print_email_html(c, None, user, field))

        value1 = 'contact@foo.bar'
        self.assertEqual(
            f'<a href="mailto:{value1}">{value1}</a>',
            print_email_html(c, value1, user, field)
        )

        value2 = '</a><script>Muhahaha</script>contact@foo.bar'
        self.assertEqual(
            '<a href="mailto:{email}">{email}</a>'.format(email=escape(value2)),
            print_email_html(c, value2, user, field)
        )

    def test_print_text_html(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('description')
        self.assertEqual('', print_text_html(c, None, user, field))

        text = 'See you <b>space</b> cowboy...\nThe real folk blues: www.bebop.org'

        with override_settings(URLIZE_TARGET_BLANK=True):
            p1 = print_text_html(c, user=user, field=field, fval=text)

        self.assertHTMLEqual(
            '<p>See you &lt;b&gt;space&lt;/b&gt; cowboy...<br>The real folk blues: '
            '<a target="_blank" rel="noopener noreferrer" href="http://www.bebop.org">'
            'www.bebop.org'
            '</a>'
            '</p>',
            p1
        )

        with override_settings(URLIZE_TARGET_BLANK=False):
            p2 = print_text_html(c, user=user, field=field, fval=text)

        self.assertEqual(
            '<p>See you &lt;b&gt;space&lt;/b&gt; cowboy...<br>The real folk blues: '
            '<a href="http://www.bebop.org">www.bebop.org</a>'
            '</p>',
            p2
        )

    def test_print_unsafehtml_html(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('description')
        self.assertEqual('', print_unsafehtml_html(c, None, user, field))

        self.assertEqual(
            '<p>&lt;p&gt;See you space cowboy...&lt;/p&gt;</p>',
            print_unsafehtml_html(
                c, user=user, field=field,
                fval='<p>See you space cowboy...</p>',
            )
        )

    def test_print_file_html01(self):
        "Not image."
        user = self.create_user()
        folder = FakeFolder.objects.create(user=user, title='TestGui')

        file_name = 'FieldsPrintersTestCase_test_print_file_html01.txt'
        file_path = self.create_uploaded_file(file_name=file_name, dir_name='gui')
        doc1 = FakeDocument.objects.create(
            user=user,
            linked_folder=folder,
            filedata=file_path,
        )
        self.assertHTMLEqual(
            '<a href="{url}" alt="{label}">{label}</a>'.format(
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
                doc1,
                doc1.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            )
        )

        # ---
        doc2 = FakeDocument.objects.create(
            user=user,
            linked_folder=folder,
            # filedata=file_path,
        )
        self.assertEqual(
            '',
            print_file_html(
                doc2,
                doc2.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            )
        )

    @override_settings(ALLOWED_IMAGES_EXTENSIONS=['gif', 'png', 'jpg'])
    def test_print_file_html02(self):
        "Image."
        user = self.create_user()
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
            """<a onclick="creme.dialogs.image('{url}').open();">
                <img src="{url}" alt="{label}" width="200.0" height="200.0" />
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
                doc1,
                doc1.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            )
        )

        # ---
        doc2 = FakeDocument.objects.create(
            user=user,
            linked_folder=folder,
            # filedata=file_path,
        )
        self.assertHTMLEqual(
            '',
            print_file_html(
                doc2,
                doc2.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            )
        )

    @override_settings(ALLOWED_IMAGES_EXTENSIONS=['gif', 'jpg'])  # Not 'png'
    def test_print_file_html03(self):
        "Not allowed image extensions."
        user = self.create_user()
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
            '<a href="{url}" alt="{label}">{label}</a>'.format(
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
                doc,
                doc.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            )
        )

    def test_print_file_html04(self):
        "Field not registered for download."
        user = self.create_user()

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
            # f'upload/creme_core-tests/gui/{file_name}',
            f'creme_core-tests/gui/{file_name}',
            print_file_html(
                comp,
                comp.filedata,
                user=user,
                field=FakeFileComponent._meta.get_field('filedata'),
            )
        )

    @override_settings(ALLOWED_IMAGES_EXTENSIONS=['gif', 'png', 'jpg'])
    def test_print_image_html(self):
        user = self.create_user()
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
            """<a onclick="creme.dialogs.image('{url}').open();">
                <img src="{url}" alt="{label}" width="200.0" height="200.0" />
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
                doc1,
                doc1.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            )
        )

        # ---
        doc2 = FakeDocument.objects.create(
            user=user,
            linked_folder=folder,
            # filedata=file_path,
        )
        self.assertHTMLEqual(
            '',
            print_image_html(
                doc2,
                doc2.filedata,
                user=user,
                field=FakeDocument._meta.get_field('filedata'),
            )
        )

    def test_fk_printer01(self):
        user = self.create_user()

        c = FakeContact()
        field1 = c._meta.get_field('sector')

        printer = FKPrinter(
            none_printer=FKPrinter.print_fk_null_html,
            default_printer=simple_print_html,
        )

        self.assertEqual('', printer(c, None, user, field1))

        sector = FakeSector.objects.first()
        self.assertEqual(str(sector), printer(c, sector, user, field1))

        # entity without specific handler ---
        img = FakeImage.objects.create(user=user, name='Img#1')
        field2 = c._meta.get_field('image')
        self.assertEqual(str(img), printer(c, img, user, field2))

        # null_label ---
        field3 = c._meta.get_field('is_user')
        self.assertEqual(
            '<em>{}</em>'.format(pgettext('persons-is_user', 'None')),
            printer(c, None, user, field3)
        )

    def test_fk_printer02(self):
        "CremeEntity."
        user = self.create_user()
        c = FakeContact()
        field = c._meta.get_field('image')

        printer = FKPrinter(
            none_printer=FKPrinter.print_fk_null_html,
            default_printer=simple_print_html,
        ).register(CremeEntity, FKPrinter.print_fk_entity_html)

        img = FakeImage.objects.create(user=user, name='Img#1')
        self.assertEqual(
            f'<a href="{img.get_absolute_url()}">{img}</a>',
            printer(c, img, user, field)
        )

    def test_fk_printer03(self):
        "EntityFilter."
        user = self.create_user()

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
            '<div class="entity_filter-summary">{name}'
            '  <ul>'
            '    <li>{cond1}</li>'
            '    <li>{cond2}</li>'
            '  </ul>'
            '</div>'.format(
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
            print_foreignkey_html(r, efilter, user, field)
        )

    def test_print_foreignkey_csv01(self):
        user = self.create_user()

        c = FakeContact()
        field1 = c._meta.get_field('sector')

        self.assertEqual(
            '',
            print_foreignkey_csv(c, None, user, field1)
        )

        sector = FakeSector.objects.first()
        self.assertEqual(
            str(sector),
            print_foreignkey_csv(c, sector, user, field1)
        )

        # entity (credentials OK)
        img = FakeImage.objects.create(user=user, name='Img#1')
        field2 = c._meta.get_field('image')
        self.assertEqual(
            str(img),
            print_foreignkey_csv(c, img, user, field2)
        )

    def test_print_foreignkey_csv02(self):
        "No view credentials."
        user = self.login(is_superuser=False)

        c = FakeContact()
        img = FakeImage.objects.create(user=user, name='Img#1')
        field = c._meta.get_field('image')
        self.assertEqual(
            settings.HIDDEN_VALUE,
            print_foreignkey_csv(c, img, user, field)
        )

    # def test_m2m_printer(self):  # DEPRECATED
    #     user = self.create_user()
    #     img = FakeImage.objects.create(user=user, name='My img')
    #     field = img._meta.get_field('categories')
    #
    #     printer = M2MPrinter(
    #         default_printer=M2MPrinter.printer_html,
    #         default_enumerator=M2MPrinter.enumerator_all,
    #     )
    #
    #     self.assertEqual('', printer(img, img.categories, user, field))
    #
    #     img.categories.set([
    #         FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')
    #     ])
    #     self.assertHTMLEqual(
    #         '<ul><li>A</li><li>B</li><li>C</li></ul>',
    #         printer(img, img.categories, user, field)
    #     )

    def test_many2many_printer_html01(self):
        user = self.create_user()
        img = FakeImage.objects.create(user=user, name='My img')
        field = img._meta.get_field('categories')

        printer = M2MPrinterForHTML(
            default_printer=M2MPrinterForHTML.printer_html,
            default_enumerator=M2MPrinterForHTML.enumerator_all,
        )

        self.assertEqual('', printer(img, img.categories, user, field))

        img.categories.set([
            FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')
        ])
        self.assertHTMLEqual(
            '<ul><li>A</li><li>B</li><li>C</li></ul>',
            printer(img, img.categories, user, field)
        )

    def test_many2many_printer_html02(self):
        "Entity without specific handler."
        user = self.create_user()
        prod = FakeProduct.objects.create(user=user, name='Bebop')
        field = prod._meta.get_field('images')

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='My img#1')
        img2 = create_img(name='My img#2')
        prod.images.set([img1, img2])

        printer = M2MPrinterForHTML(
            default_printer=M2MPrinterForHTML.printer_html,
            default_enumerator=M2MPrinterForHTML.enumerator_all,
        )
        self.assertHTMLEqual(
            f'<ul><li>{img1}</li><li>{img2}</li></ul>',
            printer(prod, prod.images, user, field)
        )

    def test_many2many_printer_html03(self):
        "Entity printer."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        prod = FakeProduct.objects.create(user=user, name='Bebop')
        field = prod._meta.get_field('images')

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='My img#1')
        img2 = create_img(name='My img#2', user=self.other_user)
        img3 = create_img(name='My img#3', is_deleted=True)
        prod.images.set([img1, img2, img3])

        printer = M2MPrinterForHTML(
            default_printer=M2MPrinterForHTML.printer_html,
            default_enumerator=M2MPrinterForHTML.enumerator_all,
        ).register(
            CremeEntity,
            # TODO: test is_deleted too (other enumerator)
            printer=M2MPrinterForHTML.printer_entity_html,
            enumerator=M2MPrinterForHTML.enumerator_entity,
        )
        self.assertHTMLEqual(
            f'<ul>'
            f' <li><a target="_blank" href="{img1.get_absolute_url()}">{img1}</a></li>'
            f' <li>{settings.HIDDEN_VALUE}</li>'
            f'</ul>',
            printer(prod, prod.images, user, field)
        )

    def test_print_many2many_csv01(self):
        user = self.create_user()
        img = FakeImage.objects.create(user=user, name='My img')
        field = img._meta.get_field('categories')

        self.assertEqual(
            '',
            print_many2many_csv(img, img.categories, user, field)
        )

        img.categories.set([
            FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')
        ])
        self.assertHTMLEqual(
            'A/B/C',
            print_many2many_csv(img, img.categories, user, field)
        )

    def test_print_many2many_csv02(self):
        "Entity printer."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        prod = FakeProduct.objects.create(user=user, name='Bebop')
        field = prod._meta.get_field('images')

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='My img#1')
        img2 = create_img(name='My img#2', user=self.other_user)
        img3 = create_img(name='My img#3', is_deleted=True)
        prod.images.set([img1, img2, img3])

        self.assertHTMLEqual(
            f'{img1}/{settings.HIDDEN_VALUE}',
            print_many2many_csv(prod, prod.images, user, field)
        )

    def test_registry(self):
        "Default."
        user = CremeUser()

        registry = _FieldPrintersRegistry()
        as_html = registry.get_html_field_value
        as_csv = registry.get_csv_field_value

        sector = FakeSector.objects.all()[0]
        o = FakeOrganisation(
            user=user, name='Mars', url_site='www.mars.info', sector=sector,
        )

        self.assertEqual(o.name, as_html(o, 'name', user))
        self.assertEqual(o.name, as_csv(o, 'name', user))

        self.assertHTMLEqual(
            '<a href="{url}" target="_blank">{url}</a>'.format(url=o.url_site),
            as_html(o, 'url_site', user),
        )
        self.assertEqual(o.url_site, as_csv(o, 'url_site', user))

        self.assertEqual(sector.title, as_html(o, 'sector', user))
        self.assertEqual(sector.title, as_csv(o, 'sector', user))

        self.assertEqual(sector.title, as_html(o, 'sector__title', user))
        self.assertEqual(sector.title, as_csv(o, 'sector__title', user))

    def test_registry02(self):
        "Register by field types, different outputs..."
        user = self.create_user()

        print_charfield_html_args = []
        print_integerfield_html_args = []

        def print_charfield_html(entity, fval, user, field):
            print_charfield_html_args.append((entity, fval, user, field))
            return f'<span>{fval}</span>'

        def print_charfield_csv(entity, fval, user, field):
            return f'«{fval}»'

        def print_integerfield_html(entity, fval, user, field):
            print_integerfield_html_args.append((entity, fval, user, field))
            return f'<span data-type="integer">{fval}</span>'

        registry = _FieldPrintersRegistry(
        ).register(
            models.CharField, print_charfield_html
        ).register(
            models.CharField, print_charfield_csv, output='csv',
        ).register(
            models.IntegerField, print_integerfield_html, output='html',
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='NERV', capital=1234)
        orga2 = create_orga(name='Seele')

        get_html_val = registry.get_html_field_value
        get_field = FakeOrganisation._meta.get_field

        self.assertEqual('<span>NERV</span>', get_html_val(orga1, 'name', user))
        self.assertListEqual(
            [(orga1, orga1.name, user, get_field('name'))],
            print_charfield_html_args
        )

        self.assertEqual('<span>Seele</span>', get_html_val(orga2, 'name', user))
        self.assertEqual('«NERV»', registry.get_csv_field_value(orga1, 'name', user))

        self.assertEqual(
            '<span data-type="integer">1234</span>',
            get_html_val(orga1, 'capital', user)
        )
        self.assertListEqual(
            [(orga1, orga1.capital, user, get_field('capital'))],
            print_integerfield_html_args
        )

    def test_registry_choice01(self):
        user = CremeUser()

        registry = _FieldPrintersRegistry()
        as_html = registry.get_html_field_value
        as_csv = registry.get_csv_field_value

        # l1 = FakeInvoiceLine(discount_unit=FAKE_PERCENT_UNIT)
        l1 = FakeInvoiceLine(discount_unit=FakeInvoiceLine.Discount.PERCENT)
        expected1 = _('Percent')
        self.assertEqual(expected1, as_html(l1, 'discount_unit', user))
        self.assertEqual(expected1, as_csv(l1,  'discount_unit', user))

        # l2 = FakeInvoiceLine(discount_unit=FAKE_AMOUNT_UNIT)
        l2 = FakeInvoiceLine(discount_unit=FakeInvoiceLine.Discount.AMOUNT)
        expected2 = _('Amount')
        self.assertEqual(expected2, as_html(l2, 'discount_unit', user))
        self.assertEqual(expected2, as_csv(l2,  'discount_unit', user))

        l3 = FakeInvoiceLine(discount_unit=None)
        self.assertEqual('', as_html(l3, 'discount_unit', user))
        self.assertEqual('', as_csv(l3,  'discount_unit', user))

    def test_registry_choice02(self):
        user = CremeUser()

        registry = _FieldPrintersRegistry()

        def print_choices_html(entity, fval, user, field):
            return '<em>{}</em>'.format(getattr(entity, f'get_{field.name}_display')())

        def print_choices_csv(entity, fval, user, field):
            return getattr(entity, f'get_{field.name}_display')().upper()

        registry.register_choice_printer(
            print_choices_html, output='html',
        ).register_choice_printer(
            print_choices_csv, output='csv',
        )

        # line = FakeInvoiceLine(discount_unit=FAKE_PERCENT_UNIT)
        line = FakeInvoiceLine(discount_unit=FakeInvoiceLine.Discount.PERCENT)
        label = _('Percent')
        self.assertEqual(
            '<em>{}</em>'.format(label),
            registry.get_html_field_value(line, 'discount_unit', user)
        )
        self.assertEqual(
            label.upper(),
            registry.get_csv_field_value(line,  'discount_unit', user)
        )

    def test_registry_numeric(self):
        user = self.create_user()
        field_printers_registry = _FieldPrintersRegistry()

        # Integer
        capital = 12345

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Hawk', capital=capital)
        orga2 = create_orga(name='God hand')

        get_csv_val = field_printers_registry.get_csv_field_value
        self.assertEqual(str(capital), get_csv_val(orga1, 'capital', user))
        self.assertEqual('',           get_csv_val(orga2, 'capital', user))

        # Decimal & integer with choices
        line1 = FakeInvoiceLine(
            item='Swords',  quantity='3.00', unit_price='125.6',
            # discount_unit=FAKE_PERCENT_UNIT,
            discount_unit=FakeInvoiceLine.Discount.PERCENT,
        )
        dec_format = partial(number_format, use_l10n=True)
        self.assertEqual(dec_format('3.00'),  get_csv_val(line1, 'quantity',   user))
        self.assertEqual(dec_format('125.6'), get_csv_val(line1, 'unit_price', user))

    @override_settings(URLIZE_TARGET_BLANK=True)
    def test_registry_textfield(self):
        "Test TexField: link => target='_blank'."
        user = self.create_user()
        field_printers_registry = _FieldPrintersRegistry()

        hawk = FakeOrganisation.objects.create(
            user=user, name='Hawk',
            description='A powerful army.\nOfficial site: www.hawk-troop.org',
        )

        get_html_val = field_printers_registry.get_html_field_value
        self.assertHTMLEqual(
            '<p>A powerful army.<br>'
            'Official site: '
            '<a target="_blank" rel="noopener noreferrer" href="http://www.hawk-troop.org">'
            'www.hawk-troop.org'
            '</a>'
            '</p>',
            get_html_val(hawk, 'description', user)
        )

    def test_registry_booleanfield(self):
        "Boolean Field."
        user = self.create_user()
        field_printers_registry = _FieldPrintersRegistry()

        create_contact = partial(FakeContact.objects.create, user=user)
        casca = create_contact(first_name='Casca', last_name='Mylove', is_a_nerd=False)
        judo  = create_contact(first_name='Judo',  last_name='Doe',    is_a_nerd=True)

        get_html_val = field_printers_registry.get_html_field_value
        self.assertEqual(
            '<input type="checkbox" disabled/>' + _('No'),
            get_html_val(casca, 'is_a_nerd', user)
        )
        self.assertEqual(
            '<input type="checkbox" checked disabled/>' + _('Yes'),
            get_html_val(judo, 'is_a_nerd', user)
        )

        get_csv_val = field_printers_registry.get_csv_field_value
        self.assertEqual(_('No'),  get_csv_val(casca, 'is_a_nerd', user))
        self.assertEqual(_('Yes'), get_csv_val(judo, 'is_a_nerd', user))

    def test_registry_fk(self):
        "ForeignKey."
        user = self.create_user()

        print_foreignkey_html = FKPrinter(
            none_printer=FKPrinter.print_fk_null_html,
            default_printer=simple_print_html,
        )
        print_foreignkey_html.register(
            CremeEntity, FKPrinter.print_fk_entity_html,
        )

        field_printers_registry = _FieldPrintersRegistry()
        field_printers_registry.register(models.ForeignKey, print_foreignkey_html)

        get_html_val = field_printers_registry.get_html_field_value
        get_csv_val  = field_printers_registry.get_csv_field_value

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

        self.assertEqual(casca.last_name,      get_html_val(casca, 'last_name',       user))
        self.assertEqual(casca.last_name,      get_csv_val(casca,  'last_name',       user))

        self.assertEqual(casca.first_name,     get_html_val(casca, 'first_name',      user))
        self.assertEqual(escaped_title,        get_html_val(casca, 'position',        user))

        self.assertEqual(escaped_title,        get_html_val(casca, 'position__title', user))
        self.assertEqual(casca.position.title, get_csv_val(casca,  'position__title', user))

        # FK: with & without customised null_label
        self.assertEqual('', get_html_val(judo, 'position', user))
        self.assertEqual('', get_csv_val(judo,  'position', user))
        self.assertEqual(
            '<em>{}</em>'.format(pgettext('persons-is_user', 'None')),
            get_html_val(casca, 'is_user', user)
        )
        # Null_label not used in CSV backend
        self.assertEqual('', get_csv_val(casca, 'is_user', user))

        self.assertEqual(
            f'<a href="{img.get_absolute_url()}">{escape(img)}</a>',
            get_html_val(casca, 'image', user)
        )
        self.assertEqual(str(casca.image), get_csv_val(casca, 'image', user))

        self.assertEqual(
            # '<p>Casca&#39;s selfie</p>',
            '<p>Casca&#x27;s selfie</p>',
            get_html_val(casca, 'image__description', user)
        )
        self.assertEqual(
            casca.image.description,
            get_csv_val(casca, 'image__description', user)
        )

        date_str = date_format(localtime(casca.created), 'DATETIME_FORMAT')
        self.assertEqual(date_str, get_html_val(casca, 'created', user))
        self.assertEqual(date_str, get_csv_val(casca,  'created', user))

        self.assertEqual(
            f'<ul><li>{cat1.name}</li><li>{cat2.name}</li></ul>',
            get_html_val(casca, 'image__categories', user)
        )
        self.assertEqual(
            f'{cat1.name}/{cat2.name}',
            get_csv_val(casca, 'image__categories', user)
        )
        # TODO: test ImageField

        self.assertEqual('', get_html_val(judo, 'position__title',    user))
        self.assertEqual('', get_html_val(judo, 'image',              user))
        self.assertEqual('', get_html_val(judo, 'image__description', user))
        self.assertEqual('', get_html_val(judo, 'image__categories',  user))

        # depth = 2
        self.assertEqual(str(user), get_html_val(casca, 'image__user', user))

        # depth = 3
        self.assertEqual(user.username, get_html_val(casca, 'image__user__username', user))

    def test_registry_m2m01(self):
        user = self.create_user()

        registry = _FieldPrintersRegistry()
        as_html = registry.get_html_field_value
        as_csv = registry.get_csv_field_value

        img = FakeImage.objects.create(user=user, name='My img')
        img.categories.set([
            FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')
        ])

        self.assertHTMLEqual(
            '<ul><li>A</li><li>B</li><li>C</li></ul>',
            as_html(img, 'categories', user),
        )
        self.assertEqual('A/B/C', as_csv(img, 'categories', user))

        self.assertHTMLEqual(
            '<ul><li>A</li><li>B</li><li>C</li></ul>',
            as_html(img, 'categories__name', user),
        )
        self.assertEqual('A/B/C', as_csv(img, 'categories', user))

    def test_registry_m2m02(self):
        "Empty sub-values."
        user1 = self.create_user(0)
        user2 = self.create_user(1, theme='')

        team = CremeUser.objects.create(username='Team17', is_team=True)
        team.teammates_set.set([user1, user2])

        registry = _FieldPrintersRegistry()
        theme1 = settings.THEMES[0][1]
        self.assertHTMLEqual(
            f'<ul><li>{theme1}</li></ul>',
            registry.get_html_field_value(team, 'teammates_set__theme', user1),
        )
        self.assertEqual(
            theme1,
            registry.get_csv_field_value(team, 'teammates_set__theme', user1)
        )

    def test_registry_m2m_entity01(self):
        user = self.create_user()

        registry = _FieldPrintersRegistry()
        as_html = registry.get_html_field_value
        as_csv = registry.get_csv_field_value

        create_ml = partial(FakeMailingList.objects.create, user=user)
        ml1 = create_ml(name='Swimsuits', description='Best swimsuits of this year')
        ml2 = create_ml(name='Hats')  # Notice that description is empty

        camp = FakeEmailCampaign.objects.create(user=user, name='Summer 2020')
        camp.mailing_lists.set([ml1, ml2])

        self.assertHTMLEqual(
            f'<ul><li>{ml2.name}</li><li>{ml1.name}</li></ul>',
            as_html(camp, 'mailing_lists__name', user),
        )
        self.assertEqual(
            f'{ml2.name}/{ml1.name}',
            as_csv(camp, 'mailing_lists__name', user),
        )

        self.assertHTMLEqual(
            f'<ul><li><p>{ml1.description}</p></li></ul>',
            as_html(camp, 'mailing_lists__description', user),
        )
        self.assertEqual(
            ml1.description,
            as_csv(camp, 'mailing_lists__description', user),
        )

    def test_registry_m2m_entity02(self):
        "Credentials."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        create_ml = FakeMailingList.objects.create
        ml1 = create_ml(user=user, name='Swimsuits')
        ml2 = create_ml(user=self.other_user, name='Hats')

        camp = FakeEmailCampaign.objects.create(user=user, name='Summer 2020')
        camp.mailing_lists.set([ml1, ml2])

        registry = _FieldPrintersRegistry()
        self.assertHTMLEqual(
            f'<ul><li>{settings.HIDDEN_VALUE}</li><li>{ml1.name}</li></ul>',
            registry.get_html_field_value(camp, 'mailing_lists__name', user),
        )
        self.assertEqual(
            f'{settings.HIDDEN_VALUE}/{ml1.name}',
            registry.get_csv_field_value(camp, 'mailing_lists__name', user),
        )

    def test_registry_m2m_entity03(self):
        "Deleted entity."
        user = self.create_user()

        create_ml = partial(FakeMailingList.objects.create, user=user)
        ml1 = create_ml(name='Swimsuits')
        ml2 = create_ml(name='Hats', is_deleted=True)

        camp = FakeEmailCampaign.objects.create(user=user, name='Summer 2020')
        camp.mailing_lists.set([ml1, ml2])

        registry = _FieldPrintersRegistry()
        self.assertHTMLEqual(
            f'<ul><li>{ml1.name}</li></ul>',
            registry.get_html_field_value(camp, 'mailing_lists__name', user),
        )
        self.assertEqual(
            ml1.name,
            registry.get_csv_field_value(camp, 'mailing_lists__name', user),
        )

    def test_registry_credentials(self):
        user = self.login(is_superuser=False, allowed_apps=['creme_core'])
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        field_printers_registry = _FieldPrintersRegistry()

        create_img = FakeImage.objects.create
        casca_face = create_img(
            name='Casca face', user=self.other_user, description="Casca's selfie",
        )
        judo_face = create_img(
            name='Judo face',  user=user, description="Judo's selfie"
        )
        self.assertTrue(user.has_perm_to_view(judo_face))
        self.assertFalse(user.has_perm_to_view(casca_face))

        create_contact = partial(FakeContact.objects.create, user=user)
        casca = create_contact(first_name='Casca', last_name='Mylove', image=casca_face)
        judo  = create_contact(first_name='Judo',  last_name='Doe',    image=judo_face)

        get_html_val = field_printers_registry.get_html_field_value
        self.assertEqual(
            f'<a href="{judo_face.get_absolute_url()}">{judo_face}</a>',
            get_html_val(judo, 'image', user)
        )
        self.assertEqual(
            # '<p>Judo&#39;s selfie</p>',
            '<p>Judo&#x27;s selfie</p>',
            get_html_val(judo, 'image__description', user)
        )

        HIDDEN_VALUE = settings.HIDDEN_VALUE
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image', user))
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image__description', user))
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image__categories', user))

        get_csv_val = field_printers_registry.get_csv_field_value
        self.assertEqual(HIDDEN_VALUE, get_csv_val(casca, 'image', user))
        self.assertEqual(HIDDEN_VALUE, get_csv_val(casca, 'image__description', user))
        self.assertEqual(HIDDEN_VALUE, get_csv_val(casca, 'image__categories', user))

    # TODO: test image_size()
    # TODO: test print_color_html()
    # TODO: test print_duration()
    # TODO: test register_listview_css_class()
    # TODO: test get_listview_css_class_for_field()
    # TODO: test get_header_listview_css_class_for_field()
