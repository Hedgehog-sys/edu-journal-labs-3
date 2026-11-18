from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('about/', views.about, name='about'),
    path('contacts/', views.contacts, name='contacts'),
    path('accounts/register/', views.register, name='register'),
    path('attendance/add/', views.add_attendance, name='attendance_add'),
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('profile/', views.profile, name='profile'),
    path('attendance/stats/', views.attendance_stats, name='attendance_stats'),
    path('attendance/stats/by-name/', views.stats_absences_by_name, name='stats_by_name'),
    path('attendance/stats/by-count/', views.stats_absences_by_count, name='stats_by_count'),
    path('my-attendance/', views.my_attendance, name='my_attendance'),
    path('attendance/groups/', views.group_stats_view, name='group_stats'),

    path('teacher/groups/', views.teacher_groups, name='teacher_groups'),
    path('teacher/groups/<int:group_id>/students/', views.teacher_group_students, name='teacher_group_students'),
    path('teacher/lessons/', views.teacher_lessons, name='teacher_lessons'),
    path('teacher/lessons/<int:lesson_id>/attendance/', views.teacher_lesson_attendance, name='teacher_lesson_attendance'),
    path('student/attendance/', views.student_attendance, name='student_attendance'),


    path('teacher/lessons/<int:lesson_id>/attendance/edit/', views.lesson_attendance_bulk_edit, name='lesson_attendance_bulk_edit'),

    path('teacher/report/', views.attendance_report, name='attendance_report'),

    path('teacher/lessons/export/csv/', views.export_attendance_csv, name='export_attendance_csv'),
]
