export default async function handler(req, res) {
  const backendBase = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
  const targetUrl = new URL(req.url, backendBase);

  try {
    const headers = {};
    for (const [key, value] of Object.entries(req.headers || {})) {
      if (key.toLowerCase() !== 'host' && typeof value === 'string') {
        headers[key] = value;
      }
    }

    const fetchOptions = {
      method: req.method,
      headers,
    };

    if (!['GET', 'HEAD'].includes(req.method) && req.body) {
      fetchOptions.body = typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
    }

    const response = await fetch(targetUrl.toString(), fetchOptions);
    const data = await response.text();

    res.status(response.status);
    response.headers.forEach((val, key) => {
      res.setHeader(key, val);
    });
    res.send(data);
  } catch (err) {
    res.status(502).json({
      error: 'Internal Backend service unavailable',
      details: err.message,
    });
  }
}
