#!/usr/bin/env python3
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify
import json
import google.generativeai as genai

# --- Configuration ---
# STEP 1: Paste your Google AI API key here.
API_KEY = "AIzaSyDnoX6ZkMw7M5OPiNtfVpZFzsLR_v74hZ8"

# Configure the Generative AI library
if API_KEY and API_KEY != "AIzaSyDnoX6ZkMw7M5OPiNtfVpZFzsLR_v74hZ8":
    genai.configure(api_key=API_KEY)
    print("✅ Google AI API Key configured.")
else:
    print("\n\n⚠️ WARNING: API KEY NOT SET ⚠️")
    print("Please paste your Google AI API key into the 'API_KEY' variable in the script.\n")

# --- Flask App Setup ---
app = Flask(__name__, static_folder="static")
ANNOTATIONS_DIR = Path(app.static_folder) / "annotations"

# --- HTML Template (with both features) ---
VIEWER_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/><title>Viewer - {{name}}</title>
  <style>
    :root {
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
      grid-template-rows: 1fr; grid-template-areas: "sidebar-left main sidebar-right";
      height: 100vh; padding: 1rem; gap: 1rem;
    }
    .sidebar-left { grid-area: sidebar-left; }
    .main-viewer-area { grid-area: main; position: relative; border: 1px solid var(--border); border-radius: var(--radius); background: var(--background); }
    .sidebar-right { grid-area: sidebar-right; display: flex; flex-direction: column; gap: 1rem; overflow-y: auto; }
    .panel { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1rem; }
    .panel h3 { margin-top: 0; margin-bottom: 1rem; font-size: 0.9rem; font-weight: 600; }
    .btn { display: inline-flex; align-items: center; justify-content: center; width: 100%; border-radius: var(--radius); text-decoration: none; padding: 0.5rem 1rem; font-weight: 500; transition: all 0.2s; border: 1px solid var(--border); background: transparent; color: var(--foreground); cursor: pointer; }
    .btn:hover { background-color: var(--muted); }
    .btn.btn-primary { color: var(--primary-foreground); background-color: var(--primary); border-color: var(--primary); }
    .btn.active { background-color: var(--primary); color: var(--primary-foreground); }
    .form-group input[type="text"], .form-group textarea { width: 100%; border: 1px solid var(--border); background: var(--background); padding: 0.5rem; border-radius: var(--radius); margin-bottom: 0.75rem; color: var(--foreground); }
    .form-status { font-size: 0.8rem; color: var(--muted-foreground); min-height: 20px; }
    #rag-answer { white-space: pre-wrap; word-wrap: break-word; font-size: 0.9rem; background: var(--muted); padding: 0.75rem; border-radius: var(--radius); min-height: 50px; margin-top: 0.5rem; }
    #viewer { width: 100%; height: 100%; border-radius: var(--radius); }
    .openseadragon-canvas.drawing { cursor: crosshair; }
    #selection-rect { position: absolute; border: 2px dashed var(--primary); background-color: hsla(217, 91%, 59%, 0.2); z-index: 100; pointer-events: none; }
    .annotation-marker { width: 20px; height: 20px; border-radius: 50%; background-color: hsla(347, 91%, 59%, 0.7); border: 2px solid white; box-shadow: 0 0 5px black; cursor: pointer; transform: translate(-50%, -50%); }
    .annotation-marker:hover .annotation-tooltip { display: block; }
    .annotation-tooltip { display: none; position: absolute; bottom: 120%; left: 50%; transform: translateX(-50%); background: #222; color: white; padding: 5px 10px; border-radius: 4px; font-size: 0.9rem; white-space: nowrap; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/openseadragon@4.1.1/build/openseadragon/openseadragon.min.js"></script>
</head>
<body>
<div class="viewer-grid-container">
    <div class="sidebar-left"></div>
    <div class="main-viewer-area">
        <div id="viewer"></div>
        <div id="selection-rect" style="display:none;"></div>
    </div>
    <div class="sidebar-right">
        <div class="panel"><h3>Dataset: {{name}}</h3></div>
        <div class="panel form-group">
            <h3>Visual Query</h3>
            <p id="rag-status" class="form-status">Click "Select Region" to begin.</p>
            <button id="select-region-btn" class="btn">Select Region</button>
            <textarea id="rag-question" placeholder="Ask about the selected region..." rows="3" style="resize: vertical; margin-top: 0.75rem;"></textarea>
            <button id="ask-rag-btn" class="btn btn-primary">Ask AI</button>
            <div id="rag-answer">AI answers will appear here.</div>
        </div>
        <div class="panel form-group">
            <h3>Annotations</h3>
            <p id="annotation-status" class="form-status">Click on the image to place a marker.</p>
            <input type="text" id="annotation-text" placeholder="Add annotation...">
            <button id="add-annotation-btn" class="btn btn-primary">+ Add</button>
        </div>
    </div>
</div>

<script>
    const datasetName = "{{name}}";
    const viewer = OpenSeadragon({
        id: "viewer",
        prefixUrl: "https://cdn.jsdelivr.net/npm/openseadragon@4.1.1/build/openseadragon/images/",
        tileSources: `/static/tiles/{{name}}/output.dzi`,
    });

    // --- State Variables ---
    let isDrawing = false, isSelectionMode = false;
    let selectionRect = { startX: 0, startY: 0 };
    let selectedRegionDataUrl = null;
    let newAnnotationPoint = null;

    const selectionDiv = document.getElementById('selection-rect');
    const viewerCanvas = viewer.canvas.querySelector('.openseadragon-canvas');
    
    // --- Event Listeners Setup ---
    document.addEventListener('DOMContentLoaded', () => {
        document.getElementById('ask-rag-btn').addEventListener('click', handleVisualQuery);
        document.getElementById('select-region-btn').addEventListener('click', toggleSelectionMode);
        document.getElementById('add-annotation-btn').addEventListener('click', handleAddAnnotation);
    });

    // --- Annotation Logic ---
    function drawAnnotation(annotation) {
        const marker = document.createElement('div');
        marker.className = 'annotation-marker';
        const tooltip = document.createElement('div');
        tooltip.className = 'annotation-tooltip';
        tooltip.textContent = annotation.text;
        marker.appendChild(tooltip);
        viewer.addOverlay({ element: marker, location: new OpenSeadragon.Point(annotation.x, annotation.y) });
    }

    async function loadAnnotations() {
        try {
            const response = await fetch(`/annotations/${datasetName}`);
            if (response.ok) { (await response.json()).forEach(drawAnnotation); }
        } catch (e) { console.error("Could not load annotations", e); }
    }
    
    viewer.addHandler('open', loadAnnotations);

    async function handleAddAnnotation() {
        const textInput = document.getElementById('annotation-text');
        const text = textInput.value.trim();
        if (!newAnnotationPoint) { alert('Please click on the image to place a marker first.'); return; }
        if (!text) { alert('Please enter text for the annotation.'); return; }

        const newAnnotation = { x: newAnnotationPoint.x, y: newAnnotationPoint.y, text: text };
        const response = await fetch(`/annotations/${datasetName}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newAnnotation)
        });

        if (response.ok) {
            drawAnnotation(newAnnotation);
            textInput.value = '';
            newAnnotationPoint = null;
            document.getElementById('annotation-status').textContent = 'Annotation saved! Click image for a new one.';
        } else { alert('Failed to save annotation.'); }
    }
    
    // --- Visual Query Logic ---
    function toggleSelectionMode() {
        isSelectionMode = !isSelectionMode;
        const btn = document.getElementById('select-region-btn');
        if (isSelectionMode) {
            btn.classList.add('active'); btn.textContent = 'Cancel Selection';
            viewer.setMouseNavEnabled(false); viewerCanvas.classList.add('drawing');
            document.getElementById('rag-status').textContent = 'Click and drag on the image.';
        } else {
            btn.classList.remove('active'); btn.textContent = 'Select Region';
            viewer.setMouseNavEnabled(true); viewerCanvas.classList.remove('drawing');
            selectionDiv.style.display = 'none';
        }
    }

    function cropSelectedRegion() {
        const rect = selectionDiv.getBoundingClientRect();
        const viewerRect = viewer.container.getBoundingClientRect();
        const [x, y, width, height] = [rect.left - viewerRect.left, rect.top - viewerRect.top, rect.width, rect.height];
        
        if (width <= 0 || height <= 0) { selectedRegionDataUrl = null; return; }
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = width; tempCanvas.height = height;
        const ctx = tempCanvas.getContext('2d');
        ctx.drawImage(viewer.drawer.canvas, x, y, width, height, 0, 0, width, height);
        selectedRegionDataUrl = tempCanvas.toDataURL('image/jpeg');
    }

    async function handleVisualQuery() {
        const question = document.getElementById('rag-question').value.trim();
        const answerDiv = document.getElementById('rag-answer');
        if (!question) { alert('Please enter a question.'); return; }
        if (!selectedRegionDataUrl) { alert('Please select a region on the image first.'); return; }
        answerDiv.textContent = '🧠 Sending to server for analysis...';
        const base64_image = selectedRegionDataUrl.split(',')[1];
        try {
            const response = await fetch('/query_visual_rag', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: base64_image, question: question })
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Server Error: ${response.statusText}`);
            }
            const data = await response.json();
            answerDiv.textContent = data.answer;
        } catch (error) {
            console.error("Visual Query failed:", error);
            answerDiv.textContent = `Error: ${error.message}`;
        }
    }
    
    // --- Combined Mouse/Canvas Event Handlers ---
    viewer.addHandler('canvas-press', e => {
        if (!isSelectionMode) return;
        isDrawing = true;
        selectionRect = { startX: e.position.x, startY: e.position.y };
        Object.assign(selectionDiv.style, {left: `${e.position.x}px`, top: `${e.position.y}px`, width: '0px', height: '0px', display: 'block'});
    });
    viewer.addHandler('canvas-drag', e => {
        if (!isSelectionMode) return;
        let { startX, startY } = selectionRect;
        let endX = e.position.x, endY = e.position.y;
        Object.assign(selectionDiv.style, {
            left: `${Math.min(startX, endX)}px`, top: `${Math.min(startY, endY)}px`,
            width: `${Math.abs(startX - endX)}px`, height: `${Math.abs(startY - endY)}px`
        });
    });
    viewer.addHandler('canvas-release', e => {
        if (!isDrawing) return;
        isDrawing = false;
        cropSelectedRegion();
        toggleSelectionMode();
        document.getElementById('rag-status').textContent = '✅ Region selected. Ask a question.';
    });
    viewer.addHandler('canvas-click', function(event) {
        if (isSelectionMode) return; // Don't place annotation marker when selecting a region
        newAnnotationPoint = viewer.viewport.pointFromPixel(event.position);
        document.getElementById('annotation-status').textContent = 'Marker placed. Add text and save.';
    });
