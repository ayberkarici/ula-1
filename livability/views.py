from django.contrib.auth.forms import UserCreationForm
from .utils.fuzzy_ahp import apply_topsis, compute_fuzzy_weights, calculate_consistency_ratio, fuzzy_comparison_matrix
from django.shortcuts import render, redirect
from django.db.models import Avg
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from itertools import combinations
from livability.models import CityLivabilityScore, Category
from .models import CategoryFuzzyComparison, CityLivabilityScore
from .forms import CategoryFuzzyComparisonForm
from itertools import combinations
from django.http import JsonResponse
import unicodedata

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
    return render(request, 'livability/home.html')


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
    rankings = apply_topsis(request.user)
    # Consistency Ratio hesapla
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
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = UserCreationForm()
    return render(request, "registration/register.html", {"form": form})

def overall_list(request):
    # Her kullanıcının son sıralamasını al
    from livability.models import FuzzyWeight, CityLivabilityScore, Category
    users = FuzzyWeight.objects.values_list('user', flat=True).distinct()
    if not users:
        return render(request, "livability/overall_list.html", {"rankings": None})

    # Her kullanıcı için şehir skorlarını topla
    city_scores = {}
    for user_id in users:
        # Kullanıcıya göre ağırlıkları al (defuzzify: l+m+u/3)
        weights = {
            fw.category.id: (fw.weight_l + fw.weight_m + fw.weight_u) / 3
            for fw in FuzzyWeight.objects.filter(user_id=user_id)
        }
        total = sum(weights.values()) or 1
        weights = {k: v / total for k, v in weights.items()}
        # Şehir skorlarını topla
        for entry in CityLivabilityScore.objects.select_related("category"):
            if entry.category.id not in weights:
                continue
            score = entry.value * weights[entry.category.id]
            city_scores.setdefault(entry.city_name, []).append(score)
    # Ortalama skorları hesapla
    avg_scores = {city: sum(scores)/len(scores) for city, scores in city_scores.items() if scores}
    # Sırala
    rankings = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
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