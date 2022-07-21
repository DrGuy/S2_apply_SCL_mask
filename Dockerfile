# For more information, please refer to https://aka.ms/vscode-docker-python
FROM osgeo/gdal

ADD S2_apply_SCL_mask.py .
ADD S2_apply_SCL_mask_v2.py .
# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Update image
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# RUN apt-get update && apt-get install --auto-remove -y \
#     binutils \
#     gdal-bin \
#     libgdal-dev \
#     python3-gdal \
#     binutils \
#     libproj-dev \
#     ffmpeg \
#     python3-numpy


WORKDIR /app
COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD [ "python", "S2_apply_SCL_mask_v2.py" ]
