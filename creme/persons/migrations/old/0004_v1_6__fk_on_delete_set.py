# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('persons', '0003_v1_6__custom_blocks'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='billing_address',
            field=models.ForeignKey(related_name='billing_address_contact_set', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='contact',
            name='shipping_address',
            field=models.ForeignKey(related_name='shipping_address_contact_set', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='billing_address',
            field=models.ForeignKey(related_name='billing_address_orga_set', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='image',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Logo', blank=True, to='media_managers.Image', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='shipping_address',
            field=models.ForeignKey(related_name='shipping_address_orga_set', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address'),
            preserve_default=True,
        ),
    ]
