# -*- coding: utf-8 -*-

import datetime

from south.db import db
from south.v2 import SchemaMigration

from django.db import models


class Migration(SchemaMigration):
    def forwards(self, orm):
        # Adding model 'CremeEntity'
        db.create_table('creme_core_cremeentity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('entity_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('header_filter_search_field', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('is_deleted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_actived', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('creme_core', ['CremeEntity'])

        # Adding model 'CremePropertyType'
        db.create_table('creme_core_cremepropertytype', (
            ('id', self.gf('django.db.models.fields.CharField')(max_length=100, primary_key=True)),
            ('text', self.gf('django.db.models.fields.CharField')(unique=True, max_length=200)),
            ('is_custom', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('creme_core', ['CremePropertyType'])

        # Adding M2M table for field subject_ctypes on 'CremePropertyType'
        db.create_table('creme_core_cremepropertytype_subject_ctypes', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('cremepropertytype', models.ForeignKey(orm['creme_core.cremepropertytype'], null=False)),
            ('contenttype', models.ForeignKey(orm['contenttypes.contenttype'], null=False))
        ))
        db.create_unique('creme_core_cremepropertytype_subject_ctypes', ['cremepropertytype_id', 'contenttype_id'])

        # Adding model 'CremeProperty'
        db.create_table('creme_core_cremeproperty', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremePropertyType'])),
            ('creme_entity', self.gf('django.db.models.fields.related.ForeignKey')(related_name='properties', to=orm['creme_core.CremeEntity'])),
        ))
        db.send_create_signal('creme_core', ['CremeProperty'])

        # Adding model 'RelationType'
        db.create_table('creme_core_relationtype', (
            ('id', self.gf('django.db.models.fields.CharField')(max_length=100, primary_key=True)),
            ('is_internal', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_custom', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('predicate', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('symmetric_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.RelationType'], null=True, blank=True)),
        ))
        db.send_create_signal('creme_core', ['RelationType'])

        # Adding M2M table for field subject_ctypes on 'RelationType'
        db.create_table('creme_core_relationtype_subject_ctypes', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('relationtype', models.ForeignKey(orm['creme_core.relationtype'], null=False)),
            ('contenttype', models.ForeignKey(orm['contenttypes.contenttype'], null=False))
        ))
        db.create_unique('creme_core_relationtype_subject_ctypes', ['relationtype_id', 'contenttype_id'])

        # Adding M2M table for field object_ctypes on 'RelationType'
        db.create_table('creme_core_relationtype_object_ctypes', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('relationtype', models.ForeignKey(orm['creme_core.relationtype'], null=False)),
            ('contenttype', models.ForeignKey(orm['contenttypes.contenttype'], null=False))
        ))
        db.create_unique('creme_core_relationtype_object_ctypes', ['relationtype_id', 'contenttype_id'])

        # Adding M2M table for field subject_properties on 'RelationType'
        db.create_table('creme_core_relationtype_subject_properties', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('relationtype', models.ForeignKey(orm['creme_core.relationtype'], null=False)),
            ('cremepropertytype', models.ForeignKey(orm['creme_core.cremepropertytype'], null=False))
        ))
        db.create_unique('creme_core_relationtype_subject_properties', ['relationtype_id', 'cremepropertytype_id'])

        # Adding M2M table for field object_properties on 'RelationType'
        db.create_table('creme_core_relationtype_object_properties', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('relationtype', models.ForeignKey(orm['creme_core.relationtype'], null=False)),
            ('cremepropertytype', models.ForeignKey(orm['creme_core.cremepropertytype'], null=False))
        ))
        db.create_unique('creme_core_relationtype_object_properties', ['relationtype_id', 'cremepropertytype_id'])

        # Adding model 'Relation'
        db.create_table('creme_core_relation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('entity_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('header_filter_search_field', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('is_deleted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_actived', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.RelationType'], null=True, blank=True)),
            ('symmetric_relation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.Relation'], null=True, blank=True)),
            ('subject_entity', self.gf('django.db.models.fields.related.ForeignKey')(related_name='relations', on_delete=models.PROTECT, to=orm['creme_core.CremeEntity'])),
            ('object_entity', self.gf('django.db.models.fields.related.ForeignKey')(related_name='relations_where_is_object', on_delete=models.PROTECT, to=orm['creme_core.CremeEntity'])),
        ))
        db.send_create_signal('creme_core', ['Relation'])

        # Adding model 'SemiFixedRelationType'
        db.create_table('creme_core_semifixedrelationtype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('predicate', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('relation_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.RelationType'])),
            ('object_entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremeEntity'])),
        ))
        db.send_create_signal('creme_core', ['SemiFixedRelationType'])

        # Adding unique constraint on 'SemiFixedRelationType', fields ['relation_type', 'object_entity']
        db.create_unique('creme_core_semifixedrelationtype', ['relation_type_id', 'object_entity_id'])

        # Adding model 'CustomField'
        db.create_table('creme_core_customfield', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('field_type', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
        ))
        db.send_create_signal('creme_core', ['CustomField'])

        # Adding model 'CustomFieldString'
        db.create_table('creme_core_customfieldstring', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('custom_field', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CustomField'])),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremeEntity'])),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('creme_core', ['CustomFieldString'])

        # Adding model 'CustomFieldInteger'
        db.create_table('creme_core_customfieldinteger', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('custom_field', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CustomField'])),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremeEntity'])),
            ('value', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('creme_core', ['CustomFieldInteger'])

        # Adding model 'CustomFieldFloat'
        db.create_table('creme_core_customfieldfloat', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('custom_field', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CustomField'])),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremeEntity'])),
            ('value', self.gf('django.db.models.fields.DecimalField')(max_digits=12, decimal_places=2)),
        ))
        db.send_create_signal('creme_core', ['CustomFieldFloat'])

        # Adding model 'CustomFieldDateTime'
        db.create_table('creme_core_customfielddatetime', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('custom_field', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CustomField'])),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremeEntity'])),
            ('value', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('creme_core', ['CustomFieldDateTime'])

        # Adding model 'CustomFieldBoolean'
        db.create_table('creme_core_customfieldboolean', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('custom_field', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CustomField'])),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremeEntity'])),
            ('value', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('creme_core', ['CustomFieldBoolean'])

        # Adding model 'CustomFieldEnumValue'
        db.create_table('creme_core_customfieldenumvalue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('custom_field', self.gf('django.db.models.fields.related.ForeignKey')(related_name='customfieldenumvalue_set', to=orm['creme_core.CustomField'])),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('creme_core', ['CustomFieldEnumValue'])

        # Adding model 'CustomFieldEnum'
        db.create_table('creme_core_customfieldenum', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('custom_field', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CustomField'])),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremeEntity'])),
            ('value', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CustomFieldEnumValue'])),
        ))
        db.send_create_signal('creme_core', ['CustomFieldEnum'])

        # Adding model 'CustomFieldMultiEnum'
        db.create_table('creme_core_customfieldmultienum', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('custom_field', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CustomField'])),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremeEntity'])),
        ))
        db.send_create_signal('creme_core', ['CustomFieldMultiEnum'])

        # Adding M2M table for field value on 'CustomFieldMultiEnum'
        db.create_table('creme_core_customfieldmultienum_value', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('customfieldmultienum', models.ForeignKey(orm['creme_core.customfieldmultienum'], null=False)),
            ('customfieldenumvalue', models.ForeignKey(orm['creme_core.customfieldenumvalue'], null=False))
        ))
        db.create_unique('creme_core_customfieldmultienum_value', ['customfieldmultienum_id', 'customfieldenumvalue_id'])

        # Adding model 'HeaderFilter'
        db.create_table('creme_core_headerfilter', (
            ('id', self.gf('django.db.models.fields.CharField')(max_length=100, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('entity_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('is_custom', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('creme_core', ['HeaderFilter'])

        # Adding model 'HeaderFilterItem'
        db.create_table('creme_core_headerfilteritem', (
            ('id', self.gf('django.db.models.fields.CharField')(max_length=100, primary_key=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('type', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('header_filter', self.gf('django.db.models.fields.related.ForeignKey')(related_name='header_filter_items', to=orm['creme_core.HeaderFilter'])),
            ('has_a_filter', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('editable', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('sortable', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('filter_string', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('relation_predicat', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.RelationType'], null=True, blank=True)),
            ('relation_content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True)),
        ))
        db.send_create_signal('creme_core', ['HeaderFilterItem'])

        # Adding model 'EntityFilter'
        db.create_table('creme_core_entityfilter', (
            ('id', self.gf('django.db.models.fields.CharField')(max_length=100, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('entity_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('is_custom', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('use_or', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('creme_core', ['EntityFilter'])

        # Adding model 'EntityFilterCondition'
        db.create_table('creme_core_entityfiltercondition', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('filter', self.gf('django.db.models.fields.related.ForeignKey')(related_name='conditions', to=orm['creme_core.EntityFilter'])),
            ('type', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('creme_core', ['EntityFilterCondition'])

        # Adding model 'Mutex'
        db.create_table('creme_core_mutex', (
            ('id', self.gf('django.db.models.fields.CharField')(max_length=100, primary_key=True)),
        ))
        db.send_create_signal('creme_core', ['Mutex'])

        # Adding model 'Language'
        db.create_table('creme_core_language', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=5)),
        ))
        db.send_create_signal('creme_core', ['Language'])

        # Adding model 'Currency'
        db.create_table('creme_core_currency', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('local_symbol', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('international_symbol', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('is_custom', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('creme_core', ['Currency'])

        # Adding model 'BlockDetailviewLocation'
        db.create_table('creme_core_blockdetailviewlocation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
            ('block_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('zone', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
        ))
        db.send_create_signal('creme_core', ['BlockDetailviewLocation'])

        # Adding model 'BlockPortalLocation'
        db.create_table('creme_core_blockportallocation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('app_name', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('block_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('creme_core', ['BlockPortalLocation'])

        # Adding model 'BlockMypageLocation'
        db.create_table('creme_core_blockmypagelocation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('block_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('creme_core', ['BlockMypageLocation'])

        # Adding model 'RelationBlockItem'
        db.create_table('creme_core_relationblockitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('block_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('relation_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.RelationType'], unique=True)),
        ))
        db.send_create_signal('creme_core', ['RelationBlockItem'])

        # Adding model 'InstanceBlockConfigItem'
        db.create_table('creme_core_instanceblockconfigitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('block_id', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremeEntity'])),
            ('data', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('verbose', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
        ))
        db.send_create_signal('creme_core', ['InstanceBlockConfigItem'])

        # Adding model 'BlockState'
        db.create_table('creme_core_blockstate', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('block_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('is_open', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('show_empty_fields', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('creme_core', ['BlockState'])

        # Adding unique constraint on 'BlockState', fields ['user', 'block_id']
        db.create_unique('creme_core_blockstate', ['user_id', 'block_id'])

        # Adding model 'PreferedMenuItem'
        db.create_table('creme_core_preferedmenuitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('creme_core', ['PreferedMenuItem'])

        # Adding model 'ButtonMenuItem'
        db.create_table('creme_core_buttonmenuitem', (
            ('id', self.gf('django.db.models.fields.CharField')(max_length=100, primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
            ('button_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('creme_core', ['ButtonMenuItem'])

        # Adding model 'DateReminder'
        db.create_table('creme_core_datereminder', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date_of_remind', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('ident', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('model_content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reminders_set', to=orm['contenttypes.ContentType'])),
            ('model_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('creme_core', ['DateReminder'])

        # Adding model 'HistoryLine'
        db.create_table('creme_core_historyline', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('entity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.CremeEntity'], null=True, on_delete=models.SET_NULL)),
            ('entity_ctype', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('entity_owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('username', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('type', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('value', self.gf('django.db.models.fields.TextField')(null=True)),
        ))
        db.send_create_signal('creme_core', ['HistoryLine'])

        # Adding model 'HistoryConfigItem'
        db.create_table('creme_core_historyconfigitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('relation_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.RelationType'], unique=True)),
        ))
        db.send_create_signal('creme_core', ['HistoryConfigItem'])

        # Adding model 'SearchConfigItem'
        db.create_table('creme_core_searchconfigitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
        ))
        db.send_create_signal('creme_core', ['SearchConfigItem'])

        # Adding model 'SearchField'
        db.create_table('creme_core_searchfield', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('field', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('field_verbose_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('search_config_item', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['creme_core.SearchConfigItem'])),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('creme_core', ['SearchField'])

        # Adding model 'UserRole'
        db.create_table('creme_core_userrole', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('raw_allowed_apps', self.gf('django.db.models.fields.TextField')(default='')),
            ('raw_admin_4_apps', self.gf('django.db.models.fields.TextField')(default='')),
        ))
        db.send_create_signal('creme_core', ['UserRole'])

        # Adding M2M table for field creatable_ctypes on 'UserRole'
        db.create_table('creme_core_userrole_creatable_ctypes', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('userrole', models.ForeignKey(orm['creme_core.userrole'], null=False)),
            ('contenttype', models.ForeignKey(orm['contenttypes.contenttype'], null=False))
        ))
        db.create_unique('creme_core_userrole_creatable_ctypes', ['userrole_id', 'contenttype_id'])

        # Adding M2M table for field exportable_ctypes on 'UserRole'
        db.create_table('creme_core_userrole_exportable_ctypes', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('userrole', models.ForeignKey(orm['creme_core.userrole'], null=False)),
            ('contenttype', models.ForeignKey(orm['contenttypes.contenttype'], null=False))
        ))
        db.create_unique('creme_core_userrole_exportable_ctypes', ['userrole_id', 'contenttype_id'])

        # Adding model 'SetCredentials'
        db.create_table('creme_core_setcredentials', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('role', self.gf('django.db.models.fields.related.ForeignKey')(related_name='credentials', to=orm['creme_core.UserRole'])),
            ('value', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('set_type', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('ctype', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True)),
        ))
        db.send_create_signal('creme_core', ['SetCredentials'])

        # Adding model 'TeamM2M'
        db.create_table('creme_core_teamm2m', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('team', self.gf('django.db.models.fields.related.ForeignKey')(related_name='team_m2m_teamside', to=orm['auth.User'])),
            ('teammate', self.gf('django.db.models.fields.related.ForeignKey')(related_name='team_m2m', to=orm['auth.User'])),
        ))
        db.send_create_signal('creme_core', ['TeamM2M'])

        # Adding model 'Version'
        db.create_table('creme_core_version', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('creme_core', ['Version'])

    def backwards(self, orm):
        # Removing unique constraint on 'BlockState', fields ['user', 'block_id']
        db.delete_unique('creme_core_blockstate', ['user_id', 'block_id'])

        # Removing unique constraint on 'SemiFixedRelationType', fields ['relation_type', 'object_entity']
        db.delete_unique('creme_core_semifixedrelationtype', ['relation_type_id', 'object_entity_id'])

        # Deleting model 'CremeEntity'
        db.delete_table('creme_core_cremeentity')

        # Deleting model 'CremePropertyType'
        db.delete_table('creme_core_cremepropertytype')

        # Removing M2M table for field subject_ctypes on 'CremePropertyType'
        db.delete_table('creme_core_cremepropertytype_subject_ctypes')

        # Deleting model 'CremeProperty'
        db.delete_table('creme_core_cremeproperty')

        # Deleting model 'RelationType'
        db.delete_table('creme_core_relationtype')

        # Removing M2M table for field subject_ctypes on 'RelationType'
        db.delete_table('creme_core_relationtype_subject_ctypes')

        # Removing M2M table for field object_ctypes on 'RelationType'
        db.delete_table('creme_core_relationtype_object_ctypes')

        # Removing M2M table for field subject_properties on 'RelationType'
        db.delete_table('creme_core_relationtype_subject_properties')

        # Removing M2M table for field object_properties on 'RelationType'
        db.delete_table('creme_core_relationtype_object_properties')

        # Deleting model 'Relation'
        db.delete_table('creme_core_relation')

        # Deleting model 'SemiFixedRelationType'
        db.delete_table('creme_core_semifixedrelationtype')

        # Deleting model 'CustomField'
        db.delete_table('creme_core_customfield')

        # Deleting model 'CustomFieldString'
        db.delete_table('creme_core_customfieldstring')

        # Deleting model 'CustomFieldInteger'
        db.delete_table('creme_core_customfieldinteger')

        # Deleting model 'CustomFieldFloat'
        db.delete_table('creme_core_customfieldfloat')

        # Deleting model 'CustomFieldDateTime'
        db.delete_table('creme_core_customfielddatetime')

        # Deleting model 'CustomFieldBoolean'
        db.delete_table('creme_core_customfieldboolean')

        # Deleting model 'CustomFieldEnumValue'
        db.delete_table('creme_core_customfieldenumvalue')

        # Deleting model 'CustomFieldEnum'
        db.delete_table('creme_core_customfieldenum')

        # Deleting model 'CustomFieldMultiEnum'
        db.delete_table('creme_core_customfieldmultienum')

        # Removing M2M table for field value on 'CustomFieldMultiEnum'
        db.delete_table('creme_core_customfieldmultienum_value')

        # Deleting model 'HeaderFilter'
        db.delete_table('creme_core_headerfilter')

        # Deleting model 'HeaderFilterItem'
        db.delete_table('creme_core_headerfilteritem')

        # Deleting model 'EntityFilter'
        db.delete_table('creme_core_entityfilter')

        # Deleting model 'EntityFilterCondition'
        db.delete_table('creme_core_entityfiltercondition')

        # Deleting model 'Mutex'
        db.delete_table('creme_core_mutex')

        # Deleting model 'Language'
        db.delete_table('creme_core_language')

        # Deleting model 'Currency'
        db.delete_table('creme_core_currency')

        # Deleting model 'BlockDetailviewLocation'
        db.delete_table('creme_core_blockdetailviewlocation')

        # Deleting model 'BlockPortalLocation'
        db.delete_table('creme_core_blockportallocation')

        # Deleting model 'BlockMypageLocation'
        db.delete_table('creme_core_blockmypagelocation')

        # Deleting model 'RelationBlockItem'
        db.delete_table('creme_core_relationblockitem')

        # Deleting model 'InstanceBlockConfigItem'
        db.delete_table('creme_core_instanceblockconfigitem')

        # Deleting model 'BlockState'
        db.delete_table('creme_core_blockstate')

        # Deleting model 'PreferedMenuItem'
        db.delete_table('creme_core_preferedmenuitem')

        # Deleting model 'ButtonMenuItem'
        db.delete_table('creme_core_buttonmenuitem')

        # Deleting model 'DateReminder'
        db.delete_table('creme_core_datereminder')

        # Deleting model 'HistoryLine'
        db.delete_table('creme_core_historyline')

        # Deleting model 'HistoryConfigItem'
        db.delete_table('creme_core_historyconfigitem')

        # Deleting model 'SearchConfigItem'
        db.delete_table('creme_core_searchconfigitem')

        # Deleting model 'SearchField'
        db.delete_table('creme_core_searchfield')

        # Deleting model 'UserRole'
        db.delete_table('creme_core_userrole')

        # Removing M2M table for field creatable_ctypes on 'UserRole'
        db.delete_table('creme_core_userrole_creatable_ctypes')

        # Removing M2M table for field exportable_ctypes on 'UserRole'
        db.delete_table('creme_core_userrole_exportable_ctypes')

        # Deleting model 'SetCredentials'
        db.delete_table('creme_core_setcredentials')

        # Deleting model 'TeamM2M'
        db.delete_table('creme_core_teamm2m')

        # Deleting model 'Version'
        db.delete_table('creme_core_version')

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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'creme_core.blockdetailviewlocation': {
            'Meta': {'object_name': 'BlockDetailviewLocation'},
            'block_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'zone': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'creme_core.blockmypagelocation': {
            'Meta': {'object_name': 'BlockMypageLocation'},
            'block_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        },
        'creme_core.blockportallocation': {
            'Meta': {'object_name': 'BlockPortalLocation'},
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
            'Meta': {'object_name': 'CremePropertyType'},
            'id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'creme_core.headerfilteritem': {
            'Meta': {'ordering': "('order',)", 'object_name': 'HeaderFilterItem'},
            'editable': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'filter_string': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'has_a_filter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'header_filter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'header_filter_items'", 'to': "orm['creme_core.HeaderFilter']"}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'relation_content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'relation_predicat': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.RelationType']", 'null': 'True', 'blank': 'True'}),
            'sortable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'type': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
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
            'relation_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.RelationType']", 'unique': 'True'})
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
        'creme_core.searchconfigitem': {
            'Meta': {'object_name': 'SearchConfigItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        },
        'creme_core.searchfield': {
            'Meta': {'ordering': "('order',)", 'object_name': 'SearchField'},
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
        'creme_core.version': {
            'Meta': {'object_name': 'Version'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['creme_core']