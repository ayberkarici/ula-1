from django.db import models



class City(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    population = models.IntegerField()
    livability_score = models.FloatField()
    image = models.ImageField(upload_to='city_images', null=True, blank=True)
    
    def __str__(self):
        return self.name
    
class LivabilityFactor(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    def __str__(self):
        return self.name
    
class UserFeedback(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    factor = models.ForeignKey(LivabilityFactor, on_delete=models.CASCADE)
    score = models.IntegerField()
    comment = models.TextField()
    
    def __str__(self):
        return f"{self.city.name} - {self.factor.name}"



