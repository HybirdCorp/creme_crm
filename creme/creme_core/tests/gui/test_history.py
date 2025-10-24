import json
from datetime import date
from decimal import Decimal
from functools import partial

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.formats import date_format, number_format
from django.utils.html import escape, format_html
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.bricks import HistoryBrick
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
        user = self.get_root_user()
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
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='<i>Acme</i>')

        # One modification ---
        orga = self.refresh(orga)
        orga.name = '<i>Acme corp</i>'
        orga.save()

        hline1 = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline1.type)
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">{_("Name")}</span>',
                    oldvalue='<span class="field-change-old_value">'
                             '&lt;i&gt;Acme&lt;/i&gt;'
                             '</span>',
                    value='<span class="field-change-new_value">'
                          '&lt;i&gt;Acme corp&lt;/i&gt;'
                          '</span>',
                ),
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
            '<div class="history-line history-line-edition">'
            ' <ul>'
            '  <li>{mod1}</li>'
            '  <li>{mod2}</li>'
            '  <li>{mod3}</li>'
            '  <li>{mod4}</li>'
            ' </ul>'
            '<div>'.format(
                mod1=self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("Email address")}</span>',
                    value=f'<span class="field-change-new_value">{orga.email}</span>',
                ),
                mod2=self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("Capital")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{number_format(orga.capital, force_grouping=True)}'
                          f'</span>',
                ),
                mod3=self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">{_("Subject to VAT")}</span>',
                    oldvalue=f'<span class="field-change-old_value">{_("Yes")}</span>',
                    value=f'<span class="field-change-new_value">{_("No")}</span>',
                ),
                mod4=self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("Date of creation")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{date_format(orga.creation_date, "DATE_FORMAT")}'
                          f'</span>',
                ),
            ),
            self.render_line(self.get_hline(), user),
        )

    def test_render_edition_invalid_field(self):
        user = self.get_root_user()

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
            '<div class="history-line history-line-edition">{}<div>'.format(
                _('“{field}” set').format(field=fname)
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_datefield(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Seele')

        orga = self.refresh(orga)
        orga.creation_date = date1 = date(year=2005, month=11, day=15)
        orga.save()

        hline1 = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline1.type)
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("Date of creation")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{date_format(date1, "DATE_FORMAT")}'
                          f'</span>',
                ),
            ),
            self.render_line(hline1, user),
        )

        # Datetime stored ---
        orga = self.refresh(orga)
        orga.creation_date = dt2 = self.create_datetime(
            year=2004, month=6, day=1, hour=12, minute=30,
        )
        orga.save()

        hline2 = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline2.type)
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">{_("Date of creation")}</span>',
                    oldvalue=f'<span class="field-change-old_value">'
                             f'{date_format(date1, "DATE_FORMAT")}'
                             f'</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{date_format(dt2, "DATE_FORMAT")}'
                          f'</span>',
                ),
            ),
            self.render_line(hline2, user),
        )

    def test_render_edition_datetimefield(self):
        user = self.get_root_user()

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
            '<div class="history-line history-line-edition">{}<div>'.format(
                self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("Start")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{date_format(activity.start, "DATETIME_FORMAT")}'
                          f'</span>',
                ),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_textfield(self):
        user = self.get_root_user()

        orga = FakeOrganisation.objects.create(user=user, name='Gainax')

        # 1 value ---
        old_description = 'Awesome!\nanimation studio'
        orga = self.refresh(orga)
        orga.description = old_description
        orga.save()

        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                _('{field} set {details_link}').format(
                    field=f'<span class="field-change-field_name">{_("Description")}</span>',
                    details_link=(
                        f'<a class="field-change-text_details" data-action="popover">'
                        f' {_("(see details)")}'
                        f' <summary>{_("Details of modifications")}</summary>'
                        f' <details>'
                        f'  <div class="history-line-field-change-text-old_value">'
                        f'   <h4>{_("Old value")}</h4><p class="empty-field">—</p>'
                        f'  </div>'
                        f'  <div class="history-line-field-change-text-new_value">'
                        f'   <h4>{_("New value")}</h4><p>Awesome!<br>animation studio</p>'
                        f'  </div>'
                        f' </details>'
                        f'</a>'
                    ),
                )
            ),
            self.render_line(self.get_hline(), user),
        )

        # 2 values ---
        orga = self.refresh(orga)
        orga.description = 'Created "Evangelion"'
        orga.save()

        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                _('{field} set {details_link}').format(
                    field=f'<span class="field-change-field_name">{_("Description")}</span>',
                    details_link=(
                        f'<a class="field-change-text_details" data-action="popover">'
                        f' {_("(see details)")}'
                        f' <summary>{_("Details of modifications")}</summary>'
                        f' <details>'
                        f'  <div class="history-line-field-change-text-old_value">'
                        f'   <h4>{_("Old value")}</h4><p>Awesome!<br>animation studio</p>'
                        f'  </div>'
                        f'  <div class="history-line-field-change-text-new_value">'
                        f'   <h4>{_("New value")}</h4><p>{orga.description}</p>'
                        f'  </div>'
                        f' </details>'
                        f'</a>'
                    ),
                )
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
            '<div class="history-line history-line-edition">{}<div>'.format(
                _('{field} emptied {details_link}').format(
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
                        f'   <h4>{_("New value")}</h4><p class="empty-field">—</p>'
                        f'  </div>'
                        f' </details>'
                        f'</a>'
                    ),
                ),
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
            '<div class="history-line history-line-edition">{}<div>'.format(
                _('{field} set').format(
                    field=f'<span class="field-change-field_name">{_("Description")}</span>',
                ),
            ),
            self.render_line(self.refresh(hline3), user),
        )

    def test_render_edition_choices(self):
        "Field with <choices> attribute."
        user = self.get_root_user()

        camp = FakeEmailCampaign.objects.create(
            user=user, name='Campaign for Seele products',
            status=FakeEmailCampaign.Status.WAITING,
            type=None,
        )

        camp = self.refresh(camp)
        camp.status = FakeEmailCampaign.Status.SENT_OK
        camp.type = FakeEmailCampaign.Type.EXTERNAL
        camp.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline.type)
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">'
            ' <ul>'
            '  <li>{mod1}</li>'
            '  <li>{mod2}</li>'
            ' </ul>'
            '<div>'.format(
                mod1=self.FMT_2_VALUES(
                    field='<span class="field-change-field_name">Type</span>',
                    value='<span class="field-change-new_value">External</span>',
                ),
                mod2=self.FMT_3_VALUES(
                    field='<span class="field-change-field_name">Status</span>',
                    oldvalue='<span class="field-change-old_value">Waiting</span>',
                    value='<span class="field-change-new_value">Sent</span>',
                ),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_set_null01(self):
        "BooleanField."
        user = self.get_root_user()

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
            '<div class="history-line history-line-edition">{}<div>'.format(
                self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">{_("Loves comics")}</span>',
                    oldvalue=f'<span class="field-change-old_value">{_("Yes")}</span>',
                    value=f'<span class="field-change-new_value">{_("N/A")}</span>',
                ),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_set_null02(self):
        "IntegerField."
        user = self.get_root_user()

        old_capital = 1000
        orga = FakeOrganisation.objects.create(user=user, name='Acme', capital=old_capital)

        orga = self.refresh(orga)
        orga.capital = None
        orga.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline.type)
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                _('{field} emptied (it was {oldvalue})').format(
                    field=f'<span class="field-change-field_name">{_("Capital")}</span>',
                    oldvalue=f'<span class="field-change-old_value">'
                             f'{number_format(old_capital, force_grouping=True)}'
                             f'</span>',
                ),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_fk01(self):
        # new value format '["Hayao Miyazaki", ["position_id", X], ["image_id", X]]'
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

        hayao = FakeContact.objects.create(
            user=user, first_name='Hayao', last_name='Miyazaki',
        )
        img = FakeImage.objects.create(user=user, name='<b>Grumpy</b> Hayao')
        # NB: should be escaped
        position = FakePosition.objects.create(title='Director<br>')

        hayao = self.refresh(hayao)
        hayao.image = img
        hayao.position = position
        hayao.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline.type)
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">'
            ' <ul>'
            '  <li>{mod1}</li>'
            '  <li>{mod2}</li>'
            ' </ul>'
            '<div>'.format(
                mod1=_('{field} set to {value}').format(
                    field=f'<span class="field-change-field_name">{_("Position")}</span>',
                    value=f'<span class="field-change-new_value">{escape(position.title)}</span>',
                ),
                mod2=_('{field} set to {value}').format(
                    field=f'<span class="field-change-field_name">{_("Photograph")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'<a href="{img.get_absolute_url()}" target="_self">'
                          f'&lt;b&gt;Grumpy&lt;/b&gt; Hayao'
                          f'</a>'
                          f'</span>',
                ),
            ),
            self.render_line(hline, user),
        )

        # Deleted instances
        img_id = img.id
        img.delete()

        position_id = position.id
        position.delete()

        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">'
            ' <ul>'
            '  <li>{mod1}</li>'
            '  <li>{mod2}</li>'
            ' </ul>'
            '<div>'.format(
                mod1=_('{field} set to {value}').format(
                    field=f'<span class="field-change-field_name">{_("Position")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{_("{pk} (deleted)").format(pk=position_id)}'
                          f'</span>',
                ),
                mod2=_('{field} set to {value}').format(
                    field=f'<span class="field-change-field_name">{_("Photograph")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{_("{pk} (deleted)").format(pk=img_id)}'
                          f'</span>',
                ),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_fk01__old_fk_format(self):
        # new value format '["Hayao Miyazaki", ["position_id", X], ["image_id", X]]'
        # old value format '["Hayao Miyazaki", ["position", X], ["image", X]]'
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

        img = FakeImage.objects.create(user=user, name='<b>Grumpy</b> Hayao')
        # NB: should be escaped
        position = FakePosition.objects.create(title='Director<br>')

        hayao = FakeContact.objects.create(
            user=user,
            first_name='Hayao',
            last_name='Miyazaki',
            image=img,
            position=position
        )

        hline = HistoryLine.objects.create(
            entity=hayao,
            entity_ctype=ContentType.objects.get_for_model(hayao),
            type=history.TYPE_EDITION,
            value=json.dumps(["Hayao Miyazaki", ["position", position.id], ["image", img.id]]),
            entity_owner=user,
        )

        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">'
            ' <ul>'
            '  <li>{mod1}</li>'
            '  <li>{mod2}</li>'
            ' </ul>'
            '<div>'.format(
                mod1=_('{field} set to {value}').format(
                    field=f'<span class="field-change-field_name">{_("Position")}</span>',
                    value=f'<span class="field-change-new_value">{escape(position.title)}</span>',
                ),
                mod2=_('{field} set to {value}').format(
                    field=f'<span class="field-change-field_name">{_("Photograph")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'<a href="{img.get_absolute_url()}" target="_self">'
                          f'&lt;b&gt;Grumpy&lt;/b&gt; Hayao'
                          f'</a>'
                          f'</span>',
                ),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_fk02(self):
        "Not allowed to see."
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

        hayao = FakeContact.objects.create(
            user=user, first_name='Hayao', last_name='Miyazaki',
        )
        img = FakeImage.objects.create(user=self.get_root_user(), name='Grumpy Hayao')

        hayao = self.refresh(hayao)
        hayao.image = img
        hayao.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline.type)
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                _('{field} set to {value}').format(
                    field=f'<span class="field-change-field_name">{_("Photograph")}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{settings.HIDDEN_VALUE}'
                          f'</span>',
                ),
            ),
            self.render_line(hline, user),
        )

    def test_render_edition_m2m01(self):
        user = self.get_root_user()
        cat1, cat2 = FakeImageCategory.objects.order_by('id')[:2]
        cat3 = FakeImageCategory.objects.create(name='<i>grumpy</i>')

        img = FakeImage.objects.create(user=user, name='Grumpy Hayao')

        # One addition ---
        img.categories.add(cat1)
        hline1 = self.get_hline()
        self.assertEqual(history.TYPE_EDITION, hline1.type)

        field_msg = f'<span class="field-change-field_name">{_("Categories")}</span>'
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                _('{field} changed: {changes}').format(
                    field=field_msg,
                    changes=ngettext('{} was added', '{} were added', 1).format(
                        f'<span class="field-change-m2m_added">{cat1}</span>'
                    ),
                ),
            ),
            self.render_line(hline1, user),
        )

        # Several addition ---
        self.refresh(img).categories.set([cat1, cat2, cat3])

        first_cat1, second_cat1 = sorted([cat2.name, '&lt;i&gt;grumpy&lt;/i&gt;'])
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                _('{field} changed: {changes}').format(
                    field=field_msg,
                    changes=ngettext('{} was added', '{} were added', 2).format(
                        f'<span class="field-change-m2m_added">{first_cat1}</span>, '
                        f'<span class="field-change-m2m_added">{second_cat1}</span>'
                    ),
                ),
            ),
            self.render_line(self.get_hline(), user),
        )

        # One removing ---
        self.refresh(img).categories.remove(cat2)
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                _('{field} changed: {changes}').format(
                    field=field_msg,
                    changes=ngettext('{} was removed', '{} were removed', 1).format(
                        f'<span class="field-change-m2m_removed">{cat2}</span>'
                    ),
                ),
            ),
            self.render_line(self.get_hline(), user),
        )

        # Several removing
        first_cat2, second_cat2 = sorted([cat1.name, '&lt;i&gt;grumpy&lt;/i&gt;'])
        self.refresh(img).categories.clear()
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                _('{field} changed: {changes}').format(
                    field=field_msg,
                    changes=ngettext('{} was removed', '{} were removed', 2).format(
                        f'<span class="field-change-m2m_removed">{first_cat2}</span>, '
                        f'<span class="field-change-m2m_removed">{second_cat2}</span>'
                    ),
                ),
            ),
            self.render_line(self.get_hline(), user),
        )

    def test_render_edition_m2m02(self):
        "Adding & removing at the same time."
        user = self.get_root_user()
        cat1, cat2, cat3 = FakeImageCategory.objects.order_by('id')[:3]

        img = FakeImage.objects.create(user=user, name='Grumpy Hayao')
        img.categories.add(cat2)

        self.refresh(img).categories.set([cat1, cat3])

        first_cat, second_cat = sorted([cat1.name, cat3.name])
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                _('{field} changed: {changes}').format(
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
                ),
            ),
            self.render_line(self.get_hline(), user),
        )

    def test_render_edition_m2m03(self):
        "M2M to entities."
        user = self.login_as_standard()
        self.add_credentials(user.role, own=['VIEW'])

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
            '<div class="history-line history-line-edition">{}<div>'.format(
                change_fmt(
                    field=field_msg,
                    changes=ngettext('{} was added', '{} were added', 1).format(
                        f'<span class="field-change-m2m_added">'
                        f'<a href="{ml.get_absolute_url()}" target="_self">{ml}</a>'
                        f'</span>'
                    ),
                ),
            ),
            self.render_line(self.get_hline(), user),
        )

        # Removing ----
        self.refresh(campaign).mailing_lists.remove(ml)
        hline2 = self.get_hline()
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                change_fmt(
                    field=field_msg,
                    changes=ngettext('{} was removed', '{} were removed', 1).format(
                        f'<span class="field-change-m2m_removed">'
                        f'<a href="{ml.get_absolute_url()}" target="_self">{ml}</a>'
                        f'</span>'
                    ),
                ),
            ),
            self.render_line(hline2, user),
        )

        # Credentials ---
        ml.user = self.get_root_user()
        ml.save()
        self.assertHTMLEqual(
            '<div class="history-line history-line-edition">{}<div>'.format(
                change_fmt(
                    field=field_msg,
                    changes=ngettext('{} was removed', '{} were removed', 1).format(
                        f'<span class="field-change-m2m_removed">'
                        f'{settings.HIDDEN_VALUE}'
                        f'</span>'
                    ),
                ),
            ),
            self.render_line(hline2, user),
        )

    def test_render_edition_prefetching(self):
        user = self.get_root_user()

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
        user = self.get_root_user()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        cfield1 = create_cfield(name='Punch line',   field_type=CustomField.STR)
        cfield2 = create_cfield(name='First attack', field_type=CustomField.DATE)
        cfield3 = create_cfield(name='<i>Power</i>', field_type=CustomField.INT)

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
            '<div class="history-line history-line-custom_edition">'
            ' <ul>'
            '  <li>{mod1}</li>'
            '  <li>{mod2}</li>'
            '  <li>{mod3}</li>'
            ' </ul>'
            '<div>'.format(
                mod1=self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{cfield1.name}</span>',
                    value=f'<span class="field-change-new_value">{value_str1}</span>',
                ),
                mod2=self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{cfield2.name}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{date_format(value_date, "DATE_FORMAT")}'
                          f'</span>',
                ),
                mod3=self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{escape(cfield3.name)}</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{number_format(value_int, force_grouping=True)}'
                          f'</span>',
                ),
            ),
            self.render_line(hline1, user),
        )

        # Old & new value ---
        self.clear_global_info()  # Current line is stored in global cache

        value_str2 = 'We fight angels'
        save_cvalues(cfield1, [nerv], value_str2)

        hline2 = self.get_hline()
        self.assertEqual(history.TYPE_CUSTOM_EDITION, hline2.type)
        self.assertNotEqual(hline1, hline2)

        self.assertHTMLEqual(
            '<div class="history-line history-line-custom_edition">{}<div>'.format(
                self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">{cfield1.name}</span>',
                    oldvalue=f'<span class="field-change-old_value">{value_str1}</span>',
                    value=f'<span class="field-change-new_value">{value_str2}</span>',
                ),
            ),
            self.render_line(hline2, user),
        )

    def test_render_custom_edition02(self):
        "Enum & multi-enum."
        user = self.get_root_user()

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
            '<div class="history-line history-line-custom_edition">'
            ' <ul>'
            '  <li>{mod1}</li>'
            '  <li>{mod2}</li>'
            ' </ul>'
            '<div>'.format(
                mod1=self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{cfield1.name}</span>',
                    value=f'<span class="field-change-new_value">{choice1}</span>',
                ),
                mod2=_('{field} changed: {changes}').format(
                    field=f'<span class="field-change-field_name">{cfield2.name}</span>',
                    changes=ngettext('{} was added', '{} were added', 1).format(
                        f'<span class="field-change-m2m_added">{choice2}</span>'
                    ),
                ),
            ),
            self.render_line(hline1, user),
        )

    def test_render_custom_edition03(self):
        "Deleted CustomField."
        user = self.get_root_user()

        cfield = CustomField.objects.create(
            content_type=FakeOrganisation, name='Punch line', field_type=CustomField.STR,
        )
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        CustomFieldValue.save_values_for_entities(cfield, [nerv], 'Future proof')

        self.clear_global_info()  # Current line is stored in global cache
        cfield_id = cfield.id
        cfield.delete()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_CUSTOM_EDITION, hline.type)
        self.assertHTMLEqual(
            '<div class="history-line history-line-custom_edition">{}<div>'.format(
                _('Deleted field (with id={id}) set').format(id=cfield_id),
            ),
            self.render_line(hline, user),
        )

    def test_render_custom_edition04(self):
        "Invalid value (does not match CustomField type)."
        user = self.get_root_user()

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
        user = self.get_root_user()

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

        self.clear_global_info()
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
        user = self.get_root_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')

        gainax.delete()
        hline = self.get_hline()
        self.assertEqual(history.TYPE_DELETION,  hline.type)
        self.assertHTMLEqual(
            '<div class="history-line history-line-deletion"><div>',
            self.render_line(hline, user),
        )

    def test_render_related_edition(self):
        user = self.get_root_user()
        ghibli = FakeOrganisation.objects.create(user=user, name='Ghibli')

        hayao = FakeContact.objects.create(user=user, last_name='<i>Miyazaki</i>')

        rtype = RelationType.objects.builder(
            id='test-subject_employed', predicate='is employed',
        ).symmetric(id='test-object_employed', predicate='employs').get_or_create()[0]
        Relation.objects.create(
            user=user, subject_entity=hayao, object_entity=ghibli, type=rtype,
        )

        HistoryConfigItem.objects.create(relation_type=rtype)

        hayao = self.refresh(hayao)
        # hayao.description = 'A great animation movie maker'  # TODO: more complex mods
        hayao.first_name = 'Hayao'
        hayao.save()

        self.maxDiff = None
        hline = self.get_hline()
        self.assertEqual(history.TYPE_RELATED, hline.type)
        self.assertHTMLEqual(
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
            '<div>'.format(
                title=_('%(entity_link)s edited') % {
                    'entity_link':
                        f'<a href="{hayao.get_absolute_url()}" target="_self">{escape(hayao)}</a>',
                },
                expand_title=_('Expand'),
                collapse_title=_('Close'),
                mod=self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("First name")}</span>',
                    value=f'<span class="field-change-new_value">{hayao.first_name}</span>',
                ),
            ),
            self.render_line(hline, user),
        )

        # Deleted entity ---
        hayao_repr = escape(hayao)
        hayao.delete()
        self.maxDiff = None
        self.assertHTMLEqual(
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
            '<div>'.format(
                title=_('“%(entity)s“ edited') % {'entity': hayao_repr},
                expand_title=_('Expand'),
                collapse_title=_('Close'),
                mod=self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("First name")}</span>',
                    value=f'<span class="field-change-new_value">{hayao.first_name}</span>',
                ),
            ),
            self.render_line(self.refresh(hline), user),
        )

    def test_render_property_addition(self):
        user = self.get_root_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')

        text = 'Make <i>anime</i> series'
        ptype = CremePropertyType.objects.create(text=text)
        prop = CremeProperty.objects.create(type=ptype, creme_entity=gainax)

        hline = self.get_hline()
        self.assertEqual(history.TYPE_PROP_ADD, hline.type)
        html_format_str = '<div class="history-line history-line-property_addition">{}<div>'
        self.assertHTMLEqual(
            html_format_str.format(_('%(property_text)s added') % {
                'property_text': f'<span class="property-text">{escape(text)}</span>',
            }),
            self.render_line(hline, user),
        )

        # ---
        ptype_id = ptype.id
        prop.delete()
        ptype.delete()
        self.assertHTMLEqual(
            html_format_str.format(_('%(property_text)s added') % {
                # TODO: "?? (id=XX)"
                'property_text': f'<span class="property-text">{ptype_id}</span>',
            }),
            self.render_line(hline, user),
        )

    def test_render_property_deletion(self):
        user = self.get_root_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')

        text = 'Make <i>anime</i> series'
        ptype = CremePropertyType.objects.create(text=text)
        prop = CremeProperty.objects.create(type=ptype, creme_entity=gainax)

        prop.delete()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_PROP_DEL, hline.type)

        html_format_str = '<div class="history-line history-line-property_deletion">{}<div>'
        self.assertHTMLEqual(
            html_format_str.format(_('%(property_text)s removed') % {
                'property_text': f'<span class="property-text">{escape(text)}</span>',
            }),
            self.render_line(hline, user),
        )

        # ---
        ptype_id = ptype.id
        ptype.delete()
        self.assertHTMLEqual(
            html_format_str.format(_('%(property_text)s removed') % {
                'property_text': f'<span class="property-text">{ptype_id}</span>',
            }),
            self.render_line(hline, user),
        )

    def test_render_property_prefetching(self):
        user = self.get_root_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Makes anime series')
        ptype2 = create_ptype(text='Makes film')

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
        user = self.get_root_user()
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        rtype = RelationType.objects.builder(
            id='test-subject_works', predicate='is <i>employed</i>',
        ).symmetric(id='test-object_works', predicate='employs').get_or_create()[0]
        relation = Relation.objects.create(
            user=user, subject_entity=rei, object_entity=nerv, type=rtype,
        )

        hline_sym, hline = HistoryLine.objects.order_by('-id')[:2]

        self.assertEqual(history.TYPE_RELATION, hline.type)
        html_format_str = (
            '<div class="history-line history-line-relationship_addition">{}<div>'
        )
        self.assertHTMLEqual(
            html_format_str.format(_('%(predicate)s added to %(entity_link)s') % {
                'predicate': f'<span class="relationship-predicate">'
                             f'{escape(rtype.predicate)}'
                             f'</span>',  # <==
                'entity_link': f'<a href="{nerv.get_absolute_url()}" target="_self">{nerv}</a>',
            }),
            self.render_line(hline, user),
        )

        self.assertEqual(history.TYPE_SYM_RELATION, hline_sym.type)
        self.assertHTMLEqual(
            html_format_str.format(_('%(predicate)s added to %(entity_link)s') % {
                'predicate': f'<span class="relationship-predicate">'
                             f'{rtype.symmetric_type.predicate}'
                             f'</span>',  # <==
                'entity_link': f'<a href="{rei.get_absolute_url()}" target="_self">{rei}</a>',
            }),
            self.render_line(hline_sym, user),
        )

        # Deleted relation-type ---
        rtype_id = rtype.id
        relation.delete()
        rtype.delete()
        self.assertDoesNotExist(relation)
        self.assertDoesNotExist(rtype)
        self.assertHTMLEqual(
            html_format_str.format(_('%(predicate)s added to %(entity_link)s') % {
                'predicate': f'<span class="relationship-predicate">'
                             f'{rtype_id}'
                             f'</span>',  # <==
                'entity_link': f'<a href="{nerv.get_absolute_url()}" target="_self">{nerv}</a>',
            }),
            self.render_line(self.refresh(hline), user),
        )

        # Deleted entity ---
        nerv_repr = str(nerv)
        nerv.delete()
        self.assertHTMLEqual(
            html_format_str.format(_('%(predicate)s added to “%(entity)s“') % {
                'predicate': f'<span class="relationship-predicate">'
                             f'{rtype_id}'
                             f'</span>',  # <==
                'entity': nerv_repr,
            }),
            self.render_line(self.refresh(hline), user),
        )

    def test_render_relation_deletion(self):
        user = self.get_root_user()
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        rtype = RelationType.objects.builder(
            id='test-subject_works', predicate='is <i>employed</i>',
        ).symmetric(id='test-object_works', predicate='employs').get_or_create()[0]
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
            html_format_str.format(_('%(predicate)s to %(entity_link)s removed') % {
                'predicate': f'<span class="relationship-predicate">'
                             f'{escape(rtype.predicate)}'
                             f'</span>',  # <==
                'entity_link':
                    f'<a href="{nerv.get_absolute_url()}" target="_self">{nerv}</a>',
            }),
            self.render_line(hline, user),
        )

        self.assertEqual(history.TYPE_SYM_REL_DEL, hline_sym.type)
        self.assertHTMLEqual(
            html_format_str.format(_('%(predicate)s to %(entity_link)s removed') % {
                'predicate': f'<span class="relationship-predicate">'
                             f'{rtype.symmetric_type.predicate}'
                             f'</span>',  # <==
                'entity_link': f'<a href="{rei.get_absolute_url()}" target="_self">{rei}</a>',
            }),
            self.render_line(hline_sym, user),
        )

        # ---
        rtype_id = rtype.id
        rtype.delete()
        self.assertDoesNotExist(rtype)
        self.assertHTMLEqual(
            html_format_str.format(_('%(predicate)s to %(entity_link)s removed') % {
                'predicate': f'<span class="relationship-predicate">'
                             f'{rtype_id}'
                             f'</span>',  # <==
                'entity_link':
                    f'<a href="{nerv.get_absolute_url()}" target="_self">{nerv}</a>',
            }),
            self.render_line(self.refresh(hline), user),
        )

        # Deleted entity ---
        nerv_repr = str(nerv)
        nerv.delete()
        self.assertHTMLEqual(
            html_format_str.format(_('%(predicate)s to “%(entity)s“ removed') % {
                'predicate': f'<span class="relationship-predicate">'
                             f'{rtype_id}'
                             f'</span>',
                'entity': nerv_repr,  # <==
            }),
            self.render_line(self.refresh(hline), user),
        )

    def test_render_relation_prefetching(self):
        user = self.get_root_user()

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')

        rtype1 = RelationType.objects.builder(
            id='test-subject_works', predicate='is employed',
        ).symmetric(id='test-object_works', predicate='employs').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_pilot', predicate='is pilot for',
        ).symmetric(id='test-object_pilot', predicate='has pilot').get_or_create()[0]

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
        user = self.get_root_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        address = FakeAddress.objects.create(
            entity=gainax, country='Japan', city='<b>Mitaka</b>',
        )

        hline = self.get_hline()
        self.assertEqual(history.TYPE_AUX_CREATION, hline.type)
        self.assertHTMLEqual(
            '<div class="history-line history-line-auxiliary_creation">'
            '{title}'
            '<div>'.format(
                title=_('“%(auxiliary_ctype)s“ added: %(auxiliary_value)s') % {
                    'auxiliary_ctype': 'Test address',
                    'auxiliary_value': escape(address),
                },
            ),
            self.render_line(hline, user),
        )

    def test_render_auxiliary_creation__invalid_ctype_id(self):
        user = self.get_root_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        address = FakeAddress.objects.create(
            entity=gainax, country='Japan', city='Tokyo',
        )

        hline = self.get_hline()
        self.assertEqual(history.TYPE_AUX_CREATION, hline.type)
        # print(hline.value)

        self.assertListEqual(
            [
                'Gainax',
                ContentType.objects.get_for_model(FakeAddress).id,
                address.id,
                'Tokyo Japan',
            ],
            json.loads(hline.value),
        )
        hline.value = json.dumps([
            'Gainax',
            self.UNUSED_PK,  # <==
            address.id,
            'Tokyo Japan',
        ])
        hline.save()

        self.assertHTMLEqual(
            '<div class="history-line history-line-auxiliary_creation">'
            '{title}'
            '<div>'.format(
                title=_('“%(auxiliary_ctype)s“ added: %(auxiliary_value)s') % {
                    'auxiliary_ctype': '??',
                    'auxiliary_value': escape(address),
                },
            ),
            self.render_line(hline, user),
        )

    def test_render_auxiliary_edition(self):
        user = self.get_root_user()

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
            '<div>'.format(
                title=_('“%(auxiliary_ctype)s“ edited: %(auxiliary_value)s') % {
                    'auxiliary_ctype': 'Test address',
                    'auxiliary_value': address,
                },
                expand_title=_('Expand'),
                collapse_title=_('Close'),
                mod1=self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">{_("City")}</span>',
                    oldvalue=f'<span class="field-change-old_value">{old_city}</span>',
                    value=f'<span class="field-change-new_value">{address.city}</span>',
                ),
                mod2=self.FMT_2_VALUES(
                    field=f'<span class="field-change-field_name">{_("Department")}</span>',
                    value=f'<span class="field-change-new_value">{address.department}</span>',
                ),
            ),
            self.render_line(hline, user),
        )

    def test_render_auxiliary_edition__entity(self):
        """FakeInvoiceLine:
        - an auxiliary + CremeEntity at the same time.
        - DecimalField.
        - field with choices.
        """
        user = self.get_root_user()
        invoice = FakeInvoice.objects.create(
            user=user, name='Invoice', expiration_date=date(year=2021, month=12, day=15),
        )
        old_quantity = Decimal('1.30')
        pline = FakeInvoiceLine.objects.create(
            item='DeathNote', user=user,
            linked_invoice=invoice, quantity=old_quantity,
            discount_unit=FakeInvoiceLine.Discount.AMOUNT,
        )

        pline = self.refresh(pline)
        pline.quantity = Decimal('2.5')
        pline.discount_unit = FakeInvoiceLine.Discount.PERCENT
        pline.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_AUX_EDITION, hline.type)
        self.maxDiff = None
        self.assertHTMLEqual(
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
            '<div>'.format(
                title=_('“%(auxiliary_ctype)s“ edited: %(auxiliary_value)s') % {
                    'auxiliary_ctype': 'Test Invoice Line',
                    'auxiliary_value': pline,
                },
                expand_title=_('Expand'),
                collapse_title=_('Close'),
                mod1=self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">'
                          f'{_("Quantity")}'
                          f'</span>',
                    oldvalue=f'<span class="field-change-old_value">'
                             f'{number_format(old_quantity)}'
                             f'</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{number_format(pline.quantity)}'
                          f'</span>',
                ),
                mod2=self.FMT_3_VALUES(
                    field=f'<span class="field-change-field_name">'
                          f'{_("Discount Unit")}'
                          f'</span>',
                    oldvalue=f'<span class="field-change-old_value">'
                             f'{_("Amount")}'
                             f'</span>',
                    value=f'<span class="field-change-new_value">'
                          f'{_("Percent")}'
                          f'</span>',
                ),
            ),
            self.render_line(hline, user),
        )

    def test_render_auxiliary_edition__m2m(self):
        user = self.get_root_user()
        cat = FakeTodoCategory.objects.create(name='Very <b>Important</b>')

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        todo = FakeTodo.objects.create(title='New logo', creme_entity=gainax)

        todo.categories.add(cat)

        hline = self.get_hline()
        self.assertEqual(history.TYPE_AUX_EDITION, hline.type)
        self.maxDiff = None
        self.assertHTMLEqual(
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
            '<div>'.format(
                title=_('“%(auxiliary_ctype)s“ edited: %(auxiliary_value)s') % {
                    'auxiliary_ctype': 'Test Todo',
                    'auxiliary_value': todo,
                },
                expand_title=_('Expand'),
                collapse_title=_('Close'),
                mod=_('{field} changed: {changes}').format(
                    field=(
                        f'<span class="field-change-field_name">'
                        f'{_("Categories")}'
                        f'</span>'
                    ),
                    changes=ngettext('{} was added', '{} were added', 1).format(
                        f'<span class="field-change-m2m_added">{escape(cat)}</span>'
                    ),
                ),
            ),
            self.render_line(hline, user),
        )

    def test_render_auxiliary_edition__invalid_ctype_id(self):
        user = self.get_root_user()

        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        address = FakeAddress.objects.create(entity=gainax, country='Japan')

        address = self.refresh(address)
        address.department = 'Tokyo'
        address.save()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_AUX_EDITION, hline.type)
        self.assertListEqual(
            [
                'Gainax',
                [
                    ContentType.objects.get_for_model(FakeAddress).id,
                    address.id,
                    'Tokyo Japan',
                ],
                ['department', 'Tokyo'],
            ],
            json.loads(hline.value),
        )
        hline.value = json.dumps([
            'Gainax',
            [
                self.UNUSED_PK,  # <==
                address.id,
                'Tokyo Japan',
            ],
            ['department', 'Tokyo'],
        ])
        hline.save()
        self.maxDiff = None
        self.assertHTMLEqual(
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
            ' <ul class="history-line-details"></ul>'
            '<div>'.format(
                title=_('“%(auxiliary_ctype)s“ edited: %(auxiliary_value)s') % {
                    'auxiliary_ctype': '??',
                    'auxiliary_value': address,
                },
                expand_title=_('Expand'),
                collapse_title=_('Close'),
            ),
            self.render_line(hline, user),
        )

    def test_render_auxiliary_deletion(self):
        user = self.get_root_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        address = FakeAddress.objects.create(
            entity=gainax, country='Japan', city='<b>Mitaka</b>',
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

    def test_render_auxiliary_deletion__invalid_ctype_id(self):
        user = self.get_root_user()
        gainax = FakeOrganisation.objects.create(user=user, name='Gainax')
        address = FakeAddress.objects.create(
            entity=gainax, country='Japan', city='Tokyo',
        )

        address.delete()

        hline = self.get_hline()
        self.assertEqual(history.TYPE_AUX_DELETION, hline.type)
        self.assertListEqual(
            [
                'Gainax',
                ContentType.objects.get_for_model(FakeAddress).id,
                'Tokyo Japan',
            ],
            json.loads(hline.value),
        )

        hline.value = json.dumps([
            'Gainax',
            self.UNUSED_PK,  # <==
            'Tokyo Japan',
        ])

        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-auxiliary_deletion">'
                '{title}'
                '<div>',
                title=_('“%(auxiliary_ctype)s“ deleted: “%(auxiliary_value)s”') % {
                    'auxiliary_ctype': '??',
                    'auxiliary_value': address,
                },
            ),
            self.render_line(hline, user),
        )

    def test_render_trash(self):
        user = self.get_root_user()
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
