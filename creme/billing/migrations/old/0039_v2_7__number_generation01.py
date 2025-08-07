from django.conf import settings
from django.db import migrations, models

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.PERSONS_ORGANISATION_MODEL),
        ('billing', '0038_v2_7__templatebase_status_uuid03'),
    ]

    operations = [
        migrations.CreateModel(
            name='NumberGeneratorItem',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID',
                    )
                ),
                (
                    'is_edition_allowed',
                    models.BooleanField(
                        verbose_name='Editable number',
                        default=True,
                        help_text='Can the number be manually edited?',
                    )
                ),
                ('data', models.JSONField(default=dict)),
                (
                    'numbered_type',
                    EntityCTypeForeignKey(
                        to='contenttypes.contenttype', on_delete=models.CASCADE,
                    )
                ),
                (
                    'organisation',
                    models.ForeignKey(
                        to=settings.PERSONS_ORGANISATION_MODEL,
                        on_delete=models.CASCADE,
                    )),
            ],
            options={
                'unique_together': {('organisation', 'numbered_type')},
            },
        ),
    ]
