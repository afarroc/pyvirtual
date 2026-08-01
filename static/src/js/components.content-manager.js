/**
 * Content Manager JavaScript
 * Handles the creation and management of content blocks
 */

// Variables globales
let selectedContentType = '';

document.addEventListener('DOMContentLoaded', function() {
    initializeContentManager();
});

function initializeContentManager() {
    // Inicializar selectores de tipo de contenido
    initializeContentTypeSelector();

    // Inicializar filtros de búsqueda
    initializeFilters();

    // Inicializar formulario de creación
    initializeCreateForm();
}

function initializeContentTypeSelector() {
    document.querySelectorAll('.content-type-card').forEach(card => {
        card.addEventListener('click', function() {
            selectContentType(this.dataset.type);
        });
    });
}

function selectContentType(contentType) {
    // Remover selección anterior
    document.querySelectorAll('.content-type-card').forEach(c => c.classList.remove('selected'));

    // Seleccionar este
    const selectedCard = document.querySelector(`[data-type="${contentType}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }

    selectedContentType = contentType;
    document.getElementById('selectedContentType').value = selectedContentType;

    // Habilitar botón de crear
    const createButton = document.getElementById('createButton');
    if (createButton) {
        createButton.disabled = false;
    }

    // Mostrar campos específicos
    showContentFields(selectedContentType);
}

function showContentFields(contentType) {
    const contentFields = document.getElementById('contentFields');
    const dynamicFields = document.getElementById('dynamicFields');
    const sectionTitle = document.getElementById('contentSectionTitle');

    if (!contentFields || !dynamicFields || !sectionTitle) return;

    contentFields.style.display = 'block';

    let fieldsHtml = '';

    switch(contentType) {
        case 'html':
        case 'bootstrap':
            sectionTitle.innerHTML = '<i class="bi bi-code-slash text-primary"></i> Código HTML/Bootstrap';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Código HTML/Bootstrap *</label>
                    <textarea class="form-control" name="html_content" rows="10" placeholder="Ingresa tu código HTML o Bootstrap aquí..." required></textarea>
                    <div class="form-text">Puedes incluir clases de Bootstrap y estilos personalizados</div>
                </div>
            `;
            break;

        case 'markdown':
            sectionTitle.innerHTML = '<i class="bi bi-markdown text-success"></i> Contenido Markdown';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Contenido Markdown *</label>
                    <textarea class="form-control" name="markdown_content" rows="10" placeholder="# Título Principal\n\nEste es un **texto en negrita** y este es *itálico*.\n\n- Elemento de lista 1\n- Elemento de lista 2\n\n\`\`\`python\nprint('Hola Mundo')\n\`\`\`" required></textarea>
                    <div class="form-text">Soporta encabezados, listas, código, enlaces, imágenes, etc.</div>
                </div>
            `;
            break;

        case 'json':
            sectionTitle.innerHTML = '<i class="bi bi-braces text-warning"></i> Contenido Estructurado JSON';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Elementos Estructurados (JSON)</label>
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle me-2"></i>
                        Este tipo permite crear contenido complejo con múltiples elementos estructurados para lecciones.
                    </div>
                    <div class="text-end mb-2">
                        <button type="button" class="btn btn-sm btn-outline-primary" onclick="addStructuredElement()">
                            <i class="bi bi-plus-circle me-1"></i>Agregar Elemento
                        </button>
                    </div>
                    <div id="structuredElements" class="border rounded p-3" style="min-height: 200px;">
                        <!-- Los elementos se agregarán aquí dinámicamente -->
                        <p class="text-muted text-center">Haz clic en "Agregar Elemento" para comenzar</p>
                    </div>
                </div>
            `;
            break;

        case 'text':
            sectionTitle.innerHTML = '<i class="bi bi-textarea-t text-info"></i> Texto Simple';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Contenido de Texto *</label>
                    <textarea class="form-control" name="text_content" rows="6" placeholder="Ingresa el contenido de texto aquí..." required></textarea>
                </div>
            `;
            break;

        case 'image':
            sectionTitle.innerHTML = '<i class="bi bi-image text-danger"></i> Imagen';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">URL de la Imagen *</label>
                        <input type="url" class="form-control" name="image_url" placeholder="https://ejemplo.com/imagen.jpg" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Texto Alternativo</label>
                        <input type="text" class="form-control" name="image_alt" placeholder="Descripción de la imagen">
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Pie de Foto</label>
                    <input type="text" class="form-control" name="image_caption" placeholder="Texto que aparece debajo de la imagen">
                </div>
            `;
            break;

        case 'video':
            sectionTitle.innerHTML = '<i class="bi bi-play-circle text-success"></i> Video';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">URL del Video *</label>
                    <input type="url" class="form-control" name="video_url" placeholder="https://www.youtube.com/watch?v=..." required>
                    <div class="form-text">Soporta YouTube, Vimeo y URLs directas de video</div>
                </div>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Descripción</label>
                        <input type="text" class="form-control" name="video_description" placeholder="Breve descripción del video">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Duración (minutos)</label>
                        <input type="number" class="form-control" name="video_duration" min="1" placeholder="15">
                    </div>
                </div>
            `;
            break;

        case 'quote':
            sectionTitle.innerHTML = '<i class="bi bi-quote text-secondary"></i> Cita';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Texto de la Cita *</label>
                    <textarea class="form-control" name="quote_text" rows="3" placeholder="La educación es el arma más poderosa..." required></textarea>
                </div>
                <div class="mb-3">
                    <label class="form-label">Autor de la Cita</label>
                    <input type="text" class="form-control" name="quote_author" placeholder="Nelson Mandela">
                </div>
            `;
            break;

        case 'code':
            sectionTitle.innerHTML = '<i class="bi bi-terminal text-dark"></i> Código';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Lenguaje de Programación *</label>
                        <select class="form-select" name="code_language" required>
                            <option value="text">Texto Plano</option>
                            <option value="python">Python</option>
                            <option value="javascript">JavaScript</option>
                            <option value="html">HTML</option>
                            <option value="css">CSS</option>
                            <option value="java">Java</option>
                            <option value="cpp">C++</option>
                            <option value="c">C</option>
                            <option value="php">PHP</option>
                            <option value="ruby">Ruby</option>
                            <option value="sql">SQL</option>
                            <option value="bash">Bash</option>
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Título del Código</label>
                        <input type="text" class="form-control" name="code_title" placeholder="Ejemplo de función">
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Código Fuente *</label>
                    <textarea class="form-control font-monospace" name="code_content" rows="8" placeholder="def hello_world():\n    print('Hello, World!')" required></textarea>
                </div>
            `;
            break;

        case 'list':
            sectionTitle.innerHTML = '<i class="bi bi-list-ul text-primary"></i> Lista';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Tipo de Lista *</label>
                    <select class="form-select" name="list_type" required>
                        <option value="unordered">Lista No Ordenada</option>
                        <option value="ordered">Lista Ordenada</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Elementos de la Lista *</label>
                    <textarea class="form-control" name="list_items" rows="6" placeholder="Elemento 1&#10;Elemento 2&#10;Elemento 3" required></textarea>
                    <div class="form-text">Cada línea representa un elemento de la lista</div>
                </div>
            `;
            break;

        case 'table':
            sectionTitle.innerHTML = '<i class="bi bi-table text-info"></i> Tabla';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Encabezados (separados por coma) *</label>
                    <input type="text" class="form-control" name="table_headers" placeholder="Nombre, Edad, Ciudad" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Filas de Datos *</label>
                    <textarea class="form-control" name="table_rows" rows="6" placeholder="Juan, 25, Madrid&#10;María, 30, Barcelona&#10;Pedro, 35, Valencia" required></textarea>
                    <div class="form-text">Cada línea es una fila, valores separados por coma</div>
                </div>
            `;
            break;

        case 'card':
            sectionTitle.innerHTML = '<i class="bi bi-card-text text-warning"></i> Tarjeta';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Título de la Tarjeta *</label>
                        <input type="text" class="form-control" name="card_title" placeholder="Título principal" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Texto de la Tarjeta *</label>
                        <textarea class="form-control" name="card_text" rows="2" placeholder="Contenido de la tarjeta" required></textarea>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">URL del Botón</label>
                        <input type="url" class="form-control" name="card_button_url" placeholder="https://ejemplo.com">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Texto del Botón</label>
                        <input type="text" class="form-control" name="card_button_text" placeholder="Ver más" value="Ver más">
                    </div>
                </div>
            `;
            break;

        case 'alert':
            sectionTitle.innerHTML = '<i class="bi bi-exclamation-triangle text-warning"></i> Alerta';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Tipo de Alerta *</label>
                        <select class="form-select" name="alert_type" required>
                            <option value="primary">Primario</option>
                            <option value="secondary">Secundario</option>
                            <option value="success">Éxito</option>
                            <option value="danger">Peligro</option>
                            <option value="warning">Advertencia</option>
                            <option value="info">Información</option>
                            <option value="light">Claro</option>
                            <option value="dark">Oscuro</option>
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Mensaje de Alerta *</label>
                        <input type="text" class="form-control" name="alert_message" placeholder="Texto del mensaje de alerta" required>
                    </div>
                </div>
            `;
            break;

        case 'button':
            sectionTitle.innerHTML = '<i class="bi bi-hand-index-thumb text-info"></i> Botón';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Texto del Botón *</label>
                        <input type="text" class="form-control" name="button_text" placeholder="Haz clic aquí" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">URL del Botón *</label>
                        <input type="url" class="form-control" name="button_url" placeholder="https://ejemplo.com" required>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Estilo del Botón</label>
                        <select class="form-select" name="button_style">
                            <option value="primary">Primario</option>
                            <option value="secondary">Secundario</option>
                            <option value="success">Éxito</option>
                            <option value="danger">Peligro</option>
                            <option value="warning">Advertencia</option>
                            <option value="info">Información</option>
                            <option value="light">Claro</option>
                            <option value="dark">Oscuro</option>
                        </select>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Tamaño del Botón</label>
                        <select class="form-select" name="button_size">
                            <option value="sm">Pequeño</option>
                            <option value="md" selected>Mediano</option>
                            <option value="lg">Grande</option>
                        </select>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Ícono (opcional)</label>
                        <input type="text" class="form-control" name="button_icon" placeholder="bi-star, bi-heart, etc.">
                        <div class="form-text">Nombre del ícono de Bootstrap Icons</div>
                    </div>
                </div>
            `;
            break;

        case 'form':
            sectionTitle.innerHTML = '<i class="bi bi-ui-checks text-success"></i> Formulario';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">URL de Acción del Formulario *</label>
                    <input type="url" class="form-control" name="form_action" placeholder="/procesar-formulario" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Campos del Formulario (JSON)</label>
                    <textarea class="form-control font-monospace" name="form_fields" rows="8" placeholder='[
  {"type": "text", "name": "nombre", "label": "Nombre", "required": true},
  {"type": "email", "name": "email", "label": "Correo Electrónico", "required": true},
  {"type": "textarea", "name": "mensaje", "label": "Mensaje", "placeholder": "Escribe tu mensaje aquí"}
]'></textarea>
                    <div class="form-text">Define los campos del formulario en formato JSON</div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Texto del Botón de Envío</label>
                    <input type="text" class="form-control" name="form_submit_text" placeholder="Enviar" value="Enviar">
                </div>
            `;
            break;

        case 'divider':
            sectionTitle.innerHTML = '<i class="bi bi-dash text-muted"></i> Separador';
            fieldsHtml = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle me-2"></i>
                    El separador es un elemento visual simple que no requiere configuración adicional.
                </div>
            `;
            break;

        case 'icon':
            sectionTitle.innerHTML = '<i class="bi bi-star text-warning"></i> Ícono';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Ícono *</label>
                        <input type="text" class="form-control" name="icon_name" placeholder="star" required>
                        <div class="form-text">Nombre del ícono de Bootstrap Icons (sin "bi-")</div>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Color</label>
                        <select class="form-select" name="icon_color">
                            <option value="primary">Primario</option>
                            <option value="secondary">Secundario</option>
                            <option value="success">Éxito</option>
                            <option value="danger">Peligro</option>
                            <option value="warning">Advertencia</option>
                            <option value="info">Información</option>
                            <option value="dark">Oscuro</option>
                        </select>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Texto Adicional</label>
                        <input type="text" class="form-control" name="icon_text" placeholder="Texto opcional junto al ícono">
                    </div>
                </div>
            `;
            break;

        case 'progress':
            sectionTitle.innerHTML = '<i class="bi bi-bar-chart text-success"></i> Barra de Progreso';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Valor del Progreso (0-100) *</label>
                        <input type="number" class="form-control" name="progress_value" min="0" max="100" value="50" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Color de la Barra</label>
                        <select class="form-select" name="progress_color">
                            <option value="primary">Primario</option>
                            <option value="secondary">Secundario</option>
                            <option value="success">Éxito</option>
                            <option value="danger">Peligro</option>
                            <option value="warning">Advertencia</option>
                            <option value="info">Información</option>
                            <option value="dark">Oscuro</option>
                        </select>
                    </div>
                </div>
            `;
            break;

        case 'badge':
            sectionTitle.innerHTML = '<i class="bi bi-tag text-info"></i> Insignia';
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Texto de la Insignia *</label>
                        <input type="text" class="form-control" name="badge_text" placeholder="Nuevo" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Color de la Insignia</label>
                        <select class="form-select" name="badge_color">
                            <option value="primary">Primario</option>
                            <option value="secondary">Secundario</option>
                            <option value="success">Éxito</option>
                            <option value="danger">Peligro</option>
                            <option value="warning">Advertencia</option>
                            <option value="info">Información</option>
                            <option value="dark">Oscuro</option>
                        </select>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Ícono (opcional)</label>
                    <input type="text" class="form-control" name="badge_icon" placeholder="bi-star">
                    <div class="form-text">Nombre del ícono de Bootstrap Icons</div>
                </div>
            `;
            break;

        case 'timeline':
            sectionTitle.innerHTML = '<i class="bi bi-timeline text-primary"></i> Línea de Tiempo';
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Elementos de la Línea de Tiempo (JSON)</label>
                    <textarea class="form-control font-monospace" name="timeline_items" rows="8" placeholder='[
  {"title": "Evento 1", "description": "Descripción del primer evento", "date": "2024-01-01", "color": "primary"},
  {"title": "Evento 2", "description": "Descripción del segundo evento", "date": "2024-02-01", "color": "success"}
]'></textarea>
                    <div class="form-text">Define los elementos de la línea de tiempo en formato JSON</div>
                </div>
            `;
            break;

        default:
            fieldsHtml = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Tipo de contenido no reconocido. Los campos se cargarán dinámicamente.
                </div>
            `;
    }

    dynamicFields.innerHTML = fieldsHtml;
}

function initializeFilters() {
    // Filtros de búsqueda (si existen)
    const searchInput = document.getElementById('searchBlocks');
    const typeFilter = document.getElementById('filterType');
    const visibilityFilter = document.getElementById('filterVisibility');

    if (searchInput) searchInput.addEventListener('input', filterBlocks);
    if (typeFilter) typeFilter.addEventListener('change', filterBlocks);
    if (visibilityFilter) visibilityFilter.addEventListener('change', filterBlocks);
}

function filterBlocks() {
    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    const typeFilterValue = typeFilter ? typeFilter.value : '';
    const visibilityFilterValue = visibilityFilter ? visibilityFilter.value : '';

    const blocks = document.querySelectorAll('.block-card');

    blocks.forEach(block => {
        const title = block.querySelector('.block-title').textContent.toLowerCase();
        const type = block.dataset.type;
        const visibility = block.dataset.visibility;

        const matchesSearch = title.includes(searchTerm);
        const matchesType = !typeFilterValue || type === typeFilterValue;
        const matchesVisibility = !visibilityFilterValue || visibility === visibilityFilterValue;

        if (matchesSearch && matchesType && matchesVisibility) {
            block.style.display = '';
        } else {
            block.style.display = 'none';
        }
    });
}

function initializeCreateForm() {
    const createForm = document.getElementById('createBlockForm');
    if (createForm) {
        createForm.addEventListener('submit', handleCreateFormSubmit);
    }
}

function handleCreateFormSubmit(e) {
    e.preventDefault();

    // Validar que se haya seleccionado un tipo de contenido
    if (!selectedContentType) {
        alert('Por favor selecciona un tipo de contenido');
        return;
    }

    const formData = new FormData(this);

    // Procesar elementos estructurados si existen
    if (selectedContentType === 'json') {
        const structuredElements = [];
        const elementDivs = document.querySelectorAll('.structured-element');

        elementDivs.forEach((elementDiv, index) => {
            const elementData = {
                type: elementDiv.querySelector('.element-type').value,
                title: elementDiv.querySelector(`input[name="structured_elements[${index}][title]"]`)?.value || '',
            };

            // Agregar campos específicos según el tipo
            const type = elementData.type;
            switch(type) {
                case 'heading':
                    elementData.level = elementDiv.querySelector(`select[name="structured_elements[${index}][level]"]`).value;
                    elementData.content = elementDiv.querySelector(`input[name="structured_elements[${index}][content]"]`).value;
                    break;
                case 'text':
                    elementData.content = elementDiv.querySelector(`textarea[name="structured_elements[${index}][content]"]`).value;
                    break;
                case 'list':
                    elementData.ordered = elementDiv.querySelector(`select[name="structured_elements[${index}][ordered]"]`).value;
                    elementData.items = elementDiv.querySelector(`textarea[name="structured_elements[${index}][items]"]`).value.split('\n').filter(item => item.trim());
                    break;
                case 'image':
                    elementData.content = elementDiv.querySelector(`input[name="structured_elements[${index}][content]"]`).value;
                    break;
                case 'video':
                    elementData.content = elementDiv.querySelector(`input[name="structured_elements[${index}][content]"]`).value;
                    break;
                case 'code':
                    elementData.language = elementDiv.querySelector(`input[name="structured_elements[${index}][language]"]`).value;
                    elementData.code = elementDiv.querySelector(`textarea[name="structured_elements[${index}][code]"]`).value;
                    break;
                case 'exercise':
                    elementData.content = elementDiv.querySelector(`textarea[name="structured_elements[${index}][content]"]`).value;
                    elementData.difficulty = elementDiv.querySelector(`select[name="structured_elements[${index}][difficulty]"]`).value;
                    elementData.estimated_time = elementDiv.querySelector(`input[name="structured_elements[${index}][estimated_time]"]`).value;
                    break;
            }

            structuredElements.push(elementData);
        });

        formData.set('json_content', JSON.stringify(structuredElements));
    }

    // Mostrar indicador de carga
    const submitButton = document.getElementById('createButton');
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Creando...';
    submitButton.disabled = true;

    fetch(`/courses/content/create/${selectedContentType}/`, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (response.ok) {
            // Recargar la página para mostrar el nuevo bloque
            location.reload();
        } else {
            return response.json().then(data => {
                if (data.errors) {
                    // Mostrar errores de validación
                    let errorMessage = 'Errores de validación:\n';
                    for (const [field, messages] of Object.entries(data.errors)) {
                        errorMessage += `${field}: ${messages.join(', ')}\n`;
                    }
                    alert(errorMessage);
                } else {
                    alert('Error al crear el bloque');
                }
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error de conexión al crear el bloque');
    })
    .finally(() => {
        // Restaurar el botón
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    });
}

// Funciones para gestionar elementos estructurados
function addStructuredElement() {
    const container = document.getElementById('structuredElements');
    const elementCount = container.querySelectorAll('.structured-element').length;

    const elementHtml = `
        <div class="structured-element border rounded p-3 mb-3" data-index="${elementCount}">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="mb-0">Elemento ${elementCount + 1}</h6>
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeStructuredElement(this)">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label">Tipo de Elemento</label>
                    <select class="form-select element-type" name="structured_elements[${elementCount}][type]" onchange="updateElementFields(this)">
                        <option value="heading">Encabezado</option>
                        <option value="text">Texto</option>
                        <option value="list">Lista</option>
                        <option value="image">Imagen</option>
                        <option value="video">Video</option>
                        <option value="code">Código</option>
                        <option value="exercise">Ejercicio</option>
                    </select>
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Título (opcional)</label>
                    <input type="text" class="form-control" name="structured_elements[${elementCount}][title]" placeholder="Título del elemento">
                </div>
            </div>
            <div class="element-fields">
                <!-- Los campos específicos se cargarán aquí -->
            </div>
        </div>
    `;

    if (elementCount === 0) {
        container.innerHTML = '';
    }

    container.insertAdjacentHTML('beforeend', elementHtml);

    // Inicializar campos para el primer elemento
    const firstElement = container.lastElementChild;
    const typeSelect = firstElement.querySelector('.element-type');
    updateElementFields(typeSelect);
}

function removeStructuredElement(button) {
    button.closest('.structured-element').remove();

    // Reordenar índices si es necesario
    const elements = document.querySelectorAll('.structured-element');
    elements.forEach((el, index) => {
        el.dataset.index = index;
        el.querySelector('h6').textContent = `Elemento ${index + 1}`;

        // Actualizar nombres de campos
        const inputs = el.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (input.name) {
                input.name = input.name.replace(/\[\d+\]/, `[${index}]`);
            }
        });
    });
}

function updateElementFields(select) {
    const elementDiv = select.closest('.structured-element');
    const fieldsContainer = elementDiv.querySelector('.element-fields');
    const elementIndex = elementDiv.dataset.index;
    const elementType = select.value;

    let fieldsHtml = '';

    switch(elementType) {
        case 'heading':
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Nivel del Encabezado</label>
                        <select class="form-select" name="structured_elements[${elementIndex}][level]">
                            <option value="1">H1</option>
                            <option value="2">H2</option>
                            <option value="3">H3</option>
                            <option value="4">H4</option>
                            <option value="5">H5</option>
                            <option value="6">H6</option>
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Texto del Encabezado *</label>
                        <input type="text" class="form-control" name="structured_elements[${elementIndex}][content]" required>
                    </div>
                </div>
            `;
            break;

        case 'text':
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Contenido de Texto *</label>
                    <textarea class="form-control" name="structured_elements[${elementIndex}][content]" rows="4" required></textarea>
                </div>
            `;
            break;

        case 'list':
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Tipo de Lista</label>
                    <select class="form-select" name="structured_elements[${elementIndex}][ordered]">
                        <option value="false">Lista No Ordenada</option>
                        <option value="true">Lista Ordenada</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Elementos de la Lista *</label>
                    <textarea class="form-control" name="structured_elements[${elementIndex}][items]" rows="4" placeholder="Elemento 1&#10;Elemento 2&#10;Elemento 3" required></textarea>
                    <div class="form-text">Cada línea representa un elemento de la lista</div>
                </div>
            `;
            break;

        case 'image':
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">URL de la Imagen *</label>
                    <input type="url" class="form-control" name="structured_elements[${elementIndex}][content]" required>
                </div>
            `;
            break;

        case 'video':
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">URL del Video *</label>
                    <input type="url" class="form-control" name="structured_elements[${elementIndex}][content]" required>
                </div>
            `;
            break;

        case 'code':
            fieldsHtml = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Lenguaje</label>
                        <input type="text" class="form-control" name="structured_elements[${elementIndex}][language]" placeholder="python">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Código *</label>
                        <textarea class="form-control font-monospace" name="structured_elements[${elementIndex}][code]" rows="6" required></textarea>
                    </div>
                </div>
            `;
            break;

        case 'exercise':
            fieldsHtml = `
                <div class="mb-3">
                    <label class="form-label">Descripción del Ejercicio *</label>
                    <textarea class="form-control" name="structured_elements[${elementIndex}][content]" rows="4" required></textarea>
                </div>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Dificultad</label>
                        <select class="form-select" name="structured_elements[${elementIndex}][difficulty]">
                            <option value="beginner">Principiante</option>
                            <option value="intermediate">Intermedio</option>
                            <option value="advanced">Avanzado</option>
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Tiempo Estimado (min)</label>
                        <input type="number" class="form-control" name="structured_elements[${elementIndex}][estimated_time]" min="1">
                    </div>
                </div>
            `;
            break;
    }

    fieldsContainer.innerHTML = fieldsHtml;
}

// Funciones para gestionar bloques
function previewBlock(slug) {
    fetch(`/courses/content/${slug}/preview/`)
        .then(response => response.text())
        .then(html => {
            document.getElementById('previewContent').innerHTML = html;
            new bootstrap.Modal(document.getElementById('previewModal')).show();
        })
        .catch(error => {
            console.error('Error loading preview:', error);
            document.getElementById('previewContent').innerHTML = '<div class="alert alert-danger">Error al cargar la vista previa</div>';
            new bootstrap.Modal(document.getElementById('previewModal')).show();
        });
}

function duplicateBlock(slug) {
    if (confirm('¿Estás seguro de que quieres duplicar este bloque?')) {
        fetch(`/courses/content/${slug}/duplicate/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => {
            if (response.ok) {
                location.reload();
            } else {
                alert('Error al duplicar el bloque');
            }
        });
    }
}

