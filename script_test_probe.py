import urllib.request, json

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/rag-governance/test-llm-connection',
    data=json.dumps({}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    print('Endpoint HTTP Status:', resp.status)
    print('Success:', res.get('success'))
    print('Latency ms:', res.get('latency_ms'))
    print('Model:', res.get('model_used'))
    print('Base URL:', res.get('base_url'))
    print('Reply:', res.get('preview_reply'))
