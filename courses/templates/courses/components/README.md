# Componentes Reutilizables - Courses UI

Esta carpeta contiene los componentes modulares para la interfaz de usuario de cursos. Cada componente está diseñado para ser reutilizable y mantener consistencia visual.

## 📁 Estructura de Archivos

```
partials/
├── _course_card_modern.html     # Tarjeta moderna de curso
├── _management_indicator.html   # Indicador de gestión con métricas
├── _dashboard_stats.html        # Panel de estadísticas del dashboard
├── _quick_actions.html          # Acciones rápidas del tutor
├── _empty_state.html           # Estado vacío cuando no hay cursos
└── README.md                   # Esta documentación
```

## 🎨 Sistema de Diseño

### Variables CSS
Los estilos utilizan un sistema de variables CSS definido en `static/assets/css/manage_courses.css`:

- **Gradientes**: `--primary-gradient`, `--secondary-gradient`, etc.
- **Sombras**: `--shadow-light`, `--shadow-medium`, `--shadow-heavy`
- **Transiciones**: `--transition-fast`, `--transition-slow`
- **Colores consistentes** y **bordes redondeados**

### Animaciones
- `fade-in-up`: Animación de entrada suave
- Efectos hover mejorados con transformaciones
- Micro-interacciones en botones

## 🧩 Componentes Disponibles

### 1. `_course_card_modern.html`
**Uso**: `{% include "courses/partials/_course_card_modern.html" with course=course %}`

**Parámetros requeridos**:
- `course`: Objeto del curso con todos sus atributos

**Características**:
- Diseño moderno con gradientes
- Estados hover interactivos
- Sistema de calificación con estrellas
- Acciones contextuales (Editar, Analíticas, Ver)
- Responsive design
- Indicador de estado (Publicado/Borrador)

### 2. `_management_indicator.html`
**Uso**: `{% include "courses/partials/_management_indicator.html" with courses=courses total_students=total_students avg_rating=avg_rating %}`

**Parámetros requeridos**:
- `courses`: QuerySet de cursos
- `total_students`: Número total de estudiantes
- `avg_rating`: Calificación promedio

**Características**:
- Indicador visual con gradiente
- Métricas en tiempo real
- Diseño adaptable a móviles
- Patrón de fondo sutil

### 3. `_dashboard_stats.html`
**Uso**: `{% include "courses/partials/_dashboard_stats.html" with courses=courses total_students=total_students total_duration=total_duration avg_rating=avg_rating %}`

**Parámetros requeridos**:
- `courses`: QuerySet de cursos
- `total_students`: Número total de estudiantes
- `total_duration`: Duración total en horas
- `avg_rating`: Calificación promedio

**Características**:
- Grid responsive automático
- Estadísticas visuales claras
- Diseño consistente con el indicador

### 4. `_quick_actions.html`
**Uso**: `{% include "courses/partials/_quick_actions.html" %}`

**Parámetros**: Ninguno requerido

**Características**:
- Acciones rápidas para navegación
- Diseño de tarjetas interactivas
- Iconos descriptivos
- Grid adaptable

### 5. `_empty_state.html`
**Uso**: `{% include "courses/partials/_empty_state.html" %}`

**Parámetros**: Ninguno requerido

**Características**:
- Estado vacío amigable
- Call-to-action claro
- Diseño centrado y atractivo

## 🚀 Cómo Usar

### En Templates Principales

```django
{% extends "courses/base.html" %}
{% load static %}

{% block extra_head %}
<link rel="stylesheet" href="{% static 'assets/css/manage_courses.css' %}">
{% endblock %}

{% block course_content %}
<!-- Usar componentes -->
{% include "courses/partials/_management_indicator.html" with courses=courses total_students=total_students avg_rating=avg_rating %}

{% if courses %}
<div class="row">
    {% for course in courses %}
    {% include "courses/partials/_course_card_modern.html" with course=course %}
    {% endfor %}
</div>
{% include "courses/partials/_quick_actions.html" %}
{% else %}
{% include "courses/partials/_empty_state.html" %}
{% endif %}
{% endblock %}
```

### En Otros Contextos

Los componentes pueden reutilizarse en otras vistas como:
- `course_list.html` - Para mostrar cursos en lista
- `dashboard.html` - Para paneles de usuario
- `admin/dashboard.html` - Para vistas administrativas

## 🎯 Beneficios

- **Mantenibilidad**: Cambios en un componente afectan todos los usos
- **Consistencia**: Diseño uniforme en toda la aplicación
- **Reutilización**: Componentes modulares para diferentes contextos
- **Rendimiento**: CSS separado y optimizado
- **Escalabilidad**: Fácil agregar nuevos componentes

## 🔧 Personalización

### Modificar Estilos
Edita `static/assets/css/manage_courses.css` para:
- Cambiar colores del tema
- Ajustar animaciones
- Modificar responsive breakpoints
- Actualizar gradientes

### Agregar Nuevos Componentes
1. Crea el archivo `_nuevo_componente.html`
2. Agrega estilos en `manage_courses.css`
3. Documenta en este README
4. Inclúyelo en los templates necesarios

## 📱 Responsive Design

Todos los componentes incluyen:
- Breakpoints móviles optimizados
- Grid adaptable
- Texto escalable
- Touch-friendly interactions

## 🎨 Paleta de Colores

- **Primario**: Gradiente azul-púrpura
- **Éxito**: Gradiente verde
- **Advertencia**: Gradiente naranja-amarillo
- **Info**: Gradiente azul claro
- **Texto**: Gris oscuro (#2d3748)
- **Fondo**: Blanco con sombras sutiles