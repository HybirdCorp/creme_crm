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
from django.utils.safestring import mark_safe
from django.forms.util import flatatt
from django.template.loader import render_to_string

from creme_core.models import CremeModel, CremeEntity, Relation
from creme_core.views.file_handling import handle_uploaded_file

from emails.utils import generate_id, get_unicode_decoded_str

from persons.models import MailSignature

from documents.models import Document, Folder, FolderCategory
from documents.constants import REL_OBJ_RELATED_2_DOC

from creme_settings import (CREME_GET_EMAIL_SERVER,
                            CREME_GET_EMAIL_USERNAME,
                            CREME_GET_EMAIL_PASSWORD,
                            CREME_GET_EMAIL_PORT,
                            CREME_GET_EMAIL_SSL,
                            CREME_GET_EMAIL_SSL_KEYFILE,
                            CREME_GET_EMAIL_SSL_CERTFILE)

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
    """
    id is a unique generated string in order to avoid stats hacking.
    """
#    id             = CharField(_(u'Identifiant du mail'), primary_key=True, max_length=ID_LENGTH)
#    sending        = ForeignKey(EmailSending, null=True, verbose_name=_(u"Envoi associé"), related_name='mails_set')

    reads          = PositiveIntegerField(_(u'Number of reads'), blank=True, null=True, default=0)
    status         = PositiveSmallIntegerField(_(u'Status'))

    sender         = CharField(_(u'Sender'), max_length=100)
    recipient      = CharField(_(u'Recipient'), max_length=100)
    #cc             = CharField(_(u'cc'), max_length=100)
    subject        = CharField(_(u'Subject'), max_length=100, blank=True, null=True)
    body_html      = TextField()
    body           = TextField()
    sending_date   = DateTimeField(_(u"Sending date"), blank=True, null=True)
    reception_date = DateTimeField(_(u"Reception date"), blank=True, null=True)
    signature      = ForeignKey(MailSignature, verbose_name=_(u'Signature'), blank=True, null=True) ##merge with body ????
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
    identifier = CharField(_(u'Email ID'), unique=True, max_length=ID_LENGTH, null=False, blank=False, default=generate_id)

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

    def get_delete_absolute_url(self):
        return u"/emails/entitymail/delete/%s" % self.id

    def get_entity_actions(self):
        ctx = {
            'actions' : [
                    (self.get_absolute_url(),        ugettext(u"See"),    mark_safe(flatatt({})), "%s/images/view_16.png" % settings.MEDIA_URL),
                    (self.get_delete_absolute_url(), ugettext(u"Delete"), mark_safe(flatatt({'class': 'confirm_delete'})), "%s/images/delete_16.png"  % settings.MEDIA_URL)
            ],
            'id': self.id,
        }
        return render_to_string("creme_core/frags/actions.html", ctx)
#        return u"""<a href="%s">Voir</a> | <a href="%s" onclick="creme.utils.confirmDelete(event, this);">Effacer</a>""" \
#                % (self.get_absolute_url(), self.get_delete_absolute_url())


    @staticmethod
    def fetch_mails(user_id_to_assign):
        client = None
        message_count = mailbox_size = 0
        response = messages = total_size = ""

        try:
            if CREME_GET_EMAIL_SSL:
                client = poplib.POP3_SSL(CREME_GET_EMAIL_SERVER, CREME_GET_EMAIL_PORT, CREME_GET_EMAIL_SSL_KEYFILE, CREME_GET_EMAIL_SSL_CERTFILE)
            else:
                client = poplib.POP3(CREME_GET_EMAIL_SERVER, CREME_GET_EMAIL_PORT)
            client.user(CREME_GET_EMAIL_USERNAME)
            client.pass_(CREME_GET_EMAIL_PASSWORD)

            message_count, mailbox_size = client.stat()
            response, messages, total_size = client.list()
        except Exception, e:#TODO: Define better exception
            debug("Pop connection error : %s", e)
            if client is not None:
                client.quit()
            return -1

        getaddresses = email.utils.getaddresses
        parsedate    = email.utils.parsedate

        attachment_paths = []

        current_user = User.objects.get(pk=user_id_to_assign)
        #TODO: create category in the populate ?? refactor
        folder_cat, is_cat_created  = FolderCategory.objects.get_or_create(name=u"Fichiers reçus par mail") #TODO: i18n

        folder, is_fold_created = Folder.objects.get_or_create(title=u'Fichiers de %s reçus par mail' % current_user.username, #TODO: i18n
                                                               user=current_user,
                                                               category=folder_cat)

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

            dates = []
            for d in get_all('date', []):
                if d is not None:
                    dates.append(datetime(*parsedate(d)[:-3]))

            body_html = u''
            body = u''
            # CONTENT HTML / PLAIN
            if email_message.is_multipart():
                for part in email_message.walk():
                    encodings = set(part.get_charsets()) - set([None])
                    payload   = part.get_payload(decode=True)

                    mct = part.get_content_maintype()
                    if mct == 'multipart':
                        continue

                    if mct != 'text':
                        filename = part.get_filename()
                        f = SimpleUploadedFile(filename, payload, content_type=part.get_content_type())
                        attachment_paths.append(handle_uploaded_file(f, path=['upload','emails','attachments'], name=filename))

                    else:
                        cst = part.get_content_subtype()
                        content = get_unicode_decoded_str(payload, encodings)
                        if cst == 'html':
                            body_html = content
                        elif cst == 'plain':
                            body = content
            else:
                encodings = set(email_message.get_charsets()) - set([None])

                cst = email_message.get_content_subtype()
                content = get_unicode_decoded_str(email_message.get_payload(decode=True), encodings)
                if cst == 'plain':
                    body = content
                elif cst == 'html':
                    body_html = body = content

            mail.body      = body.encode('utf-8')
            mail.body_html = body_html.encode('utf-8')
            mail.sender    = u', '.join(set(from_emails))
            mail.recipient = u', '.join(set(chain(to_emails, cc_emails)))
            mail.subject   = u', '.join(subjects)
            mail.user_id   = user_id_to_assign
            if dates:
                mail.reception_date = dates[0]
            mail.genid_n_save()

            for attachment_path in attachment_paths:
                doc = Document()
                doc.title = u"%s (mail %s)" % (attachment_path.rpartition(os.sep)[2], mail.id)
                doc.description = ugettext(u"Received with the mail %s") % (mail, )
                doc.filedata = attachment_path
                doc.user_id = user_id_to_assign
                doc.folder = folder
                doc.save()
                Relation.create(doc, REL_OBJ_RELATED_2_DOC, mail)

            # We delete the mail from the server when treated
            client.dele(message_number)

        client.quit()

        return message_count
