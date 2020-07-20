# -*- coding: utf-8 -*-

from copy import deepcopy
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_config import bricks
from creme.creme_core.bricks import (
    CustomFieldsBrick,
    HistoryBrick,
    PropertiesBrick,
    RelationsBrick,
)
from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.gui import bricks as gui_bricks
from creme.creme_core.gui.bricks import (
    Brick,
    InstanceBrick,
    SpecificRelationsBrick,
)
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickMypageLocation,
    BrickState,
    CustomBrickConfigItem,
    CustomField,
    FieldsConfig,
    InstanceBrickConfigItem,
    RelationBrickItem,
    RelationType,
    UserRole,
)
from creme.creme_core.registry import creme_registry
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_models import (
    FakeActivity,
    FakeAddress,
    FakeContact,
    FakeEmailCampaign,
    FakeImage,
    FakeInvoiceLine,
    FakeOrganisation,
)


# Test Bricks ------------------------------------------------------------------
class _BaseCompleteBrick(Brick):
    verbose_name = 'Testing purpose'

    def detailview_display(self, context):
        return f'<table id="{self.id_}"></table>'

    def home_display(self, context):
        return f'<table id="{self.id_}"></table>'


class CompleteBrick1(_BaseCompleteBrick):
    id_ = Brick.generate_id('creme_config', 'testbrickconfig_complete_1')
    verbose_name = 'Complete brick #1'


class CompleteBrick2(_BaseCompleteBrick):
    id_ = Brick.generate_id('creme_config', 'testbrickconfig_complete_2')
    verbose_name = 'Complete brick #2'


class CompleteBrick3(_BaseCompleteBrick):
    id_ = Brick.generate_id('creme_config', 'testbrickconfig_complete_3')
    verbose_name = 'Complete brick #3'


class CompleteBrick4(_BaseCompleteBrick):
    id_ = Brick.generate_id('creme_config', 'testbrickconfig_complete_4')
    verbose_name = 'Complete brick #4'


# class HomePortalBrick(Brick):
#     id_          = Brick.generate_id('creme_config', 'testbrickconfig_home_portal')
#     verbose_name = 'Home/portal brick'
#
#     # def detailview_display(self, context): NO
#
#     def home_display(self, context):
#         return f'<table id="{self.id_}"></table>'


class HomeOnlyBrick1(Brick):
    id_          = Brick.generate_id('creme_config', 'testbrickconfig_home_only_1')
    verbose_name = 'Home only brick #1'

    # def detailview_display(self, context): NO

    def home_display(self, context):
        return f'<table id="{self.id_}"></table>'


class HomeOnlyBrick2(Brick):
    id_          = Brick.generate_id('creme_config', 'testbrickconfig_home_only_2')
    verbose_name = 'Home only brick #2'
    configurable = False  # <----

    # def detailview_display(self, context): NO

    def home_display(self, context):
        return f'<table id="{self.id_}"></table>'


# class DetailviewInstanceBrick(Brick):
class DetailviewInstanceBrick(InstanceBrick):
    id_ = InstanceBrickConfigItem.generate_base_id('creme_config', 'test_detail_instance')

    # def __init__(self, instance_block_config_item):
    #     super().__init__()
    #     self.ibci = instance_block_config_item
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose_name = f'Instance brick #{self.id_} for detail-view'

    def detailview_display(self, context):
        # return f'<table id="{self.id_}"><thead><tr>{self.ibci.entity}</tr></thead></table>'
        return f'<table id="{self.id_}"><thead><tr>{self.config_item.entity}</tr></thead></table>'


# class HomeInstanceBrick(Brick):
class HomeInstanceBrick(InstanceBrick):
    id_          = InstanceBrickConfigItem.generate_base_id('creme_config', 'test_home_instance')
    verbose_name = 'Testing purpose'

    # def __init__(self, instance_block_config_item):
    #     super().__init__()
    #     self.ibci = instance_block_config_item
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose_name = f'Instance brick #{self.id_} for home'

    def home_display(self, context):
        # return f'<table id="{self.id_}"><thead><tr>{self.ibci.entity}</tr></thead></table>'
        return f'<table id="{self.id_}"><thead><tr>{self.config_item.entity}</tr></thead></table>'


class FakeContactHatBrick(Brick):
    id_ = Brick._generate_hat_id('creme_core', 'test_hat_brick')
    verbose_name = 'Fake contact header brick'

    def detailview_display(self, context):
        return f'<table id="{self.id_}"></table>'


# Test case --------------------------------------------------------------------

