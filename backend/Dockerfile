FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Sangli's dedicated WAQI station A568009 can temporarily report no current AQI.
# In that case, try the verified nearby Kolhapur WAQI stations instead of returning 500.
RUN sed -i 's/"sangli":\["A568009"\]/"sangli":["A568009","A567994","A567991"]/g' aqi_data.py

EXPOSE 8000
CMD ["uvicorn", "waqi_server:app", "--host", "0.0.0.0", "--port", "8000"]
