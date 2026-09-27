#!/usr/bin/env node

// ============================================================================
// Follow Builders — Prepare Digest
// ============================================================================
// Gathers everything the LLM needs to produce a digest:
// - Fetches the central feeds (tweets + podcasts + blogs)
// - Loads the remix prompts (user custom > local shipped > upstream GitHub)
// - Reads the user's config (language, delivery method)
// - Outputs a single JSON blob to stdout
//
// The LLM's ONLY job is to read this JSON, remix the content, and output
// the digest text. Everything else is handled here deterministically.
//
// PATH NOTE: this file is fully path-independent. It resolves the skill root
// from import.meta.url, so the skill folder can live anywhere. No hardcoded
// absolute paths — safe to copy/export to other machines.
//
// Usage: node prepare-digest.js
// Output: JSON to stdout
// ============================================================================

import { readFile, mkdir, writeFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join, dirname } from 'path';
import { homedir } from 'os';
import { fileURLToPath } from 'url';

// -- Resolve paths relative to this skill's own folder -----------------------

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SKILL_DIR = join(__dirname, '..');
const CACHE_DIR = join(SKILL_DIR, '.cache');
const FEEDS_CONFIG = join(SKILL_DIR, 'config', 'feeds.json');

const USER_DIR = join(homedir(), '.follow-builders');
const CONFIG_PATH = join(USER_DIR, 'config.json');
const USER_PROMPTS_DIR = join(USER_DIR, 'prompts');
const LOCAL_PROMPTS_DIR = join(SKILL_DIR, 'prompts');

const PROMPTS_BASE = 'https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/prompts';
const PROMPT_FILES = [
  'summarize-podcast.md',
  'summarize-tweets.md',
  'summarize-blogs.md',
  'digest-intro.md',
  'translate.md',
  'translate-original.md',
  'recommend.md'
];

// Fallback feed URLs (used if config/feeds.json is missing)
const FALLBACK_FEEDS = {
  x: 'https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-x.json',
  podcasts: 'https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-podcasts.json',
  blogs: 'https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-blogs.json'
};

// -- Fetch helpers (network-safe: never throw) -------------------------------

async function fetchJSON(url) {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(15000) });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function fetchText(url) {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(15000) });
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  }
}

async function readJSON(path) {
  try {
    return JSON.parse(await readFile(path, 'utf-8'));
  } catch {
    return null;
  }
}

// -- Feed loading with cache fallback ----------------------------------------
// 1. Try live fetch. On success, cache to .cache/ for offline reuse.
// 2. On failure, try the cached copy.
// Returns { data, status: 'live' | 'cached' | 'failed' }

async function loadFeed(name, url) {
  const data = await fetchJSON(url);
  if (data) {
    try {
      await mkdir(CACHE_DIR, { recursive: true });
      await writeFile(join(CACHE_DIR, `feed-${name}.json`), JSON.stringify(data), 'utf-8');
    } catch {
      // cache write is best-effort
    }
    return { data, status: 'live' };
  }
  const cached = await readJSON(join(CACHE_DIR, `feed-${name}.json`));
  if (cached) return { data: cached, status: 'cached' };
  return { data: null, status: 'failed' };
}

// -- Prompt loading ----------------------------------------------------------
// Priority: 1) user custom (~/.follow-builders/prompts)
//           2) local shipped (inside this skill — OUR modifications win)
//           3) upstream GitHub (only if neither local file exists)
  // Local-first protects our four-part "中文总结 / 中文全文翻译 / 推荐理由 / 原文链接"
  // structure from being silently overwritten by the upstream repo's prompts on export.

