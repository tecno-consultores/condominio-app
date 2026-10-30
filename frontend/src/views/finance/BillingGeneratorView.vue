<script setup lang="ts">
import { onMounted, ref } from 'vue';
import ReceiptBreakdownModal from '../../components/finance/ReceiptBreakdownModal.vue';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import { useIdempotency } from '../../composables/useIdempotency';
import {
  useFinanceStore,
  type ModalidadFacturacion,
  type TipoFondoCondominio,
} from '../../stores/financeStore';

const financeStore = useFinanceStore();
const { currentKey: billingKey, rotateKey: rotateBillingKey } = useIdempotency();
const { currentKey: fundKey, rotateKey: rotateFundKey } = useIdempotency();

const periodo = ref('2026-10');
const modalidad = ref<ModalidadFacturacion>('ALICUOTA');
const montoCuotaFijaUsd = ref('25.00');
const incluirFondoReserva = ref(true);
const cuotaExtraUsd = ref('0.00');
const descCuotaExtra = ref('');

const nombreFondo = ref('');
const tipoFondo = ref<TipoFondoCondominio>('RESERVA_LEGAL');
const porcentajeRecargo = ref('10.00');

const validationError = ref<string | null>(null);
const successBanner = ref<string | null>(null);
const showBreakdownModal = ref(false);

onMounted(() => {
  void financeStore.fetchDashboardData();
  void financeStore.fetchFondos();
});

async function handleEmitBilling(): Promise<void> {
  validationError.value = null;
  successBanner.value = null;

  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(periodo.value.trim())) {
    validationError.value = 'El periodo debe tener el formato YYYY-MM (ej. 2026-10).';
    return;
  }
  if (modalidad.value === 'CUOTA_FIJA' && Number.parseFloat(montoCuotaFijaUsd.value) <= 0) {
    validationError.value = 'Debe indicar un monto de cuota fija mensual mayor que cero.';
    return;
  }

  try {
    const res = await financeStore.facturarPeriodo(
      {
        periodo: periodo.value.trim(),
        modalidad: modalidad.value,
        monto_cuota_fija_usd: modalidad.value === 'CUOTA_FIJA' ? montoCuotaFijaUsd.value : null,
        incluir_fondo_reserva: incluirFondoReserva.value,
        cuota_extraordinaria_total_usd: cuotaExtraUsd.value || '0.00',
        descripcion_cuota_extraordinaria: descCuotaExtra.value.trim() || null,
      },
      billingKey.value,
    );
    rotateBillingKey();
    successBanner.value = `Facturación ${res.periodo} (${res.modalidad}) emitida: ${res.recibos_emitidos} recibos por $${res.total_facturado_neto_usd} USD netos.`;
  } catch {
    // Error preservado en financeStore.errorMessage
  }
}

async function handleCreateFund(): Promise<void> {
  validationError.value = null;
  successBanner.value = null;

  if (nombreFondo.value.trim().length < 3) {
    validationError.value = 'El nombre del fondo patrimonial debe tener al menos 3 caracteres.';
    return;
  }

  try {
    const created = await financeStore.crearFondo(
      {
        nombre: nombreFondo.value.trim(),
        tipo: tipoFondo.value,
        porcentaje_recargo: porcentajeRecargo.value,
      },
      fundKey.value,
    );
    rotateFundKey();
    nombreFondo.value = '';
    successBanner.value = `Fondo "${created.nombre}" registrado exitosamente.`;
  } catch {
    // Error preservado en financeStore.errorMessage
  }
}

async function handleOpenBreakdown(reciboId: number): Promise<void> {
  try {
    await financeStore.fetchReciboDesglose(reciboId);
    showBreakdownModal.value = true;
  } catch {
    // Error preservado en financeStore.errorMessage
  }
}
</script>

