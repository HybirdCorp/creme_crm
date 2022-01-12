from django.db import migrations


def nullify_jobs_data(apps, schema_editor):
    apps.get_model(
        'creme_core', 'Job',
    ).objects.filter(raw_data='').update(raw_data=None)


def manage_empty_mass_jobs_lines(apps, schema_editor):
    apps.get_model(
        'creme_core', 'MassImportJobResult',
    ).objects.filter(raw_line='').update(raw_line='[]')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0084_v2_2__textfields_to_jsonfields01'),
    ]

    operations = [
        migrations.RunPython(nullify_jobs_data),
        migrations.RunPython(manage_empty_mass_jobs_lines),
    ]
