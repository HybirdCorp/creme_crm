from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0106_v2_4__relationtype_enabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorldSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('menu_icon', models.ImageField(upload_to='creme_core', verbose_name='Menu icon', blank=True)),
            ],
            options={
                'swappable': 'CREME_CORE_WSETTINGS_MODEL',
            },
        ),
    ]
