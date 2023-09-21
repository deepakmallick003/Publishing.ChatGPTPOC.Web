# Insight Reporting Machine learing Service

## Project Overview
The purpose of the Cabi.Publishing.ChatGPTPOC.Web project is try train ChatGPT with Publisinh data (JATS and Thesaurus) and allow users ask questions and get helpful answers

## Contact Details
* **Technical Contact:** Deepak Mallick
* **Business Owner:** James Munro, Gary Leicester
* **Project Manager:** Timothy Khouri

## Key Details

### Production URLs
* **Base URL:** https://cdn.cabi.org/publishingchatgpt/

### Development Team(s) or Suppliers
* CABI

### Technology
* **Version:** Python 3.11
* **Logging:** Seq
* **Authentication:** Azure AD

## Dependencies
* Flask==1.1.2
* Flask_Cors==3.0.10
* gTTS==2.3.2
* langchain==0.0.192
* openai==0.27.6
* python-dotenv==1.0.0
* Requests==2.31.0
* Werkzeug==2.0.3
* xmltodict==0.12.0
* gunicorn==20.1.0
* Jinja2==2.11.3
* MarkupSafe==1.1.1
* itsdangerous==1.1.0
* chromadb<0.4.0
* tiktoken==0.4.0
* seqlog>=0.3.27
* pandas<=2.0.0


### Notes
* Create virtual enviornment 
**python -m venv .venv**
* Activate the virtual environment
**.venv\Scripts\activate**
* Change the project directory to `publishingchatgptpocweb`
**cd publishingchatgptpocweb**
* Install the project dependencies
**pip install -r requirements.txt**
* Set the Flask application environment variables
**set FLASK_APP=route.py**
**set FLASK_ENV=development**
*Note: On Linux/Mac, replace `set` with `export`.
*Run the application using Gunicorn
**gunicorn -w 4 -b 127.0.0.1:5000 route:app**
* Your Flask application should now be running at [http://127.0.0.1:5000/]
* Run test
**pytest**

#### Development Notes
* For development purposes, run the Flask application using the Flask development server instead of Gunicorn
