# Generated by Django 2.2 on 2019-09-02 09:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0057_v2_1__model_brick_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='CaseSensitivity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=4)),
            ],
        ),
    ]
