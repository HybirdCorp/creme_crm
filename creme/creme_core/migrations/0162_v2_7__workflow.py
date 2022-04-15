from django.db import migrations, models

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0161_v2_7__propertytype_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('json_trigger', models.JSONField(default=dict)),
                ('json_conditions', models.JSONField(default=list)),
                ('json_actions', models.JSONField(default=list)),
                (
                    'content_type',
                    EntityCTypeForeignKey(
                        to='contenttypes.contenttype', verbose_name='Related resource',
                        on_delete=models.CASCADE,
                    )
                ),
            ],
            options={
                'verbose_name': 'Rule',
                'verbose_name_plural': 'Rules',
            },
        ),
    ]
