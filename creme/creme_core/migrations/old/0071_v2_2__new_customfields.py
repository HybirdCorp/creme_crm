from django.db import migrations, models
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0070_v2_2__customfield_is_deleted'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomFieldURL',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.URLField()),
                ('custom_field', models.ForeignKey(on_delete=CASCADE, to='creme_core.CustomField')),
                ('entity', models.ForeignKey(on_delete=CASCADE, to='creme_core.CremeEntity')),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldText',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField()),
                ('custom_field', models.ForeignKey(on_delete=CASCADE, to='creme_core.CustomField')),
                ('entity', models.ForeignKey(on_delete=CASCADE, to='creme_core.CremeEntity')),
            ],
        ),
        migrations.CreateModel(
            name='CustomFieldDate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.DateField()),
                ('custom_field', models.ForeignKey(on_delete=CASCADE, to='creme_core.CustomField')),
                ('entity', models.ForeignKey(on_delete=CASCADE, to='creme_core.CremeEntity')),
            ],
        ),
    ]
