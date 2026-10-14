import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from vehicle.models import VehicleMake, VehicleModel


class Command(BaseCommand):
    help = "Import vehicle makes and models from vehicle_model&make_list.csv."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            dest="csv_path",
            type=Path,
            default=Path(__file__).resolve().parents[3]
            / "vehicle_model&make_list.csv",
            help="Path to the vehicle catalog CSV file.",
        )

    @transaction.atomic
    def handle(self, *args, csv_path, **options):
        try:
            source = csv_path.open(encoding="utf-8-sig", newline="")
        except OSError as exc:
            raise CommandError(f"Could not open CSV file {csv_path}: {exc}") from exc

        makes_created = 0
        models_created = 0
        rows_skipped = 0

        with source:
            reader = csv.DictReader(source)
            if not reader.fieldnames or not {"make", "model"}.issubset(
                {field.strip().lower() for field in reader.fieldnames}
            ):
                raise CommandError("CSV must have 'make' and 'model' columns.")

            # Normalize header names but only read make and model. Any other
            # columns (including vehicle_type/passenger_car) are ignored.
            reader.fieldnames = [field.strip().lower() for field in reader.fieldnames]
            for line_number, row in enumerate(reader, start=2):
                make_name = (row.get("make") or "").strip()
                model_name = (row.get("model") or "").strip()
                if not make_name or not model_name:
                    rows_skipped += 1
                    self.stderr.write(
                        f"Skipping CSV line {line_number}: make or model is empty."
                    )
                    continue

                make, make_created = VehicleMake.objects.get_or_create(name=make_name)
                makes_created += int(make_created)
                _, model_created = VehicleModel.objects.get_or_create(
                    name=model_name, fkMaker=make
                )
                models_created += int(model_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete: {makes_created} makes and {models_created} "
                f"models created; {rows_skipped} rows skipped."
            )
        )
