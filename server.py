#!/usr/bin/env python3
from pathlib import Path
from flask import Flask, render_template_string, send_from_directory, request, jsonify
import json
import time

app = Flask(__name__, static_folder="static")
ANNOTATIONS_DIR = Path(app.static_folder) / "annotations"

# --- HTML Templates ---
HTML_INDEX = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>NASA Tiler — JP2 datasets</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&display=swap');
    
    :root {
      --radius: 0.5rem;
      --foreground: #ffffff;
      --orange-primary: #FF8C42;
      --red-primary: #D94D2C;
      --red-secondary: #B13B2D;
      --background-mars-top: #8B3A3A;
      --background-mars-bottom: #FF6B35;
    }
    body {
      font-family: 'Orbitron', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 2rem;
      background: linear-gradient(180deg, var(--background-mars-top) 0%, var(--background-mars-bottom) 100%);
      color: var(--foreground);
      min-height: 100vh;
      position: relative;
      overflow-x: hidden;
    }
    
    /* Animated stars */
    body::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 40%;
      background-image: 
        radial-gradient(2px 2px at 20px 30px, rgba(255,255,255,0.5), rgba(0,0,0,0)),
        radial-gradient(2px 2px at 60px 70px, rgba(255,255,255,0.4), rgba(0,0,0,0)),
        radial-gradient(1px 1px at 50px 50px, rgba(255,255,255,0.3), rgba(0,0,0,0)),
        radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.6), rgba(0,0,0,0)),
        radial-gradient(2px 2px at 90px 10px, rgba(255,255,255,0.5), rgba(0,0,0,0));
      background-size: 200px 200px;
      background-position: 0 0, 40px 60px, 130px 270px, 70px 100px, 150px 50px;
      animation: twinkle 5s ease-in-out infinite;
      pointer-events: none;
      z-index: 0;
    }
    
    @keyframes twinkle {
      0%, 100% { opacity: 0.6; }
      50% { opacity: 1; }
    }
    
    .container {
      max-width: 900px;
      margin: 2rem auto;
      padding: 2rem;
      text-align: center;
      position: relative;
      z-index: 1;
    }
    h1 {
      font-size: 3.5rem;
      font-weight: 700;
      margin-bottom: 1rem;
      text-shadow: 0 4px 8px rgba(0,0,0,0.3);
      letter-spacing: 2px;
    }
    h1 span {
        display: block;
        font-size: 4rem;
        margin-bottom: 1rem;
    }
    .subtitle {
      font-size: 1.1rem;
      margin-bottom: 2rem;
      opacity: 0.9;
      font-weight: 400;
    }
    ul {
      list-style-type: none;
      padding: 0;
      margin-top: 2rem;
    }
    .btn {
      display: block;
      padding: 1.2rem;
      margin: 0.8rem auto;
      max-width: 400px;
      border-radius: 50px;
      text-decoration: none;
      font-weight: 700;
      transition: all 0.3s ease-in-out;
      border: 3px solid transparent;
      font-family: 'Orbitron', sans-serif;
      letter-spacing: 1px;
      text-transform: uppercase;
      font-size: 1rem;
      box-shadow: 0 4px 15px rgba(0,0,0,0.3);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .btn-primary {
      background-color: var(--orange-primary);
      color: #000;
      border-color: var(--orange-primary);
    }
    .btn-primary:hover {
      background-color: #FFA057;
      border-color: #FFA057;
      transform: translateY(-3px);
      box-shadow: 0 6px 20px rgba(255, 140, 66, 0.5);
    }
    .btn-secondary {
      background-color: var(--red-primary);
      color: var(--foreground);
      border-color: var(--red-primary);
    }
    .btn-secondary:hover {
      background-color: var(--red-secondary);
      border-color: var(--red-secondary);
      transform: translateY(-3px);
      box-shadow: 0 6px 20px rgba(217, 77, 44, 0.5);
    }
  </style>
</head>
<body>
  <div class="container">
    <h1> Welcome to the HiRISE Gallery</h1>
    <p class="subtitle">You've successfully connected to the HiRISE. Click on the images to explore the HiRISE images taken by the Mars Reconnaissance Orbiter (MRO)</p>
    <ul>{{IMAGE_LIST | safe}}</ul>
  </div>
</body>
</html>
"""

VIEWER_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/><title>Viewer - {{name}}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700&display=swap');
    
    :root {
      --radius: 0.5rem;
      --foreground: #ffffff;
      --orange-primary: #FF8C42;
      --red-primary: #D94D2C;
      --red-secondary: #B13B2D;
      --background-mars-top: #8B3A3A;
      --background-mars-bottom: #FF6B35;
      --panel-bg: rgba(0, 0, 0, 0.3);
      --border-color: rgba(255, 255, 255, 0.2);
    }
    html, body {
      height: 100vh; width: 100vw; margin: 0; padding: 0;
      background: linear-gradient(180deg, var(--background-mars-top) 0%, var(--background-mars-bottom) 100%);
      font-family: 'Orbitron', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: var(--foreground); overflow: hidden;
    }
    
    /* Stars effect */
    body::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 40%;
      background-image: 
        radial-gradient(2px 2px at 20px 30px, rgba(255,255,255,0.5), rgba(0,0,0,0)),
        radial-gradient(2px 2px at 60px 70px, rgba(255,255,255,0.4), rgba(0,0,0,0)),
        radial-gradient(1px 1px at 50px 50px, rgba(255,255,255,0.3), rgba(0,0,0,0)),
        radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.6), rgba(0,0,0,0)),
        radial-gradient(2px 2px at 90px 10px, rgba(255,255,255,0.5), rgba(0,0,0,0));
      background-size: 200px 200px;
      background-position: 0 0, 40px 60px, 130px 270px, 70px 100px, 150px 50px;
      pointer-events: none;
      z-index: 0;
    }
    
    * { box-sizing: border-box; }
    .viewer-grid-container {
      display: grid; grid-template-columns: 200px 1fr 240px;
      grid-template-rows: 1fr auto; grid-template-areas: "sidebar-left main sidebar-right" "timeline timeline timeline";
      height: 100vh; padding: 1rem; gap: 1rem; position: relative; z-index: 1;
    }
    .sidebar-left { grid-area: sidebar-left; }
    .main-viewer-area { grid-area: main; position: relative; border: 2px solid var(--border-color); border-radius: var(--radius); background: #000; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
    .sidebar-right { grid-area: sidebar-right; display: flex; flex-direction: column; gap: 1rem; }
    .timeline-explorer { grid-area: timeline; }
    .panel { background: var(--panel-bg); border: 2px solid var(--border-color); border-radius: var(--radius); padding: 1rem; backdrop-filter: blur(10px); overflow: hidden; }
    .panel h3 { margin-top: 0; margin-bottom: 1rem; font-size: 0.9rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .panel p { word-wrap: break-word; overflow-wrap: break-word; font-size: 0.85rem; line-height: 1.4; }
    .btn {
      display: inline-flex; align-items: center; justify-content: center; width: 100%;
      border-radius: 50px; text-decoration: none; padding: 0.8rem 1rem; font-weight: 700;
      transition: all 0.3s ease-in-out; cursor: pointer; text-align: center;
      font-family: 'Orbitron', sans-serif; text-transform: uppercase; letter-spacing: 0.5px;
      box-shadow: 0 3px 10px rgba(0,0,0,0.3);
    }
    .btn-primary {
      background-color: var(--orange-primary); color: #000; border: 2px solid var(--orange-primary);
    }
    .btn-primary:hover { background-color: #FFA057; border-color: #FFA057; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255, 140, 66, 0.5); }
    .btn-secondary {
        background-color: transparent; color: var(--orange-primary); border: 2px solid var(--orange-primary);
    }
    .btn-secondary:hover { background-color: rgba(255, 140, 66, 0.2); transform: translateY(-2px); }
    .annotation-group input[type="text"] {
        width: 100%; border: 2px solid var(--border-color); background: rgba(0,0,0,0.3);
        padding: 0.7rem; border-radius: var(--radius); margin-bottom: 0.75rem; color: var(--foreground);
        font-family: 'Orbitron', sans-serif; font-size: 0.9rem;
    }
    .annotation-group input[type="text"]:focus { outline: none; border-color: var(--orange-primary); }
    .annotation-status { font-size: 0.75rem; color: #ccc; min-height: 20px; }
    #viewer { width: 100%; height: 100%; border-radius: var(--radius); }
    #viewer .openseadragon-canvas { cursor: url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIxNiIgY3k9IjE2IiByPSI2IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjEuNSIvPjxwYXRoIGQ9Ik0xNiA0VjEwTTE2IDIyVjI4TTQgMTZIMTBMMjIgMTZIMjgiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMS41Ii8+PC9zdmc+') 16 16, crosshair; }
    .viewer-controls { position: absolute; top: 1rem; left: 1rem; z-index: 100; display: flex; flex-direction: column; gap: 0.5rem; }
    .control-btn {
        width: 40px; height: 40px; font-size: 1.2rem; padding: 0; font-weight: 700;
        background-color: var(--panel-bg); color: var(--orange-primary); border: 2px solid var(--orange-primary);
        backdrop-filter: blur(10px);
    }
    .control-btn:hover { background-color: rgba(255, 140, 66, 0.2); transform: scale(1.1); }
    .annotation-marker { width: 24px; height: 24px; border-radius: 50%; background-color: rgba(255, 140, 66, 0.6); border: 2px solid white; box-shadow: 0 0 8px rgba(255, 140, 66, 0.8); cursor: pointer; }
    .annotation-marker:hover .annotation-tooltip { display: block; }
    .annotation-tooltip { display: none; position: absolute; bottom: 120%; left: 50%; transform: translateX(-50%); background: #222; color: white; padding: 5px 10px; border-radius: 4px; font-size: 0.9rem; white-space: nowrap; font-family: 'Orbitron', sans-serif; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/openseadragon@4.1.1/build/openseadragon/openseadragon.min.js"></script>
</head>
<body>
<div class="viewer-grid-container">
    <div class="sidebar-left"></div>
    <div class="main-viewer-area"><div id="viewer"></div><div class="viewer-controls"><button id="zoom-in" class="btn control-btn">+</button><button id="zoom-out" class="btn control-btn">-</button></div></div>
    <div class="sidebar-right">
        <div class="panel"><h3>Dataset</h3><p>{{name}}</p></div>
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
        try {
            const response = await fetch(`/annotations/${datasetName}`);
            if (!response.ok) return;
            const annotations = await response.json();
            annotations.forEach(drawAnnotation);
        } catch (e) { console.error("Could not load annotations", e); }
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
                list_items += f'<li><a href="/viewer/{name}" class="btn btn-primary">{name}</a></li>'
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