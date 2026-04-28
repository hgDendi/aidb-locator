// Pure hit-test for the layout tree.
// Bounds are half-open: x in [left, right), y in [top, bottom).
// Returns the deepest node containing the point. Among siblings at the same
// depth that all contain the point, returns the last one (z-order: later
// siblings are drawn on top).

export function findViewAt(node, x, y) {
  if (!node) return null;
  if (!_contains(node, x, y)) return null;
  return _walk(node, x, y);
}

function _contains(node, x, y) {
  const b = node.bounds;
  if (!b) return false;
  return x >= b.left && x < b.right && y >= b.top && y < b.bottom;
}

function _walk(node, x, y) {
  const children = node.children || [];
  // Walk in reverse so later (top-most) siblings win.
  for (let i = children.length - 1; i >= 0; i--) {
    const c = children[i];
    if (_contains(c, x, y)) {
      return _walk(c, x, y);
    }
  }
  return node;
}
