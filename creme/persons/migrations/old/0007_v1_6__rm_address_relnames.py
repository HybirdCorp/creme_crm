# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations
from django.db.models import ForeignKey
from django.db.models.deletion import SET_NULL


PERSONS_ADDRESS_MODEL = settings.PERSONS_ADDRESS_MODEL


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0006_v1_6__contact_full_position'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='billing_address',
            field=ForeignKey(related_name='+', on_delete=SET_NULL, editable=False, to=PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address'),
        ),
        migrations.AlterField(
            model_name='contact',
            name='shipping_address',
            field=ForeignKey(related_name='+', on_delete=SET_NULL, editable=False, to=PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address'),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='billing_address',
            field=ForeignKey(related_name='+', on_delete=SET_NULL, editable=False, to=PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address'),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='shipping_address',
            field=ForeignKey(related_name='+', on_delete=SET_NULL, editable=False, to=PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address'),
        ),
    ]
