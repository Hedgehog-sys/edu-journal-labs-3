# Create your views here.

import csv
from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import teacher_required
from .forms import AttendanceForm, RegisterForm
from .models import Attendance, AttendanceStatus, Group, Lesson, Period, Student, Subject, Teacher
from .forms import LessonFilterForm

def get_context_with_menu(request, extra_context=None):
    context = {
        'menu': [
            {'title': 'Главная', 'url_name': 'home'},
            {'title': 'О системе', 'url_name': 'about'},
            {'title': 'Контакты', 'url_name': 'contacts'},
        ]
    }

    if request.user.is_authenticated:
        context['menu'].append({'title': 'Журнал', 'url_name': 'attendance_list'})

    if extra_context:
        context.update(extra_context)
    return context

def index(request):
    return render(
        request, 
        'journal/index.html', 
        get_context_with_menu(request, {'welcome': 'Добро пожаловать в систему!'})
    )

def about(request):
    return render(request, 'journal/about.html', get_context_with_menu(request))

def contacts(request):
    return render(request, 'journal/contacts.html', get_context_with_menu(request))

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            Student.objects.create(
                name=user.get_full_name() or user.username,
                group=form.cleaned_data['group'],
                user_profile=user,
            )
            
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'journal/register.html', get_context_with_menu(request, {'form': form}))

@teacher_required
def add_attendance(request):
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('attendance_list')
    else:
        form = AttendanceForm()
    return render(request, 'journal/add_attendance.html', get_context_with_menu(request, {'form': form}))

@login_required
def attendance_list(request):
    if request.user.is_staff:
        attendances = Attendance.objects.all().order_by('-date')
    else:
        if hasattr(request.user, 'student_profile'):
            attendances = Attendance.objects.filter(student=request.user.student_profile).order_by('-date')
        else:
            attendances = Attendance.objects.none()

    return render(
        request, 
        'journal/attendance_list.html', 
        get_context_with_menu(request, {'attendances': attendances})
    )

@login_required
def profile(request):
    if request.user.is_teacher():
        return redirect('home')
    
    student = (
        request.user.student_profile
        if request.user.is_student() else None
    )

    return render(
        request,
        'journal/profile.html',
        get_context_with_menu(request, {'student': student}),
    )

