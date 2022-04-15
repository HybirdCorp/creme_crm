from uuid import uuid4

from django.db import migrations, models

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0165_v2_7__fileref_longer_filedata'),
    ]

    operations = [
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid4, unique=True, editable=False)),
                ('title', models.CharField(verbose_name='Title', max_length=100)),
                (
                    'content_type',
                    EntityCTypeForeignKey(
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
        migrations.AddField(
            model_name='historyline',
            name='by_wf_engine',
            field=models.BooleanField(default=False, verbose_name='Action of Workflow engine'),
        ),
    ]
