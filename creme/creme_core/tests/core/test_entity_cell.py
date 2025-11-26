from copy import deepcopy
from datetime import date
from decimal import Decimal
from functools import partial

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.utils.formats import date_format, number_format
from django.utils.timezone import localtime
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.utils.translation import override as override_language

from creme.creme_core.core.entity_cell import (
    CELLS_MAP,
    EntityCell,
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegistry,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.function_field import (
    FunctionField,
    FunctionFieldResult,
    function_field_registry,
)
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldEnumValue,
    FakeCivility,
    FakeContact,
    FakeDocument,
    FakeEmailCampaign,
    FakeFolder,
    FakeImage,
    FakeMailingList,
    FakePosition,
    FakeTodo,
    FieldsConfig,
    Language,
    Relation,
    RelationType,
)

from ..base import CremeTestCase


class EntityCellRegistryTestCase(CremeTestCase):
    def test_global(self):
        self.assertEqual(EntityCellRegularField,  CELLS_MAP[EntityCellRegularField.type_id])
        self.assertEqual(EntityCellCustomField,   CELLS_MAP[EntityCellCustomField.type_id])
        self.assertEqual(EntityCellFunctionField, CELLS_MAP[EntityCellFunctionField.type_id])
        self.assertEqual(EntityCellRelation,      CELLS_MAP[EntityCellRelation.type_id])

    def test_register(self):
        registry = EntityCellRegistry()

        with self.assertRaises(KeyError):
            registry[EntityCellRegularField.type_id]  # NOQA

        self.assertNotIn(EntityCellFunctionField.type_id, registry)
        self.assertListEqual([], [*registry.cell_classes])

        res = registry.register(EntityCellRegularField, EntityCellFunctionField)
        self.assertIs(res, registry)

        self.assertEqual(EntityCellRegularField,  registry[EntityCellRegularField.type_id])
        self.assertEqual(EntityCellFunctionField, registry[EntityCellFunctionField.type_id])

        self.assertIn(EntityCellRegularField.type_id,  registry)
        self.assertIn(EntityCellFunctionField.type_id, registry)

        self.assertCountEqual(
            [EntityCellRegularField, EntityCellFunctionField],
            [*registry.cell_classes],
        )

    def test_register__duplicate(self):
        registry = EntityCellRegistry().register(EntityCellRegularField)

        class DuplicatedIdCell(EntityCell):
            type_id = EntityCellRegularField.type_id

        with self.assertRaises(EntityCellRegistry.RegistrationError):
            registry.register(DuplicatedIdCell)

    def test_call(self):
        registry = EntityCellRegistry()

        with self.assertRaises(KeyError):
            registry[EntityCellRegularField.type_id]  # NOQA

        self.assertNotIn(EntityCellRegularField.type_id, registry)

        res = registry(EntityCellRegularField)
        self.assertIs(res, EntityCellRegularField)
        self.assertEqual(EntityCellRegularField, registry[EntityCellRegularField.type_id])

        self.assertIn(EntityCellRegularField.type_id, registry)

    def test_deepcopy(self):
        registry1 = EntityCellRegistry()
        registry1(EntityCellRegularField)
        registry1(EntityCellCustomField)

        registry2 = deepcopy(registry1)
        registry2(EntityCellFunctionField)

        with self.assertNoException():
            registry1[EntityCellRegularField.type_id]
            registry2[EntityCellRegularField.type_id]

            registry1[EntityCellCustomField.type_id]
            registry2[EntityCellCustomField.type_id]

            registry2[EntityCellFunctionField.type_id]

        with self.assertRaises(KeyError):
            registry1[EntityCellFunctionField.type_id]

    def test_build_cell_from_dict(self):
        build = partial(CELLS_MAP.build_cell_from_dict, model=FakeContact)
        cell1 = build(dict_cell={
            'type': EntityCellRegularField.type_id,
            'value': 'first_name',
        })
        self.assertIsInstance(cell1, EntityCellRegularField)
        self.assertEqual(FakeContact,  cell1.model)
        self.assertEqual('first_name', cell1.value)

        cell2 = build(dict_cell={
            'type': EntityCellFunctionField.type_id,
            'value': 'get_pretty_properties',
        })
        self.assertIsInstance(cell2, EntityCellFunctionField)
        self.assertEqual(FakeContact,             cell2.model)
        self.assertEqual('get_pretty_properties', cell2.value)

        with self.assertLogs(level='WARNING'):
            self.assertIsNone(build(dict_cell={
                'type': EntityCellRegularField.type_id,
                'value': 'invalid',
            }))

        with self.assertLogs(level='ERROR'):
            self.assertIsNone(build(dict_cell={
                # 'type': EntityCellRegularField.type_id,
                'value': 'first_name',
            }))

        with self.assertLogs(level='ERROR'):
            self.assertIsNone(build(dict_cell={
                'type': EntityCellRegularField.type_id,
                # 'value': 'first_name',
            }))

        with self.assertLogs(level='ERROR'):
            self.assertIsNone(build(dict_cell={
                'type': 'not_registered',  # <==
                'value': 'first_name',
            }))

    def test_build_cells_from_dicts(self):
        cells, errors = CELLS_MAP.build_cells_from_dicts(
            model=FakeContact,
            dicts=[
                {'type': EntityCellRegularField.type_id,  'value': 'first_name'},
                {'type': EntityCellFunctionField.type_id, 'value': 'get_pretty_properties'},
            ],
        )
        self.assertIs(errors, False)
        self.assertEqual(2, len(cells))

        cell1 = cells[0]
        self.assertIsInstance(cell1, EntityCellRegularField)
        self.assertEqual(FakeContact,  cell1.model)
        self.assertEqual('first_name', cell1.value)

        cell2 = cells[1]
        self.assertIsInstance(cell2, EntityCellFunctionField)
        self.assertEqual(FakeContact,             cell2.model)
        self.assertEqual('get_pretty_properties', cell2.value)

    def test_build_cells_from_dicts__error(self):
        with self.assertLogs(level='WARNING'):
            cells, errors = CELLS_MAP.build_cells_from_dicts(
                model=FakeDocument,
                dicts=[
                    {'type': EntityCellRegularField.type_id,  'value': 'invalid'},
                    {'type': EntityCellFunctionField.type_id, 'value': 'get_pretty_properties'},
                ],
            )
        self.assertIs(errors, True)

        cell = self.get_alone_element(cells)
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(FakeDocument,            cell.model)
        self.assertEqual('get_pretty_properties', cell.value)

    def test_build_cell_from_key(self):
        build = partial(CELLS_MAP.build_cell_from_key, model=FakeContact)
        cell1 = build(key='regular_field-first_name')
        self.assertIsInstance(cell1, EntityCellRegularField)
        self.assertEqual(FakeContact,  cell1.model)
        self.assertEqual('first_name', cell1.value)

        cell2 = build(key='function_field-get_pretty_properties')
        self.assertIsInstance(cell2, EntityCellFunctionField)
        self.assertEqual(FakeContact,             cell2.model)
        self.assertEqual('get_pretty_properties', cell2.value)

        with self.assertLogs(level='WARNING'):
            self.assertIsNone(build(key='regular_field-invalid'))

        with self.assertLogs(level='WARNING'):
            self.assertIsNone(build(key='first_name'))

        with self.assertLogs(level='WARNING'):
            self.assertIsNone(build(key=EntityCellRegularField.type_id))

        with self.assertLogs(level='WARNING'):
            self.assertIsNone(build(key='not_registered-first_name'))

    def test_build_cells_from_keys(self):
        cells, errors = CELLS_MAP.build_cells_from_keys(
            model=FakeContact,
            keys=[
                f'{EntityCellRegularField.type_id}-first_name',
                f'{EntityCellFunctionField.type_id}-get_pretty_properties',
            ],
        )
        self.assertIs(errors, False)
        self.assertEqual(2, len(cells))

        cell1 = cells[0]
        self.assertIsInstance(cell1, EntityCellRegularField)
        self.assertEqual(FakeContact,  cell1.model)
        self.assertEqual('first_name', cell1.value)

        cell2 = cells[1]
        self.assertIsInstance(cell2, EntityCellFunctionField)
        self.assertEqual(FakeContact,             cell2.model)
        self.assertEqual('get_pretty_properties', cell2.value)

    def test_build_cells_from_keys__error(self):
        with self.assertLogs(level='WARNING'):
            cells, errors = CELLS_MAP.build_cells_from_keys(
                model=FakeDocument,
                keys=[
                    f'{EntityCellRegularField.type_id}-invalid',
                    f'{EntityCellFunctionField.type_id}-get_pretty_properties',
                ],
            )
        self.assertIs(errors, True)

        cell = self.get_alone_element(cells)
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(FakeDocument,            cell.model)
        self.assertEqual('get_pretty_properties', cell.value)


