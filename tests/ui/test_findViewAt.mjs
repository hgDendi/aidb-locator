import { test } from 'node:test';
import assert from 'node:assert/strict';
import { findViewAt } from '../../src/aidb_locator/ui/static/findViewAt.js';

const tree = {
  class_name: 'Root',
  bounds: { left: 0, top: 0, right: 100, bottom: 100 },
  children: [
    {
      class_name: 'A',
      bounds: { left: 0, top: 0, right: 50, bottom: 50 },
      children: [
        { class_name: 'A.leaf', bounds: { left: 10, top: 10, right: 20, bottom: 20 }, children: [] },
      ],
    },
    { class_name: 'B', bounds: { left: 50, top: 0, right: 100, bottom: 50 }, children: [] },
    // Overlay only covers the right portion so it doesn't shadow A.leaf at (15,15)
    { class_name: 'Overlay', bounds: { left: 60, top: 0, right: 100, bottom: 50 }, children: [] },
  ],
};

test('returns deepest node containing point', () => {
  const v = findViewAt(tree, 15, 15);
  assert.equal(v.class_name, 'A.leaf');
});

test('returns last drawn child when overlapping at same depth', () => {
  // (60,10) is in B and Overlay (both depth 1, same parent). Overlay drawn last.
  const v = findViewAt(tree, 60, 10);
  assert.equal(v.class_name, 'Overlay');
});

test('returns root when point only in root', () => {
  const v = findViewAt(tree, 80, 80);
  assert.equal(v.class_name, 'Root');
});

test('returns null when point outside root', () => {
  const v = findViewAt(tree, 500, 500);
  assert.equal(v, null);
});

test('returns null on empty tree', () => {
  assert.equal(findViewAt(null, 0, 0), null);
});

test('point on right/bottom edge is excluded (half-open bounds)', () => {
  const v = findViewAt(tree, 50, 50);
  // (50,50) is the right/bottom edge of A and A.leaf (excluded);
  // it IS inside Root (0..100). So we expect Root.
  assert.equal(v.class_name, 'Root');
});

test('skips a transparent overlay container in favor of a deeper underlying view', () => {
  // RealContent has a deep TextView; TransparentOverlay sits on top of the
  // same area but its only child is a tiny corner button that doesn't contain
  // the click point. Expected: TextView wins (deeper than TransparentOverlay).
  const overlayTree = {
    class_name: 'Root',
    bounds: { left: 0, top: 0, right: 100, bottom: 100 },
    children: [
      { class_name: 'RealContent',
        bounds: { left: 0, top: 0, right: 100, bottom: 100 },
        children: [
          { class_name: 'TextView', id_str: 'tv', text: 'hello',
            bounds: { left: 10, top: 10, right: 90, bottom: 30 }, children: [] },
        ] },
      { class_name: 'TransparentOverlay',
        bounds: { left: 0, top: 0, right: 100, bottom: 100 },
        children: [
          { class_name: 'CornerBtn',
            bounds: { left: 90, top: 90, right: 100, bottom: 100 }, children: [] },
        ] },
    ],
  };
  const v = findViewAt(overlayTree, 50, 20);
  assert.equal(v.class_name, 'TextView');
});

test('among same-depth candidates, higher information score wins', () => {
  // Both buttons at depth 2 contain the point; the labeled one (with id_str)
  // should beat the unlabeled one even if drawn earlier.
  const t = {
    class_name: 'Root',
    bounds: { left: 0, top: 0, right: 100, bottom: 100 },
    children: [
      { class_name: 'PanelA',
        bounds: { left: 0, top: 0, right: 100, bottom: 100 },
        children: [
          { class_name: 'NamedBtn', id_str: 'submit',
            bounds: { left: 10, top: 10, right: 50, bottom: 50 }, children: [] },
        ] },
      { class_name: 'PanelB',
        bounds: { left: 0, top: 0, right: 100, bottom: 100 },
        children: [
          { class_name: 'AnonBtn',
            bounds: { left: 10, top: 10, right: 50, bottom: 50 }, children: [] },
        ] },
    ],
  };
  const v = findViewAt(t, 30, 30);
  assert.equal(v.class_name, 'NamedBtn');
});
