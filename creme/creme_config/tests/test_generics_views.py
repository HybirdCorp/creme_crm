# -*- coding: utf-8 -*-

try:
    from json import JSONEncoder, loads

    from django.apps import apps
#    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.gui.block import Block
    from creme.creme_core.forms import CremeModelForm
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import (FakeCivility as Civility,
            FakeSector as Sector, FakePosition as Position)

#    from creme.persons.models import Civility

#    from creme.billing.models import InvoiceStatus

    from ..blocks import generic_models_block
    from ..registry import _ConfigRegistry, NotRegisteredInConfig
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class GenericModelConfigTestCase(CremeTestCase):
    DOWN_URL = '/creme_config/creme_core/fake_sector/down/%s'
    UP_URL   = '/creme_config/creme_core/fake_sector/up/%s'

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core')

        cls._sector_backup = list(Sector.objects.all())
        Sector.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        CremeTestCase.tearDownClass()
        Sector.objects.bulk_create(cls._sector_backup)

    def setUp(self):
        self.login()

    def test_registry_register_model(self):
        class SectorForm(CremeModelForm):
            class Meta(CremeModelForm.Meta):
                model = Sector

        registry = _ConfigRegistry()
        registry.register((Civility, 'civility'),
                          (Sector,   'sector', SectorForm),
                         )

        with self.assertNoException():
            app_conf = registry.get_app('creme_core')

        with self.assertNoException():
            model_conf = app_conf.get_model_conf(model=Civility)
        self.assertEqual('civility', model_conf.name_in_url)
        self.assertIsSubclass(model_conf.model_form, CremeModelForm)
        self.assertEqual('Test civility', model_conf.verbose_name)

        with self.assertNoException():
            model_conf = app_conf.get_model_conf(model=Sector)
        self.assertIsSubclass(model_conf.model_form, SectorForm)

        with self.assertNoException():
            model_conf = app_conf.get_model_conf(ContentType.objects.get_for_model(Sector).id)

        self.assertEqual('sector', model_conf.name_in_url)

    def test_registry_unregister_model01(self):
        "Unregister after the registration"
        registry = _ConfigRegistry()
        registry.register((Civility, 'civility'),
                          (Sector,   'sector'),
                          (Position, 'position'),
                         )
        registry.unregister(Civility, Position)

        with self.assertNoException():
            app_conf = registry.get_app('creme_core')

        get_model_conf = app_conf.get_model_conf

        with self.assertNoException():
            get_model_conf(model=Sector)

        self.assertRaises(NotRegisteredInConfig, get_model_conf, model=Civility)
        self.assertRaises(NotRegisteredInConfig, get_model_conf, model=Position)

    def test_registry_unregister_model02(self):
        "Unregister before the registration"
        registry = _ConfigRegistry()
        registry.unregister(Civility, Position)
        registry.register((Civility, 'civility'),
                          (Sector,   'sector'),
                          (Position, 'position'),
                         )

        with self.assertNoException():
            app_conf = registry.get_app('creme_core')

        get_model_conf = app_conf.get_model_conf

        with self.assertNoException():
            get_model_conf(model=Sector)

        self.assertRaises(NotRegisteredInConfig, get_model_conf, model=Civility)
        self.assertRaises(NotRegisteredInConfig, get_model_conf, model=Position)

    def test_registry_register_blocks(self):
        class TestBlock1(Block):
            id_ = Block.generate_id('creme_config', 'test_config_registry1')

        class TestBlock2(Block):
            id_ = Block.generate_id('creme_config', 'test_config_registry2')

        block1 = TestBlock1()
        block2 = TestBlock2()

        registry = _ConfigRegistry()
        registry.register_blocks(('creme_core', block1),
                                 ('documents',  block2),
                                )

        with self.assertNoException():
            app_conf = registry.get_app('creme_core')

        blocks = app_conf.blocks()
        self.assertIn(block1,    blocks)
        self.assertNotIn(block2, blocks)

        with self.assertNoException():
            app_conf = registry.get_app('documents')

        blocks = app_conf.blocks()
        self.assertIn(block2,    blocks)
        self.assertNotIn(block1, blocks)

    def test_registry_register_userblocks(self):
        class TestUserBlock1(Block):
            id_ = Block.generate_id('creme_config', 'test_config_registry1')

        class TestUserBlock2(Block):
            id_ = Block.generate_id('creme_config', 'test_config_registry2')

        block1 = TestUserBlock1()
        block2 = TestUserBlock2()
        registry = _ConfigRegistry()

        registry.register_userblocks(block1, block2)
        self.assertIn(block1, registry.userblocks)
        self.assertIn(block2, registry.userblocks)

    def test_portals(self):
        self.assertGET200('/creme_config/creme_core/portal/')
        self.assertGET200('/creme_config/creme_core/fake_civility/portal/')
        self.assertGET404('/creme_config/creme_core/unexistingmodel/portal/')

        self.assertGET404('/creme_config/unexsitingapp/portal/')

