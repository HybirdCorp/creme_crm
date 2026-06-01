from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('polls', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='polltype',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
    ]
