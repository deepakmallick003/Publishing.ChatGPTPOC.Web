# 
FROM python:3.8.5

# 
WORKDIR /app

#
#COPY requirements.txt ./ 
COPY publishingchatgptpocweb/requirements.txt ./

# 
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Install specific versions of gunicorn and eventlet
RUN pip install gunicorn==20.1.0 eventlet==0.30.2

# 
#COPY . .
COPY publishingchatgptpocweb/. ./

# Expose the port the app runs in
EXPOSE 80

# Run the application with gevent
#CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-w", "1", "-b", "0.0.0.0:80", "route:app"]
# Run the application with gunicorn and eventlet
CMD ["gunicorn", "-k", "eventlet", "-w", "1", "-b", "0.0.0.0:80", "route:app"]
