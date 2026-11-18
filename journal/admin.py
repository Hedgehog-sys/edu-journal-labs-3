from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from simple_history.admin import SimpleHistoryAdmin
from .models import User, Group, Student, Teacher, Attendance, Period, Subject, LessonType, Lesson, AttendanceStatus

admin.site.site_header = 'Электронный журнал - Администрирование'
admin.site.index_title = 'Административная панель'
admin.site.site_title = 'ЭЖ Админ'

admin.site.register(User, UserAdmin)


@admin.register(Teacher)
class TeacherAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'name', 'user_profile')
    list_display_links = ('id', 'name')
    search_fields = ('name', 'user_profile__username')

class StudentInline(admin.TabularInline):
    model = Student
    extra = 1

@admin.register(Group)
class GroupAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    inlines = (StudentInline,)

@admin.register(Student)
class StudentAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'name', 'group')
    list_display_links = ('id', 'name')
    search_fields = ('name', 'group__name')
    list_filter = ('group',)

@admin.register(Attendance)
class AttendanceAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'student', 'date', 'present', 'lesson', 'status')
    list_display_links = ('id', 'student')
    list_filter = ('present', 'student__group', 'date', 'status')
    search_fields = ('student__name',)
    ordering = ('-date', '-id')
    autocomplete_fields = ('student',)
    fields = ('student', 'date', 'present', 'lesson', 'status')
    actions = ('mark_as_present',)

    @admin.action(
        description='Отметить выбранные как присутствовавшие',
        permissions=['change'],
    )
    def mark_as_present(self, request, queryset):
        count = queryset.update(present=True)
        self.message_user(request, f'Обновлено записей: {count}')


admin.site.register(Period, SimpleHistoryAdmin)
admin.site.register(Subject, SimpleHistoryAdmin)
admin.site.register(LessonType, SimpleHistoryAdmin)
admin.site.register(AttendanceStatus, SimpleHistoryAdmin)

@admin.register(Lesson)
class LessonAdmin(SimpleHistoryAdmin):
    list_display = ('date', 'subject', 'group', 'teacher', 'status')
    list_filter = ('date', 'status', 'subject')
    search_fields = ('group__name', 'subject__name', 'teacher__name')
    list_select_related = ('group', 'subject', 'teacher')

    def save_model(self, request, obj, form, change):
        obj.changed_by = request.user
        super().save_model(request, obj, form, change)
