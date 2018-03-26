# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal
import re
import uuid

import pytz

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import migrations, models
from django.utils.timezone import now
from django.db.models import deletion

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    # replaces = [
    #     (b'creme_core', '0001_initial'),
    #     (b'creme_core', '0015_v1_7__create_job_models'),
    #     (b'creme_core', '0016_v1_7__entity_indexes_count'),
    #     (b'creme_core', '0017_v1_7__user_tz_n_theme'),
    #     (b'creme_core', '0018_v1_7__cremeuser_settings'),
    #     (b'creme_core', '0019_v1_7__properties_uniqueness_1'),
    #     (b'creme_core', '0020_v1_7__properties_uniqueness_2'),
    #     (b'creme_core', '0021_v1_7__old_prop_managed_custom'),
    #     (b'creme_core', '0022_v1_7__rtype_min_display'),
    #     (b'creme_core', '0023_v1_7__rm_merge_button'),
    #     (b'creme_core', '0024_v1_7__roles_uniqueness_1'),
    #     (b'creme_core', '0025_v1_7__roles_uniqueness_2'),
    #     (b'creme_core', '0026_v1_7__customfields_uniqueness_1'),
    #     (b'creme_core', '0027_v1_7__customfields_uniqueness_2'),
    #     (b'creme_core', '0028_v1_7__customfields_uniqueness_3'),
    #     (b'creme_core', '0029_v1_7__cremeentity_uuid_1'),
    #     (b'creme_core', '0030_v1_7__cremeentity_uuid_2'),
    #     (b'creme_core', '0031_v1_7__cremeentity_uuid_3'),
    #     (b'creme_core', '0032_v1_7__fix_non_custom_hfilters'),
    #     (b'creme_core', '0033_v1_7__set_version'),
    # ]

    initial = True
    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
                name='UserRole',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                    ('raw_allowed_apps', models.TextField(default=b'')),
                    ('raw_admin_4_apps', models.TextField(default=b'')),
                    ('creatable_ctypes',
                     models.ManyToManyField(related_name='roles_allowing_creation', verbose_name='Creatable resources',
                                            to=b'contenttypes.ContentType')),
                    ('exportable_ctypes',
                     models.ManyToManyField(related_name='roles_allowing_export', verbose_name='Exportable resources',
                                            to=b'contenttypes.ContentType')),
                ],
                options={
                    'verbose_name':        'Role',
                    'verbose_name_plural': 'Roles',
                },
        ),
        migrations.CreateModel(
                name='SetCredentials',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('value', models.PositiveSmallIntegerField()),
                    ('set_type', models.PositiveIntegerField()),
                    ('ctype', creme.creme_core.models.fields.CTypeForeignKey(blank=True, to='contenttypes.ContentType',
                                                                             null=True)),
                    ('role', models.ForeignKey(related_name='credentials', to='creme_core.UserRole', on_delete=deletion.CASCADE)),
                ],
        ),
        migrations.CreateModel(
                name='CremeUser',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('password', models.CharField(max_length=128, verbose_name='password')),
                    ('last_login', models.DateTimeField(null=True, verbose_name='last login', blank=True)),
                    ('username', models.CharField(help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.',
                                                  unique=True, max_length=30, verbose_name='Username',
                                                  validators=[RegexValidator(re.compile(b'^[\\w.@+-]+$'),
                                                                             'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.',
                                                                             b'invalid',
                                                                            ),
                                                  ],
                                                 )
                    ),
                    ('first_name', models.CharField(max_length=100, verbose_name='First name', blank=True)),
                    ('last_name', models.CharField(max_length=100, verbose_name='Last name', blank=True)),
                    ('email', models.EmailField(max_length=254, verbose_name='Email address', blank=True)),
                    ('date_joined', models.DateTimeField(default=now, verbose_name='Date joined')),
                    ('is_active', models.BooleanField(default=True, verbose_name='Active?')),
                    ('is_staff', models.BooleanField(default=False, verbose_name='Is staff?')),
                    ('is_superuser', models.BooleanField(default=False, verbose_name='Is a superuser?')),
                    ('is_team', models.BooleanField(default=False, verbose_name='Is a team?')),
                    ('role', models.ForeignKey(on_delete=deletion.PROTECT, verbose_name='Role',
                                               to='creme_core.UserRole', null=True,
                                              )
                    ),
                    ('teammates_set', models.ManyToManyField(related_name='teams_set', verbose_name='Teammates',
                                                             to=settings.AUTH_USER_MODEL,
                                                            )
                    ),
                    ('theme', models.CharField(default=settings.THEMES[0][0], max_length=50, verbose_name='Theme',
                                               choices=settings.THEMES,
                                              ),
                    ),
                    ('time_zone', models.CharField(default=settings.TIME_ZONE,
                                                   max_length=50, verbose_name='Time zone',
                                                   choices=[(tz, tz) for tz in pytz.common_timezones],
                                                  )
                    ),
                    ('json_settings', models.TextField(default='{}', editable=False)),
                ],
                options={
                    'ordering':            ('username',),
                    'verbose_name':        'User',
                    'verbose_name_plural': 'Users',
                },
        ),
        migrations.CreateModel(
            name='BlockDetailviewLocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('block_id', models.CharField(max_length=100)),
                ('order', models.PositiveIntegerField()),
                ('zone', models.PositiveSmallIntegerField()),
                ('content_type', creme.creme_core.models.fields.CTypeForeignKey(verbose_name='Related type', to='contenttypes.ContentType', null=True)),
                ('role', models.ForeignKey(default=None, verbose_name='Related role', to='creme_core.UserRole', null=True, on_delete=deletion.CASCADE)),
                ('superuser', models.BooleanField(default=False, verbose_name='related to superusers', editable=False)),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='BlockMypageLocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('block_id', models.CharField(max_length=100)),
                ('order', models.PositiveIntegerField()),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True, on_delete=deletion.CASCADE)),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='BlockPortalLocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('app_name', models.CharField(max_length=40)),
                ('block_id', models.CharField(max_length=100)),
                ('order', models.PositiveIntegerField()),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='BlockState',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('block_id', models.CharField(max_length=100, verbose_name='Block ID')),
                ('is_open', models.BooleanField(default=True)),
                ('show_empty_fields', models.BooleanField(default=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=deletion.CASCADE)),
            ],
            options={
                'unique_together': {('user', 'block_id')},
            }
        ),
        migrations.CreateModel(
            name='ButtonMenuItem',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, primary_key=True)),
                ('button_id', models.CharField(max_length=100, verbose_name='Button ID')),
                ('order', models.PositiveIntegerField(verbose_name='Priority')),
                ('content_type', creme.creme_core.models.fields.CTypeForeignKey(verbose_name='Related type', to='contenttypes.ContentType', null=True)),
            ],
            options={
                'verbose_name': 'Button to display',
                'verbose_name_plural': 'Buttons to display',
            },
        ),
        migrations.CreateModel(
            name='CremeEntity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
                ('created', creme.creme_core.models.fields.CreationDateTimeField(default=now, verbose_name='Creation date', editable=False, blank=True)),
                ('modified', creme.creme_core.models.fields.ModificationDateTimeField(default=now, verbose_name='Last modification', editable=False, blank=True)),
                ('header_filter_search_field', models.CharField(max_length=200, editable=False)),
                ('is_deleted', models.BooleanField(default=False, editable=False)),
                ('is_actived', models.BooleanField(default=False, editable=False)),
                ('entity_type', creme.creme_core.models.fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType')),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('header_filter_search_field',),
                'index_together': {('entity_type', 'is_deleted')},
            },
        ),
        migrations.CreateModel(
            name='CremePropertyType',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, primary_key=True)),
                ('text', models.CharField(unique=True, max_length=200, verbose_name='Text')),
                ('is_custom', models.BooleanField(default=False)),
                ('is_copiable', models.BooleanField(default=True, verbose_name='Is copiable')),
                ('subject_ctypes', models.ManyToManyField(related_name='subject_ctypes_creme_property_set',
                                                          verbose_name='Applies on entities with following types',
                                                          to=b'contenttypes.ContentType', blank=True,
                                                         )
                ),
            ],
            options={
                'ordering': ('text',),
                'verbose_name': 'Type of property',
                'verbose_name_plural': 'Types of property',
            },
        ),
        migrations.CreateModel(
            name='CremeProperty',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creme_entity', models.ForeignKey(related_name='properties', to='creme_core.CremeEntity', on_delete=deletion.CASCADE)),
                ('type', models.ForeignKey(to='creme_core.CremePropertyType', on_delete=deletion.CASCADE)),
            ],
            options={
                'verbose_name': 'Property',
                'verbose_name_plural': 'Properties',
                'unique_together': {('type', 'creme_entity')},
            },
        ),
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Currency')),
                ('local_symbol', models.CharField(max_length=100, verbose_name='Local symbol')),
                ('international_symbol', models.CharField(max_length=100, verbose_name='International symbol')),
                ('is_custom', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Currency',
                'verbose_name_plural': 'Currencies',
            },
        ),
        migrations.CreateModel(
            name='CustomBlockConfigItem',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('json_cells', models.TextField(null=True, editable=False)),
                ('content_type', creme.creme_core.models.fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType', verbose_name='Related type')),
            ],
        ),
        migrations.CreateModel(
            name='CustomField',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
                ('name', models.CharField(max_length=100, verbose_name='Field name')),
                ('field_type', models.PositiveSmallIntegerField(verbose_name='Field type')),
                ('content_type', creme.creme_core.models.fields.CTypeForeignKey(verbose_name='Related type', to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ('id',),
                'verbose_name': 'Custom field',
                'verbose_name_plural': 'Custom fields',
                'unique_together': {('content_type', 'name')},
            },
        ),
        migrations.CreateModel(
            name='CustomFieldBoolean',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.BooleanField(default=False)),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=deletion.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldDateTime',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.DateTimeField()),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=deletion.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldEnumValue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=100)),
                ('custom_field', models.ForeignKey(related_name='customfieldenumvalue_set', to='creme_core.CustomField', on_delete=deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldEnum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=deletion.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=deletion.CASCADE)),
                ('value', models.ForeignKey(to='creme_core.CustomFieldEnumValue', on_delete=deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldFloat',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.DecimalField(max_digits=12, decimal_places=2)),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=deletion.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldInteger',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.IntegerField()),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=deletion.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldMultiEnum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=deletion.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=deletion.CASCADE)),
                ('value', models.ManyToManyField(to=b'creme_core.CustomFieldEnumValue')),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldString',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=100)),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=deletion.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='DateReminder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_of_remind', models.DateTimeField(null=True, blank=True)),
                ('ident', models.PositiveIntegerField()),
                ('model_id', models.PositiveIntegerField()),
                ('model_content_type', models.ForeignKey(related_name='reminders_set', to='contenttypes.ContentType', on_delete=deletion.CASCADE)),
            ],
            options={
                'verbose_name': 'Reminder',
                'verbose_name_plural': 'Reminders',
            },
        ),
        migrations.CreateModel(
            name='EntityFilter',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('is_private', models.BooleanField(default=False, verbose_name='Is private?')),
                ('use_or', models.BooleanField(default=False, verbose_name='Use "OR"')),
                ('entity_type', creme.creme_core.models.fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType')),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Filter of Entity',
                'verbose_name_plural': 'Filters of Entity',
            },
        ),
        migrations.CreateModel(
            name='EntityFilterCondition',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.PositiveSmallIntegerField()),
                ('name', models.CharField(max_length=100)),
                ('value', models.TextField()),
                ('filter', models.ForeignKey(related_name='conditions', to='creme_core.EntityFilter', on_delete=deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='HeaderFilter',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name of the view')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('is_private', models.BooleanField(default=False, verbose_name='Is private?')),
                ('json_cells', models.TextField(null=True, editable=False)),
                ('entity_type', creme.creme_core.models.fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType')),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='HistoryLine',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('username', models.CharField(max_length=30)),
                ('date', creme.creme_core.models.fields.CreationDateTimeField(default=now, verbose_name='Date', editable=False, blank=True)),
                ('type', models.PositiveSmallIntegerField(verbose_name='Type')),
                ('value', models.TextField(null=True)),
                ('entity', models.ForeignKey(on_delete=deletion.SET_NULL, to='creme_core.CremeEntity', null=True)),
                ('entity_ctype', creme.creme_core.models.fields.CTypeForeignKey(to='contenttypes.ContentType')),
                ('entity_owner', creme.creme_core.models.fields.CremeUserForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Line of history',
                'verbose_name_plural': 'Lines of history',
            },
        ),
        migrations.CreateModel(
            name='InstanceBlockConfigItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('block_id', models.CharField(verbose_name='Brick ID', max_length=300, editable=False)),
                ('data', models.TextField(null=True, blank=True)),
                ('verbose', models.CharField(max_length=200, null=True, verbose_name='Verbose', blank=True)),
                ('entity', models.ForeignKey(verbose_name='Block related entity', to='creme_core.CremeEntity', on_delete=deletion.CASCADE)),
            ],
            options={
                'ordering': ('id',),
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('code', models.CharField(max_length=5, verbose_name='Code')),
            ],
            options={
                'verbose_name': 'Language',
                'verbose_name_plural': 'Languages',
            },
        ),
        migrations.CreateModel(
            name='Mutex',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='PreferedMenuItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(max_length=100, verbose_name='Label', blank=True)),
                ('url', models.CharField(max_length=100, verbose_name='Url', blank=True)),
                ('order', models.PositiveIntegerField(verbose_name='Order')),
                ('user', models.ForeignKey(verbose_name='User', to=settings.AUTH_USER_MODEL, null=True, on_delete=deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='RelationType',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, primary_key=True)),
                ('is_internal', models.BooleanField(default=False)),
                ('is_custom', models.BooleanField(default=False)),
                ('is_copiable', models.BooleanField(default=True)),
                ('predicate', models.CharField(max_length=100, verbose_name='Predicate')),
                ('subject_ctypes', models.ManyToManyField(related_name='relationtype_subjects_set', to=b'contenttypes.ContentType', blank=True)),
                ('object_ctypes', models.ManyToManyField(related_name='relationtype_objects_set', to=b'contenttypes.ContentType', blank=True)),
                ('subject_properties', models.ManyToManyField(related_name='relationtype_subjects_set', to=b'creme_core.CremePropertyType', blank=True)),
                ('object_properties', models.ManyToManyField(related_name='relationtype_objects_set', to=b'creme_core.CremePropertyType', blank=True)),
                ('symmetric_type', models.ForeignKey(blank=True, to='creme_core.RelationType', null=True, on_delete=deletion.CASCADE)),
                ('minimal_display', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Type of relationship',
                'verbose_name_plural': 'Types of relationship',
            },
        ),
        migrations.CreateModel(
            name='Relation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', creme.creme_core.models.fields.CreationDateTimeField(default=now, verbose_name='Creation date', editable=False, blank=True)),
                ('modified', creme.creme_core.models.fields.ModificationDateTimeField(default=now, verbose_name='Last modification', editable=False, blank=True)),
                ('header_filter_search_field', models.CharField(max_length=200, editable=False)),
                ('is_deleted', models.BooleanField(default=False, editable=False)),
                ('is_actived', models.BooleanField(default=False, editable=False)),
                ('entity_type', creme.creme_core.models.fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType')),
                ('object_entity', models.ForeignKey(related_name='relations_where_is_object', on_delete=deletion.PROTECT, to='creme_core.CremeEntity')),
                ('subject_entity', models.ForeignKey(related_name='relations', on_delete=deletion.PROTECT, to='creme_core.CremeEntity')),
                ('symmetric_relation', models.ForeignKey(blank=True, to='creme_core.Relation', null=True, on_delete=deletion.CASCADE)),
                ('type', models.ForeignKey(blank=True, to='creme_core.RelationType', null=True, on_delete=deletion.CASCADE)),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Relationship',
                'verbose_name_plural': 'Relationships',
            },
        ),
        migrations.CreateModel(
            name='RelationBlockItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('block_id', models.CharField(verbose_name='Block ID', max_length=100, editable=False)),
                ('json_cells_map', models.TextField(null=True, editable=False)),
                ('relation_type', models.OneToOneField(verbose_name='Related type of relationship', to='creme_core.RelationType', on_delete=deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='SearchConfigItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('disabled', models.BooleanField(default=False, verbose_name='Disabled?')),
                ('field_names', models.TextField(null=True)),
                ('content_type', creme.creme_core.models.fields.EntityCTypeForeignKey(verbose_name='Related resource', to='contenttypes.ContentType')),
                ('role', models.ForeignKey(default=None, verbose_name='Related role', to='creme_core.UserRole', null=True, on_delete=deletion.CASCADE)),
                ('superuser', models.BooleanField(default=False, verbose_name='related to superusers', editable=False)),
            ],
            options={
                'unique_together': {('content_type', 'role', 'superuser')},
            }
        ),
        migrations.CreateModel(
            name='SemiFixedRelationType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('predicate', models.CharField(unique=True, max_length=100, verbose_name='Predicate')),
                ('object_entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=deletion.CASCADE)),
                ('relation_type', models.ForeignKey(to='creme_core.RelationType', on_delete=deletion.CASCADE)),
            ],
            options={
                'ordering': ('predicate',),
                'verbose_name': 'Semi-fixed type of relationship',
                'verbose_name_plural': 'Semi-fixed types of relationship',
                'unique_together': {('relation_type', 'object_entity')},
            },
        ),
        migrations.CreateModel(
            name='SettingValue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key_id', models.CharField(max_length=100)),
                ('value_str', models.TextField()),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True, on_delete=deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='HistoryConfigItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('relation_type', models.OneToOneField(to='creme_core.RelationType', on_delete=deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='Vat',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.DecimalField(default=Decimal('20.0'), verbose_name='VAT', max_digits=4, decimal_places=2)),
                ('is_default', models.BooleanField(default=False, verbose_name='Is default?')),
                ('is_custom', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('value',),
                'verbose_name': 'VAT',
                'verbose_name_plural': 'VAT',
            },
        ),
        migrations.CreateModel(
            name='Version',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='FieldsConfig',
            fields=[
                ('content_type', creme.creme_core.models.fields.CTypeOneToOneField(primary_key=True, serialize=False,
                                                                                   editable=False,
                                                                                   to='contenttypes.ContentType',
                                                                                  )
                ),
                ('raw_descriptions', models.TextField(editable=False)),
            ],
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type_id', models.CharField(verbose_name='Type of job', max_length=48, editable=False)),
                ('enabled', models.BooleanField(default=True, verbose_name='Enabled', editable=False)),
                ('language', models.CharField(verbose_name='Language', max_length=10, editable=False)),
                ('reference_run', models.DateTimeField(verbose_name='Reference run')),
                ('periodicity', creme.creme_core.models.fields.DatePeriodField(null=True, verbose_name='Periodicity')),
                ('last_run', models.DateTimeField(verbose_name='Last run', null=True, editable=False)),
                ('ack_errors', models.PositiveIntegerField(default=0, editable=False)),
                ('status', models.PositiveSmallIntegerField(default=1, verbose_name='Status', editable=False,
                                                            choices=[(1, 'Waiting'),
                                                                     (10, 'Error'),
                                                                     (20, 'Completed successfully'),
                                                                    ],
                                                            )
                 ),
                ('error', models.TextField(verbose_name='Error', null=True, editable=False)),
                ('raw_data', models.TextField(editable=False)),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(editable=False,
                                                                            to=settings.AUTH_USER_MODEL,
                                                                            null=True, verbose_name='User',
                                                                           )
                ),
            ],
            options={
                'ordering':            ('id',),
                'verbose_name':        'Job',
                'verbose_name_plural': 'Jobs',
            },
        ),
        migrations.CreateModel(
            name='JobResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('raw_messages', models.TextField(null=True)),
                ('job', models.ForeignKey(to='creme_core.Job', on_delete=deletion.CASCADE)),
            ],
            options={},
        ),
        migrations.CreateModel(
            name='EntityJobResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('raw_messages', models.TextField(null=True)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', null=True, on_delete=deletion.CASCADE)),
                ('job', models.ForeignKey(to='creme_core.Job', on_delete=deletion.CASCADE)),
            ],
            options={},
        ),
        migrations.CreateModel(
            name='MassImportJobResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('raw_messages', models.TextField(null=True)),
                ('raw_line', models.TextField()),
                ('updated', models.BooleanField(default=False)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', null=True, on_delete=deletion.CASCADE)),
                ('job', models.ForeignKey(to='creme_core.Job', on_delete=deletion.CASCADE)),
            ],
            options={},
        ),
    ]

    if settings.TESTS_ON:
        operations.extend([
            migrations.CreateModel(
                name='FakeActivityType',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                    ('order', creme.creme_core.models.fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Type of activity',
                    'verbose_name_plural': 'Test Types of activity',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeActivity',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=models.CASCADE,
                                                            )
                    ),
                    ('title', models.CharField(unique=True, max_length=100, verbose_name='Title')),
                    ('start', models.DateTimeField(null=True, verbose_name='Start', blank=True)),
                    ('end', models.DateTimeField(null=True, verbose_name='End', blank=True)),
                    ('type', models.ForeignKey(verbose_name='Activity type', to='creme_core.FakeActivityType', on_delete=deletion.PROTECT)),
                ],
                options={
                    'ordering': ('-start',),
                    'verbose_name': 'Test Activity',
                    'verbose_name_plural': 'Test Activities',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeFolderCategory',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(unique=True, max_length=100, verbose_name='Category name')),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Folder category',
                    'verbose_name_plural': 'Test Folder categories',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeFolder',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=models.CASCADE,
                                                            )
                    ),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                    ('category', models.ForeignKey(on_delete=deletion.SET_NULL, verbose_name='Category', blank=True, to='creme_core.FakeFolderCategory', null=True)), #related_name='folder_category_set'
                    ('parent', models.ForeignKey(related_name='children', verbose_name='Parent folder', blank=True, to='creme_core.FakeFolder', null=True, on_delete=deletion.CASCADE)),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test Folder',
                    'verbose_name_plural': 'Test Folders',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeDocument',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=models.CASCADE,
                                                            )
                    ),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                    ('filedata', models.FileField(upload_to=b'upload/creme_core-tests', max_length=100, verbose_name='File')),
                    # ('folder', models.ForeignKey(on_delete=deletion.PROTECT, verbose_name='Folder', to='creme_core.FakeFolder')),
                    ('linked_folder', models.ForeignKey(on_delete=deletion.PROTECT, verbose_name='Folder', to='creme_core.FakeFolder')),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test Document',
                    'verbose_name_plural': 'Test Documents',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeFileComponent',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('filedata', models.FileField(null=True, upload_to=b'upload/creme_core-tests', max_length=100, verbose_name='File', blank=True)),
                ],
                options={
                    'verbose_name': 'Test File component',
                    'verbose_name_plural': 'Test File components',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeImageCategory',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Image category',
                    'verbose_name_plural': 'Test Image categories',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeImage',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=models.CASCADE,
                                                            )
                    ),
                    ('name', models.CharField(max_length=100, null=True, verbose_name='Name', blank=True)),
                    ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                    ('filedata', models.FileField(upload_to=b'upload/creme_core-tests', max_length=100, verbose_name='File', editable=False)),
                    ('categories', models.ManyToManyField(related_name='+', verbose_name='Categories', to='creme_core.FakeImageCategory', blank=True)),
                    ('exif_date', models.DateField(null=True, verbose_name='Exif date', blank=True)),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Image',
                    'verbose_name_plural': 'Test Images',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeAddress',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('value', models.TextField(null=True, verbose_name='Address', blank=True)),
                    ('zipcode', models.CharField(max_length=100, null=True, verbose_name='Zip code', blank=True)),
                    ('city', models.CharField(max_length=100, null=True, verbose_name='City', blank=True)),
                    ('department', models.CharField(max_length=100, null=True, verbose_name='Department', blank=True)),
                    ('country', models.CharField(max_length=40, null=True, verbose_name='Country', blank=True)),
                    ('entity', models.ForeignKey(related_name='+', editable=False, to='creme_core.CremeEntity', on_delete=deletion.CASCADE)),
                ],
                options={
                    'verbose_name': 'Test address',
                    'verbose_name_plural': 'Test addresses',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeCivility',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                    ('shortcut', models.CharField(max_length=100, verbose_name='Shortcut')),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test civility',
                    'verbose_name_plural': 'Test civilities',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakePosition',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test People position',
                    'verbose_name_plural': 'Test People positions',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeSector',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                    ('is_custom', models.BooleanField(default=True)),
                    ('order', creme.creme_core.models.fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
                ],
                options={
                    'ordering': ('order',),
                    'verbose_name': 'Test sector',
                    'verbose_name_plural': 'Test sectors',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeContact',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=models.CASCADE,
                                                            )
                    ),
                    ('last_name', models.CharField(max_length=100, verbose_name='Last name')),
                    ('first_name', models.CharField(max_length=100, null=True, verbose_name='First name', blank=True)),
                    ('is_a_nerd', models.BooleanField(default=False, verbose_name='Is a Nerd')),
                    ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                    ('phone', creme.creme_core.models.fields.PhoneField(max_length=100, null=True, verbose_name='Phone number', blank=True)),
                    ('mobile', creme.creme_core.models.fields.PhoneField(max_length=100, null=True, verbose_name='Mobile', blank=True)),
                    ('email', models.EmailField(max_length=100, null=True, verbose_name='Email address', blank=True)),
                    ('url_site', models.URLField(max_length=500, null=True, verbose_name='Web Site', blank=True)),
                    ('birthday', models.DateField(null=True, verbose_name='Birthday', blank=True)),
                    ('address', models.ForeignKey(related_name='+', blank=True, editable=False, to='creme_core.FakeAddress', null=True, verbose_name='Billing address', on_delete=deletion.SET_NULL)),
                    ('civility', models.ForeignKey(on_delete=deletion.SET_NULL, verbose_name='Civility', blank=True, to='creme_core.FakeCivility', null=True)),
                    ('position', models.ForeignKey(on_delete=deletion.SET_NULL, verbose_name='Position', blank=True, to='creme_core.FakePosition', null=True)),
                    ('sector', models.ForeignKey(on_delete=deletion.SET_NULL, verbose_name='Line of business', blank=True, to='creme_core.FakeSector', null=True)),
                    ('is_user', models.ForeignKey(related_name='+', on_delete=deletion.SET_NULL, blank=True, editable=False, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Related user')),
                    ('languages', models.ManyToManyField(to='creme_core.Language', verbose_name='Spoken language(s)', blank=True)),
                    ('image', models.ForeignKey(on_delete=deletion.SET_NULL, verbose_name='Photograph', blank=True, to='creme_core.FakeImage', null=True)),
                ],
                options={
                    'ordering': ('last_name', 'first_name'),
                    'verbose_name': 'Test Contact',
                    'verbose_name_plural': 'Test Contacts',
                    'index_together': {('last_name', 'first_name', 'cremeentity_ptr')},
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeMailingList',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=models.CASCADE,
                                                            )
                    ),
                    ('name', models.CharField(max_length=80, verbose_name='Name of the mailing list')),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Mailing list',
                    'verbose_name_plural': 'Test Mailing lists',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeEmailCampaign',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=models.CASCADE,
                                                            )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name of the campaign')),
                    ('mailing_lists', models.ManyToManyField(to='creme_core.FakeMailingList', verbose_name='Related mailing lists', blank=True)),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test campaign',
                    'verbose_name_plural': 'Test campaigns',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeInvoice',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=models.CASCADE,
                                                            )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    ('number', models.CharField(max_length=100, null=True, verbose_name='Number', blank=True)),
                    ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                    ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                    ('periodicity', creme.creme_core.models.fields.DatePeriodField(null=True, verbose_name='Periodicity of the generation', blank=True)),
                    ('total_vat', creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total with VAT')),
                    ('total_no_vat', creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total without VAT')),
                ],
                options={
                    'ordering': ('name', '-expiration_date'),
                    'verbose_name': 'Test Invoice',
                    'verbose_name_plural': 'Test Invoices',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeInvoiceLine',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=models.CASCADE,
                                                            )
                    ),
                    ('item', models.CharField(max_length=100, null=True, verbose_name='Item', blank=True)),
                    ('quantity', models.DecimalField(default=Decimal('1.00'), verbose_name='Quantity', max_digits=10, decimal_places=2)),
                    ('unit_price', models.DecimalField(default=Decimal('0'), verbose_name='Unit price', max_digits=10, decimal_places=2)),
                    ('discount', models.DecimalField(default=Decimal('0'), verbose_name='Discount', max_digits=10, decimal_places=2)),
                    ('discount_unit', models.PositiveIntegerField(default=1, null=True, verbose_name='Discount Unit', blank=True, choices=[(1, 'Percent'), (2, 'Amount')])),
                    # ('invoice', models.ForeignKey(to='creme_core.FakeInvoice', on_delete=deletion.CASCADE)),
                    ('linked_invoice', models.ForeignKey(to='creme_core.FakeInvoice', on_delete=deletion.CASCADE)),
                ],
                options={
                    'ordering': ('created',),
                    'verbose_name': 'Test Invoice Line',
                    'verbose_name_plural': 'Test Invoice Lines',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeLegalForm',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test legal form',
                    'verbose_name_plural': 'Test Legal forms',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeOrganisation',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=models.CASCADE,
                                                            )
                    ),
                    ('name', models.CharField(max_length=200, verbose_name='Name')),
                    ('phone', creme.creme_core.models.fields.PhoneField(max_length=100, null=True, verbose_name='Phone number', blank=True)),
                    ('email', models.EmailField(max_length=100, null=True, verbose_name='Email address', blank=True)),
                    ('url_site', models.URLField(max_length=500, null=True, verbose_name='Web Site', blank=True)),
                    ('capital', models.PositiveIntegerField(null=True, verbose_name='Capital', blank=True)),
                    ('subject_to_vat', models.BooleanField(default=True, verbose_name='Subject to VAT')),
                    ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                    ('creation_date', models.DateField(null=True, verbose_name='Date of creation', blank=True)),
                    ('address', models.ForeignKey(related_name='+', blank=True, editable=False, to='creme_core.FakeAddress', null=True, verbose_name='Billing address', on_delete=deletion.SET_NULL)),
                    ('image', models.ForeignKey(on_delete=deletion.SET_NULL, verbose_name='Logo', blank=True, to='creme_core.FakeImage', null=True)),
                    ('legal_form', models.ForeignKey(on_delete=deletion.SET_NULL, verbose_name='Legal form', blank=True, to='creme_core.FakeLegalForm', null=True)),
                    ('sector', models.ForeignKey(on_delete=deletion.SET_NULL, verbose_name='Sector', blank=True, to='creme_core.FakeSector', null=True)),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Organisation',
                    'verbose_name_plural': 'Test Organisations',
                    'index_together': {('name', 'cremeentity_ptr')},
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeProduct',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=models.CASCADE,
                                                            )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    ('images', models.ManyToManyField(verbose_name='Images', to='creme_core.FakeImage', blank=True)),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Product',
                    'verbose_name_plural': 'Test Products',
                },
                bases=('creme_core.cremeentity',),
            ),
        ])