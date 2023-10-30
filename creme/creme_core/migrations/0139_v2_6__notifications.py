import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0138_v2_6__brick_config_uuid03'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationChannel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=48, verbose_name='Name')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('type_id', models.CharField(editable=False, max_length=48)),
                (
                    'required',
                    models.BooleanField(
                        verbose_name='Is required?', default=True,
                        help_text=(
                            'When a channel is required, users have to chose at least one output '
                            '(in-app, email) in their personal configuration.'
                        ),
                    )
                ),
                ('deleted', models.DateTimeField(editable=False, null=True)),
                (
                    'default_outputs',
                    models.JSONField(verbose_name='Default outputs', default=list, editable=False)
                ),
            ],
            options={'ordering': ('id',)},
        ),
        migrations.CreateModel(
            name='NotificationChannelConfigItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('outputs', models.JSONField(default=list, editable=False)),
                (
                    'channel',
                    models.ForeignKey(
                        editable=False, on_delete=models.PROTECT, to='creme_core.notificationchannel',
                    )
                ),
                ('user', models.ForeignKey(editable=False, on_delete=models.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('channel', 'user')},
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                (
                    'channel',
                    models.ForeignKey(
                        verbose_name='Channel', to='creme_core.notificationchannel',
                        on_delete=models.PROTECT,
                        related_name='notifications',
                    )
                ),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
                ('created', models.DateTimeField(verbose_name='Creation date', auto_now_add=True)),
                ('output', models.CharField(max_length=32)),
                ('content_id', models.CharField(max_length=48)),
                ('content_data', models.JSONField(default=dict)),
                (
                    'level',
                    models.PositiveSmallIntegerField(
                        verbose_name='Level',
                        choices=[(1, 'Low'), (2, 'Normal'), (3, 'High')],
                        default=2,
                    )
                ),
                ('discarded', models.DateTimeField(null=True)),
                ('extra_data', models.JSONField(default=dict)),
            ],
            options={
                'ordering': ('-id',),
            },
        ),

        migrations.DeleteModel(name='DateReminder'),
    ]
