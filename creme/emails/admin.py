# -*- coding: utf-8 -*-

from django.contrib import admin

from emails.models import *


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'body', 'use_rte', 'signature')


class MailingListAdmin(admin.ModelAdmin):
    list_display = ('name',)


class EmailAdmin(admin.ModelAdmin):
    list_display = ('id', 'sending', 'reads', 'status', 'sender', 'recipient',
                    'subject', 'body', 'sending_date', 'signature')


class RecipientAdmin(admin.ModelAdmin):
    list_display = ('ml', 'address')


class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ('name',)


class EmailSendingAdmin(admin.ModelAdmin):
    list_display = ('sender', 'campaign', 'type', 'sending_date', 'state', 'subject', 'body', 'signature')


register = admin.site.register

register(EmailTemplate, EmailTemplateAdmin)
register(MailingList, MailingListAdmin)
register(EmailRecipient, RecipientAdmin)
register(EmailCampaign, EmailCampaignAdmin)
register(EmailSending, EmailSendingAdmin)
register(Email, EmailAdmin)
