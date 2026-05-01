# Build:  docker build -t model-home/hurricane_frequency:latest .
# Run:    echo '{"location":{"latitude":25.76,"longitude":-80.19}}' | docker run --rm -i model-home/hurricane_frequency:latest
# With input file mounted:
#   docker run --rm -v "$PWD/run:/run" model-home/hurricane_frequency:latest /run/hurricane_frequency_query.json

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY runner.py ./
COPY data ./data

ENTRYPOINT ["python", "runner.py"]
# Default to bundled example input for local smoke testing.
CMD ["data/input_data.json"]
