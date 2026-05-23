# LABYRINTH Web Server

## Local Setup

```bash
# From the labyrinth_web folder:
pip install -r requirements.txt
python server.py
# Then open http://localhost:5000
```

## File Structure

```
labyrinth_web/
  server.py          ← Flask + SocketIO backend
  requirements.txt   ← pip dependencies
  templates/
    index.html       ← Game UI
  static/
    css/style.css    ← Dark fantasy styling
    js/game.js       ← Terminal client + WebSocket

labyrinth/           ← Existing game package (unchanged)
  main.py
  game.py
  ... (all 23 files)
  saves/             ← Save files (accessible via web UI)
```

## Deploying to Railway (free, ~5 min)

1. Push both `labyrinth/` and `labyrinth_web/` to a GitHub repo
2. Go to railway.app → New Project → Deploy from GitHub
3. Set start command: `python labyrinth_web/server.py`
4. Set environment variable: `PORT=8080`
5. Done — Railway gives you a public URL

## Deploying to Render (free)

1. Push to GitHub
2. Go to render.com → New Web Service
3. Build command: `pip install -r labyrinth_web/requirements.txt`
4. Start command: `python labyrinth_web/server.py`
5. Done

## Save File Management

- **Download save:** Click 💾 → shows all save files → click Download
- **Upload save:** Click 📂 → pick a .json save file
- Save files live in `labyrinth/saves/` on the server
- Each player session is independent — multiple people can play simultaneously

## Notes

- Each browser tab = independent game session
- Sessions timeout after 5 minutes of inactivity
- The `--mature` flag is available via the "Enter (Mature)" button
- Mobile-friendly — works on iOS Safari and Android Chrome
