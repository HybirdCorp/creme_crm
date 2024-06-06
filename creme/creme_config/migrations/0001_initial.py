from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    # Memo: last migration was "0002_v2_4__cforms_brick_state"
    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = []

    if settings.TESTS_ON:
        operations.extend([
            migrations.CreateModel(
                name='FakeConfigEntity',
                fields=[
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            to='creme_core.CremeEntity', primary_key=True,
                            parent_link=True, auto_created=True, serialize=False,
                            on_delete=models.CASCADE,
                        )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test ConfigEntity',
                    'verbose_name_plural': 'Test ConfigEntities',
                },
                bases=('creme_core.cremeentity',),
            ),
        ])
