import urllib.request, json

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/rag-governance/test-llm-connection',
    data=json.dumps({}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req, timeout=35) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print('HTTP Status:', resp.status)
        print('Success:', res.get('success'))
        print('Status Code:', res.get('status_code'))
        print('Model Used:', res.get('model_used'))
        print('Base URL:', res.get('base_url'))
        print('Latency ms:', res.get('latency_ms'))
        print('Preview Reply:', res.get('preview_reply'))
except Exception as e:
    print('Error:', e)
