from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import migrations, models
from django.utils.timezone import now, zoneinfo

import creme.creme_core.models.deletion as creme_deletion
import creme.creme_core.models.fields as core_fields
from creme.creme_core.models.currency import get_default_currency_pk


class Migration(migrations.Migration):
    # replaces = [
    #     ('creme_core', '0001_initial'),
    #     ('creme_core', '0156_v2_7__fileref_description'),
    #     ('creme_core', '0157_v2_7__portable_entity_cells'),
    #     ('creme_core', '0158_v2_7__portable_ctype'),
    #     ('creme_core', '0159_v2_7__buttonmenuitem_per_role'),
    #     ('creme_core', '0160_v2_7__customentitytype'),
    #     ('creme_core', '0161_v2_7__propertytype_description'),
    #     ('creme_core', '0162_v2_7__cremeuser_uuid01'),
    #     ('creme_core', '0163_v2_7__cremeuser_uuid02'),
    #     ('creme_core', '0164_v2_7__cremeuser_uuid03'),
    #     ('creme_core', '0165_v2_7__fileref_longer_filedata'),
    #     ('creme_core', '0166_v2_7__workflow'),
    #     ('creme_core', '0167_v2_7__currency_is_default01'),
    #     ('creme_core', '0168_v2_7__currency_is_default02'),
    #     ('creme_core', '0169_v2_7__set_version'),
    # ]

    initial = True
    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='CaseSensitivity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=4)),
            ],
        ),
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                ('raw_allowed_apps', models.TextField(default='')),
                ('raw_admin_4_apps', models.TextField(default='')),
                (
                    'creatable_ctypes',
                    models.ManyToManyField(
                        related_name='roles_allowing_creation',
                        verbose_name='Creatable resources',
                        to='contenttypes.ContentType',
                    )
                ),
                (
                    'exportable_ctypes',
                    models.ManyToManyField(
                        related_name='roles_allowing_export',
                        verbose_name='Exportable resources',
                        to='contenttypes.ContentType',
                    )
                ),
                ('extra_data', models.JSONField(default=dict, editable=False)),
            ],
            options={
                'verbose_name':        'Role',
                'verbose_name_plural': 'Roles',
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='CremeUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(null=True, verbose_name='last login', blank=True)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                (
                    'username',
                    models.CharField(
                        help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.',
                        unique=True, max_length=30, verbose_name='Username',
                        validators=[UnicodeUsernameValidator()],
                        error_messages={'unique': 'A user with that username already exists.'},
                    )
                ),
                ('first_name', models.CharField(max_length=100, verbose_name='First name', blank=True)),
                ('last_name', models.CharField(max_length=100, verbose_name='Last name', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='Email address', blank=True)),
                (
                    'displayed_name',
                    models.CharField(
                        max_length=50, verbose_name='Displayed name', blank=True,
                        help_text=(
                            'If you do not fill this field, an automatic name will be used '
                            '(«John Doe» will be displayed as «John D.»).'
                        ),
                    )
                ),
                ('date_joined', models.DateTimeField(default=now, verbose_name='Date joined', editable=False)),
                ('is_active', models.BooleanField(default=True, verbose_name='Active?')),
                ('is_staff', models.BooleanField(default=False, verbose_name='Is staff?', editable=False)),
                ('is_superuser', models.BooleanField(default=False, verbose_name='Is a superuser?')),
                ('is_team', models.BooleanField(default=False, verbose_name='Is a team?')),
                (
                    'role',
                    models.ForeignKey(
                        on_delete=models.PROTECT, verbose_name='Role',
                        to='creme_core.UserRole', null=True,
                    )
                ),
                (
                    'teammates_set',
                    models.ManyToManyField(
                        related_name='teams_set', verbose_name='Teammates',
                        to=settings.AUTH_USER_MODEL,
                    )
                ),
                (
                    'theme',
                    models.CharField(
                        default=settings.THEMES[0][0], max_length=50, verbose_name='Theme',
                        choices=settings.THEMES,
                    ),
                ),
                (
                    'time_zone',
                    models.CharField(
                        default=settings.TIME_ZONE,
                        max_length=50, verbose_name='Time zone',
                        choices=[(tz, tz) for tz in zoneinfo.available_timezones()],
                    )
                ),
                (
                    'language',
                    models.CharField(
                        verbose_name='Language', max_length=10,
                        default='', blank=True,
                        choices=[
                            ('', 'Language of your browser'),
                            *settings.LANGUAGES,
                        ],
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
            name='BrickDetailviewLocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('brick_id', models.CharField(max_length=100)),
                ('order', models.PositiveIntegerField()),
                ('zone', models.PositiveSmallIntegerField()),
                (
                    'content_type',
                    core_fields.CTypeForeignKey(
                        verbose_name='Related type', to='contenttypes.ContentType', null=True,
                    )
                ),
                (
                    'role',
                    models.ForeignKey(
                        default=None, verbose_name='Related role',
                        to='creme_core.UserRole', null=True, on_delete=models.CASCADE
                    )
                ),
                (
                    'superuser',
                    models.BooleanField(
                        default=False, verbose_name='related to superusers', editable=False,
                    )
                ),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='BrickMypageLocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('brick_id', models.CharField(max_length=100)),
                ('order', models.PositiveIntegerField()),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='BrickHomeLocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('brick_id', models.CharField(max_length=100)),
                (
                    'role',
                    models.ForeignKey(
                        default=None, null=True, on_delete=models.CASCADE, to='creme_core.UserRole', verbose_name='Related role',
                    )
                ),
                ('superuser', models.BooleanField(default=False, editable=False, verbose_name='related to superusers')),
                ('order', models.PositiveIntegerField()),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='BrickState',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('brick_id', models.CharField(max_length=100, verbose_name='Block ID')),
                ('is_open', models.BooleanField(default=True)),
                ('show_empty_fields', models.BooleanField(default=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
                ('json_extra_data', models.JSONField(default=dict, editable=False)),
            ],
            options={
                'unique_together': {('user', 'brick_id')},
            }
        ),
        migrations.CreateModel(
            name='ButtonMenuItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                (
                    'role',
                    models.ForeignKey(
                        to='creme_core.userrole', verbose_name='Related role',
                        default=None, null=True, on_delete=models.CASCADE,
                    ),
                ),
                (
                    'superuser',
                    models.BooleanField(
                        default=False, editable=False, verbose_name='related to superusers',
                    ),
                ),
                ('button_id', models.CharField(max_length=100, verbose_name='Button ID')),
                ('order', models.PositiveIntegerField(verbose_name='Priority')),
                (
                    'content_type',
                    core_fields.CTypeForeignKey(
                        verbose_name='Related type', to='contenttypes.ContentType', null=True,
                    )
                ),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Button to display',
                'verbose_name_plural': 'Buttons to display',
            },
        ),
        migrations.CreateModel(
            name='Sandbox',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('type_id', models.CharField(editable=False, max_length=48, verbose_name='Type of sandbox')),
                (
                    'role',
                    models.ForeignKey(
                        default=None, editable=False, null=True, on_delete=models.CASCADE,
                        to='creme_core.UserRole', verbose_name='Related role',
                    )
                ),
                (
                    'user',
                    models.ForeignKey(
                        default=None, editable=False, null=True, on_delete=models.CASCADE,
                        to=settings.AUTH_USER_MODEL, verbose_name='Related user',
                    )
                ),
            ],
        ),
        migrations.CreateModel(
            name='CremeEntity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid4, unique=True, editable=False)),
                ('created', core_fields.CreationDateTimeField(default=now, verbose_name='Creation date', editable=False, blank=True)),
                ('modified', core_fields.ModificationDateTimeField(default=now, verbose_name='Last modification', editable=False, blank=True)),
                ('header_filter_search_field', models.CharField(max_length=200, editable=False)),
                ('is_deleted', models.BooleanField(default=False, editable=False)),
                ('entity_type', core_fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType')),
                ('user', core_fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL)),
                ('sandbox', models.ForeignKey(editable=False, null=True, on_delete=models.PROTECT, to='creme_core.Sandbox')),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('description', models.TextField(blank=True, verbose_name='Description')),
            ],
            options={
                'verbose_name': 'Entity',
                'verbose_name_plural': 'Entities',
                'ordering': ('header_filter_search_field',),
                'indexes': [
                    models.Index(
                        fields=['entity_type', 'is_deleted'],
                        name='core__entity__basic_count',
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name='CremePropertyType',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                (
                    'app_label',
                    models.CharField(
                        verbose_name='Created by the app', max_length=40, default='',
                        editable=False,
                    )
                ),
                (
                    'text',
                    models.CharField(
                        verbose_name='Text',
                        unique=True, max_length=200,
                        help_text="For example: 'is pretty'",
                    )
                ),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('is_custom', models.BooleanField(default=False, editable=False)),
                (
                    'is_copiable',
                    models.BooleanField(
                        verbose_name='Is copiable', default=True,
                        help_text='Are the properties with this type copied when an entity is cloned?',
                    )
                ),
                ('enabled', models.BooleanField(default=True, editable=False, verbose_name='Enabled?')),
                (
                    'subject_ctypes',
                    models.ManyToManyField(
                        verbose_name='Related to types of entities',
                        to='contenttypes.ContentType', blank=True,
                        related_name='subject_ctypes_creme_property_set',
                        help_text='No selected type means that all types are accepted',
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
                (
                    'creme_entity',
                    models.ForeignKey(
                        verbose_name='Entity',
                        related_name='properties', to='creme_core.CremeEntity', on_delete=models.CASCADE,
                    )
                ),
                (
                    'type',
                    models.ForeignKey(
                        verbose_name='Type of property',
                        to='creme_core.CremePropertyType', on_delete=models.PROTECT,
                    )
                ),
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
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Currency')),
                ('local_symbol', models.CharField(max_length=100, verbose_name='Local symbol')),
                ('international_symbol', models.CharField(max_length=100, verbose_name='International symbol')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_default', models.BooleanField(default=False, verbose_name='Is default?')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Currency',
                'verbose_name_plural': 'Currencies',
            },
        ),
        migrations.CreateModel(
            name='CustomBrickConfigItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('json_cells', models.JSONField(default=list, editable=False)),
                (
                    'content_type',
                    core_fields.CTypeForeignKey(
                        editable=False, to='contenttypes.ContentType', verbose_name='Related type',
                    )
                ),
            ],
        ),
        migrations.CreateModel(
            name='CustomField',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid4, unique=True, editable=False)),
                ('name', models.CharField(max_length=100, verbose_name='Field name')),
                ('field_type', models.PositiveSmallIntegerField(verbose_name='Field type')),
                (
                    'content_type',
                    core_fields.CTypeForeignKey(
                        verbose_name='Related type', to='contenttypes.ContentType',
                    )
                ),
                (
                    'is_required',
                    models.BooleanField(
                        default=False, verbose_name='Is required?',
                        help_text=(
                            'A required custom-field must be filled when a new entity is created; '
                            'existing entities are not immediately impacted.'
                        ),
                    )
                ),
                (
                    'is_deleted',
                    models.BooleanField(default=False, editable=False, verbose_name='Is deleted?')
                ),
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
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=models.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldDateTime',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.DateTimeField()),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=models.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldEnumValue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('value', models.CharField(max_length=100)),
                (
                    'custom_field',
                    models.ForeignKey(
                        related_name='customfieldenumvalue_set', to='creme_core.CustomField', on_delete=models.CASCADE,
                    )
                ),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldEnum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=models.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=models.CASCADE)),
                ('value', models.ForeignKey(to='creme_core.CustomFieldEnumValue', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldFloat',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.DecimalField(max_digits=12, decimal_places=2)),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=models.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldInteger',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.IntegerField()),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=models.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldMultiEnum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=models.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=models.CASCADE)),
                ('value', models.ManyToManyField(to='creme_core.CustomFieldEnumValue')),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldString',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=100)),
                ('custom_field', models.ForeignKey(to='creme_core.CustomField', on_delete=models.CASCADE)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldURL',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', core_fields.CremeURLField(max_length=200)),
                ('custom_field', models.ForeignKey(on_delete=models.CASCADE, to='creme_core.CustomField')),
                ('entity', models.ForeignKey(on_delete=models.CASCADE, to='creme_core.CremeEntity')),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldText',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField()),
                ('custom_field', models.ForeignKey(on_delete=models.CASCADE, to='creme_core.CustomField')),
                ('entity', models.ForeignKey(on_delete=models.CASCADE, to='creme_core.CremeEntity')),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldDate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.DateField()),
                ('custom_field', models.ForeignKey(on_delete=models.CASCADE, to='creme_core.CustomField')),
                ('entity', models.ForeignKey(on_delete=models.CASCADE, to='creme_core.CremeEntity')),
            ],
        ),
        migrations.CreateModel(
            name='CustomEntityType',
            fields=[
                (
                    'id',
                    models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
                ),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
                ('plural_name', models.CharField(max_length=50, verbose_name='Name (plural)')),
                ('enabled', models.BooleanField(default=False, editable=False)),
                ('deleted', models.BooleanField(default=False, editable=False)),
            ],
            options={
                'verbose_name': 'Custom entity',
                'verbose_name_plural': 'Custom entities',
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='CustomFormConfigItem',
            fields=[
                (
                    'id',
                    models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
                ),
                (
                    'descriptor_id',
                    models.CharField(verbose_name='Type of form', editable=False, max_length=100)
                ),
                ('json_groups', models.JSONField(default=list, editable=False)),
                (
                    'role',
                    models.ForeignKey(
                        default=None, blank=True, null=True, on_delete=models.CASCADE,
                        to='creme_core.userrole', verbose_name='Related role',
                    )
                ),
                (
                    'superuser',
                    models.BooleanField(
                        default=False, editable=False, verbose_name='related to superusers',
                    )
                ),
            ],
            options={
                'verbose_name': 'Custom form',
                'verbose_name_plural': 'Custom forms',
                'unique_together': {('descriptor_id', 'role')},
            },
        ),
        migrations.CreateModel(
            name='EntityFilter',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                (
                    'filter_type',
                    models.CharField(
                        default='creme_core-regular', editable=False, max_length=36,
                        choices=[
                            ('creme_core-credentials', 'Credentials filter'),
                            ('creme_core-regular', 'Regular filter (usable in list-view)'),
                        ],
                    )
                ),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                (
                    'is_private',
                    models.BooleanField(
                        default=False, verbose_name='Is private?',
                        help_text='A private filter can only be used by its owner (or the teammates if the owner is a team)',
                    ),
                ),
                (
                    'use_or',
                    models.BooleanField(
                        default=False, verbose_name='The entity is accepted if',
                        choices=[
                            (False, 'All the conditions are met'),
                            (True,  'Any condition is met'),
                        ],
                    )
                ),
                ('entity_type', core_fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType')),
                (
                    'user',
                    core_fields.CremeUserForeignKey(
                        verbose_name='Owner user', to=settings.AUTH_USER_MODEL,
                        null=True, blank=True,
                        help_text='If you assign an owner, only the owner can edit or delete the filter'
                    )
                ),
                ('extra_data', models.JSONField(default=dict, editable=False)),
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
                ('value', models.JSONField(default=dict)),
                (
                    'filter',
                    models.ForeignKey(related_name='conditions', to='creme_core.EntityFilter', on_delete=models.CASCADE)
                ),
            ],
        ),
        migrations.CreateModel(
            name='FileRef',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filedata', models.FileField(verbose_name='Path', max_length=500, upload_to='')),
                ('basename', models.CharField(max_length=200)),
                ('created', models.DateTimeField(verbose_name='Created', auto_now_add=True)),
                ('temporary', models.BooleanField(default=True, verbose_name='To be deleted by the job?')),
                ('user', core_fields.CremeUserForeignKey(null=True, to=settings.AUTH_USER_MODEL, verbose_name='Owner user')),
                ('description', models.TextField(verbose_name='Description')),
                ('extra_data', models.JSONField(default=dict, editable=False)),
            ],
        ),
        migrations.CreateModel(
            name='HeaderFilter',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name of the view')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                (
                    'is_private',
                    models.BooleanField(
                        default=False, verbose_name='Is private?',
                        help_text='A private view of list can only be used by its owner (or the teammates if the owner is a team)',
                    )
                ),
                ('json_cells', models.JSONField(default=list, editable=False)),
                ('entity_type', core_fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType')),
                (
                    'user',
                    core_fields.CremeUserForeignKey(
                        verbose_name='Owner user', blank=True, to=settings.AUTH_USER_MODEL, null=True,
                        help_text='If you assign an owner, only the owner can edit or delete the view',
                    )
                ),
                ('extra_data', models.JSONField(default=dict, editable=False)),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='HistoryLine',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                (
                    'entity',
                    models.ForeignKey(on_delete=models.SET_NULL, to='creme_core.CremeEntity', null=True)
                ),
                ('entity_ctype', core_fields.CTypeForeignKey(to='contenttypes.ContentType')),
                ('entity_owner', core_fields.CremeUserForeignKey(to=settings.AUTH_USER_MODEL)),
                ('username', models.CharField(max_length=30)),
                (
                    'date',
                    core_fields.CreationDateTimeField(
                        default=now, verbose_name='Date', editable=False, blank=True,
                    )
                ),
                ('type', models.PositiveSmallIntegerField(verbose_name='Type')),
                ('value', models.TextField(null=True)),
                (
                    'by_wf_engine',
                    models.BooleanField(default=False, verbose_name='Action of Workflow engine'),
                ),
            ],
            options={
                'verbose_name': 'Line of history',
                'verbose_name_plural': 'Lines of history',
                'indexes': [
                    models.Index(fields=['entity_id', '-id'], name='hline__entity_detailview'),
                ],
                'ordering': ('id',)
            },
        ),
        migrations.CreateModel(
            name='InstanceBrickConfigItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('brick_class_id', models.CharField(editable=False, max_length=300, verbose_name='Block class ID')),
                ('json_extra_data', models.JSONField(default=dict, editable=False)),
                (
                    'entity',
                    models.ForeignKey(
                        verbose_name='Block related entity', to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        editable=False,
                    )
                ),
            ],
            options={
                'ordering': ('id',),
            },
        ),
        migrations.CreateModel(
            name='Imprint',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True)),
                (
                    'entity_ctype',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.contenttype', related_name='+',
                        editable=False, on_delete=models.CASCADE,
                    )
                ),
                (
                    'entity',
                    models.ForeignKey(
                        on_delete=models.CASCADE, related_name='imprints', to='creme_core.CremeEntity',
                    )
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=models.CASCADE, related_name='imprints', to=settings.AUTH_USER_MODEL,
                    )
                ),
            ],
        ),
        migrations.CreateModel(
            name='MenuConfigItem',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID',
                    )
                ),
                ('entry_id', models.CharField(editable=False, max_length=100)),
                (
                    'role',
                    models.ForeignKey(
                        to='creme_core.userrole',
                        default=None, null=True,
                        on_delete=models.CASCADE, editable=False,
                    )
                ),
                (
                    'superuser',
                    models.BooleanField(
                        default=False, editable=False, verbose_name='related to superusers',
                    )
                ),
                ('order', models.PositiveIntegerField(editable=False)),
                (
                    'parent',
                    models.ForeignKey(
                        to='creme_core.menuconfigitem', null=True, editable=False,
                        on_delete=models.CASCADE, related_name='children',
                    )
                ),
                ('entry_data', models.JSONField(default=dict, editable=False)),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
            ],
            options={
                'verbose_name': 'Language',
                'verbose_name_plural': 'Languages',
                'ordering': ('name',)
            },
        ),
        migrations.CreateModel(
            name='Mutex',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='NotificationChannel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=48, verbose_name='Name')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('type_id', models.CharField(editable=False, max_length=48)),
                (
                    'required',
                    models.BooleanField(
                        verbose_name='Is required?', default=True,
                        help_text=(
                            'When a channel is required, users have to chose at least one output '
                            '(in-app, email) in their personal configuration.'
                        ),
                    )
                ),
                ('deleted', models.DateTimeField(editable=False, null=True)),
                (
                    'default_outputs',
                    models.JSONField(verbose_name='Default outputs', default=list, editable=False)
                ),
            ],
            options={'ordering': ('id',)},
        ),
        migrations.CreateModel(
            name='NotificationChannelConfigItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('outputs', models.JSONField(default=list, editable=False)),
                (
                    'channel',
                    models.ForeignKey(
                        editable=False, on_delete=models.PROTECT,
                        to='creme_core.notificationchannel',
                    )
                ),
                (
                    'user',
                    models.ForeignKey(
                        to=settings.AUTH_USER_MODEL,
                        editable=False, on_delete=models.CASCADE,
                    )
                ),
            ],
            options={
                'unique_together': {('channel', 'user')},
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                (
                    'channel',
                    models.ForeignKey(
                        verbose_name='Channel', to='creme_core.notificationchannel',
                        on_delete=models.PROTECT,
                        related_name='notifications',
                    )
                ),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
                ('created', models.DateTimeField(verbose_name='Creation date', auto_now_add=True)),
                ('output', models.CharField(max_length=32)),
                ('content_id', models.CharField(max_length=48)),
                ('content_data', models.JSONField(default=dict)),
                (
                    'level',
                    models.PositiveSmallIntegerField(
                        verbose_name='Level',
                        choices=[(1, 'Low'), (2, 'Normal'), (3, 'High')],
                        default=2,
                    )
                ),
                ('discarded', models.DateTimeField(null=True)),
                ('extra_data', models.JSONField(default=dict)),
            ],
            options={
                'ordering': ('-id',),
            },
        ),
        migrations.CreateModel(
            name='RelationType',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, primary_key=True)),
                ('is_internal', models.BooleanField(default=False)),
                ('is_custom', models.BooleanField(default=False)),
                ('is_copiable', models.BooleanField(default=True)),
                ('predicate', models.CharField(max_length=100, verbose_name='Predicate')),
                ('enabled', models.BooleanField(default=True, editable=False, verbose_name='Enabled?')),
                (
                    'subject_ctypes',
                    models.ManyToManyField(
                        related_name='relationtype_subjects_set', to='contenttypes.ContentType', blank=True,
                    )
                ),
                (
                    'subject_properties',
                    models.ManyToManyField(
                        related_name='relationtype_subjects_set', to='creme_core.CremePropertyType', blank=True,
                    )
                ),
                (
                    'subject_forbidden_properties',
                    models.ManyToManyField(
                        to='creme_core.CremePropertyType',
                        related_name='relationtype_forbidden_set',
                        blank=True,
                    )
                ),
                ('symmetric_type', models.ForeignKey(blank=True, to='creme_core.RelationType', null=True, on_delete=models.CASCADE)),
                ('minimal_display', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Type of relationship',
                'verbose_name_plural': 'Types of relationship',
                'ordering': ('predicate',)
            },
        ),
        migrations.CreateModel(
            name='Relation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', core_fields.CreationDateTimeField(default=now, verbose_name='Creation date', editable=False, blank=True)),
                (
                    'object_ctype',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.contenttype',
                        on_delete=models.CASCADE, related_name='+',
                        editable=False,
                    )
                ),
                (
                    'object_entity',
                    models.ForeignKey(
                        related_name='relations_where_is_object', on_delete=models.PROTECT, to='creme_core.CremeEntity',
                    ),
                ),
                (
                    'subject_entity',
                    models.ForeignKey(
                        related_name='relations', on_delete=models.PROTECT, to='creme_core.CremeEntity',
                    ),
                ),
                ('symmetric_relation', models.ForeignKey(to='creme_core.Relation', null=True, on_delete=models.CASCADE)),
                ('type', models.ForeignKey(to='creme_core.RelationType', on_delete=models.PROTECT)),
                ('user', core_fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('type', 'subject_entity', 'object_entity')},
                'verbose_name': 'Relationship',
                'verbose_name_plural': 'Relationships',
            },
        ),
        migrations.CreateModel(
            name='RelationBrickItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(unique=True, editable=False, default=uuid4)),
                (
                    'relation_type',
                    models.OneToOneField(
                        verbose_name='Related type of relationship', to='creme_core.RelationType', on_delete=models.CASCADE,
                    )
                ),
                ('json_cells_map', models.JSONField(default=dict, editable=False)),
            ],
        ),
        migrations.CreateModel(
            name='SearchConfigItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('disabled', models.BooleanField(default=False, verbose_name='Disabled?')),
                (
                    'content_type',
                    core_fields.EntityCTypeForeignKey(verbose_name='Related resource', to='contenttypes.ContentType')
                ),
                (
                    'role',
                    models.ForeignKey(
                        default=None, verbose_name='Related role', to='creme_core.UserRole',
                        null=True, on_delete=models.CASCADE,
                    )
                ),
                ('superuser', models.BooleanField(default=False, verbose_name='related to superusers', editable=False)),
                ('json_cells', models.JSONField(default=list, editable=False)),
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
                (
                    'object_ctype',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.contenttype', related_name='+',
                        editable=False, on_delete=models.CASCADE,
                    )
                ),
                ('object_entity', models.ForeignKey(to='creme_core.CremeEntity', on_delete=models.CASCADE)),
                ('relation_type', models.ForeignKey(to='creme_core.RelationType', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('predicate',),
                'verbose_name': 'Semi-fixed type of relationship',
                'verbose_name_plural': 'Semi-fixed types of relationship',
                'unique_together': {('relation_type', 'object_entity')},
            },
        ),
        migrations.CreateModel(
            name='SetCredentials',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.PositiveSmallIntegerField()),
                (
                    'set_type',
                    models.PositiveIntegerField(
                        choices=[
                            (1, 'All entities'),
                            (2, "User's own entities"),
                            (3, 'Filtered entities'),
                        ],
                        default=1,
                        help_text=(
                            'The choice «Filtered entities» allows to configure '
                            'credentials based on values of fields or relationships for example.'
                        ),
                        verbose_name='Type of entities set',
                    )
                ),
                (
                    'ctype',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.ContentType',
                        blank=True, null=True, on_delete=models.CASCADE,
                        verbose_name='Apply to a specific type',
                    )
                ),
                ('role', models.ForeignKey(related_name='credentials', to='creme_core.UserRole', on_delete=models.CASCADE, editable=False)),
                (
                    'forbidden',
                    models.BooleanField(
                        choices=[
                            (False, 'The users are allowed to perform the selected actions'),
                            (True, 'The users are NOT allowed to perform the selected actions'),
                        ],
                        default=False,
                        help_text=(
                            'Notice that actions which are forbidden & allowed '
                            'at the same time are considered as forbidden when final permissions are computed.'
                        ),
                        verbose_name='Allow or forbid?',
                    )
                ),
                (
                    'efilter',
                    models.ForeignKey(
                        editable=False, null=True, on_delete=models.PROTECT, to='creme_core.EntityFilter',
                    )
                ),
            ],
        ),
        migrations.CreateModel(
            name='SettingValue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key_id', models.CharField(max_length=100)),
                ('json_value', models.JSONField(editable=False, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='HistoryConfigItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('relation_type', models.OneToOneField(to='creme_core.RelationType', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='Vat',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                (
                    'value',
                    core_fields.DecimalPercentField(
                        verbose_name='VAT', decimal_places=2, max_digits=4, default=Decimal('20.0'),
                    )
                ),
                ('is_default', models.BooleanField(default=False, verbose_name='Is default?')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                (
                    'content_type',
                    core_fields.CTypeOneToOneField(
                        primary_key=True, serialize=False, editable=False,
                        to='contenttypes.ContentType',
                    )
                ),
                ('raw_descriptions', models.JSONField(default=list, editable=False)),
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
                ('periodicity', core_fields.DatePeriodField(null=True, verbose_name='Periodicity')),
                ('last_run', models.DateTimeField(verbose_name='Last run', null=True, editable=False)),
                ('ack_errors', models.PositiveIntegerField(default=0, editable=False)),
                (
                    'status',
                    models.PositiveSmallIntegerField(
                        default=1, verbose_name='Status', editable=False,
                        choices=[
                            (1, 'Waiting'),
                            (10, 'Error'),
                            (20, 'Completed successfully'),
                        ],
                    )
                 ),
                ('error', models.TextField(verbose_name='Error', null=True, editable=False)),
                ('data', models.JSONField(editable=False, null=True)),
                (
                    'user',
                    core_fields.CremeUserForeignKey(
                        editable=False, to=settings.AUTH_USER_MODEL, null=True, verbose_name='User',
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
                ('messages', models.JSONField(null=True)),
                ('job', models.ForeignKey(to='creme_core.Job', on_delete=models.CASCADE)),
            ],
            options={},
        ),
        migrations.CreateModel(
            name='EntityJobResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('messages', models.JSONField(null=True)),
                (
                    'entity_ctype',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.contenttype', related_name='+',
                        null=True, editable=False, on_delete=models.CASCADE,
                    )
                ),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', null=True, on_delete=models.CASCADE)),
                ('job', models.ForeignKey(to='creme_core.Job', on_delete=models.CASCADE)),
            ],
            options={},
        ),
        migrations.CreateModel(
            name='MassImportJobResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('messages', models.JSONField(null=True)),
                ('line', models.JSONField(default=list)),
                ('updated', models.BooleanField(default=False)),
                (
                    'entity_ctype',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.contenttype', related_name='+',
                        editable=False, null=True, on_delete=models.CASCADE,
                    )
                ),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', null=True, on_delete=models.CASCADE)),
                ('job', models.ForeignKey(to='creme_core.Job', on_delete=models.CASCADE)),
            ],
            options={},
        ),
        migrations.CreateModel(
            name='DeletionCommand',
            fields=[
                (
                    'content_type',
                    core_fields.CTypeOneToOneField(
                        editable=False, on_delete=models.CASCADE,
                        primary_key=True, serialize=False,
                        to='contenttypes.ContentType',
                    )
                ),
                ('job', models.ForeignKey(on_delete=models.CASCADE, to='creme_core.Job', editable=False)),
                ('pk_to_delete', models.TextField(editable=False)),
                ('deleted_repr', models.TextField(editable=False)),
                ('json_replacers', models.JSONField(default=list, editable=False)),
                ('total_count', models.PositiveIntegerField(default=0, editable=False)),
                ('updated_count', models.PositiveIntegerField(default=0, editable=False)),
            ],
        ),
        migrations.CreateModel(
            name='TrashCleaningCommand',
            fields=[
                (
                    'user',
                    models.OneToOneField(
                        editable=False, on_delete=models.CASCADE, primary_key=True,
                        serialize=False, to=settings.AUTH_USER_MODEL,
                    )
                ),
                ('job', models.ForeignKey(editable=False, on_delete=models.CASCADE, to='creme_core.Job')),
                ('deleted_count', models.PositiveIntegerField(default=0, editable=False)),
            ],
        ),
        migrations.CreateModel(
            name='Workflow',
            fields=[
                (
                    'id',
                    models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
                ),
                ('uuid', models.UUIDField(default=uuid4, unique=True, editable=False)),
                ('title', models.CharField(verbose_name='Title', max_length=100)),
                (
                    'content_type',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.contenttype', verbose_name='Related resource',
                        on_delete=models.CASCADE,
                    )
                ),
                ('json_trigger', models.JSONField(default=dict)),
                ('json_conditions', models.JSONField(default=list)),
                ('json_actions', models.JSONField(default=list)),
                (
                    'enabled',
                    models.BooleanField(default=True, editable=False)
                ),
                (
                    'is_custom',
                    models.BooleanField(default=True, editable=False)
                ),
            ],
            options={
                'verbose_name': 'Workflow',
                'verbose_name_plural': 'Workflows',
            },
        ),
        migrations.CreateModel(
            name='WorldSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('menu_icon', models.ImageField(upload_to='creme_core', verbose_name='Menu icon', blank=True)),
                (
                    'password_change_enabled',
                    models.BooleanField(
                        verbose_name='Allow all users to change their own password?',
                        default=True,
                    )
                ),
                (
                    'password_reset_enabled',
                    models.BooleanField(
                        verbose_name='Enable the «Lost password» feature?',
                        default=True,
                        help_text=(
                            'This feature allows users to reset their password if they forgot it. '
                            'The login page proposes to receive an email to start the reset process.'
                        ),
                    )
                ),
                (
                    'user_name_change_enabled',
                    models.BooleanField(
                        default=True,
                        verbose_name='Can users change their own displayed name?',
                    )
                ),
            ],
            options={
                'swappable': 'CREME_CORE_WSETTINGS_MODEL',
            },
        ),
    ]

    if settings.TESTS_ON:
        from creme.creme_core.tests.fake_models import get_sentinel_priority

        operations.extend([
            migrations.CreateModel(
                name='FakeActivityType',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                    ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                    ('extra_data', models.JSONField(default=dict, editable=False)),
                    ('is_custom', models.BooleanField(default=True, editable=False)),
                    ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('title', models.CharField(unique=True, max_length=100, verbose_name='Title')),
                    ('minutes', models.TextField(verbose_name='Minutes', blank=True)),
                    ('place', models.CharField(max_length=100, verbose_name='Place', blank=True)),
                    ('start', models.DateTimeField(null=True, verbose_name='Start', blank=True)),
                    ('end', models.DateTimeField(null=True, verbose_name='End', blank=True)),
                    (
                        'type',
                        models.ForeignKey(
                            verbose_name='Activity type', to='creme_core.FakeActivityType', on_delete=models.PROTECT,
                        )
                    ),
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
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                    (
                        'category',
                        models.ForeignKey(
                            on_delete=models.SET_NULL, verbose_name='Category',
                            blank=True, to='creme_core.FakeFolderCategory', null=True,
                        )
                    ),
                    (
                        'parent',
                        models.ForeignKey(
                            related_name='children', verbose_name='Parent folder',
                            blank=True, to='creme_core.FakeFolder', null=True, on_delete=models.CASCADE,
                        )
                    ),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test Folder',
                    'verbose_name_plural': 'Test Folders',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeDocumentCategory',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(unique=True, max_length=100, verbose_name='Category name')),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Document category',
                    'verbose_name_plural': 'Test Document categories',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeDocument',
                fields=[
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                    ('filedata', models.FileField(upload_to=b'creme_core-tests', max_length=100, verbose_name='File')),
                    (
                        'linked_folder',
                        models.ForeignKey(
                            on_delete=models.PROTECT, verbose_name='Folder', to='creme_core.FakeFolder',
                        ),
                    ),
                    (
                        'categories',
                        models.ManyToManyField(
                            verbose_name='Categories', to='creme_core.FakeDocumentCategory', blank=True,
                        )
                    ),
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
                    (
                        'filedata',
                        models.FileField(
                            verbose_name='File', null=True, blank=True,
                            upload_to=b'creme_core-tests',
                            max_length=100,
                        )
                    ),
                ],
                options={
                    'verbose_name': 'Test File component',
                    'verbose_name_plural': 'Test File components',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeFileBag',
                fields=[
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('name', models.CharField(max_length=100, null=True, verbose_name='Name', blank=True)),
                    (
                        'file1',
                        models.ForeignKey(
                            on_delete=models.PROTECT, verbose_name='First file',
                            to='creme_core.FakeFileComponent',
                            null=True, blank=True,
                        )
                    ),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test File bag',
                    'verbose_name_plural': 'Test File bags',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeImageCategory',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    ('extra_data', models.JSONField(default=dict, editable=False)),
                    ('is_custom', models.BooleanField(default=True, editable=False)),
                    ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name', blank=True)),
                    (
                        'filedata',
                        models.FileField(
                            verbose_name='File', editable=False,
                            upload_to=b'creme_core-tests',
                            max_length=100,
                        )
                    ),
                    (
                        'categories',
                        models.ManyToManyField(
                            related_name='+', verbose_name='Categories',
                            to='creme_core.FakeImageCategory', blank=True,
                        )
                    ),
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
                    ('value', models.TextField(verbose_name='Address', blank=True)),
                    ('zipcode', models.CharField(max_length=100, verbose_name='Zip code', blank=True)),
                    ('city', models.CharField(max_length=100, verbose_name='City', blank=True)),
                    ('department', models.CharField(max_length=100, verbose_name='Department', blank=True)),
                    ('country', models.CharField(max_length=40, verbose_name='Country', blank=True)),
                    ('entity', models.ForeignKey(related_name='+', editable=False, to='creme_core.CremeEntity', on_delete=models.CASCADE)),
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
                    ('extra_data', models.JSONField(default=dict, editable=False)),
                    ('is_custom', models.BooleanField(default=True, editable=False)),
                    ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test civility',
                    'verbose_name_plural': 'Test civilities',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeCountry',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    ('extra_data', models.JSONField(default=dict, editable=False)),
                    ('is_custom', models.BooleanField(default=True, editable=False)),
                    ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test country',
                    'verbose_name_plural': 'Test countries',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakePosition',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                    ('extra_data', models.JSONField(default=dict, editable=False)),
                    ('is_custom', models.BooleanField(default=True, editable=False)),
                    ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                    ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                    ('extra_data', models.JSONField(default=dict, editable=False)),
                    ('is_custom', models.BooleanField(default=True, editable=False)),
                    ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('last_name', models.CharField(max_length=100, verbose_name='Last name')),
                    ('first_name', models.CharField(max_length=100, verbose_name='First name', blank=True)),
                    ('is_a_nerd', models.BooleanField(default=False, verbose_name='Is a Nerd')),
                    ('loves_comics', models.BooleanField(default=None, null=True, blank=True, verbose_name='Loves comics')),
                    ('phone', core_fields.PhoneField(max_length=100, null=True, verbose_name='Phone', blank=True)),
                    ('mobile', core_fields.PhoneField(max_length=100, verbose_name='Mobile', blank=True)),
                    ('email', models.EmailField(max_length=100, verbose_name='Email address', blank=True)),
                    ('url_site', core_fields.CremeURLField(max_length=500, verbose_name='Web Site', blank=True)),
                    ('birthday', models.DateField(null=True, verbose_name='Birthday', blank=True)),
                    (
                        'address',
                        models.ForeignKey(
                            related_name='+', blank=True, editable=False, to='creme_core.FakeAddress',
                            null=True, verbose_name='Billing address', on_delete=models.SET_NULL,
                        )
                    ),
                    (
                        'civility',
                        models.ForeignKey(
                            on_delete=creme_deletion.CREME_REPLACE_NULL, verbose_name='Civility',
                            blank=True, to='creme_core.FakeCivility', null=True,
                        )
                    ),
                    (
                        'position',
                        models.ForeignKey(
                            on_delete=models.SET_NULL, verbose_name='Position',
                            blank=True, to='creme_core.FakePosition', null=True,
                        )
                    ),
                    (
                        'sector',
                        models.ForeignKey(
                            on_delete=creme_deletion.CREME_REPLACE_NULL,
                            verbose_name='Line of business', blank=True, to='creme_core.FakeSector', null=True,
                        )
                    ),
                    (
                        'is_user',
                        models.ForeignKey(
                            related_name='+', on_delete=models.SET_NULL,
                            blank=True, editable=False, to=settings.AUTH_USER_MODEL,
                            null=True, verbose_name='Related user',
                            help_text='The contact corresponds to a user of Creme',
                        )
                    ),
                    (
                        'languages',
                        models.ManyToManyField(
                            to='creme_core.Language', verbose_name='Spoken language(s)', blank=True,
                        )
                    ),
                    (
                        'preferred_countries',
                        models.ManyToManyField(
                            to='creme_core.FakeCountry', verbose_name='Preferred countries', blank=True,
                        )
                    ),
                    (
                        'image',
                        models.ForeignKey(
                            on_delete=models.SET_NULL, verbose_name='Photograph',
                            blank=True, to='creme_core.FakeImage', null=True,
                        )
                    ),
                ],
                options={
                    'ordering': ('last_name', 'first_name'),
                    'verbose_name': 'Test Contact',
                    'verbose_name_plural': 'Test Contacts',
                    'indexes': [
                        models.Index(
                            fields=['last_name', 'first_name', 'cremeentity_ptr'],
                            name='core__fakecontact__default_lv',
                        ),
                    ],
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeMailingList',
                fields=[
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
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
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name of the campaign')),
                    (
                        'type',
                        models.PositiveIntegerField(
                            verbose_name='Type',
                            choices=[(1, 'Internal'), (2, 'External')],
                            null=True, default=None,
                        )
                    ),
                    (
                        'status',
                        models.PositiveIntegerField(
                            verbose_name='Status',
                            choices=[(1, 'Waiting'), (2, 'Sent'), (3, 'Sent (errors)')],
                            default=1,
                        )
                    ),
                    (
                        'mailing_lists',
                        models.ManyToManyField(
                            to='creme_core.FakeMailingList', verbose_name='Related mailing lists', blank=True,
                        )
                    ),
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
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    ('number', models.CharField(max_length=100, verbose_name='Number', blank=True)),
                    ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                    ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                    (
                        'currency',
                        models.ForeignKey(
                            verbose_name='Currency', to='creme_core.Currency',
                            related_name='+', on_delete=models.PROTECT,
                            default=get_default_currency_pk,
                        )
                    ),
                    ('periodicity', core_fields.DatePeriodField(null=True, verbose_name='Periodicity of the generation', blank=True)),
                    (
                        'total_vat',
                        core_fields.MoneyField(
                            decimal_places=2, default=0, editable=False, max_digits=14,
                            null=True, verbose_name='Total with VAT',
                        )
                    ),
                    (
                        'total_no_vat',
                        core_fields.MoneyField(
                            decimal_places=2, default=0, editable=False, max_digits=14,
                            null=True, verbose_name='Total without VAT',
                        )
                    ),
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
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('item', models.CharField(max_length=100, null=True, verbose_name='Item', blank=True)),
                    ('quantity', models.DecimalField(default=Decimal('1.00'), verbose_name='Quantity', max_digits=10, decimal_places=2)),
                    ('unit_price', models.DecimalField(default=Decimal('0'), verbose_name='Unit price', max_digits=10, decimal_places=2)),
                    ('discount', models.DecimalField(default=Decimal('0'), verbose_name='Discount', max_digits=10, decimal_places=2)),
                    ('vat_value', models.ForeignKey(to='creme_core.Vat', blank=True, null=True, on_delete=models.PROTECT)),
                    (
                        'discount_unit',
                        models.PositiveIntegerField(
                            default=1, null=True, verbose_name='Discount Unit',
                            blank=True, choices=[(1, 'Percent'), (2, 'Amount')],
                        )
                    ),
                    ('linked_invoice', models.ForeignKey(to='creme_core.FakeInvoice', on_delete=models.CASCADE)),
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
                    ('extra_data', models.JSONField(default=dict, editable=False)),
                    ('is_custom', models.BooleanField(default=True, editable=False)),
                    ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test Legal form',
                    'verbose_name_plural': 'Test Legal forms',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeOrganisation',
                fields=[
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('name', models.CharField(max_length=200, verbose_name='Name')),
                    ('phone', core_fields.PhoneField(max_length=100, verbose_name='Phone', blank=True)),
                    ('email', models.EmailField(max_length=100, verbose_name='Email address', blank=True)),
                    ('url_site', models.URLField(max_length=500, null=True, verbose_name='Web Site', blank=True)),
                    ('capital', models.PositiveIntegerField(null=True, verbose_name='Capital', blank=True)),
                    ('subject_to_vat', models.BooleanField(default=True, verbose_name='Subject to VAT')),
                    ('creation_date', models.DateField(null=True, verbose_name='Date of creation', blank=True)),
                    (
                        'address',
                        models.ForeignKey(
                            related_name='+', blank=True, editable=False, to='creme_core.FakeAddress',
                            null=True, verbose_name='Billing address', on_delete=models.SET_NULL,
                        )
                    ),
                    (
                        'image',
                        models.ForeignKey(
                            on_delete=models.SET_NULL, verbose_name='Logo', blank=True, to='creme_core.FakeImage', null=True,
                        )
                    ),
                    (
                        'legal_form',
                        models.ForeignKey(
                            related_name='+', on_delete=creme_deletion.CREME_REPLACE_NULL,
                            verbose_name='Legal form', blank=True, to='creme_core.FakeLegalForm', null=True,
                        )
                    ),
                    (
                        'sector',
                        models.ForeignKey(
                            on_delete=creme_deletion.CREME_REPLACE, verbose_name='Sector',
                            blank=True, to='creme_core.FakeSector', null=True,
                        )
                    ),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Organisation',
                    'verbose_name_plural': 'Test Organisations',
                    'indexes': [
                        models.Index(
                            fields=['name', 'cremeentity_ptr'],
                            name='core__fakeorga__default_lv',
                        ),
                    ],
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeProductType',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    ('extra_data', models.JSONField(default=dict, editable=False)),
                    ('is_custom', models.BooleanField(default=True, editable=False)),
                    ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Product type',
                    'verbose_name_plural': 'Test Product types',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeProduct',
                fields=[
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    (
                        'type',
                        models.ForeignKey(
                            on_delete=models.CASCADE, verbose_name='Type',
                            blank=True, null=True, to='creme_core.FakeProductType',
                        )
                    ),
                    (
                        'images',
                        models.ManyToManyField(verbose_name='Images', to='creme_core.FakeImage', blank=True)
                    ),
                    (
                        'creation_year',
                        core_fields.YearField(verbose_name='Creation year', blank=True, null=True),
                    ),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Product',
                    'verbose_name_plural': 'Test Products',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeReport',
                fields=[
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    ('ctype', core_fields.EntityCTypeForeignKey(verbose_name='Entity type', to='contenttypes.ContentType')),
                    (
                        'efilter',
                        models.ForeignKey(
                            to='creme_core.EntityFilter', verbose_name='Filter',
                            on_delete=models.PROTECT, blank=True, null=True,
                            limit_choices_to={'filter_type': 1},  # core.entity_filter.EF_REGULAR
                        )
                    ),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Report',
                    'verbose_name_plural': 'Test Reports',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeTicketStatus',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    ('color', core_fields.ColorField(verbose_name='Color', default='ff0000')),
                    ('extra_data', models.JSONField(default=dict, editable=False)),
                    ('is_custom', models.BooleanField(default=True, editable=False)),
                    ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Ticket status',
                    'verbose_name_plural': 'Test Ticket status',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeTicketPriority',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    ('extra_data', models.JSONField(default=dict, editable=False)),
                    ('is_custom', models.BooleanField(default=True, editable=False)),
                    ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Ticket priority',
                    'verbose_name_plural': 'Test Ticket priorities',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeTicket',
                fields=[
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                    (
                        'status',
                        models.ForeignKey(
                            on_delete=models.SET_DEFAULT,
                            verbose_name='Status', default=1,
                            to='creme_core.FakeTicketStatus',
                        )
                    ),
                    (
                        'priority',
                        models.ForeignKey(
                            on_delete=models.SET(get_sentinel_priority),
                            verbose_name='Priority', default=3,
                            to='creme_core.FakeTicketPriority',
                        )
                    ),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test Ticket',
                    'verbose_name_plural': 'Test Tickets',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeIngredientGroup',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Ingredient Group',
                    'verbose_name_plural': 'Test Ingredient Groups',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeIngredient',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    (
                        'group',
                        models.ForeignKey(
                            to='creme_core.FakeIngredientGroup', verbose_name='Group',
                            on_delete=models.SET_DEFAULT,
                            null=True, blank=True, default=None,
                            related_name='fake_ingredients',
                        )
                    ),
                    ('extra_data', models.JSONField(default=dict, editable=False)),
                    ('is_custom', models.BooleanField(default=True, editable=False)),
                    ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Ingredient',
                    'verbose_name_plural': 'Test Ingredients',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeRecipe',
                fields=[
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=models.CASCADE,
                        )
                    ),
                    ('name', models.CharField(max_length=100, null=True, verbose_name='Name', blank=True)),
                    (
                        'ingredients',
                        models.ManyToManyField(
                            related_name='+', verbose_name='Ingredients',
                            to='creme_core.FakeIngredient', blank=True,
                        )
                    ),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Recipe',
                    'verbose_name_plural': 'Test Recipes',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeTodoCategory',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test ToDo category',
                    'verbose_name_plural': 'Test ToDo categories',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeTodo',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('title', models.CharField(max_length=200, verbose_name='Title')),
                    ('description', models.TextField(verbose_name='Description', blank=True)),
                    (
                        'categories',
                        models.ManyToManyField(
                            related_name='+', verbose_name='Categories',
                            to='creme_core.FakeTodoCategory', blank=True,
                        )
                    ),
                    (
                        'entity',
                        models.ForeignKey(
                            editable=False, on_delete=models.CASCADE,
                            to='creme_core.CremeEntity', related_name='fake_todos',
                        )
                    ),
                    (
                        'entity_content_type',
                        core_fields.EntityCTypeForeignKey(
                            editable=False, on_delete=models.CASCADE,
                            related_name='+', to='contenttypes.ContentType',
                        )
                    ),
                ],
                options={
                    'verbose_name': 'Test Todo',
                    'verbose_name_plural': 'Test Todos',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeSkill',
                fields=[
                    (
                        'id',
                        models.AutoField(
                            primary_key=True, verbose_name='ID',
                            serialize=False, auto_created=True,
                        )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Skill',
                    'verbose_name_plural': 'Test Skills',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeTraining',
                fields=[
                    (
                        'id',
                        models.AutoField(
                            primary_key=True, verbose_name='ID',
                            serialize=False, auto_created=True,
                        )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    (
                        'skills',
                        models.ManyToManyField(
                            to='creme_core.FakeSkill', verbose_name='Skills',
                            related_name='training', blank=True,
                        )
                    ),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test Training',
                    'verbose_name_plural': 'Test Training',
                },
                bases=(models.Model,),
            ),
        ])
