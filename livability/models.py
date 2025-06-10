from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name




class CityLivabilityScore(models.Model):
    city_name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)  # e.g., 'Güvenlik', 'Eğitim'
    value = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('city_name', 'category')
        verbose_name = 'City Livability Score'
        verbose_name_plural = 'City Livability Scores'

    def __str__(self):
        return f"{self.city_name} - {self.category.name}: {self.value}"
    


# Fuzzy pairwise comparison model for F-AHP weighting
class CategoryFuzzyComparison(models.Model):
    category1 = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='fuzzy_comp_1')
    category2 = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='fuzzy_comp_2')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Fuzzy values: Lower (L), Medium (M), Upper (U)
    value_l = models.FloatField(validators=[MinValueValidator(0.0)])
    value_m = models.FloatField(validators=[MinValueValidator(0.0)])
    value_u = models.FloatField(validators=[MinValueValidator(0.0)])

    # Consistency ratio for the fuzzy comparison
    consistency_ratio = models.FloatField(null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("category1", "category2", "user")
        verbose_name = "Category Fuzzy Comparison"
        verbose_name_plural = "Category Fuzzy Comparisons"

    def __str__(self):
        return f"{self.category1.name} vs {self.category2.name} ({self.user})"


class FuzzyWeight(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    weight_l = models.FloatField(validators=[MinValueValidator(0.0)])
    weight_m = models.FloatField(validators=[MinValueValidator(0.0)])
    weight_u = models.FloatField(validators=[MinValueValidator(0.0)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('category', 'user')
        verbose_name = "Fuzzy Weight"
        verbose_name_plural = "Fuzzy Weights"

    def __str__(self):
        return f"{self.category.name} weight for {self.user.username if self.user else 'System'}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    city = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.username} - {self.city}"


class UserTestResult(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    city = models.CharField(max_length=100)
    result_json = models.JSONField()  # {"city_name": score, ...}
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.city} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class OverallCityRanking(models.Model):
    city_name = models.CharField(max_length=100, unique=True)
    avg_score = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.city_name}: {self.avg_score:.4f}"