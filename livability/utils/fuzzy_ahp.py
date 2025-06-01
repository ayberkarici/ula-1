import pandas as pd
import numpy as np

from livability.models import CityLivabilityScore, CategoryFuzzyComparison, FuzzyWeight
from django.db import transaction

def fuzzy_number(x):
    """Convert crisp number to triangular fuzzy number"""
    return (x-0.1, x, x+0.1)

def fuzzy_comparison_matrix(preferences):
    """Create fuzzy comparison matrix from preferences"""
    n = len(preferences)
    matrix = np.zeros((n, n, 3))
    
    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i,j] = (1,1,1)
            else:
                ratio = preferences[i] / preferences[j]
                matrix[i,j] = fuzzy_number(ratio)
                matrix[j,i] = fuzzy_number(1/ratio)
    
    return matrix

def calculate_weights(comparison_matrix):
    """Calculate weights using Fuzzy AHP method"""
    n = len(comparison_matrix)
    weights = np.zeros(n)
    
    # Simplified weight calculation
    for i in range(n):
        row_product = np.prod([m[1] for m in comparison_matrix[i]])
        weights[i] = row_product ** (1.0/n)
    
    return weights / np.sum(weights)


# --- Fuzzy AHP computation from user comparisons ---
def compute_fuzzy_weights(user):
    # Step 1: Get unique categories
    from livability.models import Category
    categories = list(Category.objects.all().order_by("name"))
    category_index = {cat.id: idx for idx, cat in enumerate(categories)}
    n = len(categories)

    # Step 2: Initialize full matrix with (1,1,1)
    matrix = [[(1.0, 1.0, 1.0) for _ in range(n)] for _ in range(n)]

    # Step 3: Fill in matrix with user comparisons
    comparisons = CategoryFuzzyComparison.objects.filter(user=user)
    for comp in comparisons:
        i, j = category_index[comp.category1.id], category_index[comp.category2.id]
        matrix[i][j] = (comp.value_l, comp.value_m, comp.value_u)
        matrix[j][i] = (1/comp.value_u, 1/comp.value_m, 1/comp.value_l)

    # Step 4: Fuzzy geometric mean
    gms = []
    for row in matrix:
        Ls, Ms, Us = zip(*row)
        gm_l = np.prod(Ls) ** (1/n)
        gm_m = np.prod(Ms) ** (1/n)
        gm_u = np.prod(Us) ** (1/n)
        gms.append((gm_l, gm_m, gm_u))

    # Step 5: Normalize
    sum_l = sum(g[0] for g in gms)
    sum_m = sum(g[1] for g in gms)
    sum_u = sum(g[2] for g in gms)
    norm_weights = [(g[0]/sum_u, g[1]/sum_m, g[2]/sum_l) for g in gms]

    # Step 6: Defuzzify
    defuzzified = [(w[0] + w[1] + w[2]) / 3 for w in norm_weights]
    total = sum(defuzzified)
    normalized = [d / total for d in defuzzified]

    # Step 7: Save to DB
    with transaction.atomic():
        FuzzyWeight.objects.filter(user=user).delete()
        for i, cat in enumerate(categories):
            FuzzyWeight.objects.create(
                category=categories[i],
                user=user,
                weight_l=norm_weights[i][0],
                weight_m=norm_weights[i][1],
                weight_u=norm_weights[i][2]
            )

def compute_city_scores(user):
    """
    Compute city scores for a given user using FuzzyWeight and CityLivabilityScore.
    Returns a dictionary: {city_name: score}
    """
    from livability.models import Category, CityLivabilityScore

    # Get user's normalized weights per category
    weights = {
        fw.category.id: fw.normalized
        for fw in FuzzyWeight.objects.filter(user=user)
    }

    # Aggregate city scores
    city_scores = {}
    all_scores = CityLivabilityScore.objects.select_related("category")

    for entry in all_scores:
        if entry.category.id not in weights:
            continue  # skip if category weight is missing for user

        score = entry.value * weights[entry.category.id]
        city_scores.setdefault(entry.city_name, 0)
        city_scores[entry.city_name] += score

    return city_scores

def compute_city_matrix(user):
    """
    Return a city x category DataFrame where each value is already normalized.
    Used as input for TOPSIS.
    """
    from livability.models import Category, CityLivabilityScore

    categories = list(Category.objects.all().order_by("name"))
    category_ids = [cat.id for cat in categories]
    category_names = [cat.name for cat in categories]

    scores = CityLivabilityScore.objects.filter(category__in=category_ids)
    
    data = {}
    for score in scores:
        if score.city_name not in data:
            data[score.city_name] = {}
        data[score.city_name][score.category.name] = score.value

    df = pd.DataFrame.from_dict(data, orient="index")
    df = df.reindex(columns=category_names)  # ensure consistent column order
    return df
def apply_topsis(user):
    """
    Apply the TOPSIS method using the user's fuzzy weights and the city matrix.
    Returns a sorted list of tuples: [(city_name, topsis_score), ...]
    """
    # Get matrix and weights
    matrix = compute_city_matrix(user)
    # Defuzzify and normalize weights manually
    weights_raw = {
        fw.category.name: (fw.weight_l + fw.weight_m + fw.weight_u) / 3
        for fw in FuzzyWeight.objects.filter(user=user)
    }
    total = sum(weights_raw.values()) or 1
    weights = {k: v / total for k, v in weights_raw.items()}

    if matrix.empty or not weights:
        return []

    # Normalize matrix (if needed)
    norm_matrix = matrix / np.sqrt((matrix ** 2).sum())

    # Apply weights
    weighted_matrix = norm_matrix.copy()
    for col in weighted_matrix.columns:
        weighted_matrix[col] *= weights.get(col, 0)

    # Ideal and anti-ideal solutions
    ideal = weighted_matrix.max()
    anti_ideal = weighted_matrix.min()

    # Distance to ideal and anti-ideal
    d_plus = np.sqrt(((weighted_matrix - ideal) ** 2).sum(axis=1))
    d_minus = np.sqrt(((weighted_matrix - anti_ideal) ** 2).sum(axis=1))

    # Topsis score
    scores = d_minus / (d_plus + d_minus)
    ranked = scores.sort_values(ascending=False)
    return list(ranked.items())

def calculate_consistency_ratio(comparison_matrix):
    """
    Calculate the Consistency Ratio (CR) for a fuzzy comparison matrix.
    """
    n = len(comparison_matrix)
    if n < 2:
        return 0  # No consistency check needed for trivial cases

    # Step 1: Calculate the fuzzy weights
    weights = calculate_weights(comparison_matrix)

    # Step 2: Calculate the weighted sum vector
    weighted_sum = np.zeros(n)
    for i in range(n):
        for j in range(n):
            weighted_sum[i] += np.mean(comparison_matrix[i][j]) * weights[j]

    # Step 3: Calculate the lambda_max (principal eigenvalue)
    lambda_max = np.sum(weighted_sum / weights) / n

    # Step 4: Calculate the Consistency Index (CI)
    ci = (lambda_max - n) / (n - 1)

    # Step 5: Define the Random Index (RI) values for matrices of size 1 to 10
    ri_values = [0, 0, 0.58, 0.9, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49]
    ri = ri_values[n] if n < len(ri_values) else 1.5  # Approximation for larger matrices

    # Step 6: Calculate the Consistency Ratio (CR)
    cr = ci / ri if ri != 0 else 0
    return cr

