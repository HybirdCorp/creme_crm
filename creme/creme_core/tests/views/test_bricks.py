from copy import deepcopy
from json import dumps as json_dump

from django.urls import reverse

from creme.creme_core.bricks import RelationsBrick
from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.bricks import (
    Brick,
    BrickManager,
    BrickRegistry,
    InstanceBrick,
)
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickState,
    CustomBrickConfigItem,
    FakeAddress,
    FakeContact,
    FakeOrganisation,
    FieldsConfig,
    InstanceBrickConfigItem,
)
from creme.creme_core.views.bricks import BricksReloading

from ..base import CremeTestCase
from .base import AppPermissionBrick, BrickTestCaseMixin


class BrickViewsTestCase(BrickTestCaseMixin, CremeTestCase):
    SET_STATE_URL = reverse('creme_core__set_brick_state')

    class TestBrick(Brick):
        verbose_name = 'Testing purpose'

        string_format_detail = '<div id="brick-{id}" data-brick-id="{id}">DETAIL</div>'.format
        string_format_home   = '<div id="brick-{id}" data-brick-id="{id}">HOME</div>'.format

        def detailview_display(self, context):
            return self.string_format_detail(id=self.id)

        def home_display(self, context):
            return self.string_format_home(id=self.id)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.original_brick_registry = BricksReloading.brick_registry
        BricksReloading.brick_registry = cls.brick_registry = deepcopy(
            BricksReloading.brick_registry
        ).register(
            AppPermissionBrick,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        BricksReloading.brick_registry = cls.original_brick_registry

    def test_set_state01(self):
        user = self.login_as_root_and_get()
        brick_id = RelationsBrick.id

        self.assertTrue(BrickState.objects.get_for_brick_id(brick_id=brick_id, user=user).is_open)
        self.assertFalse(BrickState.objects.all())

        self.assertPOST200(self.SET_STATE_URL, data={'brick_id': brick_id, 'is_open': 1})
        self.assertFalse(BrickState.objects.all())

        self.assertPOST200(self.SET_STATE_URL, data={'brick_id': brick_id, 'is_open': 0})
        self.assertEqual(1, BrickState.objects.count())

        bstate = self.get_object_or_fail(BrickState, user=user, brick_id=brick_id)
        self.assertFalse(bstate.is_open)
        self.assertTrue(bstate.show_empty_fields)

        self.assertPOST200(self.SET_STATE_URL, data={'brick_id': brick_id})  # No data
        self.assertEqual(1, BrickState.objects.count())

        bstate = self.get_object_or_fail(BrickState, user=user, brick_id=brick_id)
        self.assertFalse(bstate.is_open)
        self.assertTrue(bstate.show_empty_fields)

    def test_set_state02(self):
        user = self.login_as_root_and_get()
        brick_id = RelationsBrick.id

        bstate = BrickState.objects.get_for_brick_id(brick_id=brick_id, user=user)
        self.assertTrue(bstate.is_open)
        self.assertTrue(bstate.show_empty_fields)
        self.assertIsNone(bstate.pk)

        # ---
        self.assertPOST200(
            self.SET_STATE_URL,
            data={'brick_id': brick_id, 'is_open': 1, 'show_empty_fields': 1},
        )
        self.assertFalse(BrickState.objects.all())

        # ---
        self.assertPOST200(
            self.SET_STATE_URL,
            data={'brick_id': brick_id, 'is_open': 1, 'show_empty_fields': 0},
        )
        bstate = self.get_object_or_fail(BrickState, user=user, brick_id=brick_id)
        self.assertTrue(bstate.is_open)
        self.assertFalse(bstate.show_empty_fields)

    def test_set_state03(self):
        user = self.login_as_root_and_get()
        other_user = self.create_user()

        brick_id = RelationsBrick.id
        BrickState.objects.get_for_brick_id(brick_id=brick_id, user=other_user).save()

        self.client.post(
            self.SET_STATE_URL,
            data={'brick_id': brick_id, 'is_open': 0, 'show_empty_fields': 0},
        )

        bstates = BrickState.objects.filter(brick_id=brick_id)
        user_bstate = self.get_alone_element(
            bstate for bstate in bstates if bstate.user == user
        )
        other_bstate = self.get_alone_element(
            bstate for bstate in bstates if bstate.user == other_user
        )

        self.assertTrue(other_bstate.is_open)
        self.assertTrue(other_bstate.show_empty_fields)

        self.assertFalse(user_bstate.is_open)
        self.assertFalse(user_bstate.show_empty_fields)

    def test_set_state04(self):
        "Instance brick."
        user = self.login_as_root_and_get()
        casca = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')

        class ContactBrick(InstanceBrick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'base_block')
            dependencies = (FakeOrganisation,)
            template_name = 'persons/bricks/itdoesnotexist.html'

            def detailview_display(self, context):
                return f'<table id="{self.id}"><thead><tr>' \
                       f'{self.config_item.entity}</tr></thead></table>'  # Useless :)

        ibci = InstanceBrickConfigItem.objects.create(
            entity=casca,
            brick_class_id=ContactBrick.id,
        )

        brick_registry = BrickRegistry()
        brick_registry.register_4_instance(ContactBrick)

        brick_id = ibci.brick_id

        self.assertPOST200(
            self.SET_STATE_URL,
            data={'brick_id': brick_id, 'is_open': 1, 'show_empty_fields': 1},
        )

    def test_reload_basic01(self):
        self.login_as_standard(creatable_models=[FakeContact])

        class FoobarBrick1(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_basic01_1')
            permissions = 'creme_core'

        class FoobarBrick2(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_basic01_2')
            permissions = ['creme_core', 'creme_core.add_fakecontact']

        self.brick_registry.register(FoobarBrick1, FoobarBrick2)

        response = self.assertGET200(
            reverse('creme_core__reload_bricks'),
            data={'brick_id': [FoobarBrick1.id, FoobarBrick2.id, 'silly_id']},
        )
        self.assertEqual('application/json', response['Content-Type'])

        fmt = self.TestBrick.string_format_detail
        self.assertListEqual(
            [
                [FoobarBrick1.id, fmt(id=FoobarBrick1.id)],
                [FoobarBrick2.id, fmt(id=FoobarBrick2.id)],
            ],
            response.json(),
        )

    def test_reload_basic02(self):
        "Do not have the credentials."
        self.login_as_standard()

        class FoobarBrick1(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_basic02')
            permissions = 'persons'

        self.brick_registry.register(FoobarBrick1)

        content = self.assertGET200(
            reverse('creme_core__reload_bricks'), data={'brick_id': FoobarBrick1.id},
        ).json()
        self.assertIsList(content, length=1)

        brick_info = content[0]
        self.assertEqual(FoobarBrick1.id, brick_info[0])

        brick_html = brick_info[1]
        self.assertIn('<div class="brick brick-forbidden',  brick_html)
        self.assertIn(f'id="brick-{FoobarBrick1.id}"',      brick_html)
        self.assertIn(f'data-brick-id="{FoobarBrick1.id}"', brick_html)

    def test_reload_basic03(self):
        "Other app."
        app_name = 'persons'
        self.login_as_standard(allowed_apps=[app_name])

        class FoobarBrick1(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_basic03')
            permissions = app_name

        self.brick_registry.register(FoobarBrick1)

        response = self.assertGET200(
            reverse('creme_core__reload_bricks'),
            data={'brick_id': FoobarBrick1.id},
        )
        self.assertListEqual(
            [[FoobarBrick1.id, self.TestBrick.string_format_detail(id=FoobarBrick1.id)]],
            response.json(),
        )

    def test_reload_basic04(self):
        "Extra data."
        self.login_as_root()
        extra_data = [1, 2]

        received_extra_data = None

        class FoobarBrick(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_basic04')

            @self.TestBrick.reloading_info.setter
            def reloading_info(self, info):
                nonlocal received_extra_data
                received_extra_data = info

        self.brick_registry.register(FoobarBrick)

        response = self.assertGET200(
            reverse('creme_core__reload_bricks'),
            data={
                'brick_id': FoobarBrick.id,
                'extra_data': json_dump({FoobarBrick.id: extra_data}),
            },
        )
        self.assertListEqual(
            [
                [FoobarBrick.id, self.TestBrick.string_format_detail(id=FoobarBrick.id)],
            ],
            response.json(),
        )

        self.assertEqual(extra_data, received_extra_data)

    def test_reload_basic05(self):
        "Invalid extra data."
        self.login_as_root()

        error = None
        received_extra_data = None

        class FoobarBrick(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_basic05')

            def detailview_display(self, context):
                nonlocal error, received_extra_data

                try:
                    received_extra_data = BrickManager.get(context).get_reloading_info(self)
                except Exception as e:
                    error = e

                return super().detailview_display(context)

        self.brick_registry.register(FoobarBrick)

        self.assertGET200(
            reverse('creme_core__reload_bricks'),
            data={
                'brick_id': FoobarBrick.id,
                'extra_data': '{%s: ' % FoobarBrick.id,
            },
        )
        self.assertIsNone(received_extra_data)
        self.assertIsNotNone(error)

    def test_reload_detailview01(self):
        user = self.login_as_root_and_get()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')

        class FoobarBrick(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_detailview01')

            contact = None

            def detailview_display(self, context):
                FoobarBrick.contact = context.get('object')
                return super().detailview_display(context)

        self.brick_registry.register(FoobarBrick)

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={'brick_id': FoobarBrick.id},
        )
        self.assertEqual('application/json', response['Content-Type'])
        self.assertListEqual(
            [[FoobarBrick.id, self.TestBrick.string_format_detail(id=FoobarBrick.id)]],
            response.json(),
        )
        self.assertEqual(atom, FoobarBrick.contact)

    def test_reload_detailview02(self):
        "With dependencies."
        user = self.login_as_root_and_get()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')

        class FoobarBrick1(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_detailview02_1')
            contact = None

            def detailview_display(self, context):
                FoobarBrick1.contact = context.get('object')
                return super().detailview_display(context)

        class FoobarBrick2(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_detailview02_2')
            contact = None

            def detailview_display(self, context):
                FoobarBrick2.contact = context.get('object')
                return super().detailview_display(context)

        class FoobarBrick3(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_detailview02_3')
            contact = None

            def detailview_display(self, context):
                FoobarBrick3.contact = context.get('object')
                return super().detailview_display(context)

        self.brick_registry.register(FoobarBrick1, FoobarBrick2, FoobarBrick3)

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={'brick_id': [FoobarBrick1.id, FoobarBrick2.id, FoobarBrick3.id]},
        )

        fmt = self.TestBrick.string_format_detail
        self.assertEqual(
            [
                [FoobarBrick1.id, fmt(id=FoobarBrick1.id)],
                [FoobarBrick2.id, fmt(id=FoobarBrick2.id)],
                [FoobarBrick3.id, fmt(id=FoobarBrick3.id)],
            ],
            response.json(),
        )
        self.assertEqual(atom, FoobarBrick1.contact)
        self.assertEqual(atom, FoobarBrick2.contact)
        self.assertEqual(atom, FoobarBrick3.contact)

    def test_reload_detailview03(self):
        "Do not have the credentials."
        self.login_as_standard()

        atom = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Atom', last_name='Tenma',
        )

        class FoobarBrick(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_detailview03')

        self.brick_registry.register(FoobarBrick)

        self.assertGET403(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={'brick_id': FoobarBrick.id},
        )

    def test_reload_detailview04(self):
        "Not superuser."
        user = self.login_as_standard()
        self.add_credentials(user.role, all=['VIEW'])

        atom = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Atom', last_name='Tenma',
        )
        self.assertTrue(user.has_perm_to_view(atom))

        class FoobarBrick(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_detailview04')

        self.brick_registry.register(FoobarBrick)

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={'brick_id': FoobarBrick.id},
        )
        self.assertListEqual(
            [
                [FoobarBrick.id, self.TestBrick.string_format_detail(id=FoobarBrick.id)],
            ],
            response.json(),
        )

    def test_reload_detailview05(self):
        "Invalid brick_id."
        user = self.login_as_root_and_get()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')

        url = reverse('creme_core__reload_detailview_bricks', args=(atom.id,))
        response1 = self.assertGET200(
            url, data={'brick_id': 'test_bricks_reload_detailview05'},
        )
        self.assertEqual('application/json', response1['Content-Type'])
        self.assertListEqual([], response1.json())

        # Several bricks (BUGFIX) ---
        response2 = self.assertGET200(
            url, data={'brick_id': ['test_bricks_reload_detailview05', 'other-one']},
        )
        self.assertEqual('application/json', response2['Content-Type'])
        self.assertListEqual([], response2.json())

    def test_reload_detailview06(self):
        "Extra data."
        user = self.login_as_root_and_get()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')
        extra_data = [1, 2]
        received_extra_data = None

        class FoobarBrick(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_detailview06')

            @self.TestBrick.reloading_info.setter
            def reloading_info(self, info):
                nonlocal received_extra_data
                received_extra_data = info

        self.brick_registry.register(FoobarBrick)

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={
                'brick_id': FoobarBrick.id,
                'extra_data': json_dump({FoobarBrick.id: extra_data}),
            },
        )
        self.assertListEqual(
            [
                [FoobarBrick.id, self.TestBrick.string_format_detail(id=FoobarBrick.id)],
            ],
            response.json(),
        )

        self.assertTrue(received_extra_data)
        self.assertEqual(extra_data, received_extra_data)

    def test_reload_detailview07(self):
        "Do not have the app credentials."
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*')

        atom = FakeContact.objects.create(
            user=user, first_name='Atom', last_name='Tenma',
        )
        self.assertTrue(user.has_perm_to_view(atom))

        class FoobarBrick(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_detailview07')
            permissions = 'persons'

        self.brick_registry.register(FoobarBrick)

        content = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={'brick_id': FoobarBrick.id},
        ).json()
        self.assertIsList(content, length=1)

        brick_info = content[0]
        self.assertEqual(FoobarBrick.id, brick_info[0])

        brick_html = brick_info[1]
        self.assertIn('<div class="brick brick-forbidden', brick_html)
        self.assertIn(f'id="brick-{FoobarBrick.id}"',      brick_html)
        self.assertIn(f'data-brick-id="{FoobarBrick.id}"', brick_html)

    def test_reload_detailview08(self):
        "Target_ctypes constraint."
        user = self.login_as_root_and_get()

        atom = FakeContact.objects.create(
            user=user, first_name='Atom', last_name='Tenma',
        )

        class FoobarBrick1(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_detailview08_1')
            target_ctypes = [FakeOrganisation, FakeContact]

        class FoobarBrick2(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_detailview08_2')
            target_ctypes = [FakeOrganisation]  # FakeContact

        self.brick_registry.register(FoobarBrick1, FoobarBrick2)

        content = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={'brick_id': [FoobarBrick1.id, FoobarBrick2.id]},
        ).json()
        self.assertIsList(content, length=2)

        brick1 = FoobarBrick1()
        self.assertListEqual(
            [brick1.id, brick1.detailview_display({})],
            content[0],
        )

        brick_info2 = content[1]
        self.assertEqual(FoobarBrick2.id, brick_info2[0])

        brick_html2 = brick_info2[1]
        self.assertIn('<div class="brick brick-void', brick_html2)
        self.assertIn(f'id="brick-{FoobarBrick2.id}"',      brick_html2)
        self.assertIn(f'data-brick-id="{FoobarBrick2.id}"', brick_html2)

    def test_reload_home01(self):
        self.login_as_root()

        class FoobarBrick1(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_home01_1')

        class FoobarBrick2(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_home01_2')

        self.brick_registry.register(FoobarBrick1, FoobarBrick2)

        response = self.assertGET200(
            reverse('creme_core__reload_home_bricks'),
            data={'brick_id': [FoobarBrick1.id, FoobarBrick2.id, 'silly_id']},
        )
        self.assertEqual('application/json', response['Content-Type'])

        fmt = self.TestBrick.string_format_home
        self.assertListEqual(
            [
                [FoobarBrick1.id, fmt(id=FoobarBrick1.id)],
                [FoobarBrick2.id, fmt(id=FoobarBrick2.id)],
            ],
            response.json(),
        )

    def test_reload_home02(self):
        "No app permissions."
        self.login_as_standard()

        class FoobarBrick(self.TestBrick):
            id = Brick.generate_id('creme_core', 'test_bricks_reload_home02')
            permissions = 'persons'

        self.brick_registry.register(FoobarBrick)

        content = self.assertGET200(
            reverse('creme_core__reload_home_bricks'), data={'brick_id': FoobarBrick.id},
        ).json()
        self.assertIsList(content, length=1)

        brick_info = content[0]
        self.assertEqual(FoobarBrick.id, brick_info[0])

        brick_html = brick_info[1]
        self.assertIn('<div class="brick brick-forbidden', brick_html)
        self.assertIn(f'id="brick-{FoobarBrick.id}"',      brick_html)
        self.assertIn(f'data-brick-id="{FoobarBrick.id}"', brick_html)

    def _get_contact_brick_content(self, contact, brick_id):
        response = self.assertGET200(contact.get_absolute_url())
        document = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(document, brick_id)

        return self.get_html_node_or_fail(brick_node, './/div[@class="brick-content "]')

    def _assertNoBrickTile(self, content_node, key):
        self.assertIsNone(content_node.find(f'.//div[@data-key="{key}"]'))

    def test_display_objectbrick01(self):
        user = self.login_as_root_and_get()
        naru = FakeContact.objects.create(
            user=user, last_name='Narusegawa', first_name='Naru', phone='1122334455',
        )

        content_node = self._get_contact_brick_content(naru, brick_id=MODELBRICK_ID)
        self.assertEqual(
            naru.last_name,
            self.get_brick_tile(content_node, 'regular_field-last_name').text,
        )
        self.assertIn(
            naru.phone,
            self.get_brick_tile(content_node, 'regular_field-phone').text,
        )

    def test_display_objectbrick02(self):
        "With FieldsConfig."
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
        )
        naru = FakeContact.objects.create(
            user=user, last_name='Narusegawa',
            first_name='Naru', phone='1122334455',
        )

        content_node = self._get_contact_brick_content(naru, brick_id=MODELBRICK_ID)
        self.assertEqual(
            naru.last_name,
            self.get_brick_tile(content_node, 'regular_field-last_name').text,
        )
        self._assertNoBrickTile(content_node, 'regular_field-phone')

    def test_display_custombrick01(self):
        user = self.login_as_root_and_get()

        fname1 = 'last_name'
        fname2 = 'phone'
        build_cell = EntityCellRegularField.build
        cbc_item = CustomBrickConfigItem.objects.create(
            name='Contact info',
            content_type=FakeContact,
            cells=[
                build_cell(FakeContact, fname1),
                build_cell(FakeContact, fname2),
            ],
        )
        bdl = BrickDetailviewLocation.objects.create_if_needed(
            brick=cbc_item.brick_id,
            order=1000,
            model=FakeContact,
            zone=BrickDetailviewLocation.BOTTOM,
        )
        naru = FakeContact.objects.create(
            user=user, last_name='Narusegawa', first_name='Naru', phone='1122334455',
        )

        content_node = self._get_contact_brick_content(naru, brick_id=bdl.brick_id)
        self.assertEqual(
            naru.last_name,
            self.get_brick_tile(content_node, 'regular_field-last_name').text,
        )
        self.assertIn(
            naru.phone,
            self.get_brick_tile(content_node, 'regular_field-phone').text,
        )

    def test_display_custombrick02(self):
        "With FieldsConfig."
        user = self.login_as_root_and_get()

        hidden_fname = 'phone'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )
        build_cell = EntityCellRegularField.build
        cbc_item = CustomBrickConfigItem.objects.create(
            name='Contact info',
            content_type=FakeContact,
            cells=[
                build_cell(FakeContact, 'last_name'),
                build_cell(FakeContact, hidden_fname),
            ],
        )
        bdl = BrickDetailviewLocation.objects.create_if_needed(
            brick=cbc_item.brick_id,
            order=1000,
            model=FakeContact,
            zone=BrickDetailviewLocation.BOTTOM,
        )
        naru = FakeContact.objects.create(
            user=user, last_name='Narusegawa', first_name='Naru', phone='1122334455',
        )

        content_node = self._get_contact_brick_content(naru, brick_id=bdl.brick_id)
        self.assertEqual(
            naru.last_name,
            self.get_brick_tile(content_node, 'regular_field-last_name').text,
        )
        self._assertNoBrickTile(content_node, 'regular_field-phone')

    def test_display_custombrick03(self):
        "With FieldsConfig on sub-fields."
        user = self.login_as_root_and_get()

        hidden_fname = 'zipcode'
        FieldsConfig.objects.create(
            content_type=FakeAddress,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )
        build_cell = EntityCellRegularField.build
        cbc_item = CustomBrickConfigItem.objects.create(
            name='Contact info',
            content_type=FakeContact,
            cells=[
                build_cell(FakeContact, 'last_name'),
                build_cell(FakeContact, 'address__' + hidden_fname),
                build_cell(FakeContact, 'address__city'),
            ],
        )
        bdl = BrickDetailviewLocation.objects.create_if_needed(
            brick=cbc_item.brick_id,
            order=1000,  # Should be the last block
            model=FakeContact,
            zone=BrickDetailviewLocation.BOTTOM,
        )
        naru = FakeContact.objects.create(
            user=user, last_name='Narusegawa', first_name='Naru', phone='1122334455',
        )
        naru.address = FakeAddress.objects.create(
            value='Hinata Inn', city='Tokyo', zipcode='112233', entity=naru,
        )
        naru.save()

        content_node = self._get_contact_brick_content(naru, brick_id=bdl.brick_id)
        self.assertEqual(
            naru.last_name,
            self.get_brick_tile(content_node, 'regular_field-last_name').text,
        )
        self.assertEqual(
            naru.address.city,
            self.get_brick_tile(content_node, 'regular_field-address__city').text,
        )
        self._assertNoBrickTile(content_node, 'regular_field-address__zipcode')
