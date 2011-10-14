# -*- coding: utf-8 -*-

from django.contrib import admin

from emails.models import *


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'body', 'body_html', 'signature')


class MailingListAdmin(admin.ModelAdmin):
    list_display = ('name',)


class LightWeightEmailAdmin(admin.ModelAdmin):
    list_display = ('id', 'sending', 'reads', 'status', 'sender', 'recipient', 'subject', 'sending_date')


class RecipientAdmin(admin.ModelAdmin):
    list_display = ('ml', 'address')


class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ('name',)


class EmailSendingAdmin(admin.ModelAdmin):
    list_display = ('sender', 'campaign', 'type', 'sending_date', 'state', 'subject', 'body', 'signature')


register = admin.site.register
register(EmailTemplate,    EmailTemplateAdmin)
register(MailingList,      MailingListAdmin)
register(EmailRecipient,   RecipientAdmin)
register(EmailCampaign,    EmailCampaignAdmin)
register(EmailSending,     EmailSendingAdmin)
register(LightWeightEmail, LightWeightEmailAdmin)
