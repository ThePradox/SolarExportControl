FROM python:3.11.0-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APPARGS=""

# Install pip requirements
COPY requirements.txt .
RUN python -m pip --no-cache-dir install -r requirements.txt

WORKDIR /app
COPY src .
COPY src/config ./_origin_config 
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser
VOLUME ["/app/config"]

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
ENTRYPOINT ["/entrypoint.sh"]
CMD python main.py ./config/config.json $APPARGS
