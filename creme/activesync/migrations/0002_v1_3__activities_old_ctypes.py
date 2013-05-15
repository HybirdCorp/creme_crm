# -*- coding: utf-8 -*-

from functools import partial

from south.v2 import DataMigration


class Migration(DataMigration):
    depends_on = (
        ("activities", "0004_v1_3__add_new_activity_fields_n_subtype_table"), 
    )

    needed_by = (
        ("activities", "0005_v1_3__migrate_n_clean_old_activities_n_related"),
    )

    def forwards(self, orm):
        ContentType = orm['contenttypes.ContentType']
        get_ct = partial(ContentType.objects.get, app_label='activities')

        try:
            activity_ct = get_ct(model='activity')
            old_ctypes = [get_ct(model='meeting'), get_ct(model='phonecall'), get_ct(model='task')]
        except ContentType.DoesNotExist:
            return

        orm['activesync.CremeExchangeMapping'].objects.filter(creme_entity_ct__in=old_ctypes)\
                                                      .update(creme_entity_ct=activity_ct)
        orm['activesync.UserSynchronizationHistory'].objects.filter(entity_ct__in=old_ctypes)\
                                                            .update(entity_ct=activity_ct)

    def backwards(self, orm):
        pass

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
            'client_id': ('django.db.models.fields.CharField', [], {'default': "'FAC8C3F425134EB08696716943CD95AB'", 'unique': 'True', 'max_length': '32'}),
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
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 4, 19, 0, 0)', 'blank': 'True'}),
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
            'role': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.UserRole']", 'null': 'True', 'on_delete': 'models.PROTECT'}),
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
            'creatable_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'roles_allowing_creation'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'exportable_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'roles_allowing_export'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'raw_admin_4_apps': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'raw_allowed_apps': ('django.db.models.fields.TextField', [], {'default': "''"})
        }
    }

    complete_apps = ['activesync']
    symmetrical = True
