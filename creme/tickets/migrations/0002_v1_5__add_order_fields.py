# -*- coding: utf-8 -*-

from django.db import models

from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):
    def forwards(self, orm):
        # Adding fields order'
        db.add_column('tickets_status', 'order',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=1, blank=True),
                      keep_default=False,
                     )
        db.add_column('tickets_criticity', 'order',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=1, blank=True),
                      keep_default=False,
                     )
        db.add_column('tickets_priority', 'order',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=1, blank=True),
                      keep_default=False,
                     )

        # Set PROTECT properties
        db.alter_column('tickets_tickettemplate', 'status_id',
                        self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.Status'], on_delete=models.PROTECT)
                       )
        db.alter_column('tickets_tickettemplate', 'priority_id',
                        self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.Priority'], on_delete=models.PROTECT)
                       )
        db.alter_column('tickets_tickettemplate', 'criticity_id',
                        self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.Criticity'], on_delete=models.PROTECT)
                       )

        db.alter_column('tickets_ticket', 'status_id', 
                        self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.Status'], on_delete=models.PROTECT)
                       )
        db.alter_column('tickets_ticket', 'priority_id',
                        self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.Priority'], on_delete=models.PROTECT)
                       )
        db.alter_column('tickets_ticket', 'criticity_id',
                        self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.Criticity'], on_delete=models.PROTECT)
                       )

        # Changing field 'Ticket.cremeentity_ptr' (not managed by the old south version)
        db.alter_column('tickets_ticket', 'cremeentity_ptr_id',
                        self.gf('django.db.models.fields.related.OneToOneField')(to=orm['creme_core.CremeEntity'], unique=True, primary_key=True)
                       )

    def backwards(self, orm):
        # Deleting fields 'order'
        db.delete_column('tickets_status',    'order')
        db.delete_column('tickets_criticity', 'order')
        db.delete_column('tickets_priority',  'order')

        # Remove PROTECT
        db.alter_column('tickets_tickettemplate', 'status_id',    self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.Status']))
        db.alter_column('tickets_tickettemplate', 'priority_id',  self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.Priority']))
        db.alter_column('tickets_tickettemplate', 'criticity_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.Criticity']))
        db.alter_column('tickets_ticket',         'status_id',    self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.Status']))
        db.alter_column('tickets_ticket',         'priority_id',  self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.Priority']))
        db.alter_column('tickets_ticket',         'criticity_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.Criticity']))

        # Changing field 'Ticket.cremeentity_ptr'
        db.alter_column('tickets_ticket', 'cremeentity_ptr_id',
                        self.gf('django.db.models.fields.related.OneToOneField')(to=orm['creme_core.CremeEntity'], unique=True, primary_key=True)
                       )

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
        'creme_core.cremeentity': {
            'Meta': {'ordering': "('header_filter_search_field',)", 'object_name': 'CremeEntity'},
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
        },
        'tickets.criticity': {
            'Meta': {'ordering': "('order',)", 'object_name': 'Criticity'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'blank': 'True'})
        },
        'tickets.priority': {
            'Meta': {'ordering': "('order',)", 'object_name': 'Priority'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'blank': 'True'})
        },
        'tickets.status': {
            'Meta': {'ordering': "('order',)", 'object_name': 'Status'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'blank': 'True'})
        },
        'tickets.ticket': {
            'Meta': {'ordering': "('title',)", 'object_name': 'Ticket'},
            'closing_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'criticity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tickets.Criticity']", 'on_delete': 'models.PROTECT'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'priority': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tickets.Priority']", 'on_delete': 'models.PROTECT'}),
            'solution': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tickets.Status']", 'on_delete': 'models.PROTECT'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100', 'blank': 'True'})
        },
        'tickets.tickettemplate': {
            'Meta': {'ordering': "('title',)", 'object_name': 'TicketTemplate'},
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'criticity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tickets.Criticity']", 'on_delete': 'models.PROTECT'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'priority': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tickets.Priority']", 'on_delete': 'models.PROTECT'}),
            'solution': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tickets.Status']", 'on_delete': 'models.PROTECT'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100', 'blank': 'True'})
        }
    }

    complete_apps = ['tickets']
