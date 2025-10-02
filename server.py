#!/usr/bin/env python3
from pathlib import Path
from flask import Flask, render_template_string, send_from_directory, request, jsonify
import json
import time

app = Flask(__name__, static_folder="static")
ANNOTATIONS_DIR = Path(app.static_folder) / "annotations"

# --- HTML Templates ---
HTML_INDEX = """
<!doctype html><html><head><meta charset="utf-8"/><title>NASA Tiler</title>
<style>
  :root { --background: hsl(222.2 84% 4.9%); --foreground: hsl(210 40% 98%); --card: hsl(222.2 84% 4.9%); --muted: hsl(217.2 32.6% 17.5%); --muted-foreground: hsl(215 20.2% 65.1%); --primary: hsl(217.2 91.2% 59.8%); --primary-foreground: hsl(210 40% 98%); --border: hsl(217.2 32.6% 17.5%); --radius: 0.5rem; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 2rem; background-color: var(--background); color: var(--foreground); }
  .container { max-width: 900px; margin: 2rem auto; padding: 2rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--card); }
  h1 { text-align: center; } ul { list-style-type: none; padding: 0; }
  li a { display: block; padding: 1rem; margin-bottom: 0.5rem; border-radius: var(--radius); background: var(--muted); color: var(--foreground); text-decoration: none; transition: background-color 0.2s; }
  li a:hover { background-color: var(--primary); color: var(--primary-foreground); }
</style></head><body><div class="container"><h1><span>🛰️</span> Available HiRISE Images</h1><ul>{{IMAGE_LIST}}</ul></div></body></html>
"""

