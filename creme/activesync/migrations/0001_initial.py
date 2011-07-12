# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'CremeExchangeMapping'
        db.create_table('activesync_cremeexchangemapping', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('creme_entity_id', self.gf('django.db.models.fields.IntegerField')(unique=True)),
            ('creme_entity_ct', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('exchange_entity_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
            ('synced', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_creme_modified', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('was_deleted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('creme_entity_repr', self.gf('django.db.models.fields.CharField')(default=u'', max_length=200, null=True, blank=True)),
        ))
        db.send_create_signal('activesync', ['CremeExchangeMapping'])

        # Adding model 'CremeClient'
        db.create_table('activesync_cremeclient', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
            ('client_id', self.gf('django.db.models.fields.CharField')(default='BDCAA3E66D77289793E708F5901A7CE8', unique=True, max_length=32)),
            ('policy_key', self.gf('django.db.models.fields.CharField')(default=0, max_length=200)),
            ('sync_key', self.gf('django.db.models.fields.CharField')(default=None, max_length=200, null=True, blank=True)),
            ('folder_sync_key', self.gf('django.db.models.fields.CharField')(default=None, max_length=200, null=True, blank=True)),
            ('contact_folder_id', self.gf('django.db.models.fields.CharField')(default=None, max_length=64, null=True, blank=True)),
            ('last_sync', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('activesync', ['CremeClient'])

        # Adding model 'SyncKeyHistory'
        db.create_table('activesync_synckeyhistory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('client', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activesync.CremeClient'])),
            ('sync_key', self.gf('django.db.models.fields.CharField')(default=None, max_length=200, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
        ))
        db.send_create_signal('activesync', ['SyncKeyHistory'])

        # Adding model 'UserSynchronizationHistory'
        db.create_table('activesync_usersynchronizationhistory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('entity_repr', self.gf('django.db.models.fields.CharField')(default=None, max_length=200, null=True, blank=True)),
            ('entity_pk', self.gf('django.db.models.fields.IntegerField')(max_length=50, null=True, blank=True)),
            ('entity_ct', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2011, 6, 27, 16, 55, 47, 629438), blank=True)),
            ('entity_changes', self.gf('django.db.models.fields.TextField')(default='(dp0\n.')),
            ('type', self.gf('django.db.models.fields.IntegerField')(max_length=1)),
            ('where', self.gf('django.db.models.fields.IntegerField')(max_length=1)),
        ))
        db.send_create_signal('activesync', ['UserSynchronizationHistory'])

        # Adding model 'AS_Folder'
        db.create_table('activesync_as_folder', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('client', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activesync.CremeClient'])),
            ('server_id', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('parent_id', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('display_name', self.gf('django.db.models.fields.CharField')(default='', max_length=200)),
            ('type', self.gf('django.db.models.fields.IntegerField')(max_length=2)),
            ('sync_key', self.gf('django.db.models.fields.CharField')(default=None, max_length=200, null=True, blank=True)),
            ('as_class', self.gf('django.db.models.fields.CharField')(default=None, max_length=25, null=True, blank=True)),
            ('entity_id', self.gf('django.db.models.fields.CharField')(default=None, max_length=200, null=True, blank=True)),
        ))
        db.send_create_signal('activesync', ['AS_Folder'])

        # Adding model 'EntityASData'
        db.create_table('activesync_entityasdata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremeEntity'])),
            ('field_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('field_value', self.gf('django.db.models.fields.CharField')(max_length=300)),
        ))
        db.send_create_signal('activesync', ['EntityASData'])

        # Adding unique constraint on 'EntityASData', fields ['entity', 'field_name']
        db.create_unique('activesync_entityasdata', ['entity_id', 'field_name'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'EntityASData', fields ['entity', 'field_name']
        db.delete_unique('activesync_entityasdata', ['entity_id', 'field_name'])

        # Deleting model 'CremeExchangeMapping'
        db.delete_table('activesync_cremeexchangemapping')

        # Deleting model 'CremeClient'
        db.delete_table('activesync_cremeclient')

        # Deleting model 'SyncKeyHistory'
        db.delete_table('activesync_synckeyhistory')

        # Deleting model 'UserSynchronizationHistory'
        db.delete_table('activesync_usersynchronizationhistory')

        # Deleting model 'AS_Folder'
        db.delete_table('activesync_as_folder')

        # Deleting model 'EntityASData'
        db.delete_table('activesync_entityasdata')


    models = {
        'activesync.as_folder': {
            'Meta': {'object_name': 'AS_Folder'},
            'as_class': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '25', 'null': 'True', 'blank': 'True'}),
            'client': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['activesync.CremeClient']"}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200'}),
            'entity_id': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent_id': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'server_id': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'sync_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.IntegerField', [], {'max_length': '2'})
        },
        'activesync.cremeclient': {
            'Meta': {'object_name': 'CremeClient'},
            'client_id': ('django.db.models.fields.CharField', [], {'default': "'B952A8236A7AA238B186C7B192488E22'", 'unique': 'True', 'max_length': '32'}),
            'contact_folder_id': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'folder_sync_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'policy_key': ('django.db.models.fields.CharField', [], {'default': '0', 'max_length': '200'}),
            'sync_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'activesync.cremeexchangemapping': {
            'Meta': {'object_name': 'CremeExchangeMapping'},
            'creme_entity_ct': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'creme_entity_id': ('django.db.models.fields.IntegerField', [], {'unique': 'True'}),
            'creme_entity_repr': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'exchange_entity_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_creme_modified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'synced': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'was_deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'activesync.entityasdata': {
            'Meta': {'unique_together': "(('entity', 'field_name'),)", 'object_name': 'EntityASData'},
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']"}),
            'field_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'field_value': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'activesync.synckeyhistory': {
            'Meta': {'object_name': 'SyncKeyHistory'},
            'client': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['activesync.CremeClient']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sync_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'activesync.usersynchronizationhistory': {
            'Meta': {'object_name': 'UserSynchronizationHistory'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 6, 27, 16, 55, 47, 651342)', 'blank': 'True'}),
            'entity_changes': ('django.db.models.fields.TextField', [], {'default': "'(dp0\\n.'"}),
            'entity_ct': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'entity_pk': ('django.db.models.fields.IntegerField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'entity_repr': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'where': ('django.db.models.fields.IntegerField', [], {'max_length': '1'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_team': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'role': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.UserRole']", 'null': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'creme_core.cremeentity': {
            'Meta': {'ordering': "('id',)", 'object_name': 'CremeEntity'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'entity_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'header_filter_search_field': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_actived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'creme_core.userrole': {
            'Meta': {'object_name': 'UserRole'},
            'creatable_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'raw_admin_4_apps': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'raw_allowed_apps': ('django.db.models.fields.TextField', [], {'default': "''"})
        }
    }

    complete_apps = ['activesync']
