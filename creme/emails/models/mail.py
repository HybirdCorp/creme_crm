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

import poplib
import email
import re

from datetime import datetime
from email.mime.image import MIMEImage
from itertools import chain
from logging import error, debug
from os.path import join, basename

from django.db.models import (PositiveIntegerField, PositiveSmallIntegerField, CharField,
                              TextField, DateTimeField, ForeignKey, ManyToManyField)
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError

from creme_core.models import CremeModel, CremeEntity

from emails.utils import generate_id, get_unicode_decoded_str

from persons.models import MailSignature

from documents.models import Document

from creme_settings import (CREME_GET_EMAIL_SERVER,
                            CREME_GET_EMAIL_USERNAME,
                            CREME_GET_EMAIL_PASSWORD,
                            CREME_GET_EMAIL_PORT,
                            CREME_GET_EMAIL_SSL,
                            CREME_GET_EMAIL_SSL_KEYFILE,
                            CREME_GET_EMAIL_SSL_CERTFILE)

MAIL_STATUS_SENT         = 1
MAIL_STATUS_NOTSENT      = 2
MAIL_STATUS_SENDINGERROR = 3
MAIL_STATUS_SYNCHRONIZED = 4
MAIL_STATUS_SYNCHRONIZED_SPAM = 5
MAIL_STATUS_SYNCHRONIZED_WAITING = 6

MAIL_STATUS = {
                MAIL_STATUS_SENT:                 _(u"Envoyé"),
                MAIL_STATUS_NOTSENT:              _(u"Non envoyé"),
                MAIL_STATUS_SENDINGERROR:         _(u"Erreur d'envoi"),
                MAIL_STATUS_SYNCHRONIZED:         _(u"Synchronisé"),
                MAIL_STATUS_SYNCHRONIZED_SPAM:    _(u"Synchronisé - Marqué comme SPAM"),
                MAIL_STATUS_SYNCHRONIZED_WAITING: _(u"Synchronisé - Non traité"),
              }

ID_LENGTH = 32

class _Email(CremeModel):
    """
    id is a unique generated string in order to avoid stats hacking.
    """
#    id             = CharField(_(u'Identifiant du mail'), primary_key=True, max_length=ID_LENGTH)
#    sending        = ForeignKey(EmailSending, null=True, verbose_name=_(u"Envoi associé"), related_name='mails_set')

    reads          = PositiveIntegerField(_(u'Nombre de lecture(s)'), blank=True, null=True, default=0)
    status         = PositiveSmallIntegerField(_(u'Statut'))

    sender         = CharField(_(u'Émetteur'), max_length=100)
    recipient      = CharField(_(u'Destinataire'), max_length=100)
    #cc             = CharField(_(u'cc'), max_length=100)
    subject        = CharField(_(u'Sujet'), max_length=100, blank=True, null=True)
    body_html      = TextField()
    body           = TextField()
    sending_date   = DateTimeField(_(u"Date d'envoi"), blank=True, null=True)
    reception_date = DateTimeField(_(u"Date de reception"), blank=True, null=True)
    signature      = ForeignKey(MailSignature, verbose_name=_(u'Signature'), blank=True, null=True) ##merge with body ????
    attachments    = ManyToManyField(Document, verbose_name=_(u'Fichiers attachés'))

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
            error('Mail already sent to the recipient')
            return

        body = mail.body
        #body += '<img src="http://minimails.hybird.org/emails/stats/bbm/%s" />' % mail.ident

        signature = mail.signature
        signature_images = signature.images.all() if signature else ()

        if signature:
            body += signature.corpse #'corpse' berkkkkk

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
    identifier = CharField(_(u'Identifiant du mail'), unique=True, max_length=ID_LENGTH, null=False, blank=False, default=generate_id)

    class Meta:
        app_label = "emails"
        verbose_name = _(u'Courriel')
        verbose_name_plural = _(u'Courriels')

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

    @staticmethod
    def fetch_mails(user_id):
        client = None
        try:
            if CREME_GET_EMAIL_SSL:
                client = poplib.POP3_SSL(CREME_GET_EMAIL_SERVER, CREME_GET_EMAIL_PORT, CREME_GET_EMAIL_SSL_KEYFILE, CREME_GET_EMAIL_SSL_CERTFILE)
            else:
                client = poplib.POP3(CREME_GET_EMAIL_SERVER, CREME_GET_EMAIL_PORT)
            client.user(CREME_GET_EMAIL_USERNAME)
            client.pass_(CREME_GET_EMAIL_PASSWORD)
        except Exception, e:#TODO: Define better exception
            debug("Pop connection error : %s", e)
            if client is not None:
                client.quit()
            return []

        message_count, mailbox_size = client.stat()

#        result_list = []
        response, messages, total_size = client.list()

        getaddresses = email.utils.getaddresses
#        parsedate    = email.utils.parsedate

        for msg_infos in messages:
            mail = EntityEmail()
            mail.status = MAIL_STATUS_SYNCHRONIZED_WAITING

            message_number, message_size = msg_infos.split(' ')
            r, raw_message_lines, message_size = client.retr(message_number)

            out_str = '\n'.join(raw_message_lines)
            out_str = re.sub(r'\r(?!=\n)', '\r\n', out_str)

            email_message = email.message_from_string(out_str)
            get_all = email_message.get_all

            to_emails   = [addr for name, addr in getaddresses(get_all('to', []))]
            from_emails = [addr for name, addr in getaddresses(get_all('from', []))]
            cc_emails   = [addr for name, addr in getaddresses(get_all('cc', []))]

            subjects    = get_all('subject', [])

#            dates = []
#            for d in get_all('date', []):
#                if d is not None:
#                    dates.append(datetime(*parsedate(d)[:-3]))

            body_html = u''
            body = u''
            # CONTENT HTML / PLAIN
            if email_message.is_multipart():
                for part in email_message.walk():
                    encodings = set(part.get_charsets()) - set([None])

                    mct = part.get_content_maintype()
                    if mct != 'text':
                        #TODO: Gerer les fichiers attachés
                        continue
                    cst = part.get_content_subtype()
                    if cst == 'html':
                        body_html = get_unicode_decoded_str(part.get_payload(decode=True), encodings)
                    elif cst == 'plain':
                        body = get_unicode_decoded_str(part.get_payload(decode=True), encodings)
            else:
                #print 'Payload : ', message.get_payload(decode=True)
                encodings = set(email_message.get_charsets()) - set([None])

                cst = email_message.get_content_subtype()
                if cst == 'plain':
                    body = get_unicode_decoded_str(email_message.get_payload(decode=True), encodings)
                elif cst == 'html':
                    body_html = body = get_unicode_decoded_str(email_message.get_payload(decode=True), encodings)

            mail.body      = body.encode('utf-8')
            mail.body_html = body_html.encode('utf-8')
            mail.sender    = u', '.join(chain(from_emails, cc_emails))
            mail.recipient = u', '.join(to_emails)
            mail.subject   = u', '.join(subjects)
            mail.user_id   = user_id
            mail.genid_n_save()
#            result_list.append(mail)

            # We delete the mail from the server when treated
#            client.dele(message_number)#TODO: Don't forget to uncomment

        client.quit()

#        for mail in Email.objects.filter(Q(status=MAIL_STATUS_SYNCHRONISED_SPAM) | Q(status=MAIL_STATUS_SYNCHRONISED_WAITING)):
##            if mail not in result_list:
##                result_list.append(mail)
#            result_list.append(mail)
#
##        return result_list
#        return set(result_list)
        return message_count
