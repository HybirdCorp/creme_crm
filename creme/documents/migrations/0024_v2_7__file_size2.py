from django.db import migrations

BULK_SIZE = 2000
SHOW_PROGRESS = False

def fill_sizes(apps, schema_editor):
    model = apps.get_model('documents', 'Document')
    queryset = model.objects.filter(file_size=None).order_by("pk").only('pk', "filedata")

    if SHOW_PROGRESS:
        total = queryset.count()

    def fetch_documents(previous_batch_last_pk=None):
        qs = queryset.all()
        if previous_batch_last_pk:
            qs = qs.filter(pk__gt=previous_batch_last_pk)
        return list(qs[:BULK_SIZE])

    documents = fetch_documents()

    if SHOW_PROGRESS:
        count = 0
        print()

    while documents:
        for document in documents:
            try:
                document.file_size = document.filedata.size
            except FileNotFoundError:
                document.file_size = 0

        model.objects.bulk_update(documents, ["file_size"])

        if SHOW_PROGRESS:
            count += len(documents)
            percent = count / total * 100
            print(f"Processed {percent:.2f}%", end="\r", flush=True)

        documents = fetch_documents(previous_batch_last_pk=documents[-1].pk)


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0023_v2_7__file_size1'),
    ]

    operations = [
        migrations.RunPython(fill_sizes, migrations.RunPython.noop),
    ]
