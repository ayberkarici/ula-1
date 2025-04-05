from django.shortcuts import render
from .models import City, LivabilityFactor, UserFeedback

def index(request):
    return render(request, 'livability/home.html')

def survey(request):
    cities = City.objects.all()
    factors = LivabilityFactor.objects.all()
    return render(request, 'livability/survey.html', {'cities': cities, 'factors': factors})

def city_ranking(request):
    cities = City.objects.order_by('-livability_score')
    return render(request, 'livability/city_ranking.html', {'cities': cities})

def feedback_form(request):
    factors = LivabilityFactor.objects.all()
    return render(request, 'livability/feedback_form.html', {'factors': factors})

def results(request):
    cities = [
        {"name": "İstanbul", "description": "İstanbul, tarihi dokusu, kültürel zenginliği ve ekonomik olanaklarıyla Türkiye'nin en yaşanabilir şehirlerinden biridir."},
        {"name": "Ankara", "description": "Ankara, modern yapıları, eğitim kurumları ve düzenli şehir planlaması ile öne çıkan bir başkenttir."},
        {"name": "İzmir", "description": "İzmir, sahil şeridi, ticaret potansiyeli ve sosyal yaşamı ile Türkiye'nin en yaşanabilir şehirlerinden biridir."},
        {"name": "Bursa", "description": "Bursa, sanayisi, yeşil doğası ve tarihî mirası ile öne çıkmaktadır."},
        {"name": "Antalya", "description": "Antalya, Akdeniz iklimi, turistik bölgeleri ve yaşam kalitesi ile dikkat çeker."}
    ]
    return render(request, "livability/results.html", {"cities": cities})

def more_results(request):
    cities = [
        {"name": "İstanbul", "environment": 85, "infrastructure": 78, "safety": 72, "healthcare": 90, "economy": 88},
        {"name": "Ankara", "environment": 80, "infrastructure": 82, "safety": 75, "healthcare": 88, "economy": 85},
        {"name": "İzmir", "environment": 75, "infrastructure": 80, "safety": 70, "healthcare": 85, "economy": 80},
        {"name": "Bursa", "environment": 78, "infrastructure": 76, "safety": 74, "healthcare": 83, "economy": 79},
        {"name": "Antalya", "environment": 82, "infrastructure": 75, "safety": 78, "healthcare": 86, "economy": 81}
    ]
    
    
    return render(request, "livability/more_results.html", {"cities": cities})