#        if 'creme.persons' in settings.INSTALLED_APPS:
        if apps.is_installed('creme.persons'):
            self.assertGET200('/creme_config/persons/portal/')
            self.assertGET200('/creme_config/persons/civility/portal/')
            self.assertGET404('/creme_config/persons/unexistingmodel/portal/')

        #if 'creme.billing' in settings.INSTALLED_APPS:
            #self.assertGET200('/creme_config/billing/invoice_status/portal/')

    def test_add01(self):
        count = Civility.objects.count()

#        url = '/creme_config/persons/civility/add/'
        url = '/creme_config/creme_core/fake_civility/add/'
        self.assertGET200(url)

        title = 'Generalissime'
        shortcut = 'G.'
        self.assertNoFormError(self.client.post(url, data={'title': title, 'shortcut': shortcut}))
        self.assertEqual(count + 1, Civility.objects.count())
        civility = self.get_object_or_fail(Civility, title=title)
        self.assertEqual(shortcut, civility.shortcut)

    def test_add02(self):
#        count = InvoiceStatus.objects.count()
#
#        url = '/creme_config/billing/invoice_status/add/'
#        self.assertGET200(url)
#
#        name = 'Okidoki'
#        self.assertNoFormError(self.client.post(url, data={'name': name}))
#        self.assertEqual(count + 1, InvoiceStatus.objects.count())
#
#        status = self.get_object_or_fail(InvoiceStatus, name=name, is_custom=True)
#        self.assertEqual(count + 1, status.order) #order is set to max
#
#        name = 'Youkaidi'
#        self.client.post(url, data={'name': name})
#        status = self.get_object_or_fail(InvoiceStatus, name=name)
#        self.assertEqual(count + 2, status.order) #order is set to max
        count = Sector.objects.count()

        url = '/creme_config/creme_core/fake_sector/add/'
        self.assertGET200(url)

        title = 'Music'
        self.assertNoFormError(self.client.post(url, data={'title': title}))
        self.assertEqual(count + 1, Sector.objects.count())

        sector = self.get_object_or_fail(Sector, title=title, is_custom=True)
        self.assertEqual(count + 1, sector.order) #order is set to max

        title = 'Music & movie'
        self.client.post(url, data={'title': title})
        sector = self.get_object_or_fail(Sector, title=title)
        self.assertEqual(count + 2, sector.order) #order is set to max

    def assertWidgetResponse(self, response, instance):
        #TODO: json.dumps
        self.assertEqual(u'<json>%s</json>' % JSONEncoder().encode({
                            'added': [[instance.id, unicode(instance)]], 
                            'value': instance.id
                         }), 
                         response.content
                        )

    def test_add01_from_widget(self):
        count = Civility.objects.count()

#        url = '/creme_config/persons/civility/add_widget/'
        url = '/creme_config/creme_core/fake_civility/add_widget/'
        self.assertGET200(url)

        title = 'Generalissime'
        shortcut = 'G.'
        response = self.client.post(url, data={'title': title, 'shortcut': shortcut})
        self.assertNoFormError(response)
        self.assertEqual(count + 1, Civility.objects.count())

        civility = self.get_object_or_fail(Civility, title=title)
        self.assertEqual(shortcut, civility.shortcut)
        self.assertWidgetResponse(response, civility)

    def test_add02_from_widget(self):
#        count = InvoiceStatus.objects.count()
#
#        url = '/creme_config/billing/invoice_status/add_widget/'
#        self.assertGET200(url)
#
#        name = 'Okidoki'
#        response = self.client.post(url, data={'name': name})
#        self.assertNoFormError(response)
#        self.assertEqual(count + 1, InvoiceStatus.objects.count())
#
#        status = self.get_object_or_fail(InvoiceStatus, name=name, is_custom=True)
#        self.assertEqual(count + 1, status.order) #order is set to max
#        self.assertWidgetResponse(response, status)
#
#        name = 'Youkaidi'
#        response = self.client.post(url, data={'name': name})
#        status = self.get_object_or_fail(InvoiceStatus, name=name)
#        self.assertEqual(count + 2, status.order) #order is set to max
#        self.assertWidgetResponse(response, status)
        count = Sector.objects.count()

        url = '/creme_config/creme_core/fake_sector/add_widget/'
        self.assertGET200(url)

        title = 'Music'
        response = self.client.post(url, data={'title': title})
        self.assertNoFormError(response)
        self.assertEqual(count + 1, Sector.objects.count())

        sector = self.get_object_or_fail(Sector, title=title, is_custom=True)
        self.assertEqual(count + 1, sector.order) #order is set to max
        self.assertWidgetResponse(response, sector)

        title = 'Music & movie'
        response = self.client.post(url, data={'title': title})
        sector = self.get_object_or_fail(Sector, title=title)
        self.assertEqual(count + 2, sector.order) #order is set to max
        self.assertWidgetResponse(response, sector)

    def test_edit01(self):
        title = 'herr'
        shortcut = 'H.'
        civ = Civility.objects.create(title=title, shortcut=shortcut)

