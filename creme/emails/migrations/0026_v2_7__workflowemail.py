import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0001_initial'),
        migrations.swappable_dependency(settings.DOCUMENTS_DOCUMENT_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkflowEmail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
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
                            (1, 'Sent'), (2, 'Not sent'), (3, 'Sending error'), (4, 'Synchronized'),
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
                ('body_html', creme.creme_core.models.fields.UnsafeHTMLField()),
                (
                    'signature',
                    models.ForeignKey(
                        to='emails.emailsignature',
                        null=True, on_delete=django.db.models.deletion.SET_NULL,
                    )
                ),
                ('attachments', models.ManyToManyField(to=settings.DOCUMENTS_DOCUMENT_MODEL)),
            ],
        ),
    ]
