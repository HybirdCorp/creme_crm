from creme import billing

from .custom_forms import BTEMPLATE_CREATION_CFORM

# TODO: rework 'recurrents' to use apps.py & use spawner_registry
#       (currently the loading order avoids using 'spawner_registry')
TemplateBase = billing.get_template_base_model()
to_register = (
    (billing.get_invoice_model(),     TemplateBase, BTEMPLATE_CREATION_CFORM),
    (billing.get_quote_model(),       TemplateBase, BTEMPLATE_CREATION_CFORM),
    (billing.get_sales_order_model(), TemplateBase, BTEMPLATE_CREATION_CFORM),
    (billing.get_credit_note_model(), TemplateBase, BTEMPLATE_CREATION_CFORM),
)
