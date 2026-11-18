from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from simple_history.models import HistoricalRecords

class User(AbstractUser):
    """Существующая пользовательская модель из работ 1–2."""
    def is_student(self):
        return hasattr(self, 'student_profile')
    def is_teacher(self):
        return hasattr(self, 'teacher_profile')
    def __str__(self):
        return self.get_full_name() or self.username

class Period(models.Model):
    name = models.CharField('Название периода', max_length=200, unique=True)
    date_start = models.DateField('Beginning', null=True, blank=True)
    date_end = models.DateField('Окончание', null=True, blank=True)
    term = models.CharField('Номер семестра', max_length=2, blank=True)
    history = HistoricalRecords()
    class Meta:
        ordering = ['-date_start', 'name']
        verbose_name = 'Учебный период'
        verbose_name_plural = 'Учебные периоды'
    def clean(self):
        if self.date_start and self.date_end and self.date_end < self.date_start:
            raise ValidationError({'date_end': 'Окончание раньше начала.'})
    def __str__(self):
        return self.name

class Group(models.Model):
    name = models.CharField('Название группы', max_length=50)
    id_group = models.CharField('Код группы', max_length=100, unique=True, null=True, blank=True)
    year_priem = models.CharField('Год приёма', max_length=4, blank=True)
    study_form = models.CharField('Форма обучения', max_length=100, blank=True)
    level = models.CharField('Уровень', max_length=100, blank=True)
    faculty = models.CharField('Факультет', max_length=200, blank=True)
    department = models.CharField('Подразделение', max_length=200, blank=True)
    term_number = models.CharField('Учебный период', max_length=2, blank=True)
    semestr = models.CharField('Семестр', max_length=10, blank=True)
    status = models.BooleanField('Активная группа', default=True)
    history = HistoricalRecords()
    class Meta:
        ordering = ['name']
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'
    def student_count(self):
        return self.student_set.count()
    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField('Название дисциплины', max_length=200, unique=True)
    history = HistoricalRecords()
    class Meta:
        ordering = ['name']
        verbose_name = 'Дисциплина'
        verbose_name_plural = 'Дисциплины'
    def __str__(self):
        return self.name

class Student(models.Model):
    name = models.CharField('ФИО студента', max_length=100)
    group = models.ForeignKey(Group, on_delete=models.PROTECT, verbose_name='Группа')
    user_profile = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='student_profile',
        verbose_name='Учётная запись',
    )
    last_name = models.CharField('Фамилия', max_length=100, blank=True)
    first_name = models.CharField('Имя', max_length=100, blank=True)
    second_name = models.CharField('Отчество', max_length=100, blank=True)
    student_id = models.CharField('Идентификатор студента', max_length=100, blank=True)
    id_record_book = models.CharField('Номер зачётной книжки', max_length=100, blank=True)
    starosta = models.BooleanField('Староста', default=False)
    expelled = models.BooleanField('Отчислен', default=False)
    status = models.CharField('Статус обучения', max_length=100, blank=True)
    history = HistoricalRecords()
    class Meta:
        ordering = ['name', 'pk']
        verbose_name = 'Студент'
        verbose_name_plural = 'Студенты'
    def __str__(self):
        return f'{self.name} ({self.group.name})'

class Teacher(models.Model):
    name = models.CharField('ФИО преподавателя', max_length=100)
    user_profile = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='teacher_profile',
        verbose_name='Учётная запись',
    )
    last_name = models.CharField('Фамилия', max_length=100, blank=True)
    first_name = models.CharField('Имя', max_length=100, blank=True)
    second_name = models.CharField('Отчество', max_length=100, blank=True)
    id_teacher = models.CharField('Идентификатор преподавателя', max_length=100, null=True, blank=True, unique=True)
    subjects = models.ManyToManyField(Subject, blank=True, related_name='teachers', verbose_name='Дисциплины')
    academic_degree = models.CharField('Учёная степень', max_length=200, blank=True)
    position = models.CharField('Должность', max_length=200, blank=True)
    status = models.BooleanField('Действующий', default=True)
    history = HistoricalRecords()
    class Meta:
        ordering = ['name', 'pk']
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'
    def __str__(self):
        return self.name

