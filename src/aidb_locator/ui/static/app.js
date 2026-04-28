import { findViewAt } from '/findViewAt.js';

const { createApp, ref, reactive, computed, watch, onMounted, nextTick, defineComponent, h } = Vue;

// ----- Tree node component -----
const TreeNode = defineComponent({
  name: 'tree-node',
  props: ['node', 'selected', 'search', 'path'],
  emits: ['pick'],
  setup(props, { emit }) {
    const expanded = ref(true);

    const matchesSelf = computed(() => {
      if (!props.search) return true;
      const s = props.search.toLowerCase();
      return [props.node.class_name, props.node.id_str, props.node.text]
        .filter(Boolean).some(x => String(x).toLowerCase().includes(s));
    });

    const hasMatchingDescendant = (n) => {
      if (!props.search) return true;
      const s = props.search.toLowerCase();
      const hit = [n.class_name, n.id_str, n.text]
        .filter(Boolean).some(x => String(x).toLowerCase().includes(s));
      if (hit) return true;
      return (n.children || []).some(hasMatchingDescendant);
    };

    const visible = computed(() => matchesSelf.value || hasMatchingDescendant(props.node));

    // When searching, auto-expand to reveal matches
    watch(() => props.search, () => { if (props.search) expanded.value = true; });

    const isSelected = computed(() =>
      props.selected && props.selected.mem_addr && props.selected.mem_addr === props.node.mem_addr
    );

    // True if THIS node or any descendant matches selected — used to auto-
    // expand collapsed ancestors so the selected row is actually rendered
    // (otherwise scrollIntoView has nothing to scroll to).
    const hasSelectedDescendant = computed(() => {
      const sel = props.selected;
      if (!sel?.mem_addr) return false;
      const walk = (n) => {
        if (n.mem_addr === sel.mem_addr) return true;
        return (n.children || []).some(walk);
      };
      return walk(props.node);
    });

    watch(hasSelectedDescendant, (v) => { if (v) expanded.value = true; });

    const rowRef = ref(null);
    watch(isSelected, async (val) => {
      if (!val) return;
      await nextTick();
      rowRef.value?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }, { immediate: true });

    return () => {
      if (!visible.value) return null;
      const fqn = props.node.class_name || '';
      const dot = fqn.lastIndexOf('.');
      const shortName = dot >= 0 ? fqn.slice(dot + 1) : fqn;
      const label = `${shortName}${props.node.id_str ? '#' + props.node.id_str : ''}`;
      const children = props.node.children || [];
      return h('div', { class: ['tree-node', { selected: isSelected.value }] }, [
        h('div', {
          ref: rowRef,
          class: 'tree-row',
          title: fqn,  // hover tooltip shows the full FQN
          onClick: () => emit('pick', props.node, [...props.path]),
        }, [
          children.length
            ? h('span', { onClick: (e) => { e.stopPropagation(); expanded.value = !expanded.value; } },
                expanded.value ? '▾ ' : '▸ ')
            : h('span', null, '• '),
          label,
        ]),
        expanded.value && children.length
          ? h('div', { style: 'margin-left: 12px' },
              children.map((c, i) => h(TreeNode, {
                node: c, selected: props.selected, search: props.search,
                path: [...props.path, i], onPick: (n, p) => emit('pick', n, p),
              })))
          : null,
      ]);
    };
  },
});