function deleteBlock(slug, title) {
    if (confirm(`¿Estás seguro de que quieres eliminar el bloque "${title}"?`)) {
        fetch(`/courses/content/${slug}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => {
            if (response.ok) {
                location.reload();
            } else {
                alert('Error al eliminar el bloque');
            }
        });
    }
}

// Funciones para el panel de creación
function openCreatePanel(type) {
    const panel = document.querySelector('.content-panel');
    if (panel) {
        panel.classList.add('open');
        // Si se especifica un tipo, seleccionarlo
        if (type) {
            const select = document.getElementById('panelContentType');
            if (select) {
                select.value = type;
                changePanelContentType();
            }
        }
    }
}

function closeCreatePanel() {
    const panel = document.querySelector('.content-panel');
    if (panel) {
        panel.classList.remove('open');
    }
}

function changePanelContentType() {
    const select = document.getElementById('panelContentType');
    const form = document.getElementById('panelCreateForm');
    const initialMessage = document.getElementById('panelInitialMessage');
    const dynamicFields = document.getElementById('panelDynamicFields');

    if (!select || !form || !initialMessage || !dynamicFields) return;

    const type = select.value;
    if (type) {
        form.style.display = 'block';
        initialMessage.style.display = 'none';
        document.getElementById('panelBlockType').value = type;

        // Aquí puedes agregar lógica para mostrar campos específicos según el tipo
        // Por simplicidad, mostramos todos los campos básicos
        dynamicFields.innerHTML = '';
    } else {
        form.style.display = 'none';
        initialMessage.style.display = 'block';
    }
}

function showCreateOptions() {
    // Mostrar opciones adicionales de creación
    alert('Funcionalidad adicional próximamente');
}