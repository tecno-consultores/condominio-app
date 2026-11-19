import { defineComponent, ref } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useTopLayerDialog } from './useTopLayerDialog';
import { resetDisplayTransitionProbeForTests } from './useViewTransition';

function mockDialogRect(dialog: HTMLDialogElement, overrides: Partial<DOMRect> = {}) {
  return vi.spyOn(dialog, 'getBoundingClientRect').mockReturnValue({
    top: 100,
    left: 100,
    right: 400,
    bottom: 300,
    width: 300,
    height: 200,
    x: 100,
    y: 100,
    toJSON: () => ({}),
    ...overrides,
  });
}

function mountDialogHost(options: { open: boolean; unmountsWhenClosed?: boolean }) {
  const onClose = vi.fn();
  const dialogRef = ref<HTMLDialogElement | null>(null);
  const TestHost = defineComponent({
    props: { open: { type: Boolean, required: true } },
    setup(props) {
      const top = useTopLayerDialog({
        dialogRef,
        isOpen: () => props.open,
        onClose,
        unmountsWhenClosed: options.unmountsWhenClosed,
      });
      return { dialogRef, ...top };
    },
    template: [
      '<dialog ref="dialogRef" v-bind="dialogProps" @pointerdown="onPointerDown"',
      ' @pointerup="onPointerUp" @click="onBackdropClick"><p>Contenido</p></dialog>',
    ].join(''),
  });
  const wrapper = mount(TestHost, { props: { open: options.open } });
  return { wrapper, dialogRef, onClose };
}

