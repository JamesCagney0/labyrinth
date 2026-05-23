/* LABYRINTH — Web Client */

const socket = io();
let cmdHistory = [];
let historyIdx  = -1;
let waitingForInput = false;
let gameActive = false;

// ── Connection ────────────────────────────────────────────────────

socket.on('connect', () => {
  setStatus('connected', 'Connected');
});

socket.on('disconnect', () => {
  setStatus('disconnected', 'Disconnected');
  gameActive = false;
});

socket.on('connected', (data) => {
  setStatus('connected', 'Ready');
});

socket.on('output', (data) => {
  appendOutput(data.text, data.echo ? 'echo' : null);
  waitingForInput = !!data.prompt;
  scrollBottom();
});

socket.on('session_ended', () => {
  appendOutput('\n[ Session ended. Refresh to play again. ]\n', 'system');
  gameActive = false;
  waitingForInput = false;
});

// ── Game start / stop ─────────────────────────────────────────────

function startGame(mature) {
  document.getElementById('title-screen').classList.add('hidden');
  document.getElementById('game-screen').classList.remove('hidden');
  document.getElementById('output').innerHTML = '';
  gameActive = true;
  waitingForInput = false;
  setStatus('connecting', 'Starting...');

  socket.emit('start_game', { mature });

  setTimeout(() => {
    document.getElementById('cmd-input').focus();
  }, 100);
}

function returnToTitle() {
  socket.emit('stop_game');
  gameActive = false;
  document.getElementById('game-screen').classList.add('hidden');
  document.getElementById('title-screen').classList.remove('hidden');
}

// ── Input ─────────────────────────────────────────────────────────

function handleKey(e) {
  const input = document.getElementById('cmd-input');

  if (e.key === 'Enter') {
    const cmd = input.value;
    input.value = '';
    if (cmd.trim()) {
      cmdHistory.unshift(cmd);
      if (cmdHistory.length > 100) cmdHistory.pop();
    }
    historyIdx = -1;
    sendCmd(cmd);

  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (historyIdx < cmdHistory.length - 1) {
      historyIdx++;
      input.value = cmdHistory[historyIdx];
    }
  } else if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (historyIdx > 0) {
      historyIdx--;
      input.value = cmdHistory[historyIdx];
    } else {
      historyIdx = -1;
      input.value = '';
    }
  }
}

function sendCmd(cmd) {
  if (!gameActive) return;
  socket.emit('command', { text: cmd });
}

// ── Output rendering ──────────────────────────────────────────────

function appendOutput(text, type) {
  const out = document.getElementById('output');
  const span = document.createElement('span');
  span.className = 'line-' + (type || classifyLine(text));
  span.textContent = text;
  out.appendChild(span);
}

function classifyLine(text) {
  const t = text.trim();

  // Borders / box-drawing
  if (t.startsWith('╔') || t.startsWith('╠') || t.startsWith('╚') ||
      t.startsWith('═') || t.startsWith('║'))
    return 'border';

  // Boss / combat dramatic lines
  if (t.startsWith('***') || t.includes('VICTORY') || t.includes('GAME OVER') ||
      t.includes('DEFEATED'))
    return t.includes('VICTORY') || t.includes('DEFEATED') ? 'success' : 'blood';

  // Level up / upgrades
  if (t.includes('LEVEL UP') || t.includes('CLASS UPGRADE') || t.includes('★') ||
      t.includes('★★'))
    return 'gold';

  // Boss intros / lore
  if (t.startsWith('  "') || t.startsWith("  '") || t.includes('journal') ||
      t.includes('Journal'))
    return 'lore';

  // Gold / items
  if (t.startsWith('+') || t.startsWith('Found:') || t.includes('gold coin'))
    return 'gold';

  // Errors / warnings
  if (t.startsWith('!') || t.startsWith('✗') || t.startsWith('Error:') ||
      t.includes('Inventory full'))
    return 'blood';

  // System / debug
  if (t.startsWith('[') && t.endsWith(']') && t.includes('migrat'))
    return 'system';

  // Floor / room headers
  if (t.startsWith('---') && t.endsWith('---'))
    return 'title';

  // Boss names in combat
  if (/^[A-Z][a-z]+ [A-Z]/.test(t) && t.includes(':') && t.includes('HP'))
    return 'boss';

  return 'normal';
}

