FROM python:3.10-bookworm

SHELL [ "/bin/bash", "-c" ]

ENV SHELL=/bin/bash
ENV POETRY_HOME=/etc/poetry
ENV PATH="$POETRY_HOME/venv/bin:$PATH"

RUN apt update && apt upgrade -y

RUN apt install -y g++ gcc cmake curl libssl-dev bash build-essential
RUN apt install -y libpng-dev libjpeg-dev libopenexr-dev libtiff-dev libwebp-dev
RUN apt install -y libsm6 libxext6 ffmpeg libfontconfig1 libxrender1 libgl1-mesa-glx

RUN apt install python3-pip pipx -y
RUN apt install -y python3-opencv

RUN apt autoremove -y
RUN apt autoclean -y

#INSTALL POETRY
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 -

WORKDIR /usr/src/ocr_service
COPY ocr_service ocr_service
COPY pyproject.toml .
COPY README.md .
RUN poetry env use $(which python3)
RUN poetry install

EXPOSE 8000
CMD ["poetry", "run", "python", "ocr_service/server.py"]