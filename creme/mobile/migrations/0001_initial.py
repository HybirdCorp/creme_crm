from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    # Memo: last migration was "0005_v2_6__settingvalue_json".
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MobileFavorite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('entity', models.ForeignKey(related_name='mobile_favorite', to='creme_core.CremeEntity', on_delete=CASCADE)),
                ('user', models.ForeignKey(related_name='mobile_favorite', to=settings.AUTH_USER_MODEL, on_delete=CASCADE)),
            ],
            options={
                'unique_together': {('entity', 'user')},
            },
            bases=(models.Model,),
        ),
    ]
