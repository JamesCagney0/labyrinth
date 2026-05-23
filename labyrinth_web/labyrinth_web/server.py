"""
LABYRINTH — Web Server
Flask + SocketIO backend. Each browser tab gets its own game session.
Run: python server.py
"""
import sys, os, json, threading, queue, uuid, logging

# Add game package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'labyrinth'))

from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import io

logging.basicConfig(level=logging.WARNING)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'labyrinth-secret-key'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# Active game sessions: sid -> GameSession
sessions = {}


class GameSession:
    """Wraps a Game instance for a single browser session."""

    def __init__(self, sid: str, mature: bool = False):
        self.sid        = sid
        self.mature     = mature
        self.game       = None
        self.input_q    = queue.Queue()
        self.output_buf = []
        self.thread     = None
        self.running    = False

    def start(self):
        self.running = True
        self.thread  = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        """Run the game in a background thread, redirecting I/O."""
        import builtins, io as _io

        original_input = builtins.input
        original_print = builtins.print

        def patched_input(prompt=''):
            # Send prompt to browser
            if prompt:
                self._emit_output(str(prompt), prompt=True)
            # Block until player types something
            try:
                value = self.input_q.get(timeout=300)  # 5 min timeout
                return value
            except queue.Empty:
                raise EOFError("Session timed out")

        def patched_print(*args, **kwargs):
            end  = kwargs.get('end', '\n')
            sep  = kwargs.get('sep', ' ')
            text = sep.join(str(a) for a in args) + end
            self._emit_output(text)

        builtins.input = patched_input
        builtins.print = patched_print

        try:
            from game import Game
            self.game = Game()
            if self.mature:
                self.game.mature_mode = True
            self.game.start_game()
        except Exception as e:
            self._emit_output(f'\n[Session ended: {e}]\n')
        finally:
            builtins.input = original_input
            builtins.print = original_print
            self.running   = False
            socketio.emit('session_ended', {}, room=self.sid)

    def _emit_output(self, text: str, prompt: bool = False):
        socketio.emit('output', {'text': text, 'prompt': prompt}, room=self.sid)

    def send_input(self, text: str):
        self.input_q.put(text)

    def stop(self):
        self.running = False
        self.input_q.put('')  # unblock any waiting input()


# ── Routes ────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/saves/<filename>')
def download_save(filename):
    """Download a save file."""
    save_dir = os.path.join(os.path.dirname(__file__), '..', 'labyrinth', 'saves')
    path = os.path.join(save_dir, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404


@app.route('/saves/upload', methods=['POST'])
def upload_save():
    """Upload / replace a save file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    f = request.files['file']
    if not f.filename.endswith('.json'):
        return jsonify({'error': 'Must be a .json save file'}), 400
    save_dir = os.path.join(os.path.dirname(__file__), '..', 'labyrinth', 'saves')
    os.makedirs(save_dir, exist_ok=True)
    f.save(os.path.join(save_dir, f.filename))
    return jsonify({'ok': True, 'filename': f.filename})


@app.route('/saves/list')
def list_saves():
    """List available save files."""
    save_dir = os.path.join(os.path.dirname(__file__), '..', 'labyrinth', 'saves')
    if not os.path.exists(save_dir):
        return jsonify([])
    files = [fn for fn in os.listdir(save_dir) if fn.endswith('.json')]
    result = []
    for fn in sorted(files):
        path = os.path.join(save_dir, fn)
        try:
            data = json.load(open(path))
            # save1-5 have player info
            if 'name' in data:
                result.append({
                    'filename': fn,
                    'name':  data.get('name', '?'),
                    'class': data.get('character_class', '?'),
                    'level': data.get('level', 1),
                    'floor': data.get('current_floor', 1),
                })
            else:
                result.append({'filename': fn})
        except Exception:
            result.append({'filename': fn})
    return jsonify(result)


# ── SocketIO events ───────────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    sid = request.sid
    join_room(sid)
    emit('connected', {'sid': sid})


@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    if sid in sessions:
        sessions[sid].stop()
        del sessions[sid]


@socketio.on('start_game')
def on_start_game(data):
    sid    = request.sid
    mature = data.get('mature', False)
    if sid in sessions and sessions[sid].running:
        sessions[sid].stop()
    session = GameSession(sid, mature=mature)
    sessions[sid] = session
    session.start()


@socketio.on('command')
def on_command(data):
    sid = request.sid
    cmd = data.get('text', '').strip()
    if sid in sessions:
        # Echo the command back so it appears in the terminal
        emit('output', {'text': cmd + '\n', 'echo': True})
        sessions[sid].send_input(cmd)


@socketio.on('stop_game')
def on_stop_game():
    sid = request.sid
    if sid in sessions:
        sessions[sid].stop()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n  LABYRINTH Web Server")
    print(f"  Running at http://localhost:{port}")
    print(f"  Press Ctrl+C to stop\n")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
