# define what image we're starting from.
FROM python:3.9-slim

# Set pip config
ENV PIP_NO_CACHE_DIR=false

# Create the working directory
WORKDIR /bot

# Install project dependencies
# - first build tools, because pillow-simd isn't pre-compiled
RUN apt-get -qq update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
python3-dev python3-setuptools libtiff5-dev libjpeg-dev libopenjp2-7-dev \
zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev \
python3-tk libharfbuzz-dev libfribidi-dev libxcb1-dev
RUN pip install -U pillow-simd
# - then normal stuff
COPY requirements.txt ./
RUN pip install -U -r requirements.txt

# Copy the source code across last to optimize image rebuilds on code changes
# (skips all above steps if we need to redo)
COPY . .

# Define the command to run when the container starts
ENTRYPOINT ["python"]
CMD ["-m", "dreaf"]
