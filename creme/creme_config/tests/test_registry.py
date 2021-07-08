# -*- coding: utf-8 -*-

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_config.bricks import GenericModelBrick
from creme.creme_config.forms.generics import DeletionForm
from creme.creme_config.registry import (
    NotRegisteredInConfig,
    RegistrationError,
    _ConfigRegistry,
)
from creme.creme_core.core.setting_key import SettingKey, _SettingKeyRegistry
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.gui.bricks import SimpleBrick, _BrickRegistry
from creme.creme_core.models import FakeCivility, FakePosition, FakeSector
from creme.creme_core.tests.base import CremeTestCase
from creme.documents.models import DocumentCategory


class RegistryTestCase(CremeTestCase):
    def test_get_app_registry(self):
        registry = _ConfigRegistry()
        self.assertFalse([*registry.apps()])

        with self.assertRaises(KeyError):
            registry.get_app_registry('creme_core')

        with self.assertRaises(LookupError):
            registry.get_app_registry('unknownapp')

        app_registry = registry.get_app_registry('creme_core', create=True)
        self.assertEqual('creme_core', app_registry.name)
        self.assertEqual(_('Core'),    app_registry.verbose_name)
        self.assertEqual(
            reverse('creme_config__app_portal', args=('creme_core',)),
            app_registry.portal_url,
        )

        self.assertListEqual([app_registry], [*registry.apps()])

        self.assertIs(app_registry, registry.get_app_registry('creme_core', create=True))
        self.assertIs(app_registry, registry.get_app_registry('creme_core'))

        # --
        registry.get_app_registry('documents', create=True)
        self.assertEqual(2, len([*registry.apps()]))

    def test_register_model01(self):
        user = self.create_user()

        registry = _ConfigRegistry()

        model_name = 'civility'
        registry.register_model(FakeCivility, model_name=model_name)
        app_registries = [*registry.apps()]
        self.assertEqual(1, len(app_registries))

        app_registry = app_registries[0]
        self.assertEqual('creme_core', app_registry.name)

        model_configs = [*app_registry.models()]
        self.assertEqual(1, len(model_configs))

        model_config = model_configs[0]
        self.assertEqual(FakeCivility, model_config.model)
        self.assertEqual(model_name,   model_config.model_name)

        brick = model_config.get_brick()
        self.assertIsInstance(brick, GenericModelBrick)
        self.assertEqual('creme_core', brick.app_name)
        self.assertEqual(FakeCivility, brick.model_config.model)

        with self.assertRaises(NotRegisteredInConfig):
            app_registry.get_model_conf(FakeSector)

        # Creator ---
        creator = model_config.creator
        creation_form = creator.form_class
        self.assertIsSubclass(creation_form, CremeModelForm)
        self.assertEqual(FakeCivility, creation_form._meta.model)
        self.assertIsNone(creator.url_name)
        self.assertEqual(
            creator.get_url(user),
            reverse('creme_config__create_instance', args=('creme_core', 'civility')),
        )

        # Editor ---
        editor = model_config.editor
        edition_form = editor.form_class
        self.assertIsSubclass(edition_form, CremeModelForm)
        self.assertEqual(FakeCivility, edition_form._meta.model)
        self.assertIsNone(editor.url_name)

        civ = FakeCivility.objects.first()
        self.assertEqual(
            editor.get_url(civ, user),
            reverse(
                'creme_config__edit_instance', args=('creme_core', 'civility', civ.id),
            ),
        )

        # Deletor ---
        deletor = model_config.deletor
        deletion_form = deletor.form_class
        self.assertIsSubclass(deletion_form, DeletionForm)
        self.assertIsNone(deletor.url_name)
        self.assertEqual(
            deletor.get_url(civ, user),
            reverse(
                'creme_config__delete_instance', args=('creme_core', 'civility', civ.id),
            ),
        )

    def test_register_model02(self):
        "Another model ; get_app()/get_model_conf() ; no 'name_in_url' argument."
        user = self.create_user()
        registry = _ConfigRegistry()

        registry.register_model(DocumentCategory)
        app_registry = registry.get_app_registry('documents')
        self.assertEqual('documents',    app_registry.name)
        self.assertEqual(_('Documents'), app_registry.verbose_name)

        model_config = app_registry.get_model_conf(DocumentCategory)
        self.assertEqual(DocumentCategory,   model_config.model)
        self.assertEqual('documentcategory', model_config.model_name)

        self.assertEqual(
            model_config.creator.get_url(user),
            reverse(
                'creme_config__create_instance',
                args=('documents', 'documentcategory'),
            ),
        )

        sector = FakeSector.objects.first()
        self.assertEqual(
            model_config.editor.get_url(sector, user=user),
            reverse(
                'creme_config__edit_instance',
                args=('documents', 'documentcategory', sector.id),
            ),
        )

        self.assertEqual(
            model_config.deletor.get_url(sector, user=user),
            reverse(
                'creme_config__delete_instance',
                args=('documents', 'documentcategory', sector.id),
            ),
        )

    def test_register_model03(self):
        "Change name_in_url."
        user = self.create_user()

        registry = _ConfigRegistry()
        self.assertFalse([*registry.apps()])

        registry.register_model(FakeCivility)
        model_config = registry.get_app_registry('creme_core').get_model_conf(FakeCivility)

        model_config.model_name = new_name = 'civ'
        self.assertEqual(new_name, model_config.model_name)
        self.assertEqual(
            model_config.creator.get_url(user=user),
            reverse('creme_config__create_instance', args=('creme_core', new_name)),
        )

        civ = FakeCivility.objects.first()
        self.assertEqual(
            model_config.editor.get_url(civ, user=user),
            reverse('creme_config__edit_instance', args=('creme_core', new_name, civ.id)),
        )
        self.assertEqual(
            model_config.deletor.get_url(civ, user=user),
            reverse('creme_config__delete_instance', args=('creme_core', new_name, civ.id)),
        )

        # --
        with self.assertRaises(ValueError):
            registry.register_model(FakeSector, 'my-sector')  # Invalid char '-'

    def test_register_model04(self):
        "Register specific forms."
        registry = _ConfigRegistry()

        class CivCreationForm(CremeModelForm):
            class Meta:
                model = FakeCivility
                fields = ('title', )

        class CivEditionForm(CremeModelForm):
            class Meta:
                model = FakeCivility
                fields = ('shortcut', )

        class CivDeletionForm(DeletionForm):
            pass

        registry.register_model(FakeCivility) \
                .creation(form_class=CivCreationForm) \
                .edition(form_class=CivEditionForm) \
                .deletion(form_class=CivDeletionForm)

        model_config = registry.get_app_registry('creme_core').get_model_conf(FakeCivility)
        self.assertIsSubclass(model_config.creator.form_class, CivCreationForm)
        self.assertIsSubclass(model_config.editor.form_class, CivEditionForm)
        self.assertIsSubclass(model_config.deletor.form_class, CivDeletionForm)

    def test_register_model05(self):
        "Register specific URLs."
        user = self.create_user()
        registry = _ConfigRegistry()

        creation_url_name = 'creme_config__create_team'
        edition_url_name = 'creme_config__edit_team'  # NB: need an URL with an int arg
        deletion_url_name = 'creme_config__edit_user'  # idem

        registry.register_model(FakeCivility) \
                .edition(url_name=edition_url_name) \
                .deletion(url_name=deletion_url_name) \
                .creation(url_name=creation_url_name)

        model_config = registry.get_app_registry('creme_core').get_model_conf(FakeCivility)
        creator = model_config.creator
        self.assertEqual(creator.url_name, creation_url_name)
        self.assertEqual(creator.get_url(user=user), reverse(creation_url_name))

        civ = FakeCivility.objects.first()
        editor = model_config.editor
        self.assertEqual(
            editor.get_url(civ, user=user),
            reverse(edition_url_name, args=(civ.id,)),
        )

        deletor = model_config.deletor
        self.assertEqual(
            deletor.get_url(civ, user=user),
            reverse(deletion_url_name, args=(civ.id,)),
        )

        # Back to default
        creator.url_name = None
        self.assertEqual(
            creator.get_url(user),
            reverse(
                'creme_config__create_instance',
                args=('creme_core', 'fakecivility'),
            ),
        )

        editor.url_name = None
        self.assertEqual(
            editor.get_url(civ, user),
            reverse(
                'creme_config__edit_instance',
                args=('creme_core', 'fakecivility', civ.id),
            ),
        )

    def test_register_model06(self):
        "Disable edition forms."
        user1 = self.create_user(index=0)
        user2 = self.create_user(index=1)
        registry = _ConfigRegistry()

        civ1, civ2 = FakeCivility.objects.all()[:2]
        registry.register_model(FakeCivility).edition(
            enable_func=lambda instance, user: instance.id == civ1.id
        )

        model_config = registry.get_app_registry('creme_core').get_model_conf(FakeCivility)
        self.assertIsSubclass(model_config.creator.form_class, CremeModelForm)

        editor = model_config.editor
        self.assertIsSubclass(editor.form_class, CremeModelForm)

        url1 = reverse(
            'creme_config__edit_instance',
            args=('creme_core', 'fakecivility', civ1.id),
        )
        self.assertEqual(url1, editor.get_url(instance=civ1, user=user1))
        self.assertEqual(url1, editor.get_url(instance=civ1, user=user2))
        self.assertIsNone(editor.get_url(instance=civ2, user=user1))

        # Disable with user
        user_name = user1.username
        editor.enable_func = lambda instance, user: user.username == user_name
        self.assertEqual(url1, editor.get_url(instance=civ1, user=user1))
        self.assertEqual(
            reverse(
                'creme_config__edit_instance',
                args=('creme_core', 'fakecivility', civ2.id),
            ),
            editor.get_url(instance=civ2, user=user1),
        )
        self.assertIsNone(editor.get_url(instance=civ1, user=user2))

    def test_register_model07(self):
        "Disable creation forms."
        user1 = self.create_user(index=0)
        user2 = self.create_user(index=1)
        registry = _ConfigRegistry()

        user_name = user1.username
        registry.register_model(FakeCivility).creation(
            enable_func=lambda user: user.username == user_name
        )

        model_config = registry.get_app_registry('creme_core').get_model_conf(FakeCivility)
        creator = model_config.creator
        self.assertIsSubclass(creator.form_class, CremeModelForm)
        self.assertEqual(
            reverse(
                'creme_config__create_instance',
                args=('creme_core', 'fakecivility')
            ),
            creator.get_url(user=user1)
        )
        self.assertIsNone(creator.get_url(user=user2))

        editor = model_config.editor
        self.assertIsSubclass(editor.form_class, CremeModelForm)

        civ = FakeCivility.objects.first()
        self.assertEqual(
            reverse(
                'creme_config__edit_instance',
                args=('creme_core', 'fakecivility', civ.id),
            ),
            editor.get_url(civ, user=user1),
        )

    def test_register_model08(self):
        "Disable deletion forms."
        user1 = self.create_user(index=0)
        user2 = self.create_user(index=1)
        registry = _ConfigRegistry()

        civ1, civ2 = FakeCivility.objects.all()[:2]
        registry.register_model(FakeCivility).deletion(
            enable_func=lambda instance, user: instance.id == civ1.id
        )

        model_config = registry.get_app_registry('creme_core').get_model_conf(FakeCivility)
        self.assertIsSubclass(model_config.creator.form_class, CremeModelForm)

        deletor = model_config.deletor
        self.assertIsSubclass(deletor.form_class, CremeModelForm)

        url1 = reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'fakecivility', civ1.id),
        )
        self.assertEqual(url1, deletor.get_url(instance=civ1, user=user1))
        self.assertEqual(url1, deletor.get_url(instance=civ1, user=user2))
        self.assertIsNone(deletor.get_url(instance=civ2, user=user1))

        # Disable with user
        user_name = user1.username
        deletor.enable_func = lambda instance, user: user.username == user_name
        self.assertEqual(url1, deletor.get_url(instance=civ1, user=user1))
        self.assertEqual(
            reverse(
                'creme_config__delete_instance',
                args=('creme_core', 'fakecivility', civ2.id),
            ),
            deletor.get_url(instance=civ2, user=user1),
        )
        self.assertIsNone(deletor.get_url(instance=civ1, user=user2))

    def test_register_model09(self):
        "Register specific Brick."
        registry = _ConfigRegistry()

        class SectorBrick(GenericModelBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_register_model08')

        registry.register_model(FakeSector) \
                .brick_class(SectorBrick) \
                .edition(enable_func=lambda x: False)

        model_config = registry.get_app_registry('creme_core').get_model_conf(FakeSector)

        brick = model_config.get_brick()
        self.assertIsInstance(brick, SectorBrick)
        self.assertEqual('creme_core', brick.app_name)
        self.assertEqual(FakeSector,   brick.model_config.model)

        # Change class
        class SectorBrick_V2(GenericModelBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_register_model08_V2')

        model_config.brick_cls = SectorBrick_V2
        self.assertIsInstance(model_config.get_brick(), SectorBrick_V2)

    def test_register_model10(self):
        "Duplicated registration."
        registry = _ConfigRegistry()

        registry.register_model(FakeCivility)

        with self.assertRaises(RegistrationError):
            registry.register_model(FakeCivility)

    def test_unregister_model01(self):
        registry = _ConfigRegistry()
        registry.register_model(FakeCivility)
        registry.register_model(FakeSector)
        registry.register_model(FakePosition)

        registry.unregister_models(FakeCivility, FakePosition)

        with self.assertNoException():
            app_conf = registry.get_app_registry('creme_core')

        get_model_conf = app_conf.get_model_conf

        with self.assertNoException():
            get_model_conf(model=FakeSector)

        self.assertRaises(NotRegisteredInConfig, get_model_conf, model=FakeCivility)
        self.assertRaises(NotRegisteredInConfig, get_model_conf, model=FakePosition)

    def test_register_app_brick(self):
        class TestBrick(SimpleBrick):
            pass

        class TestBrick1(TestBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_register_app_bricks1')

        class TestBrick2(TestBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_register_app_bricks2')

        class TestBrick3(TestBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_register_app_bricks3')

        brick_registry = _BrickRegistry()
        brick_registry.register(TestBrick1, TestBrick2, TestBrick3)

        registry = _ConfigRegistry(brick_registry)
        registry.register_app_bricks('creme_core', TestBrick1, TestBrick2)
        registry.register_app_bricks('documents', TestBrick3)

        with self.assertNoException():
            app_reg1 = registry.get_app_registry('creme_core')

        def get_brick_ids(app_conf_registry):
            b_ids = set()
            for brick in app_conf_registry.bricks:
                self.assertIsInstance(brick, SimpleBrick)
                b_ids.add(brick.id_)
            return b_ids

        brick_ids = get_brick_ids(app_reg1)
        self.assertIn(TestBrick1.id_, brick_ids)
        self.assertIn(TestBrick2.id_, brick_ids)
        self.assertNotIn(TestBrick3, brick_ids)

        with self.assertNoException():
            app_reg2 = registry.get_app_registry('documents')

        brick_ids = get_brick_ids(app_reg2)
        self.assertIn(TestBrick3.id_, brick_ids)
        self.assertNotIn(TestBrick1, brick_ids)
        self.assertNotIn(TestBrick2, brick_ids)

    def test_register_userbricks(self):
        class TestUserBrick1(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_register_userbricks1')

        class TestUserBrick2(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_register_userbricks2')

        brick_registry = _BrickRegistry()
        brick_registry.register(TestUserBrick1, TestUserBrick2)

        registry = _ConfigRegistry(brick_registry)

        registry.register_user_bricks(TestUserBrick1, TestUserBrick2)
        bricks = [*registry.user_bricks]
        self.assertEqual(2, len(bricks))
        self.assertIsInstance(bricks[0], TestUserBrick1)
        self.assertIsInstance(bricks[1], TestUserBrick2)

    def test_register_portal_bricks(self):
        class TestPortalBrick(SimpleBrick):
            pass

        class TestPortalBrick1(TestPortalBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_register_portal_bricks1')

        class TestPortalBrick2(TestPortalBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_register_portal_bricks2')

        brick_registry = _BrickRegistry()
        brick_registry.register(TestPortalBrick1, TestPortalBrick2)

        registry = _ConfigRegistry(brick_registry)
        registry.register_portal_bricks(TestPortalBrick1, TestPortalBrick2)

        brick_ids = set()
        for brick in registry.portal_bricks:
            self.assertIsInstance(brick, TestPortalBrick)
            brick_ids.add(brick.id_)

        self.assertIn(TestPortalBrick1.id_, brick_ids)
        self.assertIn(TestPortalBrick2.id_, brick_ids)

    def test_app_registry_is_empty01(self):
        "use models."
        registry = _ConfigRegistry(
            brick_registry=_BrickRegistry(),
            setting_key_registry=_SettingKeyRegistry(),
        )
        app_registry = registry.get_app_registry('creme_core', create=True)
        self.assertIs(True, app_registry.is_empty)

        registry.register_model(FakeCivility)
        self.assertIs(False, app_registry.is_empty)

    def test_app_registry_is_empty02(self):
        "use bricks."
        class TestBrick(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_config', 'test_app_registry_is_empty02')

        brick_registry = _BrickRegistry()
        registry = _ConfigRegistry(
            brick_registry=brick_registry,
            setting_key_registry=_SettingKeyRegistry(),
        )

        app_registry = registry.get_app_registry('creme_core', create=True)
        self.assertTrue(app_registry.is_empty)

        brick_registry.register(TestBrick)
        self.assertTrue(app_registry.is_empty)

        registry.register_app_bricks('creme_core', TestBrick)
        self.assertFalse(app_registry.is_empty)

    def test_app_registry_is_empty03(self):
        "Use SettingKeys."
        sk1 = SettingKey(
            'creme_core-test_sk_string',
            description='Page title',
            app_label='documents',  # <== not 'creme_core'
            type=SettingKey.STRING,
            blank=True,
        )
        sk2 = SettingKey(
            'creme_core-test_sk_int',
            description='Page size',
            app_label='creme_core',
            type=SettingKey.INT,
            hidden=True,  # <==
        )
        sk3 = SettingKey(
            'creme_core-test_sk_bool',
            description='Page hidden',
            app_label='creme_core',
            type=SettingKey.BOOL,
        )

        skey_registry = _SettingKeyRegistry()

        registry = _ConfigRegistry(setting_key_registry=skey_registry)
        app_registry = registry.get_app_registry('creme_core', create=True)
        self.assertIs(True, app_registry.is_empty)

        skey_registry.register(sk1)
        self.assertIs(True, app_registry.is_empty)

        skey_registry.register(sk2)
        self.assertIs(True, app_registry.is_empty)

        skey_registry.register(sk3)
        self.assertIs(False, app_registry.is_empty)

    def test_get_model_creation_info01(self):
        "Not registered model."
        user = self.login()
        registry = _ConfigRegistry()

        url, allowed = registry.get_model_creation_info(model=FakeCivility, user=user)
        self.assertIs(False, allowed)
        self.assertIsNone(url)

    def test_get_model_creation_info02(self):
        "Registered model."
        user = self.login()

        registry = _ConfigRegistry()
        registry.register_model(FakeCivility)

        url, allowed = registry.get_model_creation_info(model=FakeCivility, user=user)
        self.assertIs(True, allowed)
        creation_url = reverse(
            'creme_config__create_instance_from_widget',
            args=('creme_core', 'fakecivility'),
        )
        self.assertEqual(creation_url, url)

        # User than cannot admin
        url, allowed = registry.get_model_creation_info(model=FakeCivility, user=self.other_user)
        self.assertIs(False, allowed)
        self.assertEqual(creation_url, url)

    def test_get_model_creation_info03(self):
        "Not super-user."
        user = self.login(is_superuser=False, admin_4_apps=['creme_core'])

        registry = _ConfigRegistry()
        registry.register_model(FakeCivility)

        url, allowed = registry.get_model_creation_info(model=FakeCivility, user=user)
        self.assertTrue(allowed)

    def test_get_model_creation_info04(self):
        "Specific creation URL."
        user = self.login()

        registry = _ConfigRegistry()
        registry.register_model(FakeCivility).creation(url_name='creme_config__create_team')

        url, allowed = registry.get_model_creation_info(model=FakeCivility, user=user)
        self.assertFalse(allowed)
        self.assertIsNone(url)

    def test_get_model_creation_info05(self):
        "Enable function OK."
        user = self.login()

        registry = _ConfigRegistry()
        registry.register_model(FakeCivility).creation(enable_func=lambda user: True)

        url, allowed = registry.get_model_creation_info(model=FakeCivility, user=user)
        self.assertEqual(
            reverse(
                'creme_config__create_instance_from_widget',
                args=('creme_core', 'fakecivility'),
            ),
            url,
        )

    def test_get_model_creation_info06(self):
        "Enable function KO."
        user = self.login()

        registry = _ConfigRegistry()
        registry.register_model(FakeCivility).creation(enable_func=lambda user: False)

        url, allowed = registry.get_model_creation_info(model=FakeCivility, user=user)
        self.assertIsNone(url)