@override_settings(CELL_SIZE=50, HIDDEN_VALUE='Nope!')
class EntityCellRegularFieldTestCase(CremeTestCase):
    def test_main(self):
        self.assertEqual(_('Fields'), EntityCellRegularField.verbose_name)

        field_name = 'first_name'
        cell = EntityCellRegularField.build(model=FakeContact, name=field_name)
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_name,      cell.value)
        self.assertEqual(field_name,      cell.portable_value)
        self.assertEqual(_('First name'), cell.title)
        self.assertEqual('',              cell.description)
        self.assertIs(cell.is_excluded, False)
        self.assertIs(cell.is_multiline, False)

        key = f'regular_field-{field_name}'
        self.assertEqual(key, cell.key)
        self.assertEqual(key, cell.portable_key)

        dict_cell = {'type': 'regular_field', 'value': field_name}
        self.assertDictEqual(dict_cell, cell.to_dict())
        self.assertDictEqual(dict_cell, cell.to_dict(portable=False))
        self.assertDictEqual(dict_cell, cell.to_dict(portable=True))

        # Render ---
        user = self.get_root_user()
        yoko = FakeContact(user=user, first_name='Yoko', last_name='Littner')
        self.assertEqual(
            yoko.first_name,
            cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(
            yoko.first_name,
            cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN),
        )

    def test_description(self):
        self.assertEqual(
            'The contact corresponds to a user of Creme',
            EntityCellRegularField.build(model=FakeContact, name='is_user').description,
        )

    def test_date_field(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='birthday')
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        birthday = date(year=2058, month=3, day=26)
        user = self.get_root_user()
        yoko = FakeContact(
            user=user, first_name='Yoko', last_name='Littner', birthday=birthday,
        )

        with override_language('en'):
            self.assertEqual(
                date_format(birthday, 'DATE_FORMAT'),
                cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
            )
            self.assertEqual(
                birthday.strftime('%Y-%m-%d'),
                cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN),
            )

    def test_boolean_field(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='is_a_nerd')
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

        # Render ---
        user = self.get_root_user()
        yoko = FakeContact.objects.create(
            user=user, first_name='Yoko', last_name='Littner', is_a_nerd=True,
        )
        self.assertHTMLEqual(
            '<input type="checkbox" checked disabled/>' + _('Yes'),
            cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )

        yoko.is_a_nerd = False
        self.assertHTMLEqual(
            '<input type="checkbox" disabled/>' + _('No'),
            cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )

    def test_fk(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='position')
        self.assertEqual('regular_field-position', cell.key)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

        user = self.get_root_user()
        position = FakePosition.objects.create(title='Sniper')
        yoko = self.refresh(FakeContact.objects.create(
            user=user, first_name='Yoko', last_name='Littner', position=position,
        ))

        with self.assertNumQueries(1):
            EntityCellRegularField.populate_entities(
                cells=[cell], entities=[yoko], user=user,
            )

        # Render ---
        with self.assertNumQueries(0):
            self.assertHTMLEqual(
                position.title,
                cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
            )

        self.assertHTMLEqual(
            position.title,
            cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN),
        )

    def test_fk__entity(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='image')
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

        # Render (allowed) ---
        role = self.create_role(allowed_apps=['creme_core'])
        self.add_credentials(role=role, own=['VIEW'])
        user = self.create_user(role=role)

        img1 = FakeImage.objects.create(user=user, name='Mugshot')
        self.assertTrue(user.has_perm_to_view(img1))
        yoko = FakeContact(
            user=user, first_name='Yoko', last_name='Littner', image=img1,
        )
        self.assertHTMLEqual(
            f'<a href="{img1.get_absolute_url()}" target="_self">{img1.name}</a>',
            cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )

        # Render (forbidden) ---
        img2 = FakeImage.objects.create(user=self.get_root_user(), name='Mugshot #2')
        self.assertFalse(user.has_perm_to_view(img2))
        yoko.image = img2
        self.assertHTMLEqual(
            'Nope!', cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )

    def test_fk_subfield(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='position__title')
        self.assertEqual('regular_field-position__title', cell.key)

        cell = EntityCellRegularField.build(model=FakeContact, name='image__name')
        self.assertEqual('regular_field-image__name', cell.key)

    def test_fk_subfield__date(self):
        "ForeignKey subfield is a DateField."
        cell = EntityCellRegularField.build(model=FakeContact, name='image__created')
        self.assertEqual('{} - {}'.format(_('Photograph'), _('Creation date')), cell.title)

    def test_fk_subfield__fk(self):
        "ForeignKey subfield is a FK."
        cell = EntityCellRegularField.build(model=FakeDocument, name='linked_folder__category')
        self.assertEqual('regular_field-linked_folder__category', cell.key)

    def test_m2m(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='languages')
        self.assertTrue(cell.is_multiline)

        user = self.get_root_user()
        l1, l2 = Language.objects.all()[:2]
        yoko = FakeContact.objects.create(
            user=user, first_name='Yoko', last_name='Littner',
        )
        yoko.languages.set([l1, l2])

        yoko = self.refresh(yoko)

        # Render (no prefetch) ---
        expected_txt = f'{l1.name}/{l2.name}'
        expected_html = f'<ul class="limited-list"><li>{l1.name}</li><li>{l2.name}</li></ul>'

        with self.assertNumQueries(1):
            self.assertEqual(
                expected_txt,
                cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN),
            )

        with self.assertNumQueries(0):  # Use cache
            self.assertEqual(
                expected_html,
                cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
            )

        # Render (with prefetch) ---
        with self.assertNumQueries(1):
            EntityCellRegularField.populate_entities(
                cells=[cell], entities=[yoko], user=user,
            )

        with self.assertNumQueries(0):
            self.assertEqual(
                expected_txt,
                cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN),
            )

        self.assertEqual(
            expected_html,
            cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )

    def test_m2m__entity(self):
        cell = EntityCellRegularField.build(model=FakeEmailCampaign, name='mailing_lists')
        self.assertTrue(cell.is_multiline)

        # Render ---
        user = self.get_root_user()
        create_ml = partial(FakeMailingList.objects.create, user=user)
        ml1 = create_ml(name='ML #1')
        ml2 = create_ml(name='ML #2', is_deleted=True)
        ml3 = create_ml(name='ML #3')

        camp = FakeEmailCampaign.objects.create(user=user, name='Summer discount')
        camp.mailing_lists.set([ml1, ml2, ml3])

        with self.assertNumQueries(1):
            self.assertHTMLEqual(
                f'<ul class="limited-list">'
                f' <li><a href="{ml1.get_absolute_url()}" target="_blank">{ml1.name}</li>'
                f' <li><a href="{ml3.get_absolute_url()}" target="_blank">{ml3.name}</li>'
                # f' <li><a href="{ml2.get_absolute_url()}" target="_blank" class="is_deleted">'
                # f' {ml2.name}'
                # f' </li>'
                f'</ul>',
                cell.render(entity=camp, user=user, tag=ViewTag.HTML_DETAIL),
            )

        with self.assertNumQueries(0):  # Use cache
            self.assertHTMLEqual(
                f'{ml1.name}/{ml3.name}',
                cell.render(entity=camp, user=user, tag=ViewTag.TEXT_PLAIN),
            )

    def test_m2m_subfield(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='languages__name')
        self.assertTrue(cell.is_multiline)

        # Render ---
        user = self.get_root_user()
        l1, l2 = Language.objects.all()[:2]
        yoko = FakeContact.objects.create(
            user=user, first_name='Yoko', last_name='Littner',
        )
        yoko.languages.set([l1, l2])

        self.assertEqual(
            f'{l1.name}/{l2.name}',
            cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN),
        )
        self.assertEqual(
            f'<ul class="limited-list"><li>{l1.name}</li><li>{l2.name}</li></ul>',
            cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )

    def test_hidden_field(self):
        hidden = 'first_name'

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (hidden,  {FieldsConfig.HIDDEN: True}),
            ],
        )

        cell = EntityCellRegularField.build(model=FakeContact, name=hidden)
        self.assertEqual(_('{} [hidden]').format(_('First name')), cell.title)
        self.assertIs(cell.is_excluded, True)

    def test_not_viewable_field(self):
        cell1 = EntityCellRegularField.build(model=FakeTodo, name='entity')
        self.assertTrue(cell1.is_excluded)
        self.assertEqual(_('{} [hidden]').format('entity'), cell1.title)

        cell2 = EntityCellRegularField.build(model=FakeTodo, name='entity__user')
        self.assertTrue(cell2.is_excluded)

    def test_errors(self):
        build = partial(EntityCellRegularField.build, model=FakeContact)

        with self.assertLogs(level='WARNING'):
            self.assertIsNone(build(name='unknown_field'))

        with self.assertLogs(level='WARNING'):
            self.assertIsNone(build(name='user__unknownfield'))

    def test_populate_entities(self):
        user = self.get_root_user()

        pos = FakePosition.objects.create(title='Pilot')
        create_contact = partial(FakeContact.objects.create, user=user, position_id=pos.id)
        contacts = [
            create_contact(first_name='Nagate',  last_name='Tanikaze'),
            create_contact(first_name='Shizuka', last_name='Hoshijiro'),
        ]

        build = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [build(name='last_name'), build(name='first_name')]

        with self.assertNumQueries(0):
            EntityCellRegularField.populate_entities(
                cells=cells, entities=contacts, user=user,
            )

        with self.assertNumQueries(1):
            contacts[0].position  # NOQA

    def test_populate_entities__fk(self):
        user = self.get_root_user()

        pos = FakePosition.objects.all()[0]
        civ = FakeCivility.objects.all()[0]
        create_contact = partial(
            FakeContact.objects.create, user=user, position=pos, civility=civ,
        )
        contact1 = create_contact(first_name='Nagate', last_name='Tanikaze')
        contact2 = create_contact(first_name='Shizuka', last_name='Hoshijiro')
        # NB: we refresh because the __str__() method retrieves the civility
        contacts = [self.refresh(contact1), self.refresh(contact2)]

        build = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [
            build(name='last_name'), build(name='first_name'),
            build(name='position'),
            build(name='civility__title'),
        ]

        with self.assertNumQueries(2):
            EntityCellRegularField.populate_entities(
                cells=cells, entities=contacts, user=user,
            )

        with self.assertNumQueries(0):
            contacts[0].position  # NOQA
            contacts[1].position  # NOQA
            contacts[0].civility  # NOQA
            contacts[1].civility  # NOQA


