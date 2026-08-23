import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("qa", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="status",
            field=models.CharField(
                choices=[("processing", "Processing"), ("ready", "Ready"), ("failed", "Failed")],
                default="processing",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="owner",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="documents",
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
    ]