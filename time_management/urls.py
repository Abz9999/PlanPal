from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from student_calendar import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('create_event/', views.create_event, name='create_event'),
    path('clear-schedule/', views.clear_schedule, name='clear_schedule'), #schedule/<int:schedule_id>/clear/ , add for multiple scheduling later
    path('', views.home, name='home'),
    path('log_in/', views.LogInView.as_view(), name='log_in'),
    path('log_out/', views.log_out, name='log_out'),
    path('sign_up/', views.SignupView.as_view(), name='sign_up'),
    path('main_page/', views.main_page, name='main_page'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('completed/', views.completed_events, name='completed_events'),
    path('statistics/', views.statistics, name='statistics'),
    path('user/details/', views.user_details, name='user_details'),
    path('event/<int:pk>', views.event_detail, name='event_detail'),
    path('api/schedule-events/', views.get_events_api, name='get_events'),
    path('api/events/', views.get_event_templates, name='get_event_templates'),
    path('api/schedules/', views.get_schedules, name='get_schedules'),
    path('api/schedules/<int:schedule_id>/', views.delete_schedule, name='delete_schedule'),
    path('event/<int:pk>/delete/', views.delete_event, name='delete_event'),
    path('event/<int:pk>/edit/', views.edit_event, name='edit_event'),
    path('event/<int:pk>/instances/', views.get_event_instances, name='event_instances'),
    path('schedule-event/<int:pk>/status/', views.update_instance_status, name='update_instance_status'),
    path('smart-plan/events/', views.get_smart_planner_events, name='smart_plan_events'),
    path('smart-plan/generate/', views.generate_smart_plan, name='smart_plan_generate'),
    path('smart-plan/confirm/', views.confirm_smart_plan, name='smart_plan_confirm'),
    path('schedule-event/<int:pk>/place/', views.place_instance, name='place_instance'),
    path('schedule-event/<int:pk>/unplace/', views.unplace_instance, name='unplace_instance'),
    path('api/update-event/<int:pk>/', views.update_schedule_event)
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
