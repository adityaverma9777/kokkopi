const esbuild = require('esbuild');

const isWatch = process.argv.includes('--watch');

esbuild.build({
  entryPoints: ['src/widget.ts'],
  bundle: true,
  minify: true,
  sourcemap: true,
  outfile: 'dist/widget.js',
  target: ['chrome100', 'safari15', 'firefox100'],
  format: 'iife',
}).then(result => {
  if (isWatch) {
    console.log('Watching...');
  } else {
    console.log('Build completed.');
  }
}).catch(() => process.exit(1));
