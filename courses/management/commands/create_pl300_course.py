from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

User = get_user_model()
from courses.models import Course, Module, Lesson, CourseCategory
from cv.models import Curriculum

# Contenido real extraído de los documentos descargados:
#  - "Formación para Certificación PL-300.docx"
#  - "Guía para la Certificación Microsoft Power BI Data Analyst (PL-300).docx"
PL300_SYLLABUS = """
Syllabus: Microsoft Power BI Data Analyst (PL-300)

Estructura General del Curso

Curso: Microsoft Power BI Data Analyst (PL-300)
Duración: 3 días (formación instructor-led) / estudio autodirigido
Nivel: Intermedio
Certificaciones relacionadas: Microsoft Certified: Power BI Data Analyst Associate
Objetivo: Preparar a profesionales en el análisis de datos usando Power BI, alineado con los requisitos técnicos y empresariales para modelar, visualizar y analizar datos, habilitando la obtención del examen PL-300.

---

Módulo 1: Preparación de Datos (25-30% del examen)

Duración: 1 día
Objetivo: Conectar, transformar y limpiar datos desde múltiples orígenes usando Power Query.

Lección 1.1: Conexión a Fuentes de Datos

Elementos:

· Texto: Conexión a fuentes relacionales, no relacionales y servicios en la nube.
· Video: [10 min] Conectores de Power BI y autenticación.
· Imagen: Mapa de arquitectura de ingesta de datos.
· Ejercicios: Conectar a SQL Server, Excel y una API REST.
· Markdown: Lista de conectores soportados.
· Enlaces: Documentación oficial de conectores de Power BI.

Lección 1.2: Transformación y Limpieza con Power Query

Elementos:

· Texto: Perfil de datos, tipos, dividir columnas, valores reemplazados.
· Video: [12 min] Editor de Power Query paso a paso.
· Imagen: Ejemplo de columna condicional.
· Ejercicios: Limpiar un dataset desordenado de ventas.
· Quiz: Evaluación de transformaciones.
· Enlaces: Guía de M (Power Query Formula Language).

Lección 1.3: Parámetros y Modos de Almacenamiento

Elementos:

· Texto: Configuración de parámetros y modos Import vs DirectQuery.
· Video: [8 min] Cuándo usar Import vs DirectQuery.
· Imagen: Diagrama comparativo de modos de almacenamiento.
· Ejercicios: Crear un parámetro de ruta de archivo reutilizable.
· Markdown: Tabla de ventajas y desventajas por modo.

---

Módulo 2: Modelado de Datos (25-30% del examen)

Duración: 1 día
Objetivo: Diseñar modelos semánticos eficientes y crear cálculos con DAX.

Lección 2.1: Diseño de Modelos Semánticos

Elementos:

· Texto: Esquema estrella, tablas de hechos y dimensiones.
· Video: [12 min] Modelado dimensional en Power BI.
· Imagen: Diagrama de esquema estrella de ventas.
· Ejercicios: Convertir un modelo de tabla plana a estrella.
· Markdown: Glosario de cardinalidad y relaciones.

Lección 2.2: Cálculos con DAX

Elementos:

· Texto: Medidas, columnas calculadas, inteligencia de tiempo y funciones estadísticas.
· Video: [15 min] Diferencia entre medidas y columnas calculadas.
· Imagen: Ejemplo de medida de acumulado (YTD).
· Ejercicios: Crear medidas de ventas YTD y variación %.
· Quiz: Evaluación de funciones DAX.
· Enlaces: Referencia de funciones DAX.

Lección 2.3: Optimización del Rendimiento del Modelo

Elementos:

· Texto: Reducción de cardinalidad, tablas de fechas, eliminación de columnas innecesarias.
· Video: [10 min] Uso de Performance Analyzer y DAX Studio.
· Imagen: Captura de plan de consulta lento vs optimizado.
· Ejercicios: Optimizar un modelo con 5M de filas.
· Markdown: Checklist de rendimiento.

---

Módulo 3: Visualización y Análisis (25-30% del examen)

Duración: 1 día
Objetivo: Crear informes interactivos y aplicar técnicas de storytelling.

Lección 3.1: Informes Interactivos con Visuales Avanzados

Elementos:

· Texto: Mapas, KPIs, gráficos y jerarquías.
· Video: [12 min] Diseño de un informe ejecutivo.
· Imagen: Mockup de dashboard de ventas.
· Ejercicios: Construir un KPI con tarjeta multironda.
· Markdown: Mejores prácticas de accesibilidad visual.

Lección 3.2: Storytelling y Usabilidad

Elementos:

· Texto: Bookmarks, tooltips y segmentaciones.
· Video: [10 min] Navegación con bookmarks.
· Imagen: Ejemplo de tooltip personalizado.
· Ejercicios: Crear una segmentación sincronizada entre páginas.
· Quiz: Evaluación de UX de informes.

Lección 3.3: Patrones con Herramientas de IA

Elementos:

· Texto: Forecasting y detección de anomalías en Power BI.
· Video: [8 min] Configurar un pronóstico en un gráfico de líneas.
· Imagen: Detección de anomalías resaltada en serie temporal.
· Ejercicios: Aplicar detección de anomalías a ventas mensuales.
· Enlaces: Documentación de IA en Power BI.

---

Módulo 4: Gestión y Seguridad (15-20% del examen)

Duración: medio día
Objetivo: Administrar workspaces, seguridad y actualizaciones en Power BI Service.

Lección 4.1: Administración de Workspaces y Apps

Elementos:

· Texto: Workspaces, apps y dashboards en Power BI Service.
· Video: [10 min] Publicar y distribuir una app.
· Imagen: Jerarquía de workspace a audiencia.
· Ejercicios: Crear un workspace y asignar permisos.
· Markdown: Roles de workspace (Admin, Member, Contributor, Viewer).

Lección 4.2: Seguridad (RLS y Etiquetas)

Elementos:

· Texto: Row-Level Security y sensitivity labels.
· Video: [12 min] Implementar RLS dinámica con DAX.
· Imagen: Matriz de acceso por región.
· Ejercicios: Definir roles RLS por país.
· Quiz: Evaluación de seguridad.

Lección 4.3: Actualizaciones Programadas y Gateways

Elementos:

· Texto: Configuración de actualizaciones programadas y gateways.
· Video: [8 min] Instalación y registro de un gateway personal.
· Imagen: Flujo de actualización on-premises a la nube.
· Ejercicios: Programar una actualización diaria de un dataset.
· Enlaces: Guía de gateways de Power BI.

---

Recursos Generales del Curso

Elementos Transversales:

· Foro de discusión: Por módulo para dudas y colaboración.
· Biblioteca digital: Rutas de aprendizaje oficiales de Microsoft (Introducción al análisis de datos, Preparación de datos, Modelar datos, Visualización, etc.).
· Glosario interactivo: Términos de Power BI y DAX.
· Sistema de progreso: Barra de avance y logros por módulo.

Evaluación:

· Quiz por lección: 5-10 preguntas de comprensión.
· Examen por módulo: Simulador tipo PL-300.
· Examen final: Simulacro completo de PL-300 (65 preguntas aprox.).
· Certificado: Al completar >=80% del curso y aprobar el simulacro final.

Características Técnicas:

· Responsive: Adaptable a web, tablet y móvil.
· Accesibilidad: Alto contraste y navegación por teclado.
· Modo offline: Descarga de materiales esenciales.
· Sincronización: Progreso guardado en la nube.

---
"""


