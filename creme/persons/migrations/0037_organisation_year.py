from django.db import migrations

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0036_v2_7__organisation_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='year',
            field=creme.creme_core.models.fields.YearField(blank=True, null=True, verbose_name='Year TMP'),
        ),
    ]
