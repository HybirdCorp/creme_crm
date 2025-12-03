from decimal import Decimal
from functools import partial
from json import dumps as json_dump

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import number_format

from creme.creme_core.bricks import (
    ButtonsBrick,
    CustomFieldsBrick,
    HistoryBrick,
    PinnedEntitiesBrick,
    PropertiesBrick,
    RecentEntitiesBrick,
    RelationsBrick,
    StatisticsBrick,
)
from creme.creme_core.gui import button_menu
from creme.creme_core.gui.statistics import statistic_registry
from creme.creme_core.models import (
    BrickDetailviewLocation,
    ButtonMenuItem,
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CustomField,
    FakeAddress,
    FakeContact,
    FakeOrganisation,
    HistoryLine,
    LastViewedEntity,
    PinnedEntity,
    Relation,
    RelationBrickItem,
    RelationType,
)

from .base import CremeTestCase
from .views.base import BrickTestCaseMixin


class _TestButton(button_menu.Button):
    action_id = 'creme_core-tests-??'
    template_name = 'creme_core/tests/unit/buttons/test_buttons_brick.html'

    def get_context(self, *, entity, request):
        context = super().get_context(entity=entity, request=request)
        context['action_id'] = self.action_id

        return context


class TestButton1(_TestButton):
    id = _TestButton.generate_id('creme_core', 'test_brick_buttons1')
    action_id = 'creme_core-tests-dosomethingawesome1'


class TestButton2(_TestButton):
    id = _TestButton.generate_id('creme_core', 'test_brick_buttons2')
    action_id = 'creme_core-tests-dosomethingawesome2'


class TestButton3(_TestButton):
    id = _TestButton.generate_id('creme_core', 'test_brick_buttons3')
    action_id = 'creme_core-tests-dosomethingawesome3'


class TestButton4(_TestButton):
    id = _TestButton.generate_id('creme_core', 'test_brick_buttons4')
    action_id = 'creme_core-tests-dosomethingawesome4'


class TestButton5(_TestButton):
    id = _TestButton.generate_id('creme_core', 'test_brick_buttons5')
    action_id = 'creme_core-tests-dosomethingawesome5'


