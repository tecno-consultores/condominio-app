// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Jesus Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)

module.exports = {
  // Extiende las reglas estándar de la industria (Conventional Commits)
  extends: ['@commitlint/config-conventional'],
  
  rules: {
    // 1. Tipos de commit permitidos (Qué se está haciendo)
    'type-enum': [
      2, // 2 = Nivel de error (Falla el commit si no cumple)
      'always',
      [
        'feat',     // Nueva característica (ej. nueva herramienta QA, nuevo orquestador)
        'fix',      // Corrección de un error (ej. reparar un script de limpieza)
        'docs',     // Cambios exclusivos en documentación (README, FAQ, SECURITY)
        'chore',    // Tareas de mantenimiento (actualización de dependencias, configuraciones)
        'style',    // Cambios estéticos de código (Prettier, ruff) que no alteran la lógica
        'refactor', // Refactorización de código (ni añade feature ni arregla bug)
        'ci',       // Cambios en los pipelines (.github/workflows)
        'test',     // Adición o corrección de pruebas faltantes
        'perf',     // Mejoras de rendimiento comprobables
        'revert'    // Revertir un commit previo
      ]
    ],
    
    // 2. Ámbitos permitidos (Dónde se está haciendo el cambio)
    // Adaptado estrictamente a las carpetas de tu repositorio
    'scope-enum': [
      2,
      'always',
      [
        'backend',    // Cambios en backend FastAPI
        'frontend',   // Cambios en frontend Vue 3
        'specs',      // Cambios en especificaciones técnicas
        'qa',         // Pruebas, auditorías o gates de calidad
        'graphify',   // Actualización o scripts de grafo AST
        'roadmap',    // Hoja de ruta y control de hitos
        'hito8',      // Certificación E2E/WCAG/Lighthouse
        'hito10',     // Alícuotas, facturación y solvencia
        'hito11',     // Cartas consulta LPH
        'hito12',     // Pases QR y paquetería
        'hito13',     // Reserva de amenidades
        'hito14',     // Ayuda contextual y manuales
        'hito15',     // Rediseño UX/UI OKLCH y transiciones
        'hito16',     // Gobernanza Thin-Repo y saneamiento 11X
        'hito17',     // Endurecimiento backend y sesión frontend
        'hito18',     // Empaquetado productivo Docker y worker
        'python',     // Compatibilidad blueprint python/
        'fastapi',    // Compatibilidad blueprint fastapi/
        'node',       // Compatibilidad blueprint node-backend/
        'vue3',       // Compatibilidad blueprint vue3/
        'react',      // Compatibilidad blueprint react-frontend/
        'php',        // Compatibilidad blueprint php/
        'bash',       // Compatibilidad blueprint bash-scripts/
        'mcp-server', // Compatibilidad blueprint mcp-server/
        'agents',     // Cambios en .agents/ y gobernanza IA
        'security',   // Mitigaciones de seguridad transversales
        'gate',       // Compuertas de certificación 11X
        'blueprints', // Plantillas multi-stack
        'docs',       // Cambios en la carpeta docs/ o archivos .md globales
        'ci',         // Cambios en configuración de integración continua
        'global'      // Cambios que afectan a todo el repositorio
      ]
    ],
    
    // 3. Reglas sobre la descripción del commit (Subject)
    // El asunto no puede estar vacío, no puede ser mayúscula sostenida y no debe terminar en punto.
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    'subject-case': [
      2,
      'never',
      ['upper-case', 'pascal-case', 'start-case'] // Obliga a iniciar en minúscula para mantener uniformidad
    ],
    
    // 4. Reglas estructurales
    'type-empty': [2, 'never'], // Siempre debe haber un tipo (feat, fix, etc.)
    'header-max-length': [2, 'always', 72] // Evita commits con títulos excesivamente largos
  }
};
