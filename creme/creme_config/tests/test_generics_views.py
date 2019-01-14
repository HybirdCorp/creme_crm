# -*- coding: utf-8 -*-

try:
    from django.apps import apps
    from django.urls import reverse
    from django.utils.translation import ugettext as _

    # from creme.creme_core.forms import CremeModelForm
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_bricks import FakeAppPortalBrick
    from creme.creme_core.tests.fake_models import (FakeCivility, FakeSector,
            FakePosition, FakeLegalForm)
    from creme.creme_core.tests.views.base import BrickTestCaseMixin

    from ..bricks import GenericModelBrick, PropertyTypesBrick, SettingsBrick
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class GenericModelConfigTestCase(CremeTestCase, BrickTestCaseMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._sector_backup = list(FakeSector.objects.all())
        FakeSector.objects.all().delete()

        # # We import here in order to not launch the automatic registration before the fake bricks are registered.
        # from .. import registry
        # cls._ConfigRegistry = registry._ConfigRegistry
        # cls.NotRegisteredInConfig = registry.NotRegisteredInConfig

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        FakeSector.objects.all().delete()
        FakeSector.objects.bulk_create(cls._sector_backup)

    def setUp(self):
        self.login()

    def test_portals(self):
        response = self.assertGET200(reverse('creme_config__app_portal', args=('creme_core',)))
        self.assertTemplateUsed(response, 'creme_config/generics/app-portal.html')

        self.assertGET404(reverse('creme_config__app_portal', args=('unexistingapp',)))

        response = self.assertGET200(reverse('creme_config__model_portal', args=('creme_core', 'fake_civility')))
        self.assertTemplateUsed(response, 'creme_config/generics/model-portal.html')

        self.assertGET404(reverse('creme_config__model_portal', args=('creme_core', 'unexistingmodel')))

        if apps.is_installed('creme.persons'):
            self.assertGET200(reverse('creme_config__app_portal', args=('persons',)))
            self.assertGET200(reverse('creme_config__model_portal', args=('persons', 'civility')))
            self.assertGET404(reverse('creme_config__model_portal', args=('persons', 'unexistingmodel')))

    def test_add01(self):
        count = FakeCivility.objects.count()

        url = reverse('creme_config__create_instance', args=('creme_core', 'fake_civility'))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/form/add-popup.html')

        context = response.context
        self.assertEqual(_('Create'), context.get('title'))
        self.assertEqual(_('Save'),   context.get('submit_label'))

        title = 'Generalissime'
        shortcut = 'G.'
        self.assertNoFormError(self.client.post(url, data={'title': title, 'shortcut': shortcut}))
        self.assertEqual(count + 1, FakeCivility.objects.count())
        civility = self.get_object_or_fail(FakeCivility, title=title)
        self.assertEqual(shortcut, civility.shortcut)

    def test_add02(self):
        count = FakeSector.objects.count()

        url = reverse('creme_config__create_instance', args=('creme_core', 'fake_sector'))
        context = self.assertGET200(url).context
        self.assertEqual(_('Create a sector'), context.get('title'))
        self.assertEqual(_('Save the sector'), context.get('submit_label'))

        title = 'Music'
        self.assertNoFormError(self.client.post(url, data={'title': title}))
        self.assertEqual(count + 1, FakeSector.objects.count())

        sector = self.get_object_or_fail(FakeSector, title=title, is_custom=True)
        self.assertEqual(count + 1, sector.order)  # order is set to max

        title = 'Music & movie'
        self.client.post(url, data={'title': title})
        sector = self.get_object_or_fail(FakeSector, title=title)
        self.assertEqual(count + 2, sector.order)  # order is set to max

    def test_add03(self):
        "Disabled creation (see creme.creme_core.apps.CremeCoreConfig.register_creme_config())."
        self.assertGET409(reverse('creme_config__create_instance',
                                  args=('creme_core', 'fake_position'),
                                 )
                         )

    def test_add04(self):
        "Not vanilla-URL (see creme.creme_core.apps.CremeCoreConfig.register_creme_config())."
        self.assertGET409(reverse('creme_config__create_instance',
                                  args=('creme_core', 'fake_legalform'),
                                 )
                         )

    def assertWidgetResponse(self, response, instance):
        self.assertEqual({'added': [[instance.id, str(instance)]],
                          'value': instance.id
                         },
                         response.json()
                        )

    def test_add01_from_widget(self):
        count = FakeCivility.objects.count()

        url = reverse('creme_config__create_instance_from_widget',
                      args=('creme_core', 'fake_civility')
                     )
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/form/add-popup.html')

        context = response.context
        self.assertEqual(_('Create'), context.get('title'))
        self.assertEqual(_('Save'), context.get('submit_label'))

        # ---
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

        url = reverse('creme_config__create_instance_from_widget',
                      args=('creme_core', 'fake_sector')
                     )
        context = self.assertGET200(url).context

        self.assertEqual(_('Create a sector'), context.get('title'))
        self.assertEqual(_('Save the sector'), context.get('submit_label'))

        # ---
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
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/form/edit-popup.html')
        self.assertEqual(_('Edit «{object}»').format(object=civ), response.context.get('title'))

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

    def test_edit03(self):
        "Edition disabled (see creme.creme_core.apps.CremeCoreConfig.register_creme_config())."
        lf = FakeLegalForm.objects.create(title='Foundation')
        self.assertGET409(reverse('creme_config__edit_instance',
                                  args=('creme_core', 'fake_legalform', lf.id,)
                                 )
                          )

    def test_edit04(self):
        "Not vanilla-URL (see creme.creme_core.apps.CremeCoreConfig.register_creme_config())."
        position = FakePosition.objects.first()

        self.assertGET409(reverse('creme_config__edit_instance',
                                  args=('creme_core', 'fake_position', position.id),
                                 )
                         )

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

    def test_reload_model_brick(self):
        response = self.assertGET200(reverse('creme_config__reload_model_brick',
                                             args=('creme_core', 'fake_civility'),
                                            )
                                    )

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

        results = response.json()
        self.assertIsInstance(results, list)
        self.assertEqual(1, len(results))

        result = results[0]
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))

        brick_id = FakeAppPortalBrick.id_
        self.assertEqual(brick_id, result[0])
        self.get_brick_node(self.get_html_tree(result[1]), brick_id)

    def test_reorder(self):
        create_sector = FakeSector.objects.create
        sector1 = create_sector(title='Music', order=1)
        sector2 = create_sector(title='Movie', order=2)
        sector3 = create_sector(title='Book',  order=3)
        sector4 = create_sector(title='Web',   order=4)

        url = reverse('creme_config__reorder_instance', args=('creme_core', 'fake_sector', sector1.id))
        self.assertGET(405, url, data={'target': 3})

        self.assertPOST200(url, data={'target': 3})
        self.assertEqual(3, self.refresh(sector1).order)
        self.assertEqual(1, self.refresh(sector2).order)
        self.assertEqual(2, self.refresh(sector3).order)
        self.assertEqual(4, self.refresh(sector4).order)
