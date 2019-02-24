from flask import Flask, render_template, request
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/upload', methods=["POST"])
def upload():
    file = request.files['inputFile']
    
    return file.filename
    
if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=True)