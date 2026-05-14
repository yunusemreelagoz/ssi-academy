# OpenShift & Linux Uyumlu Üretim (Production) Dockerfile'ı
# Build komutu (repo kökünden çalıştırılmalı):
#   docker build -f openshift-nixar-api/Dockerfile -t nixar-api:latest .
FROM --platform=linux/amd64 ubuntu:22.04

USER root

# 1. Sistem bağımlılıklarını kur (python3-venv gerekmez, global pip kullanıyoruz)
RUN apt-get update && \
    apt-get -y install --no-install-recommends python3-pip tzdata curl && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Nixar Linux paylaşımlı kütüphanelerini sisteme kopyala (x86_64)
# Build context: repo kökü — yollar oraya göre yazılmıştır
COPY openshift-nixar-api/nixar_api_linux/x86_64-unknown-linux-gnu/libnixar_core.so /usr/local/lib/
COPY openshift-nixar-api/nixar_api_linux/x86_64-unknown-linux-gnu/libzmq.so.5 /usr/local/lib/
COPY openshift-nixar-api/nixar_api_linux/x86_64-unknown-linux-gnu/libsodium.so.23 /usr/local/lib/

# Linux'a "bu kütüphaneleri önbelleğe al" emrini ver
RUN ldconfig
ENV LD_LIBRARY_PATH=/usr/local/lib

# 3. Çalışma dizinini OpenShift standartlarına uygun oluştur
#    OpenShift: UID rastgele atanır, GID=0 (root grubu) olur → g+rwX zorunlu
WORKDIR /app
RUN chown -R 1001:0 /app && chmod -R u+rwX,g+rwX /app

# 4. Python kaynak kodlarını kopyala (nixar_api_python klasöründen)
COPY nixar-backend/nixar_api_python/nixar/ /app/nixar/
COPY nixar-backend/nixar_api_python/main.py /app/
COPY nixar-backend/nixar_api_python/test_utils.py /app/
COPY nixar-backend/nixar_api_python/genesis.txn /app/
COPY nixar-backend/nixar_api_python/genesises/ /app/genesises/

# 5. Python bağımlılıklarını kur
COPY openshift-nixar-api/requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# 6. Agent kayıt defteri ve cüzdan dosyaları için kalıcı dizin
#    OpenShift'te UID 1001 (veya rastgele) yazabilmeli — g+rwX şart
RUN mkdir -p /app/.tmp && chown -R 1001:0 /app/.tmp && chmod -R u+rwX,g+rwX /app/.tmp

# 7. Python modül yolu
ENV PYTHONPATH=/app

# Von-Network kullanımı (0=kapalı, 1=açık). Von-Network'e bağlanmak için 1 yapın.
ENV USE_VON_NETWORK=0

# 8. OpenShift SCC Kuralı: Root ile çalıştırma!
USER 1001

# 9. Sağlık kontrolü — 8080 portunu dışa aç
EXPOSE 8080

# 10. FastAPI'yi Uvicorn ile başlat
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
