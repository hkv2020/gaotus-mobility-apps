import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeBuilderInput, normalizeTarget } from '../scripts/normalize-builder-input.mjs';

test('hash navigation target is normalized against remote base URL', () => {
  assert.equal(normalizeTarget('#', 'https://example.com/'), 'https://example.com/#');
  assert.equal(normalizeTarget('#cart', 'https://example.com/app/'), 'https://example.com/app/#cart');
});

test('query target is normalized against remote base URL', () => {
  assert.equal(normalizeTarget('?s=test', 'https://example.com/'), 'https://example.com/?s=test');
});

test('relative and absolute targets remain unchanged', () => {
  assert.equal(normalizeTarget('/cart', 'https://example.com/'), '/cart');
  assert.equal(normalizeTarget('https://other.example/path', 'https://example.com/'), 'https://other.example/path');
});

test('builder navigation placeholders normalize before config validation', () => {
  const out = normalizeBuilderInput({
    mode: 'remote',
    url: 'https://example.com/',
    uiNavigation: {
      bottom_nav_items: [
        { label: 'Home', url: '/', icon: 'home' },
        { label: 'Alerts', url: '#', icon: 'bell' },
        { label: 'Cart', url: '#cart', icon: 'cart' }
      ]
    }
  });
  assert.equal(out.uiNavigation.bottom_nav_items[1].url, 'https://example.com/#');
  assert.equal(out.uiNavigation.bottom_nav_items[2].url, 'https://example.com/#cart');
});
