# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import os
import poplib
import email
import re

from datetime import datetime
from email.mime.image import MIMEImage
from itertools import chain
from logging import error, debug
from os.path import join, basename

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import (PositiveIntegerField, PositiveSmallIntegerField, CharField,
                              TextField, DateTimeField, ForeignKey, ManyToManyField)
from django.utils.translation import ugettext_lazy as _, ugettext
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError
#from django.utils.safestring import mark_safe
#from django.forms.util import flatatt
from django.template.loader import render_to_string

from creme_core.models import CremeModel, CremeEntity, Relation
from creme_core.views.file_handling import handle_uploaded_file

from crudity.frontends.pop import pop_frontend

from documents.models import Document, Folder, FolderCategory
from documents.constants import REL_OBJ_RELATED_2_DOC

from emails.utils import generate_id#, get_unicode_decoded_str
from emails.models import EmailSignature


MAIL_STATUS_SENT                    = 1
MAIL_STATUS_NOTSENT                 = 2
MAIL_STATUS_SENDINGERROR            = 3
MAIL_STATUS_SYNCHRONIZED            = 4
MAIL_STATUS_SYNCHRONIZED_SPAM       = 5
MAIL_STATUS_SYNCHRONIZED_WAITING    = 6

MAIL_STATUS = {
                MAIL_STATUS_SENT:                 _(u"Sent"),
                MAIL_STATUS_NOTSENT:              _(u"Not sent"),
                MAIL_STATUS_SENDINGERROR:         _(u"Sending error"),
                MAIL_STATUS_SYNCHRONIZED:         _(u"Synchronized"),
                MAIL_STATUS_SYNCHRONIZED_SPAM:    _(u"Synchronized - Marked as SPAM"),
                MAIL_STATUS_SYNCHRONIZED_WAITING: _(u"Synchronized - Untreated"),
              }

ID_LENGTH = 32

class _Email(CremeModel):
    reads          = PositiveIntegerField(_(u'Number of reads'), blank=True, null=True, default=0)
    status         = PositiveSmallIntegerField(_(u'Status'), default=MAIL_STATUS_NOTSENT)

    sender         = CharField(_(u'Sender'), max_length=100)
    recipient      = CharField(_(u'Recipient'), max_length=100)
    #cc             = CharField(_(u'cc'), max_length=100)
    subject        = CharField(_(u'Subject'), max_length=100, blank=True, null=True)
    body_html      = TextField()
    body           = TextField()
    sending_date   = DateTimeField(_(u"Sending date"), blank=True, null=True)
    reception_date = DateTimeField(_(u"Reception date"), blank=True, null=True)
    signature      = ForeignKey(EmailSignature, verbose_name=_(u'Signature'), blank=True, null=True) ##merge with body ????
    attachments    = ManyToManyField(Document, verbose_name=_(u'Attachments'))

    class Meta:
        abstract = True
        app_label = "emails"

    def __unicode__(self):
        return u"Mail<from: %s> <to: %s> <sent: %s> <id: %s>" % (self.sender, self.recipient, self.sending_date, self.id)

    def get_status_str(self):
        return MAIL_STATUS[self.status]

    def get_body(self):
        return self.body

    #TODO: factorise with EmailSending.send_mails()
    def send(self):
        mail = self

        img_cache = {}

        if mail.status == MAIL_STATUS_SENT:
            error('Mail already sent to the recipient') #i18n ?
            return

        body = mail.body_html or mail.body
        #body += '<img src="http://minimails.hybird.org/emails/stats/bbm/%s" />' % mail.ident

        signature = mail.signature
        signature_images = signature.images.all() if signature else ()

        if signature:
            body += signature.body

            for signature_img in signature_images:
                body += '<img src="cid:img_%s" /><br/>' % signature_img.id

        msg = EmailMultiAlternatives(mail.subject, body, mail.sender, [mail.recipient])
        msg.attach_alternative(body, "text/html")

        for signature_img in signature_images:
            name = signature_img.image.name
            mime_img = img_cache.get(name)

            if mime_img is None:
                try:
                    f = open(join(settings.MEDIA_ROOT, name), 'rb')
                    mime_img = MIMEImage(f.read())
                    mime_img.add_header('Content-ID','<img_%s>' % signature_img.id)
                    mime_img.add_header('Content-Disposition', 'inline', filename=basename(f.name))
                    f.close()
                except Exception, e: #better exception ???
                    error('Sending: exception when adding image signature: %s', e)
                    continue
                else:
                    img_cache[name] = mime_img

            msg.attach(mime_img)

        #TODO: use a cache to not open the sames files for each mail ?????
        for attachment in mail.attachments.all():
            msg.attach_file(join(settings.MEDIA_ROOT, attachment.filedata.name))

        try:
            msg.send()
        except Exception, e: #better exception ??
            error("Sending: error during sending mail.")
            mail.status = MAIL_STATUS_SENDINGERROR
        else:
            mail.status = MAIL_STATUS_SENT
            mail.sending_date = datetime.now()

        mail.save()
        debug("Mail sent to %s", mail.recipient)


class EntityEmail(_Email, CremeEntity):
    identifier = CharField(_(u'Email ID'), unique=True, max_length=ID_LENGTH, null=False, blank=False, default=generate_id)#TODO: lambda for this

    class Meta:
        app_label = "emails"
        verbose_name = _(u'Email')
        verbose_name_plural = _(u'Emails')

    def genid_n_save(self):
        #BEWARE: manage manually
        while True:
            try:
                self.identifier = generate_id()
                self.save(force_insert=True)
            except IntegrityError:  #a mail with this id already exists
                debug('Mail id already exists: %s', self.identifier)
                self.pk = None
            else:
                break

    def __unicode__(self):
        return u"Mail <de: %s> <à: %s><status: %s>" % (self.sender, self.recipient, self.get_status_str())

    def get_absolute_url(self):
        return u"/emails/mail/%s" % self.pk

    @staticmethod
    def get_lv_absolute_url():
        return "/emails/mails"

    @staticmethod
    def create_n_send_mail(sender, recipient, subject, user_pk, body_html=u"", signature=None, attachments=None):
        email           = EntityEmail()
        email.sender    = sender
        email.recipient = recipient
        email.subject   = subject
        email.body_html = body_html
        email.signature = signature
        email.user_id   = user_pk
        email.genid_n_save()
        if attachments:
            email.attachments = attachments
            email.save()
        email.send()
        return email

    def _pre_save_clone(self, source):
        self.genid_n_save()
