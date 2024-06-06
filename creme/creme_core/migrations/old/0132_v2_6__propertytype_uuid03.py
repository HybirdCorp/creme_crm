from uuid import uuid4

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0131_v2_6__propertytype_uuid02'),
    ]

    operations = [
        # Delete the M2M to avoid constraint issues (we made backups) ----------
        migrations.RemoveField(
            model_name='CremePropertyType',
            name='subject_ctypes',
        ),
        migrations.RemoveField(
            model_name='RelationType',
            name='subject_properties',
        ),
        migrations.RemoveField(
            model_name='RelationType',
            name='subject_forbidden_properties',
        ),

        # Remove constraints on deprecated FK ----------------------------------
        migrations.AlterUniqueTogether(
            name='CremeProperty',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='CremeProperty',
            name='type',
            field=models.ForeignKey(
                verbose_name='Type of property', to='creme_core.CremePropertyType',
                on_delete=models.CASCADE,
                db_constraint=False,
                db_index=False,
            ),
        ),
        migrations.AlterField(
            model_name='CremePropertyType',
            name='text',
            field=models.CharField(
                # unique=True,  # Issue with PG (same table name for constraint with new type model)
                max_length=200, verbose_name='Text',
                help_text="For example: 'is pretty'",
            ),
        ),

        # Rename deprecated FK -------------------------------------------------
        migrations.RenameField(
            model_name='CremeProperty',
            old_name='type',
            new_name='old_type',
        ),

        # Rename deprecated model ----------------------------------------------
        migrations.RenameModel(
            old_name='CremePropertyType',
            new_name='OldCremePropertyType',
        ),

        # "New" model with UUIDs (and id backup for mapping) -------------------
        # NB: we create a new model instead of modifying existing ones because of
        #     strange constraint errors with MySQL/MariaDB (& it's probably simpler).
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
                        verbose_name='Created by the app', max_length=40, default='', editable=False,
                    )
                ),
                (
                    'text',
                    models.CharField(
                        unique=True, max_length=200, verbose_name='Text',
                        help_text="For example: 'is pretty'",
                    ),
                ),
                ('is_custom', models.BooleanField(default=False, editable=False)),
                (
                    'is_copiable',
                    models.BooleanField(
                        default=True, verbose_name='Is copiable',
                        help_text='Are the properties with this type copied when an entity is cloned?',
                    )),
                ('enabled', models.BooleanField(default=True, editable=False, verbose_name='Enabled?')),
                (
                    'subject_ctypes',
                    models.ManyToManyField(
                        related_name='subject_ctypes_creme_property_set',
                        verbose_name='Related to types of entities',
                        to='contenttypes.ContentType', blank=True,
                        help_text='No selected type means that all types are accepted',
                    )
                ),

                (
                    'old_id',
                    models.CharField(
                        max_length=100, serialize=False, editable=False,
                        # primary_key=True,
                    )
                ),
            ],
            options={
                'ordering': ('text',),
                'verbose_name': 'Type of property',
                'verbose_name_plural': 'Types of property',
            },
        ),

        # New FK & M2Ms --------------------------------------------------------
        migrations.AddField(
            model_name='CremeProperty',
            name='type',
            field=models.ForeignKey(
                verbose_name='Type of property',
                to='creme_core.CremePropertyType',
                on_delete=models.CASCADE,
                # Temporary
                null=True, default=None,
            ),
        ),
        migrations.AddField(
            model_name='RelationType',
            name='subject_properties',
            field=models.ManyToManyField(
                to='creme_core.CremePropertyType',
                related_name='relationtype_subjects_set',
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name='RelationType',
            name='subject_forbidden_properties',
            field=models.ManyToManyField(
                to='creme_core.CremePropertyType',
                related_name='relationtype_forbidden_set',
                blank=True,
            ),
        ),
    ]
