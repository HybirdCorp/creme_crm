# -*- coding: utf-8 -*-

from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):
    def forwards(self, orm):
        # 'key_id' is no more a ForeignKey but a regular CharField
        db.delete_index('creme_config_settingvalue', ['key_id'])
        db.alter_column('creme_config_settingvalue', 'key_id',
                        self.gf('django.db.models.fields.CharField')(max_length=100)
                       )

        db.delete_table('creme_config_settingkey')

        db.rename_table('creme_config_settingvalue', 'creme_core_settingvalue')

    def backwards(self, orm):
        db.rename_table('creme_core_settingvalue', 'creme_config_settingvalue')

        # Adding model 'SettingKey'
        db.create_table('creme_config_settingkey', (
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('app_label',   self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('hidden',      self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('type',        self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('id',          self.gf('django.db.models.fields.CharField')(max_length=100, primary_key=True)),
        ))
        db.send_create_signal('creme_config', ['SettingKey'])

        db.alter_column('creme_config_settingvalue', 'key_id',
                        self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_config.SettingKey'])
                       )
        #db.create_index('creme_config_settingvalue', ['key_id']) #It seems it already exists

    models = {}
    complete_apps = ['creme_config']
