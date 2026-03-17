from django.db import migrations


def remove_ctype(apps, schema_editor):
    apps.get_model('contenttypes', 'ContentType').objects.filter(
        app_label='reports', model='reportgraph'
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remove_ctype),
    ]