class BricksTestCase(BrickTestCaseMixin, CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original_button_registry = ButtonsBrick.button_registry

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        ButtonsBrick.button_registry = cls.original_button_registry

    def setUp(self):
        super().setUp()
        ButtonsBrick.button_registry = button_menu.ButtonRegistry().register(
            TestButton1, TestButton2, TestButton3, TestButton4, TestButton5,
        )

    @staticmethod
    def _get_button_action_ids(node):
        return [
            node.attrib.get('data-action')
            for li_node in node.findall('.//li')
            for node in li_node.findall('.//a')
            if 'menu_button' in node.attrib.get('class').split()
        ]

    def _assertMenuButtons(self, user, entity, buttons):
        brick = ButtonsBrick()
        render = brick.detailview_display(
            context=self.build_context(user=user, instance=entity)
        )
        brick_node = self.get_brick_node(self.get_html_tree(render), brick=brick)
        self.assertListEqual(
            [button.action_id for button in buttons],
            self._get_button_action_ids(brick_node),
        )

    def test_buttons_brick(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_button = ButtonMenuItem.objects.create
        create_button(button=TestButton1, order=1)
        create_button(button=TestButton2, order=102, content_type=FakeOrganisation)
        create_button(button=TestButton3, order=101, content_type=FakeOrganisation)
        create_button(button=TestButton4, order=102, content_type=FakeContact)

        self._assertMenuButtons(
            user=user, entity=orga, buttons=[TestButton1, TestButton3, TestButton2],
        )

    def test_buttons_brick__duplicate(self):
        "A button present in default config & ContentType's one => not duplicated."
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_button = ButtonMenuItem.objects.create
        create_button(button=TestButton1, order=1)
        create_button(button=TestButton2, order=101, content_type=type(orga))
        create_button(button=TestButton1, order=102, content_type=type(orga))

        self._assertMenuButtons(
            user=user, entity=orga, buttons=[TestButton1, TestButton2],
        )

    def test_buttons_brick__mandatory(self):
        class MandatoryButton1(_TestButton):
            id = _TestButton.generate_id('creme_core', 'test_mandatory_button_1')
            action_id = 'creme_core-tests_mandatory01'

        class MandatoryButton2(_TestButton):
            id = _TestButton.generate_id('creme_core', 'test_mandatory_button_2')
            action_id = 'creme_core-tests_mandatory02'

            def get_ctypes(this):
                return [FakeOrganisation, FakeContact]

        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')

        ButtonMenuItem.objects.create(button=TestButton1, order=1)

        ButtonsBrick.button_registry.register_mandatory(
            button_class=MandatoryButton1, priority=8,
        ).register_mandatory(
            button_class=MandatoryButton2, priority=1,
        )
        self._assertMenuButtons(
            user=user, entity=orga,
            buttons=[MandatoryButton2, MandatoryButton1, TestButton1],
        )

    def test_buttons_brick__superuser_config__empty(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_button = ButtonMenuItem.objects.create
        create_button(button=TestButton1, order=1)
        create_button(button=TestButton2, order=101, content_type=type(orga))

        ButtonMenuItem.objects.create(
            content_type=None, button_id='', order=1, superuser=True,
        )
        self._assertMenuButtons(user=user, entity=orga, buttons=[])

    def test_buttons_brick__superuser_config__default(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_button = ButtonMenuItem.objects.create
        create_button(button=TestButton1, order=1)
        create_button(button=TestButton2, order=102, content_type=type(orga))
        create_button(button=TestButton3, order=101, superuser=True)
        create_button(button=TestButton4, order=102, superuser=True)

        self._assertMenuButtons(user=user, entity=orga, buttons=[TestButton3, TestButton4])

    def test_buttons_brick__superuser_config__ctype(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_button = ButtonMenuItem.objects.create
        create_button(button=TestButton1, order=1)
        create_button(button=TestButton2, order=101, content_type=type(orga))
        create_button(button=TestButton3, order=1,   superuser=True)
        create_button(button=TestButton4, order=101, superuser=True, content_type=type(orga))
        create_button(button=TestButton5, order=101, superuser=True, content_type=FakeContact)

        self._assertMenuButtons(user=user, entity=orga, buttons=[TestButton3, TestButton4])

    def test_buttons_brick__role_config__empty(self):
        user = self.create_user(role=self.create_role())
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_bmi = ButtonMenuItem.objects.create
        create_bmi(button=TestButton1, order=1)
        create_bmi(button=TestButton2, order=102, content_type=type(orga))
        create_bmi(button_id='',       order=1,   content_type=None, role=user.role)
        self._assertMenuButtons(user=user, entity=orga, buttons=[])

    def test_buttons_brick__role_config__default(self):
        user = self.create_user(role=self.create_role())
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_bmi = ButtonMenuItem.objects.create
        create_bmi(button=TestButton1, order=1)
        create_bmi(button=TestButton2, order=102, content_type=(type(orga)))
        create_bmi(button=TestButton3, order=101, role=user.role)
        create_bmi(button=TestButton4, order=102, role=user.role)
        self._assertMenuButtons(
            user=user, entity=orga, buttons=[TestButton3, TestButton4],
        )

    def test_buttons_brick__role_config__ctype(self):
        user = self.create_user(role=self.create_role())
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_bmi = ButtonMenuItem.objects.create
        create_bmi(button=TestButton1, order=1)
        create_bmi(button=TestButton2, order=101, content_type=FakeOrganisation)
        create_bmi(button=TestButton3, order=1, role=user.role)
        create_bmi(button=TestButton4, order=101, role=user.role, content_type=FakeOrganisation)
        create_bmi(button=TestButton5, order=101, role=user.role, content_type=FakeContact)
        create_bmi(button=TestButton5, order=101, superuser=True, content_type=FakeOrganisation)
        self._assertMenuButtons(user=user, entity=orga, buttons=[TestButton3, TestButton4])

    def test_properties_brick(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        atom  = create_contact(first_name='Atom', last_name='Tenma')
        tenma = create_contact(first_name='Dr',   last_name='Tenma')

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is a robot')
        ptype2 = create_ptype(text='Is a human')
        ptype3 = create_ptype(text='Is cool')

        create_prop = CremeProperty.objects.safe_create
        create_prop(creme_entity=atom,  type=ptype1)
        create_prop(creme_entity=atom,  type=ptype3)
        create_prop(creme_entity=tenma, type=ptype2)

        PropertiesBrick.page_size = max(4, settings.BLOCK_SIZE)

        ContentType.objects.get_for_model(CremeProperty)  # Fill cache

        context = self.build_context(user=user, instance=atom)
        # Queries:
        #   - COUNT CremeProperties
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        #   - CremeProperties
        with self.assertNumQueries(4):
            render = PropertiesBrick().detailview_display(context)

        brick_node1 = self.get_brick_node(self.get_html_tree(render), brick=PropertiesBrick)
        self.assertInstanceLink(brick_node1, ptype1)
        self.assertInstanceLink(brick_node1, ptype3)
        self.assertNoInstanceLink(brick_node1, ptype2)

        # From view ---
        response = self.assertGET200(atom.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/bricks/properties.html')

        brick_node2 = self.get_brick_node(
            self.get_html_tree(response.content), brick=PropertiesBrick,
        )
        self.assertInstanceLink(brick_node2, ptype1)
        self.assertInstanceLink(brick_node2, ptype3)
        self.assertNoInstanceLink(brick_node2, ptype2)

    def test_relations_brick(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        atom  = create_contact(first_name='Atom', last_name='Tenma')
        tenma = create_contact(first_name='Dr',   last_name='Tenma')
        uran  = create_contact(first_name='Uran', last_name='Ochanomizu')

        rtype1 = RelationType.objects.builder(
            id='test-subject_son', predicate='is the son of',
        ).symmetric(id='test-object_father', predicate='is the father of').get_or_create()[0]
        Relation.objects.create(
            subject_entity=atom, type=rtype1, object_entity=tenma, user=user,
        )

        rtype2 = RelationType.objects.builder(
            id='test-subject_brother', predicate='is the brother of',
        ).symmetric(id='test-object_sister', predicate='is the sister of').get_or_create()[0]
        Relation.objects.create(
            subject_entity=atom, type=rtype2, object_entity=uran, user=user,
        )

        RelationsBrick.page_size = max(4, settings.BLOCK_SIZE)

        ContentType.objects.get_for_models(Relation, CremeEntity)  # Fill cache
        context = self.build_context(user=user, instance=atom)

        # Queries:
        #   - COUNT Relations
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        #   - Relations
        #   - Contacts (objects)
        with self.assertNumQueries(5):
            render = RelationsBrick().detailview_display(context)

        brick_node1 = self.get_brick_node(self.get_html_tree(render), brick=RelationsBrick)
        self.assertInstanceLink(brick_node1, tenma)
        self.assertInstanceLink(brick_node1, uran)

        # From view ---
        response = self.assertGET200(atom.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/bricks/relations.html')

        brick_node2 = self.get_brick_node(
            self.get_html_tree(response.content), brick=RelationsBrick,
        )
        self.assertInstanceLink(brick_node2, tenma)
        self.assertInstanceLink(brick_node2, uran)
        self.assertEqual('{}', brick_node2.attrib.get('data-brick-reloading-info'))

    def test_relations_brick__no_minimal_display(self):
        """With A SpecificRelationBrick; but the concerned relationship is minimal_display=False
        (so there is no RelationType to exclude).
        """
        user = self.login_as_root_and_get()
        rbrick_id = RelationsBrick.id

        rtype1 = RelationType.objects.builder(
            id='test-subject_son', predicate='is the son of',
        ).symmetric(id='test-object_father', predicate='is the father of').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_brother', predicate='is the brother of',
        ).symmetric(id='test-object_sister', predicate='is the sister of').get_or_create()[0]
        rbi = RelationBrickItem.objects.create(relation_type=rtype1)

        BrickDetailviewLocation.objects.create_for_model_brick(
            order=1, zone=BrickDetailviewLocation.LEFT, model=FakeContact,
        )

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            zone=BrickDetailviewLocation.RIGHT, model=FakeContact,
        )
        create_bdl(brick=rbi.brick_id, order=2)
        create_bdl(brick=rbrick_id,    order=3)

        create_contact = partial(FakeContact.objects.create, user=user)
        atom  = create_contact(first_name='Atom', last_name='Tenma')
        tenma = create_contact(first_name='Dr',   last_name='Tenma')
        uran  = create_contact(first_name='Uran', last_name='Ochanomizu')

        create_rel = partial(Relation.objects.create, subject_entity=atom, user=user)
        create_rel(type=rtype1, object_entity=tenma)
        create_rel(type=rtype2, object_entity=uran)

        response = self.assertGET200(atom.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/bricks/relations.html')
        self.assertTemplateUsed(response, 'creme_core/bricks/specific-relations.html')

        document = self.get_html_tree(response.content)
        rel_brick_node = self.get_brick_node(document, rbrick_id)

        reloading_info = {'include': [rtype1.id]}
        self.assertEqual(
            json_dump(reloading_info, separators=(',', ':')),
            rel_brick_node.attrib.get('data-brick-reloading-info'),
        )
        self.assertInstanceLink(rel_brick_node, tenma)
        self.assertInstanceLink(rel_brick_node, uran)

        rbi_brick_node = self.get_brick_node(document, rbi.brick_id)
        self.assertIsNone(rbi_brick_node.attrib.get('data-brick-reloading-info'))
        self.assertInstanceLink(rbi_brick_node, tenma)
        self.assertNoInstanceLink(rbi_brick_node, uran)

        # Reloading
        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={
                'brick_id': rbrick_id,
                'extra_data': json_dump({rbrick_id: reloading_info}),
            },
        )

        load_data = response.json()
        self.assertEqual(load_data[0][0], rbrick_id)

        l_document = self.get_html_tree(load_data[0][1])
        l_rel_brick_node = self.get_brick_node(l_document, rbrick_id)
        self.assertInstanceLink(l_rel_brick_node, tenma)
        self.assertInstanceLink(l_rel_brick_node, uran)

    def test_relations_brick__minimal_display(self):
        """With A SpecificRelationBrick; the concerned relationship is minimal_display=True,
        so the RelationType is excluded.
        """
        user = self.login_as_root_and_get()
        rbrick_id = RelationsBrick.id

        rtype1 = RelationType.objects.builder(
            id='test-subject_son', predicate='is the son of', minimal_display=True,
        ).symmetric(
            id='test-object_father', predicate='is the father of', minimal_display=True,
        ).get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_brother', predicate='is the brother of',
        ).symmetric(id='test-object_sister', predicate='is the sister of').get_or_create()[0]
        rbi = RelationBrickItem.objects.create(relation_type=rtype1)

        BrickDetailviewLocation.objects.create_for_model_brick(
            order=1, zone=BrickDetailviewLocation.LEFT, model=FakeContact,
        )

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            zone=BrickDetailviewLocation.RIGHT, model=FakeContact,
        )
        create_bdl(brick=rbi.brick_id, order=2)
        create_bdl(brick=rbrick_id,    order=3)

        create_contact = partial(FakeContact.objects.create, user=user)
        atom  = create_contact(first_name='Atom', last_name='Tenma')
        tenma = create_contact(first_name='Dr',   last_name='Tenma')
        uran  = create_contact(first_name='Uran', last_name='Ochanomizu')

        create_rel = partial(Relation.objects.create, subject_entity=atom, user=user)
        create_rel(type=rtype1, object_entity=tenma)
        create_rel(type=rtype2, object_entity=uran)

        response = self.assertGET200(atom.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/bricks/relations.html')
        self.assertTemplateUsed(response, 'creme_core/bricks/specific-relations.html')

        document = self.get_html_tree(response.content)

        rel_brick_node = self.get_brick_node(document, rbrick_id)
        self.assertInstanceLink(rel_brick_node, uran)
        self.assertNoInstanceLink(rel_brick_node, tenma)

        reloading_info = {'exclude': [rtype1.id]}
        self.assertEqual(
            json_dump(reloading_info, separators=(',', ':')),
            rel_brick_node.attrib.get('data-brick-reloading-info'),
        )

        # Reloading
        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={
                'brick_id': rbrick_id,
                'extra_data': json_dump({rbrick_id: reloading_info}),
            },
        )

        load_data = response.json()
        self.assertEqual(load_data[0][0], rbrick_id)

        l_document = self.get_html_tree(load_data[0][1])
        l_rel_brick_node = self.get_brick_node(l_document, rbrick_id)
        self.assertNoInstanceLink(l_rel_brick_node, tenma)
        self.assertInstanceLink(l_rel_brick_node, uran)

        # Reloading + bad data
        def assertBadData(data):
            self.assertGET200(
                reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
                data={
                    'brick_id': rbrick_id,
                    'extra_data': json_dump({rbrick_id: data}),
                },
            )

        assertBadData(1)
        assertBadData({'include': 1})
        assertBadData({'exclude': 1})
        assertBadData({'include': [[]]})
        assertBadData({'exclude': [[]]})

    def test_customfields_brick(self):
        user = self.login_as_root_and_get()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')

        create_cfield = partial(CustomField.objects.create, content_type=type(atom))
        cfield1 = create_cfield(name='Strength', field_type=CustomField.INT)
        cfield2 = create_cfield(name='Energy',   field_type=CustomField.FLOAT)

        strength = 1523
        energy = Decimal('99.60')
        cfield1.value_class.objects.create(
            entity=atom, custom_field=cfield1, value=strength,
        )
        cfield2.value_class.objects.create(
            entity=atom, custom_field=cfield2, value=energy,
        )

        context = self.build_context(user=user, instance=atom)
        # Queries:
        #   - CustomFields
        #   - CustomFieldIntegers
        #   - CustomFieldFloats
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        with self.assertNumQueries(5):
            render = CustomFieldsBrick().detailview_display(context)

        brick_node1 = self.get_brick_node(self.get_html_tree(render), brick=CustomFieldsBrick)
        self.assertEqual(
            number_format(strength, force_grouping=True),
            self.get_brick_tile(brick_node1, f'custom_field-{cfield1.id}').text,
        )
        self.assertEqual(
            number_format(energy, force_grouping=True),
            self.get_brick_tile(brick_node1, f'custom_field-{cfield2.id}').text,
        )

        # From view ---
        response = self.assertGET200(atom.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/bricks/custom-fields.html')

        brick_node2 = self.get_brick_node(
            self.get_html_tree(response.content), brick=CustomFieldsBrick,
        )
        self.assertEqual(
            number_format(strength, force_grouping=True),
            self.get_brick_tile(brick_node2, f'custom_field-{cfield1.id}').text,
        )
        self.assertEqual(
            number_format(energy, force_grouping=True),
            self.get_brick_tile(brick_node2, f'custom_field-{cfield2.id}').text,
        )

    def test_history_brick__deatilview(self):
        user = self.login_as_root_and_get()
        atom = FakeContact.objects.create(
            user=user, first_name='Atom', last_name='Tenma', phone='123456',
        )

        atom = self.refresh(atom)
        atom.phone = '1234567'
        atom.email = 'atom@tenma.corp'
        atom.save()

        HistoryBrick.page_size = max(4, settings.BLOCK_SIZE)

        ContentType.objects.get_for_models(HistoryLine, CremeEntity)  # Fill cache

        context = self.build_context(user=user, instance=atom)
        # Queries:
        #   - COUNT HistoryLines
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        #   - HistoryLines
        #   - Users
        with self.assertNumQueries(5):
            render = HistoryBrick().detailview_display(context)

        self.get_brick_node(self.get_html_tree(render), brick=HistoryBrick)

        # From view ---
        response = self.assertGET200(atom.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/bricks/history.html')

        brick_node = self.get_brick_node(self.get_html_tree(response.content), brick=HistoryBrick)

        h_info = []
        cls_prefix = 'history-line-'
        for div_node in brick_node.findall('.//div'):
            css_classes = div_node.attrib.get('class', '').split(' ')
            if 'history-line' in css_classes:
                for css_cls in css_classes:
                    if css_cls.startswith(cls_prefix):
                        h_info.append(
                            (css_cls.removeprefix(cls_prefix), div_node)
                        )

        self.assertEqual(2, len(h_info))
        self.assertEqual('creation', h_info[1][0])

        edition_cls, edition_node = h_info[0]
        self.assertEqual('edition', edition_cls)
        self.assertEqual(2, len(edition_node.findall('.//li')))

    def test_history_brick__home(self):
        user = self.login_as_root_and_get()

        HistoryLine.objects.all().delete()

        create_contact = partial(FakeContact.objects.create, user=user)
        atom  = create_contact(first_name='Atom', last_name='Tenma')
        tenma = create_contact(first_name='Dr',   last_name='Tenma')

        atom = self.refresh(atom)
        atom.phone = '1234567'
        atom.save()

        HistoryBrick.page_size = max(4, settings.BLOCK_SIZE)

        ContentType.objects.get_for_models(HistoryLine, CremeEntity)  # Fill cache

        context = self.build_context(user=user)
        # Queries:
        #   - COUNT HistoryLines
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        #   - HistoryLines
        #   - Contacts
        #   - Users
        with self.assertNumQueries(6):
            render = HistoryBrick().home_display(context)

        brick_node1 = self.get_brick_node(self.get_html_tree(render), brick=HistoryBrick)
        self.assertInstanceLink(brick_node1, atom)
        self.assertInstanceLink(brick_node1, tenma)

        # From view ---
        response = self.assertGET200(reverse('creme_core__home'))
        self.assertTemplateUsed(response, 'creme_core/bricks/history.html')

        brick_node2 = self.get_brick_node(
            self.get_html_tree(response.content), brick=HistoryBrick,
        )
        self.assertInstanceLink(brick_node2, atom)
        self.assertInstanceLink(brick_node2, tenma)

    @override_settings(LAST_ENTITIES_SIZE=10)
    def test_recent_entities_brick(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')
        contact3 = create_contact(first_name='Mycroft', last_name='Holmes')

        orga = FakeOrganisation.objects.create(user=user, name='Moriarty corp')

        create_lve = partial(LastViewedEntity.objects.create, user=user)
        create_lve(real_entity=contact1)
        create_lve(real_entity=orga)
        create_lve(real_entity=contact2, user=self.create_user())
        create_lve(real_entity=contact3)

        contact3.trash()

        response = self.assertGET200(reverse('creme_core__home'))
        self.assertTemplateUsed(response, 'creme_core/bricks/recent-entities.html')

        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=RecentEntitiesBrick)
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Recent entity',
            plural_title='{count} Recent entities',
        )
        self.assertInstanceLink(brick_node=brick_node, entity=contact1)
        self.assertInstanceLink(brick_node=brick_node, entity=orga)
        self.assertNoInstanceLink(brick_node=brick_node, entity=contact2)
        self.assertNoInstanceLink(brick_node=brick_node, entity=contact3)

    @override_settings(PINNED_ENTITIES_SIZE=10)
    def test_pinned_entities_brick(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')

        orga = FakeOrganisation.objects.create(user=user, name='Moriarty corp')

        create_pinned = PinnedEntity.objects.create
        create_pinned(real_entity=contact1, user=user)
        create_pinned(real_entity=orga, user=user)
        create_pinned(real_entity=contact2, user=self.create_user())

        response = self.assertGET200(reverse('creme_core__my_page'))
        self.assertTemplateUsed(response, 'creme_core/bricks/pinned-entities.html')

        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=PinnedEntitiesBrick)
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Pinned entity',
            plural_title='{count} Pinned entities',
        )
        self.assertInstanceLink(brick_node=brick_node, entity=contact1)
        self.assertInstanceLink(brick_node=brick_node, entity=orga)
        self.assertNoInstanceLink(brick_node=brick_node, entity=contact2)

    def test_statistics_brick(self):
        user = self.login_as_standard()

        s_id1 = 'creme_core-fake_contacts'
        label1 = 'Fake Contacts'
        fmt1 = 'There are {} Contacts'.format

        s_id2 = 'creme_core-fake_organisations'
        label2 = 'Fake Organisations'
        fmt2 = 'There are {} Organisations'.format

        s_id3 = 'creme_core-fake_addresses'
        label3 = 'Fake Addresses'
        fmt3 = 'There are {} Addresses'.format

        statistic_registry.register(
            s_id1, label1, lambda: [fmt1(FakeContact.objects.count())],
        ).register(
            id=s_id2, label=label2,
            func=lambda: [fmt2(FakeOrganisation.objects.count())],
            perm='creme_core',
        ).register(
            id=s_id3, label=label3,
            func=lambda: [fmt3(FakeAddress.objects.count())],
            perm='persons',  # <== not allowed
        )

        create_contact = partial(FakeContact.objects.create, user=user)
        create_contact(first_name='Atom', last_name='Tenma')
        create_contact(first_name='Dr',   last_name='Tenma')

        FakeOrganisation.objects.create(user=user, name='Tenma corp')

        response = self.assertGET200(reverse('creme_core__home'))
        self.assertTemplateUsed(response, 'creme_core/bricks/statistics.html')

        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=StatisticsBrick)

        stats_info = {}

        for tr_node in brick_node.findall('.//tr'):
            texts = [td_node.text.strip() for td_node in tr_node.findall('.//td')]
            self.assertEqual(2, len(texts))

            stats_info[texts[0]] = texts[1]

        self.assertEqual(
            fmt1(FakeContact.objects.count()),
            stats_info.get(label1),
        )
        self.assertEqual(
            fmt2(FakeOrganisation.objects.count()),
            stats_info.get(label2),
        )
        self.assertNotIn(label3, stats_info)
