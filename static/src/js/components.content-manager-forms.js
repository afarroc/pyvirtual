// Content Manager Forms - JavaScript modular para gestión de formularios
// Agrupa tipos de contenido en categorías lógicas para simplificar la UX

class ContentManagerForms {
    constructor() {
        this.selectedCategory = null;
        this.selectedType = null;
        this.currentStep = 1;
        this.maxSteps = 1;
        this.formData = {};
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupValidation();
    }

    // Categorías de contenido organizadas lógicamente
    getContentCategories() {
        return {
            text: {
                name: 'Contenido de Texto',
                icon: 'bi-textarea-t',
                color: 'text-info',
                types: ['text', 'markdown', 'quote']
            },
            media: {
                name: 'Multimedia',
                icon: 'bi-play-circle',
                color: 'text-success',
                types: ['image', 'video']
            },
            interactive: {
                name: 'Elementos Interactivos',
                icon: 'bi-hand-index-thumb',
                color: 'text-warning',
                types: ['button', 'form', 'alert', 'badge', 'progress']
            },
            structural: {
                name: 'Estructural',
                icon: 'bi-grid-3x3-gap',
                color: 'text-primary',
                types: ['html', 'bootstrap', 'json', 'list', 'table', 'card', 'timeline']
            },
            utility: {
                name: 'Utilidades',
                icon: 'bi-gear',
                color: 'text-secondary',
                types: ['code', 'divider', 'icon']
            }
        };
    }

    bindEvents() {
        // Selección de categoría
        document.addEventListener('click', (e) => {
            if (e.target.closest('.category-card')) {
                const category = e.target.closest('.category-card').dataset.category;
                this.selectCategory(category);
            }
        });

        // Selección de tipo de contenido
        document.addEventListener('click', (e) => {
            if (e.target.closest('.content-type-btn')) {
                const type = e.target.closest('.content-type-btn').dataset.type;
                this.selectContentType(type);
            }
        });

        // Navegación del wizard
        document.addEventListener('click', (e) => {
            if (e.target.matches('.wizard-next')) {
                this.nextStep();
            }
            if (e.target.matches('.wizard-prev')) {
                this.prevStep();
            }
        });

        // Validación en tiempo real
        document.addEventListener('input', (e) => {
            if (e.target.matches('input[required], textarea[required], select[required]')) {
                this.validateField(e.target);
            }
        });
    }

