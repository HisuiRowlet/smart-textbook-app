# textbook/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'textbook'

urlpatterns = [
    # Home and core pages
    path('', views.home, name='home'),
    path('upload/', views.upload_document, name='upload'),
    path('lesson/<int:lesson_id>/', views.lesson_view, name='lesson'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='textbook/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    
    # Document management
    path('delete-upload/<int:upload_id>/', views.delete_upload, name='delete_upload'),
    path('document/<int:document_id>/', views.document_detail, name='document_detail'),
    # ^^^ ONLY THIS document URL - NO SEPARATE CHAT URL ^^^
    
    # AI and testing
    path('test-ollama/', views.testollama, name='test_ollama'),
    path('ai-status/', views.ai_status, name='ai_status'),
    path('setup-guide/', views.setup_guide, name='setup_guide'),
    path('test-ai/', views.test_ai_directly, name='test_ai'),
    
    # Notes and notebooks
    path('notes/', views.notebook_list, name='notebook_list'),
    path('notes/create/', views.create_note, name='create_note'),
    path('notes/<int:note_id>/', views.note_detail, name='note_detail'),
    path('notes/<int:note_id>/edit/', views.edit_note, name='edit_note'),
    path('notes/<int:note_id>/delete/', views.delete_note, name='delete_note'),
    path('notebooks/create/', views.create_notebook, name='create_notebook'),
    
    # Pomodoro
    path('pomodoro/', views.pomodoro_timer, name='pomodoro_timer'),
    path('pomodoro/start/', views.start_pomodoro_session, name='start_pomodoro_session'),
    path('pomodoro/complete/<int:session_id>/', views.complete_pomodoro_session, name='complete_pomodoro_session'),
    path('pomodoro/stats/', views.pomodoro_stats, name='pomodoro_stats'),
]