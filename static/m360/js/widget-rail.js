/**
 * Widget Rail — gestión unificada de widgets flotantes (chat, inbox, tools)
 */
class WidgetRail {
  constructor() {
    this.widgets = new Map();
    this.activeWidgetId = null;
    this.initialized = false;

    this.init();
  }

  init() {
    if (this.initialized) return;
    this.initialized = true;

    document.addEventListener('keydown', (e) => this.handleGlobalShortcut(e));
    this.restoreState();
  }

  register(widget) {
    if (!widget || !widget.id) return;
    this.widgets.set(widget.id, {
      id: widget.id,
      label: widget.label || widget.id,
      icon: widget.icon || 'bi-grid',
      open: false,
      badge: 0,
      onToggle: widget.onToggle || null,
      onOpen: widget.onOpen || null,
      onClose: widget.onClose || null,
      onBadgeChange: widget.onBadgeChange || null,
    });
  }

  setBadge(widgetId, count) {
    const widget = this.widgets.get(widgetId);
    if (!widget) return;
    widget.badge = Math.max(0, count);

    const badgeEl = document.querySelector(`[data-widget-rail-badge="${widgetId}"]`);
    if (badgeEl) {
      badgeEl.textContent = String(widget.badge);
      badgeEl.style.display = widget.badge > 0 ? 'inline-flex' : 'none';
    }

    if (widget.onBadgeChange) {
      widget.onBadgeChange(widgetId, widget.badge);
    }
  }

  async toggle(widgetId) {
    if (this.activeWidgetId && this.activeWidgetId !== widgetId) {
      await this.close(this.activeWidgetId);
    }

    const widget = this.widgets.get(widgetId);
    if (!widget) return;

    if (widget.open) {
      await this.close(widgetId);
    } else {
      await this.open(widgetId);
    }
  }

  async open(widgetId) {
    const widget = this.widgets.get(widgetId);
    if (!widget || widget.open) return;

    if (this.activeWidgetId && this.activeWidgetId !== widgetId) {
      await this.close(this.activeWidgetId);
    }

    widget.open = true;
    this.activeWidgetId = widgetId;
    this.updateItemState(widgetId);
    this.updatePanelState(widgetId);

    if (widget.onOpen) {
      await widget.onOpen(widgetId);
    }

    this.persistState();
  }

  async close(widgetId) {
    const widget = this.widgets.get(widgetId);
    if (!widget || !widget.open) return;

    widget.open = false;
    if (this.activeWidgetId === widgetId) {
      this.activeWidgetId = null;
    }
    this.updateItemState(widgetId);
    this.updatePanelState(widgetId);

    if (widget.onClose) {
      await widget.onClose(widgetId);
    }

    this.persistState();
  }

  closeAll() {
    const ids = Array.from(this.widgets.keys());
    return Promise.all(ids.map((id) => this.close(id)));
  }

  updateItemState(widgetId) {
    const button = document.querySelector(`[data-widget-rail-item="${widgetId}"]`);
    if (!button) return;

    const widget = this.widgets.get(widgetId);
    button.setAttribute('aria-pressed', widget && widget.open ? 'true' : 'false');
  }

  updatePanelState(widgetId) {
    this.widgets.forEach((widget, id) => {
      const panel = document.querySelector(`[data-widget-rail-panel="${id}"]`);
      if (!panel) return;

      if (id === widgetId && widget.open) {
        panel.classList.add('is-open');
        panel.setAttribute('aria-hidden', 'false');
      } else {
        panel.classList.remove('is-open');
        panel.setAttribute('aria-hidden', 'true');
      }
    });
  }

  handleGlobalShortcut(e) {
    if (e.key === 'Escape' && this.activeWidgetId) {
      this.close(this.activeWidgetId);
      return;
    }

    if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
      e.preventDefault();
      if (this.activeWidgetId) {
        this.close(this.activeWidgetId);
      } else if (this.widgets.size > 0) {
        const first = Array.from(this.widgets.keys())[0];
        this.open(first);
      }
    }
  }

  persistState() {
    try {
      const state = {};
      this.widgets.forEach((widget, id) => {
        if (widget.open) {
          state[id] = true;
        }
      });
      localStorage.setItem('widgetRailState', JSON.stringify(state));
    } catch (e) {
      // noop
    }
  }

  restoreState() {
    try {
      const raw = localStorage.getItem('widgetRailState');
      if (!raw) return;
      const state = JSON.parse(raw);
      if (!state || typeof state !== 'object') return;

      const entries = Object.entries(state).filter(([id, open]) => {
        const widget = this.widgets.get(id);
        return widget && open;
      });

      if (entries.length > 0) {
        const [id] = entries[0];
        this.open(id).catch(() => {});
      }
    } catch (e) {
      // noop
    }
  }
}

window.WidgetRail = WidgetRail;
window.widgetRailInstance = null;
