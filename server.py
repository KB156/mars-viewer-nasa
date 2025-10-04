#!/usr/bin/env python3
from pathlib import Path
from flask import Flask, render_template_string, send_from_directory, request, jsonify
import json
import time
import os
import base64
import google.generativeai as genai

# --- AI Model Configuration ---
# Configure the Gemini API client using an environment variable
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    ai_model = genai.GenerativeModel('models/gemini-pro-latest')
    print("✅ Gemini AI Model configured successfully.")
except KeyError:
    ai_model = None
    print("⚠️ WARNING: GOOGLE_API_KEY environment variable not set. AI features will be disabled.")

# --- EDIT THIS DICTIONARY to define which images can be compared ---
# To make two images comparable, you must add an entry for each one.
# For example, to compare A and B, you need both 'A': 'B' and 'B': 'A'.
SIMILAR_IMAGES = {
    "ESP_011371_1835_ESP_011522_1835_RED": "ESP_012047_1155_ESP_029809_1155_RED",
    "ESP_012047_1155_ESP_029809_1155_RED": "ESP_011371_1835_ESP_011522_1835_RED",

    "ESP_062317_1740_MRGB" : "ESP_069651_1740_MRGB",
    "ESP_069651_1740_MRGB" : "ESP_062317_1740_MRGB",


    # Add other pairs here, for example:
    # "IMAGE_C_NAME": "IMAGE_D_NAME",
    # "IMAGE_D_NAME": "IMAGE_C_NAME",
}

app = Flask(__name__, static_folder="static")
ANNOTATIONS_DIR = Path(app.static_folder) / "annotations"

# --- HTML Templates ---
HTML_INDEX = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>HiRISE Gallery</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&display=swap');
    
    :root {
      --radius: 0.5rem;
      --foreground: #F0F0F0;
      --orange-accent: #FF6B35; /* A fiery orange for highlights */
      --red-primary: #D94D2C;   /* A strong red for key elements */
      --background-deep-space: #2a0800; /* Very dark, deep red */
      --background-horizon: #8B3A3A;    /* Muted red horizon */
      --border-color: rgba(255, 107, 53, 0.3); /* Glowing orange border */
    }
    * {
        box-sizing: border-box;
    }
    body {
      font-family: 'Orbitron', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 2rem;
      background: linear-gradient(180deg, var(--background-deep-space) 0%, var(--background-horizon) 100%);
      color: var(--foreground);
      min-height: 100vh;
      position: relative;
    }
    
    @keyframes move-stars {
        from { transform: translateY(0px); }
        to   { transform: translateY(-2000px); }
    }
    .stars {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        width: 100%;
        height: 100%;
        display: block;
        z-index: -1;
    }
    .stars.s1 {
        background: transparent url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2000"><circle cx="100" cy="300" r="1" fill="white"/><circle cx="400" cy="200" r="1" fill="white"/><circle cx="900" cy="800" r="1" fill="white"/><circle cx="1300" cy="600" r="1" fill="white"/><circle cx="1800" cy="1100" r="1" fill="white"/><circle cx="50" cy="1800" r="1" fill="white"/><circle cx="650" cy="1400" r="1" fill="white"/><circle cx="1050" cy="100" r="1" fill="white"/><circle cx="1450" cy="950" r="1" fill="white"/><circle cx="1950" cy="1550" r="1" fill="white"/><circle cx="220" cy="740" r="1" fill="white"/><circle cx="780" cy="1860" r="1" fill="white"/><circle cx="1230" cy="1340" r="1" fill="white"/><circle cx="1680" cy="250" r="1" fill="white"/><circle cx="880" cy="550" r="1" fill="white"/></svg>') repeat;
        animation: move-stars 200s linear infinite;
    }
    .stars.s2 {
        background: transparent url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2000"><circle cx="250" cy="500" r="2" fill="white"/><circle cx="600" cy="800" r="2" fill="white"/><circle cx="1100" cy="1200" r="2" fill="white"/><circle cx="1500" cy="300" r="2" fill="white"/><circle cx="1900" cy="900" r="2" fill="white"/><circle cx="430" cy="1700" r="2" fill="white"/><circle cx="830" cy="100" r="2" fill="white"/><circle cx="1330" cy="1950" r="2" fill="white"/><circle cx="1730" cy="1400" r="2" fill="white"/></svg>') repeat;
        animation: move-stars 150s linear infinite;
    }
    .stars.s3 {
        background: transparent url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2000"><circle cx="150" cy="900" r="3" fill="white"/><circle cx="800" cy="1400" r="3" fill="white"/><circle cx="1200" cy="100" r="3" fill="white"/><circle cx="1600" cy="700" r="3" fill="white"/><circle cx="300" cy="1800" r="3" fill="white"/><circle cx="1000" cy="500" r="3" fill="white"/><circle cx="1850" cy="1600" r="3" fill="white"/></svg>') repeat;
        animation: move-stars 100s linear infinite;
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
    .subtitle {
      font-size: 1.1rem;
      margin-bottom: 2rem;
      opacity: 0.9;
      font-weight: 400;
    }
    ul {
      list-style-type: none;
      padding: 0;
      margin-top: 3rem;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 2rem;
    }
    .image-card {
      position: relative;
      display: block;
      aspect-ratio: 4 / 3;
      text-decoration: none;
      color: var(--foreground);
      background-color: rgba(0,0,0,0.3);
      backdrop-filter: blur(5px);
      border-radius: var(--radius);
      overflow: hidden;
      border: 2px solid var(--border-color);
      box-shadow: 0 4px 15px rgba(0,0,0,0.3);
      transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
    }
    .image-card:hover {
      transform: translateY(-5px);
      box-shadow: 0 8px 25px rgba(0,0,0,0.5);
      border-color: var(--orange-accent);
    }
    .image-card img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
      transition: transform 0.3s ease;
    }
    .image-card:hover img {
      transform: scale(1.05);
    }
    .card-title {
      position: absolute;
      bottom: 0;
      left: 0;
      width: 100%;
      padding: 1.5rem 0.8rem 0.8rem 0.8rem;
      font-weight: 600;
      text-align: center;
      font-size: 0.9rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: white;
      text-shadow: 1px 1px 3px rgba(0,0,0,0.7);
      background: linear-gradient(to top, rgba(0, 0, 0, 0.85) 0%, transparent 100%);
    }
  </style>
