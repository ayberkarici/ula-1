from django.contrib.auth.forms import UserCreationForm
from .utils.fuzzy_ahp import apply_topsis, compute_fuzzy_weights, calculate_consistency_ratio, fuzzy_comparison_matrix
from django.shortcuts import render, redirect
from django.db.models import Avg
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from itertools import combinations
from livability.models import CityLivabilityScore, Category
from .models import CategoryFuzzyComparison, CityLivabilityScore, UserTestResult, OverallCityRanking
from .forms import CategoryFuzzyComparisonForm
from itertools import combinations
from django.http import JsonResponse
from .models import FuzzyWeight
import unicodedata
from django.db import transaction
from django.core.cache import cache

@login_required
def fahp_pairwise_ui(request):
    # Always start with a fresh comparison set
    CategoryFuzzyComparison.objects.filter(user=request.user).delete()
    categories = Category.objects.all().order_by("name")

    # Normalize + temiz isim listesi
    clean_names = [unicodedata.normalize("NFKC", c.name.strip()) for c in categories]
    all_pairs = list(combinations(sorted(clean_names), 2))
    print("All pairs:", all_pairs)

    category_map = {
        unicodedata.normalize("NFKC", c.name.strip()): c.id for c in categories
    }

    return render(request, "livability/fahp_cards.html", {
        "pairs": all_pairs,
        "category_map": category_map,
    })

def index(request):
    # İlk kullanıcı girişinde veri yükleme kontrolü
    if not cache.get('data_loaded'):
        from livability.models import CityLivabilityScore
        if not CityLivabilityScore.objects.exists():
            from .views import load_scores_from_project_folder
            with transaction.atomic():
                load_scores_from_project_folder(request)
            cache.set('data_loaded', True, timeout=None)
        else:
            cache.set('data_loaded', True, timeout=None)
    # Şehirlerin kategori önceliklerini infografik için hazırla
    from livability.models import UserProfile, FuzzyWeight, Category
    import json
    city_category_top = []
    all_cities = set(UserProfile.objects.values_list('city', flat=True))
    categories = list(Category.objects.all().order_by('name'))
    category_names = [cat.name for cat in categories]
    # For each city, aggregate user priorities
    for city in sorted(all_cities):
        users = UserProfile.objects.filter(city=city).values_list('user', flat=True)
        if not users:
            city_category_top.append({
                'city': city,
                'categories': [],
                'no_data': True
            })
            continue
        # category_id -> [defuzzified_weight, ...]
        cat_weights = {cat.id: [] for cat in categories}
        for user_id in users:
            for fw in FuzzyWeight.objects.filter(user_id=user_id):
                defuzz = (fw.weight_l + fw.weight_m + fw.weight_u) / 3
                cat_weights[fw.category_id].append(defuzz)
        # Calculate average for each category
        cat_avg = []
        for cat in categories:
            vals = cat_weights[cat.id]
            if vals:
                avg = sum(vals) / len(vals)
                cat_avg.append((cat.name, avg))
        if cat_avg:
            # Sort by avg descending, take top 3
            cat_avg = sorted(cat_avg, key=lambda x: -x[1])[:3]
            city_category_top.append({
                'city': city,
                'categories': cat_avg,
                'no_data': False
            })
        else:
            city_category_top.append({
                'city': city,
                'categories': [],
                'no_data': True
            })
    # If no cities at all, show empty
    if not city_category_top:
        city_category_top = None
    # Limit to max 6 cities for homepage
    city_category_top_home = city_category_top[:6] if city_category_top else None
    return render(request, 'livability/home.html', {'city_category_top': city_category_top_home})


@login_required
def save_fuzzy_pair_ajax(request):
    if request.method == "POST":
        data = request.POST
        cat1 = Category.objects.get(pk=data["category1"])
        cat2 = Category.objects.get(pk=data["category2"])

        CategoryFuzzyComparison.objects.update_or_create(
            category1=cat1,
            category2=cat2,
            user=request.user,
            defaults={
                "value_l": float(data["value_l"]),
                "value_m": float(data["value_m"]),
                "value_u": float(data["value_u"]),
            }
        )

        # Check if user has completed all comparisons
        categories = list(Category.objects.values_list("id", flat=True))
        total_pairs = len(list(combinations(categories, 2)))
        answered = CategoryFuzzyComparison.objects.filter(user=request.user).count()

        if answered >= total_pairs:
            # Consistency Ratio kontrolü
            comparisons = CategoryFuzzyComparison.objects.filter(user=request.user)
            n = len(categories)
            matrix = [[(1.0, 1.0, 1.0) for _ in range(n)] for _ in range(n)]
            category_index = {cat.id: idx for idx, cat in enumerate(Category.objects.all().order_by("name"))}

            for comp in comparisons:
                i, j = category_index[comp.category1.id], category_index[comp.category2.id]
                matrix[i][j] = (comp.value_l, comp.value_m, comp.value_u)
                matrix[j][i] = (1/comp.value_u, 1/comp.value_m, 1/comp.value_l)

            cr = calculate_consistency_ratio(matrix)
            if cr > 0.2:  # CR eşik değeri
                print(f"Consistency Ratio çok yüksek: {cr:.2f}")  # Konsola mesaj yazdır
                return JsonResponse({"status": "error", "message": f"Consistency Ratio çok yüksek: {cr:.2f}"}, status=400)

            # CR 0.2'den küçükse işlem tamamlanır
            compute_fuzzy_weights(request.user)
            return JsonResponse({"status": "complete"})

        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error"}, status=400)


