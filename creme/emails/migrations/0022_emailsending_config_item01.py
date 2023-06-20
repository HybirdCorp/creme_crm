from django.db import migrations, models
from django.db.models.deletion import SET_NULL


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0021_v2_5__sync_status_update'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailSendingConfigItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'name',
                    models.CharField(
                        verbose_name='Name', max_length=100, unique=True,
                        help_text='Name displayed to users when selecting a configuration',
                    )
                ),
                (
                    'host', models.CharField(
                        verbose_name='Server URL', max_length=100,
                        help_text='Eg: smtp.mydomain.org',
                    )
                ),
                (
                    'username',
                    models.CharField(
                        verbose_name='Username', max_length=254, blank=True,
                        help_text='Eg: me@mydomain.org',
                    )
                ),
                ('encoded_password', models.CharField(editable=False, max_length=128, verbose_name='Password')),
                (
                    'port',
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name='Port',
                        help_text='Leave empty to use the default port',
                    )
                ),
                ('use_tls', models.BooleanField(default=True, verbose_name='Use TLS')),
                (
                    'default_sender',
                    models.EmailField(
                        verbose_name='Default sender', max_length=254, blank=True,
                        help_text=(
                            'If you fill this field with an email address, '
                            'this address will be used as the default value in '
                            'the form for the field «Sender» when sending a campaign.'
                        ),
                    )
                ),
            ],
            options={
                'verbose_name': 'SMTP configuration',
                'ordering': ('name',),
            },
        ),
        migrations.AddField(
            model_name='emailsending',
            name='config_item',
            field=models.ForeignKey(
                to='emails.emailsendingconfigitem', verbose_name='SMTP server',
                null=True, on_delete=SET_NULL,
            ),
        ),
    ]
