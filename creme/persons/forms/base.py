# import warnings
#
#
# def _get_address_field_names(addr_fieldname):
#     warnings.warn('_get_address_field_names is deprecated.', DeprecationWarning)
#
#     from .address import _AuxiliaryAddressForm
#
#     form = _AuxiliaryAddressForm(prefix=addr_fieldname)
#     return [form.add_prefix(name) for name in form.base_fields]
