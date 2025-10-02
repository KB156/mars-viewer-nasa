#!/usr/bin/env python3
from pathlib import Path
from flask import Flask, render_template_string

app = Flask(__name__, static_folder="static")

# The only change is in this HTML block below
HTML_INDEX = """
<!doctype html><html><head><meta charset="utf-8"/><title>NASA Tiler</title>
<style>
  :root { --background: hsl(222.2 84% 4.9%); --foreground: hsl(210 40% 98%); --card: hsl(222.2 84% 4.9%); --muted: hsl(217.2 32.6% 17.5%); --muted-foreground: hsl(215 20.2% 65.1%); --primary: hsl(217.2 91.2% 59.8%); --primary-foreground: hsl(210 40% 98%); --border: hsl(217.2 32.6% 17.5%); --radius: 0.5rem; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 2rem; background-color: var(--background); color: var(--foreground); }
  .container { max-width: 900px; margin: 2rem auto; padding: 2rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--card); }
  h1 { text-align: center; } ul { list-style-type: none; padding: 0; }
  li a { display: block; padding: 1rem; margin-bottom: 0.5rem; border-radius: var(--radius); background: var(--muted); color: var(--foreground); text-decoration: none; transition: background-color 0.2s; }
  li a:hover { background-color: var(--primary); color: var(--primary-foreground); }
</style></head><body><div class="container"><h1><span>🛰️</span> Available HiRISE Images</h1>
  <ul>{{IMAGE_LIST | safe}}</ul>
</div></body></html>
"""

VIEWER_HTML = """
<!doctype html><html><head><meta charset="utf-8"/><title>Viewer - {{name}}</title>
<style>html, body, #viewer { width: 100%; height: 100%; margin: 0; padding: 0; background: #000; }</style>
<script src="https://cdn.jsdelivr.net/npm/openseadragon@4.1.1/build/openseadragon/openseadragon.min.js"></script>
</head><body><div id="viewer"></div><script>
OpenSeadragon({ id: "viewer", prefixUrl: "https://cdn.jsdelivr.net/npm/openseadragon@4.1.1/build/openseadragon/images/", tileSources: "/static/tiles/{{name}}/output.dzi", showNavigator: true });
</script></body></html>
"""

@app.route("/")
def index():
    list_items = ""
    tiles_dir = Path(app.static_folder) / "tiles"
    if tiles_dir.exists():
        for subdir in sorted(tiles_dir.iterdir()):
            if subdir.is_dir() and (subdir / "output.dzi").exists():
                name = subdir.name
                list_items += f'<li><a href="/viewer/{name}">{name}</a></li>'
    if not list_items:
        list_items = "<p>No processed image folders found in static/tiles.</p>"
    return render_template_string(HTML_INDEX, IMAGE_LIST=list_items)

@app.route("/viewer/<name>")
def viewer(name):
    return render_template_string(VIEWER_HTML, name=name)

if __name__ == "__main__":
    from flask import send_from_directory
    @app.route("/static/tiles/<path:filename>")
    def serve_tiles(filename):
        return send_from_directory(Path(app.static_folder) / "tiles", filename)
    app.run(host="0.0.0.0", port=8080, debug=True)