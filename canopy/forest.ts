import * as fs from 'fs';
import * as path from 'path';

// ─── Types ────────────────────────────────────────────────────────────────

export interface AgentInfo {
  name: string;
  role: string;
  status: string;
}

export interface LayerInfo {
  name: string;
  description: string;
  agents: AgentInfo[];
  connections: string[];
}

export interface ForestMap {
  meta: {
    name: string;
    version: string;
    updated: string;
  };
  layers: LayerInfo[];
  connections: string[];
}

// ─── Forest Map file path ────────────────────────────────────────────────

const FOREST_MAP_PATH = '/tmp/ai-forest/FOREST-MAP.md';

// ─── Default forest map (fallback) ───────────────────────────────────────

const DEFAULT_FOREST: ForestMap = {
  meta: {
    name: 'AI Forest',
    version: '1.0.0',
    updated: new Date().toISOString(),
  },
  layers: [
    {
      name: 'canopy',
      description: 'Strategic coordination layer — observes and directs',
      agents: [{ name: 'oracle1', role: 'coordinator', status: 'active' }],
      connections: ['understory'],
    },
    {
      name: 'understory',
      description: 'Growth layer — implements directives and runs experiments',
      agents: [{ name: 'worker-1', role: 'implementer', status: 'active' }],
      connections: ['canopy', 'floor'],
    },
    {
      name: 'floor',
      description: 'Decomposition layer — processes raw data and logs',
      agents: [{ name: 'scavenger-1', role: 'processor', status: 'idle' }],
      connections: ['understory', 'mycelium'],
    },
    {
      name: 'mycelium',
      description: 'Network layer — inter-agent messaging and coordination',
      agents: [{ name: 'mycelium-relay', role: 'router', status: 'active' }],
      connections: ['floor', 'seed-bank'],
    },
    {
      name: 'seed-bank',
      description: 'Knowledge layer — persistent memory and learnings',
      agents: [{ name: 'archivist-1', role: 'librarian', status: 'active' }],
      connections: ['mycelium'],
    },
  ],
  connections: [
    'canopy → understory',
    'understory → floor',
    'floor → mycelium',
    'mycelium → seed-bank',
  ],
};

// ─── Forest Map parser ────────────────────────────────────────────────────

interface Chunk {
  heading: string;
  headingLevel: number;
  bodyLines: string[];
}

function splitIntoChunks(markdown: string): Chunk[] {
  const lines = markdown.split('\n');
  const chunks: Chunk[] = [];
  let current: Chunk | null = null;

  for (const line of lines) {
    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      if (current) chunks.push(current);
      current = {
        heading: headingMatch[2].trim(),
        headingLevel: headingMatch[1].length,
        bodyLines: [],
      };
    } else {
      if (current) current.bodyLines.push(line);
    }
  }
  if (current) chunks.push(current);

  return chunks;
}

function parseMetaChunk(chunk: Chunk): Partial<ForestMap['meta']> {
  const meta: Partial<ForestMap['meta']> = {};
  const fullText = chunk.bodyLines.join('\n');

  const nameMatch = fullText.match(/\*\*Name\*\*:\s*(.+)/i);
  const versionMatch = fullText.match(/\*\*Version\*\*:\s*(.+)/i);
  const updatedMatch = fullText.match(/\*\*Updated\*\*:\s*(.+)/i);
  if (nameMatch) meta.name = nameMatch[1].trim();
  if (versionMatch) meta.version = versionMatch[1].trim();
  if (updatedMatch) meta.updated = updatedMatch[1].trim();

  return meta;
}

function parseLayerChunk(chunk: Chunk): LayerInfo {
  const name = chunk.heading.toLowerCase().replace(/\s+/g, '-');
  const description = chunk.bodyLines
    .filter((l) => l.trim().startsWith('-') || l.trim().startsWith('*'))
    .map((l) => l.replace(/^[-*\s]+/, '').trim())
    .join('; ');
  const agents: AgentInfo[] = [];
  const connections: string[] = [];

  for (const line of chunk.bodyLines) {
    const agentMatch = line.match(/\*\*(.+?)\*\*.*?\((active|idle|busy|offline)\)/i);
    if (agentMatch) {
      agents.push({ name: agentMatch[1].trim(), role: 'member', status: agentMatch[2].toLowerCase() });
    }
    const connMatch = line.match(/connected\s+(?:to\s+)?(.+)/i);
    if (connMatch) {
      connMatch[1].split(/[,;]/).forEach((c) => connections.push(c.trim()));
    }
  }

  return {
    name,
    description: description || chunk.bodyLines.filter((l) => l.trim()).join(' '),
    agents: agents.length > 0 ? agents : [{ name: 'unknown', role: 'member', status: 'unknown' }],
    connections,
  };
}

function parseConnectionsSection(bodyLines: string[]): string[] {
  const conns: string[] = [];
  for (const line of bodyLines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
      const clean = trimmed.replace(/^[-*\s]+/, '').trim();
      if (clean.includes('→') || clean.includes('->') || clean.includes('--')) {
        conns.push(clean);
      }
    }
  }
  return conns;
}

// ─── Read forest map from file ──────────────────────────────────────────

export async function readForestMap(): Promise<ForestMap> {
  try {
    // Check multiple possible paths
    const possiblePaths = [
      FOREST_MAP_PATH,
      path.join(process.cwd(), '..', 'FOREST-MAP.md'),
      path.join(process.cwd(), 'FOREST-MAP.md'),
    ];

    let content: string | null = null;
    for (const p of possiblePaths) {
      if (fs.existsSync(p)) {
        content = fs.readFileSync(p, 'utf-8');
        break;
      }
    }

    if (!content) {
      console.warn('[forest] FOREST-MAP.md not found, using default map');
      return DEFAULT_FOREST;
    }

    const chunks = splitIntoChunks(content);
    const forest: ForestMap = {
      meta: { name: 'AI Forest', version: '1.0.0', updated: new Date().toISOString() },
      layers: [],
      connections: [],
    };

    for (const chunk of chunks) {
      const headingLower = chunk.heading.toLowerCase();

      if (headingLower.includes('meta') || headingLower.includes('forest map')) {
        const meta = parseMetaChunk(chunk);
        if (meta.name) forest.meta.name = meta.name;
        if (meta.version) forest.meta.version = meta.version;
        if (meta.updated) forest.meta.updated = meta.updated;
      } else if (
        headingLower.includes('canopy') ||
        headingLower.includes('understory') ||
        headingLower.includes('floor') ||
        headingLower.includes('mycelium') ||
        headingLower.includes('seed-bank')
      ) {
        forest.layers.push(parseLayerChunk(chunk));
      } else if (headingLower.includes('connection') || headingLower.includes('topology')) {
        forest.connections = parseConnectionsSection(chunk.bodyLines);
      }
    }

    // If layers array is empty, use default
    if (forest.layers.length === 0) {
      forest.layers = DEFAULT_FOREST.layers;
    }

    return forest;
  } catch (err) {
    console.error('[forest] Error reading forest map:', err);
    return DEFAULT_FOREST;
  }
}

// ─── Get a specific layer by name ────────────────────────────────────────

export function getLayer(forest: ForestMap, name: string): LayerInfo | null {
  const layerName = name.toLowerCase();
  return forest.layers.find((l) => l.name === layerName) || null;
}
