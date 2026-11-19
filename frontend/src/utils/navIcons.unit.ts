// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { NAV_ICON_PATHS, type NavIconKey } from './navIcons';

const EXPECTED_NAV_ICON_KEYS: readonly NavIconKey[] = [
  'home',
  'credit-card',
  'shield-check',
  'check-square',
  'calculator',
  'receipt',
  'alert-circle',
  'vote',
  'book-open',
  'users',
  'calendar',
  'qr-code',
  'scan',
  'package',
  'clipboard-check',
  'building',
  'user-check',
  'award',
];

describe('navIcons', () => {
  it('expone trazados SVG válidos no vacíos para las 18 claves del catálogo', () => {
    const keys = Object.keys(NAV_ICON_PATHS).sort();
    expect(keys).toEqual([...EXPECTED_NAV_ICON_KEYS].sort());
    for (const key of EXPECTED_NAV_ICON_KEYS) {
      const paths = NAV_ICON_PATHS[key];
      expect(Array.isArray(paths)).toBe(true);
      expect(paths.length).toBeGreaterThan(0);
      for (const d of paths) {
        expect(typeof d).toBe('string');
        expect(d.trim().length).toBeGreaterThan(0);
      }
    }
  });
});