class BricksConfigTestCase(CremeTestCase):
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

        cls.brick_registry = brick_registry = deepcopy(gui_bricks.brick_registry)
        brick_registry.register(
            CompleteBrick1, CompleteBrick2, CompleteBrick3, CompleteBrick4,
            # HomePortalBrick,
            HomeOnlyBrick1,
            HomeOnlyBrick2,
        )

        brick_registry.register_4_instance(DetailviewInstanceBrick)
        brick_registry.register_4_instance(HomeInstanceBrick)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        BrickDetailviewLocation.objects.all().delete()
        BrickHomeLocation.objects.all().delete()
        BrickMypageLocation.objects.all().delete()
        RelationBrickItem.objects.all().delete()

        for model, backup in [(BrickDetailviewLocation, cls._bdl_backup),
                              (BrickHomeLocation, cls._bpl_backup),
                              (BrickMypageLocation, cls._bml_backup),
                              (RelationBrickItem, cls._rbi_backup),
                             ]:
            try:
                model.objects.bulk_create(backup)
            except Exception:
                print(
                    'CremeBlockTagsTestCase: '
                    'test-data backup problem with model={}'.format(model)
                )

        gui_bricks.brick_registry = cls._original_brick_registry

    def setUp(self):
        super().setUp()
        gui_bricks.brick_registry = self.brick_registry = deepcopy(self.brick_registry)

    def _build_adddetail_url(self, ct):
        return reverse('creme_config__create_detailviews_bricks', args=(ct.id,))

    def _build_editdetail_url(self, ct=None, role=None, superuser=False):
        return reverse('creme_config__edit_detailview_bricks', args=(
            ct.id if ct else 0,
            'superuser' if superuser else role.id if role else 'default',
        ))

    def _build_rbrick_addctypes_wizard_url(self, rbi):
        return reverse('creme_config__add_cells_to_rtype_brick', args=(rbi.id,))

    def _build_rbrick_editctype_url(self, rbi, model):
        return reverse(
            'creme_config__edit_cells_of_rtype_brick',
            args=(rbi.id, ContentType.objects.get_for_model(model).id,),
        )

    def _build_custombrick_edit_url(self, cbc_item):
        return reverse('creme_config__edit_custom_brick', args=(cbc_item.id,))

    # def _find_field_index(self, formfield, name):
    #     for i, (fname, fvname) in enumerate(formfield.choices):
    #         if fname == name:
    #             return i
    #
    #     self.fail(f'No "{name}" field')

    def _find_location(self, brick_id, locations):
        for location in locations:
            if location.brick_id == brick_id:
                return location

        self.fail('No "{}" in locations ({})'.format(
            brick_id,
            [location.brick_id for location in locations],
        ))

    def test_portal(self):
        self.login()
        response = self.assertGET200(reverse('creme_config__bricks'))
        self.assertTemplateUsed(response, 'creme_config/bricks_portal.html')
        self.assertEqual(reverse('creme_core__reload_bricks'),
                         response.context.get('bricks_reload_url')
                        )

        fmt = 'id="{}"'.format
        self.assertContains(response, fmt(bricks.BrickDetailviewLocationsBrick.id_))
        self.assertContains(response, fmt(bricks.BrickHomeLocationsBrick.id_))
        self.assertContains(response, fmt(bricks.BrickDefaultMypageLocationsBrick.id_))
        self.assertContains(response, fmt(bricks.RelationBricksConfigBrick.id_))
        self.assertContains(response, fmt(bricks.InstanceBricksConfigBrick.id_))
        self.assertContains(response, fmt(bricks.CustomBricksConfigBrick.id_))

    def _aux_test_add_detailview(self, role=None, superuser=False):
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        url = self._build_adddetail_url(ct)
        context = self.assertGET200(url).context
        self.assertEqual(
            _('New block configuration for «{model}»').format(model='Test Contact'),
            context.get('title')
        )
        self.assertEqual(_('Save the configuration'), context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields
            top_choices    = fields['top'].choices
            left_choices   = fields['left'].choices
            right_choices  = fields['right'].choices
            bottom_choices = fields['bottom'].choices

        self.assertNotIn('hat', fields)

        bricks = [*self.brick_registry.get_compatible_bricks(model)]
        self.assertGreaterEqual(len(bricks), 5)
        self.assertInChoices(
            value=CompleteBrick1.id_,
            label=CompleteBrick1.verbose_name,
            choices=top_choices,
        )

        brick_top1   = bricks[0]
        brick_top2   = bricks[1]
        brick_left1  = bricks[2]
        brick_left2  = self.brick_registry.get_brick_4_object(model)
        brick_right  = bricks[3]
        brick_bottom = bricks[4]

        brick_top_index1 = self.assertInChoices(
            value=brick_top1.id_,
            label=brick_top1.verbose_name,
            choices=top_choices,
        )
        brick_top_index2 = self.assertInChoices(
            value=brick_top2.id_,
            label=brick_top2.verbose_name,
            choices=top_choices,
        )
        brick_left_index1 = self.assertInChoices(
            value=brick_left1.id_,
            label=brick_left1.verbose_name,
            choices=left_choices,
        )
        brick_left_index2 = self.assertInChoices(
            value=brick_left2.id_,
            label=brick_left2.verbose_name,
            choices=left_choices,
        )
        brick_right_index = self.assertInChoices(
            value=brick_right.id_,
            label=brick_right.verbose_name,
            choices=right_choices,
        )
        brick_bottom_index = self.assertInChoices(
            value=brick_bottom.id_,
            label=brick_bottom.verbose_name,
            choices=bottom_choices,
        )

        response = self.client.post(
            url,
            data={
                'role': role.id if role else '',

                f'top_check_{brick_top_index1}': 'on',
                f'top_value_{brick_top_index1}': brick_top1.id_,
                f'top_order_{brick_top_index1}': 1,

                f'top_check_{brick_top_index2}': 'on',
                f'top_value_{brick_top_index2}': brick_top2.id_,
                f'top_order_{brick_top_index2}': 2,

                f'left_check_{brick_left_index1}': 'on',
                f'left_value_{brick_left_index1}': brick_left1.id_,
                f'left_order_{brick_left_index1}': 1,

                f'left_check_{brick_left_index2}': 'on',
                f'left_value_{brick_left_index2}': brick_left2.id_,
                f'left_order_{brick_left_index2}': 2,

                f'right_check_{brick_right_index}': 'on',
                f'right_value_{brick_right_index}': brick_right.id_,
                f'right_order_{brick_right_index}': 1,

                f'bottom_check_{brick_bottom_index}': 'on',
                f'bottom_value_{brick_bottom_index}': brick_bottom.id_,
                f'bottom_order_{brick_bottom_index}': 1,
            },
        )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(
            content_type=ct, role=role, superuser=superuser,
        )

        def filter_locs(zone):
            return [bl for bl in b_locs if bl.zone == zone]

        locations = filter_locs(BrickDetailviewLocation.TOP)
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(brick_top1.id_, locations).order)
        self.assertEqual(2, self._find_location(brick_top2.id_, locations).order)

        locations = filter_locs(BrickDetailviewLocation.LEFT)
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(brick_left1.id_, locations).order)
        self.assertEqual(2, self._find_location(brick_left2.id_, locations).order)

        locations = filter_locs(BrickDetailviewLocation.RIGHT)
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(brick_right.id_, locations).order)

        locations = filter_locs(BrickDetailviewLocation.BOTTOM)
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(brick_bottom.id_, locations).order)

        self.assertListEqual(
            [''],
            [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.HAT)]
        )

    def test_add_detailview01(self):
        self.login(is_superuser=False, admin_4_apps=['creme_core'])
        self._aux_test_add_detailview(role=self.role, superuser=False)

    def test_add_detailview02(self):
        self.login()
        self._aux_test_add_detailview(role=None, superuser=True)

    def test_add_detailview03(self):
        "Used roles are not proposed anymore."
        self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)
        url = self._build_adddetail_url(ct)

        role1 = self.role
        role2 = UserRole.objects.create(name='Viewer')

        def get_choices():
            response = self.assertGET200(url)

            with self.assertNoException():
                return [*response.context['form'].fields['role'].choices]

        choices = get_choices()
        self.assertInChoices(value='',       label='*{}*'.format(_('Superuser')), choices=choices)
        self.assertInChoices(value=role1.id, label=role1.name,                    choices=choices)
        self.assertInChoices(value=role2.id, label=role2.name,                    choices=choices)

        # Role ------------
        bricks = [*self.brick_registry.get_compatible_bricks(model)]
        self.assertGreaterEqual(len(bricks), 5, bricks)

        create_loc = partial(BrickDetailviewLocation.objects.create, content_type=ct, order=1)
        create_loc(role=role1, brick_id=bricks[0].id_, zone=BrickDetailviewLocation.TOP)
        create_loc(role=role1, brick_id=bricks[1].id_, zone=BrickDetailviewLocation.LEFT)
        create_loc(role=role1, brick_id=bricks[2].id_, zone=BrickDetailviewLocation.RIGHT)
        create_loc(role=role1, brick_id=bricks[3].id_, zone=BrickDetailviewLocation.BOTTOM)

        choices = get_choices()
        self.assertInChoices(value='',       label='*{}*'.format(_('Superuser')), choices=choices)
        self.assertInChoices(value=role2.id, label=role2.name,                    choices=choices)
        self.assertNotInChoices(value=role1.id, choices=choices)

        # Superuser ------------
        create_loc(superuser=True, brick_id=bricks[0].id_, zone=BrickDetailviewLocation.TOP)
        create_loc(superuser=True, brick_id=bricks[1].id_, zone=BrickDetailviewLocation.LEFT)
        create_loc(superuser=True, brick_id=bricks[2].id_, zone=BrickDetailviewLocation.RIGHT)
        create_loc(superuser=True, brick_id=bricks[3].id_, zone=BrickDetailviewLocation.BOTTOM)

        choices = get_choices()
        self.assertInChoices(value=role2.id, label=role2.name, choices=choices)
        self.assertNotInChoices(value=role1.id, choices=choices)
        self.assertNotInChoices(value='',       choices=choices)

    def test_add_detailview04(self):
        "Un-configurable models"
        self.login()
        get_ct = ContentType.objects.get_for_model

        build_url = self._build_adddetail_url
        self.assertGET409(build_url(get_ct(FakeAddress)))  # Not a CremeEntity

        model = FakeInvoiceLine
        self.assertIn(model, creme_registry.iter_entity_models())
        self.assertGET409(build_url(get_ct(model)))

    def test_add_detailview05(self):
        "Extra HatBrick."
        self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        self.brick_registry.register_hat(model, secondary_brick_classes=[FakeContactHatBrick])

        url = self._build_adddetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            top_choices = fields['top'].choices
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
            value=FakeContactHatBrick.id_,
            label=FakeContactHatBrick.verbose_name,
            choices=hat_choices,
        )
        self.assertEqual(1, hat_index)

        self.assertEqual(generic_brick_id, hat_f.initial)

        brick_top_index = self.assertInChoices(
            value=CompleteBrick1.id_,
            label=CompleteBrick1.verbose_name,
            choices=top_choices,
        )
        response = self.client.post(
            url,
            data={
                'hat': FakeContactHatBrick.id_,

                f'top_check_{brick_top_index}': 'on',
                f'top_value_{brick_top_index}': CompleteBrick1.id_,
                f'top_order_{brick_top_index}': 1,
            },
        )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(content_type=ct, role=None, superuser=True)

        def filter_locs(zone):
            return [bl for bl in b_locs if bl.zone == zone]

        top_locations = filter_locs(BrickDetailviewLocation.TOP)
        self.assertEqual(1, len(top_locations))
        self.assertEqual(CompleteBrick1.id_, top_locations[0].brick_id)

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
        self.assertEqual(FakeContactHatBrick.id_, hat_locations[0].brick_id)

    def test_add_detailview06(self):
        "Admin credentials are needed"
        self.login(is_superuser=False)
        self.assertGET403(
            self._build_adddetail_url(ContentType.objects.get_for_model(FakeContact))
        )

    def _aux_test_edit_detailview(
            self, role=None, superuser=False, expected_title='Edit the bricks'):
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        url = self._build_editdetail_url(ct, role, superuser)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(expected_title,              context.get('title'))
        self.assertEqual(_('Save the configuration'), context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields
            top_choices    = fields['top'].choices
            left_choices   = fields['left'].choices
            right_choices  = fields['right'].choices
            bottom_choices = fields['bottom'].choices

        bricks = [*self.brick_registry.get_compatible_bricks(model)]
        self.assertGreaterEqual(len(bricks), 5)
        self.assertInChoices(
            value=CompleteBrick1.id_,
            label=CompleteBrick1.verbose_name,
            choices=top_choices,
        )

        # self.assertNotInChoices(value=HomePortalBrick.id_, choices=top_choices)
        self.assertNotInChoices(value=HomeOnlyBrick1.id_, choices=top_choices)

        brick_top1   = bricks[0]
        brick_top2   = bricks[1]
        brick_left1  = self.brick_registry.get_brick_4_object(model)
        brick_left2  = bricks[2]
        brick_right  = bricks[3]
        brick_bottom = bricks[4]

        brick_top_index1 = self.assertInChoices(
            value=brick_top1.id_,
            label=brick_top1.verbose_name,
            choices=top_choices,
        )
        brick_top_index2 = self.assertInChoices(
            value=brick_top2.id_,
            label=brick_top2.verbose_name,
            choices=top_choices,
        )
        brick_left_index1 = self.assertInChoices(
            value=brick_left1.id_,
            label=brick_left1.verbose_name,
            choices=left_choices,
        )
        brick_left_index2 = self.assertInChoices(
            value=brick_left2.id_,
            label=brick_left2.verbose_name,
            choices=left_choices,
        )
        brick_right_index = self.assertInChoices(
            value=brick_right.id_,
            label=brick_right.verbose_name,
            choices=right_choices,
        )
        brick_bottom_index = self.assertInChoices(
            value=brick_bottom.id_,
            label=brick_bottom.verbose_name,
            choices=bottom_choices,
        )

        response = self.client.post(
            url,
            data={
                f'top_check_{brick_top_index1}': 'on',
                f'top_value_{brick_top_index1}': brick_top1.id_,
                f'top_order_{brick_top_index1}': 1,

                f'top_check_{brick_top_index2}': 'on',
                f'top_value_{brick_top_index2}': brick_top2.id_,
                f'top_order_{brick_top_index2}': 2,

                f'left_check_{brick_left_index1}': 'on',
                f'left_value_{brick_left_index1}': brick_left1.id_,
                f'left_order_{brick_left_index1}': 1,

                f'left_check_{brick_left_index2}': 'on',
                f'left_value_{brick_left_index2}': brick_left2.id_,
                f'left_order_{brick_left_index2}': 2,

                f'right_check_{brick_right_index}': 'on',
                f'right_value_{brick_right_index}': brick_right.id_,
                f'right_order_{brick_right_index}': 1,

                f'bottom_check_{brick_bottom_index}': 'on',
                f'bottom_value_{brick_bottom_index}': brick_bottom.id_,
                f'bottom_order_{brick_bottom_index}': 1,
            },
        )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(
            content_type=ct, role=role, superuser=superuser,
        )

        def filter_locs(zone):
            return [bl for bl in b_locs if bl.zone == zone]

        locations = filter_locs(BrickDetailviewLocation.TOP)
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(brick_top1.id_, locations).order)
        self.assertEqual(2, self._find_location(brick_top2.id_, locations).order)

        locations = filter_locs(BrickDetailviewLocation.LEFT)
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(brick_left1.id_, locations).order)
        self.assertEqual(2, self._find_location(brick_left2.id_, locations).order)

        locations = filter_locs(BrickDetailviewLocation.RIGHT)
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(brick_right.id_, locations).order)

        locations = filter_locs(BrickDetailviewLocation.BOTTOM)
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(brick_bottom.id_, locations).order)

        self.assertListEqual(
            [''],
            [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.HAT)]
        )

    def test_edit_detailview01(self):
        "Default configuration of a ContentType."
        self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)
        brick_id = [*self.brick_registry.get_compatible_bricks(model)][0].id_

        # These bricks should not be modified
        create_loc = partial(BrickDetailviewLocation.objects.create,
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

    def test_edit_detailview02(self):
        "Configuration for a role"
        self.login()
        self._aux_test_edit_detailview(
            role=self.role, superuser=False,
            expected_title=_('Edit configuration of «{role}» for «{model}»').format(
                role=self.role,
                model=FakeContact._meta.verbose_name,
            ),
        )

    def test_edit_detailview03(self):
        "Configuration for superusers"
        self.login()
        self._aux_test_edit_detailview(
            role=None, superuser=True,
            expected_title=_('Edit configuration of super-users for «{model}»').format(
                model=FakeContact._meta.verbose_name,
            )
        )

    def test_edit_detailview04(self):
        "When no block -> fake block."
        self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        bricks = [*self.brick_registry.get_compatible_bricks(model)]
        self.assertGreaterEqual(len(bricks), 5, bricks)

        create_loc = partial(BrickDetailviewLocation.objects.create, content_type=ct, order=1)
        create_loc(brick_id=bricks[0].id_, zone=BrickDetailviewLocation.TOP)
        create_loc(brick_id=bricks[1].id_, zone=BrickDetailviewLocation.LEFT)
        create_loc(brick_id=bricks[2].id_, zone=BrickDetailviewLocation.RIGHT)
        create_loc(brick_id=bricks[3].id_, zone=BrickDetailviewLocation.BOTTOM)

        url = self._build_editdetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            top_field    = fields['top']
            left_field   = fields['left']
            right_field  = fields['right']
            bottom_field = fields['bottom']

        brick_top_id1 = bricks[0].id_
        brick_top_id2 = bricks[1].id_

        self.assertEqual([brick_top_id1], top_field.initial)
        self.assertEqual([brick_top_id2], left_field.initial)
        self.assertEqual([bricks[2].id_], right_field.initial)
        self.assertEqual([bricks[3].id_], bottom_field.initial)

        brick_top_index1 = self.assertInChoices(
            value=brick_top_id1, label=bricks[0].verbose_name, choices=top_field.choices,
        )
        brick_top_index2 = self.assertInChoices(
            value=brick_top_id2, label=bricks[1].verbose_name, choices=top_field.choices,
        )

        response = self.client.post(
            url,
            data={
                f'top_check_{brick_top_index1}': 'on',
                f'top_value_{brick_top_index1}': brick_top_id1,
                f'top_order_{brick_top_index1}': 1,

                f'top_check_{brick_top_index2}': 'on',
                f'top_value_{brick_top_index2}': brick_top_id2,
                f'top_order_{brick_top_index2}': 2,
            },
        )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(content_type=ct)
        locations = [b_loc for b_loc in b_locs if b_loc.zone == BrickDetailviewLocation.TOP]
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(brick_top_id1, locations).order)
        self.assertEqual(2, self._find_location(brick_top_id2, locations).order)

        def bricks_info(zone):
            return [(bl.brick_id, bl.order) for bl in b_locs if bl.zone == zone]

        self.assertListEqual([('', 1)], bricks_info(BrickDetailviewLocation.LEFT))
        self.assertListEqual([('', 1)], bricks_info(BrickDetailviewLocation.RIGHT))
        self.assertListEqual([('', 1)], bricks_info(BrickDetailviewLocation.BOTTOM))

    def test_edit_detailview05(self):
        "Default conf + no empty configuration."
        self.login()
        self.assertGET404(self._build_editdetail_url(ct=None, role=self.role))

        url = self._build_editdetail_url(ct=None)
        context = self.assertGET200(url).context
        self.assertEqual(_('Edit default configuration'), context.get('title'))

        response = self.assertPOST200(url, data={})
        self.assertFormError(response, 'form', None,
                             _('Your configuration is empty !')
                            )

        bricks = [*self.brick_registry.get_compatible_bricks(None)]
        self.assertGreaterEqual(len(bricks), 1, bricks)
        brick = bricks[0]
        brick_id = brick.id_

        with self.assertNoException():
            top_choices = response.context['form'].fields['top'].choices

        index = self.assertInChoices(
            value=brick_id,
            label=brick.verbose_name,
            choices=top_choices,
        )
        response = self.client.post(
            url,
            data={
                f'top_check_{index}': 'on',
                f'top_value_{index}': brick_id,
                f'top_order_{index}': 1,
            },
        )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(content_type=None)

        def bricks_info(zone):
            return [(bl.brick_id, bl.order) for bl in b_locs if bl.zone == zone]

        self.assertListEqual([(brick_id, 1)], bricks_info(BrickDetailviewLocation.TOP))
        self.assertListEqual([('', 1)], bricks_info(BrickDetailviewLocation.LEFT))
        self.assertListEqual([('', 1)], bricks_info(BrickDetailviewLocation.RIGHT))
        self.assertListEqual([('', 1)], bricks_info(BrickDetailviewLocation.BOTTOM))

    def test_edit_detailview06(self):
        "Post one block several times -> validation error."
        self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        url = self._build_editdetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            left_field  = fields['left']
            right_field = fields['right']

        bricks = [*self.brick_registry.get_compatible_bricks(model)]
        self.assertTrue(bricks)

        def post(brick):
            brick_left_id = block_right_id = brick.id_  # <= same block !!
            brick_left_index = self.assertInChoices(
                value=brick_left_id, label=brick.verbose_name, choices=left_field.choices,
            )
            brick_right_index = self.assertInChoices(
                value=block_right_id, label=brick.verbose_name, choices=right_field.choices,
            )

            response = self.client.post(
                url,
                data={
                    f'right_check_{brick_right_index}': 'on',
                    f'right_value_{brick_right_index}': block_right_id,
                    f'right_order_{brick_right_index}': 1,

                    f'left_check_{brick_left_index}': 'on',
                    f'left_value_{brick_left_index}': brick_left_id,
                    f'left_order_{brick_left_index}': 1,
                },
            )
            self.assertFormError(
                response, 'form', field=None,
                errors=_('The following block should be displayed only once: «%(block)s»') % {
                    'block': brick.verbose_name,
                },
            )

        modelbrick = self.brick_registry.get_brick_4_object(model)

        with self.assertNoException():
            evil_brick = next((b for b in bricks if not b.id_ != modelbrick.id_))

        post(evil_brick)
        post(modelbrick)

    def test_edit_detailview07(self):
        "Instance brick, RelationType brick."
        user = self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        rtype = RelationType.create(
            ('test-subfoo', 'subject_predicate'),
            ('test-objfoo', 'object_predicate'),
        )[0]

        rtype_brick_id = SpecificRelationsBrick.generate_id('test', 'foobar')
        RelationBrickItem.objects.create(brick_id=rtype_brick_id, relation_type=rtype)

        naru = FakeContact.objects.create(user=user, first_name='Naru', last_name='Narusegawa')

        # instance_brick_id = InstanceBrickConfigItem.generate_id(
        #     DetailviewInstanceBrick, naru, '')
        ibci = InstanceBrickConfigItem.objects.create(
            # brick_id=instance_brick_id,
            brick_class_id=DetailviewInstanceBrick.id_,
            entity=naru,
            # verbose='All stuffes',
        )

        response = self.assertGET200(self._build_editdetail_url(ct))

        with self.assertNoException():
            # top_field = response.context['form'].fields['top']
            top_choices = response.context['form'].fields['top'].choices

        # choices = [brick_id for brick_id, brick_vname in top_field.choices]
        # self.assertIn(rtype_brick_id,    choices)
        # self.assertIn(instance_brick_id, choices)
        self.assertInChoices(
            rtype_brick_id,
            label=_('Relationship block: «{predicate}»').format(predicate=rtype.predicate),
            choices=top_choices,
        )
        self.assertInChoices(
            ibci.brick_id,
            label=f'Instance brick #{ibci.brick_id} for detail-view',
            choices=top_choices,
        )

    def test_edit_detailview08(self):
        "Invalid models."
        self.login()
        build_url = self._build_editdetail_url
        get_ct = ContentType.objects.get_for_model
        self.assertGET409(build_url(get_ct(FakeAddress)))
        self.assertGET409(build_url(get_ct(FakeInvoiceLine)))

    def test_edit_detailview09(self):
        "Extra HatBrick."
        self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        self.brick_registry.register_hat(model, secondary_brick_classes=[FakeContactHatBrick])

        url = self._build_editdetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            top_choices = fields['top'].choices
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
            value=FakeContactHatBrick.id_,
            label=FakeContactHatBrick.verbose_name,
            choices=hat_choices,
        )
        self.assertEqual(1, hat_index)

        self.assertEqual(generic_id, hat_f.initial)

        brick_top_id = CompleteBrick1.id_
        brick_top_index = self.assertInChoices(
            value=brick_top_id,
            label=CompleteBrick1.verbose_name,
            choices=top_choices,
        )
        response = self.client.post(
            url,
            data={
                'hat': FakeContactHatBrick.id_,

                f'top_check_{brick_top_index}': 'on',
                f'top_value_{brick_top_index}': brick_top_id,
                f'top_order_{brick_top_index}': 1,
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
        self.assertEqual(FakeContactHatBrick.id_, hat_locations[0].brick_id)

        # -----------
        response = self.assertGET200(url)

        with self.assertNoException():
            hat_f = response.context['form'].fields['hat']

        self.assertEqual(FakeContactHatBrick.id_, hat_f.initial)

    def test_delete_detailview01(self):
        "Can not delete default conf"
        self.login()
        self.assertPOST404(self.DEL_DETAIL_URL, data={'id': 0})

    def test_delete_detailview02(self):
        "Default ContentType configuration"
        self.login()
        get_ct = ContentType.objects.get_for_model
        ct = get_ct(FakeContact)

        create_bdl = partial(BrickDetailviewLocation.objects.create, order=1,
                             content_type=ct, zone=BrickDetailviewLocation.TOP,
                            )
        locs = [
            create_bdl(brick_id=RelationsBrick.id_),
            create_bdl(zone=BrickDetailviewLocation.LEFT,   brick_id=PropertiesBrick.id_),
            create_bdl(zone=BrickDetailviewLocation.RIGHT,  brick_id=CustomFieldsBrick.id_),
            create_bdl(zone=BrickDetailviewLocation.BOTTOM, brick_id=HistoryBrick.id_),
        ]
        locs_2 = [
            create_bdl(brick_id=RelationsBrick.id_, role=self.role),
            create_bdl(brick_id=RelationsBrick.id_, superuser=True),
            create_bdl(brick_id=RelationsBrick.id_, content_type=get_ct(FakeOrganisation)),
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

    def test_delete_detailview03(self):
        "Role configuration."
        self.login()
        get_ct = ContentType.objects.get_for_model
        ct = get_ct(FakeContact)
        role = self.role

        create_bdl = partial(
            BrickDetailviewLocation.objects.create,
            order=1,
            content_type=ct,
            zone=BrickDetailviewLocation.TOP,
            role=role,
        )
        locs = [
            create_bdl(brick_id=RelationsBrick.id_),
            create_bdl(zone=BrickDetailviewLocation.LEFT,   brick_id=PropertiesBrick.id_),
            create_bdl(zone=BrickDetailviewLocation.RIGHT,  brick_id=CustomFieldsBrick.id_),
            create_bdl(zone=BrickDetailviewLocation.BOTTOM, brick_id=HistoryBrick.id_),
        ]
        locs_2 = [
            create_bdl(brick_id=RelationsBrick.id_, role=None),
            create_bdl(brick_id=RelationsBrick.id_, superuser=True),
            create_bdl(brick_id=RelationsBrick.id_, content_type=get_ct(FakeOrganisation)),
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

    def test_delete_detailview04(self):
        "Superuser configuration."
        self.login()
        get_ct = ContentType.objects.get_for_model
        ct = get_ct(FakeOrganisation)

        create_bdl = partial(
            BrickDetailviewLocation.objects.create,
            order=1,
            content_type=ct,
            zone=BrickDetailviewLocation.TOP,
            superuser=True,
        )
        locs = [
            create_bdl(brick_id=RelationsBrick.id_),
            create_bdl(zone=BrickDetailviewLocation.LEFT,   brick_id=PropertiesBrick.id_),
            create_bdl(zone=BrickDetailviewLocation.RIGHT,  brick_id=CustomFieldsBrick.id_),
            create_bdl(zone=BrickDetailviewLocation.BOTTOM, brick_id=HistoryBrick.id_),
        ]

        locs_2 = [
            create_bdl(brick_id=RelationsBrick.id_, role=self.role),
            create_bdl(brick_id=RelationsBrick.id_, superuser=False),
            create_bdl(brick_id=RelationsBrick.id_, content_type=get_ct(FakeContact)),
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

    def _aux_test_add_home(self, role=None, superuser=False):
        url = reverse('creme_config__create_home_bricks')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(_('Create home configuration for a role'), context.get('title'))
        self.assertEqual(_('Save the configuration'),  context.get('submit_label'))

        with self.assertNoException():
            choices = context['form'].fields['bricks'].choices

        index1 = self.assertInChoices(
            value=CompleteBrick1.id_,
            label=CompleteBrick1.verbose_name,
            choices=choices,
        )
        index2 = self.assertInChoices(
            value=HomeOnlyBrick1.id_,
            label=HomeOnlyBrick1.verbose_name,
            choices=choices,
        )
        # self._find_field_index(bricks_field, HomePortalBrick.id_)

        # NB: No home_display()
        self.assertNotInChoices(value=RelationsBrick.id_, choices=choices)

        response = self.client.post(
            url,
            data={
                'role': '' if role is None else role.id,

                f'bricks_check_{index1}': 'on',
                f'bricks_value_{index1}': CompleteBrick1.id_,
                f'bricks_order_{index1}': 1,

                f'bricks_check_{index2}': 'on',
                f'bricks_value_{index2}': HomeOnlyBrick1.id_,
                f'bricks_order_{index2}': 2,
            },
        )
        self.assertNoFormError(response)

        b_locs = [*BrickHomeLocation.objects.filter(role=role)]
        self.assertEqual(2, len(b_locs))

        b_loc1 = self._find_location(CompleteBrick1.id_, b_locs)
        self.assertEqual(1, b_loc1.order)
        self.assertEqual(role, b_loc1.role)
        self.assertIs(b_loc1.superuser, superuser)

        self.assertEqual(2, self._find_location(HomeOnlyBrick1.id_, b_locs).order)

    def test_add_home01(self):
        "Role."
        self.login()
        self._aux_test_add_home(role=self.role, superuser=False)

    def test_add_home02(self):
        "Superuser."
        self.login()
        self._aux_test_add_home(superuser=True)

    def test_add_home03(self):
        "Used roles are not proposed anymore."
        self.login()
        url = reverse('creme_config__create_home_bricks')

        role1 = self.role
        role2 = UserRole.objects.create(name='Viewer')

        def get_choices():
            response = self.assertGET200(url)

            with self.assertNoException():
                return [*response.context['form'].fields['role'].choices]

        choices = get_choices()
        self.assertInChoices(value='',       label='*{}*'.format(_('Superuser')), choices=choices)
        self.assertInChoices(value=role1.id, label=role1.name,                    choices=choices)
        self.assertInChoices(value=role2.id, label=role2.name,                    choices=choices)

        # Role ------------
        bricks = [*self.brick_registry.get_compatible_home_bricks()]
        self.assertTrue(bricks)

        create_loc = partial(BrickHomeLocation.objects.create, order=1, brick_id=bricks[0].id_)
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

    # def test_edit_home(self):
    def test_edit_home01(self):
        "Default configuration."
        user = self.login()

        already_chosen = HistoryBrick
        BrickHomeLocation.objects.create(brick_id=already_chosen.id_, order=8)

        # Not already chosen because they are role configuration, not the default one
        not_already_chosen1 = CompleteBrick1
        not_already_chosen2 = HomeOnlyBrick1
        BrickHomeLocation.objects.create(brick_id=not_already_chosen1.id_, order=8, role=self.role)
        BrickHomeLocation.objects.create(brick_id=not_already_chosen2.id_, order=8, superuser=True)

        naru = FakeContact.objects.create(user=user, first_name='Naru', last_name='Narusegawa')
        # instance_brick_id = InstanceBrickConfigItem.generate_id(HomeInstanceBrick, naru, '')
        ibci = InstanceBrickConfigItem.objects.create(
            # brick_id=instance_brick_id,
            brick_class_id=HomeInstanceBrick.id_,
            entity=naru,
            # verbose='All stuffes',
        )

        url = reverse('creme_config__edit_home_bricks', args=('default',))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit home configuration'), context.get('title'))
        self.assertEqual(_('Save the modifications'),  context.get('submit_label'))

        with self.assertNoException():
            bricks_field = context['form'].fields['bricks']
            choices = bricks_field.choices

        initial = bricks_field.initial
        self.assertIn(already_chosen.id_, initial)
        self.assertNotIn(not_already_chosen1.id_, initial)
        self.assertNotIn(not_already_chosen2.id_, initial)

        index2 = self.assertInChoices(
            value=already_chosen.id_,
            label=already_chosen.verbose_name,
            choices=choices,
        )
        index1 = self.assertInChoices(
            value=not_already_chosen1.id_,
            label=not_already_chosen1.verbose_name,
            choices=choices,
        )
        self.assertInChoices(
            value=not_already_chosen2.id_,
            label=not_already_chosen2.verbose_name,
            choices=choices,
        )
        # self._find_field_index(bricks_field, HomePortalBrick.id_)
        # self._find_field_index(bricks_field, instance_brick_id)
        self.assertInChoices(
            value=ibci.brick_id,
            label=f'Instance brick #{ibci.brick_id} for home',
            choices=choices,
        )

        # NB: No home_display()
        self.assertNotInChoices(value=RelationsBrick.id_, choices=choices)
        # NB: Brick is not configurable
        self.assertNotInChoices(value=HomeOnlyBrick2.id_, choices=choices)

        response = self.client.post(
            url,
            data={
                f'bricks_check_{index1}': 'on',
                f'bricks_value_{index1}': not_already_chosen1.id_,
                f'bricks_order_{index1}': 1,

                f'bricks_check_{index2}': 'on',
                f'bricks_value_{index2}': already_chosen.id_,
                f'bricks_order_{index2}': 2,
            },
        )
        self.assertNoFormError(response)

        b_locs = [*BrickHomeLocation.objects.filter(role__isnull=True, superuser=False)]
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(not_already_chosen1.id_, b_locs).order)
        self.assertEqual(2, self._find_location(already_chosen.id_,      b_locs).order)

        self.assertEqual(1, BrickHomeLocation.objects.filter(role=self.role).count())
        self.assertEqual(1, BrickHomeLocation.objects.filter(superuser=True).count())

    def test_edit_home02(self):
        "Role."
        self.login()
        role = self.role

        already_chosen = HistoryBrick
        BrickHomeLocation.objects.create(brick_id=already_chosen.id_, order=8, role=role)

        # Not already chosen because it's the default configuration
        not_already_chosen1 = CompleteBrick1
        BrickHomeLocation.objects.create(brick_id=not_already_chosen1.id_, order=8)

        # Not already chosen because it's the superuser configuration
        not_already_chosen2 = HomeOnlyBrick1
        BrickHomeLocation.objects.create(brick_id=not_already_chosen2.id_, order=8, superuser=True)

        url = reverse('creme_config__edit_home_bricks', args=(role.id,))
        response = self.assertGET200(url)

        with self.assertNoException():
            bricks_field = response.context['form'].fields['bricks']
            choices = bricks_field.choices

        initial = bricks_field.initial
        self.assertIn(already_chosen.id_, initial)
        self.assertNotIn(not_already_chosen1.id_, initial)
        self.assertNotIn(not_already_chosen2.id_, initial)

        index2 = self.assertInChoices(
            value=already_chosen.id_,
            label=already_chosen.verbose_name,
            choices=choices,
        )
        index1 = self.assertInChoices(
            value=not_already_chosen1.id_,
            label=not_already_chosen1.verbose_name,
            choices=choices,
        )
        self.assertInChoices(
            value=not_already_chosen2.id_,
            label=not_already_chosen2.verbose_name,
            choices=choices,
        )

        # NB: No home_display()
        self.assertNotInChoices(value=RelationsBrick.id_, choices=bricks_field.choices)

        response = self.client.post(
            url,
            data={
                f'bricks_check_{index1}': 'on',
                f'bricks_value_{index1}': not_already_chosen1.id_,
                f'bricks_order_{index1}': 1,

                f'bricks_check_{index2}': 'on',
                f'bricks_value_{index2}': already_chosen.id_,
                f'bricks_order_{index2}': 2,
            },
        )
        self.assertNoFormError(response)

        b_locs = [*BrickHomeLocation.objects.filter(role=role, superuser=False)]
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(not_already_chosen1.id_, b_locs).order)
        self.assertEqual(2, self._find_location(already_chosen.id_,      b_locs).order)

        self.assertEqual(1, BrickHomeLocation.objects.filter(role=None, superuser=False).count())
        self.assertEqual(1, BrickHomeLocation.objects.filter(superuser=True).count())

    def test_edit_home03(self):
        "Superuser."
        self.login()
        role = self.role

        already_chosen = HistoryBrick
        BrickHomeLocation.objects.create(brick_id=already_chosen.id_, order=8, superuser=True)

        # Not already chosen because it's the default configuration
        not_already_chosen1 = CompleteBrick1
        BrickHomeLocation.objects.create(brick_id=not_already_chosen1.id_, order=8)

        # Not already chosen because it's a role configuration
        not_already_chosen2 = HomeOnlyBrick1
        BrickHomeLocation.objects.create(brick_id=not_already_chosen2.id_, order=8, role=role)

        url = reverse('creme_config__edit_home_bricks', args=('superuser',))
        response = self.assertGET200(url)

        with self.assertNoException():
            bricks_field = response.context['form'].fields['bricks']
            choices = bricks_field.choices

        initial = bricks_field.initial
        self.assertIn(already_chosen.id_, initial)
        self.assertNotIn(not_already_chosen1.id_, initial)
        self.assertNotIn(not_already_chosen2.id_, initial)

        self.assertInChoices(
            value=already_chosen.id_,
            label=already_chosen.verbose_name,
            choices=choices,
        )
        index2 = self.assertInChoices(
            value=not_already_chosen1.id_,
            label=not_already_chosen1.verbose_name,
            choices=choices,
        )
        index1 = self.assertInChoices(
            value=not_already_chosen2.id_,
            label=not_already_chosen2.verbose_name,
            choices=choices,
        )

        self.assertNotInChoices(value=RelationsBrick.id_, choices=choices)

        response = self.client.post(
            url,
            data={
                f'bricks_check_{index1}': 'on',
                f'bricks_value_{index1}': not_already_chosen2.id_,
                f'bricks_order_{index1}': 1,

                f'bricks_check_{index2}': 'on',
                f'bricks_value_{index2}': not_already_chosen1.id_,
                f'bricks_order_{index2}': 2,
            },
        )
        self.assertNoFormError(response)

        b_locs = [*BrickHomeLocation.objects.filter(role=None, superuser=True)]
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(not_already_chosen2.id_, b_locs).order)
        self.assertEqual(2, self._find_location(not_already_chosen1.id_, b_locs).order)

        self.assertEqual(1, BrickHomeLocation.objects.filter(role=None, superuser=False).count())
        self.assertEqual(1, BrickHomeLocation.objects.filter(role=role).count())

    def test_delete_home01(self):
        "Role."
        self.login()
        role = self.role
        bricks = [
            block
            for brick_id, block in self.brick_registry
            if hasattr(block, 'home_display')
        ]
        self.assertGreaterEqual(len(bricks), 2)

        create_bhl = partial(BrickHomeLocation.objects.create, brick_id=bricks[0].id_, order=1)
        bhl01 = create_bhl()
        bhl02 = create_bhl(role=role)
        bhl03 = create_bhl(superuser=True)
        bhl04 = create_bhl(role=role, brick_id=bricks[1].id_, order=2)

        self.assertGET405(reverse('creme_config__delete_home_brick'))
        self.assertGET405(reverse('creme_config__delete_home_brick'), data={'role': role.id})
        self.assertPOST404(reverse('creme_config__delete_home_brick'))

        self.assertPOST200(reverse('creme_config__delete_home_brick'), data={'role': role.id})
        self.assertDoesNotExist(bhl02)
        self.assertDoesNotExist(bhl04)
        self.assertStillExists(bhl01)
        self.assertStillExists(bhl03)

    def test_delete_home02(self):
        "Superuser"
        self.login()
        role = self.role
        bricks = [
            block
            for brick_id, block in self.brick_registry
            if hasattr(block, 'home_display')
        ]
        self.assertGreaterEqual(len(bricks), 2)

        create_bhl = partial(BrickHomeLocation.objects.create, brick_id=bricks[0].id_, order=1)
        bhl01 = create_bhl()
        bhl02 = create_bhl(superuser=True)
        bhl03 = create_bhl(role=role)
        bhl04 = create_bhl(superuser=True, brick_id=bricks[1].id_, order=2)

        self.assertPOST200(reverse('creme_config__delete_home_brick'), data={'role': 'superuser'})
        self.assertDoesNotExist(bhl02)
        self.assertDoesNotExist(bhl04)
        self.assertStillExists(bhl01)
        self.assertStillExists(bhl03)

    def test_edit_default_mypage(self):
        self.login()
        url = reverse('creme_config__edit_default_mypage_bricks')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit default "My page"'), context.get('title'))
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

        with self.assertNoException():
            bricks_field = context['form'].fields['bricks']
            choices = bricks_field.choices

        self.assertGreaterEqual(len(choices), 2)
        self.assertListEqual(
            [*BrickMypageLocation.objects.filter(user=None).values_list('brick_id', flat=True)],
            bricks_field.initial
        )

        index1 = self.assertInChoices(
            value=HomeOnlyBrick1.id_,
            label=HomeOnlyBrick1.verbose_name,
            choices=choices,
        )
        index2 = self.assertInChoices(
            value=CompleteBrick1.id_,
            label=CompleteBrick1.verbose_name,
            choices=choices,
        )

        response = self.client.post(
            url,
            data={
                f'bricks_check_{index1}': 'on',
                f'bricks_value_{index1}': HomeOnlyBrick1.id_,
                f'bricks_order_{index1}': 1,

                f'bricks_check_{index2}': 'on',
                f'bricks_value_{index2}': CompleteBrick1.id_,
                f'bricks_order_{index2}': 2,
            },
        )
        self.assertNoFormError(response)

        b_locs = [*BrickMypageLocation.objects.filter(user=None)]
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(HomeOnlyBrick1.id_, b_locs).order)
        self.assertEqual(2, self._find_location(CompleteBrick1.id_, b_locs).order)

    def test_edit_mypage01(self):
        user = self.login()
        url = reverse('creme_config__edit_mypage_bricks')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit "My page"'),         context.get('title'))
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

        with self.assertNoException():
            bricks_field = response.context['form'].fields['bricks']
            choices = bricks_field.choices

        self.assertGreaterEqual(len(choices), 2)
        self.assertEqual(
            [*BrickMypageLocation.objects.filter(user=None)
                                         .values_list('brick_id', flat=True)
            ],
            bricks_field.initial
        )

        index1 = self.assertInChoices(
            value=CompleteBrick1.id_,
            label=CompleteBrick1.verbose_name,
            choices=choices,
        )
        index2 = self.assertInChoices(
            value=HomeOnlyBrick1.id_,
            label=HomeOnlyBrick1.verbose_name,
            choices=choices,
        )

        response = self.client.post(
            url,
            data={
                f'bricks_check_{index1}': 'on',
                f'bricks_value_{index1}': CompleteBrick1.id_,
                f'bricks_order_{index1}': 1,

                f'bricks_check_{index2}': 'on',
                f'bricks_value_{index2}': HomeOnlyBrick1.id_,
                f'bricks_order_{index2}': 2,
            },
        )
        self.assertNoFormError(response)

        b_locs = [*BrickMypageLocation.objects.filter(user=user)]
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(CompleteBrick1.id_, b_locs).order)
        self.assertEqual(2, self._find_location(HomeOnlyBrick1.id_, b_locs).order)

    def test_edit_mypage02(self):
        "Not super-user."
        self.login(is_superuser=False)
        self.assertGET200(reverse('creme_config__edit_mypage_bricks'))

    def test_delete_default_mypage01(self):
        self.login()
        loc = BrickMypageLocation.objects.create(
            user=None, brick_id=HistoryBrick.id_, order=1,
        )
        self.assertPOST200(
            reverse('creme_config__delete_default_mypage_bricks'),
            data={'id': loc.id},
        )
        self.assertDoesNotExist(loc)

    def test_delete_default_mypage02(self):
        "'user' must be 'None'"
        user = self.login()
        loc = BrickMypageLocation.objects.create(
            user=user, brick_id=HistoryBrick.id_, order=1,
        )
        self.assertPOST404(
            reverse('creme_config__delete_default_mypage_bricks'),
            data={'id': loc.id},
        )
        self.assertStillExists(loc)

    def test_delete_mypage01(self):
        user = self.login()
        loc = BrickMypageLocation.objects.create(
            user=user, brick_id=HistoryBrick.id_, order=1,
        )
        self.assertPOST200(
            reverse('creme_config__delete_mypage_bricks'), data={'id': loc.id},
        )
        self.assertDoesNotExist(loc)

    def test_delete_mypage02(self):
        "BlockMypageLocation must belong to the user."
        self.login()
        loc = BrickMypageLocation.objects.create(
            user=self.other_user, brick_id=HistoryBrick.id_, order=1,
        )
        self.assertPOST404(
            reverse('creme_config__delete_mypage_bricks'),
            data={'id': loc.id},
        )
        self.assertStillExists(loc)

    def test_add_relationbrick(self):
        self.login()
        rt = RelationType.create(
            ('test-subfoo', 'subject_predicate'),
            ('test-objfoo', 'object_predicate'),
        )[0]
        self.assertFalse(RelationBrickItem.objects.filter(relation_type=rt).exists())

        url = reverse('creme_config__create_rtype_brick')
        context = self.assertGET200(url).context
        self.assertEqual(_('Create a type of block'), context.get('title'))
        self.assertEqual(_('Save the block'),         context.get('submit_label'))

        self.assertNoFormError(self.client.post(url, data={'relation_type': rt.id}))

        rb_items = RelationBrickItem.objects.all()
        self.assertEqual(1, len(rb_items))

        rb_item = rb_items[0]
        self.assertEqual(rt.id, rb_item.relation_type.id)
        self.assertEqual('specificblock_creme_config-test-subfoo', rb_item.brick_id)
        self.assertIsNone(rb_item.get_cells(ContentType.objects.get_for_model(FakeContact)))

    def test_add_relationbrick_ctypes_wizard01(self):
        self.login()
        rt = RelationType.create(
            ('test-subfoo', 'Subject predicate'),
            ('test-objfoo', 'Object predicate', [FakeContact, FakeOrganisation, FakeActivity]),
        )[0]

        rb_item = RelationBrickItem.objects.create(
            brick_id='specificblock_creme_config-test-subfoo',
            relation_type=rt,
        )

        url = self._build_rbrick_addctypes_wizard_url(rb_item)

        # Step 1 ---
        response = self.assertGET200(url)
        context = response.context
        self.assertEqual(
            _('New customised type for «{object}»').format(object=rt.predicate),
            context.get('title')
        )

        with self.assertNoException():
            choices = context['form'].fields['ctype'].ctypes

        get_ct = ContentType.objects.get_for_model
        ct_contact  = get_ct(FakeContact)
        ct_activity = get_ct(FakeActivity)
        ct_image    = get_ct(FakeImage)
        self.assertIn(ct_contact,           choices)
        self.assertIn(get_ct(FakeOrganisation), choices)
        self.assertIn(ct_activity,          choices)
        self.assertNotIn(ct_image,          choices)

        step_key = 'relation_c_type_brick_wizard-current_step'
        response = self.assertPOST200(
            url,
            data={
                step_key: '0',
                '0-ctype': ct_contact.pk,
            },
        )

        # Last step is not submitted so nothing yet in database
        rb_item = self.refresh(rb_item)
        self.assertIsNone(rb_item.get_cells(ct_contact))
        context = response.context
        self.assertEqual(
            _('New customised type for «{object}»').format(object=rt.predicate),
            context.get('title')
        )

        with self.assertNoException():
            fields = context['form'].fields

        self.assertIn('cells', fields)

        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')
        field_fname = 'first_name'
        field_lname = 'last_name'
        response = self.client.post(
            url,
            data={
                step_key: '1',
                '1-cells': f'regular_field-{field_fname},'
                           f'regular_field-{field_lname},'
                           f'function_field-{funcfield.name}',
            },
        )
        self.assertNoFormError(response)

        rb_item = self.refresh(rb_item)
        self.assertIsNone(rb_item.get_cells(ct_activity))

        cells = rb_item.get_cells(ct_contact)
        self.assertIsInstance(cells, list)
        self.assertEqual(3, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_fname, cell.value)

        self.assertEqual(field_lname, cells[1].value)

        cell = cells[2]
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(funcfield.name, cell.value)

        # Used CTypes should not be proposed
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['ctype'].ctypes

        self.assertIn(ct_activity,   choices)  # Compatible & not used
        self.assertNotIn(ct_image,   choices)  # Still not compatible
        self.assertNotIn(ct_contact, choices)  # Used

    def test_add_relationbrick_ctypes_wizard02(self):
        "ContentType constraint"
        self.login()
        rtype = RelationType.create(
            ('test-subfoo', 'subject_predicate', [FakeContact]),
            ('test-objfoo', 'object_predicate',  [FakeOrganisation]),
        )[0]
        rb_item = RelationBrickItem.objects.create(
            brick_id='specificblock_creme_config-test-subfoo',
            relation_type=rtype,
        )

        url = self._build_rbrick_addctypes_wizard_url(rb_item)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['ctype'].ctypes

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(FakeContact)
        self.assertIn(get_ct(FakeOrganisation), choices)
        self.assertNotIn(ct_contact,        choices)
        self.assertNotIn(get_ct(FakeActivity), choices)

        response = self.client.post(
            url,
            data={
                'relation_c_type_brick_wizard-current_step': '0',
                '0-ctype': ct_contact.pk,
            },
        )
        self.assertFormError(
            response, 'form', 'ctype',
            _('Select a valid choice. That choice is not one of the available choices.')
        )

    def test_add_relationbrick_ctypes_wizard03(self):
        "Go back."
        self.login()
        rtype = RelationType.create(
            ('test-subfoo', 'subject_predicate', [FakeOrganisation]),
            ('test-objfoo', 'object_predicate',  [FakeContact]),
        )[0]
        rb_item = RelationBrickItem.objects.create(
            brick_id='specificblock_creme_config-test-subfoo',
            relation_type=rtype,
        )

        url = self._build_rbrick_addctypes_wizard_url(rb_item)

        ct_contact  = ContentType.objects.get_for_model(FakeContact)
        self.assertPOST200(
            url,
            data={
                'relation_c_type_brick_wizard-current_step': '0',
                '0-ctype': ct_contact.pk,
            },
        )

        # Return to first step
        response = self.assertPOST200(
            url,
            data={
                'relation_c_type_brick_wizard-current_step': '1',
                'wizard_goto_step': '0',
            },
        )

        with self.assertNoException():
            choices = response.context['form'].fields['ctype'].ctypes

        self.assertIn(ct_contact, choices)

    def test_edit_relationbrick_ctypes01(self):
        self.login()
        ct = ContentType.objects.get_for_model(FakeContact)
        rt = RelationType.create(
            ('test-subfoo', 'subject_predicate'),
            ('test-objfoo', 'object_predicate'),
        )[0]

        rb_item = RelationBrickItem(
            brick_id='specificblock_creme_config-test-subfoo',
            relation_type=rt,
        )
        rb_item.set_cells(ct, ())
        rb_item.save()

        self.assertGET404(self._build_rbrick_editctype_url(rb_item, FakeOrganisation))

        url = self._build_rbrick_editctype_url(rb_item, FakeContact)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(
            _('Edit «{model}» configuration').format(model=ct),
            context.get('title')
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
        self.assertIsInstance(cells, list)
        self.assertEqual(3, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_fname, cell.value)

        self.assertEqual(field_lname, cells[1].value)

        cell = cells[2]
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(funcfield.name, cell.value)

    def test_edit_relationbrick_ctypes02(self):
        "Validation errors with URLField & ForeignKey."
        self.login()
        rb_item = RelationBrickItem(
            brick_id='specificblock_creme_config-test-subfoo',
            relation_type=RelationType.create(
                ('test-subfoo', 'subject_predicate'),
                ('test-objfoo', 'object_predicate'),
            )[0],
        )
        rb_item.set_cells(ContentType.objects.get_for_model(FakeContact), ())
        rb_item.save()

        url = self._build_rbrick_editctype_url(rb_item, FakeContact)

        def post(field_name, error=True):
            response = self.assertPOST200(
                url,
                data={'cells': f'regular_field-{field_name},regular_field-last_name'},
            )
            if error:
                self.assertFormError(
                    response, 'form', 'cells',
                    _('This type of field can not be the first column.')
                )
            else:
                self.assertNoFormError(response)

        post('url_site')
        post('email')
        post('image')
        post('image__name')
        post('civility', error=False)
        post('civility__shortcut', error=False)

    def test_edit_relationbrick_ctypes03(self):
        "Validation errors with M2M"
        self.login()
        rb_item = RelationBrickItem(
            brick_id='specificblock_creme_config-test-subfoo',
            relation_type=RelationType.create(
                ('test-subfoo', 'subject_predicate'),
                ('test-objfoo', 'object_predicate'),
            )[0],
        )
        rb_item.set_cells(ContentType.objects.get_for_model(FakeEmailCampaign), ())
        rb_item.save()

        url = self._build_rbrick_editctype_url(rb_item, FakeEmailCampaign)

        def post(field_name):
            response = self.assertPOST200(
                url,
                data={'cells': f'regular_field-{field_name},regular_field-name'}
            )
            self.assertFormError(
                response, 'form', 'cells',
                _('This type of field can not be the first column.')
            )

        post('mailing_lists')
        post('mailing_lists__name')

    def test_edit_relationbrick_ctypes04(self):
        "Validation errors with Relation."
        self.login()
        create_rtype = RelationType.create
        rt1 = create_rtype(
            ('test-subfoo', 'subject_predicate1'),
            ('test-objfoo', 'object_predicate2'),
        )[0]
        rt2 = create_rtype(
            ('test-subbar', 'subject_predicate2'),
            ('test-objbar', 'object_predicate2'),
        )[0]

        rb_item = RelationBrickItem(
            brick_id='specificblock_creme_config-test-subfoo',
            relation_type=rt1,
        )
        rb_item.set_cells(ContentType.objects.get_for_model(FakeOrganisation), ())
        rb_item.save()

        response = self.assertPOST200(
            self._build_rbrick_editctype_url(rb_item, FakeOrganisation),
            data={'cells': f'relation-{rt2.id},regular_field-name'},
        )
        self.assertFormError(
            response, 'form', 'cells',
            _('This type of field can not be the first column.')
        )

    def test_edit_relationbrick_ctypes05(self):
        "With FieldsConfig."
        self.login()
        ct = ContentType.objects.get_for_model(FakeContact)
        rt = RelationType.create(
            ('test-subfoo', 'subject_predicate'),
            ('test-objfoo', 'object_predicate'),
        )[0]

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

        rb_item = RelationBrickItem(
            brick_id='specificblock_creme_config-test-subfoo',
            relation_type=rt,
        )
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
            response, 'form', 'cells',
            # _('Enter a valid value.')
            _('This value is invalid: %(value)s') % {'value': hidden_fname2},
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

    def test_delete_relationbrick_ctypes(self):
        self.login()
        get_ct = ContentType.objects.get_for_model
        ct = get_ct(FakeContact)

        rb_item = RelationBrickItem(
            brick_id='specificblock_creme_config-test-subfoo',
            relation_type=RelationType.create(
                ('test-subfoo', 'subject_predicate'),
                ('test-objfoo', 'object_predicate'),
            )[0],
        )
        rb_item.set_cells(ct, [EntityCellRegularField.build(FakeContact, 'first_name')])
        rb_item.save()

        url = reverse('creme_config__delete_cells_of_rtype_brick', args=(rb_item.id,))
        self.assertPOST404(url, data={'id': get_ct(FakeOrganisation).id})

        data = {'id': ct.id}
        self.assertGET405(url, data=data)  # Only POST

        self.assertPOST200(url, data=data)
        self.assertIsNone(self.refresh(rb_item).get_cells(ct))

    def test_delete_relationbrick(self):
        user = self.login()
        rt = RelationType.create(
            ('test-subfoo', 'subject_predicate'),
            ('test-objfoo', 'object_predicate'),
            is_custom=False,
        )[0]
        rbi = RelationBrickItem.objects.create(brick_id='foobarid', relation_type=rt)

        brick_id = rbi.brick_id

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            zone=BrickDetailviewLocation.RIGHT, model=FakeContact,
        )
        loc1 = create_bdl(brick=brick_id,           order=5)
        loc2 = create_bdl(brick=CompleteBrick1.id_, order=6)

        create_state = partial(BrickState.objects.create, user=user)
        state1 = create_state(brick_id=brick_id)
        state2 = create_state(brick_id=CompleteBrick1.id_)

        self.assertPOST200(reverse('creme_config__delete_rtype_brick'), data={'id': rbi.id})
        self.assertDoesNotExist(rbi)
        self.assertDoesNotExist(loc1)
        self.assertStillExists(loc2)
        self.assertDoesNotExist(state1)
        self.assertStillExists(state2)

    def test_delete_instancebrick(self):
        user = self.login()
        naru = FakeContact.objects.create(user=user, first_name='Naru', last_name='Narusegawa')

        ibi = InstanceBrickConfigItem.objects.create(
            # brick_id=InstanceBrickConfigItem.generate_id(DetailviewInstanceBrick, naru, ''),
            brick_class_id=DetailviewInstanceBrick.id_,
            entity=naru,
            # verbose='All stuffes',
        )

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            zone=BrickDetailviewLocation.RIGHT, model=FakeContact,
        )
        brick_id = ibi.brick_id
        # dloc1 = create_bdl(brick=ibi.brick_id,       order=5)
        dloc1 = create_bdl(brick=brick_id,           order=5)
        dloc2 = create_bdl(brick=CompleteBrick1.id_, order=6)

        create_bhl = BrickHomeLocation.objects.create
        # hloc1 = create_bhl(brick_id=ibi.brick_id,       order=5)
        hloc1 = create_bhl(brick_id=brick_id,           order=5)
        hloc2 = create_bhl(brick_id=CompleteBrick1.id_, order=6)

        create_bml = BrickMypageLocation.objects.create
        # mloc1 = create_bml(brick_id=ibi.brick_id,       order=5)
        mloc1 = create_bml(brick_id=brick_id,           order=5)
        mloc2 = create_bml(brick_id=CompleteBrick1.id_, order=6)

        create_state = BrickState.objects.create
        # state1 = create_state(brick_id=ibi.brick_id,       user=self.user)
        state1 = create_state(brick_id=brick_id,           user=user)
        state2 = create_state(brick_id=CompleteBrick1.id_, user=user)

        self.assertPOST200(reverse('creme_config__delete_instance_brick'), data={'id': ibi.id})
        self.assertDoesNotExist(ibi)
        self.assertDoesNotExist(dloc1)
        self.assertStillExists(dloc2)
        self.assertDoesNotExist(hloc1)
        self.assertStillExists(hloc2)
        self.assertDoesNotExist(mloc1)
        self.assertStillExists(mloc2)
        self.assertDoesNotExist(state1)
        self.assertStillExists(state2)

    def test_edit_custombrick01(self):
        self.login()
        ct = ContentType.objects.get_for_model(FakeContact)

        loves = RelationType.create(('test-subject_love', 'Is loving'),
                                    ('test-object_love',  'Is loved by')
                                   )[0]
        customfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=ct,
        )
        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')

        name = 'info'
        cbc_item = CustomBrickConfigItem.objects.create(
            id='tests-contacts1', content_type=ct, name=name,
        )

        url = self._build_custombrick_edit_url(cbc_item)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Edit the block «{object}»').format(object=cbc_item),
            response.context.get('title')
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
        self.assertIsInstance(cells, list)
        self.assertEqual(5, len(cells))

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

    def test_edit_custombrick02(self):
        "With FieldsConfig."
        self.login()
        ct = ContentType.objects.get_for_model(FakeContact)

        valid_fname = 'last_name'
        # valid_subfname = 'city'
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
            id='tests-contacts1',
            name='Contact info',
            content_type=ct,
        )

        url = self._build_custombrick_edit_url(cbc_item)
        # response = self.assertGET200(url)
        #
        # with self.assertNoException():
        #     widget = response.context['form'].fields['cells'].widget
        #     choices_keys = {c[0] for c in widget.model_fields}
        #
        # self.assertIn('regular_field-' + valid_fname,     choices_keys)
        # self.assertIn('regular_field-address',            choices_keys)
        # self.assertNotIn('regular_field-' + hidden_fname, choices_keys)

        response1 = self.assertPOST200(
            url, follow=True,
            data={
                'name':  cbc_item.name,
                'cells': f'regular_field-{valid_fname},'
                         f'regular_field-{hidden_fname}',
            },
        )
        self.assertFormError(
            response1, 'form', 'cells',
            # _('Enter a valid value.')
            _('This value is invalid: %(value)s') % {'value': hidden_fname},
        )

        # ---------------------------
        # with self.assertNoException():
        #     address_choices_keys = {
        #         c[0] for c in widget.model_subfields['regular_field-address']
        #     }
        #
        prefix = 'address__'
        # self.assertIn('regular_field-' + prefix + valid_subfname, address_choices_keys)
        # self.assertNotIn('regular_field-' + prefix + hidden_subfname, address_choices_keys)

        response2 = self.assertPOST200(
            url, follow=True,
            data={
                'name':  cbc_item.name,
                'cells': f'regular_field-{valid_fname},'
                         f'regular_field-{prefix}{hidden_subfname}',
            },
        )
        self.assertFormError(
            response2, 'form', 'cells',
            # _('Enter a valid value.')
            _('This value is invalid: %(value)s') % {'value': prefix + hidden_subfname},
        )

        # ----------------------------
        # self.assertNotIn('regular_field-' + hidden_fkname, choices_keys)
        # self.assertFalse(widget.model_subfields['regular_field-image'])

        response3 = self.assertPOST200(
            url, follow=True,
            data={
                'name':  cbc_item.name,
                'cells': f'regular_field-{valid_fname},'
                         f'regular_field-{hidden_fkname}',
            },
        )
        self.assertFormError(
            response3, 'form', 'cells',
            _('This value is invalid: %(value)s') % {'value': hidden_fkname},
        )

    def test_edit_custombrick03(self):
        "With FieldsConfig + field in the blocks becomes hidden => still proposed in the form."
        self.login()
        ct = ContentType.objects.get_for_model(FakeContact)

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
            id='tests-contacts1', name='Contact info', content_type=ct,
            cells=[
                build_cell(FakeContact, valid_fname),
                build_cell(FakeContact, hidden_fname1),
                build_cell(FakeContact, addr_prefix + hidden_subfname1),
                build_cell(FakeContact, hidden_fkname),
            ],
        )

        url = self._build_custombrick_edit_url(cbc_item)
        # response = self.assertGET200(url)
        #
        # with self.assertNoException():
        #     widget = response.context['form'].fields['cells'].widget
        #     choices_keys = {c[0] for c in widget.model_fields}
        #
        #     subfields = widget.model_subfields
        #     address_choices_keys = {c[0] for c in subfields['regular_field-address']}
        #     image_choices_keys   = {c[0] for c in subfields['regular_field-image']}
        #
        rf_prefix = 'regular_field-'
        # self.assertIn(rf_prefix + valid_fname,   choices_keys)
        # self.assertIn(rf_prefix + hidden_fname1, choices_keys)
        # self.assertNotIn(rf_prefix + hidden_fname2, choices_keys)
        #
        # self.assertIn(rf_prefix + addr_prefix + hidden_subfname1, address_choices_keys) # idem
        # self.assertNotIn(rf_prefix + addr_prefix + hidden_subfname2, address_choices_keys)
        #
        # self.assertIn(rf_prefix + hidden_fkname, image_choices_keys) # idem
        # self.assertIn(rf_prefix + 'image',       choices_keys)

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
        # self.assertEqual(4, len(self.refresh(cbc_item).cells))
        self.assertListEqual(
            [
                build_cell(FakeContact, valid_fname),
                build_cell(FakeContact, hidden_fname1),
                build_cell(FakeContact, addr_prefix + hidden_subfname1),
                build_cell(FakeContact, hidden_fkname),
            ],
            self.refresh(cbc_item).cells
        )

    def test_delete_custombrick(self):
        self.login()
        ct = ContentType.objects.get_for_model(FakeContact)
        cbci = CustomBrickConfigItem.objects.create(content_type=ct, name='Info')
        loc = BrickDetailviewLocation.objects.create_if_needed(
            brick=cbci.generate_id(), order=5,
            model=FakeContact,
            zone=BrickDetailviewLocation.RIGHT,
        )

        self.assertPOST200(
            reverse('creme_config__delete_custom_brick'),
            data={'id': cbci.id},
        )
        self.assertDoesNotExist(cbci)
        self.assertDoesNotExist(loc)

    def test_custombrick_wizard_model_step(self):
        self.login()
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        # contact_customfield = CustomField.objects.create(
        #     name='Size (cm)',
        #     field_type=CustomField.INT,
        #     content_type=contact_ct,
        # )

        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

        response = self.assertGET200(self.CUSTOM_WIZARD_URL)
        self.assertIn(contact_ct, response.context['form'].fields['ctype'].ctypes)

        response = self.assertPOST200(
            self.CUSTOM_WIZARD_URL,
            data={
                'custom_brick_wizard-current_step': '0',
                '0-ctype': contact_ct.pk,
                '0-name': 'foobar',
            },
        )

        # cells_widget = ].widget
        self.assertIn('cells', response.context['form'].fields)
        # customfield_ids = [e[0] for e in cells_widget.custom_fields]
        # regularfield_ids = [e[0] for e in cells_widget.model_fields]
        #
        # self.assertIn(f'custom_field-{contact_customfield.id}', customfield_ids)
        # self.assertIn('regular_field-first_name', regularfield_ids)
        # self.assertIn('regular_field-birthday', regularfield_ids)

        # last step is not submitted so nothing yet in database
        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

    def test_custombrick_wizard_model_step_invalid(self):
        self.login()
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

        response = self.assertGET200(self.CUSTOM_WIZARD_URL)
        self.assertIn(contact_ct, response.context['form'].fields['ctype'].ctypes)

        response = self.assertPOST200(
            self.CUSTOM_WIZARD_URL,
            data={
                'custom_brick_wizard-current_step': '0',
                '0-ctype': 'unknown',
                '0-name': 'foobar',
            },
        )

        self.assertFormError(
            response, 'form', 'ctype',
            _('Select a valid choice. That choice is not one of the available choices.')
        )

        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

    def test_custombrick_wizard_config_step(self):
        self.login()
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        contact_customfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=contact_ct,
        )

        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

        response = self.assertGET200(self.CUSTOM_WIZARD_URL)
        self.assertIn(contact_ct, response.context['form'].fields['ctype'].ctypes)

        # response = self.assertPOST200(
        self.assertPOST200(
            self.CUSTOM_WIZARD_URL,
            data={
                'custom_brick_wizard-current_step': '0',
                '0-ctype': contact_ct.pk,
                '0-name': 'foobar',
            },
        )
        # cells_widget = response.context['form'].fields['cells'].widget
        # customfield_ids = [e[0] for e in cells_widget.custom_fields]
        # regularfield_ids = [e[0] for e in cells_widget.model_fields]
        #
        # # self.assertIn(f'custom_field-{contact_customfield.id}', customfield_ids)
        # self.assertInChoices(
        #     f'custom_field-{contact_customfield.id}',
        #     label=contact_customfield.name,
        #     choices=customfield_choices,
        # )
        # self.assertIn('regular_field-first_name', regularfield_ids)
        # self.assertIn('regular_field-birthday', regularfield_ids)

        response = self.assertPOST200(
            self.CUSTOM_WIZARD_URL,
            data={
                'custom_brick_wizard-current_step': '1',
                '1-cells': f'regular_field-first_name,'
                           f'custom_field-{contact_customfield.id}',
            },
        )
        self.assertNoFormError(response)

        cbci = self.get_object_or_fail(CustomBrickConfigItem, content_type=contact_ct)
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, 'first_name'),
                EntityCellCustomField(contact_customfield),
            ],
            cbci.cells
        )

    def test_custombrick_wizard_go_back(self):
        self.login()
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        # contact_customfield = CustomField.objects.create(
        #     name='Size (cm)',
        #     field_type=CustomField.INT,
        #     content_type=contact_ct,
        # )

        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

        response = self.assertGET200(self.CUSTOM_WIZARD_URL)
        self.assertIn(contact_ct, response.context['form'].fields['ctype'].ctypes)

        response = self.assertPOST200(
            self.CUSTOM_WIZARD_URL,
            data={
                'custom_brick_wizard-current_step': '0',
                '0-ctype': contact_ct.pk,
                '0-name': 'foobar',
            },
        )
        # cells_widget = response.context['form'].fields['cells'].widget
        self.assertIn('cells', response.context['form'].fields)
        # customfield_ids = [e[0] for e in cells_widget.custom_fields]
        # regularfield_ids = [e[0] for e in cells_widget.model_fields]
        #
        # self.assertIn(f'custom_field-{contact_customfield.id}', customfield_ids)
        # self.assertIn('regular_field-first_name',               regularfield_ids)
        # self.assertIn('regular_field-birthday',                 regularfield_ids)

        # Return to first step
        response = self.assertPOST200(
            self.CUSTOM_WIZARD_URL,
            data={
                'custom_brick_wizard-current_step': '1',
                'wizard_goto_step': '0',
            },
        )
        self.assertIn(contact_ct, response.context['form'].fields['ctype'].ctypes)
