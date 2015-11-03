# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations
from django.utils.translation import activate, ugettext as _

from ..  import contact_model_is_custom, organisation_model_is_custom


MODELBLOCK_ID = 'modelblock'


def convert_old_blocks(apps, schema_editor):
    get_model = apps.get_model
    BlockDetailviewLocation = get_model('creme_core', 'BlockDetailviewLocation')

    if not BlockDetailviewLocation.objects.exists():
        return

    activate(settings.LANGUAGE_CODE)

    get_ct = get_model('contenttypes', 'ContentType').objects.get

    def get_persons_ct(model_name, custom_func):
        if not custom_func():
            return get_ct(app_label='persons', model=model_name)

    contact_ctype = get_persons_ct('contact',      contact_model_is_custom)
    orga_ctype    = get_persons_ct('organisation', organisation_model_is_custom)

    create_cbci = get_model('creme_core', 'CustomBlockConfigItem').objects.create

    if contact_ctype is not None:
        # NB: queries crash with ContentType instance (?!) => use ID
        try:
            bdl = BlockDetailviewLocation.objects.get(content_type=contact_ctype.id,
                                                      block_id=MODELBLOCK_ID,
                                                     )
        except BlockDetailviewLocation.DoesNotExist:
            pass
        else:
            cbci = create_cbci(id='persons-contact_main_info',
                               name=_('Contact information'),
                               content_type=contact_ctype,
                               json_cells='[{"type": "regular_field", "value": "created"}, '
                                           '{"type": "regular_field", "value": "modified"}, '
                                           '{"type": "regular_field", "value": "civility"}, '
                                           '{"type": "regular_field", "value": "first_name"}, '
                                           '{"type": "regular_field", "value": "last_name"}, '
                                           '{"type": "regular_field", "value": "sector"}, '
                                           '{"type": "regular_field", "value": "position"}, '
                                           '{"type": "regular_field", "value": "user"}, '
                                           '{"type": "regular_field", "value": "is_user"}, '
                                           '{"type": "regular_field", "value": "birthday"}, '
                                           '{"type": "regular_field", "value": "image"}, '
                                           '{"type": "regular_field", "value": "description"}]',
                              )

            bdl.block_id = 'customblock-%s' % cbci.id
            bdl.save()

        try:
            bdl = BlockDetailviewLocation.objects.get(content_type=contact_ctype.id,
                                                      block_id='block_%s-%s' % ('persons', 'contact_coordinates'),
                                                     )
        except BlockDetailviewLocation.DoesNotExist:
            pass
        else:
            cbci = create_cbci(id='persons-contact_details',
                               name=_('Contact details'),
                               content_type=contact_ctype,
                               json_cells='[{"type": "regular_field", "value": "phone"}, '
                                           '{"type": "regular_field", "value": "mobile"}, '
                                           '{"type": "regular_field", "value": "fax"}, '
                                           '{"type": "regular_field", "value": "email"}, '
                                           '{"type": "regular_field", "value": "url_site"}, '
                                           '{"type": "regular_field", "value": "skype"}]',
                              )

            bdl.block_id = 'customblock-%s' % cbci.id
            bdl.save()

    if orga_ctype is not None:
        try:
            bdl = BlockDetailviewLocation.objects.get(content_type=orga_ctype.id,
                                                      block_id=MODELBLOCK_ID,
                                                     )
        except BlockDetailviewLocation.DoesNotExist:
            pass
        else:
            cbci = create_cbci(id='persons-organisation_main_info',
                               name=_('Organisation information'),
                               content_type=orga_ctype,
                               json_cells='[{"type": "regular_field", "value": "created"}, '
                                           '{"type": "regular_field", "value": "modified"}, '
                                           '{"type": "regular_field", "value": "name"}, '
                                           '{"type": "regular_field", "value": "staff_size"}, '
                                           '{"type": "regular_field", "value": "legal_form"}, '
                                           '{"type": "regular_field", "value": "sector"}, '
                                           '{"type": "regular_field", "value": "capital"}, '
                                           '{"type": "regular_field", "value": "siren"}, '
                                           '{"type": "regular_field", "value": "naf"}, '
                                           '{"type": "regular_field", "value": "siret"}, '
                                           '{"type": "regular_field", "value": "rcs"}, '
                                           '{"type": "regular_field", "value": "tvaintra"}, '
                                           '{"type": "regular_field", "value": "subject_to_vat"}, '
                                           '{"type": "regular_field", "value": "user"}, '
                                           '{"type": "regular_field", "value": "annual_revenue"}, '
                                           '{"type": "regular_field", "value": "description"}, '
                                           '{"type": "regular_field", "value": "creation_date"}, '
                                           '{"type": "regular_field", "value": "image"}]',
                              )

            bdl.block_id = 'customblock-%s' % cbci.id
            bdl.save()

        try:
            bdl = BlockDetailviewLocation.objects.get(content_type=orga_ctype.id,
                                                      block_id='block_%s-%s' % ('persons', 'orga_coordinates'),
                                                     )
        except BlockDetailviewLocation.DoesNotExist:
            pass
        else:
            cbci = create_cbci(id='persons-organisation_details',
                               name=_('Organisation details'),
                               content_type=orga_ctype,
                               json_cells='[{"type": "regular_field", "value": "phone"}, '
                                           '{"type": "regular_field", "value": "fax"}, '
                                           '{"type": "regular_field", "value": "email"}, '
                                           '{"type": "regular_field", "value": "url_site"}]',
                              )

            bdl.block_id = 'customblock-%s' % cbci.id
            bdl.save()


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0002_v1_6__convert_user_FKs'),
    ]

    operations = [
        migrations.RunPython(convert_old_blocks),
    ]
