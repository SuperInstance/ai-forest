import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import { readForestMap, getLayer, ForestMap, LayerInfo } from './forest';

// ─── Constants ────────────────────────────────────────────────────────────

const PORT = 4075;
const PLATO_BASE = 'http://localhost:8847';
const PLATO_ROOM = 'canopy-directives';

// ─── App setup ────────────────────────────────────────────────────────────

const app = express();
app.use(cors());
app.use(express.json({ limit: '1mb' }));

// ─── Request logging middleware ───────────────────────────────────────────

app.use((req: Request, _res: Response, next: NextFunction) => {
  const ts = new Date().toISOString();
  const method = req.method;
  const url = req.url;
  const body = req.method !== 'GET' && req.body ? ` body=${JSON.stringify(req.body).slice(0, 200)}` : '';
  console.log(`[${ts}] ${method} ${url}${body}`);
  next();
});

// ─── State ────────────────────────────────────────────────────────────────

interface TileCounts {
  [layerName: string]: number;
}

// Track which layers are connected (heartbeat from other processes would update this)
const connectedLayers: Set<string> = new Set([
  'canopy',
  'understory',
  'floor',
  'mycelium',
  'seed-bank',
]);
const tileCounts: TileCounts = {
  canopy: 12,
  understory: 47,
  floor: 203,
  mycelium: 89,
  'seed-bank': 156,
};

// ─── PLATO Tiling helper ──────────────────────────────────────────────────

async function tileToPlato(directive: any): Promise<{ ok: boolean; error?: string; tileId?: string }> {
  try {
    const response = await fetch(`${PLATO_BASE}/room/${PLATO_ROOM}/tile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: typeof directive === 'string' ? directive : JSON.stringify(directive, null, 2),
        source: 'canopy-api',
        timestamp: new Date().toISOString(),
      }),
    });

    if (!response.ok) {
      const text = await response.text();
      return { ok: false, error: `PLATO returned ${response.status}: ${text}` };
    }

    const result = await response.json() as Record<string, any>;
    return { ok: true, tileId: result.id || result.tileId || 'unknown' };
  } catch (err: any) {
    return { ok: false, error: `PLATO connection failed: ${err.message}` };
  }
}

// ─── Routes ───────────────────────────────────────────────────────────────

// GET / — Status overview
app.get('/', async (_req: Request, res: Response) => {
  console.log('[canopy] GET / — returning status dashboard');
  res.json({
    service: 'Canopy API',
    version: '1.0.0',
    forest: 'AI Forest',
    status: 'running',
    layers: Array.from(connectedLayers).map((name) => ({
      name,
      connected: true,
      tiles: tileCounts[name] || 0,
    })),
    timestamp: new Date().toISOString(),
  });
});

// GET /status — Detailed status
app.get('/status', async (_req: Request, res: Response) => {
  const forest: ForestMap = await readForestMap();

  const layersStatus = forest.layers.map((layer: LayerInfo) => ({
    name: layer.name,
    description: layer.description,
    agents: layer.agents,
    connected: connectedLayers.has(layer.name),
    tiles: tileCounts[layer.name] || 0,
  }));

  res.json({
    service: 'Canopy API',
    status: 'running',
    uptime: process.uptime(),
    activeConnections: connectedLayers.size,
    totalTiles: Object.values(tileCounts).reduce((a, b) => a + b, 0),
    layers: layersStatus,
    timestamp: new Date().toISOString(),
  });
});

// POST /directive — Submit a canopy directive
app.post('/directive', async (req: Request, res: Response) => {
  console.log('[canopy] POST /directive — submitting canopy directive');
  const directive = req.body;

  if (!directive || Object.keys(directive).length === 0) {
    return res.status(400).json({ error: 'Directive body is required' });
  }

  // Ensure directive has metadata
  const enrichedDirective = {
    ...directive,
    _meta: {
      ...(directive._meta || {}),
      submittedAt: new Date().toISOString(),
      source: 'canopy-api',
    },
  };

  // Tile to PLATO
  const result = await tileToPlato(enrichedDirective);

  if (!result.ok) {
    console.error('[canopy] Failed to tile directive:', result.error);
    return res.status(502).json({
      error: 'Failed to persist directive to PLATO',
      detail: result.error,
      directive: enrichedDirective,
    });
  }

  console.log('[canopy] Directive tiled to PLATO:', result.tileId);
  res.status(201).json({
    status: 'accepted',
    message: 'Directive submitted and tiled to PLATO',
    tileId: result.tileId,
    directive: enrichedDirective,
    timestamp: new Date().toISOString(),
  });
});

// GET /forest — Full forest map
app.get('/forest', async (_req: Request, res: Response) => {
  console.log('[canopy] GET /forest — reading forest map');
  try {
    const forest: ForestMap = await readForestMap();
    res.json({
      forest,
      timestamp: new Date().toISOString(),
    });
  } catch (err: any) {
    res.status(500).json({ error: 'Failed to read forest map', detail: err.message });
  }
});

// GET /layer/:name — Get specific layer info
app.get('/layer/:name', async (req: Request, res: Response) => {
  const { name } = req.params;
  console.log(`[canopy] GET /layer/${name} — fetching layer info`);
  try {
    const forest: ForestMap = await readForestMap();
    const layer = getLayer(forest, name);
    if (!layer) {
      return res.status(404).json({
        error: 'Layer not found',
        validLayers: ['canopy', 'understory', 'floor', 'mycelium', 'seed-bank'],
      });
    }
    res.json({
      layer,
      connected: connectedLayers.has(layer.name),
      tiles: tileCounts[layer.name] || 0,
      timestamp: new Date().toISOString(),
    });
  } catch (err: any) {
    res.status(500).json({ error: 'Failed to read layer info', detail: err.message });
  }
});

// ─── 404 handler ──────────────────────────────────────────────────────────

app.use((_req: Request, res: Response) => {
  res.status(404).json({
    error: 'Not found',
    endpoints: ['GET /', 'GET /status', 'POST /directive', 'GET /forest', 'GET /layer/:name'],
  });
});

// ─── Start server ─────────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`\n  🌳 Canopy API Server`);
  console.log(`  ────────────────────`);
  console.log(`  Port    : ${PORT}`);
  console.log(`  PLATO   : ${PLATO_BASE}/room/${PLATO_ROOM}`);
  console.log(`  Forest  : /tmp/ai-forest/FOREST-MAP.md`);
  console.log(`  Status  : http://localhost:${PORT}/\n`);
});