VIEWER_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/><title>Viewer - {{name}}</title>
  <style>
    :root {
      /* Dark Theme Palette */
      --background: hsl(224, 71%, 4%); --foreground: hsl(210 40% 98%);
      --card: hsl(224, 71%, 4%); --card-foreground: hsl(210 40% 98%);
      --muted: hsl(217.2 32.6% 17.5%); --muted-foreground: hsl(215 20.2% 65.1%);
      --primary: hsl(217.2 91.2% 59.8%); --primary-foreground: hsl(210 40% 98%);
      --border: hsl(217.2 32.6% 17.5%); --radius: 0.5rem;
    }
    html, body {
      height: 100vh; width: 100vw; margin: 0; padding: 0;
      background-color: var(--background);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: var(--foreground); overflow: hidden;
    }
    * { box-sizing: border-box; }
    .viewer-grid-container {
      display: grid; grid-template-columns: 200px 1fr 240px;
      grid-template-rows: 1fr auto; grid-template-areas: "sidebar-left main sidebar-right" "timeline timeline timeline";
      height: 100vh; padding: 1rem; gap: 1rem;
    }
    .sidebar-left { grid-area: sidebar-left; }
    .main-viewer-area { grid-area: main; position: relative; border: 1px solid var(--border); border-radius: var(--radius); background: var(--background); }
    .sidebar-right { grid-area: sidebar-right; display: flex; flex-direction: column; gap: 1rem; }
    .timeline-explorer { grid-area: timeline; }
    .panel { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1rem; }
    .panel h3 { margin-top: 0; margin-bottom: 1rem; font-size: 0.9rem; font-weight: 600; }
    .btn { display: inline-flex; align-items: center; justify-content: center; width: 100%; border-radius: var(--radius); text-decoration: none; padding: 0.5rem 1rem; font-weight: 500; transition: all 0.2s; border: 1px solid var(--border); background: transparent; color: var(--foreground); cursor: pointer; }
    .btn:hover { background-color: var(--muted); }
    .btn.btn-primary { color: var(--primary-foreground); background-color: var(--primary); border-color: var(--primary); }
    .annotation-group input[type="text"] { width: 100%; border: 1px solid var(--border); background: var(--background); padding: 0.5rem; border-radius: var(--radius); margin-bottom: 0.75rem; color: var(--foreground); }
    .annotation-status { font-size: 0.8rem; color: var(--muted-foreground); min-height: 20px; }
    #viewer { width: 100%; height: 100%; border-radius: var(--radius); }
    #viewer .openseadragon-canvas { cursor: url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIxNiIgY3k9IjE2IiByPSI2IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjEuNSIvPjxwYXRoIGQ9Ik0xNiA0VjEwTTE2IDIyVjI4TTQgMTZIMTBMMjIgMTZIMjgiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMS41Ii8+PC9zdmc+') 16 16, crosshair; }
    .viewer-controls { position: absolute; top: 1rem; left: 1rem; z-index: 100; display: flex; flex-direction: column; gap: 0.5rem; }
    .control-btn { width: 36px; height: 36px; font-size: 1rem; padding: 0; background: var(--card); }
    .annotation-marker { width: 24px; height: 24px; border-radius: 50%; background-color: hsla(217, 91%, 59%, 0.5); border: 2px solid white; box-shadow: 0 0 5px black; cursor: pointer; }
    .annotation-marker:hover .annotation-tooltip { display: block; }
    .annotation-tooltip { display: none; position: absolute; bottom: 120%; left: 50%; transform: translateX(-50%); background: #222; color: white; padding: 5px 10px; border-radius: 4px; font-size: 0.9rem; white-space: nowrap; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/openseadragon@4.1.1/build/openseadragon/openseadragon.min.js"></script>
</head><body>
<div class="viewer-grid-container">
    <div class="sidebar-left"></div>
    <div class="main-viewer-area"><div id="viewer"></div><div class="viewer-controls"><button id="zoom-in" class="btn control-btn">+</button><button id="zoom-out" class="btn control-btn">-</button></div></div>
    <div class="sidebar-right">
        <div class="panel"><h3>Dataset</h3></div>
        <div class="panel annotation-group">
            <h3>Annotations</h3>
            <p id="annotation-status" class="annotation-status">Click on the image to place a marker.</p>
            <input type="text" id="annotation-text" placeholder="Add annotation..."><button id="add-annotation-btn" class="btn btn-primary">+ Add</button>
        </div>
    </div>
    <div class="timeline-explorer panel"></div>
</div>
<script>
    const datasetName = "{{name}}"; let newAnnotationPoint = null;
    const viewer = OpenSeadragon({ id: "viewer", prefixUrl: "https://cdn.jsdelivr.net/npm/openseadragon@4.1.1/build/openseadragon/images/", tileSources: `/static/tiles/{{name}}/output.dzi`, showZoomControl: false, showHomeControl: false, showFullScreenControl: false, showNavigator: false });
    function drawAnnotation(annotation) {
        const marker = document.createElement('div'); marker.className = 'annotation-marker';
        const tooltip = document.createElement('div'); tooltip.className = 'annotation-tooltip'; tooltip.textContent = annotation.text;
        marker.appendChild(tooltip);
        viewer.addOverlay({ element: marker, location: new OpenSeadragon.Point(annotation.x, annotation.y) });
    }
    async function loadAnnotations() {
        const response = await fetch(`/annotations/${datasetName}`); const annotations = await response.json();
        annotations.forEach(drawAnnotation);
    }
    viewer.addHandler('open', loadAnnotations);
    viewer.addHandler('canvas-click', function(event) {
        newAnnotationPoint = viewer.viewport.pointFromPixel(event.position);
        document.getElementById('annotation-status').textContent = 'Marker placed. Add text and save.';
    });
    document.getElementById('add-annotation-btn').addEventListener('click', async function() {
        const textInput = document.getElementById('annotation-text'); const text = textInput.value.trim();
        if (!newAnnotationPoint) { alert('Please click on the image to place a marker first.'); return; }
        if (!text) { alert('Please enter some text for the annotation.'); return; }
        const newAnnotation = { x: newAnnotationPoint.x, y: newAnnotationPoint.y, text: text };
        const response = await fetch(`/annotations/${datasetName}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(newAnnotation) });
        if (response.ok) {
            drawAnnotation(newAnnotation); textInput.value = ''; newAnnotationPoint = null;
            document.getElementById('annotation-status').textContent = 'Annotation saved! Click image for new marker.';
        } else { alert('Failed to save annotation.'); }
    });
    document.getElementById('zoom-in').addEventListener('click', () => viewer.viewport.zoomBy(1.4));
    document.getElementById('zoom-out').addEventListener('click', () => viewer.viewport.zoomBy(1 / 1.4));
</script>
</body>
</html>
"""

# --- Web Routes ---
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
        list_items = "<p>No processed image folders found.</p>"
    return render_template_string(HTML_INDEX, IMAGE_LIST=list_items)

@app.route("/viewer/<name>")
def viewer(name):
    return render_template_string(VIEWER_HTML, name=name)

# --- Annotation API Endpoints ---
@app.route("/annotations/<name>", methods=['GET'])
def get_annotations(name):
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    annotation_file = ANNOTATIONS_DIR / f"{name}.json"
    if not annotation_file.exists():
        return jsonify([])
    with open(annotation_file, 'r') as f:
        try: data = json.load(f)
        except json.JSONDecodeError: data = []
    response = jsonify(data)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.route("/annotations/<name>", methods=['POST'])
def add_annotation(name):
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    new_annotation = request.get_json()
    if not new_annotation: return jsonify({"error": "Invalid data"}), 400
    
    annotation_file = ANNOTATIONS_DIR / f"{name}.json"
    annotations = []
    if annotation_file.exists():
        with open(annotation_file, 'r') as f:
            try: annotations = json.load(f)
            except json.JSONDecodeError: pass
    
    annotations.append(new_annotation)
    
    with open(annotation_file, 'w') as f:
        json.dump(annotations, f, indent=2)
    return jsonify({"success": True}), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)