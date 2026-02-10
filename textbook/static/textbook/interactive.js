// interactive.js - Theme-aware interactive functionality

document.addEventListener('DOMContentLoaded', function () {
    // Quiz functionality
    initializeQuizSystem();
    
    // Theme-aware element updates
    updateThemeAwareElements();
    
    // Observe theme changes
    initializeThemeObserver();
    
    // Search and filter functionality
    initializeSearchSystems();
});

function initializeQuizSystem() {
    document.querySelectorAll('.opt-btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            const block = e.target.closest('.quiz-block');
            const selected = e.target.dataset.answer;

            // Disable all buttons in this quiz block
            block.querySelectorAll('.opt-btn').forEach(b => b.disabled = true);
            
            // Show result
            const result = block.querySelector('.quiz-result');
            result.style.display = 'block';
            result.textContent = 'Answer recorded (demo).';
            result.className = 'quiz-result info';
            
            // Add visual feedback
            e.target.classList.add('selected');
            
            // Theme-aware animation
            if (document.documentElement.getAttribute('data-theme') === 'dark') {
                e.target.style.boxShadow = '0 0 0 2px rgba(59, 130, 246, 0.5)';
            } else {
                e.target.style.boxShadow = '0 0 0 2px rgba(37, 99, 235, 0.3)';
            }
        });
    });
}

function updateThemeAwareElements() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    
    // Update quiz buttons
    document.querySelectorAll('.opt-btn').forEach(btn => {
        if (isDark) {
            btn.style.backgroundColor = 'var(--surface)';
            btn.style.color = 'var(--text)';
            btn.style.borderColor = 'var(--border)';
        } else {
            btn.style.backgroundColor = 'var(--surface)';
            btn.style.color = 'var(--text)';
            btn.style.borderColor = 'var(--border)';
        }
    });
    
    // Update code blocks if any
    const codeBlocks = document.querySelectorAll('pre code');
    codeBlocks.forEach(block => {
        if (isDark) {
            block.style.backgroundColor = '#1a202c';
            block.style.color = '#e2e8f0';
            block.style.border = '1px solid #2d3748';
        } else {
            block.style.backgroundColor = '#f7fafc';
            block.style.color = '#2d3748';
            block.style.border = '1px solid #e2e8f0';
        }
    });
    
    // Update any charts or visual elements
    const charts = document.querySelectorAll('.chart, .graph, .visualization');
    charts.forEach(chart => {
        if (isDark) {
            chart.style.filter = 'invert(1) hue-rotate(180deg) brightness(0.9)';
        } else {
            chart.style.filter = 'none';
        }
    });
}

function initializeThemeObserver() {
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.attributeName === 'data-theme') {
                updateThemeAwareElements();
                updateInteractiveColors();
            }
        });
    });
    
    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
    });
}

function updateInteractiveColors() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    
    // Update button hover effects based on theme
    const buttons = document.querySelectorAll('.btn, .opt-btn, .nav-link');
    buttons.forEach(btn => {
        if (isDark) {
            btn.style.setProperty('--hover-bg', 'rgba(59, 130, 246, 0.1)');
        } else {
            btn.style.setProperty('--hover-bg', 'rgba(37, 99, 235, 0.1)');
        }
    });
}

function initializeSearchSystems() {
    // Real-time search for notes
    const searchInputs = document.querySelectorAll('.search-input');
    searchInputs.forEach(input => {
        input.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const container = this.closest('.container');
            const items = container.querySelectorAll('.note-card, .lesson-card, .upload-card');
            
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    item.style.display = 'block';
                    // Highlight matching text
                    highlightText(item, searchTerm);
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });
}

function highlightText(element, searchTerm) {
    if (!searchTerm) return;
    
    const walker = document.createTreeWalker(
        element,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );
    
    let node;
    while (node = walker.nextNode()) {
        const parent = node.parentNode;
        if (parent.nodeName === 'MARK') continue;
        
        const index = node.textContent.toLowerCase().indexOf(searchTerm);
        if (index >= 0) {
            const span = document.createElement('mark');
            span.style.backgroundColor = 'var(--accent)';
            span.style.color = 'var(--text)';
            span.style.padding = '0.1rem 0.2rem';
            span.style.borderRadius = '2px';
            
            const middle = node.splitText(index);
            const end = middle.splitText(searchTerm.length);
            
            const highlighted = middle.cloneNode(true);
            span.appendChild(highlighted);
            parent.replaceChild(span, middle);
        }
    }
}

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Loading states for buttons
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function() {
        const submitBtn = this.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<div class="loading-spinner"></div> Loading...';
        }
    });
});

// Auto-resize textareas
document.querySelectorAll('textarea').forEach(textarea => {
    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
    
    // Trigger initial resize
    textarea.dispatchEvent(new Event('input'));
});