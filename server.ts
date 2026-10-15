import express, { Request, Response } from 'express';
import { createServer as createViteServer } from 'vite';
import dotenv from 'dotenv';
import { Readable, Transform } from 'node:stream';

dotenv.config();

const app = express();
const PORT = 3000;
const MAX_PROXY_UPLOAD_BYTES = 26 * 1024 * 1024;

app.use(express.json({ limit: '50mb' }));

app.use('/api', async (req: Request, res: Response) => {
  const backendUrl = process.env.PYTHON_API_URL || 'http://127.0.0.1:8000';
  const contentType = req.headers['content-type'];
  const headers: Record<string, string> = {};
  if (contentType) headers['content-type'] = contentType;
  if (req.headers['content-length']) headers['content-length'] = req.headers['content-length'];
  if (req.headers.authorization) headers.authorization = req.headers.authorization;
  const twilioSignature = req.header('x-twilio-signature');
  if (twilioSignature) headers['x-twilio-signature'] = twilioSignature;

  let body: BodyInit | undefined;
  let duplex: 'half' | undefined;
  let uploadLimitExceeded = false;
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    if (req.is('application/json')) {
      body = JSON.stringify(req.body ?? {});
    } else if (req.is('multipart/form-data') || req.is('application/x-www-form-urlencoded')) {
      const contentLength = Number(req.headers['content-length'] || 0);
      if (contentLength > MAX_PROXY_UPLOAD_BYTES) {
        res.status(413).json({ detail: 'Request body exceeds the 26 MiB proxy limit.' });
        return;
      }
      let receivedBytes = 0;
      const boundedBody = new Transform({
        transform(chunk: Buffer, _encoding, callback) {
          receivedBytes += chunk.length;
          if (receivedBytes > MAX_PROXY_UPLOAD_BYTES) {
            uploadLimitExceeded = true;
            req.unpipe(boundedBody);
            req.resume();
            callback(new Error('UPLOAD_LIMIT_EXCEEDED'));
            return;
          }
          callback(null, chunk);
        }
      });
      req.pipe(boundedBody);
      body = Readable.toWeb(boundedBody) as ReadableStream<Uint8Array>;
      duplex = 'half';
    }
  }

  try {
    const upstream = await fetch(new URL(req.originalUrl, backendUrl), {
      method: req.method,
      headers,
      body,
      ...(duplex ? { duplex } : {}),
    } as RequestInit & { duplex?: 'half' });
    const upstreamType = upstream.headers.get('content-type');
    if (upstreamType) res.setHeader('content-type', upstreamType);
    res.status(upstream.status).send(Buffer.from(await upstream.arrayBuffer()));
  } catch {
    if (uploadLimitExceeded && !res.headersSent) {
      res.status(413).json({ detail: 'Request body exceeds the 26 MiB proxy limit.' });
      return;
    }
    res.status(503).json({ detail: 'Python API unavailable. Start the FastAPI service on port 8000.' });
  }
});

async function startServer() {
  const vite = await createViteServer({
    server: { middlewareMode: true },
    appType: 'spa',
  });
  app.use(vite.middlewares);

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`StockUp Pulse Full-Stack Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
