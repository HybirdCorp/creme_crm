REL_SUB_EMPLOYED_BY = 'persons-subject_employed_by'
REL_OBJ_EMPLOYED_BY = 'persons-object_employed_by'

REL_SUB_CUSTOMER_SUPPLIER = 'persons-subject_customer_supplier'
REL_OBJ_CUSTOMER_SUPPLIER = 'persons-object_customer_supplier'

REL_SUB_MANAGES = 'persons-subject_manages'
REL_OBJ_MANAGES = 'persons-object_manages'

REL_SUB_PROSPECT = 'persons-subject_prospect'
REL_OBJ_PROSPECT = 'persons-object_prospect'

REL_SUB_SUSPECT = 'persons-subject_suspect'
REL_OBJ_SUSPECT = 'persons-object_suspect'

REL_SUB_PARTNER = 'persons-subject_partner'
REL_OBJ_PARTNER = 'persons-object_partner'

REL_SUB_INACTIVE = 'persons-subject_inactive_customer'
REL_OBJ_INACTIVE = 'persons-object_inactive_customer'

REL_SUB_SUBSIDIARY = 'persons-subject_subsidiary'
REL_OBJ_SUBSIDIARY = 'persons-object_subsidiary'

REL_SUB_COMPETITOR = 'persons-subject_competitor'
REL_OBJ_COMPETITOR = 'persons-object_competitor'

FILTER_MANAGED_ORGA = 'persons-managed_organisations'
FILTER_CONTACT_ME   = 'persons-contact_me'

DEFAULT_HFILTER_CONTACT = 'persons-hf_contact'
DEFAULT_HFILTER_ORGA    = 'persons-hf_organisation'
DEFAULT_HFILTER_ORGA_CUSTOMERS = 'persons-hf_leadcustomer'

# TODO: move to 'populate.py'?
# NB: Beware you should probably not use these UUIDs to retrieve these
#     Contact/Organisation by their UUID (e.g. they could be deleted).
#     It's just a good thing that the first Contact/Organisation has the same
#     UUID on different DB (e.g. for importing/exporting data).
UUID_FIRST_CONTACT = '498b1986-5f70-409e-82c0-a8df1b2b9c39'
UUID_FIRST_ORGA    = 'bb93b21d-f7f1-46d7-a92f-7edda7b9ec2b'

UUID_DOC_CAT_IMG_ORGA    = 'b1486e1c-633a-4849-95bc-376119135dcd'
UUID_DOC_CAT_IMG_CONTACT = 'fad633b9-a270-4708-917e-1d73b2514f06'

# RGF_OWNED = 'persons-owned'
