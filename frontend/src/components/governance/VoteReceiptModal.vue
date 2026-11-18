<script setup lang="ts">
import { ref } from 'vue';
import { useTopLayerDialog } from '../../composables/useTopLayerDialog';
import CopyButton from '../common/CopyButton.vue';
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

const { dialogProps, onPointerDown, onPointerUp, onBackdropClick } = useTopLayerDialog({
  dialogRef,
  isOpen: () => Boolean(props.open && props.recibo),
  onClose: () => emit('close'),
  unmountsWhenClosed: true,
});
</script>

<template>
  <dialog
    v-if="open && recibo"
    id="modal-vote-receipt"
    ref="dialogRef"
    v-bind="dialogProps"
    class="vote-receipt-modal top-layer-dialog"
    aria-labelledby="vote-receipt-title"
    @close="emit('close')"
    @pointerdown="onPointerDown"
    @pointerup="onPointerUp"
    @click="onBackdropClick"
  >
    <div class="vote-receipt-modal__card">
      <header class="vote-receipt-modal__header">
        <div>
          <span class="vote-receipt-modal__eyebrow">Comprobante Inmutable Art. 23 LPH</span>
          <h2 id="vote-receipt-title" class="vote-receipt-modal__title">
            Recibo Criptográfico de Votación
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
          <dd id="receipt-alicuota-capturada" class="tabular-nums">
            <strong>{{ recibo.alicuota_capturada }}%</strong>
          </dd>
        </div>
      </dl>

      <div class="vote-receipt-modal__signature-box">
        <div class="vote-receipt-modal__signature-header">
          <span class="vote-receipt-modal__signature-label">Sello Criptográfico HMAC-SHA256:</span>
          <CopyButton
            id="btn-copy-vote-hmac"
            target-id="receipt-firma-hmac"
            label="Copiar sello criptográfico HMAC-SHA256"
          />
        </div>
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
          autofocus
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
.vote-receipt-modal[open] {
  padding: 0;
  border: none;
  background: transparent;
  inline-size: min(100% - 1.5rem, 34rem);
  max-block-size: min(85dvh, 40rem);
  overscroll-behavior: contain;
}

.vote-receipt-modal::backdrop {
  backdrop-filter: blur(2px);
}

.vote-receipt-modal__card {
  inline-size: 100%;
  max-block-size: min(85dvh, 40rem);
  overflow-y: auto;
  overscroll-behavior: contain;
  background-color: var(--surface-elevated);
  color: var(--text-primary);
  border-radius: var(--radius-lg);
  padding: clamp(1rem, 3cqi, 1.5rem);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--surface-hairline), var(--shadow-modal);
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
  color: var(--brand-accent);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.vote-receipt-modal__title {
  margin: 0.2rem 0 0;
  font-size: clamp(1rem, 2.5cqi, 1.15rem);
  font-weight: 800;
  color: var(--text-primary);
  text-wrap: balance;
}

.vote-receipt-modal__badge {
  font-size: 0.725rem;
  font-weight: 700;
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-pill);
  background-color: var(--status-ok-bg);
  color: var(--status-ok-text);
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
  border-radius: var(--radius-sm);
  background-color: var(--surface-subtle);
  border: 1px solid var(--border-subtle);
  font-size: 0.875rem;
}

.vote-receipt-modal__row dt {
  color: var(--text-secondary);
}

.vote-receipt-modal__row dd {
  margin: 0;
  color: var(--text-primary);
}

.vote-receipt-modal__signature-box {
  padding: 0.75rem;
  border-radius: var(--radius-sm);
  background-color: var(--surface-code-bg);
  color: var(--surface-code-text);
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.vote-receipt-modal__signature-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.vote-receipt-modal__signature-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--surface-code-accent);
}

.vote-receipt-modal__signature {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  word-break: break-all;
  color: var(--surface-code-text);
}

.vote-receipt-modal__message {
  margin: 0;
  font-size: 0.725rem;
  color: var(--surface-code-text);
  opacity: 0.82;
  word-break: break-all;
}

.vote-receipt-modal__footer {
  display: flex;
  justify-content: flex-end;
}

.vote-receipt-modal__close {
  min-block-size: 2.75rem;
  padding: 0.55rem 1rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--brand-600);
  background-color: var(--brand-600);
  color: var(--text-on-accent);
  font-weight: 700;
  cursor: pointer;
}

@media (max-width: 639px) {
  .vote-receipt-modal[open] {
    margin: auto 0 0 0;
    inline-size: 100%;
    max-inline-size: 100%;
    max-block-size: 88dvh;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  }

  .vote-receipt-modal__card {
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    max-block-size: 88dvh;
  }
}
</style>