</head>
<body>
  <div class="stars s1"></div>
  <div class="stars s2"></div>
  <div class="stars s3"></div>
  <div class="container">
    <h1>Welcome to the HiRISE Gallery</h1>
    <p class="subtitle">You've successfully connected to the HiRISE. Click on an image to explore the high-resolution datasets from the Mars Reconnaissance Orbiter (MRO).</p>
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
      --orange-accent: #FF6B35;
      --red-primary: #D94D2C;
      --background-deep-space: #2a0800;
      --background-horizon: #8B3A3A;
      --panel-bg: rgba(0, 0, 0, 0.3);
      --border-color: rgba(255, 107, 53, 0.3);
    }
    html, body {
      height: 100vh; width: 100vw; margin: 0; padding: 0;
      background: linear-gradient(180deg, var(--background-deep-space) 0%, var(--background-horizon) 100%);
      font-family: 'Orbitron', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: var(--foreground); overflow: hidden;
    }
    
    @keyframes move-stars {
        from { transform: translateY(0px); }
        to   { transform: translateY(-2000px); }
    }
    .stars {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        width: 100%; height: 100%;
        display: block; z-index: 0;
    }
    .stars.s1 {
        background: transparent url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2000"><circle cx="100" cy="300" r="1" fill="white"/><circle cx="400" cy="200" r="1" fill="white"/><circle cx="900" cy="800" r="1" fill="white"/><circle cx="1300" cy="600" r="1" fill="white"/><circle cx="1800" cy="1100" r="1" fill="white"/></svg>') repeat;
        animation: move-stars 200s linear infinite;
    }
    .stars.s2 {
        background: transparent url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2000"><circle cx="250" cy="500" r="2" fill="white"/><circle cx="600" cy="800" r="2" fill="white"/><circle cx="1100" cy="1200" r="2" fill="white"/><circle cx="1500" cy="300" r="2" fill="white"/><circle cx="1900" cy="900" r="2" fill="white"/></svg>') repeat;
        animation: move-stars 150s linear infinite;
    }
    
    * { box-sizing: border-box; }
    .viewer-grid-container {
      display: grid; 
      grid-template-columns: 240px 1fr 240px;
      grid-template-rows: 1fr; 
      grid-template-areas: "sidebar-left main sidebar-right";
      height: 100vh; padding: 1rem; gap: 1rem; position: relative; z-index: 1;
    }
    .sidebar-left, .sidebar-right { 
        grid-area: sidebar-left; 
        display: flex; 
        flex-direction: column; 
        gap: 1rem; 
        max-height: calc(100vh - 2rem);
    }
    .sidebar-right { grid-area: sidebar-right; }
    .main-viewer-area { grid-area: main; position: relative; border: 2px solid var(--border-color); border-radius: var(--radius); background: #000; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
    .panel { background: var(--panel-bg); border: 2px solid var(--border-color); border-radius: var(--radius); padding: 1rem; backdrop-filter: blur(10px); display: flex; flex-direction: column; }
    .panel h3 { margin-top: 0; margin-bottom: 1rem; font-size: 0.9rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; flex-shrink: 0; }
    .panel p { word-wrap: break-word; overflow-wrap: break-word; font-size: 0.85rem; line-height: 1.4; }
    
    .btn {
      display: inline-flex; align-items: center; justify-content: center; width: 100%;
      border-radius: 50px; text-decoration: none; padding: 0.8rem 1rem; font-weight: 700;
      transition: all 0.3s ease-in-out; cursor: pointer; text-align: center;
      font-family: 'Orbitron', sans-serif; text-transform: uppercase; letter-spacing: 0.5px;
      box-shadow: 0 3px 10px rgba(0,0,0,0.3);
      color: white; border: 2px solid var(--orange-accent);
    }
    .btn-primary { background-color: var(--orange-accent); }
    .btn-primary:hover { background-color: var(--red-primary); border-color: var(--red-primary); transform: translateY(-2px); box-shadow: 0 5px 15px rgba(217, 77, 44, 0.5); }
    .btn-secondary { background-color: transparent; }
    .btn-secondary:hover { background-color: rgba(255, 107, 53, 0.2); transform: translateY(-2px); }
    
    .form-group input, .form-group textarea {
        width: 100%; border: 2px solid var(--border-color); background: rgba(0,0,0,0.3);
        padding: 0.7rem; border-radius: var(--radius); margin-bottom: 0.75rem; color: var(--foreground);
        font-family: 'Orbitron', sans-serif; font-size: 0.9rem;
    }
    .form-group input:focus, .form-group textarea:focus { outline: none; border-color: var(--orange-accent); }
    .status-text { font-size: 0.75rem; color: #ccc; min-height: 20px; }
    #viewer { width: 100%; height: 100%; border-radius: var(--radius); }
    #viewer .openseadragon-canvas { cursor: url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIxNiIgY3k9IjE2IiByPSI2IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjEuNSIvPjxwYXRoIGQ9Ik0xNiA0VjEwTTE2IDIyVjI4TTQgMTZIMTBMMjIgMTZIMjgiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMS41Ii8+PC9zdmc+') 16 16, crosshair; }
    .viewer-controls { position: absolute; top: 1rem; left: 1rem; z-index: 100; display: flex; flex-direction: column; gap: 0.5rem; }
    .control-btn {
        width: 40px; height: 40px; font-size: 1.2rem; padding: 0; font-weight: 700;
        background-color: var(--panel-bg); color: var(--orange-accent); border: 2px solid var(--orange-accent);
        backdrop-filter: blur(10px);
    }
    .control-btn:hover { background-color: rgba(255, 107, 53, 0.2); transform: scale(1.1); }
    
    .annotation-marker { width: 24px; height: 24px; border-radius: 50%; background-color: rgba(255, 107, 53, 0.6); border: 2px solid white; box-shadow: 0 0 8px rgba(255, 107, 53, 0.8); cursor: pointer; }
    #ai-response-area {
        background-color: rgba(0,0,0,0.2); border-radius: var(--radius); padding: 0.8rem;
        margin-top: 0.5rem; font-size: 0.85rem; line-height: 1.5;
        white-space: pre-wrap; overflow-y: auto; flex-grow: 1; min-height: 0;
    }
    
    /* --- NEW: Comparison Modal Styles --- */
    .modal-overlay {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-color: rgba(0,0,0,0.85); backdrop-filter: blur(10px);
        display: none; /* Hidden by default */
        flex-direction: column; z-index: 1000; padding: 2rem;
    }
    .modal-header { display: flex; justify-content: space-between; align-items: center; color: white; margin-bottom: 1rem; flex-shrink: 0;}
    .modal-header h2 { margin: 0; }
    #close-modal-btn { background: transparent; border: none; color: white; font-size: 2.5rem; cursor: pointer; }
    .modal-content { display: flex; flex-grow: 1; gap: 1rem; }
    .viewer-container { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; color: white; text-align: center; }
    .compare-viewer { width: 100%; height: 100%; border: 2px solid var(--border-color); border-radius: var(--radius); }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/openseadragon@4.1.1/build/openseadragon/openseadragon.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
</head>
<body>
  <div class="stars s1"></div>
  <div class="stars s2"></div>
<div class="viewer-grid-container">
    <div class="sidebar-left">
        <div class="panel"><h3>Dataset</h3><p>{{name}}</p></div>
        
        {% if compare_target %}
        <div class="panel">
            <h3>Compare Images</h3>
            <p style="font-size: 0.8rem; opacity: 0.8; margin-bottom: 1rem;">A similar image is available for side-by-side comparison.</p>
            <button id="compare-btn" class="btn btn-secondary">Compare</button>
        </div>
        {% endif %}
        
        <div class="panel form-group">
            <h3>Annotations</h3>
            <p id="annotation-status" class="status-text">Click on the image to place a marker.</p>
            <input type="text" id="annotation-text" placeholder="Add annotation...">
            <button id="add-annotation-btn" class="btn btn-secondary">+ Add</button>
        </div>
    </div>
    <div class="main-viewer-area"><div id="viewer"></div><div class="viewer-controls"><button id="zoom-in" class="btn control-btn">+</button><button id="zoom-out" class="btn control-btn">-</button></div></div>
    <div class="sidebar-right">
        <div class="panel form-group" style="flex-grow: 1;">
            <h3>AI Planetary Expert</h3>
            <textarea id="ai-question-input" placeholder="Ask about this view..." rows="3" style="resize: vertical;"></textarea>
            <button id="ai-ask-btn" class="btn btn-primary">Ask The Expert</button>
            <div id="ai-response-area">Response will appear here...</div>
        </div>
    </div>
</div>

<div id="compare-modal" class="modal-overlay">
    <div class="modal-header">
        <h2>Image Comparison</h2>
        <button id="close-modal-btn">&times;</button>
    </div>
    <div class="modal-content">
        <div class="viewer-container">
            <p>{{ name }}</p>
            <div id="viewer-left" class="compare-viewer"></div>
        </div>
        <div class="viewer-container">
            <p>{{ compare_target }}</p>
            <div id="viewer-right" class="compare-viewer"></div>
        </div>
    </div>
</div>

<script>
    const datasetName = "{{name}}"; let newAnnotationPoint = null;
    const viewer = OpenSeadragon({ id: "viewer", prefixUrl: "https://cdn.jsdelivr.net/npm/openseadragon@4.1.1/build/openseadragon/images/", tileSources: `/static/tiles/{{name}}/output.dzi`, showZoomControl: false, showHomeControl: false, showFullScreenControl: false, showNavigator: false });
    function drawAnnotation(annotation) {
        const marker = document.createElement('div'); marker.className = 'annotation-marker';
        marker.style.pointerEvents = 'auto'; /* Enable clicks on the marker */
        const tooltip = document.createElement('div'); 
        tooltip.style.display = 'none';
        tooltip.style.position = 'absolute';
        tooltip.style.bottom = '120%';
        tooltip.style.left = '50%';
        tooltip.style.transform = 'translateX(-50%)';
        tooltip.style.background = '#222';
        tooltip.style.color = 'white';
        tooltip.style.padding = '5px 10px';
        tooltip.style.borderRadius = '4px';
        tooltip.style.fontSize = '0.9rem';
        tooltip.style.whiteSpace = 'nowrap';
        tooltip.textContent = annotation.text;
        marker.appendChild(tooltip);
        marker.onmouseover = () => { tooltip.style.display = 'block'; };
        marker.onmouseout = () => { tooltip.style.display = 'none'; };
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
    document.getElementById('ai-ask-btn').addEventListener('click', async function() {
        const questionInput = document.getElementById('ai-question-input');
        const question = questionInput.value.trim();
        const responseArea = document.getElementById('ai-response-area');
        const viewerElement = document.getElementById('viewer');
        if (!question) {
            responseArea.textContent = "Please enter a question.";
            return;
        }
        responseArea.textContent = "Capturing viewport and consulting AI...";
        this.disabled = true;
        try {
            const canvas = await html2canvas(viewerElement);
            const image_data_url = canvas.toDataURL('image/jpeg', 0.9);
            const response = await fetch(`/ask/${datasetName}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    image_base_64: image_data_url
                })
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'An unknown error occurred.');
            }
            const data = await response.json();
            responseArea.textContent = data.answer;
        } catch (error) {
            console.error("AI request failed:", error);
            responseArea.textContent = `Error: ${error.message}`;
        } finally {
            this.disabled = false;
        }
    });

    // --- NEW: Comparison Modal JavaScript ---
    const compareBtn = document.getElementById('compare-btn');
    const compareModal = document.getElementById('compare-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    let viewerLeft = null;
    let viewerRight = null;

    function initCompareViewers() {
        // Only initialize if they don't already exist
        if (viewerLeft || viewerRight) return;

        const originalImage = "{{ name }}";
        const compareImage = "{{ compare_target }}";
        const osdPrefix = "https://cdn.jsdelivr.net/npm/openseadragon@4.1.1/build/openseadragon/images/";

        viewerLeft = OpenSeadragon({
            id: "viewer-left",
            prefixUrl: osdPrefix,
            tileSources: `/static/tiles/${originalImage}/output.dzi`
        });

        viewerRight = OpenSeadragon({
            id: "viewer-right",
            prefixUrl: osdPrefix,
            tileSources: `/static/tiles/${compareImage}/output.dzi`
        });
    }

    if (compareBtn) {
        compareBtn.addEventListener('click', () => {
            compareModal.style.display = 'flex';
            // Use a short delay to ensure the modal is visible before initializing viewers
            setTimeout(initCompareViewers, 50);
        });
    }

    closeModalBtn.addEventListener('click', () => {
        compareModal.style.display = 'none';
        // Destroy the viewers to free up memory and prevent errors
        if (viewerLeft) {
            viewerLeft.destroy();
            viewerLeft = null;
        }
        if (viewerRight) {
            viewerRight.destroy();
            viewerRight = null;
        }
    });

</script>
</body>
</html>
"""

# --- Web Routes ---
@app.route("/")
def index():
    image_cards_html = ""
    tiles_dir = Path(app.static_folder) / "tiles"
    if tiles_dir.exists():
        for subdir in sorted(tiles_dir.iterdir()):
            if subdir.is_dir() and (subdir / "output.dzi").exists():
                name = subdir.name
                preview_image_url = f"/static/tiles/{name}/output_files/10/0_0.jpg"
                image_cards_html += f"""
                <li>
                    <a href="/viewer/{name}" class="image-card">
                        <img src="{preview_image_url}" alt="Preview of {name}" onerror="this.parentElement.style.display='none'">
                        <div class="card-title">{name}</div>
                    </a>
                </li>
                """
    if not image_cards_html:
        image_cards_html = "<p>No processed image folders found.</p>"
    return render_template_string(HTML_INDEX, IMAGE_LIST=image_cards_html)


@app.route("/viewer/<name>")
def viewer(name):
    # Check if the current image has a comparison target defined
    compare_with = SIMILAR_IMAGES.get(name, None)
    return render_template_string(
        VIEWER_HTML, 
        name=name, 
        compare_target=compare_with
    )

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

# --- AI Route for Handling Questions ---
@app.route("/ask/<name>", methods=['POST'])
def ask_ai_about_view(name):
    if not ai_model:
        return jsonify({"error": "AI model is not configured on the server."}), 503

    data = request.get_json()
    if not data or 'question' not in data or 'image_base_64' not in data:
        return jsonify({"error": "Missing question or image data from request."}), 400

    question = data['question']
    base64_string = data['image_base_64']

    try:
        header, encoded = base64_string.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        mime_type = header.split(";")[0].split(":")[1]
        img_for_ai = {'mime_type': mime_type, 'data': image_bytes}
        
        system_prompt = """You are a helpful planetary geologist and image analysis expert. 
Your task is to analyze images from the surface of Mars provided by a user.
Answer the user's questions about the visual features in the image concisely.
If a feature is ambiguous due to image quality, it is okay to say so.
Do not make up features that are not visible.Keep the answers under 60 words. No need to mention your role."""

        prompt = [system_prompt, "User question: " + question, img_for_ai]
        response = ai_model.generate_content(prompt)
        return jsonify({"answer": response.text})

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)