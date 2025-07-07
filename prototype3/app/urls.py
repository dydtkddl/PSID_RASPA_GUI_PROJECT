from django.urls import path
from . import views

urlpatterns = [
    path('', views.new_simulation, name='new_simulation'),
    path('api/ucell/', views.ucell_api, name='ucell_api'),

    path('simulations/', views.simulations, name='simulations'),
    # ---- delete_multiple를 동적 패턴보다 위로 올립니다. ----
    path(
        'simulations/delete_multiple/',
        views.delete_simulations,
        name='delete_multiple'
    ),
    # --------------------------------------------------------
    path('simulations/<str:sim_name>/', views.simulation_detail,
         name='simulation_detail'),
    path('simulations/<str:sim_name>/log/', views.simulation_log_api,
         name='simulation_log_api'),
    path('simulations/<str:sim_name>/delete/',
         views.delete_simulation,
         name='delete_simulation'),

    # Settings
    path('settings/', views.settings_view, name='settings'),
        path('simulations/<str:sim_name>/refresh/', views.simulation_refresh_api,
         name='simulation_refresh_api'),
]
