from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Criticity',
            new_name='Criticality',
        ),

        migrations.RenameField(
            model_name='ticket',
            old_name='criticity',
            new_name='criticality',
        ),
        migrations.RenameField(
            model_name='tickettemplate',
            old_name='criticity',
            new_name='criticality',
        ),
    ]