// ----- View details / edit form -----
// type: 'box4' → 4 number inputs (l,t,r,b); 'box2' → 2 inputs (x,y or w,h)
// unit: shown after the input(s); CodeLocator returns dimensional fields in px,
// so values are always px. Android source convention uses dp/sp; users can
// mentally convert via the device density shown in the device size badge.
const EDIT_FIELDS = [
  { code: 'T',    label: '文字',     type: 'text',   from: n => n.text || '' },
  { code: 'P',    label: 'Padding',  type: 'box4',   unit: 'px', from: n => (n.padding || [0,0,0,0]).join(',') },
  { code: 'M',    label: 'Margin',   type: 'box4',   unit: 'px', from: n => (n.margin  || [0,0,0,0]).join(',') },
  { code: 'A',    label: '透明度',   type: 'alpha',  from: n => String(n.alpha ?? 1) },
  { code: 'B',    label: '背景色',   type: 'color',  from: n => n.background_color || '#ffffff' },
  { code: 'TC',   label: '文字色',   type: 'color',  from: n => n.text_color || '#000000' },
  { code: 'TS',   label: '文字大小', type: 'number', unit: 'px', from: n => String(n.text_size || 0) },
  { code: 'VF',   label: '可见性',   type: 'visibility', from: n => n.visibility || 'V' },
  { code: 'LP',   label: '宽高',     type: 'box2',   unit: 'px', from: n => `${(n.bounds?.right ?? 0) - (n.bounds?.left ?? 0)},${(n.bounds?.bottom ?? 0) - (n.bounds?.top ?? 0)}` },
  { code: 'TXY',  label: '位移',     type: 'box2',   unit: 'px', from: () => '0,0' },
  { code: 'SCXY', label: '缩放',     type: 'box2',   from: () => '1,1' },
];

// ----- Tree walking helpers -----
function findAncestors(root, addr, chain = []) {
  if (!root || !addr) return null;
  const here = [...chain, root];
  if (root.mem_addr === addr) return here;
  for (const c of root.children || []) {
    const r = findAncestors(c, addr, here);
    if (r) return r;
  }
  return null;
}
function findByMemAddr(root, addr) {
  if (!root || !addr) return null;
  if (root.mem_addr === addr) return root;
  for (const c of root.children || []) {
    const r = findByMemAddr(c, addr);
    if (r) return r;
  }
  return null;
}

// ----- Color helpers (parse/format #AARRGGBB; native picker is RGB-only) -----
function parseColor(s) {
  const m = String(s || '').match(/^#?([0-9a-fA-F]{8}|[0-9a-fA-F]{6})$/);
  if (!m) return { a: 255, r: 0, g: 0, b: 0 };
  const hex = m[1];
  if (hex.length === 6) {
    return { a: 255,
             r: parseInt(hex.slice(0,2), 16),
             g: parseInt(hex.slice(2,4), 16),
             b: parseInt(hex.slice(4,6), 16) };
  }
  return { a: parseInt(hex.slice(0,2), 16),
           r: parseInt(hex.slice(2,4), 16),
           g: parseInt(hex.slice(4,6), 16),
           b: parseInt(hex.slice(6,8), 16) };
}
function formatColor(a, r, g, b) {
  const hh = n => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, '0');
  return `#${hh(a)}${hh(r)}${hh(g)}${hh(b)}`;
}
function renderColor(value, onUpdate) {
  const c = parseColor(value);
  const argbHex = formatColor(c.a, c.r, c.g, c.b).toUpperCase();   // #AARRGGBB
  const rgbHex = `#${[c.r, c.g, c.b].map(n => n.toString(16).padStart(2,'0')).join('')}`;
  return h('div', { class: 'flex-1 flex items-center gap-1' }, [
    h('input', { type: 'color', value: rgbHex,
      onInput: e => {
        const v = e.target.value;
        onUpdate(formatColor(c.a, parseInt(v.slice(1,3),16), parseInt(v.slice(3,5),16), parseInt(v.slice(5,7),16)));
      },
      class: 'w-8 h-6 shrink-0 border rounded' }),
    h('input', { type: 'text', value: argbHex,
      onChange: e => {
        const p = parseColor(e.target.value);
        onUpdate(formatColor(p.a, p.r, p.g, p.b));
      },
      class: 'flex-1 border rounded px-1 text-xs font-mono uppercase' }),
  ]);
}

function renderBoxN(values, n, onUpdate) {
  const parts = String(values || '').split(',').concat(['0','0','0','0']).slice(0, n);
  return h('div', { class: 'flex gap-1 flex-1' },
    parts.map((p, i) => h('input', {
      type: 'number',
      value: p,
      onInput: e => {
        const next = [...parts]; next[i] = e.target.value;
        onUpdate(next.join(','));
      },
      class: 'w-12 border rounded px-1 text-xs',
    }))
  );
}

