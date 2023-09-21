# 
FROM python:3.11

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 
WORKDIR /app

#
#COPY requirements.txt ./ 
COPY publishingchatgptpoc.web/requirements.txt ./

# 
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 
#COPY . .
COPY publishingchatgptpoc.web/. ./

# Expose the port the app runs in
EXPOSE 5000

# Run the application
#CMD ["gunicorn", "-b", "0.0.0.0:5000", "route:app"]
CMD ["gunicorn", "-k", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "route:app"]

