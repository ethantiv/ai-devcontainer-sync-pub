const { spawn } = require('child_process');
const fs = require('fs');

function cleanup() {
  const cleanupScript = './loop/cleanup.sh';

  if (!fs.existsSync(cleanupScript)) {
    console.error('Error: loop/cleanup.sh not found. Run "npx loop init" first.');
    process.exit(1);
  }

  const child = spawn(cleanupScript, [], {
    stdio: 'inherit',
    cwd: process.cwd(),
  });

  child.on('close', (code) => {
    process.exit(code ?? 0);
  });
}

module.exports = { cleanup };