function scrollBottom() {
  const term = document.getElementById('terminal');
  term.scrollTop = term.scrollHeight;
}

// Keep focus on input when clicking terminal
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('terminal')?.addEventListener('click', () => {
    document.getElementById('cmd-input')?.focus();
  });
});

// ── Status bar ────────────────────────────────────────────────────

function setStatus(state, text) {
  const dot  = document.getElementById('status-dot');
  const txt  = document.getElementById('status-text');
  dot.className = 'dot ' + state;
  txt.textContent = text;
}

// ── Save file management ──────────────────────────────────────────

async function showSaves() {
  const panel = document.getElementById('save-panel');
  panel.classList.remove('hidden');
  const list  = document.getElementById('save-list');
  list.innerHTML = '<span style="color:var(--text-dim);font-size:0.8rem">Loading...</span>';

  try {
    const res   = await fetch('/saves/list');
    const saves = await res.json();
    if (!saves.length) {
      list.innerHTML = '<span style="color:var(--text-dim);font-size:0.8rem">No save files found.</span>';
      return;
    }
    list.innerHTML = '';
    saves.forEach(s => {
      const div  = document.createElement('div');
      div.className = 'save-item';
      const info = s.name
        ? `${s.name} — ${s.class} L${s.level} F${s.floor}`
        : s.filename;
      div.innerHTML = `
        <div>
          <div>${s.filename}</div>
          <div class="save-info">${info}</div>
        </div>
        <button onclick="downloadSave('${s.filename}')">⬇ Download</button>
      `;
      list.appendChild(div);
    });
  } catch(e) {
    list.innerHTML = '<span style="color:var(--blood-bright);font-size:0.8rem">Could not load saves.</span>';
  }
}

function hideSaves() {
  document.getElementById('save-panel').classList.add('hidden');
}

function downloadSave(filename) {
  window.open('/saves/' + filename, '_blank');
}

async function exportSave() {
  showSaves();
}

async function uploadSave(input) {
  if (!input.files.length) return;
  const file = input.files[0];
  const form = new FormData();
  form.append('file', file);

  try {
    const res  = await fetch('/saves/upload', { method: 'POST', body: form });
    const data = await res.json();
    if (data.ok) {
      alert(`✓ ${data.filename} uploaded successfully. Restart the game to use it.`);
      showSaves();
    } else {
      alert('Upload failed: ' + (data.error || 'Unknown error'));
    }
  } catch(e) {
    alert('Upload failed: ' + e.message);
  }
  input.value = '';
}

// ── Background particle effect ────────────────────────────────────

(function initBg() {
  const canvas = document.getElementById('bg-canvas');
  const ctx    = canvas.getContext('2d');

  let W, H, particles = [];

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  class Particle {
    constructor() { this.reset(true); }
    reset(initial) {
      this.x    = Math.random() * W;
      this.y    = initial ? Math.random() * H : H + 5;
      this.vy   = -(0.1 + Math.random() * 0.4);
      this.size = 0.5 + Math.random() * 1.5;
      this.life = 0;
      this.max  = 200 + Math.random() * 300;
      // Alternate between gold dust and blue sparks
      this.gold = Math.random() > 0.6;
    }
    update() {
      this.y   += this.vy;
      this.x   += (Math.random() - 0.5) * 0.3;
      this.life++;
      if (this.y < -5 || this.life > this.max) this.reset(false);
    }
    draw() {
      const alpha = Math.sin((this.life / this.max) * Math.PI) * 0.5;
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fillStyle = this.gold
        ? `rgba(201,168,76,${alpha})`
        : `rgba(42,82,152,${alpha * 0.7})`;
      ctx.fill();
    }
  }

  function init() {
    resize();
    particles = Array.from({length: 80}, () => new Particle());
  }

  function loop() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => { p.update(); p.draw(); });
    requestAnimationFrame(loop);
  }

  window.addEventListener('resize', resize);
  init();
  loop();
})();