const ViewDetails = defineComponent({
  name: 'view-details',
  props: ['node', 'device', 'snapshot'],
  emits: ['edit-applied', 'error'],
  setup(props, { emit }) {
    const editValues = reactive({});      // current input values per field code
    const baseline   = reactive({});      // value at the moment the node was first selected
    const appliedValue = reactive({});    // last value successfully applied (per field) — drives 撤销 button + change report
    const lastAddr = ref(null);

    // When a *different* node is selected, capture baseline + reset applied.
    // When the *same* node is refreshed (post-edit), only refresh editValues for
    // fields the user hasn't applied (so unapplied dirty input is preserved).
    watch(() => props.node, (n) => {
      if (!n) return;
      const switched = lastAddr.value !== n.mem_addr;
      lastAddr.value = n.mem_addr;
      if (switched) {
        for (const k of Object.keys(baseline))     delete baseline[k];
        for (const k of Object.keys(appliedValue)) delete appliedValue[k];
      }
      for (const f of EDIT_FIELDS) {
        const v = f.from(n);
        if (switched) baseline[f.code] = v;
        if (appliedValue[f.code] === undefined) editValues[f.code] = v;
      }
    }, { immediate: true });

    const copy = (text) => navigator.clipboard.writeText(text).catch(() => {});

    // What the device most recently has for this field (per our knowledge):
    // last applied value if any, otherwise the baseline.
    const effectiveValue = (code) =>
      appliedValue[code] !== undefined ? appliedValue[code] : baseline[code];
    const isDirty = (code) => editValues[code] !== effectiveValue(code);
    const wasApplied = (code) => appliedValue[code] !== undefined;
    const hasAnyApplied = computed(() =>
      EDIT_FIELDS.some(f => appliedValue[f.code] !== undefined));

    function buildElementReport() {
      const n = props.node;
      const b = n.bounds || {};
      const w = (b.right || 0) - (b.left || 0);
      const ht = (b.bottom || 0) - (b.top || 0);
      const snap = props.snapshot || {};
      const d = snap.density || 0;
      const sizeStr = d > 0 ? `${w}×${ht} px (${(w/d).toFixed(4)}×${(ht/d).toFixed(4)} dp)` : `${w}×${ht} px`;
      const ancestors = findAncestors(snap.layout, n.mem_addr) || [n];
      const chain = ancestors.slice(0, -1);

      const lines = [
        '# UI Element',
        '',
        `class: ${n.class_name}`,
        n.id_str ? `id: ${n.id_str}` : null,
        `bounds: ${b.left},${b.top} → ${b.right},${b.bottom}`,
        `size: ${sizeStr}`,
        n.text ? `text: ${JSON.stringify(n.text)}` : null,
        `mem_addr: ${n.mem_addr ?? ''}`,
        `visibility: ${n.visibility ?? 'V'}`,
        `clickable: ${!!n.is_clickable}`,
        `alpha: ${n.alpha ?? 1}`,
        `background_color: ${n.background_color || 'null'}`,
        `text_color: ${n.text_color || 'null'}`,
        `text_size: ${n.text_size || 0}`,
        `padding [l,t,r,b]: ${(n.padding || [0,0,0,0]).join(',')}`,
        `margin  [l,t,r,b]: ${(n.margin  || [0,0,0,0]).join(',')}`,
        '',
        '## Hierarchy (root → selected)',
        ...chain.map((a, i) => `${'  '.repeat(i)}${a.class_name}${a.id_str ? '#' + a.id_str : ''}`),
        `${'  '.repeat(chain.length)}${n.class_name}${n.id_str ? '#' + n.id_str : ''}  ← selected`,
      ];

      const act = snap.activity;
      if (act && (act.activity || act.fragments?.length)) {
        lines.push('', '## Activity');
        if (act.activity) lines.push(`activity: ${act.activity}`);
        if (act.package)  lines.push(`package: ${act.package}`);
        if (act.fragments?.length) lines.push(`fragments: ${act.fragments.join(' > ')}`);
      }
      const ds = snap.device_size;
      if (ds && (ds.width || ds.height)) {
        lines.push('', '## Device');
        lines.push(`screen: ${ds.width}×${ds.height} px @ density ${d}`);
      }

      return lines.filter(l => l !== null).join('\n');
    }

    async function _send(code, value) {
      const url = '/api/edit' + (props.device ? `?device=${encodeURIComponent(props.device)}` : '');
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ view_addr: props.node.mem_addr, edit_type: code, value }),
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.message || `HTTP ${r.status}`);
      }
    }

    async function applyEdit(code) {
      try {
        await _send(code, editValues[code]);
        appliedValue[code] = editValues[code];   // remember for 撤销 + 改动报告
        emit('edit-applied');
      } catch (e) {
        emit('error', `编辑失败: ${e.message}`);
      }
    }

    async function undoEdit(code) {
      try {
        await _send(code, baseline[code]);
        delete appliedValue[code];
        editValues[code] = baseline[code];
        emit('edit-applied');
      } catch (e) {
        emit('error', `撤销失败: ${e.message}`);
      }
    }

    function buildChangesReport() {
      const lines = ['# Changes Applied', ''];
      for (const f of EDIT_FIELDS) {
        if (appliedValue[f.code] === undefined) continue;
        lines.push(`- ${f.label} (${f.code}): \`${baseline[f.code]}\` → \`${appliedValue[f.code]}\``);
      }
      lines.push('', buildElementReport());
      return lines.join('\n');
    }

    function exportViewPng() {
      const url = `/api/capture/${encodeURIComponent(props.node.mem_addr)}` +
        (props.device ? `?device=${encodeURIComponent(props.device)}` : '');
      window.open(url, '_blank');
    }

    return () => {
      const n = props.node;
      const b = n.bounds || {};
      const w = (b.right || 0) - (b.left || 0);
      const ht = (b.bottom || 0) - (b.top || 0);
      const d = props.snapshot?.density || 0;
      const sizeStr = d > 0
        ? `${w}×${ht} px (${(w / d).toFixed(4)} × ${(ht / d).toFixed(4)} dp)`
        : `${w.toFixed(4)}×${ht.toFixed(4)}`;
      return h('div', { class: 'p-3 text-sm space-y-3' }, [
        h('div', { class: 'space-y-1' }, [
          h('div', null, [h('b', null, 'class: '), n.class_name]),
          n.id_str ? h('div', null, [h('b', null, 'id: '), n.id_str]) : null,
          h('div', null, [h('b', null, 'bounds: '), `${b.left},${b.top} → ${b.right},${b.bottom}`]),
          h('div', null, [h('b', null, 'size: '), sizeStr]),
          n.text ? h('div', null, [h('b', null, 'text: '), n.text]) : null,
          n.mem_addr ? h('div', null, [h('b', null, 'mem_addr: '), n.mem_addr]) : null,
        ]),
        h('div', { class: 'flex gap-2 flex-wrap' }, [
          h('button', {
            class: 'bg-blue-600 text-white px-3 py-1 rounded text-xs',
            onClick: () => copy(buildElementReport()),
            title: '把节点详情、层级、Activity / Fragment 拷到剪贴板，方便丢给 AI',
          }, '📋 Copy element'),
        ]),
        h('hr'),
        h('div', { class: 'space-y-2' }, [
          h('div', { class: 'font-bold' }, '编辑属性'),
          ...EDIT_FIELDS.map(f => h('div', { class: 'flex items-center gap-2' }, [
            h('label', { class: 'w-16 text-xs text-gray-600' }, f.label),
            f.type === 'color'
              ? renderColor(editValues[f.code], v => editValues[f.code] = v)
              : f.type === 'visibility'
              ? h('select', { value: editValues[f.code],
                  onChange: e => editValues[f.code] = e.target.value,
                  class: 'flex-1 border rounded px-1 text-xs' }, [
                  h('option', { value: 'V' }, 'Visible'),
                  h('option', { value: 'I' }, 'Invisible'),
                  h('option', { value: 'G' }, 'Gone'),
                ])
              : f.type === 'alpha'
              ? h('input', { type: 'range', min: 0, max: 1, step: 0.01,
                  value: editValues[f.code],
                  onInput: e => editValues[f.code] = e.target.value,
                  class: 'flex-1' })
              : f.type === 'box4'
              ? renderBoxN(editValues[f.code], 4, v => editValues[f.code] = v)
              : f.type === 'box2'
              ? renderBoxN(editValues[f.code], 2, v => editValues[f.code] = v)
              : h('input', { type: f.type === 'number' ? 'number' : 'text',
                  value: editValues[f.code],
                  onInput: e => editValues[f.code] = e.target.value,
                  class: 'flex-1 border rounded px-1 text-xs' }),
            f.unit ? h('span', { class: 'text-[10px] text-gray-500 w-5 text-center' }, f.unit) : null,
            // Buttons appear conditionally: 应用 only when dirty, 撤销 only after
            // a successful apply; both can show if user re-edits after applying.
            isDirty(f.code)
              ? h('button', { class: 'bg-blue-600 text-white px-2 py-1 rounded text-xs',
                              title: `从 \`${effectiveValue(f.code)}\` 改为 \`${editValues[f.code]}\``,
                              onClick: () => applyEdit(f.code) }, '应用')
              : null,
            wasApplied(f.code)
              ? h('button', { class: 'bg-orange-500 text-white px-2 py-1 rounded text-xs',
                              title: `还原成最初的 \`${baseline[f.code]}\``,
                              onClick: () => undoEdit(f.code) }, '撤销')
              : null,
          ])),
        ]),
        hasAnyApplied.value
          ? h('div', { class: 'pt-2 border-t border-orange-200' }, [
              h('button', {
                class: 'bg-orange-600 text-white px-3 py-1 rounded text-xs',
                onClick: () => copy(buildChangesReport()),
                title: '把所有 applied 改动 + element 信息一起拷贝（可直接给 AI）',
              }, '📋 copy 改动'),
            ])
          : null,
        h('hr'),
        n.mem_addr
          ? h('button', { class: 'bg-gray-200 px-3 py-1 rounded text-xs',
                          onClick: exportViewPng }, '📥 导出该 view 截图')
          : null,
      ]);
    };
  },
});