    selectCategory(category) {
        this.selectedCategory = category;
        this.selectedType = null;
        this.currentStep = 1;

        // Actualizar UI
        document.querySelectorAll('.category-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-category="${category}"]`).classList.add('selected');

        // Mostrar tipos de la categoría
        this.showCategoryTypes(category);

        // Ocultar formulario hasta seleccionar tipo
        this.hideForm();
    }

    showCategoryTypes(category) {
        const categories = this.getContentCategories();
        const categoryData = categories[category];
        const typesContainer = document.getElementById('contentTypesContainer');

        if (!categoryData) return;

        const typesHtml = categoryData.types.map(type => {
            const typeInfo = this.getTypeInfo(type);
            return `
                <button class="content-type-btn" data-type="${type}">
                    <div class="type-icon">
                        <i class="bi ${typeInfo.icon}"></i>
                    </div>
                    <div class="type-info">
                        <div class="type-name">${typeInfo.name}</div>
                        <div class="type-desc">${typeInfo.description}</div>
                    </div>
                </button>
            `;
        }).join('');

        typesContainer.innerHTML = `
            <div class="category-header">
                <i class="bi ${categoryData.icon} ${categoryData.color} me-2"></i>
                ${categoryData.name}
            </div>
            <div class="types-grid">
                ${typesHtml}
            </div>
        `;
    }

    selectContentType(type) {
        this.selectedType = type;

        // Actualizar UI
        document.querySelectorAll('.content-type-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        document.querySelector(`[data-type="${type}"]`).classList.add('selected');

        // Determinar si necesita wizard
        const needsWizard = this.typeNeedsWizard(type);
        this.maxSteps = needsWizard ? 2 : 1;

        // Mostrar formulario
        this.showForm(type);
        this.updateWizardNavigation();
    }

    typeNeedsWizard(type) {
        // Tipos que necesitan configuración avanzada
        return ['json', 'form', 'table', 'timeline'].includes(type);
    }

    showForm(type) {
        const formContainer = document.getElementById('contentFormContainer');
        const typeInfo = this.getTypeInfo(type);

        // Header del formulario
        const headerHtml = `
            <div class="form-header">
                <div class="form-title">
                    <i class="bi ${typeInfo.icon} me-2"></i>
                    ${typeInfo.name}
                </div>
                <div class="form-description">${typeInfo.description}</div>
            </div>
        `;

        // Campos del formulario
        const fieldsHtml = this.getTypeFields(type);

        // Navegación del wizard si es necesario
        const wizardNav = this.maxSteps > 1 ? this.getWizardNavigation() : '';

        formContainer.innerHTML = `
            ${headerHtml}
            <form id="contentBlockForm" method="post">
                ${fieldsHtml}
                ${wizardNav}
            </form>
        `;

        // Mostrar contenedor
        formContainer.style.display = 'block';

        // Inicializar campos específicos
        this.initTypeSpecificFields(type);
    }

    hideForm() {
        document.getElementById('contentFormContainer').style.display = 'none';
    }

    getTypeFields(type) {
        const fields = {
            // Campos básicos para todos los tipos
            basic: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-8 mb-3">
                            <label class="form-label">Título *</label>
                            <input type="text" class="form-control" name="title" required>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Categoría</label>
                            <input type="text" class="form-control" name="category" placeholder="ej: Introducción">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Descripción</label>
                        <textarea class="form-control" name="description" rows="2" placeholder="Breve descripción del contenido"></textarea>
                    </div>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Etiquetas</label>
                            <input type="text" class="form-control" name="tags" placeholder="separadas por coma">
                        </div>
                        <div class="col-md-6 mb-3">
                            <div class="form-check mt-4">
                                <input class="form-check-input" type="checkbox" name="is_public" id="isPublic">
                                <label class="form-check-label" for="isPublic">
                                    Contenido público
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
            `,

            // Campos específicos por tipo
            text: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Contenido de Texto *</label>
                        <textarea class="form-control" name="text_content" rows="6" placeholder="Ingresa el contenido de texto aquí..." required></textarea>
                    </div>
                </div>
            `,

            markdown: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Contenido Markdown *</label>
                        <textarea class="form-control" name="markdown_content" rows="8" placeholder="# Título\\n\\nContenido en **Markdown**..." required></textarea>
                        <div class="form-text">Soporta encabezados, listas, código, enlaces, imágenes, etc.</div>
                    </div>
                </div>
            `,

            quote: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Texto de la Cita *</label>
                        <textarea class="form-control" name="quote_text" rows="3" placeholder="La educación es el arma más poderosa..." required></textarea>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Autor de la Cita</label>
                        <input type="text" class="form-control" name="quote_author" placeholder="Nelson Mandela">
                    </div>
                </div>
            `,

            image: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-8 mb-3">
                            <label class="form-label">URL de la Imagen *</label>
                            <input type="url" class="form-control" name="image_url" placeholder="https://ejemplo.com/imagen.jpg" required>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Texto Alternativo</label>
                            <input type="text" class="form-control" name="image_alt" placeholder="Descripción de la imagen">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Pie de Foto</label>
                        <input type="text" class="form-control" name="image_caption" placeholder="Texto que aparece debajo de la imagen">
                    </div>
                </div>
            `,

            video: `
                <div class="form-step" data-step="1">
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
                </div>
            `,

            button: `
                <div class="form-step" data-step="1">
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
                            <input type="text" class="form-control" name="button_icon" placeholder="bi-star">
                            <div class="form-text">Nombre del ícono de Bootstrap Icons</div>
                        </div>
                    </div>
                </div>
            `,

            alert: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Tipo de Alerta *</label>
                            <select class="form-select" name="alert_type" required>
                                <option value="primary">Primario</option>
                                <option value="success">Éxito</option>
                                <option value="danger">Peligro</option>
                                <option value="warning">Advertencia</option>
                                <option value="info">Información</option>
                            </select>
                        </div>
                        <div class="col-md-8 mb-3">
                            <label class="form-label">Mensaje de Alerta *</label>
                            <input type="text" class="form-control" name="alert_message" placeholder="Texto del mensaje de alerta" required>
                        </div>
                    </div>
                </div>
            `,

            badge: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Texto de la Insignia *</label>
                            <input type="text" class="form-control" name="badge_text" placeholder="Nuevo" required>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Color de la Insignia</label>
                            <select class="form-select" name="badge_color">
                                <option value="primary">Primario</option>
                                <option value="success">Éxito</option>
                                <option value="danger">Peligro</option>
                                <option value="warning">Advertencia</option>
                                <option value="info">Información</option>
                            </select>
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Ícono (opcional)</label>
                        <input type="text" class="form-control" name="badge_icon" placeholder="bi-star">
                        <div class="form-text">Nombre del ícono de Bootstrap Icons</div>
                    </div>
                </div>
            `,

            progress: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Valor del Progreso (0-100) *</label>
                            <input type="number" class="form-control" name="progress_value" min="0" max="100" value="50" required>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Color de la Barra</label>
                            <select class="form-select" name="progress_color">
                                <option value="primary">Primario</option>
                                <option value="success">Éxito</option>
                                <option value="info">Información</option>
                                <option value="warning">Advertencia</option>
                                <option value="danger">Peligro</option>
                            </select>
                        </div>
                    </div>
                </div>
            `,

            html: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Código HTML *</label>
                        <textarea class="form-control font-monospace" name="html_content" rows="10" placeholder="<div>Tu código HTML aquí</div>" required></textarea>
                        <div class="form-text">Puedes incluir clases de Bootstrap y estilos personalizados</div>
                    </div>
                </div>
            `,

            bootstrap: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Código HTML/Bootstrap *</label>
                        <textarea class="form-control font-monospace" name="html_content" rows="10" placeholder="<div class='alert alert-primary'>Tu código Bootstrap aquí</div>" required></textarea>
                        <div class="form-text">Utiliza componentes y clases de Bootstrap</div>
                    </div>
                </div>
            `,

            code: `
                <div class="form-step" data-step="1">
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Lenguaje de Programación *</label>
                            <select class="form-select" name="code_language" required>
                                <option value="text">Texto Plano</option>
                                <option value="python">Python</option>
                                <option value="javascript">JavaScript</option>
                                <option value="html">HTML</option>
                                <option value="css">CSS</option>
                                <option value="java">Java</option>
                                <option value="cpp">C++</option>
                                <option value="sql">SQL</option>
                                <option value="bash">Bash</option>
                            </select>
                        </div>
                        <div class="col-md-8 mb-3">
                            <label class="form-label">Título del Código</label>
                            <input type="text" class="form-control" name="code_title" placeholder="Ejemplo de función">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Código Fuente *</label>
                        <textarea class="form-control font-monospace" name="code_content" rows="8" placeholder="def hello_world():\\n    print('Hello, World!')" required></textarea>
                    </div>
                </div>
            `,

            list: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Tipo de Lista *</label>
                        <select class="form-select" name="list_type" required>
                            <option value="unordered">Lista No Ordenada</option>
                            <option value="ordered">Lista Ordenada</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Elementos de la Lista *</label>
                        <textarea class="form-control" name="list_items" rows="6" placeholder="Elemento 1\\nElemento 2\\nElemento 3" required></textarea>
                        <div class="form-text">Cada línea representa un elemento de la lista</div>
                    </div>
                </div>
            `,

            table: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Encabezados (separados por coma) *</label>
                        <input type="text" class="form-control" name="table_headers" placeholder="Nombre, Edad, Ciudad" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Filas de Datos *</label>
                        <textarea class="form-control" name="table_rows" rows="6" placeholder="Juan, 25, Madrid\\nMaría, 30, Barcelona\\nPedro, 35, Valencia" required></textarea>
                        <div class="form-text">Cada línea es una fila, valores separados por coma</div>
                    </div>
                </div>
            `,

            card: `
                <div class="form-step" data-step="1">
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
                </div>
            `,

            divider: `
                <div class="form-step" data-step="1">
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle me-2"></i>
                        El separador es un elemento visual simple que no requiere configuración adicional.
                    </div>
                </div>
            `,

            icon: `
                <div class="form-step" data-step="1">
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
                                <option value="success">Éxito</option>
                                <option value="danger">Peligro</option>
                                <option value="warning">Advertencia</option>
                                <option value="info">Información</option>
                            </select>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">Texto Adicional</label>
                            <input type="text" class="form-control" name="icon_text" placeholder="Texto opcional junto al ícono">
                        </div>
                    </div>
                </div>
            `,

            // Tipos que usan wizard
            json: `
                <div class="form-step" data-step="1">
                    <div class="alert alert-info mb-3">
                        <i class="bi bi-info-circle me-2"></i>
                        Este tipo permite crear contenido complejo con múltiples elementos estructurados.
                    </div>
                    <div class="text-center mb-4">
                        <button type="button" class="btn btn-primary" onclick="contentManagerForms.addStructuredElement()">
                            <i class="bi bi-plus-circle me-1"></i>Agregar Elemento
                        </button>
                    </div>
                    <div id="structuredElements" class="structured-elements-container">
                        <p class="text-muted text-center">Haz clic en "Agregar Elemento" para comenzar</p>
                    </div>
                </div>
            `,

            form: `
                <div class="form-step" data-step="1">
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
                </div>
            `,

            timeline: `
                <div class="form-step" data-step="1">
                    <div class="mb-3">
                        <label class="form-label">Elementos de la Línea de Tiempo (JSON)</label>
                        <textarea class="form-control font-monospace" name="timeline_items" rows="8" placeholder='[
  {"title": "Evento 1", "description": "Descripción del primer evento", "date": "2024-01-01", "color": "primary"},
  {"title": "Evento 2", "description": "Descripción del segundo evento", "date": "2024-02-01", "color": "success"}
]'></textarea>
                        <div class="form-text">Define los elementos de la línea de tiempo en formato JSON</div>
                    </div>
                </div>
            `
        };

        // Combinar campos básicos con específicos
        const basicFields = fields.basic;
        const specificFields = fields[type] || '<div class="alert alert-warning">Tipo de contenido no soportado</div>';

        return basicFields + specificFields;
    }

    getWizardNavigation() {
        return `
            <div class="wizard-navigation mt-4">
                <div class="d-flex justify-content-between align-items-center">
                    <button type="button" class="btn btn-outline-secondary wizard-prev" ${this.currentStep === 1 ? 'disabled' : ''}>
                        <i class="bi bi-arrow-left me-1"></i>Anterior
                    </button>
                    <div class="wizard-steps">
                        Paso ${this.currentStep} de ${this.maxSteps}
                    </div>
                    <button type="button" class="btn btn-primary wizard-next" ${this.currentStep === this.maxSteps ? 'disabled' : ''}>
                        Siguiente<i class="bi bi-arrow-right ms-1"></i>
                    </button>
                </div>
            </div>
        `;
    }

    nextStep() {
        if (this.currentStep < this.maxSteps) {
            this.currentStep++;
            this.updateWizardSteps();
            this.updateWizardNavigation();
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateWizardSteps();
            this.updateWizardNavigation();
        }
    }

    updateWizardSteps() {
        document.querySelectorAll('.form-step').forEach(step => {
            const stepNum = parseInt(step.dataset.step);
            step.style.display = stepNum === this.currentStep ? 'block' : 'none';
        });
    }

    updateWizardNavigation() {
        const prevBtn = document.querySelector('.wizard-prev');
        const nextBtn = document.querySelector('.wizard-next');
        const stepsIndicator = document.querySelector('.wizard-steps');

        if (prevBtn) prevBtn.disabled = this.currentStep === 1;
        if (nextBtn) nextBtn.disabled = this.currentStep === this.maxSteps;
        if (stepsIndicator) stepsIndicator.textContent = `Paso ${this.currentStep} de ${this.maxSteps}`;
    }

    getTypeInfo(type) {
        const typeMap = {
            text: { name: 'Texto Simple', icon: 'bi-textarea-t', description: 'Contenido de texto plano' },
            markdown: { name: 'Markdown', icon: 'bi-markdown', description: 'Contenido con formato Markdown' },
            quote: { name: 'Cita', icon: 'bi-quote', description: 'Cita o testimonial' },
            image: { name: 'Imagen', icon: 'bi-image', description: 'Imagen con descripción' },
            video: { name: 'Video', icon: 'bi-play-circle', description: 'Video embebido' },
            button: { name: 'Botón', icon: 'bi-hand-index-thumb', description: 'Botón interactivo' },
            alert: { name: 'Alerta', icon: 'bi-exclamation-triangle', description: 'Mensaje de alerta' },
            badge: { name: 'Insignia', icon: 'bi-tag', description: 'Insignia o etiqueta' },
            progress: { name: 'Barra de Progreso', icon: 'bi-bar-chart', description: 'Indicador de progreso' },
            html: { name: 'HTML', icon: 'bi-code-slash', description: 'Código HTML personalizado' },
            bootstrap: { name: 'Bootstrap', icon: 'bi-bootstrap', description: 'Componentes Bootstrap' },
            code: { name: 'Código', icon: 'bi-terminal', description: 'Bloque de código' },
            list: { name: 'Lista', icon: 'bi-list-ul', description: 'Lista ordenada o no ordenada' },
            table: { name: 'Tabla', icon: 'bi-table', description: 'Tabla de datos' },
            card: { name: 'Tarjeta', icon: 'bi-card-text', description: 'Tarjeta informativa' },
            divider: { name: 'Separador', icon: 'bi-dash', description: 'Separador visual' },
            icon: { name: 'Ícono', icon: 'bi-star', description: 'Ícono decorativo' },
            json: { name: 'Contenido Estructurado', icon: 'bi-braces', description: 'Contenido complejo estructurado' },
            form: { name: 'Formulario', icon: 'bi-ui-checks', description: 'Formulario personalizado' },
            timeline: { name: 'Línea de Tiempo', icon: 'bi-timeline', description: 'Línea de tiempo de eventos' }
        };
        return typeMap[type] || { name: 'Desconocido', icon: 'bi-question', description: 'Tipo no definido' };
    }

    initTypeSpecificFields(type) {
        // Inicializaciones específicas por tipo
        if (type === 'json') {
            // Para contenido estructurado, inicializar contenedor vacío
            this.structuredElementsCount = 0;
        }
    }

    addStructuredElement() {
        this.structuredElementsCount = (this.structuredElementsCount || 0) + 1;
        const container = document.getElementById('structuredElements');

        if (this.structuredElementsCount === 1) {
            container.innerHTML = '';
        }

        const elementHtml = `
            <div class="structured-element card mb-3" data-index="${this.structuredElementsCount}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">Elemento ${this.structuredElementsCount}</h6>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="contentManagerForms.removeStructuredElement(this)">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">Tipo de Elemento</label>
                            <select class="form-select element-type" name="structured_elements[${this.structuredElementsCount}][type]" onchange="contentManagerForms.updateElementFields(this)">
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
                            <input type="text" class="form-control" name="structured_elements[${this.structuredElementsCount}][title]" placeholder="Título del elemento">
                        </div>
                    </div>
                    <div class="element-fields">
                        <!-- Los campos específicos se cargarán aquí -->
                    </div>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', elementHtml);

        // Inicializar campos para el nuevo elemento
        const newElement = container.lastElementChild;
        const typeSelect = newElement.querySelector('.element-type');
        this.updateElementFields(typeSelect);
    }

    removeStructuredElement(button) {
        button.closest('.structured-element').remove();
        this.updateStructuredElementsIndices();
    }

    updateStructuredElementsIndices() {
        const elements = document.querySelectorAll('.structured-element');
        elements.forEach((element, index) => {
            const newIndex = index + 1;
            element.dataset.index = newIndex;
            element.querySelector('h6').textContent = `Elemento ${newIndex}`;

            // Actualizar nombres de campos
            const inputs = element.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                if (input.name) {
                    input.name = input.name.replace(/\[\d+\]/, `[${newIndex}]`);
                }
            });
        });
        this.structuredElementsCount = elements.length;
    }

    updateElementFields(select) {
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
                        <textarea class="form-control" name="structured_elements[${elementIndex}][items]" rows="4" placeholder="Elemento 1\nElemento 2\nElemento 3" required></textarea>
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

    setupValidation() {
        // Configurar validación visual
        document.addEventListener('blur', (e) => {
            if (e.target.matches('input[required], textarea[required], select[required]')) {
                this.validateField(e.target);
            }
        });
    }

    validateField(field) {
        const isValid = field.checkValidity();
        field.classList.toggle('is-valid', isValid && field.value.trim() !== '');
        field.classList.toggle('is-invalid', !isValid && field.value.trim() === '');

        // Mostrar/ocultar mensaje de error
        let feedback = field.parentNode.querySelector('.invalid-feedback');
        if (!isValid && field.value.trim() === '') {
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.textContent = 'Este campo es obligatorio';
                field.parentNode.appendChild(feedback);
            }
            feedback.style.display = 'block';
        } else if (feedback) {
            feedback.style.display = 'none';
        }
    }

    // Método para obtener datos del formulario
    getFormData() {
        const form = document.getElementById('contentBlockForm');
        if (!form) return null;

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Procesar elementos estructurados si existen
        if (this.selectedType === 'json') {
            data.structured_elements = this.getStructuredElementsData();
        }

        return data;
    }

    getStructuredElementsData() {
        const elements = document.querySelectorAll('.structured-element');
        const structuredData = [];

        elements.forEach((element, index) => {
            const elementIndex = index + 1;
            const elementData = {
                type: element.querySelector(`select[name="structured_elements[${elementIndex}][type]"]`).value,
                title: element.querySelector(`input[name="structured_elements[${elementIndex}][title]"]`).value || '',
            };

            // Agregar campos específicos según el tipo
            const type = elementData.type;
            switch(type) {
                case 'heading':
                    elementData.level = element.querySelector(`select[name="structured_elements[${elementIndex}][level]"]`).value;
                    elementData.content = element.querySelector(`input[name="structured_elements[${elementIndex}][content]"]`).value;
                    break;
                case 'text':
                    elementData.content = element.querySelector(`textarea[name="structured_elements[${elementIndex}][content]"]`).value;
                    break;
                case 'list':
                    elementData.ordered = element.querySelector(`select[name="structured_elements[${elementIndex}][ordered]"]`).value;
                    elementData.items = element.querySelector(`textarea[name="structured_elements[${elementIndex}][items]"]`).value.split('\n').filter(item => item.trim());
                    break;
                case 'image':
                case 'video':
                    elementData.content = element.querySelector(`input[name="structured_elements[${elementIndex}][content]"]`).value;
                    break;
                case 'code':
                    elementData.language = element.querySelector(`input[name="structured_elements[${elementIndex}][language]"]`).value;
                    elementData.code = element.querySelector(`textarea[name="structured_elements[${elementIndex}][code]"]`).value;
                    break;
                case 'exercise':
                    elementData.content = element.querySelector(`textarea[name="structured_elements[${elementIndex}][content]"]`).value;
                    elementData.difficulty = element.querySelector(`select[name="structured_elements[${elementIndex}][difficulty]"]`).value;
                    elementData.estimated_time = element.querySelector(`input[name="structured_elements[${elementIndex}][estimated_time]"]`).value;
                    break;
            }

            structuredData.push(elementData);
        });

        return structuredData;
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.contentManagerForms = new ContentManagerForms();
});