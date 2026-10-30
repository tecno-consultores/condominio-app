module.exports = {
  root: true,
  ignorePatterns: ['dist/**', 'coverage/**', 'node_modules/**', '*.json', 'lighthouserc.js'],
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  parser: 'vue-eslint-parser',
  parserOptions: {
    parser: '@typescript-eslint/parser',
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  plugins: ['@typescript-eslint', 'vue', 'sonarjs'],
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:sonarjs/recommended',
    'prettier',
  ],
  rules: {
    'vue/multi-word-component-names': 'off',
    'sonarjs/cognitive-complexity': ['error', 15],
    'sonarjs/no-duplicate-string': 'off',
    '@typescript-eslint/no-explicit-any': 'error',
  },
};
