# -*- coding: utf-8 -*-

from django.contrib import admin

from sms.models import *


class SMSCampaignAdmin(admin.ModelAdmin):
    list_display = ('name', )

register = admin.site.register

register(MessagingList)
register(Recipient)
register(SMSCampaign, SMSCampaignAdmin)
register(MessageTemplate)
register(Sending)
register(Message)
