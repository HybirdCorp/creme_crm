# -*- coding: utf-8 -*-

from .campaign import AbstractEmailCampaign, EmailCampaign  # NOQA
from .mail import AbstractEntityEmail, EntityEmail, _Email  # NOQA
from .mailing_list import AbstractMailingList, MailingList  # NOQA
from .recipient import EmailRecipient  # NOQA
from .sending import EmailSending, LightWeightEmail  # NOQA
from .signature import EmailSignature  # NOQA
from .template import AbstractEmailTemplate, EmailTemplate  # NOQA
