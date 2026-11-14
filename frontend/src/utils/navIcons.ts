// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

export type NavIconKey =
  | 'home'
  | 'credit-card'
  | 'shield-check'
  | 'check-square'
  | 'calculator'
  | 'receipt'
  | 'alert-circle'
  | 'vote'
  | 'book-open'
  | 'users'
  | 'calendar'
  | 'qr-code'
  | 'scan'
  | 'package'
  | 'clipboard-check'
  | 'building'
  | 'user-check'
  | 'award';

export const NAV_ICON_PATHS: Record<NavIconKey, readonly string[]> = {
  home: ['M3 9.5 12 3l9 6.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1V9.5Z'],
  'credit-card': [
    'M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z',
    'M3 10h18',
    'M7 15h4',
  ],
  'shield-check': ['M12 3 4 6v6c0 5 3.4 8.4 8 9 4.6-.6 8-4 8-9V6l-8-3Z', 'm9 12 2 2 4-4'],
  'check-square': ['M9 11l3 3L20 6', 'M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9'],
  calculator: [
    'M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z',
    'M8 8h8',
    'M8 13h2',
    'M14 13h2',
    'M8 17h2',
    'M14 17h2',
  ],
  receipt: ['M6 3h12v18l-3-2-3 2-3-2-3 2V3Z', 'M9 8h6', 'M9 12h6', 'M9 16h4'],
  'alert-circle': ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M12 8v5', 'M12 16h.01'],
  vote: ['m9 12 2 2 4-4', 'M5 7c0-1.1.9-2 2-2h10a2 2 0 0 1 2 2v12H5V7Z', 'M3 19h18'],
  'book-open': [
    'M2 6a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v14a3 3 0 0 0-3-3H4a2 2 0 0 1-2-2V6Z',
    'M22 6a2 2 0 0 0-2-2h-6a2 2 0 0 0-2 2v14a3 3 0 0 1 3-3h5a2 2 0 0 0 2-2V6Z',
  ],
  users: [
    'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2',
    'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z',
    'M22 21v-2a4 4 0 0 0-3-3.87',
    'M16 3.13a4 4 0 0 1 0 7.75',
  ],
  calendar: [
    'M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6Z',
    'M8 2v4',
    'M16 2v4',
    'M4 10h16',
  ],
  'qr-code': [
    'M4 4h6v6H4V4Z',
    'M14 4h6v6h-6V4Z',
    'M4 14h6v6H4v-6Z',
    'M14 14h2v2h-2v-2Z',
    'M18 14h2v6h-6v-2',
  ],
  scan: [
    'M4 8V6a2 2 0 0 1 2-2h2',
    'M16 4h2a2 2 0 0 1 2 2v2',
    'M20 16v2a2 2 0 0 1-2 2h-2',
    'M8 20H6a2 2 0 0 1-2-2v-2',
    'M7 12h10',
  ],
  package: ['M12 3 4 7.5v9L12 21l8-4.5v-9L12 3Z', 'M12 12 4 7.5', 'M12 12l8-4.5', 'M12 12v9'],
  'clipboard-check': [
    'M9 4h6v3H9V4Z',
    'M7 6H5a1 1 0 0 0-1 1v13a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1h-2',
    'm9 14 2 2 4-4',
  ],
  building: [
    'M4 21h16',
    'M6 21V5a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v16',
    'M9 8h2',
    'M13 8h2',
    'M9 12h2',
    'M13 12h2',
    'M10 21v-4h4v4',
  ],
  'user-check': [
    'M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2',
    'M8.5 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z',
    'm17 11 2 2 4-4',
  ],
  award: ['M12 15a6 6 0 1 0 0-12 6 6 0 0 0 0 12Z', 'm9 14-1 7 4-2 4 2-1-7'],
};
