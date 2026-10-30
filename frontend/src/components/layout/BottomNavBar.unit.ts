import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import BottomNavBar from './BottomNavBar.vue';

describe('BottomNavBar.vue (Ergonomía Mobile-First <= 4 ítems por rol)', () => {
  it('renderiza máximo 4 ítems adaptados al rol y emite navigate al hacer clic', async () => {
    const propWrapper = mount(BottomNavBar, {
      props: { role: 'PROPIETARIO', currentPath: '/dashboard' },
    });
    const buttons = propWrapper.findAll('button');
    expect(buttons.length).toBe(4);
    expect(buttons[0].attributes('aria-current')).toBe('page');

    await buttons[1].trigger('click');
    expect(propWrapper.emitted('navigate')?.[0]).toEqual(['/finanzas/reportar-pago']);

    const tesWrapper = mount(BottomNavBar, {
      props: { role: 'TESORERO', currentPath: '/tesoreria/pagos' },
    });
    expect(tesWrapper.text()).toContain('Aprobar Pagos');

    const presWrapper = mount(BottomNavBar, {
      props: { role: 'PRESIDENTE', currentPath: '/admin/usuarios' },
    });
    expect(presWrapper.text()).toContain('Usuarios');

    const consWrapper = mount(BottomNavBar, {
      props: { role: 'CONSERJE', currentPath: '/operaciones/tareas' },
    });
    expect(consWrapper.findAll('button').length).toBe(2);
  });
});
