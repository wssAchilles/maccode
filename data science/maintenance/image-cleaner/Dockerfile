FROM gcr.io/google.com/cloudsdktool/google-cloud-cli:slim

WORKDIR /app

COPY cleanup_container_images.py /app/cleanup_container_images.py

ENTRYPOINT ["python3", "/app/cleanup_container_images.py"]
