import { copyFileSync, writeFileSync } from 'fs'

// Copiar polyfills CJS al output
copyFileSync('electron/main/polyfills.cjs', 'out/main/polyfills.cjs')

// Crear launcher CJS que carga polyfills antes de ESM
writeFileSync(
  'out/main/launcher.cjs',
  "'use strict';\nrequire('./polyfills.cjs');\nimport('./index.js');\n",
)

console.log('[post-build] polyfills.cjs + launcher.cjs copiados a out/main/')
