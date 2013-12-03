# -*- coding: utf-8 -*-

from south.db import db
from south.v2 import SchemaMigration

from django.db import models


class Migration(SchemaMigration):
    depends_on = (
        ("creme_core", "0001_initial"),
    )

    def forwards(self, orm):
        # Adding model 'Graph'
        db.create_table('graphs_graph', (
            ('cremeentity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['creme_core.CremeEntity'], unique=True, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('graphs', ['Graph'])

        # Adding M2M table for field orbital_relation_types on 'Graph'
        db.create_table('graphs_graph_orbital_relation_types', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('graph', models.ForeignKey(orm['graphs.graph'], null=False)),
            ('relationtype', models.ForeignKey(orm['creme_core.relationtype'], null=False))
        ))
        db.create_unique('graphs_graph_orbital_relation_types', ['graph_id', 'relationtype_id'])

        # Adding model 'RootNode'
        db.create_table('graphs_rootnode', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('graph', self.gf('django.db.models.fields.related.ForeignKey')(related_name='roots', to=orm['graphs.Graph'])),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremeEntity'])),
        ))
        db.send_create_signal('graphs', ['RootNode'])

        # Adding M2M table for field relation_types on 'RootNode'
        db.create_table('graphs_rootnode_relation_types', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('rootnode', models.ForeignKey(orm['graphs.rootnode'], null=False)),
            ('relationtype', models.ForeignKey(orm['creme_core.relationtype'], null=False))
        ))
        db.create_unique('graphs_rootnode_relation_types', ['rootnode_id', 'relationtype_id'])

    def backwards(self, orm):
        # Deleting model 'Graph'
        db.delete_table('graphs_graph')

        # Removing M2M table for field orbital_relation_types on 'Graph'
        db.delete_table('graphs_graph_orbital_relation_types')

        # Deleting model 'RootNode'
        db.delete_table('graphs_rootnode')

        # Removing M2M table for field relation_types on 'RootNode'
        db.delete_table('graphs_rootnode_relation_types')

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
        'creme_core.cremepropertytype': {
            'Meta': {'object_name': 'CremePropertyType'},
            'id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'subject_ctypes_creme_property_set'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['contenttypes.ContentType']"}),
            'text': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        'creme_core.relationtype': {
            'Meta': {'object_name': 'RelationType'},
            'id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_internal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'object_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'relationtype_objects_set'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['contenttypes.ContentType']"}),
            'object_properties': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'relationtype_objects_set'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['creme_core.CremePropertyType']"}),
            'predicate': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'subject_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'relationtype_subjects_set'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['contenttypes.ContentType']"}),
            'subject_properties': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'relationtype_subjects_set'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['creme_core.CremePropertyType']"}),
            'symmetric_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.RelationType']", 'null': 'True', 'blank': 'True'})
        },
        'creme_core.userrole': {
            'Meta': {'object_name': 'UserRole'},
            'creatable_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'raw_admin_4_apps': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'raw_allowed_apps': ('django.db.models.fields.TextField', [], {'default': "''"})
        },
        'graphs.graph': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Graph', '_ormbases': ['creme_core.CremeEntity']},
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'orbital_relation_types': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['creme_core.RelationType']", 'symmetrical': 'False'})
        },
        'graphs.rootnode': {
            'Meta': {'object_name': 'RootNode'},
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']"}),
            'graph': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'roots'", 'to': "orm['graphs.Graph']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'relation_types': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['creme_core.RelationType']", 'symmetrical': 'False'})
        }
    }

    complete_apps = ['graphs']
