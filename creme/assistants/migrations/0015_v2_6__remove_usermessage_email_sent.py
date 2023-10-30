from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0014_v2_6__remove_usermsg_job'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usermessage',
            name='email_sent',
        ),
    ]
