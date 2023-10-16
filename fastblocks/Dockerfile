FROM python:3.12

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install production dependencies.
RUN pip install --upgrade pipx
RUN pipx install pdm
RUN pdm install

uvicorn --port $PORT --host 0.0.0.0 main:app
