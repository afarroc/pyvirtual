// edit_section.js - Versión mejorada con soporte completo para formsets dinámicos

document.addEventListener('DOMContentLoaded', function() {
    initializeFormsetHandlers();
    initializeDeleteHandlers();
    initializeFormValidation();
    initializeImagePreview();
    initializeStepIndicators();
    initializeCharacterCounter();
    initializeErrorHandling();
});

/**
 * ============================================
 * FORMSETS DINÁMICOS - USANDO TEMPLATES
 * ============================================
 */

function initializeFormsetHandlers() {
    // Inicializar botones de añadir usando templates ocultos
    document.querySelectorAll('.add-formset-row').forEach(button => {
        button.removeEventListener('click', addFormsetRowHandler);
        button.addEventListener('click', addFormsetRowHandler);
    });
}

function addFormsetRowHandler(e) {
    e.preventDefault();
    const button = e.currentTarget;
    const prefix = button.dataset.prefix;
    addFormsetRow(prefix, button);
}

/**
 * Añade una nueva fila a un formset usando su template oculto
 */
function addFormsetRow(prefix, button) {
    console.log('Ejecutando addFormsetRow para prefix:', prefix);
    
    const container = button.closest('.card-body').querySelector('.formsets-container');
    
    // Versión simple: el ID del template es prefix + '-template'
    const templateId = prefix + '-template';
    console.log('Buscando template con ID:', templateId);
    
    const template = document.getElementById(templateId);

    if (!container) {
        console.error('Container no encontrado para prefix:', prefix);
        showToast('Error: No se encontró el contenedor', 'danger');
        return;
    }

    if (!template) {
        console.error('Template no encontrado para ID:', templateId);
        console.log('Templates disponibles:', Array.from(document.querySelectorAll('[id$="-template"]')).map(el => el.id));
        showToast('Error: No se encontró la plantilla', 'danger');
        return;
    }

    // ... resto del código igual ...

    // Obtener y actualizar TOTAL_FORMS
    const totalForms = document.querySelector(`input[name="${prefix}-TOTAL_FORMS"]`);
    if (!totalForms) {
        console.error('TOTAL_FORMS no encontrado para prefix:', prefix);
        showToast('Error: No se encontró el contador de formularios', 'danger');
        return;
    }

    const currentTotal = parseInt(totalForms.value);
    const newIndex = currentTotal;
    totalForms.value = currentTotal + 1;

    console.log('Total actual:', currentTotal, 'Nuevo índice:', newIndex); // Para depuración

    // Clonar el template y quitar clases ocultas
    const newForm = template.cloneNode(true);
    newForm.classList.remove('formset-row-template', 'd-none');
    newForm.id = ''; // Eliminar id del template

    // Reemplazar __prefix__ en todos los atributos name, id y for
    replacePrefixInElement(newForm, '__prefix__', newIndex);

    // Limpiar valores de los campos
    clearFormValues(newForm);

    // Eliminar mensajes de error previos
    clearFormErrors(newForm);

    // Añadir el nuevo formulario al contenedor
    container.appendChild(newForm);

    // Re-inicializar manejadores de DELETE en la nueva fila
    initializeDeleteHandlers(newForm);

    // Animar la entrada del nuevo formulario
    animateNewRow(newForm);

    // Mostrar notificación de éxito
    showToast('Elemento añadido correctamente', 'success');
}

/**
 * Reemplaza __prefix__ en todos los atributos name, id y for
 */
function replacePrefixInElement(element, searchPattern, newIndex) {
    const attributesToCheck = ['name', 'id', 'for', 'data-target', 'data-field'];
    
    element.querySelectorAll('[name*="__prefix__"], [id*="__prefix__"], [for*="__prefix__"], [data-target*="__prefix__"], [data-field*="__prefix__"]').forEach(el => {
        attributesToCheck.forEach(attr => {
            if (el.hasAttribute(attr) && el.getAttribute(attr).includes('__prefix__')) {
                el.setAttribute(attr, el.getAttribute(attr).replace(/__prefix__/g, newIndex));
            }
        });
    });

    // También verificar elementos que puedan tener __prefix__ en su texto (como labels)
    element.querySelectorAll('label').forEach(label => {
        if (label.htmlFor) {
            label.htmlFor = label.htmlFor.replace(/__prefix__/g, newIndex);
        }
    });
}