@override_settings(CELL_SIZE=50)
class EntityCellCustomFieldTestCase(CremeTestCase):
    def test_int(self):
        self.assertEqual(_('Custom fields'), EntityCellCustomField.verbose_name)

        name = 'Size (cm)'
        cfield = CustomField.objects.create(
            name=name, field_type=CustomField.INT, content_type=FakeContact,
        )

        cell1 = EntityCellCustomField(cfield)
        self.assertIsInstance(cell1, EntityCellCustomField)

        self.assertEqual(str(cfield.id),   cell1.value)
        self.assertEqual(str(cfield.uuid), cell1.portable_value)

        self.assertEqual(name, cell1.title)
        self.assertEqual('',   cell1.description)
        self.assertEqual(f'custom_field-{cfield.id}',   cell1.key)
        self.assertEqual(f'custom_field-{cfield.uuid}', cell1.portable_key)

        self.assertIs(cell1.is_multiline, False)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,         cell1.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell1.header_listview_css_class)

        dict_cell_id = {'type': 'custom_field', 'value': str(cfield.id)}
        self.assertDictEqual(dict_cell_id, cell1.to_dict())
        self.assertDictEqual(dict_cell_id, cell1.to_dict(portable=False))
        self.assertDictEqual(
            {'type': 'custom_field', 'value': str(cfield.uuid)},
            cell1.to_dict(portable=True),
        )

        # --
        cell2 = EntityCellCustomField.build(FakeContact, str(cfield.id))
        self.assertIsInstance(cell2, EntityCellCustomField)
        self.assertEqual(str(cfield.id), cell2.value)

        with self.assertLogs(level='WARNING'):
            self.assertIsNone(EntityCellCustomField.build(FakeContact, '1000'))
        with self.assertLogs(level='WARNING'):
            self.assertIsNone(EntityCellCustomField.build(FakeContact, 'notanint'))

        # Render ---
        user = self.get_root_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        self.assertEqual('', cell2.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL))

        cfield.value_class.objects.create(entity=yoko, custom_field=cfield, value=152)
        yoko = self.refresh(yoko)  # Reset caches
        self.assertEqual('152', cell2.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL))
        self.assertEqual('152', cell2.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN))

        # Build from portable value ---
        cell3 = EntityCellCustomField.build(FakeContact, str(cfield.uuid))
        self.assertIsInstance(cell3, EntityCellCustomField)
        self.assertEqual(cfield, cell3.custom_field)

        # # Build from int (DEPRECATED) ---
        # with self.assertWarnsMessage(
        #     expected_warning=DeprecationWarning,
        #     expected_message=(
        #         'EntityCellCustomField.build() with integer value is deprecated; '
        #         'pass a string (ID ou UUID) instead.'
        #     )
        # ):
        #     cell4 = EntityCellCustomField.build(FakeContact, cfield.id)
        #
        # self.assertIsInstance(cell4, EntityCellCustomField)
        # self.assertEqual(str(cfield.id), cell4.value)

    def test_decimal(self):
        description = 'I am a very useful description'
        cfield = CustomField.objects.create(
            name='Weight',
            field_type=CustomField.FLOAT,
            content_type=FakeContact,
            description=description,
        )

        cell = EntityCellCustomField(cfield)
        self.assertEqual(description, cell.description)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,         cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.get_root_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        value = Decimal('1.52')
        value_str = number_format(value)
        cfield.value_class.objects.create(entity=yoko, custom_field=cfield, value=value)
        self.assertEqual(value_str, cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL))
        self.assertEqual(value_str, cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN))

    def test_datetime(self):
        cfield = CustomField.objects.create(
            name='Day & hour',
            field_type=CustomField.DATETIME,
            content_type=FakeContact,
        )

        cell = EntityCellCustomField(cfield)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.get_root_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        dt = self.create_datetime(year=2058, month=3, day=26, hour=12)
        cfield.value_class.objects.create(entity=yoko, custom_field=cfield, value=dt)

        local_dt = localtime(dt)

        with override_language('en'):
            self.assertHTMLEqual(
                '<span class="datetime-field" title="{seconds}">{dt}</span>'.format(
                    seconds=_('Seconds: {}').format(local_dt.second),
                    dt=date_format(local_dt, 'DATETIME_FORMAT'),
                ),
                cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
            )
            self.assertEqual(
                local_dt.strftime('%Y-%m-%d %H:%M:%S'),
                cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN),
            )

    def test_date(self):
        cfield = CustomField.objects.create(
            name='Day', field_type=CustomField.DATE, content_type=FakeContact,
        )

        cell = EntityCellCustomField(cfield)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.get_root_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        date_obj = date(year=2058, month=3, day=26)
        cfield.value_class.objects.create(
            entity=yoko, custom_field=cfield, value=date_obj,
        )

        with override_language('en'):
            self.assertEqual(
                date_format(date_obj, 'DATE_FORMAT'),
                cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
            )
            self.assertEqual(
                date_obj.strftime('%Y-%m-%d'),
                cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN),
            )

    def test_bool(self):
        cfield = CustomField.objects.create(
            name='Is fun?', field_type=CustomField.BOOL, content_type=FakeContact,
        )

        cell = EntityCellCustomField(cfield)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.get_root_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        cfield.value_class.objects.create(entity=yoko, custom_field=cfield, value=True)
        self.assertHTMLEqual(
            f'<input type="checkbox" checked disabled/>{_("Yes")}',
            cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(_('Yes'), cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN))

    def test_str(self):
        cfield = CustomField.objects.create(
            name='Nickname',
            field_type=CustomField.STR,
            content_type=FakeContact,
        )

        cell = EntityCellCustomField(cfield)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.get_root_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')

        value = '<i>Sniper</i>'
        cfield.value_class.objects.create(entity=yoko, custom_field=cfield, value=value)
        self.assertEqual(
            '&lt;i&gt;Sniper&lt;/i&gt;',
            cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(value, cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN))

    def test_text(self):
        cfield = CustomField.objects.create(
            name='Plot', field_type=CustomField.TEXT, content_type=FakeContact,
        )
        cell = EntityCellCustomField(cfield)

        # Render ---
        user = self.get_root_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')

        value = (
            'Yoko is a young woman from <i>Littner</i>, a village neighboring Giha.\n'
            'She helps introduce Simon and Kamina to the surface world.'
        )
        cfield.value_class.objects.create(entity=yoko, custom_field=cfield, value=value)
        self.assertHTMLEqual(
            '<p>'
            'Yoko is a young woman from &lt;i&gt;Littner&lt;/i&gt;, a village neighboring Giha.'
            '<br>'
            'She helps introduce Simon and Kamina to the surface world.'
            '</p>',
            cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(value, cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN))

    def test_url(self):
        cfield = CustomField.objects.create(
            name='Village URL', field_type=CustomField.URL, content_type=FakeContact,
        )
        cell = EntityCellCustomField(cfield)

        # Render ---
        user = self.get_root_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')

        value = 'www.littner.org'
        cfield.value_class.objects.create(
            entity=yoko, custom_field=cfield, value=value,
        )
        self.assertHTMLEqual(
            f'<a href="//{value}" target="_blank">{value}</a>',
            cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(value, cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN))

    def test_enum(self):
        cfield = CustomField.objects.create(
            name='Eva', field_type=CustomField.ENUM, content_type=FakeContact,
        )

        create_enumvalue = partial(
            CustomFieldEnumValue.objects.create, custom_field=cfield,
        )
        enum_value1 = create_enumvalue(value='Eva-00<script>')
        create_enumvalue(value='Eva-01')

        cell = EntityCellCustomField(cfield)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.get_root_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        self.assertEqual('', cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL))
        self.assertEqual('', cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN))

        cfield.value_class.objects.create(
            entity=yoko, custom_field=cfield, value=enum_value1,
        )
        yoko = self.refresh(yoko)  # Avoid cache
        self.assertEqual(
            'Eva-00&lt;script&gt;',
            cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(
            enum_value1.value,
            cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN),
        )

    def test_mulitenum(self):
        cfield = CustomField.objects.create(
            name='Eva',
            field_type=CustomField.MULTI_ENUM,
            content_type=FakeContact,
        )

        create_enumvalue = partial(
            CustomFieldEnumValue.objects.create,
            custom_field=cfield,
        )
        enum_value1 = create_enumvalue(value='Eva-00')
        create_enumvalue(value='Eva-01')
        enum_value3 = create_enumvalue(value='Eva-02<script>')

        cell = EntityCellCustomField(cfield)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.get_root_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        self.assertEqual('', cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL))
        self.assertEqual('', cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN))

        cf_value = cfield.value_class(entity=yoko, custom_field=cfield)
        cf_value.set_value_n_save([enum_value1.id, enum_value3.id])
        yoko = self.refresh(yoko)  # Avoid cache
        self.assertHTMLEqual(
            f'<ul class="limited-list">'
            f' <li>{enum_value1.value}</li>'
            f' <li>Eva-02&lt;script&gt;</li>'
            f'</ul>',
            cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
        )
        self.assertEqual(
            f'{enum_value1.value} / {enum_value3.value}',
            cell.render(entity=yoko, user=user, tag=ViewTag.TEXT_PLAIN),
        )

        with self.settings(CELL_SIZE=1):
            message = ngettext(
                '{count} more element', '{count} more elements', 1,
            ).format(count=1)
            self.assertHTMLEqual(
                f'<ul class="limited-list">'
                f' <li>{enum_value1.value}</li>'
                f' <li><span class="more-elements">{message}</span></li>'
                f'</ul>',
                cell.render(entity=yoko, user=user, tag=ViewTag.HTML_DETAIL),
            )

    def test_deleted(self):
        name = 'Size (cm)'
        cfield = CustomField.objects.create(
            name=name,
            field_type=CustomField.INT,
            content_type=FakeContact,
            is_deleted=True,
        )

        cell = EntityCellCustomField(cfield)
        self.assertEqual(_('{} [deleted]').format(name), cell.title)
        self.assertIs(cell.is_hidden, False)
        self.assertIs(cell.is_excluded, True)