async function loadPrompts() {
  const prompts = {};
  for (const filename of PROMPT_FILES) {
    const key = filename.replace('.md', '').replace(/-/g, '_');
    let content = null;

    const userPath = join(USER_PROMPTS_DIR, filename);
    if (existsSync(userPath)) content = await readFile(userPath, 'utf-8');

    if (content === null && existsSync(join(LOCAL_PROMPTS_DIR, filename))) {
      content = await readFile(join(LOCAL_PROMPTS_DIR, filename), 'utf-8');
    }

    if (content === null) {
      const remote = await fetchText(`${PROMPTS_BASE}/${filename}`);
      if (remote) content = remote;
    }

    if (content !== null) prompts[key] = content;
  }
  return prompts;
}

// -- Main --------------------------------------------------------------------

async function main() {
  const errors = [];

  // 1. User config
  let config = {
    language: 'zh',
    frequency: 'daily',
    delivery: { method: 'stdout' }
  };
  const userCfg = await readJSON(CONFIG_PATH);
  if (userCfg) config = userCfg;

  // 2. Feed URLs (from config/feeds.json, with fallback)
  const feedsCfg = await readJSON(FEEDS_CONFIG);
  const feeds = (feedsCfg && feedsCfg.feeds) || FALLBACK_FEEDS;

  // 3. Fetch feeds (live -> cache -> failed), in parallel
  const [fx, fp, fb] = await Promise.all([
    loadFeed('x', feeds.x),
    loadFeed('podcasts', feeds.podcasts),
    loadFeed('blogs', feeds.blogs)
  ]);

  const statuses = [fx.status, fp.status, fb.status];
  let contentFetchStatus;
  if (statuses.every((s) => s === 'live')) contentFetchStatus = 'ok';
  else if (statuses.some((s) => s === 'live')) contentFetchStatus = 'partial';
  else if (statuses.every((s) => s === 'cached')) contentFetchStatus = 'cached';
  else contentFetchStatus = 'failed';

  const feedX = fx.data;
  const feedPodcasts = fp.data;
  const feedBlogs = fb.data;

  if (feedX?.errors?.length) {
    errors.push(...feedX.errors.map((e) => `Tweet feed problem: ${e}`));
  }
  if (feedPodcasts?.errors?.length) {
    errors.push(...feedPodcasts.errors.map((e) => `Podcast feed problem: ${e}`));
  }
  if (feedBlogs?.errors?.length) {
    errors.push(...feedBlogs.errors.map((e) => `Blog feed problem: ${e}`));
  }

  // 4. Prompts
  const prompts = await loadPrompts();

  // 5. Build output — everything the LLM needs in one blob.
  //    `feeds` and `contentFetchStatus` let the agent fall back to its own
  //    WebFetch when the script's Node runtime cannot reach GitHub.
  const output = {
    status: 'ok',
    contentFetchStatus,
    generatedAt: new Date().toISOString(),

    // Feed URLs — agent uses these ONLY as a WebFetch fallback
    feeds,

    // User preferences
    config: {
      language: config.language || 'zh',
      frequency: config.frequency || 'daily',
      delivery: config.delivery || { method: 'stdout' }
    },

    // Content to remix (empty arrays if fetch failed — agent falls back)
    podcasts: feedPodcasts?.podcasts || [],
    x: feedX?.x || [],
    blogs: feedBlogs?.blogs || [],

    // Stats
    stats: {
      podcastEpisodes: feedPodcasts?.podcasts?.length || 0,
      xBuilders: feedX?.x?.length || 0,
      totalTweets: (feedX?.x || []).reduce((sum, a) => sum + (a.tweets?.length || 0), 0),
      blogPosts: feedBlogs?.blogs?.length || 0,
      feedGeneratedAt:
        feedX?.generatedAt || feedPodcasts?.generatedAt || feedBlogs?.generatedAt || null
    },

    // Remix instructions
    prompts,

    // Non-fatal errors
    errors: errors.length > 0 ? errors : undefined
  };

  console.log(JSON.stringify(output, null, 2));
}

main().catch((err) => {
  console.error(JSON.stringify({ status: 'error', message: err.message }));
  process.exit(1);
});
