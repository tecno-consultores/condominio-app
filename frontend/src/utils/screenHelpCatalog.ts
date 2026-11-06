// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

export interface ScreenHelpData {
  title: string;
  purpose: string;
  steps: string[];
  tips: string[];
}

export type RolUsuarioAyuda =
  | 'PROPIETARIO'
  | 'INQUILINO'
  | 'CONSERJE'
  | 'PRESIDENTE'
  | 'VICEPRESIDENTE'
  | 'TESORERO'
  | 'SECRETARIO'
  | 'VOCERO'
  | 'FANTASMA'
  | string;

function normalizePath(rawPath: string): string {
  if (!rawPath) return '/dashboard';
  const clean = rawPath.split('?')[0].split('#')[0].replace(/\/+$/, '') || '/';

  // Alias conocidos
  if (clean === '/inicio') return '/dashboard';
  if (clean === '/pagar') return '/finanzas/reportar-pago';
  if (clean === '/admin/pagos-revision') return '/tesoreria/pagos';
  if (clean === '/admin/finanzas') return '/tesoreria/cierre';
  if (clean === '/conserje/tareas') return '/operaciones/tareas';
  if (clean === '/admin/usuarios-pendientes') return '/admin/usuarios';

  // Patrones dinámicos
  if (/^\/consultas\/[^/]+$/.test(clean) && clean !== '/consultas') {
    return '/consultas/:id';
  }

  return clean;
}

