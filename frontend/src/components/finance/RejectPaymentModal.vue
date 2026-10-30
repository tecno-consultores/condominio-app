<script setup lang="ts">
import { computed, ref, watch } from 'vue';

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

function handleCancel(): void {
  emit('close');
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
    :open="open ? true : undefined"
    aria-labelledby="reject-modal-title"
    class="reject-dialog"
    @close="handleCancel"
  >
    <h2 id="reject-modal-title" class="reject-dialog__title">
      Rechazar Pago #{{ pagoId ?? '' }} (Auditoría Forense)
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
/* MANDATORY (both rules): without them, scrolling over the backdrop or inside the dialog scrolls the page behind it */
dialog:modal {
  overscroll-behavior: contain;
}

dialog::backdrop {
  overflow: hidden;
  overscroll-behavior: contain;
  background-color: rgba(15, 23, 42, 0.55);
}

.reject-dialog[open] {
  display: block;
  width: min(100% - 2rem, 460px);
  border: 1px solid #cbd5e1;
  border-radius: 0.75rem;
  padding: 1.25rem;
  background-color: #ffffff;
  color: #0f172a;
}

.reject-dialog__title {
  margin: 0 0 0.875rem;
  font-size: 1.1rem;
  color: #0f172a;
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
  font-size: 0.775rem;
  color: #475569;
}

.field-textarea {
  padding: 0.625rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  font-size: 0.9rem;
}

.field-textarea:user-invalid {
  border-color: #dc2626;
  background-color: #fef2f2;
}

.field-textarea:user-valid {
  border-color: #16a34a;
}

.reject-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-secondary {
  min-height: 44px;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  background-color: #f8fafc;
  color: #0f172a;
  font-weight: 600;
  cursor: pointer;
}

.btn-danger {
  min-height: 44px;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background-color: #dc2626;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.btn-danger:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