/**
 * Limpia los valores de los campos del formulario
 */
function clearFormValues(form) {
    form.querySelectorAll('input:not([type=checkbox]), select, textarea').forEach(input => {
        input.value = '';
        input.classList.remove('is-invalid', 'is-valid');
        
        // Eliminar cualquier placeholder que pueda haber quedado
        if (input.placeholder && input.placeholder.includes('__prefix__')) {
            input.placeholder = input.placeholder.replace(/__prefix__/g, '');
        }
    });

    form.querySelectorAll('input[type=checkbox]').forEach(checkbox => {
        checkbox.checked = false;
        checkbox.classList.remove('is-invalid', 'is-valid');
    });
}

/**
 * Limpia mensajes de error de un formulario
 */
function clearFormErrors(form) {
    form.querySelectorAll('.error-message, .invalid-feedback, .alert-danger').forEach(el => {
        el.remove();
    });
    
    form.querySelectorAll('.is-invalid, .is-valid').forEach(el => {
        el.classList.remove('is-invalid', 'is-valid');
    });
}

/**
 * Anima la entrada de una nueva fila
 */
function animateNewRow(row) {
    row.style.opacity = '0';
    row.style.transform = 'translateY(20px)';
    row.style.transition = 'all 0.3s ease';

    setTimeout(() => {
        row.style.opacity = '1';
        row.style.transform = 'translateY(0)';
    }, 50);

    // Añadir un pequeño efecto de resaltado
    setTimeout(() => {
        row.style.backgroundColor = '#f0f7ff';
        setTimeout(() => {
            row.style.backgroundColor = '';
        }, 500);
    }, 100);
}

/**
 * Muestra un toast notification
 */
