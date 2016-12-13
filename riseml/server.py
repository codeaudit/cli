from flask import Flask, request, Response
from flask_cors import CORS


def serve(func, host='0.0.0.0', port=3000):
    app = Flask(__name__)
    CORS(app, max_age=3600)

    @app.route('/predict', methods=['POST'])
    def predict():
        return Response(
            func(request.files['image'].read()),
            mimetype='image/jpeg')

    app.run(host=host, port=port, threaded=True)
