# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    depends_on = (
        ("creme_core", "0001_initial"),
    )

    def forwards(self, orm):

        # Adding model 'TaskStatus'
        db.create_table('projects_taskstatus', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('color_code', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('is_custom', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('projects', ['TaskStatus'])

        # Adding model 'ProjectStatus'
        db.create_table('projects_projectstatus', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('color_code', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('projects', ['ProjectStatus'])

        # Adding model 'Project'
        db.create_table('projects_project', (
            ('cremeentity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['creme_core.CremeEntity'], unique=True, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['projects.ProjectStatus'])),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('effective_end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('projects', ['Project'])

        # Adding model 'ProjectTask'
        db.create_table('projects_projecttask', (
            ('activity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['activities.Activity'], unique=True, primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='tasks_set', to=orm['projects.Project'])),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('duration', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('tstatus', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['projects.TaskStatus'])),
        ))
        db.send_create_signal('projects', ['ProjectTask'])

        # Adding M2M table for field parent_tasks on 'ProjectTask'
        db.create_table('projects_projecttask_parent_tasks', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_projecttask', models.ForeignKey(orm['projects.projecttask'], null=False)),
            ('to_projecttask', models.ForeignKey(orm['projects.projecttask'], null=False))
        ))
        db.create_unique('projects_projecttask_parent_tasks', ['from_projecttask_id', 'to_projecttask_id'])

        # Adding model 'Resource'
        db.create_table('projects_resource', (
            ('cremeentity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['creme_core.CremeEntity'], unique=True, primary_key=True)),
            ('linked_contact', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['persons.Contact'])),
            ('hourly_cost', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('task', self.gf('django.db.models.fields.related.ForeignKey')(related_name='resources_set', to=orm['projects.ProjectTask'])),
        ))
        db.send_create_signal('projects', ['Resource'])

        # Adding model 'WorkingPeriod'
        db.create_table('projects_workingperiod', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('duration', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('task', self.gf('django.db.models.fields.related.ForeignKey')(related_name='tasks_set', to=orm['projects.ProjectTask'])),
            ('resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['projects.Resource'])),
        ))
        db.send_create_signal('projects', ['WorkingPeriod'])


    def backwards(self, orm):

        # Deleting model 'TaskStatus'
        db.delete_table('projects_taskstatus')

        # Deleting model 'ProjectStatus'
        db.delete_table('projects_projectstatus')

        # Deleting model 'Project'
        db.delete_table('projects_project')

        # Deleting model 'ProjectTask'
        db.delete_table('projects_projecttask')

        # Removing M2M table for field parent_tasks on 'ProjectTask'
        db.delete_table('projects_projecttask_parent_tasks')

        # Deleting model 'Resource'
        db.delete_table('projects_resource')

        # Deleting model 'WorkingPeriod'
        db.delete_table('projects_workingperiod')


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
        'creme_core.language': {
            'Meta': {'object_name': 'Language'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'creme_core.userrole': {
            'Meta': {'object_name': 'UserRole'},
            'creatable_ctypes': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'symmetrical': 'False'}),
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
        'persons.civility': {
            'Meta': {'object_name': 'Civility'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'persons.contact': {
            'Meta': {'ordering': "('last_name', 'first_name')", 'object_name': 'Contact', '_ormbases': ['creme_core.CremeEntity']},
            'billing_address': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'billing_address_contact_set'", 'null': 'True', 'to': "orm['persons.Address']"}),
            'birthday': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'civility': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['persons.Civility']", 'null': 'True', 'blank': 'True'}),
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['media_managers.Image']", 'null': 'True', 'blank': 'True'}),
            'is_user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'related_contact'", 'null': 'True', 'to': "orm['auth.User']"}),
            'language': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['creme_core.Language']", 'null': 'True', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'mobile': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'position': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['persons.Position']", 'null': 'True', 'blank': 'True'}),
            'sector': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['persons.Sector']", 'null': 'True', 'blank': 'True'}),
            'shipping_address': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'shipping_address_contact_set'", 'null': 'True', 'to': "orm['persons.Address']"}),
            'skype': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'url_site': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        },
        'persons.position': {
            'Meta': {'object_name': 'Position'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'persons.sector': {
            'Meta': {'object_name': 'Sector'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Project', '_ormbases': ['creme_core.CremeEntity']},
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'effective_end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.ProjectStatus']"})
        },
        'projects.projectstatus': {
            'Meta': {'object_name': 'ProjectStatus'},
            'color_code': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.projecttask': {
            'Meta': {'ordering': "('-start',)", 'object_name': 'ProjectTask', '_ormbases': ['activities.Activity']},
            'activity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['activities.Activity']", 'unique': 'True', 'primary_key': 'True'}),
            'duration': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'parent_tasks': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'children_set'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['projects.ProjectTask']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tasks_set'", 'to': "orm['projects.Project']"}),
            'tstatus': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.TaskStatus']"})
        },
        'projects.resource': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Resource', '_ormbases': ['creme_core.CremeEntity']},
            'cremeentity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['creme_core.CremeEntity']", 'unique': 'True', 'primary_key': 'True'}),
            'hourly_cost': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'linked_contact': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['persons.Contact']"}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources_set'", 'to': "orm['projects.ProjectTask']"})
        },
        'projects.taskstatus': {
            'Meta': {'object_name': 'TaskStatus'},
            'color_code': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_custom': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.workingperiod': {
            'Meta': {'object_name': 'WorkingPeriod'},
            'duration': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Resource']"}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tasks_set'", 'to': "orm['projects.ProjectTask']"})
        }
    }

    complete_apps = ['projects']
