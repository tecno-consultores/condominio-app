<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import type { ReciboVotoDTO, VotoReciboResumenDTO } from '../../stores/governanceStore';

const props = defineProps<{
  open: boolean;
  recibo: ReciboVotoDTO | VotoReciboResumenDTO | null;
  tituloConsulta?: string;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const dialogRef = ref<HTMLDialogElement | null>(null);

watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) return;
    await nextTick();
    const el = dialogRef.value;
    if (el && typeof el.showModal === 'function' && !el.open) {
      el.showModal();
    }
  },
  { immediate: true },
);

function handleBackdropClick(event: MouseEvent): void {
  const dialog = dialogRef.value;
  if (!dialog) return;
  if (typeof HTMLDialogElement !== 'undefined' && 'closedBy' in HTMLDialogElement.prototype) {
    return;
  }
  if (event.target !== dialog) return;
  const rect = dialog.getBoundingClientRect();
  const isDialogContent =
    rect.height > 0 &&
    rect.width > 0 &&
    rect.top <= event.clientY &&
    event.clientY <= rect.top + rect.height &&
    rect.left <= event.clientX &&
    event.clientX <= rect.left + rect.width;
  if (isDialogContent) return;
  emit('close');
}
</script>

<template>
  <dialog
    v-if="open && recibo"
    id="modal-vote-receipt"
    ref="dialogRef"
    open
    v-bind="{ closedby: 'any' }"
    class="vote-receipt-modal"
    aria-labelledby="vote-receipt-title"
    @close="emit('close')"
    @click="handleBackdropClick"
  >
    <div class="vote-receipt-modal__card">
      <header class="vote-receipt-modal__header">
        <div>
          <span class="vote-receipt-modal__eyebrow">Comprobante Inmutable Art. 23 LPH</span>
          <h2 id="vote-receipt-title" class="vote-receipt-modal__title">
            Recibo Criptográfico de Votación #{{ recibo.voto_id }}
          </h2>
        </div>
        <span class="vote-receipt-modal__badge">HMAC-SHA256</span>
      </header>

      <dl class="vote-receipt-modal__details">
        <div class="vote-receipt-modal__row">
          <dt>Consulta:</dt>
          <dd>
            <strong>{{
              'titulo_consulta' in recibo
                ? recibo.titulo_consulta
                : tituloConsulta || 'Carta Consulta'
            }}</strong>
          </dd>
        </div>
        <div class="vote-receipt-modal__row">
          <dt>Unidad Inmobiliaria:</dt>
          <dd id="receipt-unidad">
            <strong>{{ recibo.identificador_unidad }}</strong>
          </dd>
        </div>
        <div class="vote-receipt-modal__row">
          <dt>Opción Seleccionada:</dt>
          <dd id="receipt-opcion">
            <strong>{{ recibo.opcion_etiqueta }}</strong>
          </dd>
        </div>
        <div class="vote-receipt-modal__row">
          <dt>Alícuota Ponderada Capturada:</dt>
          <dd id="receipt-alicuota-capturada" class="tabular-num">
            <strong>{{ recibo.alicuota_capturada }}%</strong>
          </dd>
        </div>
      </dl>

      <div class="vote-receipt-modal__signature-box">
        <span class="vote-receipt-modal__signature-label">Sello Criptográfico HMAC-SHA256:</span>
        <code id="receipt-firma-hmac" class="vote-receipt-modal__signature">
          {{ recibo.firma_hmac }}
        </code>
        <p
          v-if="'mensaje_verificacion' in recibo"
          id="receipt-mensaje-verificacion"
          class="vote-receipt-modal__message"
        >
          {{ recibo.mensaje_verificacion }}
        </p>
      </div>

      <footer class="vote-receipt-modal__footer">
        <button
          id="btn-close-vote-receipt"
          type="button"
          class="vote-receipt-modal__close"
          @click="emit('close')"
        >
          Cerrar Comprobante
        </button>
      </footer>
    </div>
  </dialog>
</template>

<style scoped>
dialog:modal,
.vote-receipt-modal {
  position: fixed;
  inset: 0;
  inline-size: 100%;
  block-size: 100%;
  background-color: rgba(15, 23, 42, 0.65);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem;
  z-index: 60;
  overscroll-behavior: contain;
}

dialog::backdrop,
.vote-receipt-modal::backdrop {
  background-color: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(2px);
  overflow: hidden;
  overscroll-behavior: contain;
}

.vote-receipt-modal__card {
  inline-size: min(100% - 1rem, 34rem);
  max-block-size: min(85dvh, 40rem);
  overflow-y: auto;
  overscroll-behavior: contain;
  background-color: #ffffff;
  border-radius: 1rem;
  padding: clamp(1rem, 3cqi, 1.5rem);
  border: 1px solid #cbd5e1;
  box-shadow:
    0 20px 25px -5px rgba(15, 23, 42, 0.18),
    0 8px 10px -6px rgba(15, 23, 42, 0.1);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.vote-receipt-modal__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.vote-receipt-modal__eyebrow {
  display: block;
  font-size: 0.75rem;
  font-weight: 700;
  color: #0369a1;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.vote-receipt-modal__title {
  margin: 0.2rem 0 0;
  font-size: clamp(1rem, 2.5cqi, 1.15rem);
  font-weight: 800;
  color: #0f172a;
  text-wrap: balance;
}

.vote-receipt-modal__badge {
  font-size: 0.725rem;
  font-weight: 700;
  padding: 0.25rem 0.6rem;
  border-radius: 9999px;
  background-color: #ecfdf5;
  color: #047857;
}

.vote-receipt-modal__details {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.vote-receipt-modal__row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  font-size: 0.875rem;
}

.vote-receipt-modal__row dt {
  color: #475569;
}

.vote-receipt-modal__row dd {
  margin: 0;
  color: #0f172a;
}

.vote-receipt-modal__signature-box {
  padding: 0.75rem;
  border-radius: 0.625rem;
  background-color: #0f172a;
  color: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.vote-receipt-modal__signature-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: #38bdf8;
}

.vote-receipt-modal__signature {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.75rem;
  word-break: break-all;
  color: #e2e8f0;
}

.vote-receipt-modal__message {
  margin: 0;
  font-size: 0.725rem;
  color: #94a3b8;
  word-break: break-all;
}

.vote-receipt-modal__footer {
  display: flex;
  justify-content: flex-end;
}

.vote-receipt-modal__close {
  padding: 0.55rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  background-color: #0f172a;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.tabular-num {
  font-variant-numeric: tabular-nums;
}

@media (pointer: coarse) {
  .vote-receipt-modal__close {
    min-block-size: 2.75rem;
  }
}
</style>
