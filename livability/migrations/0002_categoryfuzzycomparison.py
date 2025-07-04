# Generated by Django 4.2.3 on 2025-05-11 19:33

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('livability', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryFuzzyComparison',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category1', models.CharField(max_length=100)),
                ('category2', models.CharField(max_length=100)),
                ('value_l', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0)])),
                ('value_m', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0)])),
                ('value_u', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Category Fuzzy Comparison',
                'verbose_name_plural': 'Category Fuzzy Comparisons',
                'unique_together': {('category1', 'category2', 'user')},
            },
        ),
    ]
