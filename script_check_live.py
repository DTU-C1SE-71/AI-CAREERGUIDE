import urllib.request, json

# 1. Check status
with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/rag-governance/llm-status') as resp:
    status_data = json.loads(resp.read().decode('utf-8'))
    print('LLM Status:', status_data)

# 2. Test live connection probe
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/rag-governance/test-llm-connection',
    data=json.dumps({}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    print('Probe HTTP:', resp.status)
    print('Probe Success:', res.get('success'))
    print('Probe Latency ms:', res.get('latency_ms'))
    print('Probe Model:', res.get('model_used'))
    print('Probe Preview:', res.get('preview_reply'))
    print('Probe Message:', res.get('message'))
