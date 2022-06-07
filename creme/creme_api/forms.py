from creme.creme_core.forms import CremeModelForm

from .models import Application


class ApplicationForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = Application
        fields = [
            "name",
            "enabled",
            "token_duration",
        ]