@override_settings(CELL_SIZE=50)
class EntityCellRelationTestCase(CremeTestCase):
    def test_several_related_entities(self):
        self.assertEqual(_('Relationships'), EntityCellRelation.verbose_name)

        loved = RelationType.objects.builder(
            id='test-object_loved', predicate='Is loved by',
        ).symmetric(
            id='test-subject_loved', predicate='Is loving',
        ).get_or_create()[0]
        cell = EntityCellRelation(model=FakeContact, rtype=loved)
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(FakeContact,     cell.model)
        self.assertEqual(str(loved.id),   cell.value)
        self.assertEqual(loved.predicate, cell.title)
        self.assertEqual(f'relation-{loved.id}', cell.key)
        self.assertIs(cell.is_multiline, True)
        self.assertFalse(cell.is_hidden)
        self.assertFalse(cell.is_excluded)
        self.assertEqual(loved, cell.relation_type)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        dict_cell = {'type': 'relation', 'value': loved.id}
        self.assertDictEqual(dict_cell, cell.to_dict())
        self.assertDictEqual(dict_cell, cell.to_dict(portable=False))
        self.assertDictEqual(dict_cell, cell.to_dict(portable=True))

        # Render ---
        user = self.get_root_user()
        create_contact = partial(FakeContact.objects.create, user=user)
        contacts = [
            create_contact(first_name='Nagate',  last_name='Tanikaze'),
            create_contact(first_name='Shizuka', last_name='Hoshijiro'),
            create_contact(first_name='Izana',   last_name='Shinatose'),
        ]

        create_rel = partial(
            Relation.objects.create,
            user=user, subject_entity=contacts[0], type=loved,
        )
        create_rel(object_entity=contacts[1])
        create_rel(object_entity=contacts[2])

        self.assertEqual(
            f'{contacts[2]}/{contacts[1]}',
            cell.render(entity=contacts[0], user=user, tag=ViewTag.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            f'<ul class="limited-list">'
            f' <li>'
            f'  <a href="{contacts[2].get_absolute_url()}" target="_self">{contacts[2]}</a>'
            f' </li>'
            f' <li>'
            f'  <a href="{contacts[1].get_absolute_url()}" target="_self">{contacts[1]}</a>'
            f' </li>'
            f'</ul>',
            cell.render(entity=contacts[0], user=user, tag=ViewTag.HTML_DETAIL),
        )
        self.assertHTMLEqual(
            f'<ul class="limited-list">'
            f' <li>'
            f'  <a href="{contacts[2].get_absolute_url()}" target="_blank">{contacts[2]}</a>'
            f' </li>'
            f' <li>'
            f'  <a href="{contacts[1].get_absolute_url()}" target="_blank">{contacts[1]}</a>'
            f' </li>'
            f'</ul>',
            cell.render(entity=contacts[0], user=user, tag=ViewTag.HTML_FORM),
        )

        # Limited render (singular) ---
        with override_settings(CELL_SIZE=1):
            limit_message1 = ngettext(
                '{count} more element', '{count} more elements', 1,
            ).format(count=1)
            self.assertHTMLEqual(
                f'<ul class="limited-list">'
                f' <li>'
                f'  <a href="{contacts[2].get_absolute_url()}" target="_self">{contacts[2]}</a>'
                f' </li>'
                f' <li>'
                f'  <span class="more-elements">{limit_message1}</span>'
                f' </li>'
                f'</ul>',
                cell.render(entity=contacts[0], user=user, tag=ViewTag.HTML_DETAIL),
            )

        # Limited render (plural) ---
        contact3 = create_contact(first_name='En', last_name='Honoka')
        create_rel(object_entity=contact3)

        with override_settings(CELL_SIZE=1):
            limit_message2 = ngettext(
                '{count} more element', '{count} more elements', 2,
            ).format(count=2)
            self.assertHTMLEqual(
                f'<ul class="limited-list">'
                f' <li>'
                f'  <a href="{contact3.get_absolute_url()}" target="_self">{contact3}</a>'
                f' </li>'
                f' <li>'
                f'  <span class="more-elements">{limit_message2}</span>'
                f' </li>'
                f'</ul>',
                cell.render(entity=self.refresh(contacts[0]), user=user, tag=ViewTag.HTML_DETAIL),
            )

    def test_one_related_entity(self):
        loved = RelationType.objects.builder(
            id='test-object_loved', predicate='Is loved by',
        ).symmetric(id='test-subject_loved', predicate='Is loving').get_or_create()[0]
        cell = EntityCellRelation(model=FakeContact, rtype=loved)

        user = self.get_root_user()
        create_contact = partial(FakeContact.objects.create, user=user)
        subject = create_contact(first_name='Nagate',  last_name='Tanikaze')
        obj_entity = create_contact(first_name='Shizuka', last_name='Hoshijiro')

        Relation.objects.create(
            user=user, subject_entity=subject, type=loved, object_entity=obj_entity,
        )

        self.assertEqual(
            str(obj_entity),
            cell.render(entity=subject, user=user, tag=ViewTag.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            f'<a href="{obj_entity.get_absolute_url()}" target="_self">{obj_entity}</a>',
            cell.render(entity=subject, user=user, tag=ViewTag.HTML_DETAIL),
        )
        self.assertHTMLEqual(
            f'<a href="{obj_entity.get_absolute_url()}" target="_blank">{obj_entity}</a>',
            cell.render(entity=subject, user=user, tag=ViewTag.HTML_FORM),
        )

    def test_disabled_type(self):
        self.assertEqual(_('Relationships'), EntityCellRelation.verbose_name)

        hated = RelationType.objects.builder(
            id='test-object_hated', predicate='Is hated by',
            enabled=False,
        ).symmetric(id='test-subject_hated', predicate='Is hating').get_or_create()[0]

        cell = EntityCellRelation(model=FakeContact, rtype=hated)
        self.assertEqual(hated, cell.relation_type)
        self.assertEqual(FakeContact, cell.model)
        self.assertEqual(_('{} [disabled]').format(hated.predicate), cell.title)
        self.assertFalse(cell.is_hidden)
        self.assertTrue(cell.is_excluded)

    def test_populate_entities(self):
        user = self.get_root_user()

        loves = RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving',
        ).symmetric(id='test-object_love', predicate='Is loved by').get_or_create()[0]
        hates = RelationType.objects.builder(
            id='test-subject_hate', predicate='Is hating',
        ).symmetric(id='test-object_hate', predicate='Is hated by').get_or_create()[0]

        cells = [
            EntityCellRelation(model=FakeContact, rtype=loves),
            EntityCellRelation(model=FakeContact, rtype=hates),
        ]

        create_contact = partial(FakeContact.objects.create, user=user)
        nagate  = create_contact(first_name='Nagate',  last_name='Tanikaze')
        shizuka = create_contact(first_name='Shizuka', last_name='Hoshijiro')
        izana   = create_contact(first_name='Izana',   last_name='Shinatose')
        norio   = create_contact(first_name='Norio',   last_name='Kunato')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=nagate,  type=loves, object_entity=izana)
        create_rel(subject_entity=nagate,  type=hates, object_entity=norio)
        create_rel(subject_entity=shizuka, type=loves, object_entity=norio)

        # NB: sometimes a query to get this CT is performed when the Relations
        # are retrieved. So we force the cache to be filled has he should be
        ContentType.objects.get_for_model(CremeEntity)

        with self.assertNumQueries(2):
            EntityCellRelation.populate_entities(
                cells=cells, entities=[nagate, shizuka], user=user,
            )

        with self.assertNumQueries(0):
            r1 = nagate.get_relations(loves.id,  real_obj_entities=True)
            r2 = nagate.get_relations(hates.id,  real_obj_entities=True)
            r3 = shizuka.get_relations(loves.id, real_obj_entities=True)
            r4 = shizuka.get_relations(hates.id, real_obj_entities=True)

        with self.assertNumQueries(0):
            objs1 = [r.object_entity.get_real_entity() for r in r1]
            objs2 = [r.object_entity.get_real_entity() for r in r2]
            objs3 = [r.object_entity.get_real_entity() for r in r3]
            objs4 = [r.object_entity.get_real_entity() for r in r4]

        self.assertListEqual([izana], objs1)
        self.assertListEqual([norio], objs2)
        self.assertListEqual([norio], objs3)
        self.assertListEqual([],      objs4)

        with self.assertNumQueries(0):
            r1[0].real_object  # NOQA