class PeriodForm(forms.Form):
    start_date = forms.DateField(label='Начало периода', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(label='Конец периода', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        if start and end and start > end:
            raise forms.ValidationError('Дата начала не может быть позже даты окончания!')
        return cleaned_data

@teacher_required
def attendance_stats(request):
    form = PeriodForm(request.GET or None)
    stats = None
    
    if form.is_valid():
        start = form.cleaned_data.get('start_date')
        end = form.cleaned_data.get('end_date')
        
        q_present = Q(attendance__present=True)
        q_absent = Q(attendance__present=False)
        
        if start:
            q_present &= Q(attendance__date__gte=start)
            q_absent &= Q(attendance__date__gte=start)
        if end:
            q_present &= Q(attendance__date__lte=end)
            q_absent &= Q(attendance__date__lte=end)
            
        stats = (
            Student.objects.select_related('group')
            .annotate(
                total=Count('attendance', filter=Q(attendance__date__range=(start, end)) if start and end else (Q(attendance__date__gte=start) if start else (Q(attendance__date__lte=end) if end else None))),
                attended=Count('attendance', filter=q_present),
                absences=Count('attendance', filter=q_absent),
            )
            .order_by('-absences', 'name', 'pk')
        )
        
        for student in stats:
            student.attendance_percent = (
                student.attended * 100 / student.total
                if student.total else None
            )
            
    return render(request, 'journal/stats.html', {'stats': stats, 'form': form})

@teacher_required
def stats_absences_by_name(request):
    stats = (
        Student.objects.select_related('group')
        .annotate(
            total=Count('attendance'),
            attended=Count('attendance', filter=Q(attendance__present=True)),
            absences=Count('attendance', filter=Q(attendance__present=False)),
        )
        .filter(absences__gt=5)
        .order_by('name')
    )
    return render(request, 'journal/stats_filtered.html', {'stats': stats, 'title': 'Сортировка по имени'})

@teacher_required
def stats_absences_by_count(request):
    stats = (
        Student.objects.select_related('group')
        .annotate(
            total=Count('attendance'),
            attended=Count('attendance', filter=Q(attendance__present=True)),
            absences=Count('attendance', filter=Q(attendance__present=False)),
        )
        .filter(absences__gt=5)
        .order_by('-absences')
    )
    return render(request, 'journal/stats_filtered.html', {'stats': stats, 'title': 'Сортировка по убыванию пропусков'})

@login_required
def my_attendance(request):
    if not request.user.is_student():
        return redirect('home')
    
    student_profile = request.user.student_profile
    attendances = Attendance.objects.filter(student=student_profile).order_by('-date')
    
    return render(
        request, 
        'journal/my_attendance.html', 
        get_context_with_menu(request, {'attendances': attendances})
    )

@teacher_required
def group_stats_view(request):
    group_stats = (
        Group.objects.annotate(
            student_count=Count('student', distinct=True),
            present_count=Count(
                'student__attendance',
                filter=Q(student__attendance__present=True),
            ),
        )
        .order_by('name', 'pk')
    )
    return render(
        request, 
        'journal/group_stats.html', 
        get_context_with_menu(request, {'group_stats': group_stats})
    )    


def student_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_active or user.is_teacher() or not user.is_student():
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return login_required(wrapped)

@teacher_required
def teacher_groups(request):
    teacher = request.user.teacher_profile
    groups = (Group.objects.filter(lessons__teacher=teacher)
              .distinct().order_by('name', 'pk'))
    page_obj = Paginator(groups, 10).get_page(request.GET.get('page'))
    return render(request, 'journal/teacher_groups.html', get_context_with_menu(request, {'page_obj': page_obj}))

@teacher_required
def teacher_group_students(request, group_id):
    teacher = request.user.teacher_profile
    allowed = Group.objects.filter(lessons__teacher=teacher).distinct()
    group = get_object_or_404(allowed, pk=group_id)
    students = (Student.objects.filter(group=group)
                .select_related('user_profile')
                .order_by('name', 'pk'))
    page_obj = Paginator(students, 20).get_page(request.GET.get('page'))
    return render(request, 'journal/teacher_group_students.html', get_context_with_menu(request, {
        'group': group, 'page_obj': page_obj,
    }))

class LessonFilterForm(forms.Form):
    subject = forms.ModelChoiceField(queryset=Subject.objects.all(), required=False, label='Дисциплина', empty_label="Все дисциплины", widget=forms.Select(attrs={'class': 'form-select'}))
    period = forms.ModelChoiceField(queryset=Period.objects.all(), required=False, label='Период', empty_label="Все периоды", widget=forms.Select(attrs={'class': 'form-select'}))

from .forms import LessonFilterForm

@teacher_required
def teacher_lessons(request):
    teacher = request.user.teacher_profile
    lessons = Lesson.objects.filter(teacher=teacher).select_related('group', 'subject', 'lesson_type', 'period')

    form = LessonFilterForm(request.GET)
    if form.is_valid():
        if form.cleaned_data['subject']:
            lessons = lessons.filter(subject=form.cleaned_data['subject'])
        if form.cleaned_data['period']:
            lessons = lessons.filter(period=form.cleaned_data['period'])
            
    lessons = lessons.order_by('-date', 'pk')
    page_obj = Paginator(lessons, 15).get_page(request.GET.get('page'))
    
    return render(request, 'journal/teacher_lessons.html', {
        'page_obj': page_obj,
        'form': form
    })

@teacher_required
def teacher_lesson_attendance(request, lesson_id):
    teacher = request.user.teacher_profile
    lesson = get_object_or_404(
        Lesson.objects.select_related('group', 'subject'),
        pk=lesson_id, teacher=teacher,
    )
    records = (Attendance.objects.filter(lesson=lesson)
               .select_related('student', 'status')
               .order_by('student__name', 'pk'))
    page_obj = Paginator(records, 30).get_page(request.GET.get('page'))
    return render(request, 'journal/teacher_lesson_attendance.html', get_context_with_menu(request, {
        'lesson': lesson, 'page_obj': page_obj,
    }))

@student_required
def student_attendance(request):
    records = (Attendance.objects.filter(student__user_profile=request.user)
               .select_related('lesson__subject', 'status')
               .order_by('-date', '-pk'))
    page_obj = Paginator(records, 15).get_page(request.GET.get('page'))
    return render(request, 'journal/student_attendance.html', get_context_with_menu(request, {'page_obj': page_obj}))

@teacher_required
def lesson_attendance_bulk_edit(request, lesson_id):
    teacher = request.user.teacher_profile
    lesson = get_object_or_404(Lesson, pk=lesson_id, teacher=teacher)
    students = Student.objects.filter(group=lesson.group, expelled=False).order_by('name')
    records = Attendance.objects.filter(lesson=lesson)
    existing_records = Attendance.objects.filter(lesson=lesson).index_by('student_id') if hasattr(Attendance.objects, 'index_by') else {r.student_id: r for r in Attendance.objects.filter(lesson=lesson)}

    if request.method == 'POST':
        for student in students:
            # Считываем данные из формы для каждого студента
            present = request.POST.get(f'present_{student.pk}') == 'on'
            status_id = request.POST.get(f'status_{student.pk}')
            status = AttendanceStatus.objects.filter(pk=status_id).first() if status_id else None
            
            # Обновляем старую запись или создаем новую
            record = existing_records.get(student.pk) or Attendance(student=student, lesson=lesson, date=lesson.date)
            record.present = present
            record.status = status
            record.changed_by = request.user
            record.full_clean()
            record.save()
            
        messages.success(request, "Ведомость успешно сохранена.")
        return redirect('teacher_lesson_attendance', lesson_id=lesson.pk)
        
    statuses = AttendanceStatus.objects.all()
    return render(request, 'journal/lesson_attendance_form.html', {
        'lesson': lesson,
        'students': students,
        'existing_records': existing_records,
        'statuses': statuses,
    })

@teacher_required
def attendance_report(request):
    teacher = request.user.teacher_profile
    report_data = (Attendance.objects.filter(lesson__teacher=teacher, present=False)
                   .values('student__name', 'student__group__name', 'lesson__subject__name')
                   .annotate(absences_count=Count('id'))
                   .order_by('student__group__name', 'student__name', 'lesson__subject__name'))
    return render(request, 'journal/attendance_report.html', get_context_with_menu(request, {'report_data': report_data}))

@teacher_required
def export_attendance_csv(request):
    teacher = request.user.teacher_profile
    records = (Attendance.objects.filter(lesson__teacher=teacher)
               .select_related('student', 'student__group', 'lesson__subject', 'status')
               .order_by('-date', 'student__name'))

    response = HttpResponse(content_type='text/csv; charset=windows-1251')
    response['Content-Disposition'] = 'attachment; filename="attendance_export.csv"'
    
    writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    
    def cp1251(text):
        return str(text).encode('windows-1251', errors='replace').decode('windows-1251')

    writer.writerow([cp1251('Дата'), cp1251('Группа'), cp1251('Студент'), cp1251('Дисциплина'), cp1251('Присутствие'), cp1251('Статус')])
    
    for record in records:
        subject_name = record.lesson.subject.name if record.lesson else "Архивная запись"
        presence_status = "Да" if record.present else "Нет"
        detailed_status = record.status.name if record.status else "—"

        writer.writerow([
            record.date.strftime('%d.%m.%Y'),
            cp1251(record.student.group.name),
            cp1251(record.student.name),
            cp1251(subject_name),
            cp1251(presence_status),
            cp1251(detailed_status)
        ])
        
    return response

            
