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
            textSpan.textContent = textSpan.getAttribute('data-more-text') || 'Read more';
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
            textSpan.textContent = textSpan.getAttribute('data-less-text') || 'Read less';
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
            element.textContent = 'Show less';
        } else {
            content.classList.remove('expanded');
            content.classList.add('collapsed');
            if (overlay) overlay.style.opacity = '1';
            element.textContent = 'Show more';
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

// Función para manejar el toggle del menú mobile
function initializeMobileNavigation() {
    try {
        const toggleButtons = document.querySelectorAll('.navbar-toggle, .navbar-toggler');
        // Intentar múltiples selectores para encontrar el contenedor del menú
        let navContainer = document.querySelector('.masthead-nav') || 
                          document.querySelector('.navigation') || 
                          document.querySelector('.nav-collapse') ||
                          document.querySelector('.navbar-collapse');
        
        console.log('Inicializando navegación mobile:', {
            toggleButtons: toggleButtons.length,
            navContainer: !!navContainer,
            navContainerSelector: navContainer ? navContainer.className : 'not found'
        });
        
        toggleButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Toggle button clicked');
                console.log('Current navContainer classes:', navContainer ? navContainer.className : 'no container');
                
                if (navContainer) {
                    // Debug: verificar todas las clases actuales
                    const currentClasses = Array.from(navContainer.classList);
                    console.log('Current classes:', currentClasses);
                    
                    // Verificar múltiples clases posibles para estado abierto
                    const isCurrentlyShown = navContainer.classList.contains('show') ||
                                           navContainer.classList.contains('in') ||
                                           navContainer.classList.contains('open') ||
                                           navContainer.classList.contains('active');
                    
                    console.log('Is currently shown?', isCurrentlyShown);
                    
                    if (isCurrentlyShown) {
                        navContainer.classList.remove('show', 'in', 'open', 'active');
                        navContainer.style.display = ''; // Reset display style
                        console.log('Menú cerrado - clases removidas');
                    } else {
                        navContainer.classList.add('show', 'in');
                        console.log('Menú abierto - clases agregadas');
                    }
                    
                    // Debug: verificar clases después del cambio
                    const newClasses = Array.from(navContainer.classList);
                    console.log('New classes:', newClasses);
                    
                    // Actualizar aria-expanded basado en el nuevo estado
                    const isExpanded = navContainer.classList.contains('show') || navContainer.classList.contains('in');
                    this.setAttribute('aria-expanded', isExpanded.toString());
                    console.log('Aria-expanded set to:', isExpanded);
                }
            });
        });
        
        // Cerrar menú mobile al hacer click en un link
        const mobileNavLinks = document.querySelectorAll('.masthead-nav .navigation .nav a, .navigation .nav a, .navbar-nav a');
        mobileNavLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (navContainer && window.innerWidth <= 768) {
                    navContainer.classList.remove('show', 'in', 'open', 'active');
                    navContainer.style.display = '';
                    toggleButtons.forEach(btn => {
                        btn.setAttribute('aria-expanded', 'false');
                    });
                    console.log('Menú cerrado por click en link');
                }
            });
        });
        
        // Cerrar menú mobile al cambiar tamaño de ventana
        window.addEventListener('resize', function() {
            if (window.innerWidth > 768 && navContainer) {
                navContainer.classList.remove('show', 'in', 'open', 'active');
                navContainer.style.display = '';
                toggleButtons.forEach(btn => {
                    btn.setAttribute('aria-expanded', 'false');
                });
                console.log('Menú cerrado por resize');
            }
        });
        
    } catch (error) {
        console.error('Error inicializando navegación móvil:', error);
    }
}

