# OpenShift & Linux Uyumlu Üretim (Production) Dockerfile'ı
FROM --platform=linux/amd64 ubuntu:22.04

# 1. Root olarak genel güncellemeleri ve Python'ı kur
USER root
RUN apt-get update && \
    apt-get -y install python3-pip python3-venv tzdata curl && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Çalışma alanını OpenShift standartlarına (%100 u+rwX izinli) uygun oluştur
WORKDIR /app
RUN chown -R 1001:0 /app && chmod -R u+rwX,g+rwX /app

# 3. Nixar'ın YALNIZCA Linux dağıtımlarını içe kopyala ve kütüphane yolunu belirle
COPY nixar_api_linux/x86_64-unknown-linux-gnu/libnixar_core.so /usr/local/lib/
COPY nixar_api_linux/x86_64-unknown-linux-gnu/libzmq.so.5 /usr/local/lib/
COPY nixar_api_linux/x86_64-unknown-linux-gnu/libsodium.so.23 /usr/local/lib/

# Linux'a "bu kütüphaneleri hafızana al" emrini ver
RUN ldconfig
ENV LD_LIBRARY_PATH=/usr/local/lib

# 4. Kendi yazdığımız özel Python/FastAPI dosyalarını kopyala
COPY src/ /app/

# 5. Gereksinimleri (pip) tamamen Global (Root) olarak kur
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn

# Nixar ve OpenShift gereği Python kütüphane yolunu ayarla
ENV PYTHONPATH=/app

# 6. OpenShift Security Context Constraints (SCC) Kuralı: Root ile çalıştırma!
# OpenShift 1001 (veya rastgele) bir UID atar ama grup 0'dır (root grubu).
# Containerin güvenliğini sağlayarak dış dünyaya bağlanıyoruz:
USER 1001

# Container sağlığını kontrol edebileceğimiz 8080 portunu dışa açıyoruz
EXPOSE 8080

# Sistemi FastAPI motoru olan Uvicorn ile başlatıyoruz
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
