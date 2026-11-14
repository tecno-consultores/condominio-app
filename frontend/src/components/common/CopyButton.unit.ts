import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import CopyButton from './CopyButton.vue';

describe('CopyButton.vue', () => {
  const attachedNodes: HTMLElement[] = [];

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    delete (window as unknown as Record<string, unknown>).CommandEvent;
    for (const node of attachedNodes.splice(0)) {
      node.remove();
    }
  });

  it('copia texto con navigator.clipboard, maneja anuncios repetidos y limpia tras 2000ms', async () => {
    const target = document.createElement('code');
    target.id = 'sample-digest';
    target.textContent = '  hmac_digest_0123  ';
    document.body.append(target);
    attachedNodes.push(target);

    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    const wrapper = mount(CopyButton, {
      props: {
        id: 'btn-copy-sample',
        targetId: 'sample-digest',
        label: 'Copiar digest',
      },
    });

    const button = wrapper.find('#btn-copy-sample');
    expect(button.attributes('command')).toBe('--copy');
    expect(button.attributes('commandfor')).toBe('sample-digest');
    expect(button.attributes('aria-label')).toBe('Copiar digest');

    await button.trigger('click');
    await flushPromises();
    vi.advanceTimersByTime(20);

    expect(writeText).toHaveBeenCalledWith('hmac_digest_0123');
    expect(button.attributes('data-copied')).toBe('');
    expect(wrapper.find('.copy-control__icon').text()).toBe('✓');
    const statusEl = wrapper.find('[role="status"]').element;
    const firstMsg = statusEl.textContent;
    expect(firstMsg).toBe('Copiado');

    // Segundo clic consecutivo limpia el temporizador anterior y diferencia anuncio para VoiceOver
    await button.trigger('click');
    await flushPromises();
    vi.advanceTimersByTime(20);
    const secondMsg = statusEl.textContent;
    expect(secondMsg).toBe('Copiado\u00A0');
    expect(secondMsg).not.toBe(firstMsg);

    // Al expirar 2000ms restablece atributos, ícono y texto del live region
    vi.advanceTimersByTime(2000);
    await flushPromises();
    expect(button.attributes('data-copied')).toBeUndefined();
    expect(wrapper.find('.copy-control__icon').text()).toBe('⧉');
    expect(statusEl.textContent).toBe('');

    // Otro clic pendiente antes de desmontar ejecuta limpieza en onBeforeUnmount
    await button.trigger('click');
    await flushPromises();
    wrapper.unmount();
  });

  it('copia valor desde input y usa fallback execCommand cuando clipboard falla o no existe', async () => {
    const input = document.createElement('input');
    input.id = 'sample-input';
    input.value = 'FOL-9988';
    document.body.append(input);
    attachedNodes.push(input);

    const writeText = vi.fn().mockRejectedValue(new Error('Clipboard blocked'));
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    const execSpy = vi.fn().mockReturnValue(true);
    Object.defineProperty(document, 'execCommand', {
      configurable: true,
      value: execSpy,
    });

    const wrapper = mount(CopyButton, {
      props: {
        id: 'btn-copy-input',
        targetId: 'sample-input',
        label: 'Copiar folio',
      },
    });

    await wrapper.find('#btn-copy-input').trigger('click');
    await flushPromises();
    vi.advanceTimersByTime(20);
    expect(execSpy).toHaveBeenCalledWith('copy');
    expect(wrapper.find('#btn-copy-input').attributes('data-copied')).toBe('');

    // Caso de fallo total en legacyCopy -> estado data-failed
    execSpy.mockReturnValueOnce(false);
    await wrapper.find('#btn-copy-input').trigger('click');
    await flushPromises();
    vi.advanceTimersByTime(20);
    expect(wrapper.find('#btn-copy-input').attributes('data-failed')).toBe('');
    expect(wrapper.find('.copy-control__icon').text()).toBe('!');
    expect(wrapper.find('[role="status"]').text()).toContain('Error al copiar');

    // Repetición inmediata de error añade \u00A0 para anuncio repetido
    execSpy.mockReturnValueOnce(false);
    await wrapper.find('#btn-copy-input').trigger('click');
    await flushPromises();
    vi.advanceTimersByTime(20);
    expect(wrapper.find('[role="status"]').element.textContent).toBe('Error al copiar\u00A0');
    wrapper.unmount();
  });

  it('soporta Invoker Commands (CommandEvent) sin duplicar copia en clic e ignora destinos vacíos', async () => {
    Object.defineProperty(window, 'CommandEvent', {
      configurable: true,
      value: class FakeCommandEvent extends Event {},
    });

    const emptyEl = document.createElement('div');
    emptyEl.id = 'empty-target';
    emptyEl.textContent = '   ';
    document.body.append(emptyEl);
    attachedNodes.push(emptyEl);

    const codeEl = document.createElement('code');
    codeEl.id = 'cmd-target';
    codeEl.textContent = 'cmd_token_ok';
    document.body.append(codeEl);
    attachedNodes.push(codeEl);

    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    const wrapper = mount(CopyButton, {
      props: {
        id: 'btn-cmd',
        targetId: 'missing-target',
        label: 'Copiar comando',
      },
    });

    // Click normal se ignora si CommandEvent existe
    await wrapper.find('#btn-cmd').trigger('click');
    expect(writeText).not.toHaveBeenCalled();

    // Evento command de otra fuente se ignora
    const otherEvent = new Event('command');
    Object.assign(otherEvent, { command: '--copy', source: document.body });
    codeEl.dispatchEvent(otherEvent);
    expect(writeText).not.toHaveBeenCalled();

    // Evento command del botón hacia target real ejecuta la copia una sola vez
    const validEvent = new Event('command');
    Object.assign(validEvent, {
      command: '--copy',
      source: wrapper.find('#btn-cmd').element,
    });
    codeEl.dispatchEvent(validEvent);
    await flushPromises();
    expect(writeText).toHaveBeenCalledTimes(1);
    expect(writeText).toHaveBeenCalledWith('cmd_token_ok');

    // Destino inexistente o vacío no escribe al portapapeles
    await wrapper.setProps({ targetId: 'empty-target' });
    const emptyEvent = new Event('command');
    Object.assign(emptyEvent, {
      command: '--copy',
      source: wrapper.find('#btn-cmd').element,
    });
    emptyEl.dispatchEvent(emptyEvent);
    await flushPromises();
    expect(writeText).toHaveBeenCalledTimes(1);

    wrapper.unmount();
  });
});
