from django.urls import path
from . import views
from .views import *

app_name = 'livability'
urlpatterns = [
    path("", views.index, name="home"),
    path('fahp/pairs/', fahp_pairwise_ui, name='fahp_pairs'),
    path('fahp/save/', save_fuzzy_pair_ajax, name='save_fuzzy_pair_ajax'),
    path("rankings/", views.show_ranked_cities, name="show_ranked_cities"),
    path('overall-list/', views.overall_list, name='overall_list'),
    path("load-scores/", views.load_scores_from_project_folder, name="load_scores"),
    path('tech-stack/', views.tech_stack, name='tech_stack'),
    path('veri-toplama/', views.how_we_collect, name='how_we_collect'),
    path('save-test-result/', views.save_fuzzy_test_result, name='save_fuzzy_test_result'),
    path('city-category-detail/', views.city_category_detail, name='city_category_detail'),
]
