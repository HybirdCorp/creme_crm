from django.db import migrations

from json import loads as json_load

from ..utils.serializers import json_encode

EFC_CUSTOMFIELD = 20


def convert_conditions_old_data(apps, schema_editor):
    EntityFilterCondition = apps.get_model('creme_core', 'EntityFilterCondition')

    for condition in EntityFilterCondition.objects.filter(type=EFC_CUSTOMFIELD):
        data = json_load(condition.value)
        values = data.pop('value')

        if not isinstance(values, list):
            values = [values]

        data['values'] = values
        condition.value = json_encode(data)
        condition.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0058_v2_1__casesensitivity'),
    ]

    operations = [
        migrations.RunPython(convert_conditions_old_data),
    ]
