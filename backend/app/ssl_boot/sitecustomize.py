"""Force system trust store (Windows corporate SSL / MITM proxies).

Loaded via PYTHONPATH before pdf2zh/huggingface_hub/httpx start.
"""
try:
    import truststore

    # truststore 0.10+ uses inject_into_ssl; older used inject
    if hasattr(truststore, "inject_into_ssl"):
        truststore.inject_into_ssl()
    elif hasattr(truststore, "inject"):
        truststore.inject()
except Exception:
    try:
        import os

        import certifi

        ca = certifi.where()
        os.environ.setdefault("SSL_CERT_FILE", ca)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", ca)
        os.environ.setdefault("CURL_CA_BUNDLE", ca)
    except Exception:
        pass