</script>
</body>
</html>
"""

# --- Server-Side AI Query Route ---
@app.route("/query_visual_rag", methods=['POST'])
def query_visual_rag():
    if not API_KEY or API_KEY == "PASTE_YOUR_API_KEY_HERE":
        return jsonify({"error": "API key is not configured on the server."}), 500
    
    data = request.get_json()
    if not data or 'image' not in data or 'question' not in data:
        return jsonify({"error": "Missing image or question"}), 400

    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    image_part = {"mime_type": "image/jpeg", "data": data['image']}
    prompt_parts = [f"Analyze this specific region of a satellite image. {data['question']}", image_part]

    try:
        response = model.generate_content(prompt_parts)
        return jsonify({"answer": response.text})
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500

# --- Existing Web Routes and Annotation Endpoints ---
HTML_INDEX = """
<!doctype html><html><head><meta charset="utf-8"/><title>NASA Tiler — JP2 datasets</title><style>:root{--background:hsl(222.2 84% 4.9%);--foreground:hsl(210 40% 98%);--card:hsl(222.2 84% 4.9%);--muted:hsl(217.2 32.6% 17.5%);--muted-foreground:hsl(215 20.2% 65.1%);--primary:hsl(217.2 91.2% 59.8%);--primary-foreground:hsl(210 40% 98%);--border:hsl(217.2 32.6% 17.5%);--radius:0.5rem}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;margin:0;padding:2rem;background-color:var(--background);color:var(--foreground)}.container{max-width:900px;margin:2rem auto;padding:2rem;border-radius:var(--radius);border:1px solid var(--border);background:var(--card)}h1{text-align:center}ul{list-style-type:none;padding:0}li a{display:block;padding:1rem;margin-bottom:0.5rem;border-radius:var(--radius);background:var(--muted);color:var(--foreground);text-decoration:none;transition:background-color .2s}li a:hover{background-color:var(--primary);color:var(--primary-foreground)}</style></head><body><div class="container"><h1><span>🛰️</span> Available HiRISE Images</h1><ul>{{IMAGE_LIST | safe}}</ul></div></body></html>
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
        list_items = "<p>No processed image folders found.</p>"
    return render_template_string(HTML_INDEX, IMAGE_LIST=list_items)

@app.route("/viewer/<name>")
def viewer(name):
    return render_template_string(VIEWER_HTML, name=name)

@app.route("/annotations/<name>", methods=['GET', 'POST'])
def handle_annotations(name):
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    annotation_file = ANNOTATIONS_DIR / f"{name}.json"
    if request.method == 'GET':
        if not annotation_file.exists(): return jsonify([])
        with open(annotation_file, 'r', encoding='utf-8') as f:
            try: data = json.load(f)
            except json.JSONDecodeError: data = []
        return jsonify(data)
    if request.method == 'POST':
        new_annotation = request.get_json()
        if not new_annotation: return jsonify({"error": "Invalid data"}), 400
        annotations = []
        if annotation_file.exists():
            with open(annotation_file, 'r', encoding='utf-8') as f:
                try: annotations = json.load(f)
                except json.JSONDecodeError: pass
        annotations.append(new_annotation)
        with open(annotation_file, 'w', encoding='utf-8') as f:
            json.dump(annotations, f, indent=2)
        return jsonify({"success": True}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)