from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, SET_NULL

from creme.creme_core.models import fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('emails', '0018_v2_4__lightweightemail_recipient_ctype03'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailToSync',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=100, verbose_name='Subject')),
                ('body', models.TextField(verbose_name='Body')),
                ('body_html', core_fields.UnsafeHTMLField(verbose_name='Body (HTML)')),
                ('date', models.DateTimeField(editable=False, null=True, verbose_name='Reception date')),
                ('attachments', models.ManyToManyField(to='creme_core.FileRef', verbose_name='Attachments')),
                ('user', core_fields.CremeUserForeignKey(to=settings.AUTH_USER_MODEL, verbose_name='Owner')),
            ],
        ),
        migrations.CreateModel(
            name='EmailToSyncPerson',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID',
                    )
                ),
                (
                    'type',
                    models.PositiveSmallIntegerField(
                        choices=[(1, 'Sender'), (2, 'Recipient')], default=2, editable=False,
                    )
                ),
                ('email', models.EmailField(editable=False, max_length=254)),
                ('is_main', models.BooleanField(default=False, editable=False)),
                (
                    'email_to_sync',
                    models.ForeignKey(
                        to='emails.emailtosync', related_name='related_persons',
                        editable=False, on_delete=CASCADE,
                    )
                ),
                (
                    'entity',
                    models.ForeignKey(
                        to='creme_core.cremeentity', on_delete=SET_NULL,
                        editable=False, null=True,  related_name='+',
                    )
                ),
                (
                    'entity_ctype',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.contenttype', on_delete=CASCADE,
                        editable=False, null=True, related_name='+',
                    )),
            ],
            options={
                'verbose_name': 'Sender/recipient to synchronize',
                'verbose_name_plural': 'Senders/recipients to synchronize',
            },
        ),
        migrations.CreateModel(
            name='EmailSyncConfigItem',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID',
                    )
                ),
                (
                    'type',
                    models.PositiveSmallIntegerField(choices=[(1, 'POP'), (2, 'IMAP')], default=1)
                ),
                (
                    'host',
                    models.CharField(
                        verbose_name='Server URL', max_length=100,
                        help_text='Eg: pop.mydomain.org',
                    )
                ),
                (
                    'username',
                    models.CharField(
                        verbose_name='Username',
                        help_text='Eg: me@mydomain.org', max_length=254,
                    )
                ),
                (
                    'encoded_password',
                    models.CharField(editable=False, max_length=128, verbose_name='Password')
                ),
                (
                    'port',
                    models.PositiveIntegerField(
                        verbose_name='Port', blank=True, null=True,
                        help_text='Leave empty to use the default port',
                    )
                ),
                ('use_ssl', models.BooleanField(default=True, verbose_name='Use SSL')),
                (
                    'keep_attachments',
                    models.BooleanField(
                        verbose_name='Keep the attachments', default=True,
                        help_text=(
                            'Attachments are converted to real Documents when '
                            'the email is accepted.'
                        ),
                    )
                ),
                (
                    'default_user',
                    core_fields.CremeUserForeignKey(
                        to=settings.AUTH_USER_MODEL, verbose_name='Default owner',
                        blank=True, null=True,
                        help_text=(
                            'If no user corresponding to an email address is found '
                            '(in the fields "From", "To", "CC" or "BCC") '
                            'to be the owner of the email, this user is used as default one.\n'
                            'Beware: if *No default user* is selected, emails with no address '
                            'related to a user are just dropped.'
                        ),
                    )
                ),
            ],
        ),
    ]
