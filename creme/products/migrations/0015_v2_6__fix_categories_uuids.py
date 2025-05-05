from django.db import migrations

PRODUCTS_CATEGORY_UUIDS = [
    (1, '3fb0ef3c-45d0-40bd-8e71-b1ab49fca8d3'),  # Jewelry
    (2, '74c91fab-d671-4054-984f-ba395d7dffcb'),  # Mobile
    (3, '69084c8f-068c-41e3-80e3-42ed312e9815'),  # Electronics
    (4, '213e14fa-bda1-4850-a22d-d3e6bb832a98'),  # Travels
    (5, '684f4e8a-aad8-4eb5-980c-fbb8fc28776e'),  # Vehicle
    (6, '8ef405ac-9109-4ea6-94eb-f068b33c617d'),  # Games & Toys
    (7, '14474aee-9ba7-4a0e-816e-e19bab639af9'),  # Clothes
]

PRODUCTS_SUBCATEGORY_UUIDS = [
    (1,  '2d6555fe-4c25-4098-8128-25395cf2c10b'),  # Ring
    (2,  'c160d58f-6878-4dd6-87d6-ee05db310f3a'),  # Bracelet
    (3,  '83b79894-122e-4212-bf18-929573f57c74'),  # Necklace
    (4,  '6514cb2a-ee59-4abf-bdef-92488fac3a42'),  # Earrings
    (5,  '2abfa34f-d30f-4629-9a45-8cd63ce0a362'),  # Iphone
    (6,  '4c55bae2-44d3-44ca-aade-e8433339f2aa'),  # Blackberry
    (7,  '5fc12768-bc62-4412-a9d4-91aa9967bfac'),  # Samsung
    (8,  '62e549a1-f132-4c82-a836-e8d94ee8b29b'),  # Android
    (9,  '25f7c8db-a0d1-42af-a342-97727a2229fd'),  # Laptops
    (10, '6e3c21d1-f81e-492c-b2ce-da1fbc46727f'),  # Desktops
    (11, '13463841-90df-4036-b830-62ad75668213'),  # Tablet
    (12, '3a14d682-77b5-43b7-9b9c-8db9bcd44b0d'),  # Notebook
    (13, '79c7d28f-eed2-4565-9815-1d1887f3ccaf'),  # Fly
    (14, '9812ff36-b3f3-4670-8d4a-b8e9c916bf0d'),  # Hotel
    (15, '15e6f072-bd3e-4591-9963-be2af1888520'),  # Weekend
    (16, 'abaca40b-51c9-49c1-95c4-ba93e51bdc40'),  # Rent
    (17, '7c3492c1-7621-456f-a849-1fc6af829435'),  # Car
    (18, '1f5664c6-2a88-42d0-a554-e271dbe7fd84'),  # Bike
    (19, '669d7604-0d71-48b1-aa4e-6ca52f8923f8'),  # Boat
    (20, '886757aa-e019-4683-b83b-942ca9798e0b'),  # Plane
    (21, 'f5f5efc4-b03e-47b9-b485-f85dfb1a2630'),  # Boys
    (22, '39d811f7-707b-4419-8750-b15179d5b3eb'),  # Girls
    (23, 'd92fd9d0-a8cd-4d6e-9d8c-24037a2121fe'),  # Teens
    (24, 'dc8d1368-55d7-4abc-80c2-28ba1d3d1d3b'),  # Babies
    (25, '01109ac2-e539-45fd-a2a8-b3fff7992933'),  # Men
    (26, 'eaf8bc61-e1a1-4181-a679-84c606037922'),  # Women
    (27, 'ecf095f8-f3a7-4271-921c-81b1dff714a6'),  # Kids
    (28, 'ba170185-892e-400a-b212-1810fc86f204'),  # Babies
]

def _fix_uuids(apps, model_name, ids_to_uuids):
    filter_instances = apps.get_model('products', model_name).objects.filter
    count = 0

    for old_id, new_uuid in ids_to_uuids:
        instance = filter_instances(id=old_id).first()

        if instance is not None:
            old_uuid = str(instance.uuid)

            if old_uuid != new_uuid:
                instance.extra_data['old_uuid'] = old_uuid
                instance.uuid = new_uuid
                instance.save()

                count += 1

    if count:
        print(
            f'The UUID of {count} "{model_name}" have been modified '
            f'(old ones are stored in meta_data).'
        )

def fix_categories_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='Category',
        ids_to_uuids=PRODUCTS_CATEGORY_UUIDS,
    )

def fix_sub_categories_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='SubCategory',
        ids_to_uuids=PRODUCTS_SUBCATEGORY_UUIDS,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_categories_uuids),
        migrations.RunPython(fix_sub_categories_uuids),
    ]
