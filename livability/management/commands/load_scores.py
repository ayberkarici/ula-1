import os
import pandas as pd
from django.core.management.base import BaseCommand
from livability.models import CityLivabilityScore, Category

class Command(BaseCommand):
    help = "Loads city-category scores from Excel files"

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help="Path to the directory containing Excel files")

    def handle(self, *args, **kwargs):
        directory = kwargs['directory']
        files = [f for f in os.listdir(directory) if f.endswith('.xlsx')]

        for file in files:
            category_name = os.path.splitext(file)[0].strip()  # e.g. "Güvenlik"
            path = os.path.join(directory, file)

            try:
                df = pd.read_excel(path)
                if df.shape[1] < 2:
                    self.stdout.write(self.style.WARNING(f"{file} skipped (not enough columns)."))
                    continue

                category_obj, _ = Category.objects.get_or_create(name=category_name)

                # delete old data for this category
                CityLivabilityScore.objects.filter(category=category_obj).delete()

                for _, row in df.iterrows():
                    city = row[0]
                    value = row[1]
                    if pd.isnull(city) or pd.isnull(value):
                        continue
                    CityLivabilityScore.objects.create(
                        city_name=city.strip(),
                        category=category_obj,
                        value=float(value)
                    )
                self.stdout.write(self.style.SUCCESS(f"{file} loaded successfully."))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to load {file}: {e}"))