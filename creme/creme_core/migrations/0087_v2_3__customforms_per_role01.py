from django.db import migrations, models
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0086_v2_2__textfields_to_jsonfields03'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='CustomFormConfigItem',
            new_name='OldCustomFormConfigItem',
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
                ('json_groups', models.TextField(editable=False, null=True)),
                (
                    'role',
                    models.ForeignKey(
                        default=None, blank=True, null=True, on_delete=CASCADE,
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
    ]
