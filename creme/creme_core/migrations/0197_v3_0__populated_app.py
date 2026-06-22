from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0196_v3_0__instance_brick_class_ids'),
    ]

    operations = [
        migrations.CreateModel(
            name='PopulatedApp',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID',
                    )
                ),
                ('app', models.CharField(max_length=50)),
                ('version', models.CharField(max_length=15)),
                ('performed', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'unique_together': {('app', 'version')},
            },
        ),
    ]