export function getScreenHelp(rawPath: string, userRole?: RolUsuarioAyuda): ScreenHelpData {
  const path = normalizePath(rawPath);
  const role = (userRole || 'PROPIETARIO').toUpperCase();
  const esDirectiva = ['PRESIDENTE', 'VICEPRESIDENTE', 'TESORERO', 'SECRETARIO', 'VOCERO'].includes(
    role,
  );

  switch (path) {
    case '/login':
      return {
        title: 'Inicio de Sesión',
        purpose:
          'Permite a los residentes, conserjes y miembros de la junta acceder de forma segura al sistema.',
        steps: [
          'Ingrese su dirección de correo electrónico registrada.',
          'Escriba su contraseña confidencial. Puede usar el botón de visualización para verificarla.',
          'Haga clic en "Iniciar Sesión" para acceder a su panel principal.',
        ],
        tips: [
          'Si es un usuario recién registrado, su cuenta permanecerá en estado pendiente hasta ser activada por la junta.',
          'Consulte con el administrador o conserje si olvidó su clave de acceso.',
        ],
      };

    case '/register':
      return {
        title: 'Registro de Nuevo Residente',
        purpose:
          'Permite solicitar una cuenta residencial vinculada a una unidad habitacional o comercial.',
        steps: [
          'Complete sus datos personales: nombre completo, cédula de identidad y correo.',
          'Ingrese su número telefónico móvil para notificaciones.',
          'Seleccione la torre y unidad a la que pertenece.',
          'Indique si es Propietario o Inquilino y cree su contraseña segura.',
          'Envíe la solicitud para quedar en lista de activación por la Junta.',
        ],
        tips: [
          'Asegúrese de seleccionar la unidad correcta para agilizar la aprobación.',
          'Las contraseñas deben contener al menos 8 caracteres con números y letras.',
        ],
      };

    case '/espera-aprobacion':
      return {
        title: 'Cuenta Pendiente de Aprobación',
        purpose:
          'Indica que su usuario está en proceso de verificación por la Junta de Condominio.',
        steps: [
          'Espere que el Presidente o Administrador valide su condición de residente.',
          'Puede pulsar "Actualizar Estado" para verificar si su cuenta ya fue activada.',
          'Una vez activada, accederá automáticamente al panel financiero y vecinal.',
        ],
        tips: [
          'Comuníquese con la Junta de Condominio si la aprobación demora más de 24 horas.',
          'Verifique que su correo y número de contacto estén correctamente registrados.',
        ],
      };

    case '/dashboard':
      if (esDirectiva) {
        return {
          title: 'Panel General de Administración y Tesorería',
          purpose:
            'Vista integral del estado financiero del condominio, morosidad colectiva y egresos del mes.',
          steps: [
            'Revise la tasa oficial BCV del día en el indicador superior.',
            'Consulte el Semáforo de Cobranza para identificar unidades solventes y morosas.',
            'Examine el desglose de egresos clasificados en el gráfico interactivo.',
            'Utilice la barra lateral para acceder a la aprobación de pagos o cierre contable.',
          ],
          tips: [
            'Mantenga la tasa BCV actualizada antes de revisar comprobantes en bolívares.',
            'El Candado Contable se ejecuta una vez conciliados todos los pagos del mes.',
          ],
        };
      }
      if (role === 'CONSERJE') {
        return {
          title: 'Panel Operativo de Conserjería',
          purpose:
            'Resumen rápido de las actividades de mantenimiento, paquetes y visitas del día.',
          steps: [
            'Consulte los comunicados recientes emitidos por la Junta.',
            'Diríjase a la sección de Tareas Diarias para registrar el checklist de limpieza y bombas.',
            'Verifique la garita QR y el casillero de paquetería para entregas a residentes.',
          ],
          tips: [
            'Marque cada tarea apenas sea completada para informar en tiempo real a los copropietarios.',
          ],
        };
      }
      return {
        title: 'Panel Residencial — Tu Hogar Hoy',
        purpose:
          'Información centralizada del estado de cuenta de su inmueble, tasa oficial y avisos comunitarios.',
        steps: [
          'Verifique el estado de solvencia de su apartamento en la tarjeta principal.',
          'Consulte la tasa oficial de cambio BCV vigente.',
          'Revise los comunicados oficiales emitidos por la Junta de Condominio.',
          'Pulse el botón flotante "Reportar Pago" para registrar su abono o pago total.',
        ],
        tips: [
          'Los pagos reportados antes de las 3:00 PM suelen ser conciliados el mismo día hábil.',
          'Descargue su recibo digital una vez que la tesorería apruebe su comprobante.',
        ],
      };

    case '/finanzas/reportar-pago':
      return {
        title: 'Asistente de Reporte de Pagos',
        purpose:
          'Permite enviar los datos de su transferencia, pago móvil o depósito para su conciliación.',
        steps: [
          'Paso 1 (Monto y Moneda): Ingrese la cantidad a pagar y seleccione si es en Bolívares (VES) o Dólares (USD). Verifique si califica como Pago Total o Abono Parcial.',
          'Paso 2 (Método y Referencia): Elija la vía de pago (Pago Móvil, Transferencia, Zelle o Efectivo), coloque el número de referencia y adjunte la captura en formato JPG, PNG o AVIF (máx. 2 MB).',
          'Paso 3 (Confirmación): Verifique los datos en el resumen y presione "Confirmar y Enviar Pago".',
        ],
        tips: [
          'El sistema cuenta con protección anti-duplicados: evite reportar la misma referencia dos veces.',
          'Si realiza un pago superior a su deuda, el saldo excedente se acreditará automáticamente a su favor para el próximo mes.',
        ],
      };

    case '/finanzas/solvencia':
      return {
        title: 'Certificado Digital de Solvencia',
        purpose:
          'Emisión y validación del documento oficial que acredita que la unidad está al día con el condominio.',
        steps: [
          'Compruebe que el balance de su unidad esté en $0.00 USD (solvente).',
          'Presione el botón "Emitir Certificado Digital".',
          'Visualice el folio único, el código QR y la firma criptográfica HMAC-SHA256.',
          'Descargue o imprima el comprobante para trámites legales o mudanzas.',
        ],
        tips: [
          'El certificado incluye un Nonce y firma de integridad inalterable verificable desde cualquier dispositivo.',
          'Si posee deuda pendiente, debe reportar su pago y esperar la aprobación de tesorería para desbloquearlo.',
        ],
      };

    case '/tesoreria/pagos':
      return {
        title: 'Mesa de Revisión y Aprobación de Pagos',
        purpose:
          'Bandeja de verificación donde la Tesorería valida y concilia los comprobantes recibidos.',
        steps: [
          'Examine cada comprobante en la lista: monto en VES/USD, método, referencia y foto adjunta.',
          'Pulse "Aprobar" si los fondos ya están confirmados en la cuenta bancaria del condominio.',
          'Si el comprobante es ilegible o el monto no coincide, presione "Rechazar" e indique obligatoriamente el motivo explicativo.',
        ],
        tips: [
          'Al aprobar un pago, el balance de la unidad y el desglose del recibo se actualizan inmediatamente.',
          'Todo rechazo queda auditado y notifica al residente para que pueda corregir el reporte.',
        ],
      };

    case '/tesoreria/cierre':
      return {
        title: 'Cierre Contable Mensual y Egresos',
        purpose:
          'Administración de egresos comunitarios, fijación de tasa oficial y ejecución del Candado Contable.',
        steps: [
          'Registre la tasa de cambio oficial BCV vigente para la conversión multimoneda.',
          'Incorpore los egresos y gastos comunes del mes con su soporte y categoría.',
          'Verifique que no queden pagos pendientes de conciliar en la mesa de revisión.',
          'Ejecute el "Candado Contable" para sellar de forma inmutable el período contable.',
        ],
        tips: [
          'El Candado Contable es irreversible: una vez cerrado el mes no se podrán alterar ni borrar los recibos de ese período.',
          'Los egresos vinculados a incidencias cerradas se asocian automáticamente en la auditoría.',
        ],
      };

    case '/tesoreria/facturacion':
      return {
        title: 'Generador de Facturación Mensual',
        purpose:
          'Emisión masiva de recibos de condominio según Ley de Propiedad Horizontal (Alícuotas, Cuota Fija o Partes Iguales).',
        steps: [
          'Indique el período a facturar (ejemplo: 2026-11).',
          'Seleccione la modalidad de cálculo: Por Alícuota (Hamilton), Cuota Fija USD o Partes Iguales.',
          'Revise la simulación del total de gastos comunes a prorratear entre las unidades.',
          'Pulse "Generar Facturación Masiva" para crear los recibos de todas las unidades.',
        ],
        tips: [
          'En modalidad Cuota Fija, el excedente o déficit respecto a los gastos reales se concilia automáticamente en el Fondo de Reserva.',
          'Los créditos acumulados de residentes con sobrepago se descuentan automáticamente del monto facturado.',
        ],
      };

    case '/incidencias':
      return {
        title: 'Embudo de Incidencias Vecinales',
        purpose:
          'Canal comunitario para reportar averías y sumar apoyo vecinal a problemas prioritarios.',
        steps: [
          'Examine la cartelera de incidencias abiertas para verificar si su problema ya fue reportado.',
          'Si la incidencia ya existe, pulse "¡Me sumo!" para aumentar su prioridad sin generar reportes duplicados.',
          'Si el problema es nuevo, pulse "Reportar Incidencia", agregue título, ubicación y descripción.',
        ],
        tips: [
          'Las incidencias con más adhesiones ("¡Me sumo!") son priorizadas automáticamente por la Junta en las tareas de mantenimiento.',
          'Al resolverse la incidencia y completarse la tarea correspondiente, se notificará su cierre.',
        ],
      };

    case '/operaciones/tareas':
      return {
        title: 'Checklist Diario de Operaciones y Mantenimiento',
        purpose:
          'Lista de control diario para el conserje y personal técnico (bombas, luces, limpieza y basura).',
        steps: [
          'Revise las tareas asignadas para la jornada en la barra de progreso.',
          'Marque la casilla de verificación a medida que ejecute cada actividad.',
          'Al completar una tarea asociada a una incidencia vecinal, la incidencia se cerrará automáticamente.',
        ],
        tips: [
          'Las tareas son regeneradas diariamente a partir de las plantillas maestras de conserjería.',
          'La Junta de Condominio supervisa el porcentaje de avance en tiempo real.',
        ],
      };

    case '/voceros/galeria':
      return {
        title: 'Galería de Gestión Comunitaria',
        purpose:
          'Espacio para que los voceros de calle o torre publiquen evidencias visuales de obras y mejoras.',
        steps: [
          'Consulte las fotografías de mantenimiento y reparaciones ejecutadas.',
          'Si es Vocero o Miembro de Junta, seleccione una imagen (JPG/PNG) y escriba un pie descriptivo.',
          'Verifique el contador de cuota mensual: se admite un máximo de 30 fotos por mes calendario.',
        ],
        tips: [
          'Las imágenes son convertidas automáticamente a formato AVIF de alta compresión y nitidez.',
          'La cuota de 30 fotos se reinicia automáticamente el primer día de cada mes.',
        ],
      };

    case '/secretaria/bitacora':
      return {
        title: 'Bitácora y Minutas de Secretaría',
        purpose:
          'Registro histórico oficial de acuerdos, asambleas de copropietarios y decisiones de junta.',
        steps: [
          'Consulte el historial cronológico de actas y resoluciones aprobadas.',
          'Para asentar una nueva resolución, redacte el contenido del acta en el formulario.',
          'Haga clic en "Registrar Acta" para archivarla de manera inmutable.',
        ],
        tips: [
          'El cierre formal de una Carta Consulta genera automáticamente una entrada en esta bitácora con los votos certificados.',
        ],
      };

    case '/consultas':
      return {
        title: 'Cartas Consulta y Asambleas Digitales',
        purpose:
          'Mecanismo de toma de decisiones comunitarias con validez legal según Art. 23 de la Ley de Propiedad Horizontal.',
        steps: [
          'Consulte las consultas comunitarias activas y revise la fecha límite de participación.',
          'Haga clic sobre una consulta para ver las opciones disponibles y emitir su voto.',
          'Si es Miembro de la Junta, pulse "Crear Consulta" para someter un tema a votación vecinal.',
        ],
        tips: [
          'Cada unidad habitacional emite un único voto ponderado por el porcentaje de su alícuota.',
          'El cuórum requerido se evalúa en tiempo real según la regla estipulada (Unanimidad, Dos Tercios o Mayoría Simple).',
        ],
      };

    case '/consultas/:id':
      return {
        title: 'Votación y Escrutinio de Consulta',
        purpose:
          'Emisión del voto formal para su inmueble y descarga del comprobante criptográfico de votación.',
        steps: [
          'Lea detenidamente la propuesta y los recaudos adjuntos.',
          'Seleccione la opción de su preferencia entre las alternativas listadas.',
          'Presione "Confirmar y Emitir Voto".',
          'En el modal que aparece, guarde o copie su Recibo Criptográfico con firma HMAC-SHA256.',
        ],
        tips: [
          'Una vez emitido el voto, este es definitivo e inalterable.',
          'La Junta de Condominio podrá cerrar formalmente la consulta una vez alcanzado el cuórum legal o expirado el plazo.',
        ],
      };

    case '/accesos/pases':
      return {
        title: 'Pases QR de Invitados y Visitantes',
        purpose:
          'Generación de autorizaciones de acceso temporal para familiares, visitantes o servicios.',
        steps: [
          'Ingrese el nombre completo del visitante y su documento de identidad.',
          'Indique si el acceso es peatonal o vehicular (con placa del vehículo).',
          'Seleccione las horas de validez del pase (ejemplo: 4, 8 o 24 horas).',
          'Genere el pase y comparta la imagen o token QR con su invitado por mensajería.',
        ],
        tips: [
          'Cada código QR cuenta con un identificador único (Nonce JTI) de un solo uso que se quema al ingresar en garita.',
          'Puede revocar un pase en cualquier momento antes de que sea utilizado.',
        ],
      };

    case '/operaciones/garita-qr':
      return {
        title: 'Control de Acceso en Garita (Lector QR)',
        purpose:
          'Herramienta de vigilancia y conserjería para verificar la autenticidad de pases QR en puerta.',
        steps: [
          'Escanee el código QR presentado por el visitante con la cámara del dispositivo o pegue el token alfanumérico.',
          'Presione "Verificar Acceso".',
          'Compruebe en pantalla el nombre del visitante, cédula, unidad que visita y estatus de validez.',
          'Al validarse positivamente, el sistema registrará la entrada y quemará el token en el servidor.',
        ],
        tips: [
          'Los pases expirados, adulterados o ya utilizados serán rechazados con alerta roja inmediata.',
          'En caso de duda, comuníquese internamente con el propietario de la unidad antes de autorizar el ingreso.',
        ],
      };

    case '/operaciones/paqueteria':
      return {
        title: 'Casillero y Recepción de Paquetería',
        purpose:
          'Control de custodia de sobres, encomiendas y paquetes recibidos por vigilancia o conserjería.',
        steps: [
          'Para recepcionar: ingrese la unidad destinataria, empresa de mensajería (MRW, Zoom, MercadoLibre, etc.) y código de rastreo.',
          'El residente verá el paquete pendiente en su panel.',
          'Para entregar: cuando el residente se presente a retirar, localice el paquete y presione "Confirmar Entrega".',
        ],
        tips: [
          'Mantenga los paquetes organizados por número de torre y apartamento en el casillero de garita.',
        ],
      };

    case '/reservas/areas':
      return {
        title: 'Reserva de Áreas Comunes y Amenidades',
        purpose:
          'Solicitud de uso de salón de eventos, churuatas o áreas deportivas vinculada a solvencia.',
        steps: [
          'Seleccione el área social que desea reservar (ejemplo: Salón de Fiesta o Parrillera).',
          'Verifique el requisito de solvencia: sólo unidades al día ($0.00 de deuda) pueden reservar.',
          'Escoja la fecha del evento y complete la cantidad estimada de invitados.',
          'Envíe la solicitud para reservar la fecha.',
        ],
        tips: [
          'El sistema impide automáticamente reservas en fechas ya ocupadas (Candado Anti-Solapamiento).',
          'Al finalizar el evento, el conserje ejecutará una inspección de entrega en las tareas diarias.',
        ],
      };

    case '/admin/estructura':
      return {
        title: 'Constructor de Estructura y Unidades',
        purpose:
          'Configuración inicial o ampliación de torres, edificios, plantas, alícuotas y cuotas fijas.',
        steps: [
          'Defina el nombre del edificio o torre (ejemplo: Torre A).',
          'Indique los identificadores de unidades separados por coma (ejemplo: 1-A, 1-B, 2-A, 2-B).',
          'Presione "Generar Estructura".',
          'Posteriormente, ajuste las alícuotas porcentuales o cuotas fijas de cada unidad en la tabla inferior.',
        ],
        tips: [
          'La suma de las alícuotas del condominio debe aproximarse al 100.00% según documento de condominio.',
          'Esta operación es idempotente: no duplicará unidades ya registradas.',
        ],
      };

    case '/admin/usuarios':
      return {
        title: 'Bandeja de Activación de Usuarios Fantasma',
        purpose: 'Verificación de identidad de nuevos registros y asignación de roles y unidades.',
        steps: [
          'Localice la tarjeta del usuario solicitante con sus datos personales.',
          'Verifique o corrija la unidad asignada a su contrato de ocupación.',
          'Seleccione el rol correspondiente (PROPIETARIO, INQUILINO o CONSERJE).',
          'Presione "Activar Usuario" para concederle acceso formal a la plataforma.',
        ],
        tips: [
          'Los usuarios no pueden ver información financiera ni votar hasta que la Junta los active.',
          'Si un registro no corresponde a un vecino real, comuníquese con él o desestime la solicitud.',
        ],
      };

    case '/admin/junta':
      return {
        title: 'Asignación de Cargos de la Junta de Condominio',
        purpose:
          'Designación de los miembros directivos electos en asamblea según Ley de Propiedad Horizontal.',
        steps: [
          'Seleccione el usuario que ocupará la posición.',
          'Elija el cargo estatutario: Presidente, Vicepresidente, Tesorero, Secretario o Vocero.',
          'Presione "Asignar Cargo".',
        ],
        tips: [
          'Por disposición legal, sólo los copropietarios con contrato activo de PROPIETARIO pueden integrar la Junta de Condominio.',
          'El sistema adapta automáticamente los permisos y menús según el cargo asignado.',
        ],
      };

    default:
      return {
        title: 'Ayuda del Sistema Condominio App',
        purpose:
          'Plataforma integral de gestión residencial y administrativa bajo Ley de Propiedad Horizontal.',
        steps: [
          'Navegue a través de la barra lateral (escritorio) o barra inferior (móvil).',
          'Revise su saldo y avisos en el Panel Principal.',
          'Reporte sus pagos con comprobante para mantener su solvencia al día.',
        ],
        tips: [
          'Pulse el botón de ayuda (?) en cualquier pantalla para consultar instrucciones específicas de la sección actual.',
        ],
      };
  }
}
