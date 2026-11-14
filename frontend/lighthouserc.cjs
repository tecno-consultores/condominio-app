const fs = require('node:fs');
const path = require('node:path');

function resolvePlaywrightChrome() {
  const root = '/ms-playwright';
  if (!fs.existsSync(root)) return undefined;
  const dirs = fs.readdirSync(root).filter((d) => d.startsWith('chromium-')).sort();
  for (const dir of dirs) {
    for (const sub of ['chrome-linux64/chrome', 'chrome-linux/chrome']) {
      const candidate = path.join(root, dir, sub);
      if (fs.existsSync(candidate)) return candidate;
    }
  }
  return undefined;
}

module.exports = {
  ci: {
    collect: {
      url: ['http://ui-prod:80/login', 'http://ui-prod:80/register'],
      numberOfRuns: 1,
      chromePath: process.env.CHROME_PATH || resolvePlaywrightChrome(),
      settings: {
        chromeFlags: '--no-sandbox --disable-dev-shm-usage --headless=new --disable-gpu',
        // En red interna Docker QA (http://ui-prod:80), TLS termina en el ingress de producción.
        skipAudits: ['is-on-https', 'redirects-http'],
      },
    },
    assert: {
      assertions: {
        'categories:performance': ['error', { minScore: 0.9 }],
        'categories:accessibility': ['error', { minScore: 0.95 }],
        'categories:best-practices': ['error', { minScore: 0.95 }],
      },
    },
    upload: {
      target: 'filesystem',
      outputDir: '.lighthouseci',
    },
  },
};