describe('useTopLayerDialog — Modal Top-Layer nativo y fallback light-dismiss', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
      this.setAttribute('open', '');
    });
    HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
      this.removeAttribute('open');
    });
  });

  afterEach(() => {
    delete (HTMLDialogElement.prototype as unknown as Record<string, unknown>).closedBy;
    delete (Element.prototype as Partial<Element>).getAnimations;
    resetDisplayTransitionProbeForTests();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('abre con showModal, cierra con closeTopLayerDialog y soporta light-dismiss fuera del backdrop', async () => {
    const { wrapper, onClose } = mountDialogHost({ open: true });
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalledTimes(1);

    const dialogEl = wrapper.find('dialog').element as HTMLDialogElement;
    vi.spyOn(dialogEl, 'getBoundingClientRect').mockReturnValue({
      top: 100,
      left: 100,
      right: 400,
      bottom: 300,
      width: 300,
      height: 200,
      x: 100,
      y: 100,
      toJSON: () => ({}),
    });

    // Click directo dentro del contenido no cierra
    await wrapper.find('dialog').trigger('click', { clientX: 200, clientY: 200 });
    expect(onClose).not.toHaveBeenCalled();

    // PointerDown + PointerUp fuera del rectángulo dispara onClose
    await wrapper.find('dialog').trigger('pointerdown', { clientX: 10, clientY: 10 });
    await wrapper.find('dialog').trigger('pointerup', { clientX: 10, clientY: 10 });
    expect(onClose).toHaveBeenCalledTimes(1);

    // Click fallback directo sobre backdrop sin pointerDown previo
    await wrapper.find('dialog').trigger('click', { clientX: 20, clientY: 20 });
    expect(onClose).toHaveBeenCalledTimes(2);

    await wrapper.setProps({ open: false });
    await flushPromises();
    expect(HTMLDialogElement.prototype.close).toHaveBeenCalled();
  });

  it('evalúa con precisión los 4 lados, los bordes exactos y rectángulos sin área', async () => {
    const { wrapper, onClose } = mountDialogHost({ open: true });
    const dialogEl = wrapper.find('dialog').element as HTMLDialogElement;
    const rectSpy = mockDialogRect(dialogEl);

    // Puntos sobre cada borde exacto no disparan onClose
    const exactEdges: Array<[number, number]> = [
      [100, 200],
      [400, 200],
      [200, 100],
      [200, 300],
    ];
    for (const [clientX, clientY] of exactEdges) {
      await wrapper.find('dialog').trigger('click', { clientX, clientY });
    }
    expect(onClose).not.toHaveBeenCalled();

    // Un único eje fuera en cada uno de los 4 lados dispara onClose
    const outsideSides: Array<[number, number]> = [
      [50, 200],
      [450, 200],
      [200, 50],
      [200, 350],
    ];
    for (const [clientX, clientY] of outsideSides) {
      await wrapper.find('dialog').trigger('click', { clientX, clientY });
    }
    expect(onClose).toHaveBeenCalledTimes(4);

    // Rectángulo con ancho 0 y alto > 0 no dispara onClose
    rectSpy.mockReturnValue({
      top: 100,
      left: 100,
      right: 100,
      bottom: 300,
      width: 0,
      height: 200,
      x: 100,
      y: 100,
      toJSON: () => ({}),
    });
    await wrapper.find('dialog').trigger('click', { clientX: 10, clientY: 200 });
    expect(onClose).toHaveBeenCalledTimes(4);

    // Rectángulo con alto 0 y ancho > 0 no dispara onClose
    rectSpy.mockReturnValue({
      top: 100,
      left: 100,
      right: 400,
      bottom: 100,
      width: 300,
      height: 0,
      x: 100,
      y: 100,
      toJSON: () => ({}),
    });
    await wrapper.find('dialog').trigger('click', { clientX: 200, clientY: 10 });
    expect(onClose).toHaveBeenCalledTimes(4);
  });

  it('no abre al montar cerrado y diferencia cierre animado vs unmountsWhenClosed', async () => {
    resetDisplayTransitionProbeForTests();
    Element.prototype.getAnimations = vi.fn().mockReturnValue([{ finished: Promise.resolve() }]);

    const nonUnmounting = mountDialogHost({ open: false, unmountsWhenClosed: false });
    expect(HTMLDialogElement.prototype.showModal).not.toHaveBeenCalled();

    await nonUnmounting.wrapper.setProps({ open: true });
    await flushPromises();
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalledTimes(1);

    const dialogA = nonUnmounting.wrapper.find('dialog').element as HTMLDialogElement;
    let resolveExit!: () => void;
    const exitAnim = {
      finished: new Promise<void>((resolve) => {
        resolveExit = resolve;
      }),
    } as unknown as Animation;
    dialogA.getAnimations = vi.fn().mockReturnValue([exitAnim]);

    // Con unmountsWhenClosed=false espera closeTopLayerDialog antes de llamar close()
    await nonUnmounting.wrapper.setProps({ open: false });
    await flushPromises();
    expect(dialogA.hasAttribute('data-closing')).toBe(true);
    expect(HTMLDialogElement.prototype.close).not.toHaveBeenCalled();

    resolveExit();
    await flushPromises();
    expect(dialogA.hasAttribute('data-closing')).toBe(false);
    expect(HTMLDialogElement.prototype.close).toHaveBeenCalledTimes(1);

    // Con unmountsWhenClosed=true llama close() de inmediato sin data-closing
    const unmounting = mountDialogHost({ open: true, unmountsWhenClosed: true });
    const dialogB = unmounting.wrapper.find('dialog').element as HTMLDialogElement;
    const stuckAnim = {
      finished: new Promise<void>(() => undefined),
    } as unknown as Animation;
    dialogB.getAnimations = vi.fn().mockReturnValue([stuckAnim]);

    await unmounting.wrapper.setProps({ open: false });
    await flushPromises();
    expect(dialogB.hasAttribute('data-closing')).toBe(false);
    expect(HTMLDialogElement.prototype.close).toHaveBeenCalledTimes(2);
  });

  it('tolera dialogRef null o ausencia de close al pasar open a false', async () => {
    const nonUnmounting = mountDialogHost({ open: true, unmountsWhenClosed: false });
    nonUnmounting.dialogRef.value = null;
    await nonUnmounting.wrapper.setProps({ open: false });
    await flushPromises();
    expect(HTMLDialogElement.prototype.close).not.toHaveBeenCalled();

    const unmounting = mountDialogHost({ open: true, unmountsWhenClosed: true });
    unmounting.dialogRef.value = null;
    await unmounting.wrapper.setProps({ open: false });
    await flushPromises();
    expect(HTMLDialogElement.prototype.close).not.toHaveBeenCalled();

    const missingClose = mountDialogHost({ open: true, unmountsWhenClosed: true });
    const dialogEl = missingClose.wrapper.find('dialog').element as HTMLDialogElement;
    Object.defineProperty(dialogEl, 'close', { configurable: true, value: undefined });
    await missingClose.wrapper.setProps({ open: false });
    await flushPromises();
    expect(dialogEl.open).toBe(true);
  });

  it('respeta closedBy nativo y tolera dialogRef null en pointerdown y pointerup', async () => {
    const { wrapper, dialogRef, onClose } = mountDialogHost({ open: true });
    const dialogEl = wrapper.find('dialog').element as HTMLDialogElement;
    mockDialogRect(dialogEl);

    // Con closedBy nativo, pointerdown/pointerup/click no disparan onClose ni fijan estado
    Object.defineProperty(HTMLDialogElement.prototype, 'closedBy', {
      configurable: true,
      value: 'any',
    });
    await wrapper.find('dialog').trigger('pointerdown', { clientX: 10, clientY: 10 });
    await wrapper.find('dialog').trigger('pointerup', { clientX: 10, clientY: 10 });
    await wrapper.find('dialog').trigger('click', { clientX: 10, clientY: 10 });
    expect(onClose).not.toHaveBeenCalled();

    // Al retirar closedBy nativo, un pointerup sin pointerdown previo válido no cierra
    delete (HTMLDialogElement.prototype as unknown as Record<string, unknown>).closedBy;
    await wrapper.find('dialog').trigger('pointerup', { clientX: 10, clientY: 10 });
    expect(onClose).not.toHaveBeenCalled();

    // Si pointerdown fija pressedOutside y luego hay closedBy nativo, pointerup retorna temprano
    await wrapper.find('dialog').trigger('pointerdown', { clientX: 10, clientY: 10 });
    Object.defineProperty(HTMLDialogElement.prototype, 'closedBy', {
      configurable: true,
      value: 'any',
    });
    await wrapper.find('dialog').trigger('pointerup', { clientX: 10, clientY: 10 });
    expect(onClose).not.toHaveBeenCalled();
    delete (HTMLDialogElement.prototype as unknown as Record<string, unknown>).closedBy;

    // Con dialogRef=null y pressedOutside=true, pointerup y pointerdown no lanzan error
    dialogRef.value = null;
    await wrapper.find('dialog').trigger('pointerup', { clientX: 10, clientY: 10 });
    await wrapper.find('dialog').trigger('pointerdown', { clientX: 10, clientY: 10 });
    await wrapper.find('dialog').trigger('click', { clientX: 10, clientY: 10 });
    expect(onClose).not.toHaveBeenCalled();
  });

  it('funciona cuando HTMLDialogElement es undefined (SSR / entorno parcial)', async () => {
    const { wrapper, onClose } = mountDialogHost({ open: true });
    const dialogEl = wrapper.find('dialog').element as HTMLDialogElement;
    mockDialogRect(dialogEl);

    vi.stubGlobal('HTMLDialogElement', undefined);
    try {
      await wrapper.find('dialog').trigger('click', { clientX: 10, clientY: 10 });
    } finally {
      vi.unstubAllGlobals();
    }
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
