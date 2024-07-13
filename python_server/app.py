import chirp.inference.search.display as display
import flask_cors
from flask import Flask, request, jsonify

app = Flask(__name__)
flask_cors.CORS(app)

@app.route('/convertMelspec', methods=['POST'])
def convert_melspec():
    data = request.json
    melspec = display.convert_melspec(data['melspec'])
    return jsonify({'melspec': melspec.tolist()})