from django.conf import settings
from django.db import migrations
from django.utils import translation
from django.utils.translation import gettext as _


def convert_number_config(apps, schema_editor):
    get_simpledata = apps.get_model('billing', 'SimpleBillingAlgo').objects.get
    create_item = apps.get_model('billing', 'NumberGeneratorItem').objects.get_or_create
    configured_orga_ids = set()

    for conf in apps.get_model('billing', 'ConfigBillingAlgo').objects.all():
        if conf.name_algo != 'SIMPLE_ALGO':
            print(
                f'BEWARE: the organisation {conf.organisation} uses a specific '
                f'algorithm "{conf.name_algo}"; write a migration for it.'
            )
            continue

        # NB: working with ContentType instances does not work => we use IDs
        simple_data = get_simpledata(organisation=conf.organisation, ct_id=conf.ct_id)
        create_item(
            organisation=conf.organisation,
            numbered_type_id=conf.ct_id,
            defaults={
                'data': {
                    'format': simple_data.prefix + '{counter}',
                    'counter': simple_data.last_number + 1,
                    'reset': 'never',
                },
            },
        )

        configured_orga_ids.add(conf.organisation_id)

    if configured_orga_ids:
        translation.activate(settings.LANGUAGE_CODE)

        cnote_ct = apps.get_model('contenttypes', 'ContentType').objects.get(
            app_label='billing', model='creditnote',
        )

        for orga_id in configured_orga_ids:
            create_item(
                organisation_id=orga_id,
                numbered_type_id=cnote_ct.id,
                defaults={
                    'data': {
                        'format': _('CN') + '{counter}',
                        'counter': 1,
                        'reset': 'never',
                    },
                },
            )

def fix_button_config(apps, schema_editor):
    apps.get_model('creme_core', 'ButtonMenuItem').objects.filter(
        button_id='billing-generate_invoice_number',
    ).update(button_id='billing-generate_number')


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0039_v2_7__number_generation01'),
    ]

    operations = [
        migrations.RunPython(convert_number_config),
        migrations.RunPython(fix_button_config),
    ]
