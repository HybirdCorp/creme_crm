from uuid import uuid4

from django.db import migrations, models

import creme.creme_core.models.fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0135_v2_6__filtercondition_data'),
    ]

    operations = [
        # CustomBrickConfigItem ------------------------------------------------
        migrations.AlterField(
            model_name='CustomBrickConfigItem',
            name='content_type',
            field=core_fields.CTypeForeignKey(
                editable=False, to='contenttypes.ContentType', verbose_name='Related type',
                # NB: remove constraints because they are not automatically renamed by 'RenameModel'.
                db_constraint=False,
                db_index=False,
            )
        ),
        migrations.RenameModel(
            old_name='CustomBrickConfigItem',
            new_name='OldCustomBrickConfigItem',
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
                # TMP
                ('old_id', models.CharField(max_length=100, serialize=False, editable=False)),
            ],
        ),

        # RelationBrickItem & InstanceBrickConfigItem --------------------------
        migrations.AddField(
            model_name='RelationBrickItem',
            name='uuid',
            field=models.UUIDField(
                default=uuid4, editable=False,
                # unique=True,
            ),
        ),
        migrations.AddField(
            model_name='InstanceBrickConfigItem',
            name='uuid',
            field=models.UUIDField(
                default=uuid4, editable=False,
                # unique=True,
            ),
        ),
    ]
