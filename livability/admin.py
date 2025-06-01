from django.contrib import admin
from .models import CityLivabilityScore

@admin.register(CityLivabilityScore)
class CityLivabilityScoreAdmin(admin.ModelAdmin):
    list_display = ("city_name", "category", "value", "uploaded_at")
    list_filter = ("category", "uploaded_at")
    search_fields = ("city_name", "category")