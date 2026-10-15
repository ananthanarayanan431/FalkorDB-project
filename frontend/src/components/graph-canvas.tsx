"use client";

import type ForceGraph from "force-graph";
import type { LinkObject, NodeObject } from "force-graph";
import { useEffect, useEffectEvent, useRef, useState } from "react";

import { caption, labelColor, primaryLabel } from "@/lib/graph-style";
import type { RawEdge, RawNode } from "@/lib/types";

export interface GraphSelection {
  kind: "node" | "edge";
  id: number;
}

interface VNode extends NodeObject {
  id: number;
  raw: RawNode;
  color: string;
  caption: string;
}

interface VLink extends LinkObject<VNode> {
  id: number;
  raw: RawEdge;
  curvature: number;
}

type Graph = ForceGraph<VNode, VLink>;

interface Props {
  nodes: RawNode[];
  edges: RawEdge[];
  /** A node is hidden when any of its labels is in this set. */
  hiddenLabels: ReadonlySet<string>;
  hiddenTypes: ReadonlySet<string>;
  /** Nodes matching the current search; drawn with a marker ring. */
  matches: ReadonlySet<number>;
  selection: GraphSelection | null;
  onSelect: (selection: GraphSelection | null) => void;
  /** Centre the view on a node. A new nonce re-centres on the same node. */
  focus: { id: number; nonce: number } | null;
  /** Bump to fit every visible node in view. */
  fitNonce: number;
  className?: string;
}

const RADIUS = 6;

interface Colors {
  fg: string;
  muted: string;
  line: string;
  accent: string;
  surface: string;
  warn: string;
}

function readColors(): Colors {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string) => css.getPropertyValue(name).trim();
  return { fg: v("--fg"), muted: v("--muted"), line: v("--line"), accent: v("--accent"), surface: v("--surface"), warn: v("--warn") };
}

const endId = (end: VLink["source"]): number => (typeof end === "object" ? (end as VNode).id : (end as number));

/** Spread parallel relationships between the same two nodes so each one stays visible. */
function withCurvature(edges: RawEdge[]): VLink[] {
  const groups = new Map<string, RawEdge[]>();
  for (const e of edges) {
    const key = e.source <= e.target ? `${e.source}-${e.target}` : `${e.target}-${e.source}`;
    groups.set(key, [...(groups.get(key) ?? []), e]);
  }
  const links: VLink[] = [];
  for (const group of groups.values()) {
    group.forEach((e, i) => {
      let curvature: number;
      if (e.source === e.target) curvature = 0.6 + i * 0.25;
      else if (group.length === 1) curvature = 0;
      else {
        curvature = (i - (group.length - 1) / 2) * 0.3;
        // Curvature is relative to the link's own direction; keep one shared reference.
        if (e.source > e.target) curvature = -curvature;
      }
      links.push({ id: e.id, raw: e, source: e.source, target: e.target, curvature });
    });
  }
  return links;
}

/** Where a straight or curved link passes its middle, for drawing its type there. */
function midpoint(link: VLink): { x: number; y: number; angle: number } | null {
  const s = link.source as VNode;
  const t = link.target as VNode;
  if (typeof s !== "object" || typeof t !== "object" || s.x === undefined || t.x === undefined) return null;
  const sx = s.x, sy = s.y ?? 0, tx = t.x, ty = t.y ?? 0;
  const dx = tx - sx, dy = ty - sy;
  let angle = Math.atan2(dy, dx);
  if (angle > Math.PI / 2 || angle < -Math.PI / 2) angle += Math.PI; // keep text upright
  if (!link.curvature) return { x: (sx + tx) / 2, y: (sy + ty) / 2, angle };
  const len = Math.hypot(dx, dy);
  const a = Math.atan2(dy, dx);
  const cx = (sx + tx) / 2 + len * link.curvature * Math.cos(a - Math.PI / 2);
  const cy = (sy + ty) / 2 + len * link.curvature * Math.sin(a - Math.PI / 2);
  // Point at t = 0.5 on the quadratic curve force-graph draws.
  return { x: 0.25 * sx + 0.5 * cx + 0.25 * tx, y: 0.25 * sy + 0.5 * cy + 0.25 * ty, angle };
}

