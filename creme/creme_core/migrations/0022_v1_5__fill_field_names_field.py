# -*- coding: utf-8 -*-

from south.v2 import DataMigration


class Migration(DataMigration):
    def forwards(self, orm):
        sfields_mngr = orm['creme_core.SearchField'].objects

        for sci in orm['creme_core.SearchConfigItem'].objects.all():
            sci.field_names = ','.join(sf.field
                                        for sf in sfields_mngr.filter(search_config_item=sci)
                                                              .order_by('order')
                                      ) or None
            sci.save()

        orm['contenttypes.ContentType'].objects.filter(app_label='creme_core', model='searchfield').delete()

    def backwards(self, orm):
        pass

    models = {
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
            'Meta': {'ordering': "('username',)", 'object_name': 'User'},
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
        'creme_core.blockdetailviewlocation': {
            'Meta': {'ordering': "('order',)", 'object_name': 'BlockDetailviewLocation'},
            'block_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'zone': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'creme_core.blockmypagelocation': {
            'Meta': {'ordering': "('order',)", 'object_name': 'BlockMypageLocation'},
            'block_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        },
        'creme_core.blockportallocation': {
            'Meta': {'ordering': "('order',)", 'object_name': 'BlockPortalLocation'},
            'app_name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'block_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'creme_core.blockstate': {
            'Meta': {'unique_together': "(('user', 'block_id'),)", 'object_name': 'BlockState'},
            'block_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_empty_fields': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'creme_core.buttonmenuitem': {
            'Meta': {'object_name': 'ButtonMenuItem'},
            'button_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {})
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
        'creme_core.cremeproperty': {
            'Meta': {'object_name': 'CremeProperty'},
            'creme_entity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'properties'", 'to': "orm['creme_core.CremeEntity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremePropertyType']"})
        },
        'creme_core.cremepropertytype': {
            'Meta': {'ordering': "('text',)", 'object_name': 'CremePropertyType'},
            'id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'is_copiable': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'subject_ctypes_creme_property_set'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['contenttypes.ContentType']"}),
            'text': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        'creme_core.currency': {
            'Meta': {'object_name': 'Currency'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'international_symbol': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'local_symbol': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'creme_core.customblockconfigitem': {
            'Meta': {'object_name': 'CustomBlockConfigItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'json_cells': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'creme_core.customfield': {
            'Meta': {'ordering': "('id',)", 'object_name': 'CustomField'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'field_type': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'creme_core.customfieldboolean': {
            'Meta': {'object_name': 'CustomFieldBoolean'},
            'custom_field': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CustomField']"}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'creme_core.customfielddatetime': {
            'Meta': {'object_name': 'CustomFieldDateTime'},
            'custom_field': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CustomField']"}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.DateTimeField', [], {})
        },
        'creme_core.customfieldenum': {
            'Meta': {'object_name': 'CustomFieldEnum'},
            'custom_field': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CustomField']"}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CustomFieldEnumValue']"})
        },
        'creme_core.customfieldenumvalue': {
            'Meta': {'object_name': 'CustomFieldEnumValue'},
            'custom_field': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'customfieldenumvalue_set'", 'to': "orm['creme_core.CustomField']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'creme_core.customfieldfloat': {
            'Meta': {'object_name': 'CustomFieldFloat'},
            'custom_field': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CustomField']"}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'})
        },
        'creme_core.customfieldinteger': {
            'Meta': {'object_name': 'CustomFieldInteger'},
            'custom_field': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CustomField']"}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.IntegerField', [], {})
        },
        'creme_core.customfieldmultienum': {
            'Meta': {'object_name': 'CustomFieldMultiEnum'},
            'custom_field': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CustomField']"}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['creme_core.CustomFieldEnumValue']", 'symmetrical': 'False'})
        },
        'creme_core.customfieldstring': {
            'Meta': {'object_name': 'CustomFieldString'},
            'custom_field': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CustomField']"}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'creme_core.datereminder': {
            'Meta': {'object_name': 'DateReminder'},
            'date_of_remind': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ident': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'model_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reminders_set'", 'to': "orm['contenttypes.ContentType']"}),
            'model_id': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'creme_core.entityfilter': {
            'Meta': {'object_name': 'EntityFilter'},
            'entity_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'use_or': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'creme_core.entityfiltercondition': {
            'Meta': {'object_name': 'EntityFilterCondition'},
            'filter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'conditions'", 'to': "orm['creme_core.EntityFilter']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'type': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'creme_core.headerfilter': {
            'Meta': {'object_name': 'HeaderFilter'},
            'entity_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'json_cells': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'creme_core.historyconfigitem': {
            'Meta': {'object_name': 'HistoryConfigItem'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'relation_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.RelationType']", 'unique': 'True'})
        },
        'creme_core.historyline': {
            'Meta': {'object_name': 'HistoryLine'},
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'entity_ctype': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'entity_owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'value': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        'creme_core.instanceblockconfigitem': {
            'Meta': {'object_name': 'InstanceBlockConfigItem'},
            'block_id': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'verbose': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'creme_core.language': {
            'Meta': {'object_name': 'Language'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'creme_core.mutex': {
            'Meta': {'object_name': 'Mutex'},
            'id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'})
        },
        'creme_core.preferedmenuitem': {
            'Meta': {'object_name': 'PreferedMenuItem'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        },
        'creme_core.relation': {
            'Meta': {'object_name': 'Relation'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'entity_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'header_filter_search_field': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_actived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'object_entity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relations_where_is_object'", 'on_delete': 'models.PROTECT', 'to': "orm['creme_core.CremeEntity']"}),
            'subject_entity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relations'", 'on_delete': 'models.PROTECT', 'to': "orm['creme_core.CremeEntity']"}),
            'symmetric_relation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.Relation']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.RelationType']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'creme_core.relationblockitem': {
            'Meta': {'object_name': 'RelationBlockItem'},
            'block_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'json_cells_map': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'relation_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.RelationType']", 'unique': 'True'})
        },
        'creme_core.relationtype': {
            'Meta': {'object_name': 'RelationType'},
            'id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'is_copiable': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_internal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'object_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'relationtype_objects_set'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['contenttypes.ContentType']"}),
            'object_properties': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'relationtype_objects_set'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['creme_core.CremePropertyType']"}),
            'predicate': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'subject_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'relationtype_subjects_set'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['contenttypes.ContentType']"}),
            'subject_properties': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'relationtype_subjects_set'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['creme_core.CremePropertyType']"}),
            'symmetric_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.RelationType']", 'null': 'True', 'blank': 'True'})
        },
        'creme_core.searchconfigitem': {
            'Meta': {'object_name': 'SearchConfigItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'field_names': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        },
        'creme_core.searchfield': {
            'Meta': {'object_name': 'SearchField'},
            'field': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'field_verbose_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'search_config_item': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.SearchConfigItem']"})
        },
        'creme_core.semifixedrelationtype': {
            'Meta': {'unique_together': "(('relation_type', 'object_entity'),)", 'object_name': 'SemiFixedRelationType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']"}),
            'predicate': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'relation_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.RelationType']"})
        },
        'creme_core.setcredentials': {
            'Meta': {'object_name': 'SetCredentials'},
            'ctype': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'role': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'credentials'", 'to': "orm['creme_core.UserRole']"}),
            'set_type': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'value': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'creme_core.teamm2m': {
            'Meta': {'object_name': 'TeamM2M'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'team_m2m_teamside'", 'to': "orm['auth.User']"}),
            'teammate': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'team_m2m'", 'to': "orm['auth.User']"})
        },
        'creme_core.userrole': {
            'Meta': {'object_name': 'UserRole'},
            'creatable_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'roles_allowing_creation'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'exportable_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'roles_allowing_export'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'raw_admin_4_apps': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'raw_allowed_apps': ('django.db.models.fields.TextField', [], {'default': "''"})
        },
        'creme_core.vat': {
            'Meta': {'ordering': "('value',)", 'object_name': 'Vat'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'value': ('django.db.models.fields.DecimalField', [], {'default': "'20.0'", 'max_digits': '4', 'decimal_places': '2'})
        },
        'creme_core.version': {
            'Meta': {'object_name': 'Version'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['creme_core']
    symmetrical = True
