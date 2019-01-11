# -*- coding: utf-8 -*-

try:
    from copy import deepcopy
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import (FakeContact, FakeOrganisation, FakeAddress,
            FakeImage, FakeActivity, FakeEmailCampaign, FakeInvoiceLine)
    from creme.creme_core.bricks import (RelationsBrick, PropertiesBrick,
            HistoryBrick, CustomFieldsBrick)
    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.core.function_field import function_field_registry
    from creme.creme_core.gui import bricks as gui_bricks
    from creme.creme_core.gui.bricks import Brick, SpecificRelationsBrick
    from creme.creme_core.models import (RelationType, CustomField, FieldsConfig, UserRole,
             BrickDetailviewLocation, InstanceBrickConfigItem, BrickState,
             BrickHomeLocation, BrickMypageLocation, RelationBrickItem, CustomBrickConfigItem)
    from creme.creme_core.registry import creme_registry

    from creme.creme_config import bricks
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


# Test Bricks ------------------------------------------------------------------
class _BaseCompleteBrick(Brick):
    verbose_name = 'Testing purpose'

    def detailview_display(self, context):
        return '<table id="{}"></table>'.format(self.id_)

    def home_display(self, context):
        return '<table id="{}"></table>'.format(self.id_)

    def portal_display(self, context, ct_ids):
        return '<table id="{}"></table>'.format(self.id_)


class CompleteBrick1(_BaseCompleteBrick):
    id_ = Brick.generate_id('creme_config', 'testbrickconfig_complete_1')


class CompleteBrick2(_BaseCompleteBrick):
    id_ = Brick.generate_id('creme_config', 'testbrickconfig_complete_2')


class CompleteBrick3(_BaseCompleteBrick):
    id_ = Brick.generate_id('creme_config', 'testbrickconfig_complete_3')


class CompleteBrick4(_BaseCompleteBrick):
    id_ = Brick.generate_id('creme_config', 'testbrickconfig_complete_4')


class HomePortalBrick(Brick):
    id_          = Brick.generate_id('creme_config', 'testbrickconfig_home_portal')
    verbose_name = 'Testing purpose'

    # def detailview_display(self, context): NO

    def home_display(self, context):
        return '<table id="{}"></table>'.format(self.id_)


class HomeOnlyBrick1(Brick):
    id_          = Brick.generate_id('creme_config', 'testbrickconfig_home_only_1')
    verbose_name = 'Testing purpose'

    # def detailview_display(self, context): return self._render(self.get_block_template_context(context))

    def home_display(self, context):
        return '<table id="{}"></table>'.format(self.id_)


class HomeOnlyBrick2(Brick):
    id_          = Brick.generate_id('creme_config', 'testbrickconfig_home_only_2')
    verbose_name = 'Testing purpose'
    configurable = False  # <----

    # def detailview_display(self, context): return self._render(self.get_block_template_context(context))

    def home_display(self, context):
        return '<table id="{}"></table>'.format(self.id_)


class DetailviewInstanceBrick(Brick):
    id_ = InstanceBrickConfigItem.generate_base_id('creme_config', 'test_detail_instance')

    def __init__(self, instance_block_config_item):
        super().__init__()
        self.ibci = instance_block_config_item

    def detailview_display(self, context):
        return '<table id="{id}"><thead><tr>{entity}</tr></thead></table>'.format(id=self.id_, entity=self.ibci.entity)


class HomeInstanceBrick(Brick):
    id_          = InstanceBrickConfigItem.generate_base_id('creme_config', 'test_home_instance')
    verbose_name = 'Testing purpose'

    def __init__(self, instance_block_config_item):
        super().__init__()
        self.ibci = instance_block_config_item

    def home_display(self, context):
        return '<table id="{id}"><thead><tr>{entity}</tr></thead></table>'.format(id=self.id_, entity=self.ibci.entity)


class FakeContactHatBrick(Brick):
    id_ = Brick._generate_hat_id('creme_core', 'test_hat_brick')
    verbose_name = 'Fake contact header brick'

    def detailview_display(self, context):
        return '<table id="{}"></table>'.format(self.id_)


# Test case --------------------------------------------------------------------

