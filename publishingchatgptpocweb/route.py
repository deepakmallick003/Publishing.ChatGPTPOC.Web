import logging
import json
import threading
from flask import Flask, render_template, request, jsonify
from flask import Response
from flask_socketio import SocketIO
from core.config import PathConfig, settings
from core.pbiembedservice import PbiEmbedService
from scripts import ai, file


app = Flask(__name__, template_folder=PathConfig.TEMPLATE_DIRECTORY, static_folder=PathConfig.STATIC_DIRECTORY)
app.config['BASE_PATH'] = settings.DEPLOYED_BASE_PATH
app.config['BASE_PATH'] ='' if settings.DEPLOYED_BASE_PATH =='/' else settings.DEPLOYED_BASE_PATH
app.config['USE_WEB_SOCKET'] =settings.USE_WEB_SOCKET

socketio=None
if settings.USE_WEB_SOCKET=='true':
    socketio = SocketIO(app, cors_allowed_origins="*")

PathConfig.init_app(app)
# Instantiate AI
file_instance = file.FILES(PathConfig)
ai_instance = ai.AI(settings, PathConfig, file_instance, socketio)

# @app.before_request
# def before_request_func():
#     if settings.FLASK_ENV == 'production':
#         if 'user' not in session and request.endpoint != 'authorize':
#             return redirect(Auth.build_auth_url())

# @app.route("/signin-oidc")
# def authorize():
#     session["state"] = request.args.get("state")
#     session["nonce"] = request.args.get("nonce")
#     code = request.args.get('code')
    
#     if not code:
#         return "No code returned from Azure AD.", 400
    
#     cache = Auth.load_cache()
#     result = Auth.build_msal_app(cache=cache).acquire_token_by_authorization_code(
#         code,
#         scopes=[],  # Update with your scopes
#         redirect_uri=url_for("authorize", _external=True))
#     Auth.save_cache(cache)

#     if "error" in result:
#         return f"Authentication error: {result['error']}.", 500

#     session["user"] = result.get("id_token_claims")
#     return "User authenticated"

@app.route('/')
def index():
    try:
        ai_instance.refresh_settings_and_templates()
        return render_template('index.html')
    except Exception as e:
        logging.error(f"Exception occurred while rendering index template: {e}")
        return "An error occurred while loading the page."
    
@app.route('/settings')
def evasettings():
    try:
        return render_template('settings.html')
    except Exception as e:
        logging.error(f"Exception occurred while rendering settings template: {e}")
        return "An error occurred while loading the page."


@app.route('/save-template', methods=['POST'])
def save_template_route():
    data = request.get_json()
    file_name = data.get('fileName')
    content = data.get('content')

    message, status_code = file_instance.save_template(file_name, content)
    return jsonify({'message': message}), status_code

@app.route('/save-settings', methods=['POST'])
def save_settings_route():
    data = request.get_json()
    max_token = data.get('maxToken')
    temperature = data.get('temperature')

    message, status_code = file_instance.save_settings(max_token, temperature)
    return jsonify({'message': message}), status_code

@app.route('/about')
def about():
    try:
        return render_template('about.html')
    except Exception as e:
        logging.error(f"Exception occurred while rendering about template: {e}")
        return "An error occurred while loading the page."


@app.route('/health')
def health():
    return 'healthy'

@app.route('/health/kubernetes')
def healthkubernetes():
    return 'healthy'



@app.route('/getrelationsreport', methods=['GET'])
def getrelationsreport():
    '''Returns report embed configuration'''

    try:
        embed_info = PbiEmbedService().get_embed_params_for_single_report(settings.PBI_WORKSPACE_ID , settings.PBI_REPORT_ID_KG)
        return embed_info
    except Exception as ex:
        return json.dumps({'errorMsg': str(ex)}), 500




@app.route('/get_model_response', methods=['POST'])
def handle_get_model_response():
    response = {}
    text = request.form['text']
    type = request.form['type']

    try:
        answer_generator = ai_instance.process_query(type, text)
        resp_text = ""
        for chunk in answer_generator:
            resp_text += chunk

        response['type'] = type
        response['text'] = resp_text
        response['status'] = 'full response complete'    
    except Exception as e:
        print(f"Error during {type} Type Response: {str(e)}")
        response['type'] = resp_text
        response['text'] = str(e)
        response['status'] = 'error'
    
    return response


@app.route('/get_model_response_sse', methods=['GET'])
def handle_get_model_response_sse():
    type = request.args.get('type')
    text = request.args.get('text')    
    # Get the event stream for this type of query
    if type=='answer':
        event_stream_generator = ai_instance.custom_callback_handler_answer.event_stream()
    elif type=='reference':
        event_stream_generator = ai_instance.custom_callback_handler_reference.event_stream()
    elif type=='gptnormal':
        event_stream_generator = ai_instance.custom_callback_handler_normal.event_stream()            

    # Process the query to start generating responses
    # ai_instance.process_query(type, text)
    threading.Thread(target=ai_instance.process_query, args=(type, text)).start()

    return Response(event_stream_generator, content_type='text/event-stream')


if settings.USE_WEB_SOCKET=='true':
    @socketio.on('get_normal_request')
    def handle_get_normal_request(data):
        text = data['text']
        process_request_ws('gptnormal', text)

    @socketio.on('get_answer_request')
    def handle_get_answer_request(data):
        text = data['text']
        process_request_ws('answer', text)

    @socketio.on('get_reference_request')
    def handle_get_reference_request(data):
        text = data['text']
        process_request_ws('reference', text)
    
    def process_request_ws(type, text):
        try:        
            ai_instance.process_query(type, text)
           
            print(f"{type} Type Response Exited, sending completion status")
            socketio.emit(f'{type}_response', {'status': 'full response complete', 'type': type, 'text': 'already sent'})  
        except Exception as e:
            print(f"Error during {type} Type Response: {str(e)}")
            socketio.emit(f'{type}_response', {'status': 'error', 'type': type, 'text': str(e)})

if __name__ == '__main__':
    # app.debug = True
    # app.run()
    app.run(host='localhost', port=5000)
    # socketio.run(app, debug=True)