// Normaliza enlaces de compartir para usar URL absolutas (Twitter/Facebook)
function fixShareLinks() {
    try {
        const origin = window.location.origin;
        const selectors = 'a[href*="twitter.com/share"], a[href*="facebook.com/sharer"], a[href*="facebook.com/dialog/share"]';
        document.querySelectorAll(selectors).forEach(link => {
            const href = link.getAttribute('href') || '';
            const match = href.match(/(url|u)=([^&]+)/i);
            if (!match) return;
            const paramKey = match[1];
            const current = decodeURIComponent(match[2]);
            // If already absolute, skip
            if (/^https?:\/\//i.test(current)) return;
            const absoluteUrl = new URL(current, origin).href;
            const newHref = href.replace(match[0], `${paramKey}=${encodeURIComponent(absoluteUrl)}`);
            link.setAttribute('href', newHref);
            link.setAttribute('title', absoluteUrl);
        });
    } catch (error) {
        console.error('Error fixing share links:', error);
    }
}

// Rellena el campo URIRef/Permalink si viene vacío
function fixUriRefFields() {
    try {
        const currentUrl = window.location.href.split('#')[0];
        const inputs = document.querySelectorAll('.permanav input[type="text"], .permanav input[type="url"], input#permalink, input.permalink, input.permalink-input');
        inputs.forEach(input => {
            const value = (input.value || '').trim();
            if (!value) {
                input.value = currentUrl;
            }
            input.setAttribute('title', input.value);
        });

        const links = document.querySelectorAll('.permanav a.permalink, .permalink-label a');
        links.forEach(link => {
            const hasHref = (link.getAttribute('href') || '').trim().length > 0;
            const hasText = (link.textContent || '').trim().length > 0;
            if (!hasHref) {
                link.setAttribute('href', currentUrl);
            }
            if (!hasText) {
                link.textContent = currentUrl;
            }
            link.setAttribute('title', link.textContent);
        });
    } catch (error) {
        console.error('Error fixing URIRef fields:', error);
    }
}

// Inicialización cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    initializeEnhancements();
    initializeSlideshow();
    initializeLazyLoading();
    enhanceForms();
    enhanceSearch();
    initializeMobileNavigation();
    fixShareLinks();
    fixUriRefFields();
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
    enhanceSearch,
    initializeMobileNavigation
}; 
// ===== BOOTSTRAP 5 COMPATIBILITY FIX =====
// Convert data-toggle to data-bs-toggle for Bootstrap 5 compatibility
document.addEventListener('DOMContentLoaded', function() {
    // Fix dropdown toggles
    document.querySelectorAll('[data-toggle="dropdown"]').forEach(function(el) {
        if (!el.hasAttribute('data-bs-toggle')) {
            el.setAttribute('data-bs-toggle', 'dropdown');
        }
    });
    
    // Fix collapse toggles
    document.querySelectorAll('[data-toggle="collapse"]').forEach(function(el) {
        if (!el.hasAttribute('data-bs-toggle')) {
            el.setAttribute('data-bs-toggle', 'collapse');
        }
    });
    
    // Fix modal toggles
    document.querySelectorAll('[data-toggle="modal"]').forEach(function(el) {
        if (!el.hasAttribute('data-bs-toggle')) {
            el.setAttribute('data-bs-toggle', 'modal');
        }
    });
    
    // Fix tab toggles
    document.querySelectorAll('[data-toggle="tab"]').forEach(function(el) {
        if (!el.hasAttribute('data-bs-toggle')) {
            el.setAttribute('data-bs-toggle', 'tab');
        }
    });
    
    // Fix tooltip toggles
    document.querySelectorAll('[data-toggle="tooltip"]').forEach(function(el) {
        if (!el.hasAttribute('data-bs-toggle')) {
            el.setAttribute('data-bs-toggle', 'tooltip');
        }
    });
    
    // Initialize Bootstrap 5 dropdowns
    if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
        document.querySelectorAll('[data-bs-toggle="dropdown"]').forEach(function(el) {
            new bootstrap.Dropdown(el);
        });
    }
    
    console.log('Bootstrap 5 compatibility fix applied');
});

