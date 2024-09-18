from django.db import models


# NB: see
# https://docs.djangoproject.com/en/5.1/releases/5.0/#migrating-existing-uuidfield-on-mariadb-10-7
class Char32UUIDField(models.UUIDField):
    def db_type(self, connection):
        return "char(32)"

    def get_db_prep_value(self, value, connection, prepared=False):
        value = super().get_db_prep_value(value, connection, prepared)
        if value is not None:
            value = value.hex

        return value
