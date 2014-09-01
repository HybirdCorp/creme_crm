# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.core.setting_key import SettingKey, setting_key_registry
    from creme.creme_core.models import SettingValue
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('SettingValueTestCase',)


#TODO: clean registry in teardDown....
class SettingValueTestCase(CremeTestCase):
    def test_type_string(self):
        sk = SettingKey(id='persons-test_model_string', description=u"Page title",
                        app_label=None, type=SettingKey.STRING, hidden=False,
                       )
        setting_key_registry.register(sk)

        title = 'May the source be with you'
        sv = SettingValue.objects.create(key=sk, user=None, value=title)

        self.assertEqual(title, self.refresh(sv).value)

    def test_type_int(self):
        sk = SettingKey(id='persons-test_model_int', description=u"Page size",
                        app_label='persons', type=SettingKey.INT,
                       )
        self.assertFalse(sk.hidden)

        setting_key_registry.register(sk)

        size = 156
        sv = SettingValue.objects.create(key=sk, user=None, value=size)

        sv = self.refresh(sv)
        self.assertEqual(size, sv.value)
        self.assertEqual(size, sv.as_html)

    def test_type_bool(self):
        self.login()

        sk = SettingKey(id='activities-test_model_bool', description=u"Display logo ?",
                        app_label='activities', type=SettingKey.BOOL,
                       )
        setting_key_registry.register(sk)

        sv = SettingValue.objects.create(key=sk, user=self.user, value=True)

        sv = self.refresh(sv)
        self.assertIs(sv.value, True)
        self.assertEqual('<input type="checkbox" checked disabled/>%s' % _('Yes'), sv.as_html)

        sv.value = False
        sv.save()

        sv = self.refresh(sv)
        self.assertIs(sv.value, False)
        self.assertEqual('<input type="checkbox" disabled/>%s' % _('No'), sv.as_html)

    def test_tyoe_hour(self):
        self.login()

        sk = SettingKey(id='persons-test_model_hour', description='Reminder hour',
                        app_label='persons', type=SettingKey.HOUR,
                       )
        setting_key_registry.register(sk)

        hour = 9
        sv = SettingValue.objects.create(key=sk, user=self.user, value=hour)

        sv = self.refresh(sv)
        self.assertEqual(hour, sv.value)
        self.assertEqual(_('%sh') % hour, sv.as_html)

    def test_create_value_if_needed(self):
        self.login()

        sk = SettingKey(id='persons-test_create_value_if_needed', description=u"Page size",
                        app_label='persons', type=SettingKey.INT,
                       )
        setting_key_registry.register(sk)

        self.assertFalse(SettingValue.objects.filter(key_id=sk))

        size = 156
        sv = SettingValue.create_if_needed(key=sk, user=None, value=size)
        self.assertIsInstance(sv, SettingValue)
        self.assertIsNone(sv.user)
        self.assertEqual(size, sv.value)

        with self.assertNoException():
            self.refresh(sv)

        sv = SettingValue.create_if_needed(key=sk, user=None, value=size + 1)
        self.assertEqual(size, sv.value) #not new size
