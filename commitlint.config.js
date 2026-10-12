module.exports = {
  // Extiende las reglas estándar de la industria (Conventional Commits)
  extends: ['@commitlint/config-conventional'],

  rules: {
    // 1. Tipos de commit permitidos
    'type-enum': [
      2,
      'always',
      [
        'feat',     // Nueva característica
        'fix',      // Corrección de un error
        'docs',     // Cambios exclusivos en documentación
        'chore',    // Tareas de mantenimiento (dependencias, configuraciones)
        'style',    // Cambios estéticos que no alteran la lógica
        'refactor', // Refactorización (ni añade feature ni arregla bug)
        'ci',       // Cambios en los pipelines (.github/workflows)
        'test',     // Adición o corrección de pruebas
        'perf',     // Mejoras de rendimiento comprobables
        'revert'    // Revertir un commit previo
      ]
    ],

    // 2. Ámbitos adaptados a las carpetas del repositorio
    'scope-enum': [
      2,
      'always',
      [
        'backend',  // Cambios en backend/ (FastAPI, QA, Docker)
        'docs',     // Cambios en docs/ o archivos .md globales
        'infra',    // Hooks, scripts, auditorías de infraestructura
        'ci',       // Cambios en configuración de integración continua
        'global'    // Cambios que afectan a todo el repositorio
      ]
    ],

    // 3. Reglas sobre la descripción del commit (Subject)
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    'subject-case': [2, 'never', ['upper-case', 'pascal-case', 'start-case']],

    // 4. Reglas estructurales
    'type-empty': [2, 'never'],
    'header-max-length': [2, 'always', 72]
  }
};