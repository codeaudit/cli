import os

from flask import Flask, request, Response, jsonify, send_file, abort
from flask_cors import CORS

from riseml.config_parser import parse_file


def serve(func, host='0.0.0.0', port=os.environ.get('PORT')):
    app = Flask(__name__)
    CORS(app, max_age=3600)
    riseml_yml = 'riseml.yml'

    @app.route('/predict', methods=['POST'])
    def predict():
        return Response(
            func(request.files['image'].read()),
            mimetype='image/jpeg')

    @app.route('/config', methods=['GET'])
    def config():
        return jsonify(parse_file(riseml_yml).to_dict())

    @app.route('/samples/<path:path>', methods=['GET'])
    def samples(path):
        config = parse_file(riseml_yml)
        if (config.deploy and config.deploy.demo and
            config.deploy.demo.samples and
            path in config.deploy.demo.samples):

            full_path = os.path.join(os.getcwd(), path)
            if not os.path.exists(full_path):
                abort(404)
            with open(full_path) as f:
                return Response(
                    func(f.read()),
                    mimetype='image/jpeg')

        abort(404)

    app.run(host=host, port=port, threaded=True)
