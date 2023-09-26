# 
FROM python:3.8.5

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 
WORKDIR /publishingchatgptpocweb

# COPY requirements.txt ./ 
# 
COPY publishingchatgptpocweb/requirements.txt ./


# 
RUN pip install --no-cache-dir --upgrade -r requirements.txt


# Install specific versions of gunicorn and eventlet
# RUN pip install gunicorn==20.1.0 eventlet==0.30.2

# COPY . .
# 
COPY publishingchatgptpocweb/. ./

# Expose the port the app runs in
EXPOSE 80

# Run the application
#CMD ["gunicorn", "-b", "0.0.0.0:80", "route:app"]
#CMD ["gunicorn", "-k", "gevent", "-w", "1", "-b", "0.0.0.0:80", "route:app"]
#CMD ["gunicorn", "--worker-class", "gevent", "--worker-connections", "1000", "-w", "1", "-b", "0.0.0.0:80", "route:app"]
CMD ["gunicorn", "-k", "gevent", "-w", "1", "--timeout", "120", "-b", "0.0.0.0:80", "route:app"]