from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0085_v2_2__textfields_to_jsonfields02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deletioncommand',
            name='json_replacers',
            field=models.JSONField(default=list, editable=False),
        ),

        migrations.AlterField(
            model_name='job',
            name='raw_data',
            field=models.JSONField(editable=False, null=True),
        ),
        migrations.RenameField(
            model_name='job',
            old_name='raw_data',
            new_name='data',
        ),

        migrations.AlterField(
            model_name='entityjobresult',
            name='raw_messages',
            field=models.JSONField(null=True),
        ),
        migrations.AlterField(
            model_name='jobresult',
            name='raw_messages',
            field=models.JSONField(null=True),
        ),
        migrations.AlterField(
            model_name='massimportjobresult',
            name='raw_messages',
            field=models.JSONField(null=True),
        ),
        migrations.RenameField(
            model_name='entityjobresult',
            old_name='raw_messages',
            new_name='messages',
        ),
        migrations.RenameField(
            model_name='jobresult',
            old_name='raw_messages',
            new_name='messages',
        ),
        migrations.RenameField(
            model_name='massimportjobresult',
            old_name='raw_messages',
            new_name='messages',
        ),

        migrations.AlterField(
            model_name='massimportjobresult',
            name='raw_line',
            field=models.JSONField(default=list),
        ),
        migrations.RenameField(
            model_name='massimportjobresult',
            old_name='raw_line',
            new_name='line',
        ),
    ]