@override_settings(CELL_SIZE=50)
class EntityCellFunctionFieldTestCase(CremeTestCase):
    def test_main(self):
        self.assertEqual(_('Computed fields'), EntityCellFunctionField.verbose_name)

        name = 'get_pretty_properties'
        funfield = function_field_registry.get(FakeContact, name)
        self.assertIsNotNone(funfield)

        cell1 = EntityCellFunctionField(model=FakeContact, func_field=funfield)
        self.assertIsInstance(cell1, EntityCellFunctionField)
        self.assertEqual(name,                              cell1.value)
        self.assertEqual(str(funfield.verbose_name),        cell1.title)
        self.assertEqual(f'function_field-{funfield.name}', cell1.key)
        self.assertIs(cell1.is_hidden,    False)
        self.assertIs(cell1.is_multiline, True)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell1.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell1.header_listview_css_class)

        dict_cell = {'type': 'function_field', 'value': funfield.name}
        self.assertDictEqual(dict_cell, cell1.to_dict())
        self.assertDictEqual(dict_cell, cell1.to_dict(portable=False))
        self.assertDictEqual(dict_cell, cell1.to_dict(portable=True))

        # ---
        cell2 = EntityCellFunctionField.build(FakeContact, name=name)
        self.assertIsInstance(cell2, EntityCellFunctionField)
        self.assertEqual(name, cell2.value)

        with self.assertLogs(level='WARNING'):
            self.assertIsNone(EntityCellFunctionField.build(FakeContact, name='invalid'))

        # Render ---
        user = self.get_root_user()
        contact = FakeContact.objects.create(
            user=user, first_name='Nagate', last_name='Tanikaze',
        )

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is a pilot')
        ptype2 = create_ptype(text='Is a clone')

        create_prop = partial(CremeProperty.objects.create, creme_entity=contact)
        create_prop(type=ptype1)
        create_prop(type=ptype2)

        self.assertEqual(
            f'{ptype2.text}/{ptype1.text}',
            cell2.render(entity=contact, user=user, tag=ViewTag.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            f'<ul class="limited-list">'
            f' <li><a href="{ptype2.get_absolute_url()}">{ptype2.text}</li>'
            f' <li><a href="{ptype1.get_absolute_url()}">{ptype1.text}</li>'
            f'</ul>',
            cell2.render(entity=contact, user=user, tag=ViewTag.HTML_DETAIL),
        )

    def test_other(self):
        class PhoneFunctionField(FunctionField):
            name         = 'phone_or_mobile'
            verbose_name = 'Phone or mobile'

            def __call__(self, entity, user):
                return FunctionFieldResult(entity.phone or entity.mobile)

        funfield = PhoneFunctionField()
        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)
        self.assertEqual(funfield.name,         cell.value)
        self.assertEqual(funfield.verbose_name, cell.title)
        self.assertFalse(cell.is_multiline)


