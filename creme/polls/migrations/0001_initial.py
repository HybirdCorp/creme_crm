# -*- coding: utf-8 -*-

from south.db import db
from south.v2 import SchemaMigration

from django.db import models


class Migration(SchemaMigration):
    def forwards(self, orm):
        # Adding model 'PollType'
        db.create_table('polls_polltype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
        ))
        db.send_create_signal('polls', ['PollType'])

        # Adding model 'PollForm'
        db.create_table('polls_pollform', (
            ('cremeentity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['creme_core.CremeEntity'], unique=True, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=220)),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['polls.PollType'], null=True, on_delete=models.SET_NULL, blank=True)),
        ))
        db.send_create_signal('polls', ['PollForm'])

        # Adding model 'PollFormSection'
        db.create_table('polls_pollformsection', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pform', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sections', to=orm['polls.PollForm'])),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['polls.PollFormSection'], null=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('body', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('polls', ['PollFormSection'])

        # Adding model 'PollFormLine'
        db.create_table('polls_pollformline', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pform', self.gf('django.db.models.fields.related.ForeignKey')(related_name='lines', to=orm['polls.PollForm'])),
            ('section', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['polls.PollFormSection'], null=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('disabled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('type', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('type_args', self.gf('django.db.models.fields.TextField')(null=True)),
            ('conds_use_or', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('question', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('polls', ['PollFormLine'])

        # Adding model 'PollFormLineCondition'
        db.create_table('polls_pollformlinecondition', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('line', self.gf('django.db.models.fields.related.ForeignKey')(related_name='conditions', to=orm['polls.PollFormLine'])),
            ('source', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['polls.PollFormLine'])),
            ('operator', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('raw_answer', self.gf('django.db.models.fields.TextField')(null=True)),
        ))
        db.send_create_signal('polls', ['PollFormLineCondition'])

        # Adding model 'PollCampaign'
        db.create_table('polls_pollcampaign', (
            ('cremeentity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['creme_core.CremeEntity'], unique=True, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('goal', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('start', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('due_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('segment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['commercial.MarketSegment'], null=True, on_delete=models.PROTECT, blank=True)),
            ('expected_count', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
        ))
        db.send_create_signal('polls', ['PollCampaign'])

        # Adding model 'PollReply'
        db.create_table('polls_pollreply', (
            ('cremeentity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['creme_core.CremeEntity'], unique=True, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('pform', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['polls.PollForm'], on_delete=models.PROTECT)),
            ('campaign', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['polls.PollCampaign'], null=True, on_delete=models.PROTECT, blank=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, on_delete=models.PROTECT, to=orm['creme_core.CremeEntity'])),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['polls.PollType'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('is_complete', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('polls', ['PollReply'])

        # Adding model 'PollReplySection'
        db.create_table('polls_pollreplysection', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('preply', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sections', to=orm['polls.PollReply'])),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['polls.PollReplySection'], null=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('body', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('polls', ['PollReplySection'])

        # Adding model 'PollReplyLine'
        db.create_table('polls_pollreplyline', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('preply', self.gf('django.db.models.fields.related.ForeignKey')(related_name='lines', to=orm['polls.PollReply'])),
            ('section', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['polls.PollReplySection'], null=True)),
            ('pform_line', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['polls.PollFormLine'])),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('type', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('type_args', self.gf('django.db.models.fields.TextField')(null=True)),
            ('applicable', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('conds_use_or', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('question', self.gf('django.db.models.fields.TextField')()),
            ('raw_answer', self.gf('django.db.models.fields.TextField')(null=True)),
        ))
        db.send_create_signal('polls', ['PollReplyLine'])

        # Adding model 'PollReplyLineCondition'
        db.create_table('polls_pollreplylinecondition', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('line', self.gf('django.db.models.fields.related.ForeignKey')(related_name='conditions', to=orm['polls.PollReplyLine'])),
            ('source', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['polls.PollReplyLine'])),
            ('operator', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('raw_answer', self.gf('django.db.models.fields.TextField')(null=True)),
        ))
        db.send_create_signal('polls', ['PollReplyLineCondition'])

    def backwards(self, orm):
        # Deleting model 'PollType'
        db.delete_table('polls_polltype')

        # Deleting model 'PollForm'
        db.delete_table('polls_pollform')

        # Deleting model 'PollFormSection'
        db.delete_table('polls_pollformsection')

        # Deleting model 'PollFormLine'
        db.delete_table('polls_pollformline')

        # Deleting model 'PollFormLineCondition'
        db.delete_table('polls_pollformlinecondition')

        # Deleting model 'PollCampaign'
        db.delete_table('polls_pollcampaign')

        # Deleting model 'PollReply'
        db.delete_table('polls_pollreply')

        # Deleting model 'PollReplySection'
        db.delete_table('polls_pollreplysection')

        # Deleting model 'PollReplyLine'
        db.delete_table('polls_pollreplyline')

        # Deleting model 'PollReplyLineCondition'
        db.delete_table('polls_pollreplylinecondition')

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
            'role': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.UserRole']", 'null': 'True', 'on_delete': 'models.PROTECT'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'commercial.marketsegment': {
            'Meta': {'object_name': 'MarketSegment'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'property_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremePropertyType']"})
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
        'creme_core.userrole': {
            'Meta': {'object_name': 'UserRole'},
            'creatable_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'roles_allowing_creation'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'exportable_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'roles_allowing_export'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'raw_admin_4_apps': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'raw_allowed_apps': ('django.db.models.fields.TextField', [], {'default': "''"})
        },
        'polls.pollcampaign': {
            'Meta': {'ordering': "('id',)", 'object_name': 'PollCampaign', '_ormbases': ['creme_core.CremeEntity']},
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'due_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'expected_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'goal': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['commercial.MarketSegment']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'})
        },
        'polls.pollform': {
            'Meta': {'ordering': "('id',)", 'object_name': 'PollForm', '_ormbases': ['creme_core.CremeEntity']},
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '220'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.PollType']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'})
        },
        'polls.pollformline': {
            'Meta': {'ordering': "('order',)", 'object_name': 'PollFormLine'},
            'conds_use_or': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'pform': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'lines'", 'to': "orm['polls.PollForm']"}),
            'question': ('django.db.models.fields.TextField', [], {}),
            'section': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.PollFormSection']", 'null': 'True'}),
            'type': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'type_args': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        'polls.pollformlinecondition': {
            'Meta': {'object_name': 'PollFormLineCondition'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'conditions'", 'to': "orm['polls.PollFormLine']"}),
            'operator': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'raw_answer': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.PollFormLine']"})
        },
        'polls.pollformsection': {
            'Meta': {'ordering': "('order',)", 'object_name': 'PollFormSection'},
            'body': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.PollFormSection']", 'null': 'True'}),
            'pform': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sections'", 'to': "orm['polls.PollForm']"})
        },
        'polls.pollreply': {
            'Meta': {'ordering': "('id',)", 'object_name': 'PollReply', '_ormbases': ['creme_core.CremeEntity']},
            'campaign': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.PollCampaign']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'is_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'on_delete': 'models.PROTECT', 'to': "orm['creme_core.CremeEntity']"}),
            'pform': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.PollForm']", 'on_delete': 'models.PROTECT'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.PollType']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'})
        },
        'polls.pollreplyline': {
            'Meta': {'ordering': "('order',)", 'object_name': 'PollReplyLine'},
            'applicable': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'conds_use_or': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'pform_line': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.PollFormLine']"}),
            'preply': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'lines'", 'to': "orm['polls.PollReply']"}),
            'question': ('django.db.models.fields.TextField', [], {}),
            'raw_answer': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'section': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.PollReplySection']", 'null': 'True'}),
            'type': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'type_args': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        'polls.pollreplylinecondition': {
            'Meta': {'object_name': 'PollReplyLineCondition'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'conditions'", 'to': "orm['polls.PollReplyLine']"}),
            'operator': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'raw_answer': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.PollReplyLine']"})
        },
        'polls.pollreplysection': {
            'Meta': {'ordering': "('order',)", 'object_name': 'PollReplySection'},
            'body': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.PollReplySection']", 'null': 'True'}),
            'preply': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sections'", 'to': "orm['polls.PollReply']"})
        },
        'polls.polltype': {
            'Meta': {'object_name': 'PollType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'})
        }
    }

    complete_apps = ['polls']