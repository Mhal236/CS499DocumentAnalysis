from flask import Flask, render_template, request, redirect, url_for, abort, jsonify
import os
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.join('static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create folders if they don't exist
for folder in ['folder1', 'folder2']:
    os.makedirs(os.path.join(UPLOAD_FOLDER, folder), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_json_data():
    try:
        with open('output.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description="No file part")
        
        file = request.files['file']
        if file.filename == '':
            abort(400, description="No selected file")
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'folder1', filename))
            return redirect(url_for('index'))
        
        abort(400, description="Invalid file type")

    pre_annotated_images = [f for f in os.listdir(os.path.join(UPLOAD_FOLDER, 'folder1'))
                           if allowed_file(f)]
    annotated_images = [f for f in os.listdir(os.path.join(UPLOAD_FOLDER, 'folder2'))
                       if allowed_file(f)]
    
    return render_template('image_viewer.html',
                         pre_annotated_images=pre_annotated_images,
                         annotated_images=annotated_images)

@app.route('/annotate/<filename>')
def annotate(filename):
    if not allowed_file(filename):
        abort(400, description="Invalid file type")
        
    src = os.path.join(app.config['UPLOAD_FOLDER'], 'folder1', secure_filename(filename))
    dest = os.path.join(app.config['UPLOAD_FOLDER'], 'folder2', secure_filename(filename))
    
    if not os.path.exists(src):
        abort(404, description="File not found")
        
    os.rename(src, dest)
    return redirect(url_for('index'))

@app.route('/view/<filename>')
def view(filename):
    if not allowed_file(filename):
        abort(400, description="Invalid file type")
        
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'folder2', secure_filename(filename))
    if not os.path.exists(filepath):
        abort(404, description="File not found")
        
    data = load_json_data()
    # Handle both the filename case variations
    file_data = data.get(filename, data.get(filename.capitalize(), {}))
    if not file_data:
        # Initialize new file data if not found
        file_data = {
            "file_name": filename,
            "paragraphs": []
        }
    annotations = file_data.get('paragraphs', [])
    return render_template('display_image.html', 
                         filename=filename, 
                         annotations=annotations,
                         json_data={filename: file_data})

@app.route('/preview/<filename>')
def preview(filename):
    if not allowed_file(filename):
        abort(400, description="Invalid file type")
        
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'folder1', secure_filename(filename))
    if not os.path.exists(filepath):
        abort(404, description="File not found")
        
    return render_template('preview_image.html', filename=filename)

@app.route('/save_annotations', methods=['POST'])
def save_annotations():
    try:
        new_data = request.json
        with open('output.json', 'r') as f:
            existing_data = json.load(f)
        
        # Update only the changed file's data
        for filename, data in new_data.items():
            existing_data[filename] = data
        
        with open('output.json', 'w') as f:
            json.dump(existing_data, f, indent=4)
        
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error=error), 404

@app.errorhandler(400)
def bad_request_error(error):
    return render_template('error.html', error=error), 400

if __name__ == '__main__':
    app.run(debug=True)
