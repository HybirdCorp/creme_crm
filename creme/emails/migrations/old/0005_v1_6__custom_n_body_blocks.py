# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations
from django.utils.translation import activate, ugettext as _


MODELBLOCK_ID = 'modelblock'
LEFT = 2


def convert_old_block_config(apps, schema_editor):
    get_model = apps.get_model
    BlockDetailviewLocation = get_model('creme_core', 'BlockDetailviewLocation')

    if not BlockDetailviewLocation.objects.exists():
        return

    activate(settings.LANGUAGE_CODE)

    ContentType = get_model('contenttypes', 'ContentType')

    def get_emails_ct(model_name):
        return ContentType.objects.filter(app_label='emails', model=model_name).first()

    email_ctype    = get_emails_ct('entityemail')
    template_ctype = get_emails_ct('emailtemplate')

    create_cbci = get_model('creme_core', 'CustomBlockConfigItem').objects.create
    create_bdl = BlockDetailviewLocation.objects.create

    if email_ctype is not None:
        cbci = create_cbci(id='emails-entityemail_info',
                           name=_('Email information'),
                           content_type=email_ctype,
                           json_cells='[{"type": "regular_field", "value": "user"}, '
                                       '{"type": "regular_field", "value": "reads"}, '
                                       '{"type": "regular_field", "value": "status"}, '
                                       '{"type": "regular_field", "value": "sender"}, '
                                       '{"type": "regular_field", "value": "recipient"}, '
                                       '{"type": "regular_field", "value": "subject"}, '
                                       '{"type": "regular_field", "value": "reception_date"}, '
                                       '{"type": "regular_field", "value": "attachments"}, '
                                       '{"type": "regular_field", "value": "body"}]',
                          )

        # NB: queries crash with ContentType instance (?!) => use ID
        try:
            bdl = BlockDetailviewLocation.objects.get(content_type=email_ctype.id,
                                                      block_id=MODELBLOCK_ID,
                                                     )
        except BlockDetailviewLocation.DoesNotExist:
            if not BlockDetailviewLocation.objects.filter(content_type=email_ctype.id).exists():
                create_bdl(content_type=email_ctype, block_id='block_emails-email_html_body', order=20, zone=LEFT)

                for default_bdl in BlockDetailviewLocation.objects.filter(content_type=None):
                    default_id = default_bdl.block_id
                    create_bdl(content_type=email_ctype, order=default_bdl.order, zone=default_bdl.zone,
                               block_id='customblock-%s' % cbci.id if default_id == MODELBLOCK_ID else default_id,
                              )
        else:
            bdl.block_id = 'customblock-%s' % cbci.id
            bdl.save()

            # email_html_body_block.id_
            create_bdl(content_type=email_ctype, block_id='block_emails-email_html_body', order=bdl.order, zone=bdl.zone)

    if template_ctype is not None:
        cbci = create_cbci(id='emails-emailtemplate_info',
                           name=_('Email template information'),
                           content_type=template_ctype,
                           json_cells='[{"type": "regular_field", "value": "created"}, '
                                       '{"type": "regular_field", "value": "modified"}, '
                                       '{"type": "regular_field", "value": "user"}, '
                                       '{"type": "regular_field", "value": "name"}, '
                                       '{"type": "regular_field", "value": "subject"}, '
                                       '{"type": "regular_field", "value": "body"}, '
                                       '{"type": "regular_field", "value": "signature"}]',
                          )

        try:
            bdl = BlockDetailviewLocation.objects.get(content_type=template_ctype.id,
                                                      block_id=MODELBLOCK_ID,
                                                     )
        except BlockDetailviewLocation.DoesNotExist:
            if not BlockDetailviewLocation.objects.filter(content_type=template_ctype.id).exists():
                create_bdl(content_type=email_ctype, block_id='block_emails-template_html_body', order=20, zone=LEFT)

                for default_bdl in BlockDetailviewLocation.objects.filter(content_type=None):
                    default_id = default_bdl.block_id
                    create_bdl(content_type=template_ctype, order=default_bdl.order, zone=default_bdl.zone,
                               block_id='customblock-%s' % cbci.id if default_id == MODELBLOCK_ID else default_id,
                              )
        else:
            bdl.block_id = 'customblock-%s' % cbci.id
            bdl.save()

            # template_html_body_block.id_
            create_bdl(content_type=template_ctype, block_id='block_emails-template_html_body', order=bdl.order, zone=bdl.zone)


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0004_v1_6__not_editable_n_choices'),
    ]

    operations = [
        migrations.RunPython(convert_old_block_config),
    ]
