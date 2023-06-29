# The RFC 2822 (http://www.faqs.org/rfcs/rfc2822.html) does not define a maximum
# length for the subject of an email ; several email services truncate them
# (130 chars, 255 chars...). 100 is the historical length in Creme.
# TODO: increase to 128/256/... ? use TextFields instead of CharFields ?
SUBJECT_LENGTH = 100

REL_SUB_MAIL_RECEIVED = 'email-subject_mail_received'
REL_OBJ_MAIL_RECEIVED = 'email-object_mail_received'

REL_SUB_MAIL_SENT = 'email-subject_mail_sended'
REL_OBJ_MAIL_SENT = 'email-object_mail_sended'

REL_SUB_RELATED_TO = 'email-subject_related_to'
REL_OBJ_RELATED_TO = 'email-object_related_to'

DEFAULT_HFILTER_MAILINGLIST = 'emails-hf_mailinglist'
DEFAULT_HFILTER_CAMPAIGN    = 'emails-hf_campaign'
DEFAULT_HFILTER_TEMPLATE    = 'emails-hf_template'
DEFAULT_HFILTER_EMAIL       = 'emails-hf_email'

UUID_FOLDER_CAT_EMAILS = '7161caaa-013b-4c32-ac19-19da7cee4561'
