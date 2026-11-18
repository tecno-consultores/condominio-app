import { nextTick, onMounted, watch, type Ref } from 'vue';
import { closeTopLayerDialog } from './useViewTransition';

export interface TopLayerDialogOptions {
  dialogRef: Ref<HTMLDialogElement | null>;
  isOpen: () => boolean;
  onClose: () => void;
  unmountsWhenClosed?: boolean;
}

function hasNativeClosedBy(): boolean {
  return typeof HTMLDialogElement !== 'undefined' && 'closedBy' in HTMLDialogElement.prototype;
}

function isOutsideDialogBounds(
  event: { clientX: number; clientY: number },
  dialog: HTMLDialogElement,
): boolean {
  const rect = dialog.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) {
    return false;
  }
  return (
    event.clientX < rect.left ||
    event.clientX > rect.right ||
    event.clientY < rect.top ||
    event.clientY > rect.bottom
  );
}

export function useTopLayerDialog(options: TopLayerDialogOptions) {
  let pressedOutside: boolean | null = null;

  function showModalDialog(): void {
    const el = options.dialogRef.value;
    if (el && typeof el.showModal === 'function' && !el.open) {
      el.showModal();
    }
  }

  onMounted(() => {
    if (options.isOpen()) {
      showModalDialog();
    }
  });

  watch(options.isOpen, async (open) => {
    const el = options.dialogRef.value;
    if (!open) {
      if (!options.unmountsWhenClosed && el?.open) {
        await closeTopLayerDialog(el);
      } else if (el?.open && typeof el.close === 'function') {
        el.close();
      }
      return;
    }
    await nextTick();
    showModalDialog();
  });

  function onPointerDown(event: PointerEvent): void {
    const el = options.dialogRef.value;
    if (!el || hasNativeClosedBy()) {
      return;
    }
    pressedOutside = isOutsideDialogBounds(event, el);
  }

  function onPointerUp(event: PointerEvent): void {
    const el = options.dialogRef.value;
    if (!el || hasNativeClosedBy()) {
      return;
    }
    if (pressedOutside === true && isOutsideDialogBounds(event, el)) {
      pressedOutside = null;
      options.onClose();
    }
  }

  function onBackdropClick(event: MouseEvent): void {
    const el = options.dialogRef.value;
    if (!el || hasNativeClosedBy()) {
      return;
    }
    if (pressedOutside !== null) {
      pressedOutside = null;
      return;
    }
    if (event.target === el && isOutsideDialogBounds(event, el)) {
      options.onClose();
    }
  }

  return {
    dialogProps: { closedby: 'any' } as Record<string, string>,
    onPointerDown,
    onPointerUp,
    onBackdropClick,
  };
}
