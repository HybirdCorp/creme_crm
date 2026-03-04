from uuid import uuid4

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, SET_NULL

from creme.creme_core.models import fields as core_fields
from creme.documents.models.fields import ImageEntityManyToManyField
from creme.emails.core.validators import TemplateVariablesValidator
from creme.emails.utils import generate_id


class Migration(migrations.Migration):
    # replaces = [
    #     ('emails', '0001_initial'),
    #     ('emails', '0026_v2_7__workflowemail'),
    #     ('emails', '0027_v2_7__signature_uuid01'),
    #     ('emails', '0028_v2_7__signature_uuid02'),
    #     ('emails', '0029_v2_7__signature_uuid03'),
    # ]

    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0001_initial'),
        ('creme_core', '0001_initial'),
        migrations.swappable_dependency(settings.DOCUMENTS_DOCUMENT_MODEL),
        migrations.swappable_dependency(settings.PERSONS_CONTACT_MODEL),
        migrations.swappable_dependency(settings.PERSONS_ORGANISATION_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailSignature',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                (
                    'name',
                    models.CharField(
                        max_length=100, verbose_name='Name',
                        help_text=(
                            "The name is only used to select the signature you want to use (in "
                            "an email or an email template), it is not display in the email's "
                            "body."
                        ),
                    )
                ),
                ('body', models.TextField(verbose_name='Body')),
                (
                    'images',
                    ImageEntityManyToManyField(
                        to=settings.DOCUMENTS_DOCUMENT_MODEL,
                        verbose_name='Images', blank=True,
                        help_text=(
                            'Images embedded in emails (but not as attached).\n'
                            'Hint: try to keep your images light (less than 2MB).\n'
                            'Hint: try to keep your images less than 500px wide to get a good render on mobile.'
                        ),
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        to=settings.AUTH_USER_MODEL, verbose_name='User', on_delete=CASCADE,
                    )
                ),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Email signature',
                'verbose_name_plural': 'Email signatures',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MailingList',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    ),
                ),
                ('name', models.CharField(max_length=80, verbose_name='Name of the mailing list')),
                (
                    'children',
                    models.ManyToManyField(
                        to=settings.EMAILS_MLIST_MODEL, verbose_name='Child mailing lists',
                        related_name='parents_set', editable=False,
                    )
                ),
                (
                    'contacts',
                    models.ManyToManyField(
                        to=settings.PERSONS_CONTACT_MODEL, verbose_name='Contact-recipients',
                        editable=False,
                    )
                ),
                (
                    'organisations',
                    models.ManyToManyField(
                        to=settings.PERSONS_ORGANISATION_MODEL,
                        verbose_name='Organisations recipients', editable=False
                    )
                ),
            ],
            options={
                'swappable': 'EMAILS_MLIST_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Mailing list',
                'verbose_name_plural': 'Mailing lists',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='EmailCampaign',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    ),
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the campaign')),
                (
                    'mailing_lists',
                    models.ManyToManyField(
                        to=settings.EMAILS_MLIST_MODEL,
                        verbose_name='Related mailing lists', blank=True,
                    )
                ),
            ],
            options={
                'swappable': 'EMAILS_CAMPAIGN_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Emailing campaign',
                'verbose_name_plural': 'Emailing campaigns',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='EmailSendingConfigItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False,
                                        verbose_name='ID')),
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
                        help_text='E.g. smtp.mydomain.org',
                    )
                ),
                (
                    'username',
                    models.CharField(
                        verbose_name='Username', max_length=254, blank=True,
                        help_text='E.g. me@mydomain.org',
                    )
                ),
                ('encoded_password',
                 models.CharField(editable=False, max_length=128, verbose_name='Password')),
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
        migrations.CreateModel(
            name='EmailSending',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                (
                    'config_item',
                    models.ForeignKey(
                        to='emails.emailsendingconfigitem', verbose_name='SMTP server',
                        null=True, on_delete=SET_NULL,
                    )
                ),
                ('sender', models.EmailField(max_length=100, verbose_name='Sender address')),
                (
                    'type',
                    models.PositiveSmallIntegerField(
                        verbose_name='Sending type',
                        default=1, choices=[(1, 'Immediate'), (2, 'Deferred')],
                    )
                ),
                ('sending_date', models.DateTimeField(verbose_name='Sending date')),
                (
                    'state',
                    models.PositiveSmallIntegerField(
                        default=3, verbose_name='Sending state', editable=False,
                        choices=[
                            (1, 'Done'),
                            (2, 'In progress'),
                            (3, 'Planned'),
                            (4, 'Error during sending'),
                        ],
                    ),
                ),
                (
                    'subject',
                    models.CharField(verbose_name='Subject', max_length=100, editable=False)
                ),
                ('body', models.TextField(verbose_name='Body', editable=False)),
                (
                    'body_html',
                    models.TextField(verbose_name='Body (HTML)', null=True, editable=False)
                ),
                (
                    'attachments',
                    models.ManyToManyField(
                        verbose_name='Attachments', to=settings.DOCUMENTS_DOCUMENT_MODEL,
                        editable=False,
                    ),
                ),
                (
                    'campaign',
                    models.ForeignKey(
                        verbose_name='Related campaign', to=settings.EMAILS_CAMPAIGN_MODEL,
                        related_name='sendings_set', on_delete=CASCADE,
                        editable=False,
                    )
                ),
                (
                    'signature',
                    models.ForeignKey(
                        to='emails.EmailSignature', verbose_name='Signature',
                        on_delete=SET_NULL, editable=False,  null=True,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Email campaign sending',
                'verbose_name_plural': 'Email campaign sendings',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    ),
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('subject', models.CharField(max_length=100, verbose_name='Subject')),
                (
                    'body',
                    models.TextField(
                        verbose_name='Body',
                        help_text=(
                            'You can use variables: '
                            '{{last_name}} {{first_name}} {{civility}} {{name}}'
                        ),
                        validators=[
                            TemplateVariablesValidator(
                                allowed_variables=('last_name', 'first_name', 'civility', 'name')),
                        ],
                    ),
                ),
                (
                    'body_html',
                    core_fields.UnsafeHTMLField(
                        verbose_name='Body (HTML)', blank=True,
                        help_text=(
                            'You can use variables: '
                            '{{last_name}} {{first_name}} {{civility}} {{name}}'
                        ),
                        validators=[
                            TemplateVariablesValidator(
                                allowed_variables=('last_name', 'first_name', 'civility', 'name'),
                            ),
                        ],
                    ),
                ),
                (
                    'attachments',
                    models.ManyToManyField(
                        to=settings.DOCUMENTS_DOCUMENT_MODEL,
                        verbose_name='Attachments', blank=True,
                    ),
                ),
                (
                    'signature',
                    models.ForeignKey(
                        to='emails.EmailSignature', verbose_name='Signature',
                        blank=True, null=True, on_delete=SET_NULL,
                    )
                ),
            ],
            options={
                'swappable': 'EMAILS_TEMPLATE_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Email template',
                'verbose_name_plural': 'Email templates',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='EntityEmail',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    ),
                ),
                (
                    'reads',
                    models.PositiveIntegerField(
                        default=0, verbose_name='Number of reads', null=True, editable=False,
                    )
                ),
                (
                    'status',
                    models.PositiveSmallIntegerField(
                        default=2, verbose_name='Status', editable=False,
                        choices=[
                            (1, 'Sent'),
                            (2, 'Not sent'),
                            (3, 'Sending error'),
                            (4, 'Synchronized'),
                        ],
                    ),
                ),
                ('sender', models.CharField(max_length=100, verbose_name='Sender')),
                ('recipient', models.CharField(max_length=100, verbose_name='Recipient')),
                ('subject', models.CharField(max_length=100, verbose_name='Subject', blank=True)),
                ('body', models.TextField(verbose_name='Body')),
                (
                    'sending_date',
                    models.DateTimeField(verbose_name='Sending date', null=True, editable=False)
                ),
                (
                    'reception_date',
                    models.DateTimeField(verbose_name='Reception date', null=True, editable=False)
                ),
                (
                    'identifier',
                    models.CharField(
                        verbose_name='Email ID',
                        unique=True, max_length=32,
                        default=generate_id, editable=False,
                    )
                ),
                ('body_html', core_fields.UnsafeHTMLField(verbose_name='Body (HTML)')),
                (
                    'attachments',
                    models.ManyToManyField(
                        to=settings.DOCUMENTS_DOCUMENT_MODEL,
                        verbose_name='Attachments', blank=True,
                    )
                ),
                (
                    'signature',
                    models.ForeignKey(
                        to='emails.EmailSignature', verbose_name='Signature',
                        blank=True, null=True, on_delete=SET_NULL,
                    )
                ),
            ],
            options={
                'swappable': 'EMAILS_EMAIL_MODEL',
                'ordering': ('-sending_date',),
                'verbose_name': 'Email',
                'verbose_name_plural': 'Emails',
            },
            bases=('creme_core.cremeentity', models.Model),
        ),
        migrations.CreateModel(
            name='LightWeightEmail',
            fields=[
                (
                    'id',
                    models.CharField(
                        verbose_name='Email ID', primary_key=True, max_length=32,
                        serialize=False, editable=False,
                    )
                ),
                (
                    'reads',
                    models.PositiveIntegerField(
                        default=0, verbose_name='Number of reads', null=True, editable=False,
                    )
                ),
                (
                    'status',
                    models.PositiveSmallIntegerField(
                        default=2, verbose_name='Status', editable=False,
                        choices=[
                            (1, 'Sent'),
                            (2, 'Not sent'),
                            (3, 'Sending error'),
                            (4, 'Synchronized'),
                        ],
                    ),
                ),
                ('sender', models.CharField(max_length=100, verbose_name='Sender')),
                ('recipient', models.CharField(max_length=100, verbose_name='Recipient')),
                ('subject', models.CharField(max_length=100, verbose_name='Subject', blank=True)),
                ('body', models.TextField(verbose_name='Body')),
                (
                    'sending_date',
                    models.DateTimeField(verbose_name='Sending date', null=True, editable=False)
                ),
                (
                    'reception_date',
                    models.DateTimeField(verbose_name='Reception date', null=True, editable=False)
                ),
                (
                    'recipient_ctype',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.contenttype', related_name='+',
                        editable=False, null=True, on_delete=CASCADE,
                    )
                ),
                (
                    'recipient_entity',
                    models.ForeignKey(
                        related_name='received_lw_mails', editable=False,
                        to='creme_core.CremeEntity', null=True, on_delete=CASCADE,
                    ),
                ),
                (
                    'sending',
                    models.ForeignKey(
                        related_name='mails_set', editable=False, to='emails.EmailSending',
                        verbose_name='Related sending', on_delete=CASCADE,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Email of campaign',
                'verbose_name_plural': 'Emails of campaign',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EmailRecipient',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('address', models.CharField(max_length=100, verbose_name='Email address')),
                (
                    'ml',
                    models.ForeignKey(
                        to=settings.EMAILS_MLIST_MODEL,
                        verbose_name='Related mailing list', on_delete=CASCADE,
                    )
                ),
            ],
            options={
                'ordering': ('address',),
                'verbose_name': 'Recipient',
                'verbose_name_plural': 'Recipients',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EmailToSync',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    )
                ),
                ('subject', models.CharField(max_length=100, verbose_name='Subject')),
                ('body', models.TextField(verbose_name='Body')),
                ('body_html', core_fields.UnsafeHTMLField(verbose_name='Body (HTML)')),
                (
                    'date',
                    models.DateTimeField(editable=False, null=True, verbose_name='Reception date')
                ),
                (
                    'attachments',
                    models.ManyToManyField(to='creme_core.FileRef', verbose_name='Attachments')
                ),
                (
                    'user',
                    core_fields.CremeUserForeignKey(to=settings.AUTH_USER_MODEL, verbose_name='Owner')
                ),
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
                        editable=False, null=True, related_name='+',
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
                        help_text='E.g. pop.mydomain.org',
                    )
                ),
                (
                    'username',
                    models.CharField(
                        verbose_name='Username',
                        help_text='E.g. me@mydomain.org', max_length=254,
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
        migrations.CreateModel(
            name='WorkflowEmail',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID',
                    )
                ),
                (
                    'reads',
                    models.PositiveIntegerField(
                        default=0, editable=False, null=True, verbose_name='Number of reads',
                    )
                ),
                (
                    'status',
                    models.PositiveSmallIntegerField(
                        verbose_name='Status',
                        choices=[
                            (1, 'Sent'),
                            (2, 'Not sent'),
                            (3, 'Sending error'),
                            (4, 'Synchronized'),
                        ],
                        default=2, editable=False,
                    )
                ),
                ('sender', models.CharField(max_length=100, verbose_name='Sender')),
                ('subject', models.CharField(blank=True, max_length=100, verbose_name='Subject')),
                ('recipient', models.CharField(max_length=100, verbose_name='Recipient')),
                ('body', models.TextField(verbose_name='Body')),
                (
                    'sending_date',
                    models.DateTimeField(editable=False, null=True, verbose_name='Sending date')
                ),
                (
                    'reception_date',
                    models.DateTimeField(editable=False, null=True, verbose_name='Reception date')
                ),
                ('body_html', core_fields.UnsafeHTMLField()),
                (
                    'signature',
                    models.ForeignKey(to='emails.emailsignature', null=True, on_delete=SET_NULL)
                ),
                ('attachments', models.ManyToManyField(to=settings.DOCUMENTS_DOCUMENT_MODEL)),
            ],
        ),
    ]