class EntityCellTestCase(CremeTestCase):
    def test_eq(self):
        cell1 = EntityCellRegularField.build(model=FakeDocument, name='title')

        # Other is not an EntityCell
        self.assertNotEqual(None,       cell1)
        self.assertNotEqual('whatever', cell1)

        self.assertEqual(
            EntityCellRegularField.build(model=FakeDocument, name='title'),
            cell1
        )
        # Value is different
        self.assertNotEqual(
            EntityCellRegularField.build(model=FakeDocument, name='linked_folder'),
            cell1,
        )
        # Model is different
        self.assertNotEqual(
            EntityCellRegularField.build(model=FakeFolder, name='title'),
            cell1,
        )

        # Class is different
        class TestCell(EntityCell):
            type_id = 'test'

            def __init__(self, model, value):
                super().__init__(model=model, value=value)

        self.assertNotEqual(
            TestCell(model=FakeDocument, value='title'),
            cell1,
        )

    def test_mixed_populate_entities(self):
        user = self.get_root_user()

        pos = FakePosition.objects.all()[0]
        create_contact = partial(FakeContact.objects.create, user=user)
        contacts = [
            create_contact(first_name='Nagate',  last_name='Tanikaze', position=pos),
            create_contact(first_name='Shizuka', last_name='Hoshijiro'),
            create_contact(first_name='Izana',   last_name='Shinatose'),
        ]

        loves = RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving',
        ).symmetric(id='test-object_love', predicate='Is loved by').get_or_create()[0]
        Relation.objects.create(
            user=user, subject_entity=contacts[0], type=loves, object_entity=contacts[2],
        )

        build_rfield = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [
            build_rfield(name='last_name'),
            build_rfield(name='position'),
            EntityCellRelation(model=FakeContact, rtype=loves),
        ]

        # NB: sometimes a query to get this CT is performed when the Relations
        # are retrieved. So we force the cache to be filled has he should be
        ContentType.objects.get_for_model(CremeEntity)

        # Drop caches
        contacts = [self.refresh(c) for c in contacts]

        with self.assertNumQueries(3):
            EntityCell.mixed_populate_entities(cells, contacts, user)

        with self.assertNumQueries(0):
            contacts[0].position  # NOQA

        with self.assertNumQueries(0):
            contacts[0].get_relations(loves.id,  real_obj_entities=True)
