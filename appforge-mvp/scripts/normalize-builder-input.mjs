const clone = (value) => structuredClone(value);

function normalizeTarget(value, baseUrl) {
  const s = String(value ?? '').trim();
  if (!s) return s;
  if (s.startsWith('/') || /^https?:\/\//i.test(s) || /^\{\{ENV[.:][A-Z][A-Z0-9_]*\}\}/.test(s)) return s;
  if (s.startsWith('#') || s.startsWith('?')) {
    const base = String(baseUrl || '').replace(/\/+$/, '');
    return base ? `${base}/${s}` : '/';
  }
  return s;
}

export function normalizeBuilderInput(input) {
  const out = clone(input || {});
  const baseUrl = out.mode === 'remote' ? out.url : '';
  const ui = out.uiNavigation && typeof out.uiNavigation === 'object' ? out.uiNavigation : null;
  if (ui) {
    for (const key of ['bottom_nav_items', 'sidebar_items']) {
      if (Array.isArray(ui[key])) {
        ui[key] = ui[key].map((item) => item && typeof item === 'object'
          ? { ...item, url: normalizeTarget(item.url, baseUrl) }
          : item);
      }
    }
    for (const key of ['floating_button_url', 'header_search_url']) {
      if (key in ui) ui[key] = normalizeTarget(ui[key], baseUrl);
    }
  }
  return out;
}

export { normalizeTarget };
