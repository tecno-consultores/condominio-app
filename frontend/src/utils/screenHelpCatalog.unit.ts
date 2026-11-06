// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { describe, expect, it } from 'vitest';
import { getScreenHelp } from './screenHelpCatalog';

describe('screenHelpCatalog.ts (Ayuda Contextual Responsiva por Ruta y Rol)', () => {
  it('retorna la ayuda contextual para rutas públicas y de autenticación', () => {
    const loginHelp = getScreenHelp('/login');
    expect(loginHelp.title).toBe('Inicio de Sesión');
    expect(loginHelp.steps.length).toBeGreaterThan(0);
    expect(loginHelp.tips.length).toBeGreaterThan(0);

    const regHelp = getScreenHelp('/register');
    expect(regHelp.title).toBe('Registro de Nuevo Residente');

    const pendingHelp = getScreenHelp('/espera-aprobacion');
    expect(pendingHelp.title).toBe('Cuenta Pendiente de Aprobación');
  });

  it('adapta el contenido del Dashboard según el rol del usuario (Directiva, Conserje, Residente)', () => {
    const directivaHelp = getScreenHelp('/dashboard', 'PRESIDENTE');
    expect(directivaHelp.title).toContain('Administración y Tesorería');

    const tesoreroHelp = getScreenHelp('/inicio', 'TESORERO');
    expect(tesoreroHelp.title).toContain('Administración y Tesorería');

    const conserjeHelp = getScreenHelp('/dashboard', 'CONSERJE');
    expect(conserjeHelp.title).toContain('Conserjería');

    const propietarioHelp = getScreenHelp('/dashboard', 'PROPIETARIO');
    expect(propietarioHelp.title).toContain('Tu Hogar Hoy');

    const inquilinoHelp = getScreenHelp('/dashboard', 'INQUILINO');
    expect(inquilinoHelp.title).toContain('Tu Hogar Hoy');
  });

  it('resuelve correctamente los alias del sistema financiero y operativo', () => {
    const pagarAlias = getScreenHelp('/pagar');
    const pagarPath = getScreenHelp('/finanzas/reportar-pago');
    expect(pagarAlias.title).toBe(pagarPath.title);
    expect(pagarAlias.title).toBe('Asistente de Reporte de Pagos');

    const revisionAlias = getScreenHelp('/admin/pagos-revision');
    const revisionPath = getScreenHelp('/tesoreria/pagos');
    expect(revisionAlias.title).toBe(revisionPath.title);
    expect(revisionAlias.title).toBe('Mesa de Revisión y Aprobación de Pagos');

    const finanzasAlias = getScreenHelp('/admin/finanzas');
    const cierrePath = getScreenHelp('/tesoreria/cierre');
    expect(finanzasAlias.title).toBe(cierrePath.title);
    expect(finanzasAlias.title).toBe('Cierre Contable Mensual y Egresos');

    const tareasAlias = getScreenHelp('/conserje/tareas');
    const tareasPath = getScreenHelp('/operaciones/tareas');
    expect(tareasAlias.title).toBe(tareasPath.title);
    expect(tareasAlias.title).toBe('Checklist Diario de Operaciones y Mantenimiento');

    const usuariosAlias = getScreenHelp('/admin/usuarios-pendientes');
    const usuariosPath = getScreenHelp('/admin/usuarios');
    expect(usuariosAlias.title).toBe(usuariosPath.title);
    expect(usuariosAlias.title).toBe('Bandeja de Activación de Usuarios Fantasma');
  });

  it('soporta rutas con parámetros dinámicos como /consultas/:id y limpia query params', () => {
    const consultaDetalle = getScreenHelp('/consultas/42?tab=resultados#votacion');
    expect(consultaDetalle.title).toBe('Votación y Escrutinio de Consulta');
    expect(consultaDetalle.purpose).toContain('criptográfico');

    const consultasLista = getScreenHelp('/consultas');
    expect(consultasLista.title).toBe('Cartas Consulta y Asambleas Digitales');
  });

  it('retorna información específica para cada módulo del sistema', () => {
    const solvencia = getScreenHelp('/finanzas/solvencia');
    expect(solvencia.title).toBe('Certificado Digital de Solvencia');

    const facturacion = getScreenHelp('/tesoreria/facturacion');
    expect(facturacion.title).toBe('Generador de Facturación Mensual');

    const incidencias = getScreenHelp('/incidencias');
    expect(incidencias.title).toBe('Embudo de Incidencias Vecinales');

    const galeria = getScreenHelp('/voceros/galeria');
    expect(galeria.title).toBe('Galería de Gestión Comunitaria');

    const bitacora = getScreenHelp('/secretaria/bitacora');
    expect(bitacora.title).toBe('Bitácora y Minutas de Secretaría');

    const pases = getScreenHelp('/accesos/pases');
    expect(pases.title).toBe('Pases QR de Invitados y Visitantes');

    const garita = getScreenHelp('/operaciones/garita-qr');
    expect(garita.title).toBe('Control de Acceso en Garita (Lector QR)');

    const paqueteria = getScreenHelp('/operaciones/paqueteria');
    expect(paqueteria.title).toBe('Casillero y Recepción de Paquetería');

    const reservas = getScreenHelp('/reservas/areas');
    expect(reservas.title).toBe('Reserva de Áreas Comunes y Amenidades');

    const estructura = getScreenHelp('/admin/estructura');
    expect(estructura.title).toBe('Constructor de Estructura y Unidades');

    const junta = getScreenHelp('/admin/junta');
    expect(junta.title).toBe('Asignación de Cargos de la Junta de Condominio');
  });

  it('retorna la ayuda fallback ante rutas desconocidas o vacías', () => {
    const vacio = getScreenHelp('');
    expect(vacio.title).toBeDefined();

    const desconocido = getScreenHelp('/ruta-inexistente-123');
    expect(desconocido.title).toBe('Ayuda del Sistema Condominio App');
    expect(desconocido.steps.length).toBeGreaterThan(0);
    expect(desconocido.tips.length).toBeGreaterThan(0);
  });
});
