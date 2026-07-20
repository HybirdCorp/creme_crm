from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0204_v3_0__workflow_created_modified_disabled3'),
    ]

    operations = [
        migrations.AddField(
            model_name='entityfilter',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name='entityfilter',
            name='disabling_reason',
            field=models.TextField(editable=False, default=''),
            preserve_default=False,
        ),
    ]
