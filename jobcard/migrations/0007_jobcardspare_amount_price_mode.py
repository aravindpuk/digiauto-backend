from django.db import migrations, models
from django.db.models import DecimalField, ExpressionWrapper, F


def populate_line_amounts(apps, schema_editor):
    JobCardSpare = apps.get_model("jobcard", "JobCardSpare")
    JobCardSpare.objects.update(
        amount=ExpressionWrapper(
            F("mrp") * F("quantity"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )


class Migration(migrations.Migration):
    dependencies = [("jobcard", "0006_jobcard_delivered_at")]

    operations = [
        migrations.AddField(
            model_name="jobcardspare",
            name="amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="jobcardspare",
            name="price_mode",
            field=models.CharField(
                choices=[("unit", "Per unit"), ("total", "Line total")],
                default="unit",
                max_length=5,
            ),
        ),
        migrations.RunPython(populate_line_amounts, migrations.RunPython.noop),
    ]
