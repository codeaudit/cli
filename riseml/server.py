import os
import mimetypes
import json

from flask import Flask, request, Response, jsonify, send_file, abort, render_template_string
from flask_cors import CORS
import yaml
from jsonschema import validate, ValidationError

from config_parser import RepositoryConfig


template = '''<!DOCTYPE html>
<html>
<body>
<p>This host is running an API endpoint at <code>/predict</code>.</p>
<p>Input</p>
<ul>
{% if deploy.input %}
{% for name, schema_name in deploy.input.items() %}
<li>{{ name }}: <code>{{ schema_name }}</code></li>
{% endfor %}
{% endif %}
</ul>
<p>Output</p>
<ul>
{% if deploy.output %}
{% for name, schema_name in deploy.output.items() %}
<li>{{ name }}: <code>{{ schema_name }}</code></li>
{% endfor %}
{% endif %}
</ul>
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
    config = RepositoryConfig.from_yml_file('riseml.yml')

    schemas = {}
    if config and config.deploy and config.deploy.output and config.deploy.output:
        for name, schema_name in config.deploy.output.items():
            if get_mimetype(schema_name)[1]:
                root = os.path.abspath(os.path.dirname(__file__))
                loc = os.path.join(root, 'schemas', schema_name + '.yml')
                if not os.path.isfile(loc):
                    raise Exception('schema %s not found' % schema_name)
                with open(loc, 'rb') as f:
                    schemas[schema_name] = yaml.load(f.read())

    def _validate(obj, schema_name):
        if schema_name in schemas:
            validate(obj, schemas[schema_name])
            return json.dumps(obj)
        return obj

    @app.route('/')
    def _root():
        return render_template_string(template,
            deploy=config.deploy)

    @app.route('/predict', methods=['POST'])
    def _predict():
        for name, schema_name in config.deploy.output.items():
            try:
                return Response(
                    _validate(func(request.files[name].read()), schema_name),
                    mimetype=get_mimetype(schema_name)[0])
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

    app.run(host=host, port=port, threaded=False)
