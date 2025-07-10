/**
 * Theme Ejemplo Enhanced JavaScript
 * Funcionalidades mejoradas para el tema UNESCO
 */

// Función para manejar "leer más" / "leer menos"
function toggleReadMore(button) {
    try {
        const textContent = button.closest('.text-content');
        if (!textContent) return;
        
        const textPreview = textContent.querySelector('.text-preview');
        const textFull = textContent.querySelector('.text-full');
        const icon = button.querySelector('i');
        const textSpan = button.querySelector('.read-more-text');
        
        if (!textPreview || !textFull || !icon || !textSpan) return;
        
        const isExpanded = textFull.classList.contains('show');
        
        if (isExpanded) {
            // Colapsar texto
            textFull.classList.remove('show');
            textPreview.classList.remove('hide');
            icon.className = 'fa fa-plus';
            textSpan.textContent = textSpan.getAttribute('data-more-text') || 'Leer más';
            button.classList.remove('expanded');
            
            // Animación suave al colapsar
            textFull.style.maxHeight = '0';
            textFull.style.opacity = '0';
            setTimeout(() => {
                textFull.style.display = 'none';
                textPreview.style.display = 'block';
            }, 300);
        } else {
            // Expandir texto
            textPreview.classList.add('hide');
            textFull.classList.add('show');
            icon.className = 'fa fa-minus';
            textSpan.textContent = textSpan.getAttribute('data-less-text') || 'Leer menos';
            button.classList.add('expanded');
            
            // Animación suave al expandir
            textPreview.style.display = 'none';
            textFull.style.display = 'block';
            textFull.style.maxHeight = 'none';
            textFull.style.opacity = '1';
        }
        
        // Añadir clase de animación
        button.closest('.cardsmall-enhanced, .card-enhanced')?.classList.add('fade-in');
        
    } catch (error) {
        console.error('Error en toggleReadMore:', error);
    }
}

// Función para inicializar tooltips y efectos
function initializeEnhancements() {
    try {
        // Inicializar tooltips si Bootstrap está disponible
        if (typeof $ !== 'undefined' && $.fn.tooltip) {
            $('[data-toggle="tooltip"]').tooltip();
        }
        
        // Añadir efectos de hover mejorados
        document.querySelectorAll('.hover-lift').forEach(element => {
            element.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-4px)';
            });
            
            element.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
        
        // Añadir efectos de escala
        document.querySelectorAll('.hover-scale').forEach(element => {
            element.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.02)';
            });
            
            element.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
            });
        });
        
        // Inicializar observador de intersección para animaciones
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('fade-in');
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            });
            
            // Observar elementos con clase enhanced
            document.querySelectorAll('.cardsmall-enhanced, .card-enhanced, .section-title-enhanced').forEach(el => {
                observer.observe(el);
            });
        }
        
        // Mejorar accesibilidad
        document.querySelectorAll('.read-more-btn').forEach(button => {
            button.setAttribute('aria-expanded', 'false');
            
            button.addEventListener('click', function() {
                const isExpanded = this.classList.contains('expanded');
                this.setAttribute('aria-expanded', isExpanded.toString());
            });
        });
        
        // Añadir indicadores de carga
        document.querySelectorAll('img').forEach(img => {
            if (!img.complete) {
                img.classList.add('loading');
                
                img.addEventListener('load', function() {
                    this.classList.remove('loading');
                    this.classList.add('loaded');
                });
                
                img.addEventListener('error', function() {
                    this.classList.remove('loading');
                    this.classList.add('error');
                });
            }
        });
        
    } catch (error) {
        console.error('Error al inicializar mejoras:', error);
    }
}

// Función para expandir contenido con fade overlay
function toggleExpandableContent(element) {
    try {
        const content = element.closest('.content-expandable');
        if (!content) return;
        
        const overlay = content.querySelector('.content-fade-overlay');
        const isCollapsed = content.classList.contains('collapsed');
        
        if (isCollapsed) {
            content.classList.remove('collapsed');
            content.classList.add('expanded');
            if (overlay) overlay.style.opacity = '0';
            element.textContent = 'Mostrar menos';
        } else {
            content.classList.remove('expanded');
            content.classList.add('collapsed');
            if (overlay) overlay.style.opacity = '1';
            element.textContent = 'Mostrar más';
        }
    } catch (error) {
        console.error('Error en toggleExpandableContent:', error);
    }
}

