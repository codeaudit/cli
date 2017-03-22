import os
import mimetypes
import json

from flask import Flask, request, Response, jsonify, send_file, abort, render_template_string
from flask_cors import CORS
import yaml
from jsonschema import validate, ValidationError

from riseml.config_parser import parse_file


template = '''<!DOCTYPE html>
<html>
<body>
<p>This host is running an API endpoint at <code>/predict</code>.</p>

{% if deploy.input %}
<p>input: <code>{{ ', '.join(deploy.input) }}</code></p>
{% endif %}

{% if deploy.output %}
<p>output: <code>{{ ', '.join(deploy.output) }}</code></p>
{% endif %}

</body>
</html>'''

def serve(func,
          host=os.environ.get('HOST', '0.0.0.0'),
          port=os.environ.get('PORT')):

    def get_mimetype(value):
        if value:
            if value in mimetypes.types_map.values():
                return value, None
            return 'application/vnd.riseml+%s' % value, value
        return 'application/octet-stream', None

    app = Flask(__name__)
    CORS(app, max_age=3600)
    config = parse_file('riseml.yml')

    schema = None
    output_mimetype = None
    schema_name = None

    if config and config.deploy and config.deploy.output and config.deploy.output[0]:
        output_mimetype, schema_name = get_mimetype(config.deploy.output[0])
        if schema_name:
            root = os.path.abspath(os.path.dirname(__file__))
            loc = os.path.join(root, 'schemas', schema_name + '.yml')
            if not os.path.isfile(loc):
                raise Exception('schema %s not found' % schema_name)
            with open(loc, 'rb') as f:
                schema = yaml.load(f.read())

    def _validate(obj):
        if schema:
            validate(obj, schema)
            return json.dumps(obj)
        return obj

    @app.route('/')
    def _root():
        return render_template_string(template,
            deploy=config.deploy)

    @app.route('/predict', methods=['POST'])
    def _predict():
        try:
            return Response(
                _validate(func(request.files['image'].read())),
                mimetype=output_mimetype)
        except ValidationError as e:
            return jsonify({'error': 'invalid %s: %s' % (schema_name, e.message)})

    @app.route('/config', methods=['GET'])
    def _config():
        return jsonify(config.to_dict())

    @app.route('/samples/<path:path>', methods=['GET'])
    def _samples(path):
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