function showToast(message, type = 'info') {
    // Eliminar toasts anteriores para evitar acumulación
    const existingToasts = document.querySelectorAll('.toast-notification');
    existingToasts.forEach(toast => toast.remove());
    
    const toast = document.createElement('div');
    toast.className = `toast-notification alert alert-${type} alert-dismissible fade show`;
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '9999';
    toast.style.minWidth = '250px';
    toast.style.maxWidth = '350px';
    toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    toast.style.borderRadius = '8px';
    
    const icon = type === 'success' ? 'check-circle' : 
                 type === 'danger' ? 'exclamation-triangle' : 
                 type === 'warning' ? 'exclamation-circle' : 'info-circle';
    
    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi bi-${icon} me-2 fs-5"></i>
            <span>${message}</span>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(toast);

    // Auto-cerrar después de 3 segundos
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * ============================================
 * MANEJADORES DE ELIMINACIÓN
 * ============================================
 */

function initializeDeleteHandlers(container = document) {
    // Buscar checkboxes DELETE dentro de delete-row-btn o cualquier checkbox con DELETE en su nombre
    container.querySelectorAll('.delete-row-btn input[type="checkbox"], input[type="checkbox"][name$="-DELETE"]').forEach(checkbox => {
        checkbox.removeEventListener('change', handleDeleteCheckbox);
        checkbox.addEventListener('change', handleDeleteCheckbox);
    });
}

function handleDeleteCheckbox(event) {
    const checkbox = event.target;
    const row = checkbox.closest('.formset-row');
    
    if (!row) return;

    if (checkbox.checked) {
        // Marcar para eliminación
        row.style.opacity = '0.6';
        row.style.backgroundColor = '#fff5f5';
        row.style.transition = 'all 0.3s ease';
        row.classList.add('marked-for-deletion');

        // Deshabilitar inputs del formulario a eliminar (excepto el checkbox DELETE)
        row.querySelectorAll('input:not([type=checkbox]), select, textarea').forEach(input => {
            input.disabled = true;
            input.classList.add('text-muted');
        });

        // Mostrar indicador visual
        const deleteLabel = checkbox.closest('label');
        if (deleteLabel) {
            deleteLabel.style.fontWeight = 'bold';
            deleteLabel.style.color = '#dc3545';
        }

        // Animación sutil
        row.style.transform = 'scale(0.98)';
        setTimeout(() => {
            row.style.transform = 'scale(1)';
        }, 200);

    } else {
        // Desmarcar eliminación
        row.style.opacity = '1';
        row.style.backgroundColor = '';
        row.classList.remove('marked-for-deletion');

        // Rehabilitar inputs
        row.querySelectorAll('input:not([type=checkbox]), select, textarea').forEach(input => {
            input.disabled = false;
            input.classList.remove('text-muted');
        });

        // Restaurar estilo del label
        const deleteLabel = checkbox.closest('label');
        if (deleteLabel) {
            deleteLabel.style.fontWeight = '';
            deleteLabel.style.color = '';
        }
    }
}

/**
 * ============================================
 * VALIDACIÓN DE FORMULARIOS
 * ============================================
 */

function initializeFormValidation() {
    const form = document.getElementById('curriculum-form');
    if (!form) return;

    // Validación en tiempo real
    form.querySelectorAll('input, select, textarea').forEach(field => {
        field.addEventListener('input', function() {
            validateField(this);
        });

        field.addEventListener('blur', function() {
            validateField(this, true);
        });
    });

    // Validación al enviar
    form.addEventListener('submit', handleFormSubmit);
}

/**
 * Valida un campo individual
 */
function validateField(field, showError = false) {
    if (field.hasAttribute('required') && !field.value.trim()) {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');

        if (showError) {
            addErrorMessage(field, 'Este campo es obligatorio.');
        }
        return false;
    } else {
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
        
        // Remover mensaje de error si existe
        removeErrorMessage(field);
        return true;
    }
}

/**
 * Añade mensaje de error para un campo
 */
function addErrorMessage(field, message) {
    const container = field.closest('.mb-3') || field.closest('.form-group') || field.parentNode;
    
    // Verificar si ya existe un mensaje de error
    let errorMsg = container.querySelector('.error-message, .invalid-feedback');
    
    if (!errorMsg) {
        errorMsg = document.createElement('div');
        errorMsg.className = 'error-message';
        errorMsg.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i>${message}`;
        container.appendChild(errorMsg);
    } else {
        errorMsg.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i>${message}`;
    }
}

/**
 * Remueve mensaje de error de un campo
 */
function removeErrorMessage(field) {
    const container = field.closest('.mb-3') || field.closest('.form-group') || field.parentNode;
    const errorMsg = container.querySelector('.error-message, .invalid-feedback');
    if (errorMsg) {
        errorMsg.remove();
    }
}

/**
 * Maneja el envío del formulario
 */
function handleFormSubmit(e) {
    const form = e.currentTarget;
    const requiredFields = form.querySelectorAll('[required]');
    let hasErrors = false;
    let firstInvalid = null;
    const missingFields = [];

    // Limpiar mensajes de error anteriores
    form.querySelectorAll('.error-message, .invalid-feedback').forEach(el => el.remove());

    // Validar cada campo requerido
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            hasErrors = true;
            field.classList.add('is-invalid');

            if (!firstInvalid) {
                firstInvalid = field;
            }

            // Obtener label del campo
            const label = field.closest('.mb-3')?.querySelector('label')?.innerText || 
                         field.placeholder || 
                         'Campo';
            
            missingFields.push(label.replace(' *', '').replace(' (opcional)', ''));

            // Añadir mensaje de error
            addErrorMessage(field, 'Este campo es obligatorio.');
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        }
    });

    if (hasErrors) {
        e.preventDefault();

        // Scroll al primer campo con error
        if (firstInvalid) {
            firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
            highlightField(firstInvalid);
        }

        // Mostrar resumen de errores
        showErrorSummary(missingFields);

        // Animación en el botón de submit
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.classList.add('field-error');
            setTimeout(() => {
                submitBtn.classList.remove('field-error');
            }, 500);
        }
    } else {
        // Mostrar estado de carga
        showLoadingState(form);
    }
}

