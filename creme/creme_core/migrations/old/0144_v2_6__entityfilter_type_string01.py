from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0143_v2_6__userrole_extra_data_n_uuid03'),
    ]

    operations = [
        migrations.RenameField(
            model_name='entityfilter',
            old_name='filter_type',
            new_name='old_filter_type',
        ),
        migrations.AddField(
            model_name='entityfilter',
            name='filter_type',
            field=models.CharField(
                default='creme_core-regular', editable=False, max_length=36,
                choices=[
                    ('creme_core-credentials', 'Credentials filter'),
                    ('creme_core-regular', 'Regular filter (usable in list-view)'),
                ],
            ),
        ),
    ]
