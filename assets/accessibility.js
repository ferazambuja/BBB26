/**
 * Accessibility Toggle for BBB26 Dashboard
 * Provides colorblind-friendly mode (blue-orange instead of red-green)
 */

(function() {
  'use strict';

  const STORAGE_KEY = 'bbb26-colorblind-mode';

  // Create toggle button
  function createToggleButton() {
    const button = document.createElement('button');
    button.className = 'a11y-toggle';
    button.setAttribute('aria-label', 'Alternar modo daltonismo');
    button.setAttribute('aria-pressed', 'false');
    button.setAttribute('title', 'Modo daltonismo (azul-laranja)');
    button.innerHTML = `
      <span class="icon-normal">👁️</span>
      <span class="icon-active">🔵</span>
    `;

    button.addEventListener('click', toggleColorblindMode);
    document.body.appendChild(button);

    return button;
  }

  // Create indicator badge
  function createIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'a11y-indicator';
    indicator.textContent = 'Modo daltonismo ativo';
    document.body.appendChild(indicator);
    return indicator;
  }

  // Toggle colorblind mode
  function toggleColorblindMode() {
    const isActive = document.body.classList.toggle('colorblind-mode');
    const button = document.querySelector('.a11y-toggle');

    if (button) {
      button.setAttribute('aria-pressed', isActive.toString());
    }

    // Save preference
    localStorage.setItem(STORAGE_KEY, isActive ? 'true' : 'false');

    // Recolor Plotly charts
    recolorPlotlyCharts(isActive);
  }

  // Recolor Plotly charts for colorblind mode
  function recolorPlotlyCharts(isColorblind) {
    const plots = document.querySelectorAll('.js-plotly-plot');

    plots.forEach(plot => {
      if (!plot.data) return;

      const newData = plot.data.map(trace => {
        const newTrace = {...trace};

        // Replace colors in marker
        if (newTrace.marker) {
          newTrace.marker = recolorMarker(newTrace.marker, isColorblind);
        }

        // Replace line colors
        if (newTrace.line && newTrace.line.color) {
          newTrace.line.color = replaceColor(newTrace.line.color, isColorblind);
        }

        return newTrace;
      });

      try {
        Plotly.react(plot, newData, plot.layout);
      } catch (e) {
        // Plotly not available or chart not interactive
      }
    });
  }

  // Recolor marker object
  function recolorMarker(marker, isColorblind) {
    const newMarker = {...marker};

    if (newMarker.color) {
      if (Array.isArray(newMarker.color)) {
        newMarker.color = newMarker.color.map(c => replaceColor(c, isColorblind));
      } else {
        newMarker.color = replaceColor(newMarker.color, isColorblind);
      }
    }

    if (newMarker.colors) {
      newMarker.colors = newMarker.colors.map(c => replaceColor(c, isColorblind));
    }

    return newMarker;
  }

  // Replace individual color
  function replaceColor(color, isColorblind) {
    if (!color || typeof color !== 'string') return color;

    const colorLower = color.toLowerCase();

    if (isColorblind) {
      // Red -> Orange
      if (colorLower === '#e6194b' || colorLower.includes('230, 25, 75')) {
        return '#E65100';
      }
      // Green -> Blue
      if (colorLower === '#3cb44b' || colorLower === '#4caf50' ||
          colorLower.includes('60, 180, 75') || colorLower.includes('76, 175, 80')) {
        return '#1976D2';
      }
    } else {
      // Restore original colors
      if (colorLower === '#e65100') {
        return '#E6194B';
      }
      if (colorLower === '#1976d2') {
        return '#3CB44B';
      }
    }

    return color;
  }

  // Load saved preference
  function loadPreference() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'true') {
      document.body.classList.add('colorblind-mode');
      const button = document.querySelector('.a11y-toggle');
      if (button) {
        button.setAttribute('aria-pressed', 'true');
      }
      // Delay recoloring to allow Plotly charts to initialize
      setTimeout(() => recolorPlotlyCharts(true), 1000);
    }
  }

  // Initialize
  function init() {
    createToggleButton();
    createIndicator();
    loadPreference();
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