@login_required
def show_ranked_cities(request):
    # Kullanıcının en son test sonucunu çek
    last_result = UserTestResult.objects.filter(user=request.user).order_by('-created_at').first()
    rankings = None
    cr = None
    if last_result:
        # result_json: {city: score, ...} -> [(city, score), ...] sıralı
        rankings = sorted(last_result.result_json.items(), key=lambda x: -x[1])
        # Consistency Ratio hesapla (son testin karşılaştırmalarından)
        categories = list(Category.objects.values_list("id", flat=True))
        n = len(categories)
        comparisons = CategoryFuzzyComparison.objects.filter(user=request.user)
        matrix = [[(1.0, 1.0, 1.0) for _ in range(n)] for _ in range(n)]
        category_index = {cat.id: idx for idx, cat in enumerate(Category.objects.all().order_by("name"))}
        for comp in comparisons:
            i, j = category_index[comp.category1.id], category_index[comp.category2.id]
            matrix[i][j] = (comp.value_l, comp.value_m, comp.value_u)
            matrix[j][i] = (1/comp.value_u, 1/comp.value_m, 1/comp.value_l)
        cr = calculate_consistency_ratio(matrix) if comparisons else None
    return render(request, "livability/ranked_cities.html", {"rankings": rankings, "consistency_ratio": cr})


# User registration view
def register(request):
    from .forms import CustomUserCreationForm
    from livability.models import UserProfile
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            city = form.cleaned_data['city']
            UserProfile.objects.create(user=user, city=city)
            return redirect("login")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})

def overall_list(request):
    from livability.models import OverallCityRanking
    rankings = list(OverallCityRanking.objects.order_by('-avg_score').values_list('city_name', 'avg_score'))
    if not rankings:
        rankings = None
    return render(request, "livability/overall_list.html", {"rankings": rankings})


from django.conf import settings
import os
import pandas as pd

def load_scores_from_project_folder(request):

    folder_path = os.path.join(settings.BASE_DIR, "data/excels")
    from livability.models import Category, CityLivabilityScore
    from django.contrib import messages

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".xlsx"):
            category_name = os.path.splitext(file_name)[0]
            file_path = os.path.join(folder_path, file_name)

            try:
                df = pd.read_excel(file_path)
                category, _ = Category.objects.get_or_create(name=category_name)
                CityLivabilityScore.objects.filter(category=category).delete()

                for _, row in df.iterrows():
                    CityLivabilityScore.objects.create(
                        city_name=row["Şehir İsmi"],
                        value=row["Değer"],
                        category=category
                    )
                messages.success(request, f"{file_name} yüklendi.")
            except Exception as e:
                messages.error(request, f"{file_name} yüklenemedi: {e}")

    from django.contrib import messages
    messages.success(request, "Excel dosyaları başarıyla yüklendi.")
    return redirect("livability:home")

def tech_stack(request):
    return render(request, "livability/tech_stack.html")

def how_we_collect(request):
    return render(request, 'livability/how_we_collect.html')

@login_required
def save_fuzzy_test_result(request):
    """
    Kullanıcı tüm karşılaştırmaları bitirdiğinde, TOPSIS skorunu hesapla ve UserTestResult'a kaydet.
    Ayrıca OverallCityRanking tablosunu günceller.
    """
    if request.method == "POST":
        # Sonuçları hesapla
        rankings = apply_topsis(request.user)
        city = None
        try:
            city = request.user.profile.city
        except Exception:
            pass
        if rankings:
            UserTestResult.objects.create(
                user=request.user,
                city=city or "",
                result_json={city: float(score) for city, score in rankings}
            )
            # --- GENEL SIRALAMA AGGREGATE ---
            from livability.models import UserTestResult, OverallCityRanking
            from django.db.models import Avg
            # Her şehir için tüm kullanıcıların son test skorlarının ortalamasını hesapla
            latest_results = UserTestResult.objects.order_by('user', '-created_at').distinct('user')
            city_scores = {}
            for result in latest_results:
                for c, score in result.result_json.items():
                    city_scores.setdefault(c, []).append(score)
            for c, scores in city_scores.items():
                avg = sum(scores) / len(scores)
                OverallCityRanking.objects.update_or_create(
                    city_name=c,
                    defaults={"avg_score": avg}
                )
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error"}, status=400)

def city_category_detail(request):
    # Same aggregation as index, but show all cities
    from livability.models import UserProfile, FuzzyWeight, Category
    city_category_top = []
    all_cities = set(UserProfile.objects.values_list('city', flat=True))
    categories = list(Category.objects.all().order_by('name'))
    for city in sorted(all_cities):
        users = UserProfile.objects.filter(city=city).values_list('user', flat=True)
        if not users:
            city_category_top.append({'city': city, 'categories': [], 'no_data': True})
            continue
        cat_weights = {cat.id: [] for cat in categories}
        for user_id in users:
            for fw in FuzzyWeight.objects.filter(user_id=user_id):
                defuzz = (fw.weight_l + fw.weight_m + fw.weight_u) / 3
                cat_weights[fw.category_id].append(defuzz)
        cat_avg = []
        for cat in categories:
            vals = cat_weights[cat.id]
            if vals:
                avg = sum(vals) / len(vals)
                cat_avg.append((cat.name, avg))
        if cat_avg:
            cat_avg = sorted(cat_avg, key=lambda x: -x[1])[:3]
            city_category_top.append({'city': city, 'categories': cat_avg, 'no_data': False})
        else:
            city_category_top.append({'city': city, 'categories': [], 'no_data': True})
    if not city_category_top:
        city_category_top = None
    return render(request, 'livability/city_category_detail.html', {'city_category_top': city_category_top})