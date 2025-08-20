from flask import Flask, render_template, request, redirect, url_for, send_from_directory, make_response
import os
import shutil

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_file_type(filename):
    file_extension = filename.split('.')[-1].lower()
    if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        return 'image'
    elif file_extension in ['mp4', 'mkv', 'mov', 'avi']:
        return 'video'
    elif file_extension in ['mp3', 'wav', 'ogg']:
        return 'audio'
    else:
        return 'other'

@app.route('/')
@app.route('/<path:subdir>')
def index(subdir=''):
    current_dir = os.path.join(app.config['UPLOAD_FOLDER'], subdir)

    if not os.path.exists(current_dir):
        return "Folder not found", 404

    files = []
    dirs = []

    try:
        for item in os.listdir(current_dir):
            item_path = os.path.join(current_dir, item)
            if os.path.isdir(item_path):
                dirs.append(item)
            else:
                files.append({
                    'name': item,
                    'path': os.path.join(subdir, item),
                    'type': get_file_type(item)
                })
    except FileNotFoundError:
        return redirect(url_for('index', subdir=''))


    dirs.sort()
    files.sort(key=lambda x: x['name'])

    total_space, used_space, free_space = 0, 0, 0
    try:
        statvfs = os.statvfs(app.config['UPLOAD_FOLDER'])
        total_space = statvfs.f_blocks * statvfs.f_frsize
        free_space = statvfs.f_bfree * statvfs.f_frsize
        used_space = total_space - free_space
    except:
        pass

    used_mb = round(used_space / (1024 * 1024), 2)
    free_mb = round(free_space / (1024 * 1024), 2)
    used_percentage = 0
    if total_space > 0:
        used_percentage = round((used_space / total_space) * 100, 2)

    return render_template('index.html', dirs=dirs, files=files, current=subdir, used=used_mb, free=free_mb, used_percentage=used_percentage)

@app.route('/upload', methods=['POST'])
def upload():
    current_dir = request.form.get('current_dir', '')
    
    if 'files' in request.files:
        files = request.files.getlist('files')
        for file in files:
            if file.filename:
                filename = file.filename
                
                if '/' in filename:
                    sub_dir = os.path.dirname(filename)
                    target_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_dir, sub_dir)
                    os.makedirs(target_folder, exist_ok=True)
                else:
                    target_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_dir)
                    os.makedirs(target_folder, exist_ok=True)
                
                file.save(os.path.join(target_folder, os.path.basename(filename)))
    
    return redirect(url_for('index', subdir=current_dir))

@app.route('/download/<path:filename>')
def download(filename):
    if not os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        return "File not found", 404
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete_file', methods=['POST'])
def delete_file():
    filename = request.form['filename']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    return redirect(url_for('index', subdir=os.path.dirname(filename)))

@app.route('/delete_folder', methods=['POST'])
def delete_folder():
    folder_name = request.form['folder_name']
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    return redirect(url_for('index', subdir=os.path.dirname(folder_name)))
    
@app.route('/download_folder/<path:folder_path>')
def download_folder(folder_path):
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_path)
    if not os.path.isdir(full_path):
        return "Folder not found", 404
        
    base_name = os.path.basename(full_path)
    zip_path = os.path.join('/tmp', base_name)
    
    shutil.make_archive(zip_path, 'zip', root_dir=os.path.dirname(full_path), base_dir=base_name)
    
    zip_filename = f"{base_name}.zip"
    response = make_response(send_from_directory('/tmp', f"{base_name}.zip", as_attachment=True, download_name=zip_filename))
    
    @response.call_on_close
    def remove_zip_file():
        try:
            os.remove(f"/tmp/{base_name}.zip")
        except OSError as e:
            print(f"Error removing temporary zip file: {e}")
        
    return response

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=31413)