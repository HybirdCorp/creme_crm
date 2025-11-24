from django.conf import settings
from django.db import migrations, models
from django.utils.timezone import now

import creme.creme_core.models.fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0181_v28__userrole_deactivated_on'),
    ]

    operations = [
        migrations.CreateModel(
            name='LastViewedEntity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'entity_ctype',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.contenttype', related_name='+',
                        on_delete=models.CASCADE,
                        editable=False,
                    )
                ),
                (
                    'entity',
                    models.ForeignKey(
                        to='creme_core.cremeentity', related_name='+',
                        null=True, on_delete=models.SET_NULL,
                        editable=False,
                    )
                ),
                ('user', models.ForeignKey(on_delete=models.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('viewed', core_fields.ModificationDateTimeField(blank=True, default=now, editable=False)),
            ],
            options={
                'ordering': ('-viewed',),
            },
        ),
    ]
