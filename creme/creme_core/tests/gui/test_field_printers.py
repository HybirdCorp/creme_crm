# -*- coding: utf-8 -*-

try:
    from datetime import date
    from decimal import Decimal
    from functools import partial

    from django.conf import settings
    from django.test.utils import override_settings
    from django.utils.formats import date_format, number_format
    from django.utils.html import escape
    from django.utils.translation import gettext as _, pgettext

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.core.entity_filter import operators
    from creme.creme_core.core.entity_filter.condition_handler import RegularFieldConditionHandler
    from creme.creme_core.gui import field_printers
    from creme.creme_core.models import (
        CremeUser, SetCredentials,
        CremeEntity, EntityFilter,
        FakeContact,
        FakeOrganisation,
        FakeActivity,
        FakeInvoiceLine,
        FakeSector,
        FakeProduct,
        FakeImage, FakeImageCategory,
        FakeReport,
    )
    from creme.creme_core.tests import fake_constants
    from creme.creme_core.tests.base import CremeTestCase
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class FieldsPrintersTestCase(CremeTestCase):
    def test_simple_print_html(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('first_name')
        self.assertEqual('', field_printers.simple_print_html(c, fval=None, user=user, field=field))

        value = 'Rei'
        self.assertEqual(
            value,
            field_printers.simple_print_html(c, value, user, field)
        )

        self.assertEqual(
            '&lt;b&gt;Rei&lt;b&gt;',
            field_printers.simple_print_html(c, '<b>Rei<b>', user, field)
        )

    def test_simple_print_csv(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('first_name')
        self.assertEqual(
            '',
            field_printers.simple_print_csv(c, fval=None, user=user, field=field)
        )

        value = 'Rei'
        self.assertEqual(
            value,
            field_printers.simple_print_csv(c, value, user, field)
        )

    def test_print_integer01(self):
        o = FakeOrganisation()
        user = CremeUser()
        field = o._meta.get_field('capital')
        self.assertEqual('', field_printers.print_integer(o, fval=None, user=user, field=field))
        self.assertEqual(
            '1234',
            field_printers.print_integer(o, fval=1234, user=user, field=field)
        )

    def test_print_integer02(self):
        "Choices."
        l1 = FakeInvoiceLine(discount_unit=fake_constants.FAKE_PERCENT_UNIT)
        user = CremeUser()
        field = type(l1)._meta.get_field('discount_unit')
        self.assertEqual(
            _('Percent'),
            field_printers.print_integer(l1, fval=None, user=user, field=field)
        )

        l2 = FakeInvoiceLine(discount_unit=fake_constants.FAKE_AMOUNT_UNIT)
        self.assertEqual(
            _('Amount'),
            field_printers.print_integer(l2, fval=None, user=user, field=field)
        )

    def test_print_decimal(self):
        l = FakeInvoiceLine()
        user = CremeUser()
        field = l._meta.get_field('discount')
        self.assertEqual('', field_printers.print_decimal(l, fval=None, user=user, field=field))

        value = Decimal('12.34')
        self.assertEqual(
            number_format(value, use_l10n=True),
            field_printers.print_decimal(l, fval=value, user=user, field=field)
        )

    def test_print_boolean_html(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('is_a_nerd')
        self.assertEqual('', field_printers.print_boolean_html(c, None, user, field))

        self.assertEqual(
            '<input type="checkbox" checked disabled/>{}'.format(_('Yes')),
            field_printers.print_boolean_html(c, True, user, field)
        )
        self.assertEqual(
            '<input type="checkbox" disabled/>{}'.format(_('No')),
            field_printers.print_boolean_html(c, False, user, field)
        )

    def test_print_boolean_csv(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('is_a_nerd')
        self.assertEqual('', field_printers.print_boolean_csv(c, None, user, field))

        self.assertEqual(
            _('Yes'),
            field_printers.print_boolean_csv(c, True, user, field)
        )
        self.assertEqual(
            _('No'),
            field_printers.print_boolean_csv(c, False, user, field)
        )

    def test_print_url_html(self):
        o = FakeOrganisation()
        user = CremeUser()
        field = o._meta.get_field('url_site')
        self.assertEqual('', field_printers.print_url_html(o, fval=None, user=user, field=field))

        url1 = 'www.wikipedia.org'
        self.assertEqual(
            '<a href="{url}" target="_blank">{url}</a>'.format(url=url1),
            field_printers.print_url_html(o, fval=url1, user=user, field=field)
        )

        url2 = '</a><script>Muhaha</script>'
        self.assertEqual(
            '<a href="{url}" target="_blank">{url}</a>'.format(url=escape(url2)),
            field_printers.print_url_html(o, fval=url2, user=user, field=field)
        )

    def test_print_date(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('birthday')
        self.assertEqual('', field_printers.print_date(c, None, user, field))

        value = date(year=2019, month=8, day=21)
        self.assertEqual(
            date_format(value, 'DATE_FORMAT'),
            field_printers.print_date(c, value, user, field)
        )

    def test_print_datetime(self):
        a = FakeActivity()
        user = CremeUser()
        field = a._meta.get_field('start')
        self.assertEqual('', field_printers.print_datetime(a, None, user, field))

        value = self.create_datetime(year=2019, month=8, day=21, hour=11, minute=30)
        self.assertEqual(
            date_format(value, 'DATETIME_FORMAT'),  # TODO: localtime() ??
            field_printers.print_datetime(a, value, user, field)
        )

    def test_print_email_html(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('email')
        self.assertEqual('', field_printers.print_email_html(c, None, user, field))

        value1 = 'contact@foo.bar'
        self.assertEqual(
            '<a href="mailto:{email}">{email}</a>'.format(email=value1),
            field_printers.print_email_html(c, value1, user, field)
        )

        value2 = '</a><script>Muhahaha</script>contact@foo.bar'
        self.assertEqual(
            '<a href="mailto:{email}">{email}</a>'.format(email=escape(value2)),
            field_printers.print_email_html(c, value2, user, field)
        )

    def test_print_text_html(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('description')
        self.assertEqual('', field_printers.print_text_html(c, None, user, field))

        text = 'See you space cowboy...\nThe real folk blues: www.bebop.org'

        with override_settings(URLIZE_TARGET_BLANK=True):
            p1 = field_printers.print_text_html(c, user=user, field=field, fval=text)

        self.assertEqual(
            '<p>See you space cowboy...<br>The real folk blues: '
            '<a target="_blank" rel="noopener noreferrer" href="http://www.bebop.org">www.bebop.org</a>'
            '</p>',
            p1
        )

        with override_settings(URLIZE_TARGET_BLANK=False):
            p2 = field_printers.print_text_html(c, user=user, field=field, fval=text)

        self.assertEqual(
            '<p>See you space cowboy...<br>The real folk blues: '
            '<a href="http://www.bebop.org">www.bebop.org</a>'
            '</p>',
            p2
        )

    def test_print_unsafehtml_html(self):
        c = FakeContact()
        user = CremeUser()
        field = c._meta.get_field('description')
        self.assertEqual('', field_printers.print_unsafehtml_html(c, None, user, field))

        self.assertEqual(
            '<p>&lt;p&gt;See you space cowboy...&lt;/p&gt;</p>',
            field_printers.print_unsafehtml_html(
                c, user=user, field=field,
                fval='<p>See you space cowboy...</p>',
            )
        )

    def test_fk_printer01(self):
        user = self.login()

        c = FakeContact()
        field1 = c._meta.get_field('sector')

        FKPrinter = field_printers.FKPrinter
        printer = FKPrinter(none_printer=FKPrinter.print_fk_null_html,
                            default_printer=field_printers.simple_print_html,
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
        user = self.login()
        c = FakeContact()
        field = c._meta.get_field('image')

        FKPrinter = field_printers.FKPrinter
        printer = FKPrinter(
            none_printer=FKPrinter.print_fk_null_html,
            default_printer=field_printers.simple_print_html,
        ).register(CremeEntity, FKPrinter.print_fk_entity_html)

        img = FakeImage.objects.create(user=user, name='Img#1')
        self.assertEqual(
            '<a href="{}">{}</a>'.format(img.get_absolute_url(), img),
            printer(c, img, user, field)
        )

    def test_fk_printer03(self):
        "EntityFilter."
        user = self.login()

        name = 'Nerv'
        desc1 = 'important'
        desc2 = 'beware'
        efilter = EntityFilter.create(
            pk='test-ef_orga', name='My filter', model=FakeOrganisation, is_custom=True,
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
                '<ul>'
                    '<li>{cond1}</li>'
                    '<li>{cond2}</li>'
                '</ul>'
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
            field_printers.print_foreignkey_html(r, efilter, user, field)
        )

    def test_print_foreignkey_csv01(self):
        user = self.login()

        c = FakeContact()
        field1 = c._meta.get_field('sector')

        self.assertEqual('', field_printers.print_foreignkey_csv(c, None, user, field1))

        sector = FakeSector.objects.first()
        self.assertEqual(
            str(sector),
            field_printers.print_foreignkey_csv(c, sector, user, field1)
        )

        # entity (credentials OK)
        img = FakeImage.objects.create(user=user, name='Img#1')
        field2 = c._meta.get_field('image')
        self.assertEqual(str(img), field_printers.print_foreignkey_csv(c, img, user, field2))

    def test_print_foreignkey_csv02(self):
        "No view credentials."
        user = self.login(is_superuser=False)

        c = FakeContact()
        img = FakeImage.objects.create(user=user, name='Img#1')
        field = c._meta.get_field('image')
        self.assertEqual(
            settings.HIDDEN_VALUE,
            field_printers.print_foreignkey_csv(c, img, user, field)
        )

    def test_m2m_printer01(self):
        user = self.login()
        img = FakeImage.objects.create(user=user, name='My img')
        field = img._meta.get_field('categories')

        M2MPrinter = field_printers.M2MPrinter
        printer = M2MPrinter(
            default_printer=M2MPrinter.printer_html,
            default_enumerator=M2MPrinter.enumerator_all,
        )

        self.assertEqual('', printer(img, img.categories, user, field))

        img.categories.set([
            FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')
        ])
        self.assertHTMLEqual(
            '<ul><li>A</li><li>B</li><li>C</li></ul>',
            printer(img, img.categories, user, field)
        )

    def test_m2m_printer02(self):
        "Entity without specific handler."
        user = self.login()
        prod = FakeProduct.objects.create(user=user, name='Bebop')
        field = prod._meta.get_field('images')

        create_img = partial(FakeImage.objects.create, user=user)
        img1 = create_img(name='My img#1')
        img2 = create_img(name='My img#2')
        prod.images.set([img1, img2])

        M2MPrinter = field_printers.M2MPrinter
        printer = M2MPrinter(
            default_printer=M2MPrinter.printer_html,
            default_enumerator=M2MPrinter.enumerator_all,
        )
        self.assertHTMLEqual(
            '<ul><li>{}</li><li>{}</li></ul>'.format(img1, img2),
            printer(prod, prod.images, user, field)
        )

    def test_m2m_printer03(self):
        "Entity printer."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role,
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

        M2MPrinter = field_printers.M2MPrinter
        printer = M2MPrinter(
            default_printer=M2MPrinter.printer_html,
            default_enumerator=M2MPrinter.enumerator_all,
        ).register(CremeEntity,
                   printer=M2MPrinter.printer_entity_html,  # TODO: test is_deleted too (other enumerator)
                   enumerator=M2MPrinter.enumerator_entity,
                  )
        self.assertHTMLEqual(
            '<ul>'
              '<li><a target="_blank" href="{url1}">{label1}</a></li>'
              '<li>{img2}</li>'
            '</ul>'.format(
                url1=img1.get_absolute_url(),
                label1=img1,
                img2=settings.HIDDEN_VALUE,
            ),
            printer(prod, prod.images, user, field)
        )

    def test_print_many2many_csv01(self):
        user = self.login()
        img = FakeImage.objects.create(user=user, name='My img')
        field = img._meta.get_field('categories')

        self.assertEqual(
            '',
            field_printers.print_many2many_csv(img, img.categories, user, field)
        )

        img.categories.set([
            FakeImageCategory.objects.create(name=name) for name in ('A', 'B', 'C')
        ])
        self.assertHTMLEqual(
            'A/B/C',
            field_printers.print_many2many_csv(img, img.categories, user, field)
        )

    def test_print_many2many_csv02(self):
        "Entity printer."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role,
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
            '{}/{}'.format(img1, settings.HIDDEN_VALUE,),
            field_printers.print_many2many_csv(prod, prod.images, user, field)
        )

    def test_registry(self):
        registry = field_printers._FieldPrintersRegistry()
        o = FakeOrganisation(name='Mars', url_site='www.mars.info')
        user = CremeUser()
        self.assertEqual(
            o.name,
            registry.get_html_field_value(o, 'name', user),
        )
        self.assertEqual(
            o.name,
            registry.get_csv_field_value(o, 'name', user),
        )

        self.assertEqual(
            '<a href="{url}" target="_blank">{url}</a>'.format(url=o.url_site),
            registry.get_html_field_value(o, 'url_site', user),
        )
        self.assertEqual(
            o.url_site,
            registry.get_csv_field_value(o, 'url_site', user),
        )

        # TODO: test with deep fields

    # TODO: test image_size()
    # TODO: test print_color_html()
    # TODO: test print_image_html()
    # TODO: test print_file_html()
    # TODO: test print_duration()
    # TODO: test register_listview_css_class()
    # TODO: test get_listview_css_class_for_field()
    # TODO: test get_header_listview_css_class_for_field()
