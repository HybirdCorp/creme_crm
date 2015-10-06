# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations
from django.utils.translation import activate, ugettext as _


MODELBLOCK_ID = 'modelblock'


def convert_old_blocks(apps, schema_editor):
    get_model = apps.get_model
    BlockDetailviewLocation = get_model('creme_core', 'BlockDetailviewLocation')

    if not BlockDetailviewLocation.objects.exists():
        return

    activate(settings.LANGUAGE_CODE)

    get_ct = get_model('contenttypes', 'ContentType').objects.get
    invoice_ctype      = get_ct(app_label='billing', model='invoice')
    creditnote_ctype   = get_ct(app_label='billing', model='creditnote')
    quote_ctype        = get_ct(app_label='billing', model='quote')
    salesorder_ctype   = get_ct(app_label='billing', model='salesorder')
    templatebase_ctype = get_ct(app_label='billing', model='templatebase')

    create_cbci = get_model('creme_core', 'CustomBlockConfigItem').objects.create

    # NB: queries crash with ContentType instance (?!) => use ID
    try:
        bdl = BlockDetailviewLocation.objects.get(content_type=invoice_ctype.id,
                                                  block_id=MODELBLOCK_ID,
                                                 )
    except BlockDetailviewLocation.DoesNotExist:
        pass
    else:
        cbci = create_cbci(id='billing-invoice_info',
                           name=_('Invoice information'),
                           content_type=invoice_ctype,
                           json_cells='[{"type": "regular_field", "value": "created"}, '
                                       '{"type": "regular_field", "value": "modified"}, '
                                       '{"type": "regular_field", "value": "user"}, '
                                       '{"type": "regular_field", "value": "name"}, '
                                       '{"type": "regular_field", "value": "number"}, '
                                       '{"type": "regular_field", "value": "issuing_date"}, '
                                       '{"type": "regular_field", "value": "expiration_date"}, '
                                       '{"type": "regular_field", "value": "discount"}, '
                                       '{"type": "regular_field", "value": "comment"}, '
                                       '{"type": "regular_field", "value": "additional_info"}, '
                                       '{"type": "regular_field", "value": "payment_terms"}, '
                                       '{"type": "regular_field", "value": "currency"}, '
                                       '{"type": "regular_field", "value": "status"}, '
                                       '{"type": "regular_field", "value": "payment_type"}]',
                          )

        bdl.block_id = 'customblock-%s' % cbci.id
        bdl.save()

    try:
        bdl = BlockDetailviewLocation.objects.get(content_type=creditnote_ctype.id,
                                                  block_id=MODELBLOCK_ID,
                                                 )
    except BlockDetailviewLocation.DoesNotExist:
        pass
    else:
        cbci = create_cbci(id='billing-creditnote_info',
                           name=_('Credit note information'),
                           content_type=creditnote_ctype,
                           json_cells='[{"type": "regular_field", "value": "created"}, '
                                       '{"type": "regular_field", "value": "modified"}, '
                                       '{"type": "regular_field", "value": "user"}, '
                                       '{"type": "regular_field", "value": "name"}, '
                                       '{"type": "regular_field", "value": "number"}, '
                                       '{"type": "regular_field", "value": "issuing_date"}, '
                                       '{"type": "regular_field", "value": "expiration_date"}, '
                                       '{"type": "regular_field", "value": "discount"}, '
                                       '{"type": "regular_field", "value": "comment"}, '
                                       '{"type": "regular_field", "value": "additional_info"}, '
                                       '{"type": "regular_field", "value": "payment_terms"}, '
                                       '{"type": "regular_field", "value": "currency"}, '
                                       '{"type": "regular_field", "value": "status"}]',
                          )

        bdl.block_id = 'customblock-%s' % cbci.id
        bdl.save()

    try:
        bdl = BlockDetailviewLocation.objects.get(content_type=quote_ctype.id,
                                                  block_id=MODELBLOCK_ID,
                                                 )
    except BlockDetailviewLocation.DoesNotExist:
        pass
    else:
        cbci = create_cbci(id='billing-quote_info',
                           name=_('Quote information'),
                           content_type=quote_ctype,
                           json_cells='[{"type": "regular_field", "value": "created"}, '
                                       '{"type": "regular_field", "value": "modified"}, '
                                       '{"type": "regular_field", "value": "user"}, '
                                       '{"type": "regular_field", "value": "name"}, '
                                       '{"type": "regular_field", "value": "number"}, '
                                       '{"type": "regular_field", "value": "issuing_date"}, '
                                       '{"type": "regular_field", "value": "expiration_date"}, '
                                       '{"type": "regular_field", "value": "discount"}, '
                                       '{"type": "regular_field", "value": "comment"}, '
                                       '{"type": "regular_field", "value": "additional_info"}, '
                                       '{"type": "regular_field", "value": "payment_terms"}, '
                                       '{"type": "regular_field", "value": "currency"}, '
                                       '{"type": "regular_field", "value": "status"}, '
                                       '{"type": "regular_field", "value": "acceptation_date"}]',
                          )

        bdl.block_id = 'customblock-%s' % cbci.id
        bdl.save()

    try:
        bdl = BlockDetailviewLocation.objects.get(content_type=salesorder_ctype.id,
                                                  block_id=MODELBLOCK_ID,
                                                 )
    except BlockDetailviewLocation.DoesNotExist:
        pass
    else:
        cbci = create_cbci(id='billing-salesorder_info',
                           name=_('Salesorder information'),
                           content_type=salesorder_ctype,
                           json_cells='[{"type": "regular_field", "value": "created"}, '
                                       '{"type": "regular_field", "value": "modified"}, '
                                       '{"type": "regular_field", "value": "user"}, '
                                       '{"type": "regular_field", "value": "name"}, '
                                       '{"type": "regular_field", "value": "number"}, '
                                       '{"type": "regular_field", "value": "issuing_date"}, '
                                       '{"type": "regular_field", "value": "expiration_date"}, '
                                       '{"type": "regular_field", "value": "discount"}, '
                                       '{"type": "regular_field", "value": "comment"}, '
                                       '{"type": "regular_field", "value": "additional_info"}, '
                                       '{"type": "regular_field", "value": "payment_terms"}, '
                                       '{"type": "regular_field", "value": "currency"}, '
                                       '{"type": "regular_field", "value": "status"}]',
                          )

        bdl.block_id = 'customblock-%s' % cbci.id
        bdl.save()

    try:
        bdl = BlockDetailviewLocation.objects.get(content_type=templatebase_ctype.id,
                                                  block_id=MODELBLOCK_ID,
                                                 )
    except BlockDetailviewLocation.DoesNotExist:
        pass
    else:
        cbci = create_cbci(id='billing-templatebase_info',
                           name=_('Template information'),
                           content_type=templatebase_ctype,
                           json_cells='[{"type": "regular_field", "value": "created"}, '
                                       '{"type": "regular_field", "value": "modified"}, '
                                       '{"type": "regular_field", "value": "user"}, '
                                       '{"type": "regular_field", "value": "name"}, '
                                       '{"type": "regular_field", "value": "number"}, '
                                       '{"type": "regular_field", "value": "issuing_date"}, '
                                       '{"type": "regular_field", "value": "expiration_date"}, '
                                       '{"type": "regular_field", "value": "discount"}, '
                                       '{"type": "regular_field", "value": "comment"}, '
                                       '{"type": "regular_field", "value": "additional_info"}, '
                                       '{"type": "regular_field", "value": "payment_terms"}, '
                                       '{"type": "regular_field", "value": "currency"}, '
                                       '{"type": "function_field", "value": "get_verbose_status"}]',
                          )

        bdl.block_id = 'customblock-%s' % cbci.id
        bdl.save()


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('billing', '0009_v1_6__discount_field_type'),
    ]

    operations = [
        migrations.RunPython(convert_old_blocks),
    ]
