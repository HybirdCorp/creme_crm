# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from logging import error, debug
import os
import re
from time import sleep
from email.mime.image import MIMEImage
from os.path import join, basename
from pickle import loads

from django.db import IntegrityError
from django.db.models import (ForeignKey, DateTimeField, PositiveSmallIntegerField,
                              EmailField, CharField, TextField, ManyToManyField)
from django.core.mail import EmailMultiAlternatives, send_mail, SMTPConnection
from django.template import Template, Context
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, ugettext, activate

from creme_settings import CREME_EMAIL, CREME_EMAIL_PASSWORD, CREME_EMAIL_SERVER, CREME_EMAIL_PORT, CREME_EMAIL_USERNAME

from creme_core.models import CremeModel, CremeEntity

from emails.models.mail import _Email, ID_LENGTH, MAIL_STATUS_SENT, MAIL_STATUS_NOTSENT, MAIL_STATUS_SENDINGERROR
from emails.utils import generate_id

from documents.models import Document

from campaign import EmailCampaign
from signature import EmailSignature


SENDING_TYPE_IMMEDIATE = 1
SENDING_TYPE_DEFERRED  = 2

SENDING_TYPES = {
                    SENDING_TYPE_IMMEDIATE: _(u"Immediate"),
                    SENDING_TYPE_DEFERRED:  _(u"Deferred"),
                }

SENDING_STATE_DONE       = 1
SENDING_STATE_INPROGRESS = 2
SENDING_STATE_PLANNED    = 3
SENDING_STATE_ERROR      = 4

SENDING_STATES = {
                    SENDING_STATE_DONE:       _(u"Done"),
                    SENDING_STATE_INPROGRESS: _(u"In progress"),
                    SENDING_STATE_PLANNED:    _(u"Planned"),
                    SENDING_STATE_ERROR:      _(u"Error during sending"),
                 }


class EmailSending(CremeModel):
    sender        = EmailField(_(u"Sender address"), max_length=100)
    campaign      = ForeignKey(EmailCampaign, verbose_name=_(u'Related campaign'), related_name='sendings_set')
    type          = PositiveSmallIntegerField(verbose_name=_(u"Sending type"))
    sending_date  = DateTimeField(_(u"Sending date of emails"))
    state         = PositiveSmallIntegerField(verbose_name=_(u"Sending state"))

    subject     = CharField(_(u'Subject'), max_length=100)
    body        = TextField(_(u"Body"))
    signature   = ForeignKey(EmailSignature, verbose_name=_(u'Signature'), blank=True, null=True)
    attachments = ManyToManyField(Document, verbose_name=_(u'Attachments'))

    class Meta:
        app_label = "emails"
        verbose_name = _(u'Email campaign sending')
        verbose_name_plural = _(u'Email campaign sendings')

    def __unicode__(self):
        return ugettext(u"Sending of <%(campaign)s> on %(date)s") % {'campaign': self.campaign, 'date': self.sending_date}

    def delete(self):
        self.mails_set.all().delete() #use CremeModel delete() ??
        super(EmailSending, self).delete()

    def get_mails(self):
        return self.mails_set.all()

    def get_unsent_mails_count(self):
        return self.mails_set.filter(status__in=[MAIL_STATUS_NOTSENT, MAIL_STATUS_SENDINGERROR]).count()

    def get_state_str(self):
        return SENDING_STATES[self.state]

    def get_type_str(self):
        return SENDING_TYPES[self.type]

    def get_absolute_url(self):
        return self.campaign.get_absolute_url()

    def get_related_entity(self): #for generic views
        return self.campaign

    def send_mails(self):