class BricksConfigTestCase(CremeTestCase):
    DEL_DETAIL_URL = reverse('creme_config__delete_detailview_bricks')
    CUSTOM_WIZARD_URL = reverse('creme_config__create_custom_brick')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._bdl_backup = list(BrickDetailviewLocation.objects.all())
        cls._bpl_backup = list(BrickHomeLocation.objects.all())
        cls._bml_backup = list(BrickMypageLocation.objects.all())
        cls._rbi_backup = list(RelationBrickItem.objects.all())

        BrickDetailviewLocation.objects.all().delete()
        BrickHomeLocation.objects.all().delete()
        BrickMypageLocation.objects.all().delete()
        RelationBrickItem.objects.all().delete()

        cls._original_block_registry = gui_bricks.brick_registry

        cls.brick_registry = block_registry = deepcopy(gui_bricks.brick_registry)
        block_registry.register(CompleteBrick1, CompleteBrick2, CompleteBrick3, CompleteBrick4,
                                HomePortalBrick,
                                HomeOnlyBrick1,
                                HomeOnlyBrick2,
                               )

        block_registry.register_4_instance(DetailviewInstanceBrick)
        block_registry.register_4_instance(HomeInstanceBrick)

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
                print('CremeBlockTagsTestCase: test-data backup problem with model={}'.format(model))

        gui_bricks.brick_registry = cls._original_block_registry

    def setUp(self):
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
        return reverse('creme_config__edit_cells_of_rtype_brick', args=(
                    rbi.id, ContentType.objects.get_for_model(model).id,
                ))

    def _build_custombrick_edit_url(self, cbc_item):
        return reverse('creme_config__edit_custom_brick', args=(cbc_item.id,))

    def _find_field_index(self, formfield, name):
        for i, (fname, fvname) in enumerate(formfield.choices):
            if fname == name:
                return i

        self.fail('No "{}" field'.format(name))

    def _assertNotInChoices(self, formfield, id_, error_msg):
        for fid, fvname in formfield.choices:
            if fid == id_:
                self.fail(error_msg + ' -> should not be in choices.')

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
        self.assertEqual(_('New block configuration for «{model}»').format(model='Test Contact'),
                         context.get('title')
                        )
        self.assertEqual(_('Save the configuration'), context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields
            top_field    = fields['top']
            left_field   = fields['left']
            right_field  = fields['right']
            bottom_field = fields['bottom']

        self.assertNotIn('hat', fields)

        bricks = list(self.brick_registry.get_compatible_bricks(model))
        self.assertGreaterEqual(len(bricks), 5)
        self._find_field_index(top_field, CompleteBrick1.id_)

        brick_top_id1   = bricks[0].id_
        brick_top_id2   = bricks[1].id_
        brick_left_id1  = bricks[2].id_
        brick_left_id2  = self.brick_registry.get_brick_4_object(model).id_
        brick_right_id  = bricks[3].id_
        brick_bottom_id = bricks[4].id_

        brick_top_index1   = self._find_field_index(top_field, brick_top_id1)
        brick_top_index2   = self._find_field_index(top_field, brick_top_id2)
        brick_left_index1  = self._find_field_index(left_field, brick_left_id1)
        brick_left_index2  = self._find_field_index(left_field, brick_left_id2)
        brick_right_index  = self._find_field_index(right_field, brick_right_id)
        brick_bottom_index = self._find_field_index(bottom_field, brick_bottom_id)

        response = self.client.post(url,
                                    data={'role': role.id if role else '',

                                          'top_check_{}'.format(brick_top_index1): 'on',
                                          'top_value_{}'.format(brick_top_index1): brick_top_id1,
                                          'top_order_{}'.format(brick_top_index1): 1,

                                          'top_check_{}'.format(brick_top_index2): 'on',
                                          'top_value_{}'.format(brick_top_index2): brick_top_id2,
                                          'top_order_{}'.format(brick_top_index2): 2,

                                          'left_check_{}'.format(brick_left_index1): 'on',
                                          'left_value_{}'.format(brick_left_index1): brick_left_id1,
                                          'left_order_{}'.format(brick_left_index1): 1,

                                          'left_check_{}'.format(brick_left_index2): 'on',
                                          'left_value_{}'.format(brick_left_index2): brick_left_id2,
                                          'left_order_{}'.format(brick_left_index2): 2,

                                          'right_check_{}'.format(brick_right_index): 'on',
                                          'right_value_{}'.format(brick_right_index): brick_right_id,
                                          'right_order_{}'.format(brick_right_index): 1,

                                          'bottom_check_{}'.format(brick_bottom_index): 'on',
                                          'bottom_value_{}'.format(brick_bottom_index): brick_bottom_id,
                                          'bottom_order_{}'.format(brick_bottom_index): 1,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(content_type=ct, role=role, superuser=superuser)
        filter_locs = lambda zone: [bl for bl in b_locs if bl.zone == zone]

        locations = filter_locs(BrickDetailviewLocation.TOP)
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(brick_top_id1, locations).order)
        self.assertEqual(2, self._find_location(brick_top_id2, locations).order)

        locations = filter_locs(BrickDetailviewLocation.LEFT)
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(brick_left_id1, locations).order)
        self.assertEqual(2, self._find_location(brick_left_id2, locations).order)

        locations = filter_locs(BrickDetailviewLocation.RIGHT)
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(brick_right_id, locations).order)

        locations = filter_locs(BrickDetailviewLocation.BOTTOM)
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(brick_bottom_id, locations).order)

        self.assertEqual([''], [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.HAT)])

    def test_add_detailview01(self):
        self.login(is_superuser=False, admin_4_apps=['creme_core'])
        self._aux_test_add_detailview(role=self.role, superuser=False)

    def test_add_detailview02(self):
        self.login()
        self._aux_test_add_detailview(role=None, superuser=True)

    def test_add_detailview03(self):
        "Used roles are not proposed anymore"
        self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)
        url = self._build_adddetail_url(ct)

        role1 = self.role
        role2 = UserRole.objects.create(name='Viewer')

        def get_choices():
            response = self.assertGET200(url)

            with self.assertNoException():
                return list(response.context['form'].fields['role'].choices)

        choices = get_choices()
        self.assertIn(('', '*{}*'.format(_('Superuser'))), choices)
        self.assertIn((role1.id, role1.name), choices)
        self.assertIn((role2.id, role2.name), choices)

        # Role ------------
        bricks = list(self.brick_registry.get_compatible_bricks(model))
        self.assertGreaterEqual(len(bricks), 5, bricks)

        create_loc = partial(BrickDetailviewLocation.objects.create, content_type=ct, order=1)
        create_loc(role=role1, brick_id=bricks[0].id_, zone=BrickDetailviewLocation.TOP)
        create_loc(role=role1, brick_id=bricks[1].id_, zone=BrickDetailviewLocation.LEFT)
        create_loc(role=role1, brick_id=bricks[2].id_, zone=BrickDetailviewLocation.RIGHT)
        create_loc(role=role1, brick_id=bricks[3].id_, zone=BrickDetailviewLocation.BOTTOM)

        choices = get_choices()
        self.assertIn(('', '*{}*'.format(_('Superuser'))), choices)
        self.assertIn((role2.id, role2.name), choices)
        self.assertNotIn((role1.id, role1.name), choices)

        # Superuser ------------
        create_loc(superuser=True, brick_id=bricks[0].id_, zone=BrickDetailviewLocation.TOP)
        create_loc(superuser=True, brick_id=bricks[1].id_, zone=BrickDetailviewLocation.LEFT)
        create_loc(superuser=True, brick_id=bricks[2].id_, zone=BrickDetailviewLocation.RIGHT)
        create_loc(superuser=True, brick_id=bricks[3].id_, zone=BrickDetailviewLocation.BOTTOM)

        choices = get_choices()
        self.assertIn((role2.id, role2.name), choices)
        self.assertNotIn((role1.id, role1.name), choices)
        self.assertNotIn(('', '*{}*'.format(_('Superuser'))), choices)

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
        "Extra HatBrick"
        self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        self.brick_registry.register_hat(model, secondary_brick_classes=[FakeContactHatBrick])

        url = self._build_adddetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            top_field = fields['top']
            hat_f = fields['hat']
            hat_choices = hat_f.choices

        self.assertEqual(2, len(hat_choices))

        generic_id = Brick.GENERIC_HAT_BRICK_ID
        self.assertEqual((generic_id, _('Title bar')), hat_choices[0])
        self.assertEqual((FakeContactHatBrick.id_, FakeContactHatBrick.verbose_name),
                         hat_choices[1]
                        )
        self.assertEqual(generic_id, hat_f.initial)

        brick_top_id = CompleteBrick1.id_
        brick_top_index = self._find_field_index(top_field, brick_top_id)
        response = self.client.post(url,
                                    data={'hat': FakeContactHatBrick.id_,

                                          'top_check_{}'.format(brick_top_index): 'on',
                                          'top_value_{}'.format(brick_top_index): brick_top_id,
                                          'top_order_{}'.format(brick_top_index): 1,
                                         },
                                   )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(content_type=ct, role=None, superuser=True)
        filter_locs = lambda zone: [bl for bl in b_locs if bl.zone == zone]

        top_locations = filter_locs(BrickDetailviewLocation.TOP)
        self.assertEqual(1, len(top_locations))
        self.assertEqual(brick_top_id, top_locations[0].brick_id)

        self.assertEqual([''], [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.LEFT)])
        self.assertEqual([''], [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.RIGHT)])
        self.assertEqual([''], [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.BOTTOM)])

        hat_locations = filter_locs(BrickDetailviewLocation.HAT)
        self.assertEqual(1, len(hat_locations))
        self.assertEqual(FakeContactHatBrick.id_, hat_locations[0].brick_id)

    def test_add_detailview06(self):
        "Admin credentials are needed"
        self.login(is_superuser=False)
        self.assertGET403(self._build_adddetail_url(ContentType.objects.get_for_model(FakeContact)))

    def _aux_test_edit_detailview(self, role=None, superuser=False, expected_title='Edit the bricks'):
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
            top_field    = fields['top']
            left_field   = fields['left']
            right_field  = fields['right']
            bottom_field = fields['bottom']

        bricks = list(self.brick_registry.get_compatible_bricks(model))
        self.assertGreaterEqual(len(bricks), 5)
        self._find_field_index(top_field, CompleteBrick1.id_)
        self._assertNotInChoices(top_field, HomePortalBrick.id_,
                                 'Block has no detailview_display() method'
                                )

        brick_top_id1   = bricks[0].id_
        brick_top_id2   = bricks[1].id_
        brick_left_id1  = self.brick_registry.get_brick_4_object(model).id_
        brick_left_id2  = bricks[2].id_
        brick_right_id  = bricks[3].id_
        brick_bottom_id = bricks[4].id_

        brick_top_index1   = self._find_field_index(top_field, brick_top_id1)
        brick_top_index2   = self._find_field_index(top_field, brick_top_id2)
        brick_left_index1  = self._find_field_index(left_field, brick_left_id1)
        brick_left_index2  = self._find_field_index(left_field, brick_left_id2)
        brick_right_index  = self._find_field_index(right_field, brick_right_id)
        brick_bottom_index = self._find_field_index(bottom_field, brick_bottom_id)

        response = self.client.post(url,
                                    data={'top_check_{}'.format(brick_top_index1): 'on',
                                          'top_value_{}'.format(brick_top_index1): brick_top_id1,
                                          'top_order_{}'.format(brick_top_index1): 1,

                                          'top_check_{}'.format(brick_top_index2): 'on',
                                          'top_value_{}'.format(brick_top_index2): brick_top_id2,
                                          'top_order_{}'.format(brick_top_index2): 2,

                                          'left_check_{}'.format(brick_left_index1): 'on',
                                          'left_value_{}'.format(brick_left_index1): brick_left_id1,
                                          'left_order_{}'.format(brick_left_index1): 1,

                                          'left_check_{}'.format(brick_left_index2): 'on',
                                          'left_value_{}'.format(brick_left_index2): brick_left_id2,
                                          'left_order_{}'.format(brick_left_index2): 2,

                                          'right_check_{}'.format(brick_right_index): 'on',
                                          'right_value_{}'.format(brick_right_index): brick_right_id,
                                          'right_order_{}'.format(brick_right_index): 1,

                                          'bottom_check_{}'.format(brick_bottom_index): 'on',
                                          'bottom_value_{}'.format(brick_bottom_index): brick_bottom_id,
                                          'bottom_order_{}'.format(brick_bottom_index): 1,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(content_type=ct, role=role,
                                                        superuser=superuser,
                                                       )
        filter_locs = lambda zone: [bl for bl in b_locs if bl.zone == zone]

        locations = filter_locs(BrickDetailviewLocation.TOP)
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(brick_top_id1, locations).order)
        self.assertEqual(2, self._find_location(brick_top_id2, locations).order)

        locations = filter_locs(BrickDetailviewLocation.LEFT)
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(brick_left_id1, locations).order)
        self.assertEqual(2, self._find_location(brick_left_id2, locations).order)

        locations = filter_locs(BrickDetailviewLocation.RIGHT)
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(brick_right_id, locations).order)

        locations = filter_locs(BrickDetailviewLocation.BOTTOM)
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(brick_bottom_id, locations).order)

        self.assertEqual([''], [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.HAT)])

    def test_edit_detailview01(self):
        "Default configuration of a ContentType"
        self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)
        brick_id = list(self.brick_registry.get_compatible_bricks(model))[0].id_

        # These bricks should not be modified
        create_loc = partial(BrickDetailviewLocation.objects.create,
                             content_type=ct, order=1, brick_id=brick_id,
                             zone=BrickDetailviewLocation.TOP,
                            )
        b_loc1 = create_loc(role=self.role)
        b_loc2 = create_loc(superuser=True)

        self._aux_test_edit_detailview(
            role=None, superuser=False,
            expected_title=_('Edit default configuration for «{model}»').format(model=ct)
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
        "When no block -> fake block"
        self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        bricks = list(self.brick_registry.get_compatible_bricks(model))
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

        brick_top_index1 = self._find_field_index(top_field, brick_top_id1)
        brick_top_index2 = self._find_field_index(top_field, brick_top_id2)

        response = self.client.post(url,
                                    data={'top_check_{}'.format(brick_top_index1): 'on',
                                          'top_value_{}'.format(brick_top_index1): brick_top_id1,
                                          'top_order_{}'.format(brick_top_index1): 1,

                                          'top_check_{}'.format(brick_top_index2): 'on',
                                          'top_value_{}'.format(brick_top_index2): brick_top_id2,
                                          'top_order_{}'.format(brick_top_index2): 2,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(content_type=ct)
        locations = [b_loc for b_loc in b_locs if b_loc.zone == BrickDetailviewLocation.TOP]
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(brick_top_id1, locations).order)
        self.assertEqual(2, self._find_location(brick_top_id2, locations).order)

        bricks_info = lambda zone: [(bl.brick_id, bl.order) for bl in b_locs if bl.zone == zone]

        self.assertEqual([('', 1)], bricks_info(BrickDetailviewLocation.LEFT))
        self.assertEqual([('', 1)], bricks_info(BrickDetailviewLocation.RIGHT))
        self.assertEqual([('', 1)], bricks_info(BrickDetailviewLocation.BOTTOM))

    def test_edit_detailview05(self):
        "Default conf + no empty configuration"
        self.login()
        self.assertGET404(self._build_editdetail_url(ct=None, role=self.role))

        url = self._build_editdetail_url(ct=None)
        context = self.assertGET200(url).context
        self.assertEqual(_('Edit default configuration'), context.get('title'))

        response = self.assertPOST200(url, data={})
        self.assertFormError(response, 'form', None,
                             _('Your configuration is empty !')
                            )

        bricks = list(self.brick_registry.get_compatible_bricks(None))
        self.assertGreaterEqual(len(bricks), 1, bricks)
        brick_id = bricks[0].id_

        with self.assertNoException():
            top_field = response.context['form'].fields['top']

        index = self._find_field_index(top_field, brick_id)
        response = self.client.post(url,
                                    data={'top_check_{}'.format(index): 'on',
                                          'top_value_{}'.format(index): brick_id,
                                          'top_order_{}'.format(index): 1,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(content_type=None)
        bricks_info = lambda zone: [(bl.brick_id, bl.order) for bl in b_locs if bl.zone == zone]

        self.assertEqual([(brick_id, 1)], bricks_info(BrickDetailviewLocation.TOP))
        self.assertEqual([('', 1)], bricks_info(BrickDetailviewLocation.LEFT))
        self.assertEqual([('', 1)], bricks_info(BrickDetailviewLocation.RIGHT))
        self.assertEqual([('', 1)], bricks_info(BrickDetailviewLocation.BOTTOM))

    def test_edit_detailview06(self):
        "Post one block several times -> validation error"
        self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        url = self._build_editdetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            left_field  = fields['left']
            right_field = fields['right']

        bricks = list(self.brick_registry.get_compatible_bricks(model))
        self.assertTrue(bricks)

        def post(brick_id, brick_vname):
            brick_left_id = block_right_id = brick_id  # <= same block !!
            brick_left_index  = self._find_field_index(left_field,  brick_left_id)
            brick_right_index = self._find_field_index(right_field, block_right_id)

            response = self.client.post(url,
                                        data={'right_check_{}'.format(brick_right_index): 'on',
                                              'right_value_{}'.format(brick_right_index): block_right_id,
                                              'right_order_{}'.format(brick_right_index): 1,

                                              'left_check_{}'.format(brick_left_index): 'on',
                                              'left_value_{}'.format(brick_left_index): brick_left_id,
                                              'left_order_{}'.format(brick_left_index): 1,
                                             }
                                       )
            self.assertFormError(response, 'form', field=None,
                                 errors=_('The following block should be displayed only once: «%(block)s»') % {
                                                'block': brick_vname,
                                            }
                                )

        modelbrick_id = self.brick_registry.get_brick_4_object(model).id_

        with self.assertNoException():
            evil_brick = next((b for b in bricks if not b.id_ != modelbrick_id))

        post(evil_brick.id_, evil_brick.verbose_name)
        post(modelbrick_id, _('Information on the entity (generic)'))

    def test_edit_detailview07(self):
        self.login()
        "Instance block, RelationType brick"
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        rtype = RelationType.objects.all()[0]
        rtype_brick_id = SpecificRelationsBrick.generate_id('test', 'foobar')
        RelationBrickItem.objects.create(brick_id=rtype_brick_id, relation_type=rtype)

        naru = FakeContact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')

        instance_brick_id = InstanceBrickConfigItem.generate_id(DetailviewInstanceBrick, naru, '')
        InstanceBrickConfigItem.objects.create(brick_id=instance_brick_id,
                                               entity=naru, verbose='All stuffes',
                                              )

        response = self.assertGET200(self._build_editdetail_url(ct))

        with self.assertNoException():
            top_field = response.context['form'].fields['top']

        choices = [brick_id for brick_id, brick_vname in top_field.choices]
        self.assertIn(rtype_brick_id,    choices)
        self.assertIn(instance_brick_id, choices)

    def test_edit_detailview08(self):
        "Invalid models"
        self.login()
        build_url = self._build_editdetail_url
        get_ct = ContentType.objects.get_for_model
        self.assertGET409(build_url(get_ct(FakeAddress)))
        self.assertGET409(build_url(get_ct(FakeInvoiceLine)))

    def test_edit_detailview09(self):
        "Extra HatBrick"
        self.login()
        model = FakeContact
        ct = ContentType.objects.get_for_model(model)

        self.brick_registry.register_hat(model, secondary_brick_classes=[FakeContactHatBrick])

        url = self._build_editdetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            top_field = fields['top']
            hat_f = fields['hat']
            hat_choices = hat_f.choices

        generic_id = Brick.GENERIC_HAT_BRICK_ID
        self.assertEqual(2, len(hat_choices))
        self.assertEqual((generic_id, _('Title bar')), hat_choices[0])
        self.assertEqual((FakeContactHatBrick.id_, FakeContactHatBrick.verbose_name),
                         hat_choices[1]
                        )
        self.assertEqual(generic_id, hat_f.initial)

        brick_top_id = CompleteBrick1.id_
        brick_top_index = self._find_field_index(top_field, brick_top_id)
        response = self.client.post(url,
                                    data={'hat': FakeContactHatBrick.id_,

                                          'top_check_{}'.format(brick_top_index): 'on',
                                          'top_value_{}'.format(brick_top_index): brick_top_id,
                                          'top_order_{}'.format(brick_top_index): 1,
                                         },
                                   )
        self.assertNoFormError(response)

        b_locs = BrickDetailviewLocation.objects.filter(content_type=ct)
        filter_locs = lambda zone: [bl for bl in b_locs if bl.zone == zone]

        top_locations = filter_locs(BrickDetailviewLocation.TOP)
        self.assertEqual(1, len(top_locations))
        self.assertEqual(brick_top_id, top_locations[0].brick_id)

        self.assertEqual([''], [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.LEFT)])
        self.assertEqual([''], [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.RIGHT)])
        self.assertEqual([''], [loc.brick_id for loc in filter_locs(BrickDetailviewLocation.BOTTOM)])

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
        locs = [create_bdl(brick_id=RelationsBrick.id_),
                create_bdl(zone=BrickDetailviewLocation.LEFT,   brick_id=PropertiesBrick.id_),
                create_bdl(zone=BrickDetailviewLocation.RIGHT,  brick_id=CustomFieldsBrick.id_),
                create_bdl(zone=BrickDetailviewLocation.BOTTOM, brick_id=HistoryBrick.id_),
               ]

        locs_2 = [create_bdl(brick_id=RelationsBrick.id_, role=self.role),
                  create_bdl(brick_id=RelationsBrick.id_, superuser=True),
                  create_bdl(brick_id=RelationsBrick.id_, content_type=get_ct(FakeOrganisation)),
                 ]

        self.assertPOST200(self.DEL_DETAIL_URL, data={'id': ct.id})
        self.assertFalse(BrickDetailviewLocation.objects.filter(id__in=[l.id for l in locs]))
        self.assertEqual(len(locs_2),
                         BrickDetailviewLocation.objects.filter(id__in=[l.id for l in locs_2])
                                                        .count()
                        )

    def test_delete_detailview03(self):
        "Role configuration"
        self.login()
        get_ct = ContentType.objects.get_for_model
        ct = get_ct(FakeContact)
        role = self.role

        create_bdl = partial(BrickDetailviewLocation.objects.create, order=1,
                             content_type=ct, zone=BrickDetailviewLocation.TOP,
                             role=role,
                            )
        locs = [create_bdl(brick_id=RelationsBrick.id_),
                create_bdl(zone=BrickDetailviewLocation.LEFT,   brick_id=PropertiesBrick.id_),
                create_bdl(zone=BrickDetailviewLocation.RIGHT,  brick_id=CustomFieldsBrick.id_),
                create_bdl(zone=BrickDetailviewLocation.BOTTOM, brick_id=HistoryBrick.id_),
               ]

        locs_2 = [create_bdl(brick_id=RelationsBrick.id_, role=None),
                  create_bdl(brick_id=RelationsBrick.id_, superuser=True),
                  create_bdl(brick_id=RelationsBrick.id_, content_type=get_ct(FakeOrganisation)),
                 ]

        self.assertPOST200(self.DEL_DETAIL_URL, data={'id': ct.id, 'role': role.id})
        self.assertFalse(BrickDetailviewLocation.objects.filter(id__in=[l.id for l in locs]))
        self.assertEqual(len(locs_2),
                         BrickDetailviewLocation.objects.filter(id__in=[l.id for l in locs_2])
                                                        .count()
                        )

    def test_delete_detailview04(self):
        "Superuser configuration"
        self.login()
        get_ct = ContentType.objects.get_for_model
        ct = get_ct(FakeOrganisation)

        create_bdl = partial(BrickDetailviewLocation.objects.create, order=1,
                             content_type=ct, zone=BrickDetailviewLocation.TOP,
                             superuser=True,
                            )
        locs = [create_bdl(brick_id=RelationsBrick.id_),
                create_bdl(zone=BrickDetailviewLocation.LEFT,   brick_id=PropertiesBrick.id_),
                create_bdl(zone=BrickDetailviewLocation.RIGHT,  brick_id=CustomFieldsBrick.id_),
                create_bdl(zone=BrickDetailviewLocation.BOTTOM, brick_id=HistoryBrick.id_),
               ]

        locs_2 = [create_bdl(brick_id=RelationsBrick.id_, role=self.role),
                  create_bdl(brick_id=RelationsBrick.id_, superuser=False),
                  create_bdl(brick_id=RelationsBrick.id_, content_type=get_ct(FakeContact)),
                 ]

        self.assertPOST200(self.DEL_DETAIL_URL, data={'id': ct.id, 'role': 'superuser'})
        self.assertFalse(BrickDetailviewLocation.objects.filter(id__in=[l.id for l in locs]))
        self.assertEqual(len(locs_2),
                         BrickDetailviewLocation.objects.filter(id__in=[l.id for l in locs_2])
                                                        .count()
                        )

    def test_edit_home(self):
        self.login()

        BrickHomeLocation.objects.create(brick_id=HistoryBrick.id_, order=8)

        naru = FakeContact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')
        instance_brick_id = InstanceBrickConfigItem.generate_id(HomeInstanceBrick, naru, '')
        InstanceBrickConfigItem.objects.create(brick_id=instance_brick_id, entity=naru, verbose='All stuffes')

        url = reverse('creme_config__edit_home_bricks')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit home configuration'), context.get('title'))
        self.assertEqual(_('Save the modifications'),  context.get('submit_label'))

        with self.assertNoException():
            bricks_field = context['form'].fields['bricks']

        self._find_field_index(bricks_field, CompleteBrick1.id_)
        self._find_field_index(bricks_field, HomeOnlyBrick1.id_)
        self._find_field_index(bricks_field, HomePortalBrick.id_)
        self._find_field_index(bricks_field, instance_brick_id)

        self._assertNotInChoices(bricks_field, RelationsBrick.id_,   'No home_display().')
        self._assertNotInChoices(bricks_field, HomeOnlyBrick2.id_,   'Brick is not configurable')

        choices = bricks_field.choices
        brick_id1 = choices[0][0]
        brick_id2 = choices[1][0]

        index1 = self._find_field_index(bricks_field, brick_id1)
        index2 = self._find_field_index(bricks_field, brick_id2)

        response = self.client.post(url, data={'bricks_check_{}'.format(index1): 'on',
                                               'bricks_value_{}'.format(index1): brick_id1,
                                               'bricks_order_{}'.format(index1): 1,

                                               'bricks_check_{}'.format(index2): 'on',
                                               'bricks_value_{}'.format(index2): brick_id2,
                                               'bricks_order_{}'.format(index2): 2,
                                               }
                                    )
        self.assertNoFormError(response)

        b_locs = list(BrickHomeLocation.objects.all())
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(brick_id1, b_locs).order)
        self.assertEqual(2, self._find_location(brick_id2, b_locs).order)

    def test_delete_home_location_item(self):
        self.login()
        bricks = [block for brick_id, block in self.brick_registry
                            if hasattr(block, 'home_display')
                 ]
        self.assertGreaterEqual(len(bricks), 1)

        bpl = BrickHomeLocation.objects.create(brick_id=bricks[0].id_, order=1)
        self.assertPOST200(reverse('creme_config__delete_home_brick'), data={'id': bpl.id})
        self.assertDoesNotExist(bpl)

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
        self.assertEqual(list(BrickMypageLocation.objects.filter(user=None).values_list('brick_id', flat=True)),
                         bricks_field.initial
                        )

        brick_id1 = choices[0][0]
        brick_id2 = choices[1][0]

        index1 = self._find_field_index(bricks_field, brick_id1)
        index2 = self._find_field_index(bricks_field, brick_id2)

        response = self.client.post(url,
                                    data={
                                          'bricks_check_{}'.format(index1): 'on',
                                          'bricks_value_{}'.format(index1): brick_id1,
                                          'bricks_order_{}'.format(index1): 1,

                                          'bricks_check_{}'.format(index2): 'on',
                                          'bricks_value_{}'.format(index2): brick_id2,
                                          'bricks_order_{}'.format(index2): 2,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = list(BrickMypageLocation.objects.filter(user=None))
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(brick_id1, b_locs).order)
        self.assertEqual(2, self._find_location(brick_id2, b_locs).order)

    def test_edit_mypage01(self):
        user = self.login()
        url = reverse('creme_config__edit_mypage_bricks')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit "My page"'),         context.get('title'))
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

        with self.assertNoException():
            # blocks_field = response.context['form'].fields['blocks']
            bricks_field = response.context['form'].fields['bricks']

        choices = bricks_field.choices
        self.assertGreaterEqual(len(choices), 2)
        self.assertEqual(list(BrickMypageLocation.objects.filter(user=None).values_list('brick_id', flat=True)),
                         bricks_field.initial
                        )

        brick_id1 = choices[0][0]
        brick_id2 = choices[1][0]

        index1 = self._find_field_index(bricks_field, brick_id1)
        index2 = self._find_field_index(bricks_field, brick_id2)

        response = self.client.post(url,
                                    data={'bricks_check_{}'.format(index1): 'on',
                                          'bricks_value_{}'.format(index1): brick_id1,
                                          'bricks_order_{}'.format(index1): 1,

                                          'bricks_check_{}'.format(index2): 'on',
                                          'bricks_value_{}'.format(index2): brick_id2,
                                          'bricks_order_{}'.format(index2): 2,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = list(BrickMypageLocation.objects.filter(user=user))
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(brick_id1, b_locs).order)
        self.assertEqual(2, self._find_location(brick_id2, b_locs).order)

    def test_edit_mypage02(self):
        "Not super-user"
        self.login(is_superuser=False)
        self.assertGET200(reverse('creme_config__edit_mypage_bricks'))

    def test_delete_default_mypage01(self):
        self.login()
        loc = BrickMypageLocation.objects.create(user=None, brick_id=HistoryBrick.id_, order=1)
        self.assertPOST200(reverse('creme_config__delete_default_mypage_bricks'), data={'id': loc.id})
        self.assertDoesNotExist(loc)

    def test_delete_default_mypage02(self):
        "'user' must be 'None'"
        user = self.login()
        loc = BrickMypageLocation.objects.create(user=user, brick_id=HistoryBrick.id_, order=1)
        self.assertPOST404(reverse('creme_config__delete_default_mypage_bricks'), data={'id': loc.id})
        self.assertStillExists(loc)

    def test_delete_mypage01(self):
        user = self.login()
        loc = BrickMypageLocation.objects.create(user=user, brick_id=HistoryBrick.id_, order=1)
        self.assertPOST200(reverse('creme_config__delete_mypage_bricks'), data={'id': loc.id})
        self.assertDoesNotExist(loc)

    def test_delete_mypage02(self):
        "BlockMypageLocation must belong to the user"
        self.login()
        loc = BrickMypageLocation.objects.create(user=self.other_user, brick_id=HistoryBrick.id_, order=1)
        self.assertPOST404(reverse('creme_config__delete_mypage_bricks'), data={'id': loc.id})
        self.assertStillExists(loc)

    def test_add_relationbrick(self):
        self.login()
        rt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                 ('test-objfoo', 'object_predicate'),
                                )[0]
        self.assertFalse(RelationBrickItem.objects.filter(relation_type=rt).exists())

        url = reverse('creme_config__create_rtype_brick')
        context = self.assertGET200(url).context
        # self.assertEqual(_('New type of block'), context.get('title'))
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
        rt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                 ('test-objfoo', 'object_predicate', [FakeContact, FakeOrganisation, FakeActivity]),
                                 )[0]

        rb_item = RelationBrickItem.objects.create(
                        brick_id='specificblock_creme_config-test-subfoo',
                        relation_type=rt,
                    )

        url = self._build_rbrick_addctypes_wizard_url(rb_item)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['ctype'].ctypes

        get_ct = ContentType.objects.get_for_model
        ct_contact  = get_ct(FakeContact)
        ct_activity = get_ct(FakeActivity)
        ct_image    = get_ct(FakeImage)
        self.assertIn(ct_contact,           choices)
        self.assertIn(get_ct(FakeOrganisation), choices)
        self.assertIn(ct_activity,          choices)
        self.assertNotIn(ct_image,          choices)

        response = self.assertPOST200(url,
                                      {'relation_c_type_brick_wizard-current_step': '0',
                                       '0-ctype': ct_contact.pk,
                                      }
                                     )

        # Last step is not submitted so nothing yet in database
        rb_item = self.refresh(rb_item)
        self.assertIsNone(rb_item.get_cells(ct_contact))

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('cells', fields)

        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')
        field_fname = 'first_name'
        field_lname = 'last_name'
        response = self.client.post(
                url,
                data={'relation_c_type_brick_wizard-current_step': '1',
                      '1-cells': 'regular_field-{rfield1},regular_field-{rfield2},function_field-{ffield}'.format(
                                         rfield1=field_fname,
                                         rfield2=field_lname,
                                         ffield=funcfield.name,
                                    ),
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
        rtype = RelationType.create(('test-subfoo', 'subject_predicate', [FakeContact]),
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

        response = self.client.post(url,
                                    {'relation_c_type_brick_wizard-current_step': '0',
                                     '0-ctype': ct_contact.pk,
                                    }
                                   )
        self.assertFormError(response, 'form', 'ctype',
                             _('Select a valid choice. That choice is not one of the available choices.')
                            )

    def test_add_relationbrick_ctypes_wizard03(self):
        "Go back"
        self.login()
        rtype = RelationType.create(('test-subfoo', 'subject_predicate', [FakeOrganisation]),
                                    ('test-objfoo', 'object_predicate',  [FakeContact]),
                                    )[0]
        rb_item = RelationBrickItem.objects.create(
                        brick_id='specificblock_creme_config-test-subfoo',
                        relation_type=rtype,
                    )

        url = self._build_rbrick_addctypes_wizard_url(rb_item)

        ct_contact  = ContentType.objects.get_for_model(FakeContact)
        self.assertPOST200(url,
                           {'relation_c_type_brick_wizard-current_step': '0',
                            '0-ctype': ct_contact.pk,
                           }
                          )

        # Return to first step
        response = self.assertPOST200(url,
                                      {'relation_c_type_brick_wizard-current_step': '1',
                                       'wizard_goto_step': '0',
                                      }
                                     )

        with self.assertNoException():
            choices = response.context['form'].fields['ctype'].ctypes

        self.assertIn(ct_contact, choices)

    def test_edit_relationbrick_ctypes01(self):
        self.login()
        ct = ContentType.objects.get_for_model(FakeContact)
        rt = RelationType.create(('test-subfoo', 'subject_predicate'),
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
        self.assertEqual(_('Edit «{model}» configuration').format(model=ct),
                         context.get('title')
                        )
        self.assertEqual(_('Save the modifications'), context.get('submit_label'))

        # ---
        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')
        field_fname = 'first_name'
        field_lname = 'last_name'
        self.assertNoFormError(self.client.post(
            url,
            data={'cells': 'regular_field-{rfield1},regular_field-{rfield2},function_field-{ffield}'.format(
                                rfield1=field_fname,
                                rfield2=field_lname,
                                ffield=funcfield.name,
                            ),
                 }
           )
        )

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
        "Validation errors with URLField & ForeignKey"
        self.login()
        rb_item = RelationBrickItem(
                brick_id='specificblock_creme_config-test-subfoo',
                relation_type=RelationType.create(('test-subfoo', 'subject_predicate'),
                                                  ('test-objfoo', 'object_predicate'),
                                                 )[0],
            )
        rb_item.set_cells(ContentType.objects.get_for_model(FakeContact), ())
        rb_item.save()

        url = self._build_rbrick_editctype_url(rb_item, FakeContact)

        def post(field_name, error=True):
            response = self.assertPOST200(
                url,
                data={'cells': 'regular_field-{rfield1},regular_field-{rfield2}'.format(
                                    rfield1=field_name,
                                    rfield2='last_name',
                                ),
                     }
            )
            if error:
                self.assertFormError(response, 'form', 'cells',
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
                relation_type=RelationType.create(('test-subfoo', 'subject_predicate'),
                                                  ('test-objfoo', 'object_predicate'),
                                                 )[0],
            )
        rb_item.set_cells(ContentType.objects.get_for_model(FakeEmailCampaign), ())
        rb_item.save()

        url = self._build_rbrick_editctype_url(rb_item, FakeEmailCampaign)

        def post(field_name):
            response = self.assertPOST200(
                url,
                data={'cells': 'regular_field-{rfield1},regular_field-{rfield2}'.format(
                                    rfield1=field_name,
                                    rfield2='name',
                                ),
                     }
            )
            self.assertFormError(response, 'form', 'cells',
                                 _('This type of field can not be the first column.')
                                )

        post('mailing_lists')
        post('mailing_lists__name')

    def test_edit_relationbrick_ctypes04(self):
        "Validation errors with Relation"
        self.login()
        create_rtype = RelationType.create
        rt1 = create_rtype(('test-subfoo', 'subject_predicate1'), ('test-objfoo', 'object_predicate2'))[0]
        rt2 = create_rtype(('test-subbar', 'subject_predicate2'), ('test-objbar', 'object_predicate2'))[0]

        rb_item = RelationBrickItem(
                brick_id='specificblock_creme_config-test-subfoo',
                relation_type=rt1,
            )
        rb_item.set_cells(ContentType.objects.get_for_model(FakeOrganisation), ())
        rb_item.save()

        response = self.assertPOST200(
            self._build_rbrick_editctype_url(rb_item, FakeOrganisation),
            data={'cells': 'relation-{rtype},regular_field-{rfield}'.format(
                                rtype=rt2.id,
                                rfield='name',
                            ),
                 }
        )
        self.assertFormError(response, 'form', 'cells',
                             _('This type of field can not be the first column.')
                            )

    def test_edit_relationbrick_ctypes05(self):
        "With FieldsConfig"
        self.login()
        ct = ContentType.objects.get_for_model(FakeContact)
        rt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                 ('test-objfoo', 'object_predicate'),
                                )[0]


        valid_fname = 'last_name'
        hidden_fname1 = 'phone'
        hidden_fname2 = 'birthday'
        FieldsConfig.create(FakeContact,
                            descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True}),
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
                        data={'cells': 'regular_field-{rfield1},regular_field-{rfield2},regular_field-{rfield3}'.format(
                                            rfield1=valid_fname,
                                            rfield2=hidden_fname1,
                                            rfield3=hidden_fname2,
                                        ),
                             }
                    )
        self.assertFormError(response, 'form', 'cells', _('Enter a valid value.'))

        self.assertNoFormError(self.client.post(
            url,
            data={'cells': 'regular_field-{rfield1},regular_field-{rfield2}'.format(
                                rfield1=valid_fname,
                                rfield2=hidden_fname1,
                            ),
                 }
           ))

        rb_item = self.refresh(rb_item)
        self.assertEqual(2, len(rb_item.get_cells(ct)))

    def test_delete_relationbrick_ctypes(self):
        self.login()
        get_ct = ContentType.objects.get_for_model
        ct = get_ct(FakeContact)

        rb_item = RelationBrickItem(
                brick_id='specificblock_creme_config-test-subfoo',
                relation_type=RelationType.create(('test-subfoo', 'subject_predicate'),
                                                  ('test-objfoo', 'object_predicate'),
                                                 )[0],
            )
        rb_item.set_cells(ct, [EntityCellRegularField.build(FakeContact, 'first_name')])
        rb_item.save()

        url = reverse('creme_config__delete_cells_of_rtype_brick', args=(rb_item.id,))
        self.assertPOST404(url, data={'id': get_ct(FakeOrganisation).id})

        data = {'id': ct.id}
        self.assertGET404(url, data=data)  # Only POST

        self.assertPOST200(url, data=data)
        self.assertIsNone(self.refresh(rb_item).get_cells(ct))

    def test_delete_relationbrick(self):
        self.login()
        rt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                 ('test-objfoo', 'object_predicate'), is_custom=False
                                )[0]
        rbi = RelationBrickItem.objects.create(brick_id='foobarid', relation_type=rt)
        loc = BrickDetailviewLocation.create_if_needed(brick_id=rbi.brick_id, order=5,
                                                       zone=BrickDetailviewLocation.RIGHT,
                                                       model=FakeContact,
                                                      )

        self.assertPOST200(reverse('creme_config__delete_rtype_brick'), data={'id': rbi.id})
        self.assertDoesNotExist(rbi)
        self.assertDoesNotExist(loc)

    def test_delete_instancebrick(self):
        self.login()
        naru = FakeContact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')

        ibi = InstanceBrickConfigItem.objects.create(
                    brick_id=InstanceBrickConfigItem.generate_id(DetailviewInstanceBrick, naru, ''),
                    entity=naru, verbose='All stuffes',
                )

        create_bdl = partial(BrickDetailviewLocation.create_if_needed,
                             zone=BrickDetailviewLocation.RIGHT, model=FakeContact,
                            )
        dloc1 = create_bdl(brick_id=ibi.brick_id,       order=5)
        dloc2 = create_bdl(brick_id=CompleteBrick1.id_, order=6)

        create_bhl = BrickHomeLocation.objects.create
        hloc1 = create_bhl(brick_id=ibi.brick_id,       order=5)
        hloc2 = create_bhl(brick_id=CompleteBrick1.id_, order=6)

        create_bml = BrickMypageLocation.objects.create
        mloc1 = create_bml(brick_id=ibi.brick_id,       order=5)
        mloc2 = create_bml(brick_id=CompleteBrick1.id_, order=6)

        create_state = BrickState.objects.create
        state1 = create_state(brick_id=ibi.brick_id,       user=self.user)
        state2 = create_state(brick_id=CompleteBrick1.id_, user=self.user)

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
        customfield = CustomField.objects.create(name='Size (cm)',
                                                 field_type=CustomField.INT,
                                                 content_type=ct,
                                                )
        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')

        name = 'info'
        cbc_item = CustomBrickConfigItem.objects.create(id='tests-contacts1',
                                                        content_type=ct, name=name,
                                                       )

        url = self._build_custombrick_edit_url(cbc_item)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(_('Edit the block «{object}»').format(object=cbc_item),
                         response.context.get('title')
                        )

        # ---
        name = name.title()
        field_lname = 'last_name'
        field_subname = 'address__city'
        self.assertNoFormError(self.client.post(
            url, follow=True,
            data={'name':  name,
                  'cells': 'regular_field-{rfield1},regular_field-{rfield2},relation-{rtype},'
                           'function_field-{ffield},custom_field-{cfield}'.format(
                                rfield1=field_lname,
                                rfield2=field_subname,
                                cfield=customfield.id,
                                rtype=loves.id,
                                ffield=funcfield.name,
                            ),
                 }
           )
        )

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
        "With FieldsConfig"
        self.login()
        ct = ContentType.objects.get_for_model(FakeContact)

        valid_fname = 'last_name'
        valid_subfname = 'city'
        hidden_fname = 'phone'
        hidden_fkname = 'image'
        hidden_subfname = 'zipcode'

        create_fconf = FieldsConfig.create
        create_fconf(FakeContact, descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True}),
                                                (hidden_fkname, {FieldsConfig.HIDDEN: True}),
                                                ]
                     )
        create_fconf(FakeAddress, descriptions=[(hidden_subfname, {FieldsConfig.HIDDEN: True})])

        cbc_item = CustomBrickConfigItem.objects.create(id='tests-contacts1',
                                                        name='Contact info',
                                                        content_type=ct,
                                                       )

        url = self._build_custombrick_edit_url(cbc_item)
        response = self.assertGET200(url)

        with self.assertNoException():
            widget = response.context['form'].fields['cells'].widget
            choices_keys = {c[0] for c in widget.model_fields}

        self.assertIn('regular_field-' + valid_fname,     choices_keys)
        self.assertIn('regular_field-address',            choices_keys)
        self.assertNotIn('regular_field-' + hidden_fname, choices_keys)

        response = self.assertPOST200(
                        url, follow=True,
                        data={'name':  cbc_item.name,
                              'cells': 'regular_field-{rfield1},regular_field-{rfield2}'.format(
                                            rfield1=valid_fname,
                                            rfield2=hidden_fname,
                                        ),
                             },
                    )
        self.assertFormError(response, 'form', 'cells', _('Enter a valid value.'))

        # ---------------------------
        with self.assertNoException():
            address_choices_keys = {c[0] for c in widget.model_subfields['regular_field-address']}

        prefix = 'address__'
        self.assertIn('regular_field-' + prefix + valid_subfname, address_choices_keys)
        self.assertNotIn('regular_field-' + prefix + hidden_subfname, address_choices_keys)

        response = self.assertPOST200(
                        url, follow=True,
                        data={'name':  cbc_item.name,
                              'cells': 'regular_field-{rfield1},regular_field-{rfield2}'.format(
                                            rfield1=valid_fname,
                                            rfield2=prefix + hidden_subfname,
                                        ),
                             },
                    )
        self.assertFormError(response, 'form', 'cells', _('Enter a valid value.'))

        # ----------------------------
        self.assertNotIn('regular_field-' + hidden_fkname, choices_keys)
        self.assertFalse(widget.model_subfields['regular_field-image'])

    def test_edit_custombrick03(self):
        "With FieldsConfig + field in the blocks becomes hidden => still proposed in the form"
        self.login()
        ct = ContentType.objects.get_for_model(FakeContact)

        valid_fname = 'last_name'
        hidden_fname1 = 'phone'
        hidden_fname2 = 'mobile'

        hidden_fkname = 'image__description'

        addr_prefix = 'address__'
        hidden_subfname1 = 'zipcode'
        hidden_subfname2 = 'country'

        create_fconf = FieldsConfig.create
        create_fconf(FakeContact, descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True}),
                                                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
                                                ('image',       {FieldsConfig.HIDDEN: True}),
                                               ],
                    )
        create_fconf(FakeAddress, descriptions=[(hidden_subfname1, {FieldsConfig.HIDDEN: True}),
                                                (hidden_subfname2, {FieldsConfig.HIDDEN: True}),
                                               ],
                    )

        build_cell = EntityCellRegularField.build
        cbc_item = CustomBrickConfigItem.objects.create(
                        id='tests-contacts1', name='Contact info', content_type=ct,
                        cells=[build_cell(FakeContact, valid_fname),
                               build_cell(FakeContact, hidden_fname1),
                               build_cell(FakeContact, addr_prefix + hidden_subfname1),
                               build_cell(FakeContact, hidden_fkname),
                              ],
                    )

        url = self._build_custombrick_edit_url(cbc_item)
        response = self.assertGET200(url)

        with self.assertNoException():
            widget = response.context['form'].fields['cells'].widget
            choices_keys = {c[0] for c in widget.model_fields}

            subfields = widget.model_subfields
            address_choices_keys = {c[0] for c in subfields['regular_field-address']}
            image_choices_keys   = {c[0] for c in subfields['regular_field-image']}

        rf_prefix = 'regular_field-'
        self.assertIn(rf_prefix + valid_fname,   choices_keys)
        self.assertIn(rf_prefix + hidden_fname1, choices_keys) # was already in the block => still proposed
        self.assertNotIn(rf_prefix + hidden_fname2, choices_keys)

        self.assertIn(rf_prefix + addr_prefix + hidden_subfname1, address_choices_keys) # idem
        self.assertNotIn(rf_prefix + addr_prefix + hidden_subfname2, address_choices_keys)

        self.assertIn(rf_prefix + hidden_fkname, image_choices_keys) # idem
        self.assertIn(rf_prefix + 'image',       choices_keys) # we need it because we have a subfield

        response = self.client.post(
                        url, follow=True,
                        data={'name':  cbc_item.name,
                              'cells': ','.join(rf_prefix + fname
                                                    for fname in (valid_fname,
                                                                  hidden_fname1,
                                                                  addr_prefix + hidden_subfname1,
                                                                  hidden_fkname,
                                                                 )
                                               ),
                             },
                    )
        self.assertNoFormError(response)
        self.assertEqual(4, len(self.refresh(cbc_item).cells))

    def test_delete_custombrick(self):
        self.login()
        ct = ContentType.objects.get_for_model(FakeContact)
        cbci = CustomBrickConfigItem.objects.create(content_type=ct, name='Info')
        loc = BrickDetailviewLocation.create_if_needed(brick_id=cbci.generate_id(), order=5,
                                                       model=FakeContact,
                                                       zone=BrickDetailviewLocation.RIGHT,
                                                      )

        self.assertPOST200(reverse('creme_config__delete_custom_brick'), data={'id': cbci.id})
        self.assertDoesNotExist(cbci)
        self.assertDoesNotExist(loc)

    def test_custombrick_wizard_model_step(self):
        self.login()
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        contact_customfield = CustomField.objects.create(name='Size (cm)',
                                                         field_type=CustomField.INT,
                                                         content_type=contact_ct,
                                                        )

        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

        response = self.assertGET200(self.CUSTOM_WIZARD_URL)
        self.assertIn(contact_ct, response.context['form'].fields['ctype'].ctypes)

        response = self.assertPOST200(self.CUSTOM_WIZARD_URL,
                                      {'custom_brick_wizard-current_step': '0',
                                       '0-ctype': contact_ct.pk,
                                       '0-name': 'foobar',
                                      }
                                     )

        cells_widget = response.context['form'].fields['cells'].widget
        customfield_ids = [e[0] for e in cells_widget.custom_fields]
        regularfield_ids = [e[0] for e in cells_widget.model_fields]

        self.assertIn('custom_field-{}'.format(contact_customfield.id), customfield_ids)
        self.assertIn('regular_field-first_name', regularfield_ids)
        self.assertIn('regular_field-birthday', regularfield_ids)

        # last step is not submitted so nothing yet in database
        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

    def test_custombrick_wizard_model_step_invalid(self):
        self.login()
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

        response = self.assertGET200(self.CUSTOM_WIZARD_URL)
        self.assertIn(contact_ct, response.context['form'].fields['ctype'].ctypes)

        response = self.assertPOST200(self.CUSTOM_WIZARD_URL,
                                      {'custom_brick_wizard-current_step': '0',
                                       '0-ctype': 'unknown',
                                       '0-name': 'foobar',
                                      }
                                     )

        self.assertFormError(response, 'form', 'ctype',
                             _('Select a valid choice. That choice is not one of the available choices.')
                            )

        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

    def test_custombrick_wizard_config_step(self):
        self.login()
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        contact_customfield = CustomField.objects.create(name='Size (cm)',
                                                         field_type=CustomField.INT,
                                                         content_type=contact_ct,
                                                        )

        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

        response = self.assertGET200(self.CUSTOM_WIZARD_URL)
        self.assertIn(contact_ct, response.context['form'].fields['ctype'].ctypes)

        response = self.assertPOST200(self.CUSTOM_WIZARD_URL,
                                      {'custom_brick_wizard-current_step': '0',
                                       '0-ctype': contact_ct.pk,
                                       '0-name': 'foobar',
                                      }
                                     )
        cells_widget = response.context['form'].fields['cells'].widget
        customfield_ids = [e[0] for e in cells_widget.custom_fields]
        regularfield_ids = [e[0] for e in cells_widget.model_fields]

        self.assertIn('custom_field-{}'.format(contact_customfield.id), customfield_ids)
        self.assertIn('regular_field-first_name', regularfield_ids)
        self.assertIn('regular_field-birthday', regularfield_ids)

        response = self.assertPOST200(self.CUSTOM_WIZARD_URL,
                                      {'custom_brick_wizard-current_step': '1',
                                       '1-cells': '{},{}'.format('regular_field-first_name',
                                                                 'custom_field-{}'.format(contact_customfield.id),
                                                                ),
                                      }
                                     )
        self.assertNoFormError(response)

        cbci = self.get_object_or_fail(CustomBrickConfigItem, content_type=contact_ct)
        cells = [(c.__class__, c.key, c.value) for c in cbci.cells]

        self.assertListEqual([(EntityCellRegularField, 'regular_field-first_name', 'first_name'),
                              (EntityCellCustomField,
                               'custom_field-{}'.format(contact_customfield.id),
                               str(contact_customfield.id)
                              ),
                             ], cells
                            )

    def test_custombrick_wizard_go_back(self):
        self.login()
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        contact_customfield = CustomField.objects.create(name='Size (cm)',
                                                         field_type=CustomField.INT,
                                                         content_type=contact_ct,
                                                        )

        self.assertFalse(CustomBrickConfigItem.objects.filter(content_type=contact_ct))

        response = self.assertGET200(self.CUSTOM_WIZARD_URL)
        self.assertIn(contact_ct, response.context['form'].fields['ctype'].ctypes)

        response = self.assertPOST200(self.CUSTOM_WIZARD_URL,
                                      {'custom_brick_wizard-current_step': '0',
                                       '0-ctype': contact_ct.pk,
                                       '0-name': 'foobar',
                                      }
                                     )
        cells_widget = response.context['form'].fields['cells'].widget
        customfield_ids = [e[0] for e in cells_widget.custom_fields]
        regularfield_ids = [e[0] for e in cells_widget.model_fields]

        self.assertIn('custom_field-{}'.format(contact_customfield.id), customfield_ids)
        self.assertIn('regular_field-first_name', regularfield_ids)
        self.assertIn('regular_field-birthday', regularfield_ids)

        # Return to first step
        response = self.assertPOST200(self.CUSTOM_WIZARD_URL,
                                      {'custom_brick_wizard-current_step': '1',
                                       'wizard_goto_step': '0',
                                      }
                                     )
        self.assertIn(contact_ct, response.context['form'].fields['ctype'].ctypes)
