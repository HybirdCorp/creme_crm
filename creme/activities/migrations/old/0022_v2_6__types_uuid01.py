from uuid import uuid4

from django.db import migrations, models

import creme.creme_core.models.fields as creme_fields


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0001_initial'),
    ]

    operations = [
        # Remove constraints on deprecated FKs ---------------------------------
        migrations.AlterField(
            model_name='activitysubtype',
             name='type',
            field=models.ForeignKey(
                verbose_name='Type of activity', to='activities.ActivityType',
                on_delete=models.CASCADE,
                db_constraint=False,
                db_index=False,
            ),
        ),
        migrations.AlterField(
            model_name='activity',
            name='type',
            field=models.ForeignKey(
                on_delete=models.PROTECT, verbose_name='Activity type',
                to='activities.ActivityType',
                db_constraint=False,
                db_index=False,
            ),
        ),
        migrations.AlterField(
            model_name='activity',
            name='sub_type',
            field=models.ForeignKey(
                to='activities.activitysubtype',
                verbose_name='Activity sub-type',
                on_delete=models.PROTECT,
                db_constraint=False,
                db_index=False,
            ),
        ),

        # Rename deprecated FKs ------------------------------------------------
        migrations.RenameField(
            model_name='activity',
            old_name='type',
            new_name='old_type',
        ),
        migrations.RenameField(
            model_name='activity',
            old_name='sub_type',
            new_name='old_sub_type',
        ),

        # Rename deprecated models ---------------------------------------------
        migrations.RenameModel(
            old_name='ActivitySubType',
            new_name='OldActivitySubType',
        ),
        migrations.RenameModel(
            old_name='ActivityType',
            new_name='OldActivityType',
        ),

        # "New" models with UUIDs (and id backup for mapping) ---
        # NB: we create new models instead of modifying existing ones because of
        #     strange constraint errors with MySQL/MariaDB (& it's probably simpler).
        migrations.CreateModel(
            name='ActivityType',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                (
                    'default_day_duration',
                    models.IntegerField(verbose_name='Default day duration', default=0)
                ),
                (
                    'default_hour_duration',
                    creme_fields.DurationField(max_length=15, verbose_name='Default hour duration')
                ),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('extra_data', models.JSONField(default=dict, editable=False)),

                (
                    'old_id',
                    models.CharField(
                        max_length=100, serialize=False, editable=False,
                        # primary_key=True,
                    )
                ),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Type of activity',
                'verbose_name_plural': 'Types of activity',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ActivitySubType',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                (
                    'type',
                    models.ForeignKey(
                        verbose_name='Type of activity', to='activities.ActivityType',
                        on_delete=models.CASCADE,
                    )
                ),
                ('extra_data', models.JSONField(default=dict, editable=False)),

                (
                    'old_id',
                    models.CharField(
                        max_length=100, serialize=False, editable=False,
                        # primary_key=True,
                    )
                ),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Sub-type of activity',
                'verbose_name_plural': 'Sub-types of activity',
            },
            bases=(models.Model,),
        ),

        # New FK in Activity ---------------------------------------------------
        migrations.AddField(
            model_name='activity',
            name='type',
            field=models.ForeignKey(
                to='activities.ActivityType',
                verbose_name='Activity type',
                on_delete=models.PROTECT,
                # Temporary
                null=True, default=None,
            ),
        ),
        migrations.AddField(
            model_name='activity',
            name='sub_type',
            field=models.ForeignKey(
                to='activities.activitysubtype',
                verbose_name='Activity sub-type',
                on_delete=models.PROTECT,
                # Temporary
                null=True, default=None,
            ),
        ),
    ]
