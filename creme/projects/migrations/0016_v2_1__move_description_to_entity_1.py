from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0001_initial'),
    ]
    run_before = [
        ('creme_core', '0055_v2_1__cremeentity_description'),
    ]

    operations = [
        migrations.RenameField(
            model_name='project',
            old_name='description',
            new_name='description_tmp',
        ),
        migrations.RenameField(
            model_name='projecttask',
            old_name='description',
            new_name='description_tmp',
        ),
    ]
