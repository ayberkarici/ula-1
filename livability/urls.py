from django.urls import path

from . import views

app_name = 'livability'
urlpatterns = [
    path("", views.index, name="home"),
    path("survey/", views.survey, name="survey"),
    path("city_ranking/", views.city_ranking, name="city_ranking"),
    path("feedback_form/", views.feedback_form, name="feedback_form"),
    path("results/", views.results, name="results"),
    path("more-results/", views.more_results, name="more_results"),
    
    
]