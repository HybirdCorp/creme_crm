from rest_framework import serializers

from creme import persons

Contact = persons.get_contact_model()


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            'id',
            'last_name',
            'first_name',
            'email',
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
        }
