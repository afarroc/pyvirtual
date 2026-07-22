import os
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify
from cv.models import Curriculum  # Importamos el modelo Curriculum desde la app cv

# ======================
# CHOICES
# ======================
class CourseLevelChoices(models.TextChoices):
    BEGINNER = 'beginner', 'Principiante'
    INTERMEDIATE = 'intermediate', 'Intermedio'
    ADVANCED = 'advanced', 'Avanzado'

class EnrollmentStatusChoices(models.TextChoices):
    ACTIVE = 'active', 'Activo'
    COMPLETED = 'completed', 'Completado'
    DROPPED = 'dropped', 'Abandonado'

class LessonTypeChoices(models.TextChoices):
    VIDEO = 'video', 'Video'
    TEXT = 'text', 'Texto'
    QUIZ = 'quiz', 'Quiz'
    ASSIGNMENT = 'assignment', 'Tarea'

# ======================
# MAIN MODELS
# ======================
class CourseCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    
    class Meta:
        verbose_name_plural = 'Course Categories'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    
    # Relación con el tutor (debe tener un Curriculum asociado)
    tutor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='courses_taught',
        limit_choices_to={'cv__isnull': False}  # Solo usuarios con CV
    )
    
    # Información del curso
    category = models.ForeignKey(
        CourseCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='courses'
    )
    level = models.CharField(
        max_length=12,
        choices=CourseLevelChoices.choices,
        default=CourseLevelChoices.BEGINNER
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    duration_hours = models.PositiveIntegerField(help_text="Duración total en horas")
    thumbnail = models.ImageField(
        upload_to='courses/thumbnails/', 
        null=True, 
        blank=True
    )
    
    # Metadatos UPN
    codigo = models.CharField(max_length=50, blank=True, help_text="Código UPN")
    creditos = models.PositiveIntegerField(null=True, blank=True, help_text="Créditos")
    ht = models.PositiveIntegerField(null=True, blank=True, help_text="Horas teóricas")
    hp = models.PositiveIntegerField(null=True, blank=True, help_text="Horas prácticas")
    hl = models.PositiveIntegerField(null=True, blank=True, help_text="Horas de laboratorio")
    pc = models.PositiveIntegerField(null=True, blank=True, help_text="Práctica de campo")
    requisitos = models.CharField(max_length=200, blank=True, help_text="Requisitos")
    naturaleza = models.CharField(max_length=50, blank=True, help_text="Naturaleza: teórico, teórico-práctico, práctico")
    competencia_general = models.TextField(blank=True, help_text="Competencia general")
    componentes = models.TextField(blank=True, help_text="Componentes transversales")
    sumilla = models.TextField(blank=True, help_text="Sumilla del curso")
    logro_curso = models.TextField(blank=True, help_text="Logro del curso")
    sistema_evaluacion = models.TextField(blank=True, help_text="Sistema de evaluación")
    bibliografia = models.TextField(blank=True, help_text="Bibliografía básica")
    
    # Metadata
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    students_count = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    
    # Fechas
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()

        # Validar que el tutor tenga un perfil de CV
        if not hasattr(self.tutor, 'cv') or self.tutor.cv is None:
            raise ValueError("El tutor debe tener un perfil de CV válido para crear cursos.")

        super().save(*args, **kwargs)
    
    def get_tutor_profile(self):
        """Obtiene el perfil (Curriculum) del tutor"""
        return getattr(self.tutor, 'cv', None)

class Module(models.Model):
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='modules'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    logro_unidad = models.TextField(blank=True, help_text="Logro de la unidad")
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class LessonAttachment(models.Model):
    """Modelo para archivos adjuntos de lecciones - permite múltiples archivos por lección"""
    lesson = models.ForeignKey(
        'Lesson',
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    title = models.CharField(max_length=200, help_text="Título descriptivo del archivo")
    file = models.FileField(
        upload_to='courses/lesson_attachments/',
        validators=[FileExtensionValidator([
            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
            'txt', 'zip', 'rar', 'jpg', 'jpeg', 'png', 'gif',
            'mp4', 'avi', 'mov', 'mp3', 'wav'
        ])]
    )
    file_type = models.CharField(max_length=50, blank=True, help_text="Tipo de archivo detectado automáticamente")
    file_size = models.PositiveIntegerField(default=0, help_text="Tamaño del archivo en bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0, help_text="Orden de visualización")

    class Meta:
        ordering = ['order', 'uploaded_at']
        verbose_name = 'Archivo Adjunto de Lección'
        verbose_name_plural = 'Archivos Adjuntos de Lección'

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

    def save(self, *args, **kwargs):
        # Detectar tipo de archivo automáticamente si no está establecido
        if not self.file_type and self.file:
            self.file_type = self.get_file_type()

        # Obtener tamaño del archivo
        if self.file and hasattr(self.file, 'size'):
            self.file_size = self.file.size

        super().save(*args, **kwargs)

    def get_file_type(self):
        """Determina el tipo de archivo basado en la extensión"""
        if not self.file:
            return 'Desconocido'

        file_name = str(self.file.name).lower()

        file_types = {
            # Documentos
            '.pdf': 'PDF Documento',
            '.doc': 'Documento Word',
            '.docx': 'Documento Word',
            '.xls': 'Hoja de Cálculo Excel',
            '.xlsx': 'Hoja de Cálculo Excel',
            '.ppt': 'Presentación PowerPoint',
            '.pptx': 'Presentación PowerPoint',
            '.txt': 'Archivo de Texto',

            # Imágenes
            '.jpg': 'Imagen JPEG',
            '.jpeg': 'Imagen JPEG',
            '.png': 'Imagen PNG',
            '.gif': 'Imagen GIF',

            # Videos
            '.mp4': 'Video MP4',
            '.avi': 'Video AVI',
            '.mov': 'Video MOV',

            # Audio
            '.mp3': 'Audio MP3',
            '.wav': 'Audio WAV',

            # Archivos comprimidos
            '.zip': 'Archivo Comprimido',
            '.rar': 'Archivo Comprimido',
        }

        for ext, file_type in file_types.items():
            if file_name.endswith(ext):
                return file_type

        return 'Archivo'

    def get_file_size_display(self):
        """Retorna el tamaño del archivo en formato legible"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return ".1f"
            size /= 1024.0
        return ".1f"


class Lesson(models.Model):
    # Hacer el módulo opcional para permitir lecciones independientes
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='lessons',
        null=True,
        blank=True
    )

    # Para lecciones independientes
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='standalone_lessons',
        null=True,
        blank=True,
        help_text="Autor de la lección independiente"
    )
    slug = models.SlugField(blank=True, help_text="Slug único para lecciones independientes")
    description = models.TextField(blank=True, help_text="Descripción de la lección independiente")
    is_published = models.BooleanField(default=False, help_text="¿Está publicada la lección independiente?")
    is_featured = models.BooleanField(default=False, help_text="¿Es una lección destacada?")

    title = models.CharField(max_length=200)
    lesson_type = models.CharField(
        max_length=10,
        choices=LessonTypeChoices.choices,
        default=LessonTypeChoices.VIDEO
    )
    content = models.TextField(blank=True)  # Para lecciones de texto simples
    structured_content = models.JSONField(default=list, blank=True)  # Para contenido estructurado con elementos
    video_url = models.URLField(blank=True)  # Para lecciones de video
    duration_minutes = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    is_free = models.BooleanField(default=False)  # Lección gratuita para preview
    
    # Columnas UPN
    logro_semana = models.TextField(blank=True, help_text="Logro de la semana")
    saberes_esenciales = models.TextField(blank=True, help_text="Saberes esenciales")
    actividades = models.TextField(blank=True, help_text="Actividades")
    trabajo_campo = models.TextField(blank=True, help_text="Trabajo de campo / PC")

    # Para quizzes
    quiz_questions = models.JSONField(default=list, blank=True)  # Almacena preguntas y respuestas

    # Para assignments
    assignment_instructions = models.TextField(blank=True)
    assignment_file = models.FileField(
        upload_to='courses/assignments/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf', 'docx', 'txt'])]
    )
    assignment_due_date = models.DateTimeField(null=True, blank=True)

    # Fechas
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        if self.module:
            return f"{self.module.title} - {self.title}"
        else:
            return f"Lección Independiente: {self.title}"

    def save(self, *args, **kwargs):
        # Generar slug para lecciones independientes
        if not self.module and not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
            # Asegurar unicidad del slug
            counter = 1
            original_slug = self.slug
            while Lesson.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1

        # Validar que las lecciones independientes tengan autor
        if not self.module and not self.author:
            raise ValueError("Las lecciones independientes deben tener un autor.")

        super().save(*args, **kwargs)

    @property
    def is_standalone(self):
        """Verifica si es una lección independiente"""
        return self.module is None

    def get_absolute_url(self):
        """Retorna la URL absoluta de la lección"""
        if self.is_standalone:
            return f"/courses/lessons/{self.slug}/"
        else:
            # Para lecciones de curso, necesitaríamos más contexto
            return f"/courses/{self.module.course.slug}/learn/{self.id}/"

class Enrollment(models.Model):
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='course_enrollments'
    )
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='enrollments'
    )
    status = models.CharField(
        max_length=10,
        choices=EnrollmentStatusChoices.choices,
        default=EnrollmentStatusChoices.ACTIVE
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'course']

class Progress(models.Model):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='progress'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='progress'
    )
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    attempts = models.PositiveIntegerField(default=0)  # Número de intentos realizados
    max_attempts = models.PositiveIntegerField(default=3)  # Máximo número de intentos permitidos
    retries_left = models.PositiveIntegerField(default=3)  # Intentos restantes
    
    class Meta:
        unique_together = ['enrollment', 'lesson']
    
    def __str__(self):
        return f"{self.enrollment.student.username} - {self.lesson.title}"

class Review(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='course_reviews'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'course']

    def __str__(self):
        return f"{self.student.username} - {self.course.title} - {self.rating}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Actualizar la calificación promedio del curso
        reviews = self.course.reviews.all()
        if reviews:
            total_rating = sum(review.rating for review in reviews)
            self.course.average_rating = total_rating / reviews.count()
            self.course.save()

# ======================
# CONTENT MANAGEMENT SYSTEM
# ======================

class ContentBlock(models.Model):
    """Modelo para bloques de contenido reutilizable - CMS integrado"""

    CONTENT_TYPES = [
        ('html', 'HTML Personalizado'),
        ('bootstrap', 'Componente Bootstrap'),
        ('markdown', 'Markdown'),
        ('json', 'JSON Estructurado'),
        ('text', 'Texto Simple'),
        ('image', 'Imagen'),
        ('video', 'Video'),
        ('quote', 'Cita'),
        ('code', 'Código'),
        ('list', 'Lista'),
        ('table', 'Tabla'),
        ('card', 'Tarjeta'),
        ('alert', 'Alerta'),
        ('button', 'Botón'),
        ('form', 'Formulario'),
        ('divider', 'Separador'),
        ('icon', 'Ícono'),
        ('progress', 'Barra de Progreso'),
        ('badge', 'Insignia'),
        ('timeline', 'Línea de Tiempo'),
    ]

    title = models.CharField(max_length=200, help_text="Título descriptivo del bloque")
    slug = models.SlugField(unique=True, help_text="Identificador único para el bloque")
    description = models.TextField(blank=True, help_text="Descripción del propósito del bloque")

    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPES,
        default='html',
        help_text="Tipo de contenido del bloque"
    )

    # Contenido del bloque
    html_content = models.TextField(blank=True, help_text="Contenido HTML/Bootstrap")
    json_content = models.JSONField(default=dict, blank=True, help_text="Contenido estructurado en JSON")
    markdown_content = models.TextField(blank=True, help_text="Contenido en formato Markdown")

    # Metadata
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='content_blocks'
    )
    category = models.CharField(max_length=100, blank=True, help_text="Categoría del bloque")
    tags = models.CharField(max_length=500, blank=True, help_text="Etiquetas separadas por comas")

    # Configuración
    is_public = models.BooleanField(default=True, help_text="Bloque disponible para todos los tutores")
    is_featured = models.BooleanField(default=False, help_text="Bloque destacado")

    # Estadísticas de uso
    usage_count = models.PositiveIntegerField(default=0, help_text="Cuántas veces se ha usado este bloque")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Bloque de Contenido'
        verbose_name_plural = 'Bloques de Contenido'

    def __str__(self):
        return f"{self.title} ({self.get_content_type_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
            # Asegurar unicidad del slug
            counter = 1
            original_slug = self.slug
            while ContentBlock.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def get_content(self):
        """Obtiene el contenido principal según el tipo"""
        if self.content_type == 'html':
            return self.html_content
        elif self.content_type == 'bootstrap':
            return self.html_content
        elif self.content_type == 'markdown':
            return self.markdown_content
        elif self.content_type == 'json':
            return self.json_content
        elif self.content_type == 'text':
            return self.html_content
        return ''

    def increment_usage(self):
        """Incrementa el contador de uso"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])

    def get_tags_list(self):
        """Retorna las etiquetas como lista"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

# ======================
# MODELOS UPN
# ======================

class Evaluation(models.Model):
    """Evaluación formal del sílabo UPN: T1, T2, T3, T4, Final, Sustitutoria"""
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='evaluations'
    )
    nombre = models.CharField(max_length=100, help_text="Nombre de la evaluación: T1, T2, T3, T4, Final, Sustitutoria")
    peso = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)], help_text="Peso en porcentaje")
    semana = models.PositiveIntegerField(help_text="Semana en la que se aplica")
    descripcion = models.TextField(blank=True, help_text="Descripción de la evaluación")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['semana']
        unique_together = ['course', 'nombre']
    
    def __str__(self):
        return f"{self.course.title} - {self.nombre} (semana {self.semana})"

class Bibliografia(models.Model):
    """Referencia bibliográfica del sílabo UPN"""
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='bibliografia_items'
    )
    autor = models.CharField(max_length=200, help_text="Autor o autores")
    titulo = models.CharField(max_length=300, help_text="Título del libro o artículo")
    anio = models.CharField(max_length=10, blank=True, help_text="Año de publicación")
    enlace = models.URLField(blank=True, help_text="Enlace o referencia")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['autor']
    
    def __str__(self):
        return f"{self.autor} - {self.titulo}"

# ======================
# SIGNALS
# ======================
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Review)
def update_course_rating(sender, instance, **kwargs):
    """Actualiza la calificación promedio del curso cuando se crea/actualiza una reseña"""
    course = instance.course
    reviews = course.reviews.all()
    if reviews:
        total_rating = sum(review.rating for review in reviews)
        course.average_rating = total_rating / reviews.count()
    else:
        course.average_rating = 0
    course.save()

@receiver(post_delete, sender=Review)
def update_course_rating_on_delete(sender, instance, **kwargs):
    """Actualiza la calificación promedio cuando se elimina una reseña"""
    course = instance.course
    reviews = course.reviews.all()
    if reviews:
        total_rating = sum(review.rating for review in reviews)
        course.average_rating = total_rating / reviews.count()
    else:
        course.average_rating = 0
    course.save()

@receiver(post_save, sender=Enrollment)
def update_student_count(sender, instance, **kwargs):
    """Actualiza el contador de estudiantes cuando cambia el estado de la inscripción"""
    if instance.status == EnrollmentStatusChoices.ACTIVE and instance._state.adding:
        instance.course.students_count += 1
        instance.course.save()
    elif instance.status in [EnrollmentStatusChoices.COMPLETED, EnrollmentStatusChoices.DROPPED]:
        # No reducimos el count para mantener métricas históricas
        pass
