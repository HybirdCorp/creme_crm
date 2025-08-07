from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='templatebase',
            name='status_uuid',
            field=models.UUIDField(default='c221d765-415f-4e25-99b6-ac801b85ce20', editable=False),
            preserve_default=False,
        ),
    ]
