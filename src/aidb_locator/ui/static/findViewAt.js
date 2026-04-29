// Hit-test for the layout tree.
// Bounds are half-open: x in [left, right), y in [top, bottom).
//
// We don't strictly follow z-order, because Android UIs often have transparent
// overlay containers (e.g., a full-screen FrameLayout for a modal scrim) drawn
// on top of the actual content. If we just returned the top-most node, we'd
// constantly land on those overlays. Instead:
//
//   1. Collect every node whose bounds contain the point, across all branches.
//   2. Pick the deepest one (descendants beat ancestors).
//   3. Among the deepest tie, prefer the one with the most "informational
//      content" (id > text > clickable > bg color), then z-order (later
//      sibling wins).

export function findViewAt(node, x, y) {
  if (!node) return null;
  const candidates = [];
  _collect(node, x, y, candidates, 0);
  if (candidates.length === 0) return null;
  candidates.sort((a, b) => {
    if (b.depth !== a.depth) return b.depth - a.depth;
    const s = _score(b.node) - _score(a.node);
    if (s !== 0) return s;
    return b.drawIndex - a.drawIndex;
  });
  return candidates[0].node;
}

function _contains(node, x, y) {
  const b = node.bounds;
  if (!b) return false;
  return x >= b.left && x < b.right && y >= b.top && y < b.bottom;
}

function _collect(node, x, y, out, depth) {
  // INVISIBLE / GONE nodes (and their subtrees) don't render and aren't hit-testable.
  if (node.visibility && node.visibility !== "V") return;
  if (!_contains(node, x, y)) return;
  out.push({ node, depth, drawIndex: out.length });
  for (const c of node.children || []) {
    _collect(c, x, y, out, depth + 1);
  }
}

function _score(n) {
  let s = 0;
  if (n.id_str) s += 8;
  if (n.text) s += 4;
  if (n.is_clickable) s += 2;
  if (n.background_color) s += 1;
  return s;
}
