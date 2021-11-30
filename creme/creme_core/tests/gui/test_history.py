# -*- coding: utf-8 -*-

import json
from datetime import date
from decimal import Decimal
from functools import partial

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.formats import date_format, number_format
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.auth import EntityCredentials
from creme.creme_core.bricks import HistoryBrick
from creme.creme_core.global_info import clear_global_info
from creme.creme_core.gui.history import (
    HistoryLineExplainer,
    HistoryRegistry,
    html_history_registry,
)
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldEnumValue,
    CustomFieldValue,
    FakeActivity,
    FakeActivityType,
    FakeAddress,
    FakeContact,
    FakeEmailCampaign,
    FakeImage,
    FakeImageCategory,
    FakeInvoice,
    FakeInvoiceLine,
    FakeMailingList,
    FakeOrganisation,
    FakePosition,
    FakeTodo,
    FakeTodoCategory,
    HistoryConfigItem,
    HistoryLine,
    Relation,
    RelationType,
    SetCredentials,
    history,
)

from ..base import CremeTestCase


class HistoryRenderTestCase(CremeTestCase):
    FMT_2_VALUES = _('{field} set to {value}').format
    FMT_3_VALUES = _('{field} changed from {oldvalue} to {value}').format

    @staticmethod
    def get_hline():
        return HistoryLine.objects.order_by('-id').first()

    @staticmethod
    def get_hlines(entity, number):
        return HistoryLine.objects.filter(entity=entity.id).order_by('-id')[:number]

    @staticmethod
    def render_line(hline, user):
        return html_history_registry.line_explainers([hline], user)[0].render()

    def test_render_creation(self):
        user = self.create_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')

        registry = HistoryRegistry()
        self.assertIsList(registry.line_explainers([], user))

        hline = self.get_hline()
        self.assertEqual(history.TYPE_CREATION, hline.type)

        explainers1 = [*registry.line_explainers([hline], user=user)]
        self.assertIsList(explainers1, length=1)

        explainer11 = explainers1[0]
        self.assertIsInstance(explainer11, HistoryLineExplainer)
        self.assertEqual('??', explainer11.render())

        # ---
        class MyExplainer(HistoryLineExplainer):
            type_id = 'creation'

            def render(self):
                return f'{self.hline.entity} - {self.user.username}'

        registry.register_line_explainer(
            history.TYPE_CREATION,
            MyExplainer,
        )

        explainers2 = [*registry.line_explainers([hline], user=user)]
        self.assertIsList(explainers2, length=1)

        explainer21 = explainers2[0]
        self.assertIsInstance(explainer21, MyExplainer)
        self.assertEqual(
            f'{orga.name} - {user.username}',
            explainer21.render(),
        )

        self.assertHTMLEqual(
            '<div class="history-line history-line-creation"><div>',
            self.render_line(hline, user),
        )

    def test_render_edition(self):
        user = self.create_user()

        old_name = 'Acme'
        orga = FakeOrganisation.objects.create(user=user, name=old_name)

        # One modification ---
        orga = self.refresh(orga)
        orga.name += ' corp'
        orga.save()

        hline1 = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline1.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">{_("Name")}</span>',
                    oldvalue=f'<span class="field-change-old_value">{old_name}</span>',
                    value=f'<span class="field-change-new_value">{orga.name}</span>',
                )),
            ),
            self.render_line(hline1, user),
        )

        # Several modifications ---
        orga = self.refresh(orga)
        orga.email = 'contact@acme.org'
        orga.capital = 1000
        orga.subject_to_vat = False
        orga.creation_date = date(year=2021, month=2, day=19)
        orga.save()

        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">'
                ' <ul>'
                '  <li>{mod1}</li>'
                '  <li>{mod2}</li>'
                '  <li>{mod3}</li>'
                '  <li>{mod4}</li>'
                ' </ul>'
                '<div>',
                mod1=mark_safe(self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("Email address")}</span>',
                    value=f'<span class="field-change-new_value">{orga.email}</span>',
                )),
                mod2=mark_safe(self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("Capital")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{number_format(orga.capital, use_l10n=True, force_grouping=True)}'
                          f'</span>',
                )),
                mod3=mark_safe(self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">{_("Subject to VAT")}</span>',
                    oldvalue=f'<span class="field-change-old_value">{_("Yes")}</span>',
                    value=f'<span class="field-change-new_value">{_("No")}</span>',
                )),
                mod4=mark_safe(self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("Date of creation")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{date_format(orga.creation_date, "DATE_FORMAT")}'
                          f'</span>',
                )),
            ),
            self.render_line(self.get_hline(), user),
        )

    def test_render_edition_invalid_field(self):
        user = self.create_user()

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        nerv = self.refresh(nerv)
        nerv.name = nerv.name.upper()
        nerv.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline.type)
        self.assertIn('["NERV", ["name", "Nerv", "NERV"]]', hline.value)

        fname = 'invalid'
        hline.value = hline.value.replace('name', fname)
        hline.save()

        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                _('“{field}” set').format(field=fname),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_datetimefield(self):
        user = self.create_user()

        activity = FakeActivity.objects.create(
            user=user, title='Meeting with Seele',
            type=FakeActivityType.objects.all()[0],
        )

        activity = self.refresh(activity)
        activity.start = self.create_datetime(year=2021, month=5, day=27, hour=17, minute=42)
        activity.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("Start")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{date_format(activity.start, "DATETIME_FORMAT")}'
                          f'</span>',
                )),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_textfield(self):
        user = self.create_user()

        orga = FakeOrganisation.objects.create(user=user, name='Gainax')

        # 1 value ---
        old_description = "Awesome animation studio"
        orga = self.refresh(orga)
        orga.description = old_description
        orga.save()

        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(_('{field} set {details_link}').format(
                    field=f'<span class="field-change-field_name">{_("Description")}</span>',
                    details_link=(
                        f'<a class="field-change-text_details" data-action="popover">'
                        f' {_("(see details)")}'
                        f' <summary>{_("Details of modifications")}</summary>'
                        f' <details>'
                        f'  <div class="history-line-field-change-text-old_value">'
                        f'   <h4>{_("Old value")}</h4><p></p>'
                        f'  </div>'
                        f'  <div class="history-line-field-change-text-new_value">'
                        f'   <h4>{_("New value")}</h4><p>{orga.description}</p>'
                        f'  </div>'
                        f' </details>'
                        f'</a>'
                    ),
                ))
            ),
            self.render_line(self.get_hline(), user),
        )

        # 2 values ---
        orga = self.refresh(orga)
        orga.description += ' which created "Evangelion".'
        orga.save()

        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(_('{field} set {details_link}').format(
                    field=f'<span class="field-change-field_name">{_("Description")}</span>',
                    details_link=(
                        f'<a class="field-change-text_details" data-action="popover">'
                        f' {_("(see details)")}'
                        f' <summary>{_("Details of modifications")}</summary>'
                        f' <details>'
                        f'  <div class="history-line-field-change-text-old_value">'
                        f'   <h4>{_("Old value")}</h4><p>{old_description}</p>'
                        f'  </div>'
                        f'  <div class="history-line-field-change-text-new_value">'
                        f'   <h4>{_("New value")}</h4><p>{orga.description}</p>'
                        f'  </div>'
                        f' </details>'
                        f'</a>'
                    ),
                ))
            ),
            self.render_line(self.get_hline(), user),
        )

        # 2 values (set to empty) ---
        description_backup = orga.description
        orga = self.refresh(orga)
        orga.description = ''
        orga.save()

        hline3 = self.get_hline()
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(_('{field} emptied {details_link}').format(
                    field=f'<span class="field-change-field_name">{_("Description")}</span>',
                    details_link=(
                        f'<a class="field-change-text_details" data-action="popover">'
                        f' {_("(see details)")}'
                        f' <summary>{_("Details of modifications")}</summary>'
                        f' <details>'
                        f'  <div class="history-line-field-change-text-old_value">'
                        f'   <h4>{_("Old value")}</h4><p>{description_backup}</p>'
                        f'  </div>'
                        f'  <div class="history-line-field-change-text-new_value">'
                        f'   <h4>{_("New value")}</h4><p></p>'
                        f'  </div>'
                        f' </details>'
                        f'</a>'
                    ),
                ))
            ),
            self.render_line(hline3, user),
        )

        # Old line (no value stored)
        self.assertListEqual(
            [str(orga), ['description', description_backup, '']],
            json.loads(hline3.value),
        )

        hline3.value = json.dumps([str(orga), ['description']])
        hline3.save()

        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(_('{field} set').format(
                    field=f'<span class="field-change-field_name">{_("Description")}</span>',
                ))
            ),
            self.render_line(self.refresh(hline3), user),
        )

    def test_render_edition_set_null01(self):
        "BooleanField."
        user = self.create_user()

        peter = FakeContact.objects.create(
            user=user, first_name='Peter', last_name='Parker',
            loves_comics=True,
        )

        peter = self.refresh(peter)
        peter.loves_comics = None
        peter.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">{_("Loves comics")}</span>',
                    oldvalue=f'<span class="field-change-old_value">{_("Yes")}</span>',
                    value=f'<span class="field-change-new_value">{_("N/A")}</span>',
                )),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_set_null02(self):
        "IntegerField."
        user = self.create_user()

        old_capital = 1000
        orga = FakeOrganisation.objects.create(user=user, name='Acme', capital=old_capital)

        orga = self.refresh(orga)
        orga.capital = None
        orga.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(_('{field} emptied (it was {oldvalue})').format(
                    field=f'<span class="field-change-field_name">{_("Capital")}</span>',
                    oldvalue=f'<span class="field-change-old_value">'
                             f'{number_format(old_capital, use_l10n=True, force_grouping=True)}'
                             f'</span>',
                )),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_fk01(self):
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        hayao = FakeContact.objects.create(
            user=user, first_name='Hayao', last_name='Miyazaki',
        )
        img = FakeImage.objects.create(user=user, name='Grumpy Hayao')
        # NB: should be escaped
        position = FakePosition.objects.create(title='Director<br>')

        hayao = self.refresh(hayao)
        hayao.image = img
        hayao.position = position
        hayao.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">'
                ' <ul>'
                '  <li>{mod1}</li>'
                '  <li>{mod2}</li>'
                ' </ul>'
                '<div>',
                mod1=mark_safe(_('{field} set to {value}').format(
                    field=f'<span class="field-change-field_name">{_("Position")}</span>',
                    value=f'<span class="field-change-new_value">{escape(position.title)}</span>',
                )),
                mod2=mark_safe(_('{field} set to {value}').format(
                    field=f'<span class="field-change-field_name">{_("Photograph")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'<a href="{img.get_absolute_url()}">{img.name}</a>'
                          f'</span>',
                )),
            ),
            self.render_line(hline, user),
        )

        # Deleted instances
        img_id = img.id
        img.delete()

        position_id = position.id
        position.delete()

        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">'
                ' <ul>'
                '  <li>{mod1}</li>'
                '  <li>{mod2}</li>'
                ' </ul>'
                '<div>',
                mod1=mark_safe(_('{field} set to {value}').format(
                    field=f'<span class="field-change-field_name">{_("Position")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{_("{pk} (deleted)").format(pk=position_id)}'
                          f'</span>',
                )),
                mod2=mark_safe(_('{field} set to {value}').format(
                    field=f'<span class="field-change-field_name">{_("Photograph")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{_("{pk} (deleted)").format(pk=img_id)}'
                          f'</span>',
                )),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_fk02(self):
        "Not allowed to see."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        hayao = FakeContact.objects.create(
            user=user, first_name='Hayao', last_name='Miyazaki',
        )
        img = FakeImage.objects.create(user=self.other_user, name='Grumpy Hayao')

        hayao = self.refresh(hayao)
        hayao.image = img
        hayao.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(_('{field} set to {value}').format(
                    field=f'<span class="field-change-field_name">{_("Photograph")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{settings.HIDDEN_VALUE}'
                          f'</span>',
                )),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_m2m01(self):
        user = self.create_user()
        cat1, cat2, cat3 = FakeImageCategory.objects.order_by('id')[:3]

        img = FakeImage.objects.create(user=user, name='Grumpy Hayao')

        # One addition ---
        img.categories.add(cat1)
        hline1 = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline1.type)

        field_msg = f'<span class="field-change-field_name">{_("Categories")}</span>'
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(_('{field} changed: {changes}').format(
                    field=field_msg,
                    changes=ngettext('{} was added', '{} were added', 1).format(
                        f'<span class="field-change-m2m_added">{cat1}</span>'
                    ),
                )),
            ),
            self.render_line(hline1, user),
        )

        # Several addition ---
        self.refresh(img).categories.set([cat1, cat2, cat3])

        first_cat1, second_cat1 = sorted([cat2.name, cat3.name])
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(_('{field} changed: {changes}').format(
                    field=field_msg,
                    changes=ngettext('{} was added', '{} were added', 2).format(
                        f'<span class="field-change-m2m_added">{first_cat1}</span>, '
                        f'<span class="field-change-m2m_added">{second_cat1}</span>'
                    ),
                )),
            ),
            self.render_line(self.get_hline(), user),
        )

        # One removing ---
        self.refresh(img).categories.remove(cat2)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(_('{field} changed: {changes}').format(
                    field=field_msg,
                    changes=ngettext('{} was removed', '{} were removed', 1).format(
                        f'<span class="field-change-m2m_removed">{cat2}</span>'
                    ),
                )),
            ),
            self.render_line(self.get_hline(), user),
        )

        # Several removing
        first_cat2, second_cat2 = sorted([cat1.name, cat3.name])
        self.refresh(img).categories.clear()
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(_('{field} changed: {changes}').format(
                    field=field_msg,
                    changes=ngettext('{} was removed', '{} were removed', 2).format(
                        f'<span class="field-change-m2m_removed">{first_cat2}</span>, '
                        f'<span class="field-change-m2m_removed">{second_cat2}</span>'
                    ),
                )),
            ),
            self.render_line(self.get_hline(), user),
        )

    def test_render_edition_m2m02(self):
        "Adding & removing at the same time."
        user = self.create_user()
        cat1, cat2, cat3 = FakeImageCategory.objects.order_by('id')[:3]

        img = FakeImage.objects.create(user=user, name='Grumpy Hayao')
        img.categories.add(cat2)

        self.refresh(img).categories.set([cat1, cat3])

        first_cat, second_cat = sorted([cat1.name, cat3.name])
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(_('{field} changed: {changes}').format(
                    field=f'<span class="field-change-field_name">{_("Categories")}</span>',
                    changes='{}, {}'.format(
                        ngettext('{} was added', '{} were added', 2).format(
                            f'<span class="field-change-m2m_added">{first_cat}</span>, '
                            f'<span class="field-change-m2m_added">{second_cat}</span>'
                        ),
                        ngettext('{} was removed', '{} were removed', 1).format(
                            f'<span class="field-change-m2m_removed">{cat2}</span>'
                        ),
                    ),
                )),
            ),
            self.render_line(self.get_hline(), user),
        )

    def test_render_edition_m2m03(self):
        "M2M to entities."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        ml = FakeMailingList.objects.create(user=user, name='Nerds')
        campaign = FakeEmailCampaign.objects.create(user=user, name='Camp #1')

        campaign.mailing_lists.add(ml)
        change_fmt = _('{field} changed: {changes}').format
        field_msg = (
            f'<span class="field-change-field_name">'
            f'{_("Related mailing lists")}'
            f'</span>'
        )
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(change_fmt(
                    field=field_msg,
                    changes=ngettext('{} was added', '{} were added', 1).format(
                        f'<span class="field-change-m2m_added">'
                        f'<a href="{ml.get_absolute_url()}">{ml}</a>'
                        f'</span>'
                    ),
                )),
            ),
            self.render_line(self.get_hline(), user),
        )

        # Removing ----
        self.refresh(campaign).mailing_lists.remove(ml)
        hline2 = self.get_hline()
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(change_fmt(
                    field=field_msg,
                    changes=ngettext('{} was removed', '{} were removed', 1).format(
                        f'<span class="field-change-m2m_removed">'
                        f'<a href="{ml.get_absolute_url()}">{ml}</a>'
                        f'</span>'
                    ),
                )),
            ),
            self.render_line(hline2, user),
        )

        # Credentials ---
        ml.user = self.other_user
        ml.save()
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-edition">{}<div>',
                mark_safe(change_fmt(
                    field=field_msg,
                    changes=ngettext('{} was removed', '{} were removed', 1).format(
                        f'<span class="field-change-m2m_removed">'
                        f'{settings.HIDDEN_VALUE}'
                        f'</span>'
                    ),
                )),
            ),
            self.render_line(hline2, user),
        )

    def test_render_edition_prefetching(self):
        user = self.create_user()

        position1, position2, position3 = FakePosition.objects.all()[:3]
        hayao = FakeContact.objects.create(
            user=user, first_name='Hayao', last_name='Miyazaki',
            position=position1,
        )

        hayao = self.refresh(hayao)
        hayao.position = position2
        hayao.save()

        hayao = self.refresh(hayao)
        hayao.position = position3
        hayao.save()

        hlines = [*self.get_hlines(entity=hayao, number=2)]
        self.assertCountEqual(
            [history.TYPE_EDITION] * 2,
            [hline.type for hline in hlines],
        )

        with self.assertNumQueries(1):
            explainers = html_history_registry.line_explainers(hlines, user)

        with self.assertNumQueries(0):
            for explainer in explainers:
                explainer.render()

    def test_render_custom_edition01(self):
        "String, date, integer."
        user = self.create_user()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        cfield1 = create_cfield(name='Punch line',   field_type=CustomField.STR)
        cfield2 = create_cfield(name='First attack', field_type=CustomField.DATE)
        cfield3 = create_cfield(name='Power',        field_type=CustomField.INT)

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        value_str1 = 'Future proof'
        value_date = date(year=2021, month=7, day=16)
        value_int = 9654

        save_cvalues = CustomFieldValue.save_values_for_entities
        save_cvalues(cfield1, [nerv], value_str1)
        save_cvalues(cfield2, [nerv], value_date)
        save_cvalues(cfield3, [nerv], value_int)

        hline1 = self.get_hline()
        self.assertEqual(history.TYPE_CUSTOM_EDITION, hline1.type)

        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-custom_edition">'
                ' <ul>'
                '  <li>{mod1}</li>'
                '  <li>{mod2}</li>'
                '  <li>{mod3}</li>'
                ' </ul>'
                '<div>',
                mod1=mark_safe(self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{cfield1.name}</span>',
                    value=f'<span class="field-change-new_value">{value_str1}</span>',
                )),
                mod2=mark_safe(self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{cfield2.name}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{date_format(value_date, "DATE_FORMAT")}'
                          f'</span>',
                )),
                mod3=mark_safe(self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{cfield3.name}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{number_format(value_int, use_l10n=True, force_grouping=True)}'
                          f'</span>',
                )),
            ),
            self.render_line(hline1, user),
        )

        # Old & new value ---
        clear_global_info()  # Current line is stored in global cache

        value_str2 = 'We fight angels'
        save_cvalues(cfield1, [nerv], value_str2)

        hline2 = self.get_hline()
        self.assertEqual(history.TYPE_CUSTOM_EDITION, hline2.type)
        self.assertNotEqual(hline1, hline2)

        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-custom_edition">{}<div>',
                mark_safe(self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">{cfield1.name}</span>',
                    oldvalue=f'<span class="field-change-old_value">{value_str1}</span>',
                    value=f'<span class="field-change-new_value">{value_str2}</span>',
                )),
            ),
            self.render_line(hline2, user),
        )

    def test_render_custom_edition02(self):
        "Enum & multi-enum."
        user = self.create_user()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        cfield1 = create_cfield(name='Type', field_type=CustomField.ENUM)
        cfield2 = create_cfield(name='EVA',  field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        choice1 = create_evalue(value='Attack', custom_field=cfield1)
        choice2 = create_evalue(value='EVA01',  custom_field=cfield2)

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        save_cvalues = CustomFieldValue.save_values_for_entities
        save_cvalues(cfield1, [nerv], choice1.id)
        save_cvalues(cfield2, [nerv], [choice2.id])

        hline1 = self.get_hline()
        self.assertEqual(history.TYPE_CUSTOM_EDITION, hline1.type)

        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-custom_edition">'
                ' <ul>'
                '  <li>{mod1}</li>'
                '  <li>{mod2}</li>'
                ' </ul>'
                '<div>',
                mod1=mark_safe(self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{cfield1.name}</span>',
                    value=f'<span class="field-change-new_value">{choice1}</span>',
                )),
                mod2=mark_safe(_('{field} changed: {changes}').format(
                    field=f'<span class="field-change-field_name">{cfield2.name}</span>',
                    changes=ngettext('{} was added', '{} were added', 1).format(
                        f'<span class="field-change-m2m_added">{choice2}</span>'
                    ),
                )),

            ),
            self.render_line(hline1, user),
        )

    def test_render_custom_edition03(self):
        "Deleted CustomField."
        user = self.create_user()

        cfield = CustomField.objects.create(
            content_type=FakeOrganisation, name='Punch line', field_type=CustomField.STR,
        )
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        CustomFieldValue.save_values_for_entities(cfield, [nerv], 'Future proof')

        clear_global_info()  # Current line is stored in global cache
        cfield_id = cfield.id
        cfield.delete()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_CUSTOM_EDITION, hline.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-custom_edition">{}<div>',
                _('Deleted field (with id={id}) set').format(id=cfield_id),
            ),
            self.render_line(hline, user),
        )

    def test_render_custom_edition04(self):
        "Invalid value (does not match CustomField type)."
        user = self.create_user()

        cfield = CustomField.objects.create(
            content_type=FakeOrganisation, name='Power', field_type=CustomField.DATE,
        )
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        CustomFieldValue.save_values_for_entities(
            cfield, [nerv], date(year=2021, month=6, day=21),
        )

        hline = self.get_hline()
        self.assertListEqual(
            [nerv.name, [cfield.id, '2021-06-21']],
            json.loads(hline.value),
        )

        hline.value = json.dumps([nerv.name, [cfield.id, 'not an int']])
        hline.save()

        self.assertHTMLEqual(
            '<div class="history-line history-line-custom_edition">??<div>',
            self.render_line(self.refresh(hline), user),
        )

    def test_render_custom_edition_prefetching(self):
        user = self.create_user()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        cfield1 = create_cfield(name='Type', field_type=CustomField.ENUM)
        cfield2 = create_cfield(name='EVA',  field_type=CustomField.ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        choice1 = create_evalue(value='Attack', custom_field=cfield1)
        choice2 = create_evalue(value='EVA01',  custom_field=cfield2)

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        save_cvalues = CustomFieldValue.save_values_for_entities
        save_cvalues(cfield1, [nerv], choice1.id)

        clear_global_info()
        save_cvalues(cfield2, [nerv], choice2.id)

        hlines = [*self.get_hlines(entity=nerv, number=2)]
        self.assertCountEqual(
            [history.TYPE_CUSTOM_EDITION] * 2,
            [hline.type for hline in hlines],
        )

        with self.assertNumQueries(2):  # CustomField & CustomFieldEnumValue
            explainers = html_history_registry.line_explainers(hlines, user)

        with self.assertNumQueries(0):
            for explainer in explainers:
                explainer.render()

    def test_render_deletion(self):
        user = self.create_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')

        gainax.delete()
        hline = self.get_hline()
        self.assertEqual(history.TYPE_DELETION,  hline.type)
        self.assertHTMLEqual(
            '<div class="history-line history-line-deletion"><div>',
            self.render_line(hline, user),
        )

    def test_render_related_edition(self):
        user = self.create_user()
        ghibli = FakeOrganisation.objects.create(user=user, name='Ghibli')

        last_name = 'Miyazaki'
        hayao = FakeContact.objects.create(user=user, last_name=last_name)

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_employed', 'is employed'),
            ('test-object_employed', 'employs'),
        )[0]
        Relation.objects.create(
            user=user, subject_entity=hayao, object_entity=ghibli, type=rtype,
        )

        HistoryConfigItem.objects.create(relation_type=rtype)

        hayao = self.refresh(hayao)
        # hayao.description = 'A great animation movie maker'  # TODO: more complex mods
        hayao.first_name = 'Hayao'
        hayao.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_RELATED, hline.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-related_edition'
                ' history-line-collapsable history-line-collapsed">'
                ' <div class="history-line-main">'
                '  <div class="toggle-icon-container toggle-icon-expand" title="{expand_title}">'
                '   <div class="toggle-icon"></div>'
                '  </div>'
                '  <div class="toggle-icon-container toggle-icon-collapse"'
                '       title="{collapse_title}">'
                '   <div class="toggle-icon"></div>'
                '  </div>'
                '  <span class="history-line-title">{title}</span>'
                ' </div>'
                ' <ul class="history-line-details">'
                '  <li>{mod}</li>'
                ' </ul>'
                '<div>',
                title=mark_safe(_('%(entity_link)s edited') % {
                    'entity_link': f'<a href="{hayao.get_absolute_url()}">{hayao}</a>',
                }),
                expand_title=_('Expand'),
                collapse_title=_('Close'),
                mod=mark_safe(self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("First name")}</span>',
                    value=f'<span class="field-change-new_value">{hayao.first_name}</span>',
                )),
            ),
            self.render_line(hline, user),
        )

        # Deleted entity ---
        hayao_repr = str(hayao)
        hayao.delete()
        self.maxDiff = None
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-related_edition'
                ' history-line-collapsable history-line-collapsed">'
                ' <div class="history-line-main">'
                '  <div class="toggle-icon-container toggle-icon-expand" title="{expand_title}">'
                '   <div class="toggle-icon"></div>'
                '  </div>'
                '  <div class="toggle-icon-container toggle-icon-collapse"'
                '       title="{collapse_title}">'
                '   <div class="toggle-icon"></div>'
                '  </div>'
                '  <span class="history-line-title">{title}</span>'
                ' </div>'
                ' <ul class="history-line-details">'
                '  <li>{mod}</li>'
                ' </ul>'
                '<div>',
                title=_('“%(entity)s“ edited') % {'entity': hayao_repr},
                expand_title=_('Expand'),
                collapse_title=_('Close'),
                mod=mark_safe(self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("First name")}</span>',
                    value=f'<span class="field-change-new_value">{hayao.first_name}</span>',
                )),
            ),
            self.render_line(self.refresh(hline), user),
        )

    def test_render_property_addition(self):
        user = self.create_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')

        text = 'Make anime series'
        ptype_id = 'test-prop_make_anime'
        ptype = CremePropertyType.objects.smart_update_or_create(str_pk=ptype_id, text=text)
        prop = CremeProperty.objects.create(type=ptype, creme_entity=gainax)

        hline = self.get_hline()
        self.assertEqual(history.TYPE_PROP_ADD, hline.type)
        html_format_str = '<div class="history-line history-line-property_addition">{}<div>'
        self.assertHTMLEqual(
            format_html(
                html_format_str,
                # _('“%(property_text)s” added') % {'property_text': text},
                mark_safe(_('%(property_text)s added') % {
                    'property_text': f'<span class="property-text">{text}</span>',
                }),
            ),
            self.render_line(hline, user),
        )

        # ---
        prop.delete()
        ptype.delete()
        self.assertHTMLEqual(
            format_html(
                html_format_str,
                # _('“%(property_text)s” added') % {'property_text': ptype_id},
                mark_safe(_('%(property_text)s added') % {
                    'property_text': f'<span class="property-text">{ptype_id}</span>',
                }),
            ),
            self.render_line(hline, user),
        )

    def test_render_property_deletion(self):
        user = self.create_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')

        text = 'Make anime series'
        ptype_id = 'test-prop_make_anime'
        ptype = CremePropertyType.objects.smart_update_or_create(str_pk=ptype_id, text=text)
        prop = CremeProperty.objects.create(type=ptype, creme_entity=gainax)

        prop.delete()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_PROP_DEL, hline.type)

        html_format_str = '<div class="history-line history-line-property_deletion">{}<div>'
        self.assertHTMLEqual(
            format_html(
                html_format_str,
                # _('“%(property_text)s” removed') % {'property_text': text}
                mark_safe(_('%(property_text)s removed') % {
                    'property_text': f'<span class="property-text">{text}</span>',
                }),
            ),
            self.render_line(hline, user),
        )

        # ---
        ptype.delete()
        self.assertHTMLEqual(
            format_html(
                html_format_str,
                # _('“%(property_text)s” removed') % {'property_text': ptype_id},
                mark_safe(_('%(property_text)s removed') % {
                    'property_text': f'<span class="property-text">{ptype_id}</span>',
                }),
            ),
            self.render_line(hline, user),
        )

    def test_render_property_prefetching(self):
        user = self.create_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_make_anime', text='Makes anime series')
        ptype2 = create_ptype(str_pk='test-prop_make_film', text='Makes film')

        create_prop = partial(CremeProperty.objects.create, creme_entity=gainax)
        prop1 = create_prop(type=ptype1)
        create_prop(type=ptype2)

        prop1.delete()

        hlines = [*self.get_hlines(entity=gainax, number=3)]
        self.assertCountEqual(
            [history.TYPE_PROP_ADD, history.TYPE_PROP_ADD, history.TYPE_PROP_DEL],
            [hline.type for hline in hlines],
        )

        with self.assertNumQueries(1):
            explainers = html_history_registry.line_explainers(hlines, user)

        with self.assertNumQueries(0):
            for explainer in explainers:
                explainer.render()

    def test_render_relation_addition(self):
        user = self.create_user()
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_works', 'is employed'),
            ('test-object_works',  'employs'),
        )
        relation = Relation.objects.create(
            user=user, subject_entity=rei, object_entity=nerv, type=rtype,
        )

        hline_sym, hline = HistoryLine.objects.order_by('-id')[:2]

        self.assertEqual(history.TYPE_RELATION, hline.type)
        html_format_str = (
            '<div class="history-line history-line-relationship_addition">{}<div>'
        )
        self.assertHTMLEqual(
            format_html(
                html_format_str,
                # mark_safe(_('“%(predicate)s” added to %(entity_link)s') % {
                #     'predicate': rtype.predicate,  # <==
                #     'entity_link': f'<a href="{nerv.get_absolute_url()}">{nerv}</a>',
                # }),
                mark_safe(_('%(predicate)s added to %(entity_link)s') % {
                    'predicate': f'<span class="relationship-predicate">'
                                 f'{rtype.predicate}'
                                 f'</span>',  # <==
                    'entity_link': f'<a href="{nerv.get_absolute_url()}">{nerv}</a>',
                }),
            ),
            self.render_line(hline, user),
        )

        self.assertEqual(history.TYPE_SYM_RELATION, hline_sym.type)
        self.assertHTMLEqual(
            format_html(
                html_format_str,
                # mark_safe(_('“%(predicate)s” added to %(entity_link)s') % {
                #     'predicate': srtype.predicate,  # <==
                #     'entity_link': f'<a href="{rei.get_absolute_url()}">{rei}</a>',
                # }),
                mark_safe(_('%(predicate)s added to %(entity_link)s') % {
                    'predicate': f'<span class="relationship-predicate">'
                                 f'{srtype.predicate}'
                                 f'</span>',  # <==
                    'entity_link': f'<a href="{rei.get_absolute_url()}">{rei}</a>',
                }),
            ),
            self.render_line(hline_sym, user),
        )

        # Deleted relation-type ---
        rtype_id = rtype.id
        relation.delete()
        rtype.delete()
        self.assertDoesNotExist(relation)
        self.assertDoesNotExist(rtype)
        self.assertHTMLEqual(
            format_html(
                html_format_str,
                # mark_safe(_('“%(predicate)s” added to %(entity_link)s') % {
                #     'predicate': rtype_id,  # <==
                #     'entity_link': f'<a href="{nerv.get_absolute_url()}">{nerv}</a>',
                # }),
                mark_safe(_('%(predicate)s added to %(entity_link)s') % {
                    'predicate': f'<span class="relationship-predicate">'
                                 f'{rtype_id}'
                                 f'</span>',  # <==
                    'entity_link': f'<a href="{nerv.get_absolute_url()}">{nerv}</a>',
                }),
            ),
            self.render_line(self.refresh(hline), user),
        )

        # Deleted entity ---
        nerv_repr = str(nerv)
        nerv.delete()
        self.assertHTMLEqual(
            format_html(
                html_format_str,
                # _('“%(predicate)s” added to “%(entity)s“') % {
                #     'predicate': rtype_id,
                #     'entity': nerv_repr,
                # },
                mark_safe(_('%(predicate)s added to “%(entity)s“') % {
                    'predicate': f'<span class="relationship-predicate">'
                                 f'{rtype_id}'
                                 f'</span>',  # <==
                    'entity': nerv_repr,
                }),
            ),
            self.render_line(self.refresh(hline), user),
        )

    def test_render_relation_deletion(self):
        user = self.create_user()
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        rtype, srtype = RelationType.objects.smart_update_or_create(
            ('test-subject_works', 'is employed'),
            ('test-object_works',  'employs'),
        )
        relation = Relation.objects.create(
            user=user, subject_entity=rei, object_entity=nerv, type=rtype,
        )

        relation.delete()
        hline_sym, hline = HistoryLine.objects.order_by('-id')[:2]

        self.assertEqual(history.TYPE_RELATION_DEL, hline.type)
        html_format_str = (
            '<div class="history-line history-line-relationship_deletion">{}<div>'
        )
        self.assertHTMLEqual(
            format_html(
                html_format_str,
                # mark_safe(
                #     _('“%(predicate)s” to %(entity_link)s removed') % {
                #         'predicate': rtype.predicate,
                #         'entity_link': f'<a href="{nerv.get_absolute_url()}">{nerv}</a>',
                #     }
                # ),
                mark_safe(_('%(predicate)s to %(entity_link)s removed') % {
                    'predicate': f'<span class="relationship-predicate">'
                                 f'{rtype.predicate}'
                                 f'</span>',  # <==
                    'entity_link': f'<a href="{nerv.get_absolute_url()}">{nerv}</a>',
                }),
            ),
            self.render_line(hline, user),
        )

        self.assertEqual(history.TYPE_SYM_REL_DEL, hline_sym.type)
        self.assertHTMLEqual(
            format_html(
                html_format_str,
                # mark_safe(
                #     _('“%(predicate)s” to %(entity_link)s removed') % {
                #         'predicate': srtype.predicate,
                #         'entity_link': f'<a href="{rei.get_absolute_url()}">{rei}</a>',
                #     }
                # ),
                mark_safe(_('%(predicate)s to %(entity_link)s removed') % {
                    'predicate': f'<span class="relationship-predicate">'
                                 f'{srtype.predicate}'
                                 f'</span>',  # <==
                    'entity_link': f'<a href="{rei.get_absolute_url()}">{rei}</a>',
                }),
            ),
            self.render_line(hline_sym, user),
        )

        # ---
        rtype_id = rtype.id
        rtype.delete()
        self.assertDoesNotExist(rtype)
        self.assertHTMLEqual(
            format_html(
                html_format_str,
                # mark_safe(
                #     _('“%(predicate)s” to %(entity_link)s removed') % {
                #         'predicate': rtype_id,  # <==
                #         'entity_link': f'<a href="{nerv.get_absolute_url()}">{nerv}</a>',
                #     }
                # ),
                mark_safe(_('%(predicate)s to %(entity_link)s removed') % {
                    'predicate': f'<span class="relationship-predicate">'
                                 f'{rtype_id}'
                                 f'</span>',  # <==
                    'entity_link': f'<a href="{nerv.get_absolute_url()}">{nerv}</a>',
                }),
            ),
            self.render_line(self.refresh(hline), user),
        )

        # Deleted entity ---
        nerv_repr = str(nerv)
        nerv.delete()
        self.assertHTMLEqual(
            format_html(
                html_format_str,
                # _('“%(predicate)s” to “%(entity)s“ removed') % {
                #     'predicate': rtype_id,  # <==
                #     'entity': nerv_repr,  # <==
                # },
                mark_safe(_('%(predicate)s to “%(entity)s“ removed') % {
                    'predicate': f'<span class="relationship-predicate">'
                                 f'{rtype_id}'
                                 f'</span>',
                    'entity': nerv_repr,  # <==
                }),
            ),
            self.render_line(self.refresh(hline), user),
        )

    def test_render_relation_prefetching(self):
        user = self.create_user()

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')

        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_works', 'is employed'),
            ('test-object_works',  'employs'),
        )[0]
        rtype2 = create_rtype(
            ('test-subject_pilot', 'is pilot for'),
            ('test-object_pilot',  'has pilot'),
        )[0]

        create_rel = partial(
            Relation.objects.create,
            user=user, subject_entity=rei, object_entity=nerv,
        )
        relation1 = create_rel(type=rtype1)
        create_rel(type=rtype2)

        relation1.delete()

        hlines = [*self.get_hlines(entity=rei, number=3)]
        self.assertCountEqual(
            [history.TYPE_RELATION, history.TYPE_RELATION, history.TYPE_RELATION_DEL],
            [hline.type for hline in hlines],
        )

        # Populate
        HistoryLine.populate_related_lines(hlines)

        related_hlines = [*filter(None, (hline.related_line for hline in hlines))]
        HistoryBrick._populate_related_real_entities([*hlines, *related_hlines])

        ContentType.objects.get_for_model(CremeEntity)
        # Populate [end]

        with self.assertNumQueries(1):
            explainers = html_history_registry.line_explainers(hlines, user)

        with self.assertNumQueries(0):
            for explainer in explainers:
                explainer.render()

    def test_render_auxiliary_creation(self):
        user = self.create_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        address = FakeAddress.objects.create(
            entity=gainax, country='Japan', city='Mitaka',
        )

        hline = self.get_hline()
        self.assertEqual(history.TYPE_AUX_CREATION, hline.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-auxiliary_creation">'
                '{title}'
                '<div>',
                title=_('“%(auxiliary_ctype)s“ added: %(auxiliary_value)s') % {
                    'auxiliary_ctype': 'Test address',
                    'auxiliary_value': address,
                },
            ),
            self.render_line(hline, user),
        )

    def test_render_auxiliary_edition01(self):
        user = self.create_user()

        country = 'Japan'
        old_city = 'MITAKA'
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        address = FakeAddress.objects.create(
            entity=gainax, country=country, city=old_city,
        )

        address = self.refresh(address)
        address.city = old_city.title()
        address.department = 'Tokyo'
        address.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_AUX_EDITION, hline.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-auxiliary_edition'
                ' history-line-collapsable history-line-collapsed">'
                ' <div class="history-line-main">'
                '  <div class="toggle-icon-container toggle-icon-expand" title="{expand_title}">'
                '   <div class="toggle-icon"></div>'
                '  </div>'
                '  <div class="toggle-icon-container toggle-icon-collapse"'
                '       title="{collapse_title}">'
                '   <div class="toggle-icon"></div>'
                '  </div>'
                '  <span class="history-line-title">{title}</span>'
                ' </div>'
                ' <ul class="history-line-details">'
                '  <li>{mod1}</li>'
                '  <li>{mod2}</li>'
                ' </ul>'
                '<div>',
                title=_('“%(auxiliary_ctype)s“ edited: %(auxiliary_value)s') % {
                    'auxiliary_ctype': 'Test address',
                    'auxiliary_value': address,
                },
                expand_title=_('Expand'),
                collapse_title=_('Close'),
                mod1=mark_safe(self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">{_("City")}</span>',
                    oldvalue=f'<span class="field-change-old_value">{old_city}</span>',
                    value=f'<span class="field-change-new_value">{address.city}</span>',
                )),
                mod2=mark_safe(self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("Department")}</span>',
                    value=f'<span class="field-change-new_value">{address.department}</span>',
                )),
            ),
            self.render_line(hline, user),
        )

    def test_render_auxiliary_edition02(self):
        """FakeInvoiceLine:
        - an auxiliary + CremeEntity at the same time.
        - DecimalField.
        - field with choices.
        """
        user = self.create_user()
        invoice = FakeInvoice.objects.create(
            user=user, name='Invoice', expiration_date=date(year=2021, month=12, day=15),
        )
        old_quantity = Decimal('1.3')
        pline = FakeInvoiceLine.objects.create(
            item='DeathNote', user=user,
            linked_invoice=invoice, quantity=old_quantity,
            discount_unit=FakeInvoiceLine.Discount.AMOUNT,
        )

        pline.quantity = Decimal('2.5')
        pline.discount_unit = FakeInvoiceLine.Discount.PERCENT
        pline.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_AUX_EDITION, hline.type)
        self.maxDiff = None
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-auxiliary_edition'
                ' history-line-collapsable history-line-collapsed">'
                ' <div class="history-line-main">'
                '  <div class="toggle-icon-container toggle-icon-expand" title="{expand_title}">'
                '   <div class="toggle-icon"></div>'
                '  </div>'
                '  <div class="toggle-icon-container toggle-icon-collapse"'
                '       title="{collapse_title}">'
                '   <div class="toggle-icon"></div>'
                '  </div>'
                '  <span class="history-line-title">{title}</span>'
                ' </div>'
                ' <ul class="history-line-details">'
                '  <li>{mod1}</li>'
                '  <li>{mod2}</li>'
                ' </ul>'
                '<div>',
                title=_('“%(auxiliary_ctype)s“ edited: %(auxiliary_value)s') % {
                    'auxiliary_ctype': 'Test Invoice Line',
                    'auxiliary_value': pline,
                },
                expand_title=_('Expand'),
                collapse_title=_('Close'),
                mod1=mark_safe(self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">'
                          f'{_("Quantity")}'
                          f'</span>',
                    oldvalue=f'<span class="field-change-old_value">'
                             f'{number_format(old_quantity, use_l10n=True)}'
                             f'</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{number_format(pline.quantity, use_l10n=True)}'
                          f'</span>',
                )),
                mod2=mark_safe(self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">'
                          f'{_("Discount Unit")}'
                          f'</span>',
                    oldvalue=f'<span class="field-change-old_value">'
                             f'{_("Amount")}'
                             f'</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{_("Percent")}'
                          f'</span>',
                )),
            ),
            self.render_line(hline, user),
        )

    def test_render_auxiliary_edition_m2m(self):
        user = self.create_user()
        cat = FakeTodoCategory.objects.first()

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        todo = FakeTodo.objects.create(title='New logo', creme_entity=gainax)

        todo.categories.add(cat)

        hline = self.get_hline()
        self.assertEqual(history.TYPE_AUX_EDITION, hline.type)
        self.maxDiff = None
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-auxiliary_edition'
                ' history-line-collapsable history-line-collapsed">'
                ' <div class="history-line-main">'
                '  <div class="toggle-icon-container toggle-icon-expand" title="{expand_title}">'
                '   <div class="toggle-icon"></div>'
                '  </div>'
                '  <div class="toggle-icon-container toggle-icon-collapse"'
                '       title="{collapse_title}">'
                '   <div class="toggle-icon"></div>'
                '  </div>'
                '  <span class="history-line-title">{title}</span>'
                ' </div>'
                ' <ul class="history-line-details">'
                '  <li>{mod}</li>'
                ' </ul>'
                '<div>',
                title=_('“%(auxiliary_ctype)s“ edited: %(auxiliary_value)s') % {
                    'auxiliary_ctype': 'Test Todo',
                    'auxiliary_value': todo,
                },
                expand_title=_('Expand'),
                collapse_title=_('Close'),
                mod=mark_safe(_('{field} changed: {changes}').format(
                    field=(
                        f'<span class="field-change-field_name">'
                        f'{_("Categories")}'
                        f'</span>'
                    ),
                    changes=ngettext('{} was added', '{} were added', 1).format(
                        f'<span class="field-change-m2m_added">{cat}</span>'
                    ),
                )),
            ),
            self.render_line(hline, user),
        )

    def test_render_auxiliary_deletion(self):
        user = self.create_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        address = FakeAddress.objects.create(
            entity=gainax, country='Japan', city='Mitaka',
        )

        address.delete()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_AUX_DELETION, hline.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-auxiliary_deletion">'
                '{title}'
                '<div>',
                title=_('“%(auxiliary_ctype)s“ deleted: “%(auxiliary_value)s”') % {
                    'auxiliary_ctype': 'Test address',
                    'auxiliary_value': address,
                },
            ),
            self.render_line(hline, user),
        )

    def test_render_trash(self):
        user = self.create_user()
        gainax = self.refresh(
            FakeOrganisation.objects.create(user=user, name='Gainax')
        )

        gainax.trash()

        hline1 = self.get_hline()
        self.assertEqual(history.TYPE_TRASH, hline1.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-trash">{title}<div>',
                title=_('Sent to the trash'),
            ),
            self.render_line(hline1, user),
        )

        # ---
        self.refresh(gainax).restore()

        hline2 = self.get_hline()
        self.assertEqual(history.TYPE_TRASH, hline2.type)
        self.assertNotEqual(hline1.id, hline2.id)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-trash">{title}<div>',
                title=_('Restored'),
            ),
            self.render_line(hline2, user),
        )
