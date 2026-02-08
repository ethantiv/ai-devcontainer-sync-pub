const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

function cleanup({ logs = false } = {}) {
  if (logs) {
    cleanupLogs();
    return;
  }

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

function cleanupLogs() {
  // Resolve log_rotation.py — Docker (/opt/loop) or local (relative to this file)
  const dockerPath = '/opt/loop/telegram_bot/log_rotation.py';
  const localPath = path.resolve(__dirname, '../telegram_bot/log_rotation.py');
  const scriptPath = fs.existsSync(dockerPath) ? dockerPath : localPath;

  if (!fs.existsSync(scriptPath)) {
    console.error('Error: log_rotation.py not found.');
    process.exit(1);
  }

  const projectsRoot = process.env.PROJECTS_ROOT || path.resolve(process.env.HOME, 'projects');

  const child = spawn('python3', [
    '-c',
    `import sys; sys.path.insert(0, "${path.dirname(path.dirname(scriptPath))}"); ` +
    `from telegram_bot.log_rotation import rotate_logs, cleanup_brainstorm_files; ` +
    `from pathlib import Path; ` +
    `r1 = rotate_logs(Path("${projectsRoot}")); ` +
    `r2 = cleanup_brainstorm_files(Path("${projectsRoot}")); ` +
    `total = r1["deleted"] + r2["deleted"]; freed = (r1["freed_bytes"] + r2["freed_bytes"]) / 1024 / 1024; ` +
    `print(f"Log cleanup: {total} files removed, {freed:.1f} MB freed") if total > 0 else print("No log files to clean up")`
  ], {
    stdio: 'inherit',
    cwd: process.cwd(),
  });

  child.on('close', (code) => {
    process.exit(code ?? 0);
  });
}

module.exports = { cleanup };
