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
]