class LessonType(models.Model):
    name = models.CharField('Тип занятия', max_length=100, unique=True)
    history = HistoricalRecords()
    class Meta:
        verbose_name = 'Тип занятия'
        verbose_name_plural = 'Типы занятий'
    def __str__(self):
        return self.name

class Lesson(models.Model):
    id_lesson = models.CharField('ID из расписания', max_length=100, unique=True, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name='lessons', verbose_name='Группа')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='lessons', verbose_name='Дисциплина')
    teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT, related_name='lessons', verbose_name='Преподаватель')
    lesson_type = models.ForeignKey(LessonType, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Тип')
    period = models.ForeignKey(Period, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Период')
    topic = models.CharField('Тема занятия', max_length=200, blank=True)
    date = models.DateField('Дата занятия')
    status = models.BooleanField('Проведено', default=False)
    time_create = models.DateTimeField('Создано', auto_now_add=True)
    time_update = models.DateTimeField('Изменено', auto_now=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='modified_lessons', verbose_name='Последнее изменение',
    )
    history = HistoricalRecords()
    class Meta:
        ordering = ['-date', 'pk']
        verbose_name = 'Занятие'
        verbose_name_plural = 'Занятия'
    def clean(self):
        if self.teacher_id and self.subject_id:
            if not self.teacher.subjects.filter(pk=self.subject_id).exists():
                raise ValidationError({'teacher': 'Дисциплина не закреплена за преподавателем.'})
        if self.period_id and self.date:
            period = self.period
            if period.date_start and self.date < period.date_start:
                raise ValidationError({'date': 'Дата раньше начала периода.'})
            if period.date_end and self.date > period.date_end:
                raise ValidationError({'date': 'Дата позже окончания периода.'})
    def __str__(self):
        return f'{self.subject.name} — {self.group.name} ({self.date})'

class AttendanceStatus(models.Model):
    name = models.CharField('Статус', max_length=100, unique=True)
    short_name = models.CharField('Краткое название', max_length=30)
    history = HistoricalRecords()
    class Meta:
        ordering = ['name']
        verbose_name = 'Статус посещаемости'
        verbose_name_plural = 'Статусы посещаемости'
    def __str__(self):
        return self.name

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, verbose_name='Студент')
    date = models.DateField('Дата занятия')
    present = models.BooleanField('Присутствовал', default=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT, null=True, blank=True, related_name='attendance_records', verbose_name='Занятие')
    status = models.ForeignKey(AttendanceStatus, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Уточнённый статус')
    time_create = models.DateTimeField('Создано', default=timezone.now, editable=False)
    time_update = models.DateTimeField('Изменено', null=True, blank=True, auto_now=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='modified_attendance', verbose_name='Последнее изменение',
    )
    history = HistoricalRecords()
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student', 'date'], condition=Q(lesson__isnull=True), name='unique_legacy_student_date'),
            models.UniqueConstraint(fields=['student', 'lesson'], condition=Q(lesson__isnull=False), name='unique_student_lesson'),
        ]
        ordering = ['-date', 'student__name']
        verbose_name = 'Посещаемость'
        verbose_name_plural = 'Посещаемость'
    def clean(self):
        if self.lesson_id:
            lesson = self.lesson
            if self.date and self.date != lesson.date:
                raise ValidationError({'date': 'Дата посещаемости должна совпадать с датой занятия.'})
            if self.student_id and self.student.group_id != lesson.group_id:
                raise ValidationError({'student': 'Студент должен относиться к группе занятия.'})
    def __str__(self):
        label = 'Присутствовал' if self.present else 'Отсутствовал'
        return f'{self.student.name} — {self.date}: {label}'
