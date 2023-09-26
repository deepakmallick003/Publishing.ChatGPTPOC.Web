import logging
import traceback
import json
from flask import Flask, render_template,jsonify, request, url_for, session, redirect
from flask import stream_with_context, Response
from flask_socketio import SocketIO
from core.config import PathConfig, settings
from core.pbiembedservice import PbiEmbedService
from scripts import ai


app = Flask(__name__, template_folder=PathConfig.TEMPLATE_DIRECTORY)
app.config['BASE_PATH'] = '' if settings.DEPLOYED_BASE_PATH == '/' else settings.DEPLOYED_BASE_PATH
# socketio = SocketIO(app, cors_allowed_origins="*")
# socketio = SocketIO(app, path=settings.DEPLOYED_BASE_PATH + '/socket.io', cors_allowed_origins="*")
socketio = SocketIO(app, path='/publishingchatgpt/socket.io', cors_allowed_origins='*')


PathConfig.init_app(app)
ai = ai.AI(settings, PathConfig, socketio)


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
        return render_template('index.html')
    except Exception as e:
        logging.error(f"Exception occurred while rendering index template: {e}")
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


@socketio.on('get_gptnormal')
def handle_get_gptnormal(data):
    text = data['text']
    ai.process_query(text, 'gptnormal')
    # answer_generator = ai.process_query(text, 'gptnormal')
    # for chunk in answer_generator:
    #     print(f"GPT Normal,Sending chunk: {chunk}") 
    #     socketio.emit('gptnormal_response', chunk)

    # Send a completion message
    print("GPT Normal Exited the loop, sending complete status")
    socketio.emit('gptnormal_response', {'status': 'complete'})

@socketio.on('get_answer')
def handle_get_answer(data):
    text = data['text']
    ai.process_query(text, 'answer')
    # answer_generator = ai.process_query(text, 'answer')
    # for chunk in answer_generator:
    #     print(f"Answer, Sending chunk: {chunk}")  # Log the chunk being sent
    #     socketio.emit('answer_response', chunk)

    # Send a completion message
    print("Answer Exited the loop, sending complete status")
    socketio.emit('answer_response', {'status': 'complete'})

@socketio.on('get_reference')
def handle_get_reference(data):
    text = data['text']
    ai.process_query(text, 'reference')
    # reference_generator = ai.process_query(text, 'reference')
    # for chunk in reference_generator:
    #     print(f"Reference, Sending chunk: {chunk}")  # Log the chunk being sent
    #     socketio.emit('reference_response', chunk)

    # Send a completion message
    print("Reference Exited the loop, sending complete status")
    socketio.emit('reference_response', {'status': 'complete'})
    
if __name__ == '__main__':
    # app.debug = True
    # app.run()
    # app.run(host='localhost', port=5000)
    socketio.run(app, debug=True)