// ----- Root app -----
createApp({
  components: { 'tree-node': TreeNode, 'view-details': ViewDetails },
  setup() {
    const devices = ref([]);
    const device = ref(null);
    const snapshot = ref(null);
    const selected = ref(null);
    const search = ref('');
    const error = ref(null);
    const loading = ref(false);
    const schemaInput = ref('');
    const canvasRef = ref(null);
    const canvasWrapRef = ref(null);
    const hover = ref(null);
    const imageEl = ref(null);
    let scale = 1;            // effective canvas → device pixel ratio
    let baseScale = 1;        // fit-to-container scale before user zoom
    const zoom = ref(1);      // user zoom factor (pinch / ctrl+wheel)

    // Resizable columns
    const leftW = ref(288);   // matches old w-72
    const rightW = ref(320);  // matches old w-80

    function startResize(which, e) {
      e.preventDefault();
      const startX = e.clientX;
      const startLW = leftW.value;
      const startRW = rightW.value;
      const onMove = (ev) => {
        const dx = ev.clientX - startX;
        if (which === 'left')  leftW.value  = Math.max(160, Math.min(600, startLW + dx));
        else                   rightW.value = Math.max(220, Math.min(700, startRW - dx));
      };
      const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    function onCanvasWheel(e) {
      // macOS trackpad pinch fires wheel events with ctrlKey=true
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const factor = e.deltaY > 0 ? 0.9 : 1.111;
        zoom.value = Math.max(0.2, Math.min(8, zoom.value * factor));
        renderImage();
      }
      // else: native two-finger scroll handles pan inside overflow-auto section
    }

    function resetZoom() { zoom.value = 1; renderImage(); }

    // True when a snapshot has been loaded AND it contains a real layout tree
    // (not the empty WApplication that grab_layout() returns when no SDK responds).
    const hasLayout = computed(() => !!snapshot.value?.layout?.class_name);

    async function fetchJson(url, init) {
      const r = await fetch(url, init);
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.message || `HTTP ${r.status}`);
      }
      return r.json();
    }

    async function loadDevices() {
      try {
        devices.value = await fetchJson('/api/devices');
        if (devices.value.length && !device.value) device.value = devices.value[0].serial;
      } catch (e) {
        error.value = `获取设备失败: ${e.message}`;
      }
    }

    async function refresh() {
      if (!device.value && devices.value.length === 0) {
        await loadDevices();
      }
      loading.value = true;
      error.value = null;
      const prevAddr = selected.value?.mem_addr;
      try {
        const url = '/api/snapshot' + (device.value ? `?device=${encodeURIComponent(device.value)}` : '');
        snapshot.value = await fetchJson(url);
        // Try to keep focus on the same view by mem_addr; falls back to null
        // if the view was destroyed/recreated and now has a different addr.
        selected.value = prevAddr ? findByMemAddr(snapshot.value?.layout, prevAddr) : null;
        await nextTick();
        renderImage();
      } catch (e) {
        error.value = `刷新失败: ${e.message}`;
      } finally {
        loading.value = false;
      }
    }

    function renderImage() {
      if (!snapshot.value || !canvasRef.value) return;
      const canvas = canvasRef.value;
      const ctx = canvas.getContext('2d');
      const draw = (img) => {
        const containerW = canvasWrapRef.value?.clientWidth || 600;
        baseScale = Math.min(1, containerW / img.naturalWidth);
        scale = baseScale * zoom.value;
        canvas.width  = Math.max(1, Math.round(img.naturalWidth  * scale));
        canvas.height = Math.max(1, Math.round(img.naturalHeight * scale));
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        imageEl.value = img;
        drawOverlays();
      };
      if (imageEl.value && imageEl.value.src.endsWith(snapshot.value.screenshot_png_b64.slice(-32))) {
        // Same screenshot data — reuse decoded image (avoids flicker on zoom)
        draw(imageEl.value);
      } else {
        const img = new Image();
        img.onload = () => draw(img);
        img.src = 'data:image/png;base64,' + snapshot.value.screenshot_png_b64;
      }
    }

    function drawOverlays() {
      if (!canvasRef.value || !imageEl.value) return;
      const canvas = canvasRef.value;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(imageEl.value, 0, 0, canvas.width, canvas.height);
      const density = snapshot.value?.density || 0;
      // hover (red dashed)
      if (hover.value) drawBox(ctx, hover.value, 'rgba(220,38,38,0.9)', true);
      // selected: padding/margin fills then bounding box
      if (selected.value) {
        drawPaddingMargin(ctx, selected.value);
        drawBox(ctx, selected.value, 'rgba(37,99,235,0.95)', false);
      }
      // distance measurements between selected and hover (if different)
      if (selected.value && hover.value &&
          selected.value.mem_addr !== hover.value.mem_addr) {
        drawDistances(ctx, selected.value, hover.value, density);
      }
    }

    function drawPaddingMargin(ctx, node) {
      const b = node.bounds; if (!b) return;
      const [pl, pt, pr, pb] = node.padding || [0,0,0,0];
      const [ml, mt, mr, mb] = node.margin || [0,0,0,0];
      const s = scale;
      // Margin: yellow outside the view
      if (ml || mt || mr || mb) {
        ctx.fillStyle = 'rgba(234,179,8,0.30)';
        ctx.fillRect((b.left - ml) * s, (b.top - mt) * s, (b.right - b.left + ml + mr) * s, mt * s);              // top
        ctx.fillRect((b.left - ml) * s, b.bottom * s,       (b.right - b.left + ml + mr) * s, mb * s);             // bottom
        ctx.fillRect((b.left - ml) * s, b.top * s,           ml * s, (b.bottom - b.top) * s);                       // left
        ctx.fillRect(b.right * s,        b.top * s,           mr * s, (b.bottom - b.top) * s);                       // right
      }
      // Padding: green inside the view
      if (pl || pt || pr || pb) {
        ctx.fillStyle = 'rgba(34,197,94,0.30)';
        ctx.fillRect(b.left * s,                b.top * s,                  (b.right - b.left) * s, pt * s);                       // top
        ctx.fillRect(b.left * s,                (b.bottom - pb) * s,        (b.right - b.left) * s, pb * s);                       // bottom
        ctx.fillRect(b.left * s,                (b.top + pt) * s,           pl * s, (b.bottom - b.top - pt - pb) * s);             // left
        ctx.fillRect((b.right - pr) * s,        (b.top + pt) * s,           pr * s, (b.bottom - b.top - pt - pb) * s);             // right
      }
    }

    function drawBox(ctx, node, color, dashed) {
      const b = node.bounds; if (!b) return;
      ctx.save();
      ctx.lineWidth = 2;
      ctx.strokeStyle = color;
      if (dashed) ctx.setLineDash([6, 4]); else ctx.setLineDash([]);
      ctx.strokeRect(b.left * scale, b.top * scale,
                     (b.right - b.left) * scale, (b.bottom - b.top) * scale);
      ctx.restore();
    }

    function _expandedBounds(n) {
      const b = n.bounds;
      const [ml, mt, mr, mb] = n.margin || [0,0,0,0];
      return { left: b.left - ml, top: b.top - mt, right: b.right + mr, bottom: b.bottom + mb };
    }
    function _rectContains(outer, inner) {
      return outer.left <= inner.left && outer.top <= inner.top
          && outer.right >= inner.right && outer.bottom >= inner.bottom;
    }
    function _fmtDist(px, density) {
      if (density > 0) return `${px}px / ${(px/density).toFixed(1)}dp`;
      return `${px}px`;
    }
    function _drawMeasureLine(ctx, x1, y1, x2, y2, label, color) {
      const s = scale;
      const sx1 = x1 * s, sy1 = y1 * s, sx2 = x2 * s, sy2 = y2 * s;
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      // Line itself, dashed
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(sx1, sy1); ctx.lineTo(sx2, sy2);
      ctx.stroke();
      ctx.setLineDash([]);
      // Tick caps at both endpoints (perpendicular to the line)
      const isHorizontal = Math.abs(sy1 - sy2) < 0.5;
      const tick = 4;
      ctx.beginPath();
      if (isHorizontal) {
        ctx.moveTo(sx1, sy1 - tick); ctx.lineTo(sx1, sy1 + tick);
        ctx.moveTo(sx2, sy2 - tick); ctx.lineTo(sx2, sy2 + tick);
      } else {
        ctx.moveTo(sx1 - tick, sy1); ctx.lineTo(sx1 + tick, sy1);
        ctx.moveTo(sx2 - tick, sy2); ctx.lineTo(sx2 + tick, sy2);
      }
      ctx.stroke();
      // Label pill at midpoint
      const mx = (sx1 + sx2) / 2;
      const my = (sy1 + sy2) / 2;
      ctx.font = '11px -apple-system, system-ui, sans-serif';
      const pad = 4;
      const w = ctx.measureText(label).width + pad * 2;
      const lh = 16;
      ctx.fillStyle = color;
      ctx.fillRect(mx - w/2, my - lh/2, w, lh);
      ctx.fillStyle = 'white';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, mx, my);
      ctx.restore();
    }
    function drawDistances(ctx, sel, hov, density) {
      const a = _expandedBounds(sel);
      const b = _expandedBounds(hov);
      const color = 'rgba(236,72,153,0.95)'; // pink-500: contrasts with red+blue
      const aContainsB = _rectContains(a, b);
      const bContainsA = _rectContains(b, a);

      if (aContainsB || bContainsA) {
        // Nested: 4 inset distances from inner to outer (Figma style)
        const inner = aContainsB ? b : a;
        const outer = aContainsB ? a : b;
        const cx = (inner.left + inner.right) / 2;
        const cy = (inner.top + inner.bottom) / 2;
        const top = inner.top - outer.top;
        const bot = outer.bottom - inner.bottom;
        const lft = inner.left - outer.left;
        const rgt = outer.right - inner.right;
        if (top > 0) _drawMeasureLine(ctx, cx, outer.top,    cx, inner.top,    _fmtDist(top, density), color);
        if (bot > 0) _drawMeasureLine(ctx, cx, inner.bottom, cx, outer.bottom, _fmtDist(bot, density), color);
        if (lft > 0) _drawMeasureLine(ctx, outer.left,  cy, inner.left,  cy, _fmtDist(lft, density), color);
        if (rgt > 0) _drawMeasureLine(ctx, inner.right, cy, outer.right, cy, _fmtDist(rgt, density), color);
        return;
      }

      // Disjoint: gap on whichever axis they don't overlap
      // Vertical
      let v = null;
      if (b.top >= a.bottom)      v = { y1: a.bottom, y2: b.top, gap: b.top - a.bottom };
      else if (a.top >= b.bottom) v = { y1: b.bottom, y2: a.top, gap: a.top - b.bottom };
      if (v) {
        const ovL = Math.max(a.left, b.left);
        const ovR = Math.min(a.right, b.right);
        const cx = ovR > ovL ? (ovL + ovR) / 2 : (a.left + a.right) / 2;
        _drawMeasureLine(ctx, cx, v.y1, cx, v.y2, _fmtDist(v.gap, density), color);
      }
      // Horizontal
      let h_ = null;
      if (b.left >= a.right)      h_ = { x1: a.right, x2: b.left, gap: b.left - a.right };
      else if (a.left >= b.right) h_ = { x1: b.right, x2: a.left, gap: a.left - b.right };
      if (h_) {
        const ovT = Math.max(a.top, b.top);
        const ovB = Math.min(a.bottom, b.bottom);
        const cy = ovB > ovT ? (ovT + ovB) / 2 : (a.top + a.bottom) / 2;
        _drawMeasureLine(ctx, h_.x1, cy, h_.x2, cy, _fmtDist(h_.gap, density), color);
      }
    }

    let lastMove = 0;
    function onCanvasMove(e) {
      const now = performance.now();
      if (now - lastMove < 33) return;
      lastMove = now;
      const rect = canvasRef.value.getBoundingClientRect();
      const x = (e.clientX - rect.left) / scale;
      const y = (e.clientY - rect.top) / scale;
      hover.value = findViewAt(snapshot.value?.layout, x, y);
      drawOverlays();
    }
    function onCanvasLeave() { hover.value = null; drawOverlays(); }
    function onCanvasClick(e) {
      const rect = canvasRef.value.getBoundingClientRect();
      const x = (e.clientX - rect.left) / scale;
      const y = (e.clientY - rect.top) / scale;
      const hit = findViewAt(snapshot.value?.layout, x, y);
      if (hit) selected.value = hit;
      drawOverlays();
    }

    function onPickFromTree(node) {
      selected.value = node;
      drawOverlays();
    }

    async function sendSchema() {
      if (!schemaInput.value) return;
      try {
        const url = '/api/schema' + (device.value ? `?device=${encodeURIComponent(device.value)}` : '');
        await fetchJson(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ schema: schemaInput.value }),
        });
        await refresh();
      } catch (e) {
        error.value = `Schema 跳转失败: ${e.message}`;
      }
    }

    function exportLayoutJson() {
      if (!snapshot.value?.layout) return;
      const blob = new Blob([JSON.stringify(snapshot.value.layout, null, 2)],
                            { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `layout_${Date.now()}.json`;
      a.click();
    }

    onMounted(loadDevices);

    return {
      devices, device, snapshot, selected, search, error, loading,
      schemaInput, canvasRef, canvasWrapRef, hover, hasLayout,
      leftW, rightW, zoom,
      refresh, onCanvasMove, onCanvasLeave, onCanvasClick, onCanvasWheel,
      onPickFromTree, sendSchema, exportLayoutJson,
      startResize, resetZoom,
    };
  },
}).mount('#app');
