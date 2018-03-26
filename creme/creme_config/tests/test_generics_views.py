# -*- coding: utf-8 -*-

try:
    from json import dumps as json_dump  # loads as json_load

    from django.apps import apps
    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse

    from creme.creme_core.forms import CremeModelForm
    from creme.creme_core.gui.bricks import SimpleBrick, _BrickRegistry
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_bricks import FakeAppPortalBrick
    from creme.creme_core.tests.fake_models import FakeCivility, FakeSector, FakePosition
    from creme.creme_core.tests.views.base import BrickTestCaseMixin

    from ..bricks import GenericModelBrick, PropertyTypesBrick, SettingsBrick
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class GenericModelConfigTestCase(CremeTestCase, BrickTestCaseMixin):
    @classmethod
    def setUpClass(cls):
        super(GenericModelConfigTestCase, cls).setUpClass()

        cls._sector_backup = list(FakeSector.objects.all())
        FakeSector.objects.all().delete()

        # We import here in order to not launch the automatic registration before the fake bricks are registered.
        from .. import registry
        cls._ConfigRegistry = registry._ConfigRegistry
        cls.NotRegisteredInConfig = registry.NotRegisteredInConfig

    @classmethod
    def tearDownClass(cls):
        super(GenericModelConfigTestCase, cls).tearDownClass()
        FakeSector.objects.all().delete()
        FakeSector.objects.bulk_create(cls._sector_backup)

    def setUp(self):
        self.login()

    # def _build_down_url(self, instance_id, app_name='creme_core', short_name='fake_sector'):
    #     return reverse('creme_config__move_instance_down', args=(app_name, short_name, instance_id))
    #
    # def _build_up_url(self, instance_id, app_name='creme_core', short_name='fake_sector'):
    #     return reverse('creme_config__move_instance_up', args=(app_name, short_name, instance_id))

    def test_registry_register_model(self):
        class SectorForm(CremeModelForm):
            class Meta(CremeModelForm.Meta):
                model = FakeSector

        registry = self._ConfigRegistry()
        registry.register((FakeCivility, 'civility'),
                          (FakeSector, 'sector', SectorForm),
                         )

        with self.assertNoException():
            app_conf = registry.get_app('creme_core')

        with self.assertNoException():
            model_conf = app_conf.get_model_conf(model=FakeCivility)
        self.assertEqual('civility', model_conf.name_in_url)
        self.assertIsSubclass(model_conf.model_form, CremeModelForm)
        self.assertEqual('Test civility', model_conf.verbose_name)

        with self.assertNoException():
            model_conf = app_conf.get_model_conf(model=FakeSector)
        self.assertIsSubclass(model_conf.model_form, SectorForm)

        self.assertEqual('sector', model_conf.name_in_url)

        with self.assertRaises(ValueError):
            registry.register((FakePosition, 'my-position'))  # Invalid char '-'

    def test_registry_unregister_model01(self):
        "Unregister after the registration"
        registry = self._ConfigRegistry()
        registry.register((FakeCivility, 'civility'),
                          (FakeSector, 'sector'),
                          (FakePosition, 'position'),
                         )
        registry.unregister(FakeCivility, FakePosition)

        with self.assertNoException():
            app_conf = registry.get_app('creme_core')

        get_model_conf = app_conf.get_model_conf

        with self.assertNoException():
            get_model_conf(model=FakeSector)

        self.assertRaises(self.NotRegisteredInConfig, get_model_conf, model=FakeCivility)
        self.assertRaises(self.NotRegisteredInConfig, get_model_conf, model=FakePosition)

    def test_registry_unregister_model02(self):
        "Unregister before the registration"
        registry = self._ConfigRegistry()
        registry.unregister(FakeCivility, FakePosition)
        registry.register((FakeCivility, 'civility'),
                          (FakeSector, 'sector'),
                          (FakePosition, 'position'),
                         )

        with self.assertNoException():
            app_conf = registry.get_app('creme_core')

        get_model_conf = app_conf.get_model_conf

        with self.assertNoException():
            get_model_conf(model=FakeSector)

        self.assertRaises(self.NotRegisteredInConfig, get_model_conf, model=FakeCivility)
        self.assertRaises(self.NotRegisteredInConfig, get_model_conf, model=FakePosition)

    # def test_registry_register_blocks(self):
    #     class TestBlock1(SimpleBrick):
    #         id_ = SimpleBrick.generate_id('creme_config', 'test_registry_register_blocks1')
    #
    #     class TestBlock2(SimpleBrick):
    #         id_ = SimpleBrick.generate_id('creme_config', 'test_registry_register_blocks2')
    #
    #     block1 = TestBlock1()
    #     block2 = TestBlock2()
    #
    #     block_registry = _BrickRegistry()
    #     block_registry.register(block1, block2)
    #
    #     registry = self._ConfigRegistry(block_registry)
    #     registry.register_blocks(('creme_core', block1),
    #                              ('documents',  block2),
    #                             )
    #
    #     with self.assertNoException():
    #         app_conf = registry.get_app('creme_core')
    #
    #     blocks = app_conf.blocks()
    #     self.assertIsInstance(blocks, list)
    #     self.assertEqual(1, len(blocks))
    #     self.assertIsInstance(blocks[0], TestBlock1)
    #
    #     with self.assertNoException():
    #         app_conf = registry.get_app('documents')
    #
    #     blocks = app_conf.blocks()
    #     self.assertEqual(1, len(blocks))
    #     self.assertIsInstance(blocks[0], TestBlock2)

    def test_registry_register_bricks(self):
        class TestBrick1(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_registry_register_bricks1')

        class TestBrick2(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_registry_register_bricks2')

        brick_registry = _BrickRegistry()
        brick_registry.register(TestBrick1, TestBrick2)

        registry = self._ConfigRegistry(brick_registry)
        registry.register_bricks(('creme_core', TestBrick1),
                                 ('documents',  TestBrick2),
                                )

        with self.assertNoException():
            app_conf = registry.get_app('creme_core')

        def get_brick_ids(app_conf_registry):
            b_ids = set()
            for brick in app_conf_registry.bricks:
                self.assertIsInstance(brick, SimpleBrick)
                b_ids.add(brick.id_)
            return b_ids

        brick_ids = get_brick_ids(app_conf)
        self.assertIn(TestBrick1.id_, brick_ids)
        self.assertNotIn(TestBrick2, brick_ids)

        with self.assertNoException():
            app_conf = registry.get_app('documents')

        brick_ids = get_brick_ids(app_conf)
        self.assertIn(TestBrick2.id_, brick_ids)
        self.assertNotIn(TestBrick1, brick_ids)

    # def test_registry_register_userblocks(self):
    #     class TestUserBlock1(SimpleBrick):
    #         id_ = SimpleBrick.generate_id('creme_config', 'test_registry_register_userblocks1')
    #
    #     class TestUserBlock2(SimpleBrick):
    #         id_ = SimpleBrick.generate_id('creme_config', 'test_registry_register_userblocks2')
    #
    #     block1 = TestUserBlock1()
    #     block2 = TestUserBlock2()
    #
    #     block_registry = _BrickRegistry()
    #     block_registry.register(block1, block2)
    #
    #     registry = self._ConfigRegistry(block_registry)
    #
    #     registry.register_userblocks(block1, block2)
    #     ublocks = list(registry.userblocks)
    #     self.assertEqual(2, len(ublocks))
    #     self.assertIsInstance(ublocks[0], TestUserBlock1)
    #     self.assertIsInstance(ublocks[1], TestUserBlock2)

    def test_registry_register_userbricks(self):
        class TestUserBrick1(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_registry_register_userbricks1')

        class TestUserBrick2(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_registry_register_userbricks2')

        brick_registry = _BrickRegistry()
        brick_registry.register(TestUserBrick1, TestUserBrick2)

        registry = self._ConfigRegistry(brick_registry)

        registry.register_user_bricks(TestUserBrick1, TestUserBrick2)
        bricks = list(registry.user_bricks)
        self.assertEqual(2, len(bricks))
        self.assertIsInstance(bricks[0], TestUserBrick1)
        self.assertIsInstance(bricks[1], TestUserBrick2)

    def test_portals(self):
        self.assertGET200(reverse('creme_config__app_portal', args=('creme_core',)))
        self.assertGET404(reverse('creme_config__app_portal', args=('unexistingapp',)))

        self.assertGET200(reverse('creme_config__model_portal', args=('creme_core', 'fake_civility')))
        self.assertGET404(reverse('creme_config__model_portal', args=('creme_core', 'unexistingmodel')))

        if apps.is_installed('creme.persons'):
            self.assertGET200(reverse('creme_config__app_portal', args=('persons',)))
            self.assertGET200(reverse('creme_config__model_portal', args=('persons', 'civility')))
            self.assertGET404(reverse('creme_config__model_portal', args=('persons', 'unexistingmodel')))

    def test_add01(self):
        count = FakeCivility.objects.count()

        url = reverse('creme_config__create_instance', args=('creme_core', 'fake_civility'))
        self.assertGET200(url)

        title = 'Generalissime'
        shortcut = 'G.'
        self.assertNoFormError(self.client.post(url, data={'title': title, 'shortcut': shortcut}))
        self.assertEqual(count + 1, FakeCivility.objects.count())
        civility = self.get_object_or_fail(FakeCivility, title=title)
        self.assertEqual(shortcut, civility.shortcut)

    def test_add02(self):
        count = FakeSector.objects.count()

        url = reverse('creme_config__create_instance', args=('creme_core', 'fake_sector'))
        self.assertGET200(url)

        title = 'Music'
        self.assertNoFormError(self.client.post(url, data={'title': title}))
        self.assertEqual(count + 1, FakeSector.objects.count())

        sector = self.get_object_or_fail(FakeSector, title=title, is_custom=True)
        self.assertEqual(count + 1, sector.order)  # order is set to max

        title = 'Music & movie'
        self.client.post(url, data={'title': title})
        sector = self.get_object_or_fail(FakeSector, title=title)
        self.assertEqual(count + 2, sector.order)  # order is set to max

    def assertWidgetResponse(self, response, instance):
        self.assertEqual(json_dump({
                            'added': [[instance.id, unicode(instance)]], 
                            'value': instance.id
                         }), 
                         response.content
                        )

    def test_add01_from_widget(self):
        count = FakeCivility.objects.count()

        url = reverse('creme_config__create_instance_from_widget', args=('creme_core', 'fake_civility'))
        self.assertGET200(url)

        title = 'Generalissime'
        shortcut = 'G.'
        response = self.client.post(url, data={'title': title, 'shortcut': shortcut})
        self.assertNoFormError(response)
        self.assertEqual(count + 1, FakeCivility.objects.count())

        civility = self.get_object_or_fail(FakeCivility, title=title)
        self.assertEqual(shortcut, civility.shortcut)
        self.assertWidgetResponse(response, civility)

    def test_add02_from_widget(self):
        count = FakeSector.objects.count()

        url = reverse('creme_config__create_instance_from_widget', args=('creme_core', 'fake_sector'))
        self.assertGET200(url)

        title = 'Music'
        response = self.client.post(url, data={'title': title})
        self.assertNoFormError(response)
        self.assertEqual(count + 1, FakeSector.objects.count())

        sector = self.get_object_or_fail(FakeSector, title=title, is_custom=True)
        self.assertEqual(count + 1, sector.order)  # order is set to max
        self.assertWidgetResponse(response, sector)

        title = 'Music & movie'
        response = self.client.post(url, data={'title': title})
        sector = self.get_object_or_fail(FakeSector, title=title)
        self.assertEqual(count + 2, sector.order)  # order is set to max
        self.assertWidgetResponse(response, sector)

    def test_edit01(self):
        title = 'herr'
        shortcut = 'H.'
        civ = FakeCivility.objects.create(title=title, shortcut=shortcut)

        url = reverse('creme_config__edit_instance', args=('creme_core', 'fake_civility', civ.id,))
        self.assertGET200(url)

        title = title.title()
        self.assertNoFormError(self.client.post(url, data={'title': title,
                                                           'shortcut': shortcut,
                                                          }
                                               )
                              )

        civ = self.refresh(civ)
        self.assertEqual(title,    civ.title)
        self.assertEqual(shortcut, civ.shortcut)

    def test_edit02(self):
        "Order not changed"
        count = FakeSector.objects.count()
        sector = FakeSector.objects.create(title='music', order=count + 1)

        url = reverse('creme_config__edit_instance', args=('creme_core', 'fake_sector', sector.id,))
        self.assertGET200(url)

        title = sector.title.title()
        self.assertNoFormError(self.client.post(url, data={'title': title}))

        new_sector = self.refresh(sector)
        self.assertEqual(title,        new_sector.title)
        self.assertEqual(sector.order, new_sector.order)

    def test_delete01(self):
        civ = FakeCivility.objects.create(title='Herr')
        url = reverse('creme_config__delete_instance', args=('creme_core', 'fake_civility'))
        data = {'id': civ.pk}
        self.assertGET404(url, data=data)
        self.assertPOST200(url, data=data)
        self.assertDoesNotExist(civ)

    def test_delete02(self):
        "Not custom instance"
        sector = FakeSector.objects.create(title='Music', is_custom=False)
        self.assertPOST404(reverse('creme_config__delete_instance', args=('creme_core', 'fake_sector')),
                           data={'id': sector.pk},
                          )
        self.assertStillExists(sector)

    # def test_reload_model_block(self):
    #     response = self.assertGET200(reverse('creme_config__reload_model_block_legacy',
    #                                          args=(ContentType.objects.get_for_model(FakeCivility).id,),
    #                                         )
    #                                 )
    #
    #     with self.assertNoException():
    #         result = json_load(response.content)
    #
    #     self.assertIsInstance(result, list)
    #     self.assertEqual(1, len(result))
    #
    #     result = result[0]
    #     self.assertIsInstance(result, list)
    #     self.assertEqual(2, len(result))
    #
    #     brick_id = GenericModelBrick.id_
    #     self.assertEqual(brick_id, result[0])
    #     self.assertIn(' id="%s"' % brick_id, result[1])

    def test_reload_model_brick(self):
        response = self.assertGET200(reverse('creme_config__reload_model_brick',
                                             args=('creme_core', 'fake_civility'),
                                            )
                                    )

        # with self.assertNoException():
        #     results = json_load(response.content)
        results = response.json()
        self.assertIsInstance(results, list)
        self.assertEqual(1, len(results))

        result = results[0]
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))

        brick_id = GenericModelBrick.id_
        self.assertEqual(brick_id, result[0])
        self.get_brick_node(self.get_html_tree(result[1]), brick_id)

    def test_reload_app_bricks01(self):
        url = reverse('creme_config__reload_app_bricks', args=('creme_core',))
        self.assertGET404(url)
        self.assertGET404(url, data={'brick_id': PropertyTypesBrick.id_})

        response = self.assertGET200(url, data={'brick_id': SettingsBrick.id_})

        # with self.assertNoException():
        #     results = json_load(response.content)
        results = response.json()
        self.assertIsInstance(results, list)
        self.assertEqual(1, len(results))

        result = results[0]
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))

        brick_id = SettingsBrick.id_
        self.assertEqual(brick_id, result[0])
        self.get_brick_node(self.get_html_tree(result[1]), brick_id)

    def test_reload_app_bricks02(self):
        response = self.assertGET200(reverse('creme_config__reload_app_bricks', args=('creme_core',)),
                                     data={'brick_id': FakeAppPortalBrick.id_}
                                    )

        # with self.assertNoException():
        #     result = json_load(response.content)
        results = response.json()
        self.assertIsInstance(results, list)
        self.assertEqual(1, len(results))

        result = results[0]
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))

        brick_id = FakeAppPortalBrick.id_
        self.assertEqual(brick_id, result[0])
        self.get_brick_node(self.get_html_tree(result[1]), brick_id)

    # def test_incr_order01(self):
    #     create_sector = FakeSector.objects.create
    #     sector1 = create_sector(title='Music', order=1)
    #     sector2 = create_sector(title='Movie',   order=2)
    #
    #     url = self._build_down_url(sector1.id)
    #     self.assertGET404(url)
    #     self.assertPOST200(url)
    #
    #     self.assertEqual(2, self.refresh(sector1).order)
    #     self.assertEqual(1, self.refresh(sector2).order)
    #
    # def test_incr_order02(self):
    #     create_sector = FakeSector.objects.create
    #     sector1 = create_sector(title='Music', order=1)
    #     sector2 = create_sector(title='Movie', order=2)
    #     sector3 = create_sector(title='Book',  order=3)
    #     sector4 = create_sector(title='Web',   order=4)
    #
    #     self.assertPOST200(self._build_down_url(sector2.id))
    #
    #     self.assertEqual(1, self.refresh(sector1).order)
    #     self.assertEqual(3, self.refresh(sector2).order)
    #     self.assertEqual(2, self.refresh(sector3).order)
    #     self.assertEqual(4, self.refresh(sector4).order)
    #
    # def test_incr_order03(self):
    #     "Errors"
    #     create_sector = FakeSector.objects.create
    #     sector1 = create_sector(title='Music', order=1)
    #     sector2 = create_sector(title='Movie',   order=2)
    #
    #     self.assertPOST404(self._build_down_url(sector2.id))
    #     self.assertPOST404(self._build_down_url(sector2.id + sector1.id))  # Odd pk

    # def test_decr_order01(self):
    #     create_sector = FakeSector.objects.create
    #     sector1 = create_sector(title='Music', order=1)
    #     sector2 = create_sector(title='Movie', order=2)
    #     sector3 = create_sector(title='Book',  order=3)
    #     sector4 = create_sector(title='Web',   order=4)
    #
    #     self.assertPOST200(self._build_up_url(sector3.id))
    #
    #     self.assertEqual(1, self.refresh(sector1).order)
    #     self.assertEqual(3, self.refresh(sector2).order)
    #     self.assertEqual(2, self.refresh(sector3).order)
    #     self.assertEqual(4, self.refresh(sector4).order)
    #
    # def test_decr_order02(self):
    #     "Error: can move up the first one"
    #     create_sector = FakeSector.objects.create
    #     sector1 = create_sector(title='Music', order=1)
    #     create_sector(title='Movie', order=2)
    #
    #     # self.assertPOST404(self.UP_URL % sector1.id)
    #     self.assertPOST404(self._build_up_url(sector1.id))

    def test_reorder(self):
        create_sector = FakeSector.objects.create
        sector1 = create_sector(title='Music', order=1)
        sector2 = create_sector(title='Movie', order=2)
        sector3 = create_sector(title='Book',  order=3)
        sector4 = create_sector(title='Web',   order=4)

        url = reverse('creme_config__reorder_instance', args=('creme_core', 'fake_sector', sector1.id))
        self.assertGET404(url, data={'target': 3})

        self.client.post(url, data={'target': 3})
        self.assertEqual(3, self.refresh(sector1).order)
        self.assertEqual(1, self.refresh(sector2).order)
        self.assertEqual(2, self.refresh(sector3).order)
        self.assertEqual(4, self.refresh(sector4).order)
