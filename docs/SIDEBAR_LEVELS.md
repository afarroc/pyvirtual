# Sidebar M360 — Niveles de navegación
**Fecha:** 2026-07-27  
**Proyecto:** Management360  
**Tipo:** documentación interna

## Método
Se usa diferenciación visual por niveles M360 dentro del mismo `<ul class="m360-sidebar-nav">`:

- **Nivel 1 — Grupo principal**
  - Clase: `m360-sidebar-nav-item`
  - Trigger: `data-m360-toggle="collapse"` con icono chevron
  - Indicador: chevron SVG generado por CSS
  - Target: `ul.m360-sidebar-nav-group.m360-collapse`

- **Nivel 2 — Subgrupo**
  - Clase: `m360-sidebar-nav-group`
  - Indentación: `padding-left: var(--m360-space-4)`
  - Borde izquierdo: `1px solid var(--m360-border)`
  - Puede ser collapsible o lista directa

- **Nivel 3 — Items hoja**
  - Clase: `m360-sidebar-nav-item`
  - Indentación adicional: `padding-left: calc(var(--m360-space-3) + 18px + var(--m360-space-2))`
  - Enlaces simples con icono + texto

## Indicadores de despliegue
- Chevron en items con `data-m360-toggle="collapse"`
- Rotación 180° cuando `aria-expanded="true"`
- Transición controlada por `m360-sidebar-collapse.js`

## Tabulación / sangría
- Nivel 1: padding base del sidebar
- Nivel 2: padding-left adicional + borde izquierdo
- Nivel 3: padding-left adicional sobre items hoja

## Ejemplo
- Projects (nivel 1) → Project Actions (nivel 2 collapsible) → Create Project (nivel 3)
