import { describe, expect, it } from 'vitest';
import { getVisibleNavigationSections, NAVIGATION_LINKS } from './navigationCatalog';

describe('Catálogo compartido de navegación RBAC (navigationCatalog.ts)', () => {
  it('filtra correctamente enlaces administrativos y operativos según rol', () => {
    const propSections = getVisibleNavigationSections('PROPIETARIO');
    const propIds = propSections.flatMap((s) => s.links.map((l) => l.id));
    expect(propIds).toContain('side-dashboard');
    expect(propIds).toContain('side-consultas');
    expect(propIds).toContain('side-reservas');
    expect(propIds).toContain('side-pases-qr');
    expect(propIds).not.toContain('side-revision-pagos');
    expect(propIds).not.toContain('side-garita-qr');
    expect(propIds).not.toContain('side-junta');

    const presSections = getVisibleNavigationSections('PRESIDENTE');
    const presIds = presSections.flatMap((s) => s.links.map((l) => l.id));
    expect(presIds).toHaveLength(NAVIGATION_LINKS.length);

    const anonSections = getVisibleNavigationSections(null);
    const anonIds = anonSections.flatMap((s) => s.links.map((l) => l.id));
    expect(anonIds).not.toContain('side-junta');
  });
});
