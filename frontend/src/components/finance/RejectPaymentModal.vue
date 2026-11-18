<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useTopLayerDialog } from '../../composables/useTopLayerDialog';

const props = defineProps<{
  open: boolean;
  pagoId: number | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'confirm', payload: { pagoId: number; motivo: string }): void;
}>();

const dialogRef = ref<HTMLDialogElement | null>(null);
const motivo = ref('');
const touched = ref(false);

const isMotivoValid = computed(() => motivo.value.trim().length >= 5);

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      motivo.value = '';
      touched.value = false;
    }
  },
  { immediate: true },
);

const { dialogProps, onPointerDown, onPointerUp, onBackdropClick } = useTopLayerDialog({
  dialogRef,
  isOpen: () => props.open,
  onClose: () => emit('close'),
  unmountsWhenClosed: false,
});

function handleCancel(): void {
  emit('close');
}

function handleNativeClose(): void {
  if (props.open) {
    emit('close');
  }
}

function handleConfirm(): void {
  touched.value = true;
  if (!isMotivoValid.value || props.pagoId === null) {
    return;
  }
  emit('confirm', {
    pagoId: props.pagoId,
    motivo: motivo.value.trim(),
  });
}
</script>

<template>
  <!-- MANDATORY: no role="dialog" or aria-modal; the native modal already provides them -->
  <dialog
    id="modal-reject-reason"
    ref="dialogRef"
    v-bind="dialogProps"
    aria-labelledby="reject-modal-title"
    class="reject-dialog top-layer-dialog"
    @cancel.prevent="handleCancel"
    @close="handleNativeClose"
    @pointerdown="onPointerDown"
    @pointerup="onPointerUp"
    @click="onBackdropClick"
  >
    <h2 id="reject-modal-title" class="reject-dialog__title">
      Rechazar Pago en Revisión (Auditoría Forense)
    </h2>

    <form class="reject-dialog__form" novalidate @submit.prevent="handleConfirm">
      <div class="field-group">
        <label for="input-reject-motivo" class="field-label">Motivo obligatorio del rechazo</label>
        <p id="reject-motivo-hint" class="field-hint">
          Mínimo 5 caracteres detallando la causa (ej. referencia bancaria no localizada o monto
          incompleto). Este registro es inmutable en AuditoriaRecibo.
        </p>
        <textarea
          id="input-reject-motivo"
          v-model="motivo"
          rows="3"
          required
          minlength="5"
          class="field-textarea"
          aria-describedby="reject-motivo-hint"
          :aria-invalid="touched && !isMotivoValid ? 'true' : 'false'"
          @blur="touched = true"
        />
      </div>

      <div class="reject-dialog__actions">
        <button
          id="btn-cancel-reject"
          type="button"
          autofocus
          class="btn-secondary"
          @click="handleCancel"
        >
          Cancelar
        </button>
        <button id="btn-confirm-reject" type="submit" class="btn-danger" :disabled="!isMotivoValid">
          Confirmar Rechazo
        </button>
      </div>
    </form>
  </dialog>
</template>

<style scoped>
.reject-dialog[open] {
  display: block;
  inline-size: min(100% - 1.5rem, 28.75rem);
  max-block-size: min(85dvh, 38rem);
  overflow-y: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: clamp(1rem, 3vw, 1.5rem);
  background-color: var(--surface-elevated);
  color: var(--text-primary);
  box-shadow: var(--shadow-modal);
}

.reject-dialog__title {
  margin: 0 0 0.875rem;
  font-size: clamp(1rem, 2.5vw, 1.15rem);
  text-wrap: balance;
  color: var(--text-primary);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 1rem;
}

.field-label {
  font-size: 0.875rem;
  font-weight: 600;
}

.field-hint {
  margin: 0;
  max-inline-size: 65ch;
  text-wrap: pretty;
  font-size: 0.775rem;
  color: var(--text-secondary);
}

.field-textarea {
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--border-control);
  border-radius: var(--radius-sm);
  background-color: var(--surface-card);
  color: var(--text-primary);
  font-size: 1rem;
}

.field-textarea:user-invalid {
  border-color: var(--status-danger-border);
  background-color: var(--status-danger-bg);
}

.field-textarea:user-valid {
  border-color: var(--status-ok-border);
}

.reject-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-secondary {
  min-block-size: 2.75rem;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-subtle);
  color: var(--text-primary);
  font-weight: 600;
  cursor: pointer;
}

.btn-danger {
  min-block-size: 2.75rem;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--status-danger-border);
  background-color: var(--status-danger-border);
  color: var(--text-on-accent);
  font-weight: 700;
  cursor: pointer;
}

.btn-danger:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