/**
 * Resalta un campo con error
 */
function highlightField(field) {
    field.classList.add('focus-highlight');
    field.focus();
    
    setTimeout(() => {
        field.classList.remove('focus-highlight');
    }, 3000);
}

/**
 * Muestra un resumen de errores
 */
function showErrorSummary(missingFields) {
    // Verificar si ya existe un resumen
    let summary = document.getElementById('errorSummary');
    
    if (!summary) {
        summary = document.createElement('div');
        summary.id = 'errorSummary';
        summary.className = 'error-summary';
        
        const form = document.getElementById('curriculum-form');
        form.parentNode.insertBefore(summary, form);
    }

    summary.innerHTML = `
        <h6><i class="bi bi-exclamation-triangle-fill me-2"></i>Campos obligatorios faltantes:</h6>
        <ul>
            ${missingFields.map(field => `<li>${field}</li>`).join('')}
        </ul>
        <p class="mb-0 small text-muted">Por favor completa todos los campos requeridos antes de continuar.</p>
    `;

    // Scroll al resumen
    summary.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/**
 * Muestra estado de carga en el botón submit
 */
function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Guardando...';
        submitBtn.disabled = true;

        // Si hay un error, restaurar después de un tiempo
        setTimeout(() => {
            if (submitBtn.disabled) {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        }, 5000);
    }
}

/**
 * ============================================
 * PREVISUALIZACIÓN DE IMAGEN
 * ============================================
 */

function initializeImagePreview() {
    const fileInput = document.querySelector('input[type="file"][name="profile_picture"]');
    
    if (fileInput) {
        fileInput.addEventListener('change', handleImagePreview);
    }
}

function handleImagePreview(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validar tipo de archivo
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
    if (!validTypes.includes(file.type)) {
        showToast('Formato no válido. Use JPG, PNG o GIF.', 'danger');
        event.target.value = '';
        return;
    }

    // Validar tamaño (máximo 2MB)
    if (file.size > 2 * 1024 * 1024) {
        showToast('La imagen no puede superar los 2MB.', 'danger');
        event.target.value = '';
        return;
    }

    const reader = new FileReader();
    
    reader.onload = function(e) {
        // Buscar o crear contenedor de preview
        let previewContainer = document.getElementById('profile-preview');
        
        if (!previewContainer) {
            previewContainer = document.createElement('div');
            previewContainer.id = 'profile-preview';
            previewContainer.className = 'mt-3';
            
            const fileInputContainer = event.target.closest('.mb-3, .form-group');
            if (fileInputContainer) {
                fileInputContainer.appendChild(previewContainer);
            }
        }

        previewContainer.innerHTML = `
            <div class="card bg-light">
                <div class="card-body">
                    <h6 class="card-title">Vista previa</h6>
                    <img src="${e.target.result}" alt="Preview" class="img-thumbnail" style="max-height: 150px; border-radius: 8px;">
                    <p class="small text-muted mt-2 mb-0">${file.name}</p>
                </div>
            </div>
        `;
        
        showToast('Imagen cargada correctamente', 'success');
    };

    reader.readAsDataURL(file);
}

/**
 * ============================================
 * INDICADORES DE PROGRESO
 * ============================================
 */

function initializeStepIndicators() {
    const progressBar = document.querySelector('.progress-bar');
    const steps = document.querySelectorAll('.step-indicator, .nav-link');
    
    if (steps.length > 0 && progressBar) {
        steps.forEach((step, index) => {
            step.addEventListener('mouseenter', function() {
                const percentage = ((index + 1) / steps.length) * 100;
                
                const originalWidth = progressBar.style.width;
                
                progressBar.style.transition = 'width 0.2s ease';
                progressBar.style.width = percentage + '%';
                
                setTimeout(() => {
                    progressBar.style.width = originalWidth;
                }, 500);
            });
        });
    }

    // Actualizar contador de secciones
    updateSectionCounter();
}

