FROM python:3.11-slim
WORKDIR /app
# CPU-only torch keeps the image small; required for MaskablePPO bundles
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY policy_service/requirements.txt policy_service/requirements.txt
RUN pip install --no-cache-dir -r policy_service/requirements.txt
COPY mlops/__init__.py mlops/__init__.py
COPY mlops/common mlops/common
COPY mlops/configs mlops/configs
COPY mlops/rl mlops/rl
COPY policy_service policy_service
ENV POLICY_MODEL_MANIFEST=/artifacts/rl/latest.json
EXPOSE 8010
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8010/health')"
CMD ["uvicorn", "policy_service.app:app", "--host", "0.0.0.0", "--port", "8010"]