#        mails = Email.objects.filter(sending=self)
        mails = LightWeightEmail.objects.filter(sending=self)

        mails_count  = 0
        SENDING_SIZE = getattr(settings, 'SENDING_SIZE', 40)
        SLEEP_TIME   = getattr(settings, 'SENDING_SLEEP_TIME', 2)

        img_cache = {}
        signature = self.signature
        signature_images = signature.images.all() if signature else ()

        img_pattern   = re.compile(r'<img.*src[\s]*[=]{1,1}["\']{1,1}(?P<img_src>[\d\w:/?\=.]*)["\']{1,1}')
        img_sources   = re.findall(img_pattern, self.body)
        imgs_to_embbed = []
        path_exists = os.path.exists
        path_join   = os.path.join
        MEDIA_ROOT  = settings.MEDIA_ROOT
        creme_entity_get = CremeEntity.objects.get

        body = self.body

        #Replacing image sources with embbeded images
        for src in img_sources:
            filename = basename(src)
            
            if not path_exists(path_join(MEDIA_ROOT, "upload", "images", filename)):
                activate(settings.LANGUAGE_CODE)
                err_msg = _("Emails in the sending of the campaign <%(campaign)s> on %(date)s weren't sent because the image <%(image)s> is no longer available in the template.") % {'campaign': self.campaign, 'date': self.sending_date, 'image': filename}
                send_mail(_('[CremeCRM] Campaign email sending error.'), err_msg, settings.EMAIL_HOST_USER, [self.campaign.user.email or settings.DEFAULT_USER_EMAIL], fail_silently=False)
                return SENDING_STATE_ERROR

            names = filename.split('_')
            if names:
                try:
                    img = creme_entity_get(pk=int(names[0])).get_real_entity()
                except (ValueError, CremeEntity.DoesNotExist):
                    continue
                else:
                    try:
                        img_file = img.image.file
                        img_file.open()
                        mime_img = MIMEImage(img_file.read())
                        mime_img.add_header('Content-ID','<img_%s>' % img.id)
                        mime_img.add_header('Content-Disposition', 'inline', filename=basename(img_file.name))
                        img_file.close()
                    except IOError:
                        continue
                    else:
                        imgs_to_embbed.append(mime_img)
                        body = body.replace(src, 'cid:img_%s' % img.id)

        body_template = Template(body)
        mails_statuses = []#Stack for checking if the sending succeed
        mails_statuses_append = mails_statuses.append

        #SMTPConnection is deprecated but with mail.get_connection() we can't specify other settings than django settings
        #TODO: Write a custom e-mail backend: http://docs.djangoproject.com/en/1.3/topics/email/#topic-custom-email-backend
        con = SMTPConnection(host=CREME_EMAIL_SERVER, port=CREME_EMAIL_PORT,
                             username=CREME_EMAIL_USERNAME, password=CREME_EMAIL_PASSWORD,
                             use_tls=True)
        
        for mail in mails:
            if mail.status == MAIL_STATUS_SENT:
                error('Mail already sent to the recipient')
                continue

            body = body_template.render(Context(loads(mail.body.encode('utf-8')) if mail.body else {}))
            #body += '<img src="http://minimails.hybird.org/emails/stats/bbm/%s" />' % mail.ident

            if signature:
                body += signature.body

                for signature_img in signature_images:
                    body += '<img src="cid:img_%s" /><br/>' % signature_img.id

            msg = EmailMultiAlternatives(self.subject, body, mail.sender, [mail.recipient], connection=con)
            msg.attach_alternative(body, "text/html")
            for img_to_embbed in imgs_to_embbed:
                msg.attach(img_to_embbed)

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
            for attachment in self.attachments.all():
                msg.attach_file(join(settings.MEDIA_ROOT, attachment.filedata.name))

            try:
                msg.send()
            except Exception, e: #better exception ??
                error("Sending: error during sending mail.")
                mail.status = MAIL_STATUS_SENDINGERROR
                mails_statuses_append(True)
            else:
                mail.status = MAIL_STATUS_SENT
                mails_count += 1
                mails_statuses_append(False)

            mail.save()
            debug("Mail sent to %s", mail.recipient)

            if mails_count > SENDING_SIZE:
                debug('Sending: waiting timeout')

                mails_count = 0
                sleep(SLEEP_TIME) #avoiding the mail to be classed as spam

        if all(mails_statuses):#If no mail have been sent the sending fail
            return SENDING_STATE_ERROR

class LightWeightEmail(_Email):
    """Used by campaigns.
    id is a unique generated string in order to avoid stats hacking.
    """
    id               = CharField(_(u'Email ID'), primary_key=True, max_length=ID_LENGTH)
    sending          = ForeignKey(EmailSending, null=True, verbose_name=_(u"Related sending"), related_name='mails_set') #TODO: null=True useful ??
    recipient_entity = ForeignKey(CremeEntity, null=True, related_name='received_lw_mails')

    class Meta:
        app_label = "emails"
        verbose_name = _(u'Email of campaign')
        verbose_name_plural = _(u'Emails of campaign')

    def get_body(self):
        if self.sending is None: #really useful ??? 'assert self.sending' instead ??
            return self.body

        try:
            body_template = Template(self.sending.body)
            return body_template.render(Context(loads(self.body.encode('utf-8')) if self.body else {}))
        except:#Pickle raise too much differents exceptions...Catch'em all ?
            return ""

    def get_related_entity(self): #for generic views
        return self.sending.campaign

    def genid_n_save(self):
        #BEWARE: manage manually
        while True:
            try:
                self.id = generate_id()
                self.save(force_insert=True)
            except IntegrityError:  #a mail with this id already exists
                debug('Mail id already exists: %s', self.id)
                self.pk = None
            else:
                break