function updateSectionCounter() {
    const counter = document.getElementById('sectionCounter');
    if (!counter) return;

    const totalSections = document.querySelectorAll('.card[id^="section-"]').length;
    counter.textContent = `${totalSections} secciones`;
}

/**
 * ============================================
 * CONTADOR DE CARACTERES
 * ============================================
 */

function initializeCharacterCounter() {
    const bioField = document.querySelector('#id_bio, textarea[name="bio"]');
    
    if (bioField) {
        const counter = document.getElementById('counter-full_name') || 
                       createCharacterCounter(bioField);

        updateCharacterCount(bioField, counter);

        bioField.addEventListener('input', function() {
            updateCharacterCount(this, counter);
        });
    }
}

function createCharacterCounter(field) {
    const container = field.closest('.mb-3') || field.parentNode;
    const counter = document.createElement('div');
    counter.className = 'field-counter';
    container.appendChild(counter);
    return counter;
}

function updateCharacterCount(field, counter) {
    if (!counter) return;
    
    const length = field.value.length;
    counter.textContent = `${length} caracteres`;

    // Feedback visual por longitud
    counter.classList.remove('text-muted', 'warning', 'danger');
    
    if (length > 500) {
        counter.classList.add('danger');
        counter.style.color = '#dc3545';
    } else if (length > 300) {
        counter.classList.add('warning');
        counter.style.color = '#ffc107';
    } else {
        counter.style.color = '#6c757d';
    }
}

/**
 * ============================================
 * MANEJO DE ERRORES DEL SERVIDOR
 * ============================================
 */

function initializeErrorHandling() {
    // Enfocar primer error si existe resumen de errores
    if (document.querySelector('.error-summary')) {
        focusFirstError();
    }

    // Manejar clics en enlaces de error
    document.querySelectorAll('.error-link').forEach(link => {
        link.addEventListener('click', handleErrorLinkClick);
    });
}

function focusFirstError() {
    const errorFields = document.querySelectorAll('.is-invalid, .error-message');
    
    if (errorFields.length > 0) {
        const firstError = errorFields[0];
        const input = firstError.tagName === 'INPUT' || 
                     firstError.tagName === 'SELECT' || 
                     firstError.tagName === 'TEXTAREA' 
                     ? firstError 
                     : firstError.previousElementSibling;

        if (input) {
            setTimeout(() => {
                input.scrollIntoView({ behavior: 'smooth', block: 'center' });
                input.classList.add('focus-highlight');
                input.focus();

                setTimeout(() => {
                    input.classList.remove('focus-highlight');
                }, 3000);
            }, 100);
        }
    }
}

function handleErrorLinkClick(e) {
    e.preventDefault();
    
    const fieldName = this.dataset.field;
    const targetField = document.getElementById(`id_${fieldName}`) || 
                       document.querySelector(`[name="${fieldName}"]`);

    if (targetField) {
        targetField.scrollIntoView({ behavior: 'smooth', block: 'center' });
        targetField.classList.add('focus-highlight');
        targetField.focus();

        setTimeout(() => {
            targetField.classList.remove('focus-highlight');
        }, 3000);
    }
}

/**
 * ============================================
 * UTILIDADES GENERALES
 * ============================================
 */

// Auto-guardado opcional (descomentar si se desea)
/*
let autoSaveTimer;
const form = document.getElementById('curriculum-form');

if (form) {
    form.addEventListener('input', function() {
        clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(() => {
            // Aquí iría la lógica de auto-guardado
            console.log('Auto-saving...');
            showToast('Guardando cambios...', 'info');
        }, 2000);
    });
}
*/

// Exportar funciones para uso global si es necesario
window.showToast = showToast;
window.addFormsetRow = addFormsetRow;