// Función para manejar el slideshow mejorado
function initializeSlideshow() {
    try {
        const slides = document.querySelectorAll('.slide');
        const dots = document.querySelectorAll('.dot');
        const prevBtn = document.querySelector('.prev-btn');
        const nextBtn = document.querySelector('.next-btn');
        let currentSlide = 0;
        let slideInterval;
        
        if (slides.length === 0) return;
        
        function showSlide(index) {
            slides.forEach((slide, i) => {
                slide.style.display = i === index ? 'block' : 'none';
            });
            
            dots.forEach((dot, i) => {
                dot.classList.toggle('active', i === index);
            });
            
            currentSlide = index;
        }
        
        function nextSlide() {
            showSlide((currentSlide + 1) % slides.length);
        }
        
        function prevSlide() {
            showSlide((currentSlide - 1 + slides.length) % slides.length);
        }
        
        function startAutoSlide() {
            slideInterval = setInterval(nextSlide, 5000);
        }
        
        function stopAutoSlide() {
            clearInterval(slideInterval);
        }
        
        // Event listeners
        if (nextBtn) nextBtn.addEventListener('click', () => {
            stopAutoSlide();
            nextSlide();
            startAutoSlide();
        });
        
        if (prevBtn) prevBtn.addEventListener('click', () => {
            stopAutoSlide();
            prevSlide();
            startAutoSlide();
        });
        
        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                stopAutoSlide();
                showSlide(index);
                startAutoSlide();
            });
        });
        
        // Pausar en hover
        const slideshowContainer = document.querySelector('.slideshow-container');
        if (slideshowContainer) {
            slideshowContainer.addEventListener('mouseenter', stopAutoSlide);
            slideshowContainer.addEventListener('mouseleave', startAutoSlide);
        }
        
        // Inicializar
        showSlide(0);
        startAutoSlide();
        
    } catch (error) {
        console.error('Error al inicializar slideshow:', error);
    }
}

// Función para cargar imágenes lazy loading
function initializeLazyLoading() {
    try {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.classList.remove('lazy');
                            imageObserver.unobserve(img);
                        }
                    }
                });
            });
            
            document.querySelectorAll('img[data-src]').forEach(img => {
                img.classList.add('lazy');
                imageObserver.observe(img);
            });
        }
    } catch (error) {
        console.error('Error al inicializar lazy loading:', error);
    }
}

// Función para mejorar formularios
function enhanceForms() {
    try {
        // Añadir clases enhanced a formularios existentes
        document.querySelectorAll('input[type="text"], input[type="email"], textarea, select').forEach(input => {
            input.addEventListener('focus', function() {
                this.closest('.form-group, .field')?.classList.add('focused');
            });
            
            input.addEventListener('blur', function() {
                this.closest('.form-group, .field')?.classList.remove('focused');
            });
        });
        
        // Validación mejorada
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', function(e) {
                const requiredFields = this.querySelectorAll('[required]');
                let isValid = true;
                
                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        field.classList.add('error');
                        isValid = false;
                    } else {
                        field.classList.remove('error');
                    }
                });
                
                if (!isValid) {
                    e.preventDefault();
                }
            });
        });
        
    } catch (error) {
        console.error('Error al mejorar formularios:', error);
    }
}

// Función para añadir funcionalidad de búsqueda mejorada
function enhanceSearch() {
    try {
        const searchInputs = document.querySelectorAll('input[type="search"], .search-input');
        
        searchInputs.forEach(input => {
            // Debounce para búsqueda en tiempo real
            let timeout;
            input.addEventListener('input', function() {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    // Aquí se puede añadir lógica de búsqueda en tiempo real
                    console.log('Searching for:', this.value);
                }, 300);
            });
            
            // Limpiar búsqueda
            const clearBtn = input.parentNode.querySelector('.search-clear');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    input.value = '';
                    input.focus();
                });
            }
        });
    } catch (error) {
        console.error('Error al mejorar búsqueda:', error);
    }
}

// Inicialización cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    initializeEnhancements();
    initializeSlideshow();
    initializeLazyLoading();
    enhanceForms();
    enhanceSearch();
});

// Inicialización adicional cuando la página esté completamente cargada
window.addEventListener('load', function() {
    // Remover spinners de carga
    document.querySelectorAll('.loading-spinner').forEach(spinner => {
        spinner.style.opacity = '0';
        setTimeout(() => spinner.remove(), 300);
    });
    
    // Añadir clase loaded al body
    document.body.classList.add('loaded');
});

// Exportar funciones para uso global
window.themeEnhanced = {
    toggleReadMore,
    toggleExpandableContent,
    initializeEnhancements,
    initializeSlideshow,
    initializeLazyLoading,
    enhanceForms,
    enhanceSearch
}; 