/* ============================================================
   Scroll Reveal — IntersectionObserver para animar secciones
   al entrar en el viewport
   ============================================================ */
(function() {
    'use strict';

    function initScrollReveal() {
        // Verificar soporte del navegador
        if (!('IntersectionObserver' in window)) {
            // Fallback: mostrar todo de inmediato
            document.querySelectorAll('.reveal-section, .reveal-item').forEach(function(el) {
                el.classList.add('revealed');
            });
            return;
        }

        // Respetar preferencia de movimiento reducido
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            document.querySelectorAll('.reveal-section, .reveal-item').forEach(function(el) {
                el.classList.add('revealed');
            });
            return;
        }

        var revealObserver = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        // Observar secciones y items
        document.querySelectorAll('.reveal-section, .reveal-item').forEach(function(el) {
            revealObserver.observe(el);
        });
    }

    /* ============================================================
       Stats Bar — Animación de contadores
       ============================================================ */
    function initStatsCounter() {
        var statsBar = document.querySelector('.homepage-stats-bar');
        if (!statsBar) return;

        var counters = statsBar.querySelectorAll('.stats-bar-number strong');
        if (!counters.length) return;

        var animated = false;

        function animateCounters() {
            if (animated) return;
            animated = true;

            counters.forEach(function(counter) {
                var target = parseInt(counter.textContent.replace(/[^0-9]/g, ''), 10);
                if (isNaN(target) || target === 0) return;

                var duration = 1500;
                var start = 0;
                var startTime = null;

                function step(timestamp) {
                    if (!startTime) startTime = timestamp;
                    var progress = Math.min((timestamp - startTime) / duration, 1);
                    // Easing: ease-out cubic
                    var eased = 1 - Math.pow(1 - progress, 3);
                    var current = Math.floor(eased * target);
                    counter.textContent = current.toLocaleString();
                    if (progress < 1) {
                        requestAnimationFrame(step);
                    } else {
                        counter.textContent = target.toLocaleString();
                    }
                }

                counter.textContent = '0';
                requestAnimationFrame(step);
            });
        }

        if ('IntersectionObserver' in window) {
            var observer = new IntersectionObserver(function(entries) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        animateCounters();
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.3 });
            observer.observe(statsBar);
        } else {
            animateCounters();
        }
    }

    /* ============================================================
       Tabs accesibles de los hubs del home (explore/community)
       Los paneles se renderizan server-side; sin JS se apilan
       visibles (el CSS solo los oculta bajo html.js)
       ============================================================ */
    function initHomeTabs() {
        document.querySelectorAll('[data-tabs]').forEach(function(root) {
            var tabs = Array.prototype.slice.call(
                root.querySelectorAll('[role="tab"]'));
            var panels = Array.prototype.slice.call(
                root.querySelectorAll('[role="tabpanel"]'));
            if (!tabs.length || !panels.length) return;

            function activate(tab, focus) {
                tabs.forEach(function(t) {
                    var on = t === tab;
                    t.setAttribute('aria-selected', on ? 'true' : 'false');
                    t.tabIndex = on ? 0 : -1;
                });
                panels.forEach(function(p) {
                    p.classList.toggle(
                        'is-active', p.id === tab.getAttribute('aria-controls'));
                });
                if (focus) tab.focus();
            }

            tabs.forEach(function(tab, i) {
                tab.addEventListener('click', function() { activate(tab, false); });
                tab.addEventListener('keydown', function(e) {
                    var dir = e.key === 'ArrowRight' ? 1 :
                              e.key === 'ArrowLeft' ? -1 : 0;
                    if (!dir) return;
                    e.preventDefault();
                    activate(tabs[(i + dir + tabs.length) % tabs.length], true);
                });
            });
        });
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initScrollReveal();
            initStatsCounter();
            initHomeTabs();
        });
    } else {
        initScrollReveal();
        initStatsCounter();
        initHomeTabs();
    }
})();
