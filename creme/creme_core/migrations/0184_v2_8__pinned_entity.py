from django.conf import settings
from django.db import migrations, models
from django.utils.timezone import now

from creme.creme_core.models import fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0183_v2_8__customfield_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='PinnedEntity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'created',
                    core_fields.CreationDateTimeField(
                        verbose_name='Pinned on', blank=True, default=now, editable=False,
                    )
                ),
                (
                    'entity',
                    models.ForeignKey(
                        to='creme_core.cremeentity', on_delete=models.CASCADE,
                        related_name='+', editable=False,
                    )
                ),
                (
                    'entity_ctype',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.contenttype', on_delete=models.CASCADE,
                        related_name='+', editable=False,
                    )
                ),
                ('user', models.ForeignKey(on_delete=models.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('id',),
                'unique_together': {('entity', 'user')},
            },
        ),
    ]
