from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("qa", "0004_chunk_page_number_document_display_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="otpcode",
            name="attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