export function GraphCanvas({ nodes, edges, hiddenLabels, hiddenTypes, matches, selection, onSelect, focus, fitNonce, className }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const [ready, setReady] = useState(false);
  const nodesById = useRef(new Map<number, VNode>());
  const fitOnStop = useRef(false);
  // Everything the draw callbacks read. Kept in a ref so the canvas never re-mounts.
  const view = useRef({
    hiddenLabels,
    hiddenTypes,
    matches,
    selection,
    hovered: null as number | null,
    near: new Set<number>(), // the selected node and its visible neighbours
    colors: null as Colors | null,
  });

  const select = useEffectEvent((s: GraphSelection | null) => onSelect(s));

  function nodeVisible(n: VNode): boolean {
    return !n.raw.labels.some((l) => view.current.hiddenLabels.has(l));
  }

  function linkVisible(l: VLink): boolean {
    const s = nodesById.current.get(endId(l.source));
    const t = nodesById.current.get(endId(l.target));
    return !view.current.hiddenTypes.has(l.raw.type) && !!s && !!t && nodeVisible(s) && nodeVisible(t);
  }

  function repaint() {
    // Setting a styling prop makes force-graph redraw even after the layout has settled.
    graphRef.current?.nodeVisibility((n) => nodeVisible(n)).linkVisibility((l) => linkVisible(l));
  }

  // Create the canvas once. force-graph touches `window`, so it is loaded in the browser only.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let disposed = false;
    let graph: Graph | null = null;
    let observer: ResizeObserver | null = null;
    const scheme = window.matchMedia("(prefers-color-scheme: dark)");
    const onScheme = () => {
      view.current.colors = readColors();
      repaint();
    };
    view.current.colors = readColors();
    scheme.addEventListener("change", onScheme);

    import("force-graph").then(({ default: ForceGraphClass }) => {
      if (disposed) return;
      graph = new ForceGraphClass<VNode, VLink>(el)
        .backgroundColor("rgba(0,0,0,0)")
        .nodeId("id")
        .nodeRelSize(RADIUS)
        .nodeVal(1)
        .nodeLabel(() => "") // no HTML tooltips: captions are drawn on the canvas instead
        .linkLabel(() => "")
        .nodeVisibility((n) => nodeVisible(n))
        .linkVisibility((l) => linkVisible(l))
        .nodeCanvasObjectMode(() => "replace")
        .nodeCanvasObject((node, ctx, scale) => drawNode(node, ctx, scale))
        .linkCurvature("curvature")
        .linkColor((l) => linkColor(l))
        .linkWidth((l) => (isSelectedLink(l) ? 2.5 : 1))
        .linkDirectionalArrowLength(5)
        .linkDirectionalArrowRelPos(1)
        .linkDirectionalArrowColor((l) => linkColor(l))
        .linkCanvasObjectMode(() => "after")
        .linkCanvasObject((link, ctx, scale) => drawLinkLabel(link, ctx, scale))
        .linkHoverPrecision(6)
        .warmupTicks(60)
        .cooldownTicks(150)
        .onEngineStop(() => {
          if (fitOnStop.current) {
            fitOnStop.current = false;
            graph?.zoomToFit(0, 48, (n) => nodeVisible(n));
          }
        })
        .onNodeClick((n) => select({ kind: "node", id: n.id }))
        .onLinkClick((l) => select({ kind: "edge", id: l.id }))
        .onBackgroundClick(() => select(null))
        .onNodeHover((n) => {
          view.current.hovered = n ? n.id : null;
          el.style.cursor = n ? "pointer" : "";
          repaint();
        })
        .onLinkHover((l) => {
          el.style.cursor = l ? "pointer" : "";
        });
      graph.d3Force("charge")?.strength?.(-120);
      graph.d3Force("link")?.distance?.(60);
      observer = new ResizeObserver(([entry]) => {
        graph?.width(entry.contentRect.width).height(entry.contentRect.height);
      });
      observer.observe(el);
      graphRef.current = graph;
      setReady(true);
    });

    return () => {
      disposed = true;
      scheme.removeEventListener("change", onScheme);
      observer?.disconnect();
      graph?._destructor();
      graphRef.current = null;
      nodesById.current = new Map();
    };
    // The draw helpers only read refs, so the canvas is created exactly once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function isSelectedLink(l: VLink): boolean {
    const sel = view.current.selection;
    return sel?.kind === "edge" && sel.id === l.id;
  }

  function linkColor(l: VLink): string {
    const { colors, selection: sel, near } = view.current;
    if (!colors) return "#999";
    if (isSelectedLink(l)) return colors.accent;
    if (sel?.kind === "node") {
      const touches = endId(l.source) === sel.id || endId(l.target) === sel.id;
      return touches ? colors.fg : withAlpha(colors.muted, near.size ? 0.15 : 0.6);
    }
    return withAlpha(colors.muted, 0.6);
  }

  function drawNode(n: VNode, ctx: CanvasRenderingContext2D, scale: number) {
    const { colors, selection: sel, near, hovered, matches: found } = view.current;
    if (!colors || n.x === undefined || n.y === undefined) return;
    const dimmed = sel?.kind === "node" && !near.has(n.id);
    const selected = sel?.kind === "node" && sel.id === n.id;
    ctx.globalAlpha = dimmed ? 0.2 : 1;

    ctx.beginPath();
    ctx.arc(n.x, n.y, RADIUS, 0, 2 * Math.PI);
    ctx.fillStyle = n.color;
    ctx.fill();
    ctx.lineWidth = 1.5 / scale;
    ctx.strokeStyle = colors.surface;
    ctx.stroke();

    if (found.has(n.id)) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, RADIUS + 3, 0, 2 * Math.PI);
      ctx.lineWidth = 2 / scale;
      ctx.strokeStyle = colors.warn;
      ctx.stroke();
    }
    if (selected) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, RADIUS + 2, 0, 2 * Math.PI);
      ctx.lineWidth = 2.5 / scale;
      ctx.strokeStyle = colors.fg;
      ctx.stroke();
    }

    // Captions appear once zoomed in, and always for the hovered, selected or found nodes.
    if (scale >= 1.3 || selected || hovered === n.id || found.has(n.id) || (sel?.kind === "node" && near.has(n.id))) {
      const size = Math.max(10 / scale, 2.5);
      ctx.font = `${size}px ui-sans-serif, system-ui, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.lineWidth = 3 / scale;
      ctx.strokeStyle = colors.surface;
      ctx.strokeText(n.caption, n.x, n.y + RADIUS + 2);
      ctx.fillStyle = colors.fg;
      ctx.fillText(n.caption, n.x, n.y + RADIUS + 2);
    }
    ctx.globalAlpha = 1;
  }

  function drawLinkLabel(l: VLink, ctx: CanvasRenderingContext2D, scale: number) {
    const { colors, selection: sel } = view.current;
    if (!colors) return;
    const touchesSelection =
      isSelectedLink(l) || (sel?.kind === "node" && (endId(l.source) === sel.id || endId(l.target) === sel.id));
    if (scale < 2 && !touchesSelection) return;
    const mid = midpoint(l);
    if (!mid) return;
    const size = Math.max(8 / scale, 2);
    ctx.save();
    ctx.translate(mid.x, mid.y);
    ctx.rotate(mid.angle);
    ctx.font = `${size}px ui-monospace, Menlo, monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const w = ctx.measureText(l.raw.type).width;
    ctx.fillStyle = colors.surface;
    ctx.fillRect(-w / 2 - 1.5 / scale, -size / 2 - 1 / scale, w + 3 / scale, size + 2 / scale);
    ctx.fillStyle = isSelectedLink(l) ? colors.accent : colors.muted;
    ctx.fillText(l.raw.type, 0, 0);
    ctx.restore();
  }

  // Load or merge data, keeping the position of nodes that were already on screen.
  useEffect(() => {
    const graph = graphRef.current;
    if (!ready || !graph) return;
    const prev = nodesById.current;
    const next = new Map<number, VNode>();
    const vnodes = nodes.map((raw) => {
      const v: VNode = prev.get(raw.id) ?? ({ id: raw.id } as VNode);
      v.raw = raw;
      v.color = labelColor(primaryLabel(raw.labels));
      v.caption = caption(raw);
      next.set(raw.id, v);
      return v;
    });
    const added = vnodes.some((v) => !prev.has(v.id));
    fitOnStop.current = prev.size === 0 || (added && vnodes.length - prev.size > prev.size);
    nodesById.current = next;
    graph.graphData({ nodes: vnodes, links: withCurvature(edges.filter((e) => next.has(e.source) && next.has(e.target))) });
  }, [ready, nodes, edges]);

  // Filters, search matches and selection only change how things are drawn.
  useEffect(() => {
    const v = view.current;
    v.hiddenLabels = hiddenLabels;
    v.hiddenTypes = hiddenTypes;
    v.matches = matches;
    v.selection = selection;
    v.near = new Set<number>();
    if (selection?.kind === "node") {
      v.near.add(selection.id);
      for (const e of edges) {
        if (hiddenTypes.has(e.type)) continue;
        if (e.source === selection.id) v.near.add(e.target);
        if (e.target === selection.id) v.near.add(e.source);
      }
    }
    repaint();
    // repaint only reads refs
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, hiddenLabels, hiddenTypes, matches, selection, edges]);

  useEffect(() => {
    const n = focus && nodesById.current.get(focus.id);
    const graph = graphRef.current;
    if (!ready || !graph || !n || n.x === undefined || n.y === undefined) return;
    graph.centerAt(n.x, n.y, 0);
    if (graph.zoom() < 2) graph.zoom(2.5, 0);
  }, [ready, focus]);

  useEffect(() => {
    if (ready && fitNonce > 0) graphRef.current?.zoomToFit(0, 48, (n) => nodeVisible(n));
    // nodeVisible only reads refs
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, fitNonce]);

  return <div ref={containerRef} className={className} />;
}

function withAlpha(color: string, alpha: number): string {
  const hex = color.replace("#", "");
  if (!/^[0-9a-f]{6}$/i.test(hex)) return color;
  const n = parseInt(hex, 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}
