from django.db import migrations


def delete_job(apps, schema_editor):
    apps.get_model('creme_core', 'Job').objects.filter(
        type_id='assistants-usermessages_send',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
        ('assistants', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(delete_job),
    ]
