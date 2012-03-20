# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        try:
            get_reltype = orm['creme_core.RelationType'].objects.get
            rel_sub = get_reltype(id="commercial-subject_opportunity_linked")

            relations = orm['creme_core.Relation'].objects.filter(type=rel_sub)

            for relation in relations:
                relation.type = get_reltype(id="commercial-subject_complete_goal")
                relation.save()
                symmetric = relation.symmetric_relation
                symmetric.type = get_reltype(id="commercial-object_complete_goal")
                symmetric.save()

            rel_sub.delete() # automatically delete symetric relation
        except Exception as e:
            print e


    def backwards(self, orm):
        "Write your backwards methods here."


    models = {
        'activities.activity': {
            'Meta': {'ordering': "('-start',)", 'object_name': 'Activity', '_ormbases': ['creme_core.CremeEntity']},
            'busy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'calendars': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['activities.Calendar']", 'null': 'True', 'blank': 'True'}),
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'is_all_day': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'minutes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['activities.Status']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['activities.ActivityType']"})
        },
        'activities.activitytype': {
            'Meta': {'object_name': 'ActivityType'},
            'color': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'default_day_duration': ('django.db.models.fields.IntegerField', [], {}),
            'default_hour_duration': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'activities.calendar': {
            'Meta': {'ordering': "['name']", 'object_name': 'Calendar'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'activities.status': {
            'Meta': {'object_name': 'Status'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
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
        'commercial.act': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Act', '_ormbases': ['creme_core.CremeEntity']},
            'act_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['commercial.ActType']"}),
            'cost': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'due_date': ('django.db.models.fields.DateField', [], {}),
            'expected_sales': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'goal': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['commercial.MarketSegment']"}),
            'start': ('django.db.models.fields.DateField', [], {})
        },
        'commercial.actobjective': {
            'Meta': {'object_name': 'ActObjective'},
            'act': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'objectives'", 'to': "orm['commercial.Act']"}),
            'counter': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'counter_goal': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'ctype': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'commercial.actobjectivepattern': {
            'Meta': {'ordering': "('id',)", 'object_name': 'ActObjectivePattern', '_ormbases': ['creme_core.CremeEntity']},
            'average_sales': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['commercial.MarketSegment']"})
        },
        'commercial.actobjectivepatterncomponent': {
            'Meta': {'object_name': 'ActObjectivePatternComponent'},
            'ctype': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'null': 'True', 'to': "orm['commercial.ActObjectivePatternComponent']"}),
            'pattern': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'components'", 'to': "orm['commercial.ActObjectivePattern']"}),
            'success_rate': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'commercial.acttype': {
            'Meta': {'object_name': 'ActType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '75'})
        },
        'commercial.commercialapproach': {
            'Meta': {'object_name': 'CommercialApproach'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'entity_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'comapp_entity_set'", 'to': "orm['contenttypes.ContentType']"}),
            'entity_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ok_or_in_futur': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'related_activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['activities.Activity']", 'null': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'commercial.commercialasset': {
            'Meta': {'object_name': 'CommercialAsset'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'strategy': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'assets'", 'to': "orm['commercial.Strategy']"})
        },
        'commercial.commercialassetscore': {
            'Meta': {'object_name': 'CommercialAssetScore'},
            'asset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['commercial.CommercialAsset']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organisation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['persons.Organisation']"}),
            'score': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'segment_desc': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['commercial.MarketSegmentDescription']"})
        },
        'commercial.marketsegment': {
            'Meta': {'object_name': 'MarketSegment'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'property_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremePropertyType']"})
        },
        'commercial.marketsegmentcategory': {
            'Meta': {'object_name': 'MarketSegmentCategory'},
            'category': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organisation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['persons.Organisation']"}),
            'segment_desc': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['commercial.MarketSegmentDescription']"}),
            'strategy': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['commercial.Strategy']"})
        },
        'commercial.marketsegmentcharm': {
            'Meta': {'object_name': 'MarketSegmentCharm'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'strategy': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'charms'", 'to': "orm['commercial.Strategy']"})
        },
        'commercial.marketsegmentcharmscore': {
            'Meta': {'object_name': 'MarketSegmentCharmScore'},
            'charm': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['commercial.MarketSegmentCharm']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organisation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['persons.Organisation']"}),
            'score': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'segment_desc': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['commercial.MarketSegmentDescription']"})
        },
        'commercial.marketsegmentdescription': {
            'Meta': {'object_name': 'MarketSegmentDescription'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'place': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'price': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'product': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'promotion': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['commercial.MarketSegment']"}),
            'strategy': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'segment_info'", 'to': "orm['commercial.Strategy']"})
        },
        'commercial.strategy': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Strategy', '_ormbases': ['creme_core.CremeEntity']},
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'evaluated_orgas': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['persons.Organisation']", 'null': 'True', 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
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
        'creme_core.entitycredentials': {
            'Meta': {'object_name': 'EntityCredentials'},
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'credentials'", 'null': 'True', 'to': "orm['creme_core.CremeEntity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': "'5'"})
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
            'Meta': {'object_name': 'HeaderFilterItem'},
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
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'entity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['creme_core.CremeEntity']", 'null': 'True'}),
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
            'object_entity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relations_where_is_object'", 'to': "orm['creme_core.CremeEntity']"}),
            'subject_entity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relations'", 'to': "orm['creme_core.CremeEntity']"}),
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
        'media_managers.image': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Image', '_ormbases': ['creme_core.CremeEntity']},
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'Image_media_category_set'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['media_managers.MediaCategory']"}),
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '500'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'width': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        'media_managers.mediacategory': {
            'Meta': {'object_name': 'MediaCategory'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'opportunities.opportunity': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Opportunity', '_ormbases': ['creme_core.CremeEntity']},
            'chance_to_win': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'closing_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'currency': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': "orm['creme_core.Currency']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'estimated_sales': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'expected_closing_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'first_action_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'made_sales': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'origin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['opportunities.Origin']", 'null': 'True', 'blank': 'True'}),
            'reference': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'sales_phase': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['opportunities.SalesPhase']"})
        },
        'opportunities.origin': {
            'Meta': {'object_name': 'Origin'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'opportunities.salesphase': {
            'Meta': {'ordering': "('order',)", 'object_name': 'SalesPhase'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'})
        },
        'persons.address': {
            'Meta': {'object_name': 'Address'},
            'address': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'object_set'", 'to': "orm['contenttypes.ContentType']"}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'department': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'po_box': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'zipcode': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        },
        'persons.legalform': {
            'Meta': {'object_name': 'LegalForm'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'persons.organisation': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Organisation', '_ormbases': ['creme_core.CremeEntity']},
            'annual_revenue': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'billing_address': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'billing_address_orga_set'", 'null': 'True', 'to': "orm['persons.Address']"}),
            'capital': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'creation_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['media_managers.Image']", 'null': 'True', 'blank': 'True'}),
            'legal_form': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['persons.LegalForm']", 'null': 'True', 'blank': 'True'}),
            'naf': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'rcs': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['persons.Sector']", 'null': 'True', 'blank': 'True'}),
            'shipping_address': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'shipping_address_orga_set'", 'null': 'True', 'to': "orm['persons.Address']"}),
            'siren': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'siret': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'staff_size': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['persons.StaffSize']", 'null': 'True', 'blank': 'True'}),
            'subject_to_vat': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'tvaintra': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'url_site': ('django.db.models.fields.URLField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        },
        'persons.sector': {
            'Meta': {'object_name': 'Sector'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'persons.staffsize': {
            'Meta': {'object_name': 'StaffSize'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'size': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['creme_core', 'opportunities', 'commercial']
