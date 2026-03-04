from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0182_v2_8__last_viewed_entity'),
    ]

    operations = [
        migrations.AddField(
            model_name='customfield',
            name='description',
            field=models.TextField(
                verbose_name='Description', blank=True,
                help_text='The description is notably used in forms to help user',
            ),
        ),
    ]