#        url = '/creme_config/persons/civility/edit/%s' % civ.id
        url = '/creme_config/creme_core/fake_civility/edit/%s' % civ.id
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
#        count = InvoiceStatus.objects.count()
#        status = InvoiceStatus.objects.create(name='okidoki',  order=count + 1)
#
#        url = '/creme_config/billing/invoice_status/edit/%s' % status.id
#        self.assertGET200(url)
#
#        name = status.name.title()
#        self.assertNoFormError(self.client.post(url, data={'name': name}))
#
#        new_status = self.refresh(status)
#        self.assertEqual(name,         new_status.name)
#        self.assertEqual(status.order, new_status.order)
        count = Sector.objects.count()
        sector = Sector.objects.create(title='music', order=count + 1)

        url = '/creme_config/creme_core/fake_sector/edit/%s' % sector.id
        self.assertGET200(url)

        title = sector.title.title()
        self.assertNoFormError(self.client.post(url, data={'title': title}))

        new_sector = self.refresh(sector)
        self.assertEqual(title,        new_sector.title)
        self.assertEqual(sector.order, new_sector.order)

    def test_delete01(self):
        civ = Civility.objects.create(title='Herr')
#        url = '/creme_config/persons/civility/delete'
        url = '/creme_config/creme_core/fake_civility/delete'
        data = {'id': civ.pk}
        self.assertGET404(url, data=data)
        self.assertPOST200(url, data=data)
        self.assertDoesNotExist(civ)

    def test_delete02(self):
        "Not custom instance"
#        status = InvoiceStatus.objects.create(name='Okidoki', is_custom=False)
#        self.assertPOST404('/creme_config/billing/invoice_status/delete', data={'id': status.pk})
#        self.assertStillExists(status)
        sector = Sector.objects.create(title='Music', is_custom=False)
        self.assertPOST404('/creme_config/creme_core/fake_sector/delete',
                           data={'id': sector.pk},
                          )
        self.assertStillExists(sector)

    def test_reload_block(self):
        response = self.assertGET200('/creme_config/models/%s/reload/' %
                                        ContentType.objects.get_for_model(Civility).id
                                    )

        with self.assertNoException():
            result = loads(response.content)

        self.assertIsInstance(result, list)
        self.assertEqual(1, len(result))

        result = result[0]
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))
        self.assertEqual(generic_models_block.id_, result[0])
        self.assertIn(' id="%s"' % generic_models_block.id_, result[1])

    def test_incr_order01(self):
        create_sector = Sector.objects.create
        sector1 = create_sector(title='Music', order=1)
        sector2 = create_sector(title='Movie',   order=2)

        url = self.DOWN_URL % sector1.id
        self.assertGET404(url)
        self.assertPOST200(url)

        self.assertEqual(2, self.refresh(sector1).order)
        self.assertEqual(1, self.refresh(sector2).order)

    def test_incr_order02(self):
        create_sector = Sector.objects.create
        sector1 = create_sector(title='Music', order=1)
        sector2 = create_sector(title='Movie', order=2)
        sector3 = create_sector(title='Book',  order=3)
        sector4 = create_sector(title='Web',   order=4)

        self.assertPOST200(self.DOWN_URL % sector2.id)

        self.assertEqual(1, self.refresh(sector1).order)
        self.assertEqual(3, self.refresh(sector2).order)
        self.assertEqual(2, self.refresh(sector3).order)
        self.assertEqual(4, self.refresh(sector4).order)

    def test_incr_order03(self):
        "Errrors"
        create_sector = Sector.objects.create
        sector1 = create_sector(title='Music', order=1)
        sector2 = create_sector(title='Movie',   order=2)

        url = self.DOWN_URL
        self.assertPOST404(url % sector2.id)
        self.assertPOST404(url % (sector2.id + sector1.id)) #odd pk

    def test_decr_order01(self):
        create_sector = Sector.objects.create
        sector1 = create_sector(title='Music', order=1)
        sector2 = create_sector(title='Movie',   order=2)
        sector3 = create_sector(title='Book',         order=3)
        sector4 = create_sector(title='Web',        order=4)

        self.assertPOST200(self.UP_URL % sector3.id)

        self.assertEqual(1, self.refresh(sector1).order)
        self.assertEqual(3, self.refresh(sector2).order)
        self.assertEqual(2, self.refresh(sector3).order)
        self.assertEqual(4, self.refresh(sector4).order)

    def test_decr_order02(self):
        "Error: can move up the first one"
        create_sector = Sector.objects.create
        sector1 = create_sector(title='Music', order=1)
        create_sector(title='Movie', order=2)

        self.assertPOST404(self.UP_URL % sector1.id)
