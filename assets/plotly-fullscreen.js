/**
 * Plotly Fullscreen Modal
 * Adds fullscreen/expand buttons to all Plotly charts
 */
(function() {
    'use strict';

    // Create modal overlay (once)
    let modal = null;
    let modalChart = null;
    let currentPlotData = null;

    function createModal() {
        if (modal) return;

        modal = document.createElement('div');
        modal.className = 'plotly-modal-overlay';
        modal.innerHTML = `
            <div class="plotly-modal-content">
                <button class="plotly-modal-close" title="Fechar (Esc)">&times;</button>
                <div class="plotly-modal-chart" id="plotly-modal-chart"></div>
                <div class="plotly-modal-hint">Pressione ESC ou clique fora para fechar</div>
            </div>
        `;
        document.body.appendChild(modal);

        // Close button handler
        modal.querySelector('.plotly-modal-close').addEventListener('click', closeModal);

        // Click outside to close
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });

        // ESC key to close
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                closeModal();
            }
        });

        modalChart = document.getElementById('plotly-modal-chart');
    }

    function openModal(plotDiv) {
        createModal();

        // Get the plot data and layout from the original chart
        const data = plotDiv.data;
        const layout = JSON.parse(JSON.stringify(plotDiv.layout));

        // Adjust layout for fullscreen
        layout.width = null;
        layout.height = null;
        layout.autosize = true;

        // Increase font sizes for better readability in fullscreen
        if (layout.font) {
            layout.font.size = Math.max(14, (layout.font.size || 12) * 1.2);
        }
        if (layout.title && layout.title.font) {
            layout.title.font.size = Math.max(18, (layout.title.font.size || 16) * 1.2);
        }

        // Adjust margins for fullscreen
        layout.margin = layout.margin || {};
        layout.margin.l = Math.max(80, layout.margin.l || 70);
        layout.margin.r = Math.max(40, layout.margin.r || 30);
        layout.margin.t = Math.max(80, layout.margin.t || 70);
        layout.margin.b = Math.max(70, layout.margin.b || 60);

        // Show modal
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';

        // Render chart in modal
        const config = {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToAdd: ['hoverClosestCartesian', 'hoverCompareCartesian'],
            displaylogo: false
        };

        Plotly.newPlot(modalChart, data, layout, config);
        currentPlotData = { data, layout };
    }

    function closeModal() {
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';

            // Clean up the modal chart
            if (modalChart) {
                Plotly.purge(modalChart);
            }
            currentPlotData = null;
        }
    }

    function addFullscreenButton(plotDiv) {
        // Check if button already exists
        if (plotDiv.querySelector('.plotly-fullscreen-btn')) return;

        // Make sure the container has position relative for button positioning
        const computedStyle = window.getComputedStyle(plotDiv);
        if (computedStyle.position === 'static') {
            plotDiv.style.position = 'relative';
        }

        // Create fullscreen button
        const btn = document.createElement('button');
        btn.className = 'plotly-fullscreen-btn';
        btn.innerHTML = '⛶ Expandir';
        btn.title = 'Abrir em tela cheia';

        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            openModal(plotDiv);
        });

        plotDiv.appendChild(btn);
    }

    function initFullscreen() {
        // Find all Plotly charts
        const plots = document.querySelectorAll('.js-plotly-plot, .plotly-graph-div');
        plots.forEach(function(plot) {
            addFullscreenButton(plot);
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFullscreen);
    } else {
        // DOM already loaded
        initFullscreen();
    }

    // Also run after a short delay to catch dynamically created charts
    setTimeout(initFullscreen, 1000);
    setTimeout(initFullscreen, 3000);

    // Watch for new charts being added (MutationObserver)
    const observer = new MutationObserver(function(mutations) {
        let shouldInit = false;
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) { // Element node
                    if (node.classList &&
                        (node.classList.contains('js-plotly-plot') ||
                         node.classList.contains('plotly-graph-div'))) {
                        shouldInit = true;
                    }
                    // Also check children
                    if (node.querySelector && node.querySelector('.js-plotly-plot, .plotly-graph-div')) {
                        shouldInit = true;
                    }
                }
            });
        });
        if (shouldInit) {
            setTimeout(initFullscreen, 100);
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

})();