<template>
  <AppShellLayout>
    <section class="billing-view" aria-labelledby="billing-view-heading">
      <header class="billing-view__header">
        <h1 id="billing-view-heading" class="billing-view__title">
          Facturación Mensual LPH y Fondos Patrimoniales
        </h1>
        <p class="billing-view__subtitle">
          Emita recibos por Alícuota (Hamilton), Cuota Fija Mensual o Partes Iguales con aplicación
          automática de saldo a favor.
        </p>
      </header>

      <div
        v-if="financeStore.errorMessage"
        id="billing-error-banner"
        class="billing-view__alert billing-view__alert--warning"
        role="status"
      >
        {{ financeStore.errorMessage }}
      </div>

      <div
        v-if="successBanner"
        id="billing-success-banner"
        class="billing-view__alert billing-view__alert--success"
        role="status"
      >
        {{ successBanner }}
      </div>

      <p v-if="validationError" id="billing-validation-error" class="billing-view__error">
        {{ validationError }}
      </p>

      <div class="billing-view__layout">
        <form
          id="form-facturar-periodo"
          class="billing-view__card"
          novalidate
          @submit.prevent="handleEmitBilling"
        >
          <h2 class="billing-view__card-title">Emitir Facturación del Periodo</h2>

          <div class="billing-view__grid">
            <div class="billing-view__field">
              <label for="input-facturar-periodo" class="billing-view__label"
                >Periodo (YYYY-MM)</label
              >
              <input
                id="input-facturar-periodo"
                v-model="periodo"
                type="text"
                class="billing-view__input"
                placeholder="2026-10"
              />
            </div>

            <div class="billing-view__field">
              <label for="select-facturar-modalidad" class="billing-view__label"
                >Modalidad de Cobro</label
              >
              <select
                id="select-facturar-modalidad"
                v-model="modalidad"
                class="billing-view__input"
              >
                <option value="ALICUOTA">ALÍCUOTA (Art. 7 y 11 LPH — Hamilton)</option>
                <option value="CUOTA_FIJA">CUOTA FIJA MENSUAL (Conciliación a Fondo)</option>
                <option value="PARTES_IGUALES">PARTES IGUALES (1/N Exacto)</option>
              </select>
            </div>
          </div>

          <div v-if="modalidad === 'CUOTA_FIJA'" class="billing-view__field">
            <label for="input-monto-cuota-fija" class="billing-view__label">
              Monto Global de Cuota Fija Mensual (USD)
            </label>
            <input
              id="input-monto-cuota-fija"
              v-model="montoCuotaFijaUsd"
              type="number"
              step="0.01"
              class="billing-view__input tabular-num"
            />
          </div>

          <label class="billing-view__checkbox">
            <input id="check-incluir-reserva" v-model="incluirFondoReserva" type="checkbox" />
            <span>Incluir recargo automático del Fondo de Reserva Legal</span>
          </label>

          <div class="billing-view__grid">
            <div class="billing-view__field">
              <label for="input-cuota-extra-monto" class="billing-view__label">
                Cuota Extraordinaria Total (USD)
              </label>
              <input
                id="input-cuota-extra-monto"
                v-model="cuotaExtraUsd"
                type="number"
                step="0.01"
                class="billing-view__input tabular-num"
              />
            </div>

            <div class="billing-view__field">
              <label for="input-cuota-extra-desc" class="billing-view__label">
                Concepto Cuota Extraordinaria
              </label>
              <input
                id="input-cuota-extra-desc"
                v-model="descCuotaExtra"
                type="text"
                class="billing-view__input"
                placeholder="Ej. Impermeabilización azotea"
              />
            </div>
          </div>

          <button id="btn-submit-facturacion" type="submit" class="billing-view__submit">
            Emitir Recibos del Periodo
          </button>
        </form>

        <form
          id="form-crear-fondo"
          class="billing-view__card"
          novalidate
          @submit.prevent="handleCreateFund"
        >
          <h2 class="billing-view__card-title">Fondos Patrimoniales del Condominio</h2>

          <div class="billing-view__field">
            <label for="input-fondo-nombre" class="billing-view__label">Nombre del Fondo</label>
            <input
              id="input-fondo-nombre"
              v-model="nombreFondo"
              type="text"
              class="billing-view__input"
              placeholder="Ej. Fondo de Reserva Legal"
            />
          </div>

          <div class="billing-view__grid">
            <div class="billing-view__field">
              <label for="select-fondo-tipo" class="billing-view__label">Tipo de Fondo</label>
              <select id="select-fondo-tipo" v-model="tipoFondo" class="billing-view__input">
                <option value="RESERVA_LEGAL">RESERVA_LEGAL</option>
                <option value="CAJA_CHICA">CAJA_CHICA</option>
                <option value="ESPECIAL">ESPECIAL</option>
              </select>
            </div>

            <div class="billing-view__field">
              <label for="input-fondo-porcentaje" class="billing-view__label"
                >Recargo Mensual (%)</label
              >
              <input
                id="input-fondo-porcentaje"
                v-model="porcentajeRecargo"
                type="number"
                step="0.01"
                class="billing-view__input tabular-num"
              />
            </div>
          </div>

          <button id="btn-submit-fondo" type="submit" class="billing-view__submit">
            Registrar Fondo Patrimonial
          </button>

          <ul id="fondos-list" class="billing-view__funds-list" aria-label="Fondos activos">
            <li v-for="f in financeStore.data.fondos" :key="f.id" class="billing-view__fund-item">
              <span>
                <strong>{{ f.nombre }}</strong> ({{ f.tipo }} · {{ f.porcentaje_recargo }}%)
              </span>
              <strong class="tabular-num">${{ f.saldo_actual_usd }} USD</strong>
            </li>
          </ul>
        </form>
      </div>

      <article
        v-if="financeStore.data.ultimaFacturacion"
        id="billing-summary-card"
        class="billing-view__card"
      >
        <h2 class="billing-view__card-title">
          Resumen de Emisión — {{ financeStore.data.ultimaFacturacion.periodo }}
        </h2>
        <div class="billing-view__metrics">
          <div>
            <span>Recibos Emitidos:</span>
            <strong class="tabular-num">
              {{ financeStore.data.ultimaFacturacion.recibos_emitidos }}
            </strong>
          </div>
          <div>
            <span>Facturado Bruto:</span>
            <strong class="tabular-num">
              ${{ financeStore.data.ultimaFacturacion.total_facturado_bruto_usd }} USD
            </strong>
          </div>
          <div>
            <span>Créditos Aplicados:</span>
            <strong class="tabular-num">
              -${{ financeStore.data.ultimaFacturacion.total_credito_descontado_usd }} USD
            </strong>
          </div>
          <div>
            <span>Facturado Neto:</span>
            <strong class="tabular-num">
              ${{ financeStore.data.ultimaFacturacion.total_facturado_neto_usd }} USD
            </strong>
          </div>
        </div>
      </article>

      <section
        v-if="financeStore.data.resumen?.estado_cobranza.length"
        class="billing-view__card"
        aria-label="Recibos emitidos para consulta de desglose"
      >
        <h2 class="billing-view__card-title">Inspección de Desglose de Recibos</h2>
        <ul class="billing-view__funds-list">
          <li
            v-for="(rec, idx) in financeStore.data.resumen.estado_cobranza"
            :key="`${rec.unidad_id}-${rec.periodo}-${idx}`"
            class="billing-view__fund-item"
          >
            <span>
              Unidad #{{ rec.unidad_id }} · {{ rec.periodo }} — Saldo:
              <strong class="tabular-num">${{ rec.saldo_usd }} USD</strong>
            </span>
            <button
              :id="`btn-inspect-recibo-${rec.recibo_id ?? idx + 1}`"
              type="button"
              class="billing-view__inspect-btn"
              @click="handleOpenBreakdown(rec.recibo_id ?? idx + 1)"
            >
              Ver Desglose
            </button>
          </li>
        </ul>
      </section>

      <ReceiptBreakdownModal
        :open="showBreakdownModal"
        :desglose="financeStore.data.desgloseActivo"
        @close="showBreakdownModal = false"
      />
    </section>
  </AppShellLayout>