class Command(BaseCommand):
    help = 'Crear el curso real de certificación Microsoft Power BI Data Analyst (PL-300) desde los documentos descargados.'

    def handle(self, *args, **options):
        category, _ = CourseCategory.objects.get_or_create(
            name='Business Intelligence',
            defaults={'description': 'Cursos de análisis de datos, Power BI y BI empresarial'}
        )

        tutor = self.ensure_tutor()

        course, created = Course.objects.get_or_create(
            slug='microsoft-power-bi-data-analyst-pl300',
            defaults={
                'title': 'Microsoft Power BI Data Analyst (PL-300)',
                'description': (
                    'Curso de preparación para la certificación Microsoft Certified: Power BI Data Analyst '
                    'Associate (examen PL-300). Cubre los métodos y mejores prácticas para modelar, visualizar '
                    'y analizar datos con Power BI: preparación de datos, modelado semántico, visualización '
                    'interactiva y gestión/seguridad en Power BI Service.'
                ),
                'short_description': 'Prepárate para la certificación PL-300: Power Query, DAX, modelado y seguridad en Power BI.',
                'tutor': tutor,
                'category': category,
                'level': 'intermediate',
                'price': 199.00,
                'duration_hours': 24,  # 3 días instructor-led (~8h/día)
                'is_published': True,
                'is_featured': True,
            }
        )
        if not created:
            self.stdout.write(self.style.WARNING(f'El curso "{course.title}" ya existe. No se duplicará.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Curso "{course.title}" creado exitosamente.'))

        modules_data = self.parse_syllabus(PL300_SYLLABUS)
        for module_data in modules_data:
            module = Module.objects.create(
                course=course,
                title=module_data['title'],
                description=module_data['objective'],
                order=module_data['order']
            )
            self.stdout.write(f'Módulo "{module.title}" creado.')
            for lesson_data in module_data['lessons']:
                lesson = Lesson.objects.create(
                    module=module,
                    title=lesson_data['title'],
                    lesson_type='text',
                    content='',
                    structured_content=lesson_data['elements'],
                    duration_minutes=lesson_data['duration'],
                    order=lesson_data['order']
                )
                self.stdout.write(f'  Lección "{lesson.title}" creada.')

        self.stdout.write(self.style.SUCCESS('Curso PL-300 creado exitosamente. Visible en /courses/.'))

    def ensure_tutor(self):
        """Crea un tutor demo con CV si la base está vacía (entorno dev limpio)."""
        tutor = User.objects.filter(cv__isnull=False).first()
        if tutor:
            return tutor

        username = 'instructor_pl300'
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': 'instructor.pl300@example.com',
                'first_name': 'Instructor',
                'last_name': 'PL-300',
                'is_staff': True,
            }
        )
        if created:
            # Contraseña generada en runtime (nunca hardcodeada en el repo).
            # El usuario debe cambiarla vía admin o reset de password en producción.
            temp_password = get_random_string(16)
            user.set_password(temp_password)
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f'Usuario tutor "{username}" creado. Password temporal generado: {temp_password}'
            ))
            self.stdout.write(self.style.WARNING(
                'IMPORTANTE: anota el password temporal o cambialo via admin; no se vuelve a mostrar.'
            ))

        if not hasattr(user, 'cv') or user.cv is None:
            Curriculum.objects.create(
                user=user,
                full_name='Instructor PL-300',
                profession='Analista de Datos Senior / Instructor Power BI',
                bio='Especialista en Power BI, modelado semántico y certificación PL-300.',
            )
            self.stdout.write(self.style.SUCCESS(f'CV creado para "{username}".'))

        return user

    def parse_syllabus(self, syllabus):
        modules = []
        lines = syllabus.strip().split('\n')
        current_module = None
        current_lesson = None
        module_order = 0
        lesson_order = 0

        for line in lines:
            line = line.strip()
            if line.startswith('Módulo'):
                if current_module:
                    modules.append(current_module)
                module_order += 1
                title = line.split(':', 1)[1].strip()
                current_module = {
                    'title': title,
                    'objective': '',
                    'order': module_order,
                    'lessons': []
                }
                lesson_order = 0
            elif line.startswith('Objetivo:') and current_module:
                current_module['objective'] = line.replace('Objetivo:', '').strip()
            elif line.startswith('Lección'):
                if current_lesson:
                    current_module['lessons'].append(current_lesson)
                lesson_order += 1
                title = line.split(':', 1)[1].strip()
                current_lesson = {
                    'title': title,
                    'duration': 0,
                    'order': lesson_order,
                    'elements': []
                }
            elif line.startswith('Elementos:') or line.startswith('Elementos de la lección:'):
                continue
            elif line.startswith('· ') and current_lesson:
                element = line[2:].strip()
                element_type, content = self.parse_element(element)
                current_lesson['elements'].append({
                    'type': element_type,
                    'content': content
                })

        if current_module:
            if current_lesson:
                current_module['lessons'].append(current_lesson)
            modules.append(current_module)

        return modules

    def parse_element(self, element):
        prefixes = [
            ('Video:', 'video'),
            ('Texto:', 'text'),
            ('Imagen:', 'image'),
            ('Ejercicios:', 'exercise'),
            ('Ejercicio:', 'exercise'),
            ('Quiz:', 'quiz'),
            ('Markdown:', 'markdown'),
            ('Enlaces:', 'link'),
        ]
        for prefix, etype in prefixes:
            if element.startswith(prefix):
                content = element.replace(prefix, '').strip()
                duration = 0
                if etype == 'video' and '[' in content and 'min]' in content:
                    try:
                        duration = int(content.split('[')[1].split('min]')[0].strip())
                    except Exception:
                        pass
                return etype, {'description': content, 'duration': duration} if etype == 'video' else content
        return 'text', element
