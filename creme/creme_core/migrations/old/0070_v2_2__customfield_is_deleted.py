# Generated by Django 2.2.11 on 2020-04-28 09:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0069_v2_2__instancebricks_json_data03'),
    ]

    operations = [
        migrations.AddField(
            model_name='customfield',
            name='is_deleted',
            field=models.BooleanField(default=False, editable=False, verbose_name='Is deleted?'),
        ),
    ]