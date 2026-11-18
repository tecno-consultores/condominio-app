import { defineComponent, ref } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTopLayerDialog } from './useTopLayerDialog';

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

  it('abre con showModal, cierra con closeTopLayerDialog y soporta light-dismiss fuera del backdrop', async () => {
    const onClose = vi.fn();
    const TestHost = defineComponent({
      props: { open: { type: Boolean, required: true } },
      setup(props) {
        const dialogRef = ref<HTMLDialogElement | null>(null);
        const top = useTopLayerDialog({
          dialogRef,
          isOpen: () => props.open,
          onClose,
        });
        return { dialogRef, ...top };
      },
      template:
        '<dialog ref="dialogRef" v-bind="dialogProps" @pointerdown="onPointerDown" @pointerup="onPointerUp" @click="onBackdropClick"><p>Contenido</p></dialog>',
    });

    const wrapper = mount(TestHost, { props: { open: true } });
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
});
