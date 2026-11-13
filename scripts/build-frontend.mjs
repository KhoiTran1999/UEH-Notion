import { cp, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const frontend = resolve(root, 'frontend');
const vendor = resolve(frontend, 'vendor');
const output = resolve(frontend, 'assets', 'tailwind.css');
const tailwindCli = resolve(root, 'node_modules', 'tailwindcss', 'lib', 'cli.js');

await mkdir(resolve(frontend, 'assets'), { recursive: true });
await mkdir(vendor, { recursive: true });

await execFileAsync(
  process.execPath,
  [tailwindCli, '-i', './frontend/src/input.css', '-o', './frontend/assets/tailwind.css', '--minify'],
  { cwd: root }
);

const katexFiles = [
  ['katex/dist/katex.min.css', 'katex.min.css'],
  ['katex/dist/katex.min.js', 'katex.min.js'],
  ['katex/dist/contrib/auto-render.min.js', 'auto-render.min.js']
];

for (const [source, target] of katexFiles) {
  await cp(resolve(root, 'node_modules', source), resolve(vendor, target));
}

console.log(`Built ${output}`);
