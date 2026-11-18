import type { RolUsuario } from '../stores/authStore';
import type { NavIconKey } from './navIcons';

export interface NavigationLinkItem {
  id: string;
  label: string;
  to: string;
  icon: NavIconKey;
  section: 'FINANZAS' | 'COMUNIDAD' | 'OPERACIONES';
  roles?: RolUsuario[];
}

export interface NavigationSection {
  key: NavigationLinkItem['section'];
  title: string;
  links: NavigationLinkItem[];
}

export const NAVIGATION_LINKS: NavigationLinkItem[] = [
  {
    id: 'side-dashboard',
    label: 'Resumen Financiero',
    to: '/dashboard',
    icon: 'home',
    section: 'FINANZAS',
  },
  {
    id: 'side-pagar',
    label: 'Reportar Pago',
    to: '/finanzas/reportar-pago',
    icon: 'credit-card',
    section: 'FINANZAS',
  },
  {
    id: 'side-solvencia',
    label: 'Certificado de Solvencia',
    to: '/finanzas/solvencia',
    icon: 'shield-check',
    section: 'FINANZAS',
  },
  {
    id: 'side-revision-pagos',
    label: 'Aprobación de Pagos',
    to: '/tesoreria/pagos',
    icon: 'check-square',
    section: 'FINANZAS',
    roles: ['TESORERO', 'PRESIDENTE'],
  },
  {
    id: 'side-cierre-mensual',
    label: 'Cierre Mensual Contable',
    to: '/tesoreria/cierre',
    icon: 'calculator',
    section: 'FINANZAS',
    roles: ['TESORERO', 'PRESIDENTE'],
  },
  {
    id: 'side-facturacion',
    label: 'Facturación Mensual LPH',
    to: '/tesoreria/facturacion',
    icon: 'receipt',
    section: 'FINANZAS',
    roles: ['TESORERO', 'PRESIDENTE'],
  },
  {
    id: 'side-incidencias',
    label: 'Embudo de Incidencias',
    to: '/incidencias',
    icon: 'alert-circle',
    section: 'COMUNIDAD',
  },
  {
    id: 'side-consultas',
    label: 'Cartas Consulta (Art. 23)',
    to: '/consultas',
    icon: 'vote',
    section: 'COMUNIDAD',
  },
  {
    id: 'side-bitacora',
    label: 'Bitácora de Actas',
    to: '/secretaria/bitacora',
    icon: 'book-open',
    section: 'COMUNIDAD',
  },
  {
    id: 'side-voceros',
    label: 'Galería de Voceros',
    to: '/voceros/galeria',
    icon: 'users',
    section: 'COMUNIDAD',
  },
  {
    id: 'side-reservas',
    label: 'Reserva de Áreas Sociales',
    to: '/reservas/areas',
    icon: 'calendar',
    section: 'COMUNIDAD',
  },
  {
    id: 'side-pases-qr',
    label: 'Pases de Visita QR',
    to: '/accesos/pases',
    icon: 'qr-code',
    section: 'OPERACIONES',
  },
  {
    id: 'side-garita-qr',
    label: 'Escáner Garita QR',
    to: '/operaciones/garita-qr',
    icon: 'scan',
    section: 'OPERACIONES',
    roles: ['CONSERJE', 'PRESIDENTE', 'VOCERO'],
  },
  {
    id: 'side-paqueteria',
    label: 'Paquetería en Garita',
    to: '/operaciones/paqueteria',
    icon: 'package',
    section: 'OPERACIONES',
  },
  {
    id: 'side-tareas',
    label: 'Tareas de Conserjería',
    to: '/operaciones/tareas',
    icon: 'clipboard-check',
    section: 'OPERACIONES',
  },
  {
    id: 'side-estructura',
    label: 'Estructura Física',
    to: '/admin/estructura',
    icon: 'building',
    section: 'OPERACIONES',
    roles: ['PRESIDENTE', 'VICEPRESIDENTE'],
  },
  {
    id: 'side-usuarios',
    label: 'Usuarios Fantasma',
    to: '/admin/usuarios',
    icon: 'user-check',
    section: 'OPERACIONES',
    roles: ['PRESIDENTE', 'VICEPRESIDENTE'],
  },
  {
    id: 'side-junta',
    label: 'Junta de Condominio',
    to: '/admin/junta',
    icon: 'award',
    section: 'OPERACIONES',
    roles: ['PRESIDENTE'],
  },
];

export const NAVIGATION_SECTIONS: Array<{ key: NavigationLinkItem['section']; title: string }> = [
  { key: 'FINANZAS', title: 'Mi Hogar y Finanzas' },
  { key: 'COMUNIDAD', title: 'Comunidad y Gobernanza' },
  { key: 'OPERACIONES', title: 'Operaciones y Junta Directiva' },
];

export function canRoleAccessLink(
  link: NavigationLinkItem,
  activeRole: RolUsuario | null,
): boolean {
  return !link.roles || (activeRole !== null && link.roles.includes(activeRole));
}

export function getVisibleNavigationSections(activeRole: RolUsuario | null): NavigationSection[] {
  return NAVIGATION_SECTIONS.map((sec) => ({
    key: sec.key,
    title: sec.title,
    links: NAVIGATION_LINKS.filter(
      (link) => link.section === sec.key && canRoleAccessLink(link, activeRole),
    ),
  })).filter((sec) => sec.links.length > 0);
}
