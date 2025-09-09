from copy import deepcopy
from functools import partial
from itertools import islice
from json import dumps as json_dump

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from parameterized import parameterized

import creme.creme_core.gui.bricks as gui_bricks
from creme.creme_config import bricks
from creme.creme_core.bricks import (
    CustomFieldsBrick,
    HistoryBrick,
    PropertiesBrick,
    RelationsBrick,
)
from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.gui.bricks import Brick, InstanceBrick
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickMypageLocation,
    BrickState,
    CustomBrickConfigItem,
    CustomField,
    FakeActivity,
    FakeAddress,
    FakeContact,
    FakeEmailCampaign,
    FakeImage,
    FakeInvoiceLine,
    FakeOrganisation,
    FieldsConfig,
    InstanceBrickConfigItem,
    RelationBrickItem,
    RelationType,
    UserRole,
)
from creme.creme_core.registry import creme_registry
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin


# Test Bricks ------------------------------------------------------------------
class _BaseCompleteBrick(Brick):
    verbose_name = 'Testing purpose'

    def detailview_display(self, context):
        return f'<table id="{self.id}"></table>'

    def home_display(self, context):
        return f'<table id="{self.id}"></table>'


class CompleteBrick1(_BaseCompleteBrick):
    id = Brick.generate_id('creme_config', 'testbrickconfig_complete_1')
    verbose_name = 'Complete brick #1'


class CompleteBrick2(_BaseCompleteBrick):
    id = Brick.generate_id('creme_config', 'testbrickconfig_complete_2')
    verbose_name = 'Complete brick #2'


class CompleteBrick3(_BaseCompleteBrick):
    id = Brick.generate_id('creme_config', 'testbrickconfig_complete_3')
    verbose_name = 'Complete brick #3'


class CompleteBrick4(_BaseCompleteBrick):
    id = Brick.generate_id('creme_config', 'testbrickconfig_complete_4')
    verbose_name = 'Complete brick #4'


class HomeOnlyBrick1(Brick):
    id = Brick.generate_id('creme_config', 'testbrickconfig_home_only_1')
    verbose_name = 'Home only brick #1'

    # def detailview_display(self, context): NO

    def home_display(self, context):
        return f'<table id="{self.id}"></table>'


class HomeOnlyBrick2(Brick):
    id = Brick.generate_id('creme_config', 'testbrickconfig_home_only_2')
    verbose_name = 'Home only brick #2'
    configurable = False  # <----

    # def detailview_display(self, context): NO

    def home_display(self, context):
        return f'<table id="{self.id}"></table>'


class DetailviewInstanceBrick(InstanceBrick):
    id = InstanceBrickConfigItem.generate_base_id('creme_config', 'test_detail_instance')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose_name = f'Instance brick #{self.id} for detail-view'

    def detailview_display(self, context):
        return f'<table id="{self.id}"><thead><tr>{self.config_item.entity}</tr></thead></table>'


class HomeInstanceBrick(InstanceBrick):
    id = InstanceBrickConfigItem.generate_base_id('creme_config', 'test_home_instance')
    verbose_name = 'Testing purpose'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose_name = f'Instance brick #{self.id} for home'

    def home_display(self, context):
        return f'<table id="{self.id}"><thead><tr>{self.config_item.entity}</tr></thead></table>'


class FakeContactHatBrick(Brick):
    id = Brick._generate_hat_id('creme_core', 'test_hat_brick')
    verbose_name = 'Fake contact header brick'

    def detailview_display(self, context):
        return f'<table id="{self.id}"></table>'


# Test case --------------------------------------------------------------------

class BricksConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    CLONE_DETAIL_URL = reverse('creme_config__clone_detailview_bricks')
    DEL_DETAIL_URL = reverse('creme_config__delete_detailview_bricks')
    CUSTOM_WIZARD_URL = reverse('creme_config__create_custom_brick')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._bdl_backup = [*BrickDetailviewLocation.objects.all()]
        cls._bpl_backup = [*BrickHomeLocation.objects.all()]
        cls._bml_backup = [*BrickMypageLocation.objects.all()]
        cls._rbi_backup = [*RelationBrickItem.objects.all()]

        BrickDetailviewLocation.objects.all().delete()
        BrickHomeLocation.objects.all().delete()
        BrickMypageLocation.objects.all().delete()
        RelationBrickItem.objects.all().delete()

        cls._original_brick_registry = gui_bricks.brick_registry

        cls._cls_brick_registry = brick_registry = deepcopy(gui_bricks.brick_registry)
        brick_registry.register(
            CompleteBrick1, CompleteBrick2, CompleteBrick3, CompleteBrick4,
            HomeOnlyBrick1,
            HomeOnlyBrick2,
        )

        brick_registry.register_4_instance(DetailviewInstanceBrick)
        brick_registry.register_4_instance(HomeInstanceBrick)

        cls.user = cls.get_root_user()
        cls.role = cls.get_regular_role()

        get_ct = ContentType.objects.get_for_model
        cls.contact_ct = get_ct(FakeContact)
        cls.orga_ct    = get_ct(FakeOrganisation)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        BrickDetailviewLocation.objects.all().delete()
        BrickHomeLocation.objects.all().delete()
        BrickMypageLocation.objects.all().delete()
        RelationBrickItem.objects.all().delete()

        for model, backup in [
            (BrickDetailviewLocation, cls._bdl_backup),
            (BrickHomeLocation, cls._bpl_backup),
            (BrickMypageLocation, cls._bml_backup),
            (RelationBrickItem, cls._rbi_backup),
        ]:
            try:
                model.objects.bulk_create(backup)
            except Exception:
                print(
                    f'{cls.__name__}: test-data backup problem with model={model}'
                )

        gui_bricks.brick_registry = cls._original_brick_registry

    def setUp(self):
        super().setUp()
        gui_bricks.brick_registry = self.brick_registry = deepcopy(self._cls_brick_registry)

    @staticmethod
    def _build_adddetail_url(ct):
        return reverse('creme_config__create_detailview_bricks', args=(ct.id,))

    @staticmethod
    def _build_editdetail_url(ct=None, role=None, superuser=False):
        return reverse(
            'creme_config__edit_detailview_bricks',
            args=(
                ct.id if ct else 0,
                'superuser' if superuser else role.id if role else 'default',
            ),
        )

    @staticmethod
    def _build_rbrick_addctypes_wizard_url(rbi):
        return reverse('creme_config__add_cells_to_rtype_brick', args=(rbi.id,))

    @staticmethod
    def _build_rbrick_editctype_url(rbi, model):
        return reverse(
            'creme_config__edit_cells_of_rtype_brick',
            args=(rbi.id, ContentType.objects.get_for_model(model).id,),
        )

    @staticmethod
    def _build_custombrick_edit_url(cbc_item):
        return reverse('creme_config__edit_custom_brick', args=(cbc_item.id,))

    def _find_location(self, brick_id, locations):
        for location in locations:
            if location.brick_id == brick_id:
                return location

        self.fail('No "{}" in locations ({})'.format(
            brick_id,
            [location.brick_id for location in locations],
        ))

    def test_portal(self):
        self.login_as_root()

        response = self.assertGET200(reverse('creme_config__bricks'))
        self.assertTemplateUsed(response, 'creme_config/portals/bricks.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url')
        )

        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, brick=bricks.BrickDetailviewLocationsBrick)
        self.get_brick_node(tree, brick=bricks.BrickHomeLocationsBrick.id)
        self.get_brick_node(tree, brick=bricks.BrickDefaultMypageLocationsBrick.id)
        self.get_brick_node(tree, brick=bricks.RelationBricksConfigBrick.id)
        self.get_brick_node(tree, brick=bricks.InstanceBricksConfigBrick.id)
        self.get_brick_node(tree, brick=bricks.CustomBricksConfigBrick.id)

    @parameterized.expand([False, True])
    def test_add_detailview(self, superuser):
        if superuser:
            self.login_as_root()
            role = None
        else:
            user = self.login_as_standard(admin_4_apps=['creme_core'])
            role = user.role

        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        BrickDetailviewLocation.objects.multi_create(
            defaults={'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'order': 5},
                {'brick': PropertiesBrick, 'order': 450},
                {'brick': RelationsBrick,  'order': 500},

                {
                    'brick': HistoryBrick, 'order': 8,
                    'zone': BrickDetailviewLocation.RIGHT,
                },
            ],
        )

        url = self._build_adddetail_url(ct)
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('New block configuration for «{model}»').format(model='Test Contact'),
            context1.get('title')
        )
        self.assertEqual(_('Save the configuration'), context1.get('submit_label'))

        with self.assertNoException():
            fields = context1['form'].fields
            locations_f = fields['locations']
            locations_choices = [brick_id for (brick_id, brick) in locations_f.choices]

        self.assertNotIn('hat', fields)

        bricks = [*self.brick_registry.get_compatible_bricks(model)]
        self.assertGreaterEqual(len(bricks), 5)
        self.assertIn(CompleteBrick1.id, locations_choices)

        brick_top1   = bricks[0]
        brick_top2   = bricks[1]
        brick_left1  = bricks[2]
        brick_left2  = self.brick_registry.get_brick_4_object(model)
        brick_right  = bricks[3]
        brick_bottom = bricks[4]

        self.assertIn(brick_top1.id,   locations_choices)
        self.assertIn(brick_top2.id,   locations_choices)
        self.assertIn(brick_left1.id,  locations_choices)
        self.assertIn(brick_left2.id,  locations_choices)
        self.assertIn(brick_right.id,  locations_choices)
        self.assertIn(brick_bottom.id, locations_choices)

        self.assertDictEqual(
            {
                'top': [],
                'left': [MODELBRICK_ID, PropertiesBrick.id, RelationsBrick.id],
                'right': [HistoryBrick.id],
                'bottom': [],
            },
            locations_f.initial,
        )

        # ---
        locations_data = {
            'top':    [brick_top1.id, brick_top2.id],
            'left':   [brick_left1.id, brick_left2.id],
            'right':  [brick_right.id],
            'bottom': [brick_bottom.id],
        }
        self.assertNoFormError(self.client.post(
            url,
            data={
                'role': role.id if role else '',
                'locations': json_dump(locations_data),
            },
        ))

        b_locs = BrickDetailviewLocation.objects.filter(
            content_type=ct, role=role, superuser=superuser,
        )

        def filter_locs(zone):
            return [bl for bl in b_locs if bl.zone == zone]

        top_locations = filter_locs(BrickDetailviewLocation.TOP)
        self.assertEqual(2, len(top_locations))
        self.assertEqual(1, self._find_location(brick_top1.id, top_locations).order)
        self.assertEqual(2, self._find_location(brick_top2.id, top_locations).order)

        left_locations = filter_locs(BrickDetailviewLocation.LEFT)
        self.assertEqual(2, len(left_locations))
        self.assertEqual(1, self._find_location(brick_left1.id, left_locations).order)
        self.assertEqual(2, self._find_location(brick_left2.id, left_locations).order)

        right_locations = filter_locs(BrickDetailviewLocation.RIGHT)
        self.assertEqual(1, len(right_locations))
        self.assertEqual(1, self._find_location(brick_right.id, right_locations).order)

        bottom_locations = filter_locs(BrickDetailviewLocation.BOTTOM)
        self.assertEqual(1, len(bottom_locations))
        self.assertEqual(1, self._find_location(brick_bottom.id, bottom_locations).order)

        self.assertListEqual(
            [''],
            [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.HAT)],
        )

    def test_add_detailview__ignore_used_roles(self):
        "Used roles are not proposed anymore."
        self.login_as_root()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)
        url = self._build_adddetail_url(ct)

        role1 = self.role
        role2 = self.create_role(name='Viewer')

        def get_choices():
            response = self.assertGET200(url)
            form = self.get_form_or_fail(response)

            with self.assertNoException():
                return [*form.fields['role'].choices]

        choices = get_choices()
        self.assertInChoices(value='',       label='*{}*'.format(_('Superuser')), choices=choices)
        self.assertInChoices(value=role1.id, label=role1.name,                    choices=choices)
        self.assertInChoices(value=role2.id, label=role2.name,                    choices=choices)

        # Role ------------
        bricks = [*self.brick_registry.get_compatible_bricks(model)]
        self.assertGreaterEqual(len(bricks), 5, bricks)

        create_loc = partial(BrickDetailviewLocation.objects.create, content_type=ct, order=1)
        create_loc(role=role1, brick_id=bricks[0].id, zone=BrickDetailviewLocation.TOP)
        create_loc(role=role1, brick_id=bricks[1].id, zone=BrickDetailviewLocation.LEFT)
        create_loc(role=role1, brick_id=bricks[2].id, zone=BrickDetailviewLocation.RIGHT)
        create_loc(role=role1, brick_id=bricks[3].id, zone=BrickDetailviewLocation.BOTTOM)

        choices = get_choices()
        self.assertInChoices(value='',       label='*{}*'.format(_('Superuser')), choices=choices)
        self.assertInChoices(value=role2.id, label=role2.name,                    choices=choices)
        self.assertNotInChoices(value=role1.id, choices=choices)

        # Superuser ------------
        create_loc(superuser=True, brick_id=bricks[0].id, zone=BrickDetailviewLocation.TOP)
        create_loc(superuser=True, brick_id=bricks[1].id, zone=BrickDetailviewLocation.LEFT)
        create_loc(superuser=True, brick_id=bricks[2].id, zone=BrickDetailviewLocation.RIGHT)
        create_loc(superuser=True, brick_id=bricks[3].id, zone=BrickDetailviewLocation.BOTTOM)

        choices = get_choices()
        self.assertInChoices(value=role2.id, label=role2.name, choices=choices)
        self.assertNotInChoices(value=role1.id, choices=choices)
        self.assertNotInChoices(value='',       choices=choices)

    def test_add_detailview__initial(self):
        "A configuration for the CT exists."
        self.login_as_root()

        model = FakeContact

        BrickDetailviewLocation.objects.multi_create(
            defaults={'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'order': 5},
                {'brick': RelationsBrick,  'order': 500},

                {
                    'brick': HistoryBrick, 'order': 10,
                    'zone': BrickDetailviewLocation.RIGHT,
                },
            ],
        )
        BrickDetailviewLocation.objects.multi_create(
            defaults={
                'zone': BrickDetailviewLocation.LEFT,
                'model': model,
            },
            data=[
                {
                    'brick': HistoryBrick, 'order': 1,
                    'zone': BrickDetailviewLocation.TOP,
                },

                {'brick': PropertiesBrick, 'order': 10},
                {'order': 15},
            ],
        )

        response = self.assertGET200(
            self._build_adddetail_url(ContentType.objects.get_for_model(model))
        )

        with self.assertNoException():
            locations_f = response.context['form'].fields['locations']

        self.assertDictEqual(
            {
                'top': [HistoryBrick.id],
                'left': [PropertiesBrick.id, MODELBRICK_ID],
                'right': [],
                'bottom': [],
            },
            locations_f.initial,
        )

    def test_add_detailview__not_configurable_models(self):
        self.login_as_root()
        get_ct = ContentType.objects.get_for_model

        build_url = self._build_adddetail_url
        self.assertGET409(build_url(get_ct(FakeAddress)))  # Not a CremeEntity

        model = FakeInvoiceLine
        self.assertIn(model, creme_registry.iter_entity_models())
        self.assertGET409(build_url(get_ct(model)))

    def test_add_detailview__extra_hatbrick(self):
        "Extra HatBrick."
        self.login_as_root()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        self.brick_registry.register_hat(model, secondary_brick_classes=[FakeContactHatBrick])

        url = self._build_adddetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            locations_choices = [brick_id for (brick_id, brick) in fields['locations'].choices]
            hat_f = fields['hat']
            hat_choices = hat_f.choices

        self.assertEqual(2, len(hat_choices))

        generic_brick_id = Brick.GENERIC_HAT_BRICK_ID
        generic_index = self.assertInChoices(
            value=generic_brick_id,
            label=_('Title bar'),
            choices=hat_choices,
        )
        self.assertEqual(0, generic_index)

        hat_index = self.assertInChoices(
            value=FakeContactHatBrick.id,
            label=FakeContactHatBrick.verbose_name,
            choices=hat_choices,
        )
        self.assertEqual(1, hat_index)

        self.assertEqual(generic_brick_id, hat_f.initial)

        self.assertIn(CompleteBrick1.id, locations_choices)
        response = self.client.post(
            url,
            data={
                'hat': FakeContactHatBrick.id,
                'locations': json_dump({'top': [CompleteBrick1.id]}),
            },
        )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(content_type=ct, role=None, superuser=True)

        def filter_locs(zone):
            return [bl for bl in b_locs if bl.zone == zone]

        top_locations = filter_locs(BrickDetailviewLocation.TOP)
        self.assertEqual(1, len(top_locations))
        self.assertEqual(CompleteBrick1.id, top_locations[0].brick_id)

        self.assertListEqual(
            [''],
            [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.LEFT)]
        )
        self.assertListEqual(
            [''],
            [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.RIGHT)]
        )
        self.assertListEqual(
            [''],
            [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.BOTTOM)]
        )

        hat_locations = filter_locs(BrickDetailviewLocation.HAT)
        self.assertEqual(1, len(hat_locations))
        self.assertEqual(FakeContactHatBrick.id, hat_locations[0].brick_id)

    def test_add_detailview__perms(self):
        "Admin credentials are needed."
        self.login_as_standard()
        self.assertGET403(
            self._build_adddetail_url(self.contact_ct)
        )

    def test_clone_role_config01(self):
        "Role to role."
        self.login_as_root()
        self.assertFalse(BrickDetailviewLocation.objects.filter(superuser=True))

        role1 = self.get_regular_role()
        role2 = self.create_role()

        model1 = FakeContact
        model2 = FakeOrganisation
        get_bricks = self.brick_registry.get_compatible_bricks
        brick_ids1 = [brick_cls.id for brick_cls in islice(get_bricks(model1), 3)]
        brick_ids2 = [brick_cls.id for brick_cls in islice(get_bricks(model2), 2)]

        LEFT = BrickDetailviewLocation.LEFT
        RIGHT = BrickDetailviewLocation.RIGHT
        get_ct = ContentType.objects.get_for_model
        ct1 = get_ct(model1)
        ct2 = get_ct(model2)

        create_loc = BrickDetailviewLocation.objects.create
        create_loc(content_type=ct1, brick_id=brick_ids1[0], order=1, zone=RIGHT)
        create_loc(content_type=ct1, brick_id=brick_ids1[1], order=2, zone=RIGHT)

        role1_locs = [
            create_loc(role=role1, content_type=ct1, order=1, brick_id=brick_ids1[0], zone=LEFT),
            create_loc(role=role1, content_type=ct1, order=2, brick_id=brick_ids1[1], zone=LEFT),
            create_loc(role=role1, content_type=ct1, order=1, brick_id=brick_ids1[2], zone=RIGHT),

            create_loc(role=role1, content_type=ct2, order=1, brick_id=brick_ids2[0], zone=LEFT),
            create_loc(role=role1, content_type=ct2, order=1, brick_id=brick_ids2[1], zone=RIGHT),
        ]

        url = self.CLONE_DETAIL_URL
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Clone the configuration of a role'), context1.get('title'),
        )
        self.assertEqual(_('Create the configuration'), context1.get('submit_label'))

        with self.assertNoException():
            fields = context1['form'].fields
            source_f = fields['source']
            source_choices = [*source_f.choices]

            target_f = fields['target']
            target_choices = [*target_f.choices]

        self.assertTrue(source_f.required)
        self.assertInChoices(
            value=role1.id, label=role1.name, choices=source_choices,
        )
        self.assertNotInChoices(value=role2.id, choices=source_choices)
        self.assertNotInChoices(value='',       choices=source_choices)

        self.assertEqual(
            _('If the target has already a configuration, it will be overridden'),
            target_f.help_text,
        )
        self.assertInChoices(
            value='', label='*{}*'.format(_('Superuser')), choices=target_choices,
        )
        self.assertInChoices(
            value=role1.id,
            label=ngettext(
                singular='{role} ({count} type of entity is configured)',
                plural='{role} ({count} types of entity are configured)',
                number=2,
            ).format(role=role1.name, count=2),
            choices=target_choices,
        )
        self.assertInChoices(
            value=role2.id, label=role2.name, choices=target_choices,
        )

        # ---
        response2 = self.assertPOST200(
            url, follow=True, data={'source': role1.id, 'target': role1.id},
        )
        self.assertFormError(
            response2.context['form'],
            field=None, errors=_('The source and the target must be different.'),
        )

        # ---
        self.assertNoFormError(self.client.post(
            url, data={'source': role1.id, 'target': role2.id},
        ))

        def as_tuple(loc):
            return loc.content_type, loc.order, loc.brick_id, loc.zone

        self.assertCountEqual(
            [as_tuple(loc) for loc in role1_locs],
            [
                as_tuple(loc)
                for loc in BrickDetailviewLocation.objects.filter(role=role2, superuser=False)
            ],
        )

    def test_clone_role_config02(self):
        "Superuser to role."
        self.login_as_root()
        role = self.get_regular_role()

        model = FakeContact
        brick_ids = [
            brick_cls.id
            for brick_cls in islice(self.brick_registry.get_compatible_bricks(model), 3)
        ]

        LEFT = BrickDetailviewLocation.LEFT
        RIGHT = BrickDetailviewLocation.RIGHT
        create_loc = partial(
            BrickDetailviewLocation.objects.create,
            content_type=ContentType.objects.get_for_model(model),
        )
        create_loc(brick_id=brick_ids[0], order=1, zone=RIGHT)
        create_loc(brick_id=brick_ids[1], order=2, zone=RIGHT)
        create_loc(brick_id=brick_ids[2], order=3, zone=RIGHT)

        superuser_locs = [
            create_loc(brick_id=brick_ids[0], superuser=True, order=1, zone=LEFT),
            create_loc(brick_id=brick_ids[1], superuser=True, order=2, zone=LEFT),
        ]

        url = self.CLONE_DETAIL_URL
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            source_f = fields['source']
            source_choices = [*source_f.choices]
            target_choices = [*fields['target'].choices]

        self.assertFalse(source_f.required)
        self.assertInChoices(
            value='', label='*{}*'.format(_('Superuser')), choices=source_choices,
        )
        self.assertNotInChoices(value=role.id, choices=source_choices)

        self.assertInChoices(
            value='',
            label=ngettext(
                singular='*Superuser* ({count} type of entity is configured)',
                plural='*Superuser* ({count} types of entity are configured)',
                number=1,
            ).format(count=1),
            choices=target_choices,
        )

        # ---
        self.assertNoFormError(self.client.post(
            url, data={'source': '', 'target': role.id},
        ))

        def as_tuple(loc):
            return loc.content_type, loc.order, loc.brick_id, loc.zone

        self.maxDiff = None
        self.assertCountEqual(
            [as_tuple(loc) for loc in superuser_locs],
            [
                as_tuple(loc)
                for loc in BrickDetailviewLocation.objects.filter(role=role, superuser=False)
            ],
        )

    def test_clone_role_config03(self):
        "Role to superuser."
        self.login_as_root()
        role = self.get_regular_role()

        model = FakeContact
        brick_ids = [
            brick_cls.id
            for brick_cls in islice(self.brick_registry.get_compatible_bricks(model), 3)
        ]

        LEFT = BrickDetailviewLocation.LEFT
        RIGHT = BrickDetailviewLocation.RIGHT
        create_loc = partial(
            BrickDetailviewLocation.objects.create,
            content_type=ContentType.objects.get_for_model(model),
        )
        create_loc(brick_id=brick_ids[0], order=1, zone=RIGHT)
        create_loc(brick_id=brick_ids[1], order=2, zone=RIGHT)
        create_loc(brick_id=brick_ids[2], order=3, zone=RIGHT)

        role_locs = [
            create_loc(brick_id=brick_ids[0], role=role, order=1, zone=LEFT),
            create_loc(brick_id=brick_ids[1], role=role, order=2, zone=LEFT),
        ]

        self.assertNoFormError(self.client.post(
            self.CLONE_DETAIL_URL, data={'source': role.id, 'target': ''},
        ))

        def as_tuple(loc):
            return loc.content_type, loc.order, loc.brick_id, loc.zone

        self.maxDiff = None
        self.assertCountEqual(
            [as_tuple(loc) for loc in role_locs],
            [
                as_tuple(loc)
                for loc in BrickDetailviewLocation.objects.filter(role=None, superuser=True)
            ],
        )

    def test_clone_role_config04(self):
        "Override existing configuration (role)."
        self.login_as_root()
        self.assertFalse(BrickDetailviewLocation.objects.filter(superuser=True))

        role1 = self.get_regular_role()
        role2 = self.create_role()

        model1 = FakeContact
        model2 = FakeOrganisation
        get_bricks = self.brick_registry.get_compatible_bricks
        brick_ids1 = [brick_cls.id for brick_cls in islice(get_bricks(model1), 4)]
        brick_ids2 = [brick_cls.id for brick_cls in islice(get_bricks(model2), 2)]

        LEFT = BrickDetailviewLocation.LEFT
        RIGHT = BrickDetailviewLocation.RIGHT
        get_ct = ContentType.objects.get_for_model
        ct1 = get_ct(model1)
        ct2 = get_ct(model2)

        create_loc = BrickDetailviewLocation.objects.create
        create_loc(content_type=ct1, order=1, brick_id=brick_ids1[0], zone=LEFT)
        default_count = BrickDetailviewLocation.objects.filter(role=None, superuser=False).count()

        create_loc(role=role1, content_type=ct1, order=1, brick_id=brick_ids1[0], zone=LEFT)
        create_loc(role=role1, content_type=ct1, order=2, brick_id=brick_ids1[1], zone=LEFT)
        create_loc(role=role1, content_type=ct1, order=1, brick_id=brick_ids1[2], zone=RIGHT)

        role2_locs = [
            create_loc(role=role2, content_type=ct1, order=1, brick_id=brick_ids1[2], zone=RIGHT),
            create_loc(role=role2, content_type=ct1, order=2, brick_id=brick_ids1[3], zone=RIGHT),

            create_loc(role=role2, content_type=ct2, order=1, brick_id=brick_ids2[0], zone=LEFT),
            create_loc(role=role2, content_type=ct2, order=2, brick_id=brick_ids2[1], zone=LEFT),
        ]

        url = self.CLONE_DETAIL_URL
        response1 = self.assertGET200(url)

        with self.assertNoException():
            target_choices = [*response1.context['form'].fields['target'].choices]

        self.assertInChoices(
            value=role1.id,
            label=ngettext(
                singular='{role} ({count} type of entity is configured)',
                plural='{role} ({count} types of entity are configured)',
                number=1,
            ).format(role=role1.name, count=1),
            choices=target_choices,
        )

        # ---
        self.assertNoFormError(self.client.post(
            url, data={'source': role2.id, 'target': role1.id},
        ))

        def as_tuple(loc):
            return loc.content_type, loc.order, loc.brick_id, loc.zone

        self.assertCountEqual(
            [as_tuple(loc) for loc in role2_locs],
            [
                as_tuple(loc)
                for loc in BrickDetailviewLocation.objects.filter(role=role1, superuser=False)
            ],
        )
        self.assertEqual(
            default_count,
            BrickDetailviewLocation.objects.filter(role=None, superuser=False).count(),
        )

    def test_clone_role_config05(self):
        "Override existing configuration (superuser)."
        self.login_as_root()
        self.assertFalse(BrickDetailviewLocation.objects.filter(superuser=True))

        role = self.get_regular_role()

        model1 = FakeContact
        model2 = FakeOrganisation
        get_bricks = self.brick_registry.get_compatible_bricks
        brick_ids1 = [brick_cls.id for brick_cls in islice(get_bricks(model1), 4)]
        brick_ids2 = [brick_cls.id for brick_cls in islice(get_bricks(model2), 2)]

        LEFT = BrickDetailviewLocation.LEFT
        RIGHT = BrickDetailviewLocation.RIGHT
        get_ct = ContentType.objects.get_for_model
        ct1 = get_ct(model1)
        ct2 = get_ct(model2)

        create_loc = BrickDetailviewLocation.objects.create
        create_loc(content_type=ct1, order=1, brick_id=brick_ids1[0], zone=LEFT)
        default_count = BrickDetailviewLocation.objects.filter(role=None, superuser=False).count()

        create_loc(superuser=True, content_type=ct1, order=1, brick_id=brick_ids1[0], zone=LEFT)
        create_loc(superuser=True, content_type=ct1, order=2, brick_id=brick_ids1[1], zone=LEFT)
        create_loc(superuser=True, content_type=ct2, order=1, brick_id=brick_ids2[0], zone=RIGHT)

        role_locs = [
            create_loc(role=role, content_type=ct1, order=1, brick_id=brick_ids1[2], zone=RIGHT),
            create_loc(role=role, content_type=ct1, order=2, brick_id=brick_ids1[3], zone=RIGHT),
        ]

        url = self.CLONE_DETAIL_URL
        response1 = self.assertGET200(url)

        with self.assertNoException():
            target_choices = [*response1.context['form'].fields['target'].choices]

        self.assertInChoices(
            value='',
            label=ngettext(
                singular='*Superuser* ({count} type of entity is configured)',
                plural='*Superuser* ({count} types of entity are configured)',
                number=2,
            ).format(count=2),
            choices=target_choices,
        )

        # ---
        self.assertNoFormError(self.client.post(
            url, data={'source': role.id, 'target': ''},
        ))

        def as_tuple(loc):
            return loc.content_type, loc.order, loc.brick_id, loc.zone

        self.assertCountEqual(
            [as_tuple(loc) for loc in role_locs],
            [
                as_tuple(loc)
                for loc in BrickDetailviewLocation.objects.filter(role=None, superuser=True)
            ],
        )
        self.assertEqual(
            default_count,
            BrickDetailviewLocation.objects.filter(role=None, superuser=False).count(),
        )

    def _aux_test_edit_detailview(self, role=None, superuser=False,
                                  expected_title='Edit the bricks',
                                  ):
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        url = self._build_editdetail_url(ct, role, superuser)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context1 = response1.context
        self.assertEqual(expected_title,              context1.get('title'))
        self.assertEqual(_('Save the configuration'), context1.get('submit_label'))

        with self.assertNoException():
            fields = context1['form'].fields
            locations_choices = [brick_id for (brick_id, brick) in fields['locations'].choices]

        bricks = [*self.brick_registry.get_compatible_bricks(model)]
        self.assertGreaterEqual(len(bricks), 5)
        self.assertIn(CompleteBrick1.id, locations_choices)
        self.assertNotIn(HomeOnlyBrick1.id, locations_choices)

        brick_top1   = bricks[0]
        brick_top2   = bricks[1]
        brick_left1  = self.brick_registry.get_brick_4_object(model)
        brick_left2  = bricks[2]
        brick_right  = bricks[3]
        brick_bottom = bricks[4]

        self.assertIn(brick_top1.id,   locations_choices)
        self.assertIn(brick_top2.id,   locations_choices)
        self.assertIn(brick_left1.id,  locations_choices)
        self.assertIn(brick_left2.id,  locations_choices)
        self.assertIn(brick_right.id,  locations_choices)
        self.assertIn(brick_bottom.id, locations_choices)

        # ---
        locations_data = {
            'top': [brick_top1.id, brick_top2.id],
            'left': [brick_left1.id, brick_left2.id],
            'right': [brick_right.id],
            'bottom': [brick_bottom.id],
        }
        self.assertNoFormError(self.client.post(
            url, data={'locations': json_dump(locations_data)},
        ))

        b_locs = BrickDetailviewLocation.objects.filter(
            content_type=ct, role=role, superuser=superuser,
        )

        def filter_locs(zone):
            return [bl for bl in b_locs if bl.zone == zone]

        top_locations = filter_locs(BrickDetailviewLocation.TOP)
        self.assertEqual(2, len(top_locations))
        self.assertEqual(1, self._find_location(brick_top1.id, top_locations).order)
        self.assertEqual(2, self._find_location(brick_top2.id, top_locations).order)

        left_locations = filter_locs(BrickDetailviewLocation.LEFT)
        self.assertEqual(2, len(left_locations))
        self.assertEqual(1, self._find_location(brick_left1.id, left_locations).order)
        self.assertEqual(2, self._find_location(brick_left2.id, left_locations).order)

        right_locations = filter_locs(BrickDetailviewLocation.RIGHT)
        self.assertEqual(1, len(right_locations))
        self.assertEqual(1, self._find_location(brick_right.id, right_locations).order)

        bottom_locations = filter_locs(BrickDetailviewLocation.BOTTOM)
        self.assertEqual(1, len(bottom_locations))
        self.assertEqual(1, self._find_location(brick_bottom.id, bottom_locations).order)

        self.assertListEqual(
            [''],
            [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.HAT)],
        )

    def test_edit_detailview__default(self):
        "Default configuration of a ContentType."
        self.login_as_root()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)
        brick_id = [*self.brick_registry.get_compatible_bricks(model)][0].id

        # These bricks should not be modified
        create_loc = partial(
            BrickDetailviewLocation.objects.create,
            content_type=ct, order=1, brick_id=brick_id,
            zone=BrickDetailviewLocation.TOP,
        )
        b_loc1 = create_loc(role=self.role)
        b_loc2 = create_loc(superuser=True)

        self._aux_test_edit_detailview(
            role=None, superuser=False,
            expected_title=_('Edit default configuration for «{model}»').format(model=ct),
        )

        b_loc1 = self.refresh(b_loc1)
        self.assertEqual(self.role, b_loc1.role)
        self.assertEqual(brick_id, b_loc1.brick_id)

        b_loc2 = self.refresh(b_loc2)
        self.assertTrue(b_loc2.superuser)
        self.assertEqual(brick_id, b_loc2.brick_id)

    def test_edit_detailview__for_a_role(self):
        self.login_as_root()
        self._aux_test_edit_detailview(
            role=self.role, superuser=False,
            expected_title=_('Edit configuration of «{role}» for «{model}»').format(
                role=self.role,
                model=FakeContact._meta.verbose_name,
            ),
        )

    def test_edit_detailview__for_superusers(self):
        self.login_as_root()
        self._aux_test_edit_detailview(
            role=None, superuser=True,
            expected_title=_('Edit configuration of super-users for «{model}»').format(
                model=FakeContact._meta.verbose_name,
            )
        )

    def test_edit_detailview__initial__default_for_ctype(self):
        self.login_as_root()

        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        self.assertFalse(BrickDetailviewLocation.objects.filter(content_type=None))
        self.assertFalse(BrickDetailviewLocation.objects.filter(content_type=ct))

        BrickDetailviewLocation.objects.multi_create(
            defaults={'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'order': 5},
                {'brick': PropertiesBrick, 'order': 450},

                {
                    'brick': HistoryBrick, 'order': 8,
                    'zone': BrickDetailviewLocation.RIGHT,
                },
            ],
        )

        url = self._build_editdetail_url(ct)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            locations_f = response1.context['form'].fields['locations']

        self.assertDictEqual(
            {
                'top': [],
                'left': [MODELBRICK_ID, PropertiesBrick.id],
                'right': [HistoryBrick.id],
                'bottom': [],
            },
            locations_f.initial,
        )

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={'locations': json_dump({'top': [CompleteBrick1.id]})},
        ))

        b_locs = BrickDetailviewLocation.objects.filter(content_type=ct)

        def bricks_info(zone):
            return [(bl.brick_id, bl.order) for bl in b_locs if bl.zone == zone]

        self.assertListEqual([(CompleteBrick1.id, 1)], bricks_info(BrickDetailviewLocation.TOP))

        empty = [('', 1)]
        self.assertListEqual(empty, bricks_info(BrickDetailviewLocation.LEFT))
        self.assertListEqual(empty, bricks_info(BrickDetailviewLocation.RIGHT))
        self.assertListEqual(empty, bricks_info(BrickDetailviewLocation.BOTTOM))

        # Should not have been modified
        self.assertListEqual(
            [MODELBRICK_ID, PropertiesBrick.id],
            [*BrickDetailviewLocation.objects.filter(
                content_type=None, zone=BrickDetailviewLocation.LEFT,
            ).values_list('brick_id', flat=True)],
        )

    def test_edit_detailview__empty_zones(self):
        "When no block -> fake block."
        self.login_as_root()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        bricks = [*self.brick_registry.get_compatible_bricks(model)]
        self.assertGreaterEqual(len(bricks), 5, bricks)

        create_loc = partial(BrickDetailviewLocation.objects.create, content_type=ct, order=1)
        create_loc(brick_id=bricks[0].id, zone=BrickDetailviewLocation.TOP)
        create_loc(brick_id=bricks[1].id, zone=BrickDetailviewLocation.LEFT)
        create_loc(brick_id=bricks[2].id, zone=BrickDetailviewLocation.RIGHT)
        create_loc(brick_id=bricks[3].id, zone=BrickDetailviewLocation.BOTTOM)

        url = self._build_editdetail_url(ct)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
            locations_field = fields['locations']
            locations_choices = [brick_id for (brick_id, brick) in locations_field.choices]

        brick_top_id1 = bricks[0].id
        brick_top_id2 = bricks[1].id
        self.assertDictEqual(
            {
                'top': [brick_top_id1],
                'left': [brick_top_id2],
                'right': [bricks[2].id],
                'bottom': [bricks[3].id],
            },
            locations_field.initial,
        )

        self.assertIn(brick_top_id1, locations_choices)
        self.assertIn(brick_top_id2, locations_choices)

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={'locations': json_dump({'top': [brick_top_id1, brick_top_id2]})},
        ))

        b_locs = BrickDetailviewLocation.objects.filter(content_type=ct)
        top_locations = [b_loc for b_loc in b_locs if b_loc.zone == BrickDetailviewLocation.TOP]
        self.assertEqual(2, len(top_locations))
        self.assertEqual(1, self._find_location(brick_top_id1, top_locations).order)
        self.assertEqual(2, self._find_location(brick_top_id2, top_locations).order)

        def bricks_info(zone):
            return [(bl.brick_id, bl.order) for bl in b_locs if bl.zone == zone]

        empty = [('', 1)]
        self.assertListEqual(empty, bricks_info(BrickDetailviewLocation.LEFT))
        self.assertListEqual(empty, bricks_info(BrickDetailviewLocation.RIGHT))
        self.assertListEqual(empty, bricks_info(BrickDetailviewLocation.BOTTOM))

    def test_edit_detailview__create_empty_zones(self):
        "Default conf + no empty configuration."
        self.login_as_root()
        self.assertGET404(self._build_editdetail_url(ct=None, role=self.role))

        url = self._build_editdetail_url(ct=None)
        context = self.assertGET200(url).context
        self.assertEqual(_('Edit default configuration'), context.get('title'))

        response1 = self.assertGET200(url)

        bricks = [*self.brick_registry.get_compatible_bricks(None)]
        self.assertGreaterEqual(len(bricks), 1, bricks)
        brick = bricks[0]
        brick_id = brick.id

        with self.assertNoException():
            locations_field = response1.context['form'].fields['locations']
            locations_choices = [brick_id for (brick_id, brick) in locations_field.choices]

        self.assertIn(brick_id, locations_choices)

        # ---
        self.assertNoFormError(self.client.post(
            url, data={'locations': json_dump({'top': [brick_id]})},
        ))

        b_locs = BrickDetailviewLocation.objects.filter(content_type=None)

        def bricks_info(zone):
            return [(bl.brick_id, bl.order) for bl in b_locs if bl.zone == zone]

        self.assertListEqual([(brick_id, 1)], bricks_info(BrickDetailviewLocation.TOP))

        empty = [('', 1)]
        self.assertListEqual(empty, bricks_info(BrickDetailviewLocation.LEFT))
        self.assertListEqual(empty, bricks_info(BrickDetailviewLocation.RIGHT))
        self.assertListEqual(empty, bricks_info(BrickDetailviewLocation.BOTTOM))

    def test_edit_detailview__duplicate(self):
        "Post one block several times -> validation error."
        self.login_as_root()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        url = self._build_editdetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            locations_choices = [brick_id for (brick_id, brick) in fields['locations'].choices]

        bricks = [*self.brick_registry.get_compatible_bricks(model)]
        self.assertTrue(bricks)

        def post(brick):
            brick_left_id = block_right_id = brick.id  # <= same brick !!
            self.assertIn(brick_left_id, locations_choices)
            self.assertIn(block_right_id, locations_choices)

            post_response = self.client.post(
                url,
                data={
                    'locations': json_dump(
                        {'right': [block_right_id], 'left': [brick_left_id]}
                    ),
                },
            )
            self.assertFormError(
                self.get_form_or_fail(post_response),
                field='locations',
                errors=_('The following block should be displayed only once: «%(block)s»') % {
                    'block': brick.verbose_name,
                },
            )

        modelbrick = self.brick_registry.get_brick_4_object(model)

        with self.assertNoException():
            evil_brick = next(b for b in bricks if not b.id != modelbrick.id)

        post(evil_brick)
        post(modelbrick)

    def test_edit_detailview__special_bricks(self):
        "Instance brick, RelationType brick."
        self.login_as_root()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)
        rtype = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate',
        ).symmetric(id='test-objfoo', predicate='object_predicate').get_or_create()[0]
        rbi = RelationBrickItem.objects.create(relation_type=rtype)
        naru = FakeContact.objects.create(
            user=self.user, first_name='Naru', last_name='Narusegawa',
        )
        ibci = InstanceBrickConfigItem.objects.create(
            brick_class_id=DetailviewInstanceBrick.id, entity=naru,
        )

        response = self.assertGET200(self._build_editdetail_url(ct))

        with self.assertNoException():
            fields = response.context['form'].fields
            locations_choices = [brick_id for (brick_id, brick) in fields['locations'].choices]

        self.assertIn(rbi.brick_id, locations_choices)
        self.assertIn(ibci.brick_id, locations_choices)

    def test_edit_detailview__invalid_models(self):
        self.login_as_root()
        build_url = self._build_editdetail_url
        get_ct = ContentType.objects.get_for_model
        self.assertGET409(build_url(get_ct(FakeAddress)))
        self.assertGET409(build_url(get_ct(FakeInvoiceLine)))

    def test_edit_detailview__extra_hatbrick(self):
        self.login_as_root()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        self.brick_registry.register_hat(model, secondary_brick_classes=[FakeContactHatBrick])

        url = self._build_editdetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            locations_choices = [brick_id for (brick_id, brick) in fields['locations'].choices]
            hat_f = fields['hat']
            hat_choices = hat_f.choices

        generic_id = Brick.GENERIC_HAT_BRICK_ID
        self.assertEqual(2, len(hat_choices))
        generic_index = self.assertInChoices(
            value=generic_id,
            label=_('Title bar'),
            choices=hat_choices,
        )
        self.assertEqual(0, generic_index)

        hat_index = self.assertInChoices(
            value=FakeContactHatBrick.id,
            label=FakeContactHatBrick.verbose_name,
            choices=hat_choices,
        )
        self.assertEqual(1, hat_index)

        self.assertEqual(generic_id, hat_f.initial)

        brick_top_id = CompleteBrick1.id
        self.assertIn(brick_top_id, locations_choices)
        response = self.client.post(
            url,
            data={
                'hat': FakeContactHatBrick.id,
                'locations': json_dump({'top': [brick_top_id]}),
            },
        )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(content_type=ct)

        def filter_locs(zone):
            return [bl for bl in b_locs if bl.zone == zone]

        top_locations = filter_locs(BrickDetailviewLocation.TOP)
        self.assertEqual(1, len(top_locations))
        self.assertEqual(brick_top_id, top_locations[0].brick_id)

        self.assertListEqual(
            [''],
            [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.LEFT)]
        )
        self.assertListEqual(
            [''],
            [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.RIGHT)]
        )
        self.assertListEqual(
            [''],
            [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.BOTTOM)]
        )

        hat_locations = filter_locs(BrickDetailviewLocation.HAT)
        self.assertEqual(1, len(hat_locations))
        self.assertEqual(FakeContactHatBrick.id, hat_locations[0].brick_id)

        # -----------
        response = self.assertGET200(url)

        with self.assertNoException():
            hat_f = response.context['form'].fields['hat']

        self.assertEqual(FakeContactHatBrick.id, hat_f.initial)

    @parameterized.expand([
        [{}],
        [{'locations': ""}],
        [{'locations': "{}"}],
    ])
    def test_edit_detailview__location_required(self, data):
        "Invalid data provided to the locations field."
        self.login_as_root()

        url = self._build_editdetail_url(ct=None)
        response = self.assertPOST200(url, data=data)
        self.assertFormError(
            self.get_form_or_fail(response),
            field='locations', errors=_('Your configuration is empty!'),
        )

    def test_edit_detailview__invalid_json(self):
        "Invalid data provided to the locations field."
        self.login_as_root()

        url = self._build_editdetail_url(ct=None)
        response = self.assertPOST200(url, data={'locations': "{not a dict"})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='locations', errors=_('Enter a valid JSON.'),
        )

    @parameterized.expand([
        [{'locations': "42"}],
        [{'locations': json_dump("not a dict")}],
        [{'locations': json_dump(["not a dict"])}],
        [{'locations': json_dump({"top": "lot a list"})}],
    ])
    def test_edit_detailview__invalid_formats(self, payload):
        "Invalid data provided to the locations field."
        self.login_as_root()

        url = self._build_editdetail_url(ct=None)
        response = self.assertPOST200(url, data=payload)
        self.assertFormError(
            self.get_form_or_fail(response),
            field='locations', errors=_("The value doesn't match the expected format."),
        )

    def test_delete_detailview__default(self):
        "Can not delete default configuration."
        self.login_as_root()
        self.assertPOST404(self.DEL_DETAIL_URL, data={'id': 0})

    def test_delete_detailview__default_for_ctype(self):
        "Default ContentType configuration."
        self.login_as_root()
        get_ct = ContentType.objects.get_for_model
        ct = get_ct(FakeContact)

        create_bdl = partial(
            BrickDetailviewLocation.objects.create,
            order=1, content_type=ct, zone=BrickDetailviewLocation.TOP,
        )
        locs = [
            create_bdl(brick_id=RelationsBrick.id),
            create_bdl(zone=BrickDetailviewLocation.LEFT,   brick_id=PropertiesBrick.id),
            create_bdl(zone=BrickDetailviewLocation.RIGHT,  brick_id=CustomFieldsBrick.id),
            create_bdl(zone=BrickDetailviewLocation.BOTTOM, brick_id=HistoryBrick.id),
        ]
        locs_2 = [
            create_bdl(brick_id=RelationsBrick.id, role=self.role),
            create_bdl(brick_id=RelationsBrick.id, superuser=True),
            create_bdl(brick_id=RelationsBrick.id, content_type=get_ct(FakeOrganisation)),
        ]

        self.assertPOST200(self.DEL_DETAIL_URL, data={'id': ct.id})
        self.assertFalse(
            BrickDetailviewLocation.objects.filter(id__in=[loc.id for loc in locs])
        )
        self.assertEqual(
            len(locs_2),
            BrickDetailviewLocation.objects
                                   .filter(id__in=[loc.id for loc in locs_2])
                                   .count()
        )

    def test_delete_detailview__for_role(self):
        "Role configuration."
        self.login_as_root()
        ct = self.contact_ct
        role = self.role

        create_bdl = partial(
            BrickDetailviewLocation.objects.create,
            order=1,
            content_type=self.contact_ct,
            zone=BrickDetailviewLocation.TOP,
            role=role,
        )
        locs = [
            create_bdl(brick_id=RelationsBrick.id),
            create_bdl(zone=BrickDetailviewLocation.LEFT,   brick_id=PropertiesBrick.id),
            create_bdl(zone=BrickDetailviewLocation.RIGHT,  brick_id=CustomFieldsBrick.id),
            create_bdl(zone=BrickDetailviewLocation.BOTTOM, brick_id=HistoryBrick.id),
        ]
        locs_2 = [
            create_bdl(brick_id=RelationsBrick.id, role=None),
            create_bdl(brick_id=RelationsBrick.id, superuser=True),
            create_bdl(brick_id=RelationsBrick.id, content_type=self.orga_ct),
        ]

        self.assertPOST200(self.DEL_DETAIL_URL, data={'id': ct.id, 'role': role.id})
        self.assertFalse(
            BrickDetailviewLocation.objects.filter(id__in=[loc.id for loc in locs])
        )
        self.assertEqual(
            len(locs_2),
            BrickDetailviewLocation.objects
                                   .filter(id__in=[loc.id for loc in locs_2])
                                   .count()
        )

    def test_delete_detailview__for_super_user(self):
        "Superuser configuration."
        self.login_as_root()
        ct = self.orga_ct

        create_bdl = partial(
            BrickDetailviewLocation.objects.create,
            order=1,
            content_type=ct,
            zone=BrickDetailviewLocation.TOP,
            superuser=True,
        )
        locs = [
            create_bdl(brick_id=RelationsBrick.id),
            create_bdl(zone=BrickDetailviewLocation.LEFT,   brick_id=PropertiesBrick.id),
            create_bdl(zone=BrickDetailviewLocation.RIGHT,  brick_id=CustomFieldsBrick.id),
            create_bdl(zone=BrickDetailviewLocation.BOTTOM, brick_id=HistoryBrick.id),
        ]

        locs_2 = [
            create_bdl(brick_id=RelationsBrick.id, role=self.role),
            create_bdl(brick_id=RelationsBrick.id, superuser=False),
            create_bdl(brick_id=RelationsBrick.id, content_type=self.contact_ct),
        ]

        self.assertPOST200(self.DEL_DETAIL_URL, data={'id': ct.id, 'role': 'superuser'})
        self.assertFalse(
            BrickDetailviewLocation.objects.filter(id__in=[loc.id for loc in locs])
        )
        self.assertEqual(
            len(locs_2),
            BrickDetailviewLocation.objects
                                   .filter(id__in=[loc.id for loc in locs_2])
                                   .count()
        )

    @parameterized.expand([False, True])
    def test_add_home(self, superuser):
        if superuser:
            self.login_as_root()
            role = None
        else:
            user = self.login_as_standard(admin_4_apps=['creme_core'])
            role = user.role

        self.assertFalse(BrickHomeLocation.objects.filter(role=None, superuser=False))

        url = reverse('creme_config__create_home_bricks')
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add-popup.html')

        context = response1.context
        self.assertEqual(_('Create home configuration for a role'), context.get('title'))
        self.assertEqual(_('Save the configuration'),  context.get('submit_label'))

        with self.assertNoException():
            bricks_f = context['form'].fields['bricks']
            choices = [(choice.value, label) for choice, label in bricks_f.choices]

        self.assertInChoices(
            value=CompleteBrick1.id,
            label=CompleteBrick1.verbose_name,
            choices=choices,
        )
        self.assertInChoices(
            value=HomeOnlyBrick1.id,
            label=HomeOnlyBrick1.verbose_name,
            choices=choices,
        )
        self.assertListEqual([], bricks_f.initial)

        # NB: No home_display()
        self.assertNotInChoices(value=RelationsBrick.id, choices=choices)

        # ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                'role': '' if role is None else role.id,
                'bricks': json_dump([CompleteBrick1.id, HomeOnlyBrick1.id]),
            },
        ))

        b_locs = [*BrickHomeLocation.objects.filter(role=role)]
        self.assertEqual(2, len(b_locs))

        b_loc1 = self._find_location(CompleteBrick1.id, b_locs)
        self.assertEqual(1, b_loc1.order)
        self.assertEqual(role, b_loc1.role)
        self.assertIs(b_loc1.superuser, superuser)

        self.assertEqual(2, self._find_location(HomeOnlyBrick1.id, b_locs).order)

    def test_add_home__initial(self):
        self.login_as_root()

        create_bhl = BrickHomeLocation.objects.create
        create_bhl(brick_id=CompleteBrick1.id, order=20)
        create_bhl(brick_id=HistoryBrick.id,   order=10)
        create_bhl(brick_id=HomeOnlyBrick1.id, order=30, superuser=True)  # Not used
        create_bhl(brick_id=HomeOnlyBrick2.id, order=40, role=self.role)  # Not used

        response = self.assertGET200(reverse('creme_config__create_home_bricks'))

        with self.assertNoException():
            bricks_f = response.context['form'].fields['bricks']

        self.assertListEqual([HistoryBrick.id, CompleteBrick1.id], bricks_f.initial)

    def test_add_home__ignore_used_roles(self):
        "Used roles are not proposed anymore."
        self.login_as_root()
        url = reverse('creme_config__create_home_bricks')

        role1 = self.role
        role2 = self.create_role(name='Viewer')

        def get_choices():
            response = self.assertGET200(url)
            form = self.get_form_or_fail(response)

            with self.assertNoException():
                return [*form.fields['role'].choices]

        choices = get_choices()
        self.assertInChoices(value='',       label='*{}*'.format(_('Superuser')), choices=choices)
        self.assertInChoices(value=role1.id, label=role1.name,                    choices=choices)
        self.assertInChoices(value=role2.id, label=role2.name,                    choices=choices)

        # Role ------------
        bricks = [*self.brick_registry.get_compatible_home_bricks()]
        self.assertTrue(bricks)

        create_loc = partial(BrickHomeLocation.objects.create, order=1, brick_id=bricks[0].id)
        create_loc(role=role1)

        choices = get_choices()
        self.assertInChoices(value='',       label='*{}*'.format(_('Superuser')), choices=choices)
        self.assertInChoices(value=role2.id, label=role2.name,                    choices=choices)
        self.assertNotInChoices(value=role1.id, choices=choices)

        # Superuser ------------
        create_loc(superuser=True)

        choices = get_choices()
        self.assertInChoices(value=role2.id, label=role2.name, choices=choices)
        self.assertNotInChoices(value=role1.id, choices=choices)
        self.assertNotInChoices(value='',       choices=choices)

    def test_edit_home__default_configuration(self):
        self.login_as_root()

        already_chosen = HistoryBrick
        BrickHomeLocation.objects.create(brick_id=already_chosen.id, order=8)

        # Not already chosen because they are role configuration, not the default one
        not_already_chosen1 = CompleteBrick1
        not_already_chosen2 = HomeOnlyBrick1
        BrickHomeLocation.objects.create(brick_id=not_already_chosen1.id, order=8, role=self.role)
        BrickHomeLocation.objects.create(brick_id=not_already_chosen2.id, order=8, superuser=True)

        naru = FakeContact.objects.create(
            user=self.user, first_name='Naru', last_name='Narusegawa',
        )
        ibci = InstanceBrickConfigItem.objects.create(
            brick_class_id=HomeInstanceBrick.id,
            entity=naru,
        )

        url = reverse('creme_config__edit_home_bricks', args=('default',))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit home configuration'), context.get('title'))
        self.assertEqual(_('Save the modifications'),  context.get('submit_label'))

        with self.assertNoException():
            bricks_field = context['form'].fields['bricks']
            choices = [
                (choice.value, label) for choice, label in bricks_field.choices
            ]

        initial = bricks_field.initial
        self.assertIn(already_chosen.id, initial)
        self.assertNotIn(not_already_chosen1.id, initial)
        self.assertNotIn(not_already_chosen2.id, initial)

        self.assertInChoices(
            value=already_chosen.id,
            label=already_chosen.verbose_name,
            choices=choices,
        )
        self.assertInChoices(
            value=not_already_chosen1.id,
            label=not_already_chosen1.verbose_name,
            choices=choices,
        )
        self.assertInChoices(
            value=not_already_chosen2.id,
            label=not_already_chosen2.verbose_name,
            choices=choices,
        )
        self.assertInChoices(
            value=ibci.brick_id,
            label=f'Instance brick #{ibci.brick_id} for home',
            choices=choices,
        )

        # NB: No home_display()
        self.assertNotInChoices(value=RelationsBrick.id, choices=choices)
        # NB: Brick is not configurable
        self.assertNotInChoices(value=HomeOnlyBrick2.id, choices=choices)

        response = self.client.post(
            url, data={'bricks': json_dump([not_already_chosen1.id, already_chosen.id])},
        )
        self.assertNoFormError(response)

        b_locs = [*BrickHomeLocation.objects.filter(role__isnull=True, superuser=False)]
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(not_already_chosen1.id, b_locs).order)
        self.assertEqual(2, self._find_location(already_chosen.id,      b_locs).order)

        self.assertEqual(1, BrickHomeLocation.objects.filter(role=self.role).count())
        self.assertEqual(1, BrickHomeLocation.objects.filter(superuser=True).count())

    def test_edit_home__role(self):
        self.login_as_root()
        role = self.role

        already_chosen = HistoryBrick
        BrickHomeLocation.objects.create(brick_id=already_chosen.id, order=8, role=role)

        # Not already chosen because it's the default configuration
        not_already_chosen1 = CompleteBrick1
        BrickHomeLocation.objects.create(brick_id=not_already_chosen1.id, order=8)

        # Not already chosen because it's the superuser configuration
        not_already_chosen2 = HomeOnlyBrick1
        BrickHomeLocation.objects.create(brick_id=not_already_chosen2.id, order=8, superuser=True)

        url = reverse('creme_config__edit_home_bricks', args=(role.id,))
        response = self.assertGET200(url)

        with self.assertNoException():
            bricks_field = response.context['form'].fields['bricks']
            choices = [
                (choice.value, label) for choice, label in bricks_field.choices
            ]

        initial = bricks_field.initial
        self.assertIn(already_chosen.id, initial)
        self.assertNotIn(not_already_chosen1.id, initial)
        self.assertNotIn(not_already_chosen2.id, initial)

        self.assertInChoices(
            value=already_chosen.id,
            label=already_chosen.verbose_name,
            choices=choices,
        )
        self.assertInChoices(
            value=not_already_chosen1.id,
            label=not_already_chosen1.verbose_name,
            choices=choices,
        )
        self.assertInChoices(
            value=not_already_chosen2.id,
            label=not_already_chosen2.verbose_name,
            choices=choices,
        )

        # NB: No home_display()
        self.assertNotInChoices(value=RelationsBrick.id, choices=bricks_field.choices)

        response = self.client.post(
            url, data={'bricks': json_dump([not_already_chosen1.id, already_chosen.id])},
        )
        self.assertNoFormError(response)

        b_locs = [*BrickHomeLocation.objects.filter(role=role, superuser=False)]
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(not_already_chosen1.id, b_locs).order)
        self.assertEqual(2, self._find_location(already_chosen.id,      b_locs).order)

        self.assertEqual(1, BrickHomeLocation.objects.filter(role=None, superuser=False).count())
        self.assertEqual(1, BrickHomeLocation.objects.filter(superuser=True).count())

    def test_edit_home__superuser(self):
        self.login_as_root()
        role = self.role

        already_chosen = HistoryBrick
        BrickHomeLocation.objects.create(brick_id=already_chosen.id, order=8, superuser=True)

        # Not already chosen because it's the default configuration
        not_already_chosen1 = CompleteBrick1
        BrickHomeLocation.objects.create(brick_id=not_already_chosen1.id, order=8)

        # Not already chosen because it's a role configuration
        not_already_chosen2 = HomeOnlyBrick1
        BrickHomeLocation.objects.create(brick_id=not_already_chosen2.id, order=8, role=role)

        url = reverse('creme_config__edit_home_bricks', args=('superuser',))
        response = self.assertGET200(url)

        with self.assertNoException():
            bricks_field = response.context['form'].fields['bricks']
            choices = [
                (choice.value, label) for choice, label in bricks_field.choices
            ]

        initial = bricks_field.initial
        self.assertIn(already_chosen.id, initial)
        self.assertNotIn(not_already_chosen1.id, initial)
        self.assertNotIn(not_already_chosen2.id, initial)

        self.assertInChoices(
            value=already_chosen.id,
            label=already_chosen.verbose_name,
            choices=choices,
        )
        self.assertInChoices(
            value=not_already_chosen1.id,
            label=not_already_chosen1.verbose_name,
            choices=choices,
        )
        self.assertInChoices(
            value=not_already_chosen2.id,
            label=not_already_chosen2.verbose_name,
            choices=choices,
        )

        self.assertNotInChoices(value=RelationsBrick.id, choices=choices)

        response = self.client.post(
            url, data={'bricks': json_dump([not_already_chosen2.id, not_already_chosen1.id])},
        )
        self.assertNoFormError(response)

        b_locs = [*BrickHomeLocation.objects.filter(role=None, superuser=True)]
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(not_already_chosen2.id, b_locs).order)
        self.assertEqual(2, self._find_location(not_already_chosen1.id, b_locs).order)

        self.assertEqual(1, BrickHomeLocation.objects.filter(role=None, superuser=False).count())
        self.assertEqual(1, BrickHomeLocation.objects.filter(role=role).count())

    def test_delete_home__for_role(self):
        self.login_as_root()
        role = self.role
        bricks = [
            block
            for brick_id, block in self.brick_registry
            if hasattr(block, 'home_display')
        ]
        self.assertGreaterEqual(len(bricks), 2)

        create_bhl = partial(BrickHomeLocation.objects.create, brick_id=bricks[0].id, order=1)
        bhl01 = create_bhl()
        bhl02 = create_bhl(role=role)
        bhl03 = create_bhl(superuser=True)
        bhl04 = create_bhl(role=role, brick_id=bricks[1].id, order=2)

        self.assertGET405(reverse('creme_config__delete_home_bricks'))
        self.assertGET405(reverse('creme_config__delete_home_bricks'), data={'role': role.id})
        self.assertPOST404(reverse('creme_config__delete_home_bricks'))

        self.assertPOST200(reverse('creme_config__delete_home_bricks'), data={'role': role.id})
        self.assertDoesNotExist(bhl02)
        self.assertDoesNotExist(bhl04)
        self.assertStillExists(bhl01)
        self.assertStillExists(bhl03)

    def test_delete_home__for_superuser(self):
        self.login_as_root()
        role = self.role
        bricks = [
            block
            for brick_id, block in self.brick_registry
            if hasattr(block, 'home_display')
        ]
        self.assertGreaterEqual(len(bricks), 2)

        create_bhl = partial(BrickHomeLocation.objects.create, brick_id=bricks[0].id, order=1)
        bhl01 = create_bhl()
        bhl02 = create_bhl(superuser=True)
        bhl03 = create_bhl(role=role)
        bhl04 = create_bhl(superuser=True, brick_id=bricks[1].id, order=2)

        self.assertPOST200(
            reverse('creme_config__delete_home_bricks'), data={'role': 'superuser'},
        )
        self.assertDoesNotExist(bhl02)
        self.assertDoesNotExist(bhl04)
        self.assertStillExists(bhl01)
        self.assertStillExists(bhl03)

    def test_edit_default_mypage(self):
        self.login_as_root()
        url = reverse('creme_config__edit_default_mypage_bricks')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit default "My page"'), context.get('title'))
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

        with self.assertNoException():
            bricks_field = context['form'].fields['bricks']
            choices = [
                (choice.value, label)
                for choice, label in bricks_field.choices
            ]

        self.assertGreaterEqual(len(choices), 2)
        self.assertListEqual(
            [*BrickMypageLocation.objects.filter(user=None).values_list('brick_id', flat=True)],
            bricks_field.initial,
        )

        self.assertInChoices(
            value=HomeOnlyBrick1.id,
            label=HomeOnlyBrick1.verbose_name,
            choices=choices,
        )
        self.assertInChoices(
            value=CompleteBrick1.id,
            label=CompleteBrick1.verbose_name,
            choices=choices,
        )

        response = self.client.post(
            url, data={'bricks': json_dump([HomeOnlyBrick1.id, CompleteBrick1.id])},
        )
        self.assertNoFormError(response)

        b_locs = [*BrickMypageLocation.objects.filter(user=None)]
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(HomeOnlyBrick1.id, b_locs).order)
        self.assertEqual(2, self._find_location(CompleteBrick1.id, b_locs).order)

    def test_edit_default_mypage__empty(self):
        self.login_as_root()
        url = reverse('creme_config__edit_default_mypage_bricks')

        self.assertNoFormError(self.client.post(url, data={'bricks': '[]'}))
        # TODO:
        # self.assertFalse(BrickMypageLocation.objects.filter(user=None))
        b_loc = self.get_alone_element(BrickMypageLocation.objects.filter(user=None))
        self.assertEqual('', b_loc.brick_id)

        # ---
        get_response = self.assertGET200(url)

        with self.assertNoException():
            bricks_field = get_response.context['form'].fields['bricks']
            choices = [
                (choice.value, label) for choice, label in bricks_field.choices
            ]

        self.assertInChoices(
            value=CompleteBrick1.id,
            label=CompleteBrick1.verbose_name,
            choices=choices,
        )

    def test_edit_mypage(self):
        user = self.login_as_root_and_get()
        url = reverse('creme_config__edit_mypage_bricks')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit "My page"'),         context.get('title'))
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

        with self.assertNoException():
            bricks_field = context['form'].fields['bricks']
            choices = [
                (choice.value, label) for choice, label in bricks_field.choices
            ]

        self.assertGreaterEqual(len(choices), 2)
        self.assertListEqual(
            [
                *BrickMypageLocation.objects
                                    .filter(user=None)
                                    .values_list('brick_id', flat=True),
            ],
            bricks_field.initial,
        )

        self.assertInChoices(
            value=CompleteBrick1.id,
            label=CompleteBrick1.verbose_name,
            choices=choices,
        )
        self.assertInChoices(
            value=HomeOnlyBrick1.id,
            label=HomeOnlyBrick1.verbose_name,
            choices=choices,
        )

        response = self.client.post(
            url, data={'bricks': json_dump([CompleteBrick1.id, HomeOnlyBrick1.id])},
        )
        self.assertNoFormError(response)

        b_locs = [*BrickMypageLocation.objects.filter(user=user)]
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(CompleteBrick1.id, b_locs).order)
        self.assertEqual(2, self._find_location(HomeOnlyBrick1.id, b_locs).order)

    def test_edit_mypage__empty(self):
        user = self.login_as_root_and_get()
        url = reverse('creme_config__edit_mypage_bricks')

        self.assertNoFormError(self.client.post(url, data={'bricks': '[]'}))
        # TODO:
        # self.assertFalse(BrickMypageLocation.objects.filter(user=user))
        b_loc = self.get_alone_element(BrickMypageLocation.objects.filter(user=user))
        self.assertEqual('', b_loc.brick_id)

        # ---
        get_response = self.assertGET200(url)

        with self.assertNoException():
            bricks_field = get_response.context['form'].fields['bricks']
            choices = [
                (choice.value, label) for choice, label in bricks_field.choices
            ]

        self.assertInChoices(
            value=CompleteBrick1.id,
            label=CompleteBrick1.verbose_name,
            choices=choices,
        )

    def test_edit_mypage__perms(self):
        "Not super-user."
        self.login_as_standard()
        self.assertGET200(reverse('creme_config__edit_mypage_bricks'))

    def test_delete_default_mypage(self):
        self.login_as_root()
        loc = BrickMypageLocation.objects.create(
            user=None, brick_id=HistoryBrick.id, order=1,
        )
        self.assertPOST200(
            reverse('creme_config__delete_default_mypage_bricks'),
            data={'id': loc.id},
        )
        self.assertDoesNotExist(loc)

    def test_delete_default_mypage__error(self):
        "'user' must be 'None'."
        self.login_as_root()
        loc = BrickMypageLocation.objects.create(
            user=self.user, brick_id=HistoryBrick.id, order=1,
        )
        self.assertPOST404(
            reverse('creme_config__delete_default_mypage_bricks'),
            data={'id': loc.id},
        )
        self.assertStillExists(loc)

    def test_delete_mypage(self):
        self.login_as_root()
        loc = BrickMypageLocation.objects.create(
            user=self.user, brick_id=HistoryBrick.id, order=1,
        )
        self.assertPOST200(
            reverse('creme_config__delete_mypage_bricks'), data={'id': loc.id},
        )
        self.assertDoesNotExist(loc)

    def test_delete_mypage__error(self):
        "BlockMypageLocation must belong to the user."
        self.login_as_root()
        loc = BrickMypageLocation.objects.create(
            user=self.create_user(), brick_id=HistoryBrick.id, order=1,
        )
        self.assertPOST404(
            reverse('creme_config__delete_mypage_bricks'),
            data={'id': loc.id},
        )
        self.assertStillExists(loc)

    def test_add_relationbrick(self):
        self.login_as_root()
        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject predicate',
        ).symmetric(id='test-objfoo', predicate='object predicate').get_or_create()[0]
        self.assertFalse(RelationBrickItem.objects.filter(relation_type=rt).exists())

        disabled_rt = RelationType.objects.builder(
            id='test-subbar', predicate='subject_disabled', enabled=False,
        ).symmetric(id='test-objcar', predicate='object_disabled').get_or_create()[0]

        url = reverse('creme_config__create_rtype_brick')
        context = self.assertGET200(url).context
        self.assertEqual(_('Create a type of block'), context.get('title'))
        self.assertEqual(_('Save the block'),         context.get('submit_label'))

        with self.assertNoException():
            relation_type_f = context['form'].fields['relation_type']

        rtype_ids = {*relation_type_f.queryset.values_list('id', flat=True)}
        self.assertIn(rt.id, rtype_ids)
        self.assertNotIn(disabled_rt.id, rtype_ids)

        # ---
        self.assertNoFormError(self.client.post(url, data={'relation_type': rt.id}))

        rb_item = self.get_alone_element(RelationBrickItem.objects.all())
        self.assertEqual(rt.id, rb_item.relation_type.id)
        self.assertIsNone(rb_item.get_cells(self.contact_ct))

    def test_relationbrick_add_cells(self):
        self.login_as_root()
        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='Subject predicate',
        ).symmetric(
            id='test-objfoo', predicate='Object predicate',
            models=[FakeContact, FakeOrganisation, FakeActivity],
        ).get_or_create()[0]
        rb_item = RelationBrickItem.objects.create(relation_type=rt)
        url = self._build_rbrick_addctypes_wizard_url(rb_item)

        # Step 1 ---
        response1 = self.assertGET200(url)
        context1 = response1.context
        self.assertEqual(
            _('New customised type for «{object}»').format(object=rt.predicate),
            context1.get('title'),
        )

        with self.assertNoException():
            choices = context1['form'].fields['ctype'].ctypes

        get_ct = ContentType.objects.get_for_model
        contact_ct  = self.contact_ct
        activity_ct = get_ct(FakeActivity)
        image_ct    = get_ct(FakeImage)
        self.assertIn(contact_ct,   choices)
        self.assertIn(self.orga_ct, choices)
        self.assertIn(activity_ct,  choices)
        self.assertNotIn(image_ct,  choices)

        # ---
        step_key = 'relation_c_type_brick_wizard-current_step'
        response2 = self.assertPOST200(
            url,
            data={
                step_key: '0',
                '0-ctype': contact_ct.pk,
            },
        )

        # Last step is not submitted so nothing yet in database
        rb_item = self.refresh(rb_item)
        self.assertIsNone(rb_item.get_cells(contact_ct))
        context2 = response2.context
        self.assertEqual(
            _('New customised type for «{object}»').format(object=rt.predicate),
            context2.get('title'),
        )

        with self.assertNoException():
            fields = context2['form'].fields

        self.assertIn('cells', fields)

        # ---
        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')
        field_fname = 'first_name'
        field_lname = 'last_name'
        response3 = self.client.post(
            url,
            data={
                step_key: '1',
                '1-cells': f'regular_field-{field_fname},'
                           f'regular_field-{field_lname},'
                           f'function_field-{funcfield.name}',
            },
        )
        self.assertNoFormError(response3)

        rb_item = self.refresh(rb_item)
        self.assertIsNone(rb_item.get_cells(activity_ct))

        cells = rb_item.get_cells(contact_ct)
        self.assertIsList(cells, length=3)

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_fname, cell.value)

        self.assertEqual(field_lname, cells[1].value)

        cell = cells[2]
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(funcfield.name, cell.value)

        # Used CTypes should not be proposed ---
        response4 = self.assertGET200(url)

        with self.assertNoException():
            choices = response4.context['form'].fields['ctype'].ctypes

        self.assertIn(activity_ct,   choices)  # Compatible & not used
        self.assertNotIn(image_ct,   choices)  # Still not compatible
        self.assertNotIn(contact_ct, choices)  # Used

    def test_relationbrick_add_cells__contenttype_constraint(self):
        self.login_as_root()
        rtype = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate', models=[FakeContact],
        ).symmetric(
            id='test-objfoo', predicate='object_predicate', models=[FakeOrganisation],
        ).get_or_create()[0]
        rb_item = RelationBrickItem.objects.create(relation_type=rtype)

        url = self._build_rbrick_addctypes_wizard_url(rb_item)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            choices = response1.context['form'].fields['ctype'].ctypes

        contact_ct = self.contact_ct
        self.assertIn(self.orga_ct, choices)
        self.assertNotIn(contact_ct, choices)
        self.assertNotIn(ContentType.objects.get_for_model(FakeActivity), choices)

        # ---
        response2 = self.client.post(
            url,
            data={
                'relation_c_type_brick_wizard-current_step': '0',
                '0-ctype': contact_ct.pk,
            },
        )
        self.assertFormError(
            response2.context['wizard']['form'],
            field='ctype',
            errors=_('Select a valid choice. That choice is not one of the available choices.'),
        )

    def test_relationbrick_add_cells__go_back(self):
        self.login_as_root()
        rtype = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate', models=[FakeOrganisation],
        ).symmetric(
            id='test-objfoo', predicate='object_predicate', models=[FakeContact],
        ).get_or_create()[0]
        rb_item = RelationBrickItem.objects.create(relation_type=rtype)

        url = self._build_rbrick_addctypes_wizard_url(rb_item)
        contact_ct = self.contact_ct
        self.assertPOST200(
            url,
            data={
                'relation_c_type_brick_wizard-current_step': '0',
                '0-ctype': contact_ct.pk,
            },
        )

        # Return to first step ---
        response2 = self.assertPOST200(
            url,
            data={
                'relation_c_type_brick_wizard-current_step': '1',
                'wizard_goto_step': '0',
            },
        )

        with self.assertNoException():
            choices = response2.context['form'].fields['ctype'].ctypes

        self.assertIn(contact_ct, choices)

    def test_relationbrick_add_cells__disabled_rtype(self):
        "Relation type is disabled => error."
        self.login_as_root()
        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='Subject predicate', enabled=False,
        ).symmetric(id='test-objfoo', predicate='Object predicate').get_or_create()[0]
        rb_item = RelationBrickItem.objects.create(relation_type=rt)
        self.assertGET409(self._build_rbrick_addctypes_wizard_url(rb_item))

    def test_relationbrick_edit_cells(self):
        self.login_as_root()
        ct = self.contact_ct
        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate',
        ).symmetric(id='test-objfoo', predicate='object_predicate').get_or_create()[0]

        rb_item = RelationBrickItem(relation_type=rt)
        rb_item.set_cells(ct, [])
        rb_item.save()

        self.assertGET404(self._build_rbrick_editctype_url(rb_item, FakeOrganisation))

        url = self._build_rbrick_editctype_url(rb_item, FakeContact)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context = response1.context
        self.assertEqual(
            _('Edit «{model}» configuration').format(model=ct),
            context.get('title'),
        )
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

        # ---
        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')
        field_fname = 'first_name'
        field_lname = 'last_name'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'cells': f'regular_field-{field_fname},'
                         f'regular_field-{field_lname},'
                         f'function_field-{funcfield.name}',
            },
        ))

        rb_item = self.refresh(rb_item)
        cells = rb_item.get_cells(ct)
        self.assertIsList(cells, length=3)

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_fname, cell.value)

        self.assertEqual(field_lname, cells[1].value)

        cell = cells[2]
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(funcfield.name, cell.value)

    def test_relationbrick_edit_cells__first_column_error(self):
        "Validation errors with URLField & ForeignKey."
        self.login_as_root()
        rb_item = RelationBrickItem(
            relation_type=RelationType.objects.builder(
                id='test-subfoo', predicate='subject_predicate',
            ).symmetric(id='test-objfoo', predicate='object_predicate').get_or_create()[0],
        )
        rb_item.set_cells(self.contact_ct, [])
        rb_item.save()

        url = self._build_rbrick_editctype_url(rb_item, FakeContact)

        def post(field_name, error=True):
            response = self.assertPOST200(
                url,
                data={'cells': f'regular_field-{field_name},regular_field-last_name'},
            )
            if error:
                self.assertFormError(
                    self.get_form_or_fail(response),
                    field='cells',
                    errors=_('This type of field can not be the first column.'),
                )
            else:
                self.assertNoFormError(response)

        post('url_site')
        post('email')
        post('image')
        post('image__name')
        post('civility', error=False)
        post('civility__shortcut', error=False)

    def test_relationbrick_edit_cells__first_column_error__m2m(self):
        "Validation errors with M2M."
        self.login_as_root()
        rb_item = RelationBrickItem(
            relation_type=RelationType.objects.builder(
                id='test-subfoo', predicate='subject_predicate',
            ).symmetric(id='test-objfoo', predicate='object_predicate').get_or_create()[0],
        )
        rb_item.set_cells(ContentType.objects.get_for_model(FakeEmailCampaign), [])
        rb_item.save()

        url = self._build_rbrick_editctype_url(rb_item, FakeEmailCampaign)

        def post(field_name):
            response = self.assertPOST200(
                url,
                data={'cells': f'regular_field-{field_name},regular_field-name'},
            )
            self.assertFormError(
                self.get_form_or_fail(response),
                field='cells',
                errors=_('This type of field can not be the first column.'),
            )

        post('mailing_lists')
        post('mailing_lists__name')

    def test_relationbrick_edit_cells__first_column_error__rtype(self):
        "Validation errors with Relation."
        self.login_as_root()
        rt1 = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate1',
        ).symmetric(id='test-objfoo', predicate='object_predicate2').get_or_create()[0]
        rt2 = RelationType.objects.builder(
            id='test-subbar', predicate='subject_predicate2',
        ).symmetric(id='test-objbar', predicate='object_predicate2').get_or_create()[0]

        rb_item = RelationBrickItem(relation_type=rt1)
        rb_item.set_cells(self.orga_ct, [])
        rb_item.save()

        response = self.assertPOST200(
            self._build_rbrick_editctype_url(rb_item, FakeOrganisation),
            data={'cells': f'relation-{rt2.id},regular_field-name'},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='cells',
            errors=_('This type of field can not be the first column.'),
        )

    def test_relationbrick_edit_cells__fields_config(self):
        self.login_as_root()
        ct = self.contact_ct
        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate',
        ).symmetric(id='test-objfoo', predicate='object_predicate').get_or_create()[0]

        valid_fname = 'last_name'
        hidden_fname1 = 'phone'
        hidden_fname2 = 'birthday'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        rb_item = RelationBrickItem(relation_type=rt)
        build_cell = EntityCellRegularField.build
        rb_item.set_cells(ct, [build_cell(FakeContact, hidden_fname1)])
        rb_item.save()

        url = self._build_rbrick_editctype_url(rb_item, FakeContact)
        response = self.assertPOST200(
            url,
            data={
                'cells': f'regular_field-{valid_fname},'
                         f'regular_field-{hidden_fname1},'
                         f'regular_field-{hidden_fname2}',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='cells',
            errors=_('This value is invalid: %(value)s') % {'value': hidden_fname2},
        )

        self.assertNoFormError(self.client.post(
            url,
            data={
                'cells': f'regular_field-{valid_fname},'
                         f'regular_field-{hidden_fname1}',
            },
        ))

        rb_item = self.refresh(rb_item)
        self.assertEqual(2, len(rb_item.get_cells(ct)))

    def test_relationbrick_edit_cells__disabled_rtype(self):
        "Relation type is disabled => errors."
        self.login_as_root()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate1', enabled=False,
        ).symmetric(id='test-objfoo', predicate='object_predicate2').get_or_create()[0]

        rb_item = RelationBrickItem(relation_type=rt)
        rb_item.set_cells(self.orga_ct, [])
        rb_item.save()

        self.assertGET409(
            self._build_rbrick_editctype_url(rb_item, FakeOrganisation),
        )

    def test_relationbrick_delete_cells(self):
        self.login_as_root()

        ct = self.contact_ct
        rb_item = RelationBrickItem(
            relation_type=RelationType.objects.builder(
                id='test-subfoo', predicate='subject_predicate',
            ).symmetric(id='test-objfoo', predicate='object_predicate').get_or_create()[0],
        )
        rb_item.set_cells(ct, [EntityCellRegularField.build(FakeContact, 'first_name')])
        rb_item.save()

        url = reverse('creme_config__delete_cells_of_rtype_brick', args=(rb_item.id,))
        self.assertPOST404(url, data={'id': self.orga_ct.id})

        data = {'id': ct.id}
        self.assertGET405(url, data=data)  # Only POST

        self.assertPOST200(url, data=data)
        self.assertIsNone(self.refresh(rb_item).get_cells(ct))

    def test_delete_relationbrick(self):
        self.login_as_root()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate',  # NB: is_custom == False,
        ).symmetric(id='test-objfoo', predicate='object_predicate').get_or_create()[0]
        rbi = RelationBrickItem.objects.create(relation_type=rt)

        create_state = partial(BrickState.objects.create, user=self.user)
        state1 = create_state(brick_id=rbi.brick_id)
        state2 = create_state(brick_id=CompleteBrick1.id)

        self.assertPOST200(
            reverse('creme_config__delete_rtype_brick'),
            data={'id': rbi.id},
        )
        self.assertDoesNotExist(rbi)
        self.assertDoesNotExist(state1)
        self.assertStillExists(state2)

    def test_delete_relationbrick__error(self):
        "Cannot delete because it is used."
        self.login_as_root()

        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate',  # NB: is_custom == False,
        ).symmetric(id='test-objfoo', predicate='object_predicate').get_or_create()[0]
        rbi = RelationBrickItem.objects.create(relation_type=rt)

        url = reverse('creme_config__delete_rtype_brick')
        data = {'id': rbi.id}

        BrickDetailviewLocation.objects.create_if_needed(
            brick=rbi.brick_id,
            model=FakeContact, role=self.role,
            zone=BrickDetailviewLocation.RIGHT, order=5,
        )

        response = self.client.post(url, data=data)
        self.assertContains(
            response,
            status_code=409,
            text=_(
                'This block is used in the detail-view configuration of '
                '«{model}» for role «{role}»'
            ).format(model='Test Contact', role=self.role),
            html=True,
        )

    def test_delete_instancebrick(self):
        self.login_as_root()
        user = self.user
        naru = FakeContact.objects.create(
            user=user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=DetailviewInstanceBrick.id,
            entity=naru,
        )

        create_state = BrickState.objects.create
        state1 = create_state(brick_id=ibi.brick_id,      user=user)
        state2 = create_state(brick_id=CompleteBrick1.id, user=user)

        self.assertPOST200(
            reverse('creme_config__delete_instance_brick'),
            data={'id': ibi.id},
        )
        self.assertDoesNotExist(ibi)
        self.assertDoesNotExist(state1)
        self.assertStillExists(state2)

    def test_delete_instancebrick__error(self):
        "Cannot delete because it is used in configuration."
        self.login_as_root()
        naru = FakeContact.objects.create(
            user=self.user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=DetailviewInstanceBrick.id,
            entity=naru,
        )
        BrickDetailviewLocation.objects.create_if_needed(
            zone=BrickDetailviewLocation.RIGHT, model=FakeContact,
            brick=ibi.brick_id, order=5,
        )

        response = self.client.post(
            reverse('creme_config__delete_instance_brick'),
            data={'id': ibi.id},
        )
        self.assertContains(
            response,
            status_code=409,
            text=_(
                'This block is used in the detail-view configuration of «{model}»'
            ).format(model='Test Contact'),
            html=True,
        )

    def test_edit_custombrick(self):
        self.login_as_root()
        ct = self.contact_ct

        loves = RelationType.objects.builder(
            id='test-subject_love', predicate='Is loving',
        ).symmetric(id='test-object_love',  predicate='Is loved by').get_or_create()[0]
        customfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=ct,
        )
        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')

        name = 'info'
        cbc_item = CustomBrickConfigItem.objects.create(
            # id='tests-contacts1',
            content_type=ct, name=name,
        )

        url = self._build_custombrick_edit_url(cbc_item)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Edit the block «{object}»').format(object=cbc_item),
            response.context.get('title'),
        )

        # ---
        name = name.title()
        field_lname = 'last_name'
        field_subname = 'address__city'
        self.assertNoFormError(self.client.post(
            url, follow=True,
            data={
                'name':  name,
                'cells': f'regular_field-{field_lname},'
                         f'regular_field-{field_subname},'
                         f'relation-{loves.id},'
                         f'function_field-{funcfield.name},'
                         f'custom_field-{customfield.id}',
            },
        ))

        cbc_item = self.refresh(cbc_item)
        self.assertEqual(name, cbc_item.name)

        cells = cbc_item.cells
        self.assertIsList(cells, length=5)

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_lname, cell.value)

        self.assertEqual(field_subname, cells[1].value)

        cell = cells[2]
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(loves.id, cell.value)

        cell = cells[3]
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(funcfield.name, cell.value)

        cell = cells[4]
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(str(customfield.id), cell.value)

    def test_edit_custombrick__fields_config(self):
        self.login_as_root()
        ct = self.contact_ct

        valid_fname = 'last_name'
        hidden_fname = 'phone'
        hidden_fkname = 'image'
        hidden_subfname = 'zipcode'

        create_fconf = FieldsConfig.objects.create
        create_fconf(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname,  {FieldsConfig.HIDDEN: True}),
                (hidden_fkname, {FieldsConfig.HIDDEN: True}),
            ],
        )
        create_fconf(
            content_type=FakeAddress,
            descriptions=[(hidden_subfname, {FieldsConfig.HIDDEN: True})],
        )

        cbc_item = CustomBrickConfigItem.objects.create(
            # id='tests-contacts1',
            name='Contact info',
            content_type=ct,
        )

        url = self._build_custombrick_edit_url(cbc_item)

        response1 = self.assertPOST200(
            url, follow=True,
            data={
                'name':  cbc_item.name,
                'cells': f'regular_field-{valid_fname},'
                         f'regular_field-{hidden_fname}',
            },
        )
        msg_fmt = _('This value is invalid: %(value)s')
        self.assertFormError(
            response1.context['form'],
            field='cells', errors=msg_fmt % {'value': hidden_fname},
        )

        # ---------------------------
        prefix = 'address__'

        response2 = self.assertPOST200(
            url, follow=True,
            data={
                'name':  cbc_item.name,
                'cells': f'regular_field-{valid_fname},'
                         f'regular_field-{prefix}{hidden_subfname}',
            },
        )
        self.assertFormError(
            response2.context['form'],
            field='cells', errors=msg_fmt % {'value': prefix + hidden_subfname},
        )

        # ----------------------------
        response3 = self.assertPOST200(
            url, follow=True,
            data={
                'name':  cbc_item.name,
                'cells': f'regular_field-{valid_fname},'
                         f'regular_field-{hidden_fkname}',
            },
        )
        self.assertFormError(
            response3.context['form'],
            field='cells', errors=msg_fmt % {'value': hidden_fkname},
        )

    def test_edit_custombrick__used_hidden_field(self):
        "With FieldsConfig + field in the blocks becomes hidden => still proposed in the form."
        self.login_as_root()
        ct = self.contact_ct

        valid_fname = 'last_name'
        hidden_fname1 = 'phone'
        hidden_fname2 = 'mobile'

        hidden_fkname = 'image__description'

        addr_prefix = 'address__'
        hidden_subfname1 = 'zipcode'
        hidden_subfname2 = 'country'

        create_fconf = FieldsConfig.objects.create
        create_fconf(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
                ('image',       {FieldsConfig.HIDDEN: True}),
            ],
        )
        create_fconf(
            content_type=FakeAddress,
            descriptions=[
                (hidden_subfname1, {FieldsConfig.HIDDEN: True}),
                (hidden_subfname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        build_cell = EntityCellRegularField.build
        cbc_item = CustomBrickConfigItem.objects.create(
            name='Contact info', content_type=ct,
            cells=[
                build_cell(FakeContact, valid_fname),
                build_cell(FakeContact, hidden_fname1),
                build_cell(FakeContact, addr_prefix + hidden_subfname1),
                build_cell(FakeContact, hidden_fkname),
            ],
        )

        url = self._build_custombrick_edit_url(cbc_item)
        rf_prefix = 'regular_field-'
        response = self.client.post(
            url, follow=True,
            data={
                'name':  cbc_item.name,
                'cells': ','.join(
                    rf_prefix + fname
                    for fname in (
                        valid_fname,
                        hidden_fname1,  # was already in the block => still proposed
                        addr_prefix + hidden_subfname1,  # idem
                        hidden_fkname,
                    )
                ),
            },
        )
        self.assertNoFormError(response)
        self.assertListEqual(
            [
                build_cell(FakeContact, valid_fname),
                build_cell(FakeContact, hidden_fname1),
                build_cell(FakeContact, addr_prefix + hidden_subfname1),
                build_cell(FakeContact, hidden_fkname),
            ],
            self.refresh(cbc_item).cells,
        )

    def test_delete_custombrick(self):
        self.login_as_root()

        cbci = CustomBrickConfigItem.objects.create(content_type=self.contact_ct, name='Info')
        self.assertPOST200(
            reverse('creme_config__delete_custom_brick'),
            data={'id': cbci.id},
        )
        self.assertDoesNotExist(cbci)

    def test_delete_custombrick__error(self):
        "Cannot delete because it is used."
        self.login_as_root()

        cbci = CustomBrickConfigItem.objects.create(content_type=self.contact_ct, name='Info')
        loc = BrickDetailviewLocation.objects.create_if_needed(
            brick=cbci.brick_id, order=5,
            model=FakeContact,
            zone=BrickDetailviewLocation.RIGHT,
        )

        response = self.client.post(
            reverse('creme_config__delete_custom_brick'),
            data={'id': cbci.id},
        )
        self.assertContains(
            response,
            status_code=409,
            text=_(
                'This block is used in the detail-view configuration of «{model}»'
            ).format(model='Test Contact'),
            html=True,
        )
        self.assertStillExists(cbci)
        self.assertStillExists(loc)

    def test_custombrick_wizard_model_step(self):
        self.login_as_root()

        contact_ct = self.contact_ct
        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

        ctxt1 = self.assertGET200(self.CUSTOM_WIZARD_URL).context
        self.assertEqual(_('New custom block'), ctxt1.get('title'))

        with self.assertNoException():
            ctypes = ctxt1['form'].fields['ctype'].ctypes
        self.assertIn(contact_ct, ctypes)

        response2 = self.assertPOST200(
            self.CUSTOM_WIZARD_URL,
            data={
                'custom_brick_wizard-current_step': '0',
                '0-ctype': contact_ct.pk,
                '0-name': 'foobar',
            },
        )

        ctxt2 = response2.context
        self.assertIn('cells', ctxt2['form'].fields)

        # last step is not submitted so nothing yet in database
        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

    def test_custombrick_wizard_model_step__invalid(self):
        self.login_as_root()

        contact_ct = self.contact_ct
        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

        response1 = self.assertGET200(self.CUSTOM_WIZARD_URL)
        self.assertIn(contact_ct, response1.context['form'].fields['ctype'].ctypes)

        response2 = self.assertPOST200(
            self.CUSTOM_WIZARD_URL,
            data={
                'custom_brick_wizard-current_step': '0',
                '0-ctype': 'unknown',
                '0-name': 'foobar',
            },
        )
        self.assertFormError(
            response2.context['wizard']['form'],
            field='ctype',
            errors=_('Select a valid choice. That choice is not one of the available choices.'),
        )
        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

    def test_custombrick_wizard_config_step(self):
        self.login_as_root()

        contact_ct = self.contact_ct
        contact_customfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=contact_ct,
        )

        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

        response1 = self.assertGET200(self.CUSTOM_WIZARD_URL)
        self.assertIn(contact_ct, response1.context['form'].fields['ctype'].ctypes)

        response2 = self.assertPOST200(
            self.CUSTOM_WIZARD_URL,
            data={
                'custom_brick_wizard-current_step': '0',
                '0-ctype': contact_ct.pk,
                '0-name': 'foobar',
            },
        )
        self.assertEqual(
            _('New custom block for «{model}»').format(model=contact_ct),
            response2.context.get('title'),
        )

        response3 = self.assertPOST200(
            self.CUSTOM_WIZARD_URL,
            data={
                'custom_brick_wizard-current_step': '1',
                '1-cells': f'regular_field-first_name,'
                           f'custom_field-{contact_customfield.id}',
            },
        )
        self.assertNoFormError(response3)

        cbci = self.get_object_or_fail(CustomBrickConfigItem, content_type=contact_ct)
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, 'first_name'),
                EntityCellCustomField(contact_customfield),
            ],
            cbci.cells,
        )

    def test_custombrick_wizard_go_back(self):
        self.login_as_root()

        contact_ct = self.contact_ct
        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

        response = self.assertGET200(self.CUSTOM_WIZARD_URL)
        self.assertIn(contact_ct, self.get_form_or_fail(response).fields['ctype'].ctypes)

        response = self.assertPOST200(
            self.CUSTOM_WIZARD_URL,
            data={
                'custom_brick_wizard-current_step': '0',
                '0-ctype': contact_ct.pk,
                '0-name': 'foobar',
            },
        )
        self.assertIn('cells', self.get_form_or_fail(response).fields)

        # Return to first step
        response = self.assertPOST200(
            self.CUSTOM_WIZARD_URL,
            data={
                'custom_brick_wizard-current_step': '1',
                'wizard_goto_step': '0',
            },
        )
        self.assertIn(contact_ct, self.get_form_or_fail(response).fields['ctype'].ctypes)

    def test_BrickDetailviewLocationsBrick(self):
        role = self.role

        contact_ct = ContentType.objects.get_for_model(FakeContact)
        create_loc = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            model=contact_ct, zone=BrickDetailviewLocation.LEFT,
        )
        create_loc(brick=PropertiesBrick, order=1)
        create_loc(brick=PropertiesBrick, order=1, role='superuser')
        create_loc(brick=HistoryBrick,    order=2, role='superuser')
        create_loc(brick=PropertiesBrick, order=3, role=role)
        create_loc(brick=HistoryBrick,    order=3, role=role)
        create_loc(brick=RelationsBrick,  order=3, role=role)

        context = self.build_context(user=self.user)

        ContentType.objects.get_for_models(
            *creme_registry.iter_entity_models()
        )  # Fill cache

        # Queries:
        #   - COUNT UserRoles
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        #   - BrickDetailviewLocations
        #   - UserRoles
        #   - COUNT BrickDetailviewLocations for default configuration
        with self.assertNumQueries(6):
            render = bricks.BrickDetailviewLocationsBrick().detailview_display(context)

        brick_node = self.get_brick_node(
            self.get_html_tree(render), brick=bricks.BrickDetailviewLocationsBrick,
        )

        # Default config ---
        default_group_node = self.get_html_node_or_fail(
            brick_node, './/div[@class="brickloc-config-group brickloc-config-summary-group"]'
        )
        self.assertBrickHasAction(default_group_node, url=self._build_editdetail_url())

        # FakeContact config ---
        contact_group_node = self.get_html_node_or_fail(
            brick_node,
            './/div[@class="'
            'brick-list-item '
            'brickloc-config-item '
            'brickloc-config-item-creme_core-fakecontact'
            '"]'
        )

        contact_tbody = self.get_html_node_or_fail(
            contact_group_node,
            './/div[@class="brickloc-config-group brick-table"]/table/tbody'
        )
        contact_rows = contact_tbody.findall('.//tr')
        self.assertEqual(3, len(contact_rows))

        # ---
        contact_def_row = contact_rows.pop(0)
        self.assertEqual(
            _('Default configuration for «%(ctype)s»') % {'ctype': 'Test Contact'},
            self.get_html_node_or_fail(
                contact_def_row, './/td[@class="brickloc-config-role"]',
            ).text,
        )
        self.assertEqual(
            ngettext('%(count)s block', '%(count)s blocks', 1) % {'count': 1},
            self.get_html_node_or_fail(
                contact_def_row, './/td[@class="brickloc-config-count"]',
            ).text.strip(),
        )
        self.assertBrickHasAction(contact_def_row, url=self._build_editdetail_url(ct=contact_ct))

        # ---
        contact_rows_per_title = {
            tr_node.find('.//td').text: tr_node
            for tr_node in contact_rows
        }

        contact_super_row = contact_rows_per_title.get(_('Superuser'))
        self.get_html_node_or_fail(
            contact_super_row,
            './/td[@class="brickloc-config-role brickloc-config-role-superuser"]',
        )
        self.assertEqual(
            ngettext('%(count)s block', '%(count)s blocks', 2) % {'count': 2},
            self.get_html_node_or_fail(
                contact_super_row, './/td[@class="brickloc-config-count"]',
            ).text.strip(),
        )
        self.assertBrickHasAction(
            contact_super_row,
            url=self._build_editdetail_url(ct=contact_ct, superuser=True),
        )

        # ---
        contact_role_row = contact_rows_per_title.get(role.name)
        self.get_html_node_or_fail(
            contact_role_row, './/td[@class="brickloc-config-role"]',
        )
        self.assertEqual(
            ngettext('%(count)s block', '%(count)s blocks', 3) % {'count': 3},
            self.get_html_node_or_fail(
                contact_role_row, './/td[@class="brickloc-config-count"]',
            ).text.strip(),
        )
        self.assertBrickHasAction(
            contact_role_row,
            url=self._build_editdetail_url(ct=contact_ct, role=role),
        )
        self.assertBrickHasAction(
            contact_role_row, url=self.DEL_DETAIL_URL, action_type='delete',
        )

    def test_BrickHomeLocationsBrick(self):
        self.login_as_root()
        self.assertFalse(BrickHomeLocation.objects.filter(
            Q(role__isnull=False) | Q(superuser=False)
        ))

        existing_roles = [*UserRole.objects.all()]
        self.assertEqual(1, len(existing_roles))

        brick_id = bricks.BrickHomeLocationsBrick.id
        button_url = reverse('creme_config__create_home_bricks')
        button_label = _('Add a home configuration for a role')

        # TODO: render only the brick, not the whole page ?
        url = reverse('creme_config__bricks')
        response1 = self.assertGET200(url)
        brick_node1 = self.get_brick_node(
            self.get_html_tree(response1.content), brick_id,
        )
        self.assertBrickHeaderHasButton(
            self.get_brick_header_buttons(brick_node1),
            url=button_url, label=button_label,
        )

        # ---
        BrickHomeLocation.objects.create(
            superuser=True, brick_id=HomeOnlyBrick1.id, order=1,
        )
        response2 = self.assertGET200(url)
        brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content), brick_id,
        )
        self.assertBrickHeaderHasButton(
            self.get_brick_header_buttons(brick_node2),
            url=button_url, label=button_label,
        )

        # ---
        BrickHomeLocation.objects.create(
            role=existing_roles[0], brick_id=HomeOnlyBrick1.id, order=1,
        )
        response3 = self.assertGET200(url)
        brick_node3 = self.get_brick_node(
            self.get_html_tree(response3.content), brick_id,
        )
        self.assertBrickHeaderHasNoButton(
            self.get_brick_header_buttons(brick_node3), url=button_url,
        )

        # ---
        role2 = self.create_role(name='CEO')
        response4 = self.assertGET200(url)
        brick_node4 = self.get_brick_node(
            self.get_html_tree(response4.content), brick_id,
        )
        self.assertBrickHeaderHasButton(
            self.get_brick_header_buttons(brick_node4),
            url=button_url, label=button_label,
        )

        # ---
        BrickHomeLocation.objects.create(
            role=role2, brick_id=HomeOnlyBrick1.id, order=1,
        )
        response5 = self.assertGET200(url)
        brick_node5 = self.get_brick_node(
            self.get_html_tree(response5.content), brick_id,
        )
        self.assertBrickHeaderHasNoButton(
            self.get_brick_header_buttons(brick_node5), url=button_url,
        )

        # TODO: test paginator count (title)

    # TODO: test
    #  - bricks.BrickHomeLocationsBrick
    #  - bricks.BrickDefaultMypageLocationsBrick
    #  - bricks.RelationBricksConfigBrick
    #  - bricks.InstanceBricksConfigBrick
    #  - bricks.CustomBricksConfigBrick
