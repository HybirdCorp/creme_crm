from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0037_v2_8__calendar_created_n_modified02'),
    ]

    operations = [
        migrations.AddField(
            model_name='activitytype',
            name='order',
            field=models.PositiveIntegerField(default=1, editable=False),
        ),
        migrations.AddField(
            model_name='activitysubtype',
            name='order',
            field=models.PositiveIntegerField(default=1, editable=False),
        ),
    ]
