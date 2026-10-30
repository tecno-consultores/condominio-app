import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import DashboardView from './DashboardView.vue';
import { useAuthStore } from '../../stores/authStore';

const pushMock = vi.fn();

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/dashboard' }),
  useRouter: () => ({ push: pushMock }),
}));

describe('DashboardView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pushMock.mockReset();
  });

  it('renderiza saludo, badge de tasa BCV y FAB flotante sin colisión que navega a /finanzas/reportar-pago', async () => {
    const store = useAuthStore();
    store.setProfileForTesting({
      id: 2,
      nombre: 'Andrés Bello',
      cedula: 'V-100',
      correo: 'andres@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });

    const wrapper = mount(DashboardView);
    expect(wrapper.text()).toContain('Hola, Andrés Bello');
    expect(wrapper.find('#daily-rate-badge').exists()).toBe(true);

    await wrapper.find('#fab-reportar-pago').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/finanzas/reportar-pago');

    store.setProfileForTesting(null);
    const anonWrapper = mount(DashboardView);
    expect(anonWrapper.text()).toContain('Hola, Vecino');
  });
});