</template>

<style scoped>
.billing-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.billing-view__title {
  margin: 0;
  font-size: clamp(1.25rem, 3cqi, 1.5rem);
  font-weight: 800;
  color: #0f172a;
  text-wrap: balance;
}

.billing-view__subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: #475569;
  max-inline-size: 65ch;
}

.billing-view__alert {
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.billing-view__alert--warning {
  background-color: #fffbeb;
  border: 1px solid #f59e0b;
  color: #92400e;
}

.billing-view__alert--success {
  background-color: #ecfdf5;
  border: 1px solid #10b981;
  color: #065f46;
}

.billing-view__error {
  margin: 0;
  color: #b91c1c;
  font-size: 0.85rem;
  font-weight: 700;
}

.billing-view__layout {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
  gap: 1rem;
}

.billing-view__card {
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 0.875rem;
  padding: clamp(1rem, 2.5cqi, 1.25rem);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.billing-view__card-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
}

.billing-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.75rem;
}

.billing-view__field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.billing-view__label {
  font-size: 0.8rem;
  font-weight: 700;
  color: #334155;
}

.billing-view__input {
  padding: 0.55rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #94a3b8;
  font-size: 0.875rem;
}

.billing-view__checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: #334155;
  font-weight: 600;
}

.billing-view__submit {
  align-self: flex-start;
  padding: 0.6rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background-color: #0284c7;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.billing-view__funds-list {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.billing-view__fund-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  border-radius: 0.5rem;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  font-size: 0.85rem;
}

.billing-view__metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.75rem;
  font-size: 0.875rem;
}

.billing-view__metrics > div {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.6rem;
  border-radius: 0.5rem;
  background-color: #f8fafc;
}

.billing-view__inspect-btn {
  padding: 0.375rem 0.75rem;
  border-radius: 0.45rem;
  border: 1px solid #0284c7;
  background-color: #f0f9ff;
  color: #0369a1;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}

.tabular-num {
  font-variant-numeric: tabular-nums;
}

@media (pointer: coarse) {
  .billing-view__submit,
  .billing-view__inspect-btn {
    min-block-size: 2.75rem;
  }
}
</style>
