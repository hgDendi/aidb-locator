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

    return () => {
      if (!visible.value) return null;
      const label = `${props.node.class_name}${props.node.id_str ? '#' + props.node.id_str : ''}`;
      const children = props.node.children || [];
      return h('div', { class: ['tree-node', { selected: isSelected.value }] }, [
        h('div', {
          class: 'tree-row',
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
const EDIT_FIELDS = [
  { code: 'T',    label: '文字',     type: 'text',   from: n => n.text || '' },
  { code: 'P',    label: 'Padding',  type: 'box4',   from: n => (n.padding || [0,0,0,0]).join(',') },
  { code: 'M',    label: 'Margin',   type: 'box4',   from: n => (n.margin  || [0,0,0,0]).join(',') },
  { code: 'A',    label: '透明度',   type: 'alpha',  from: n => String(n.alpha ?? 1) },
  { code: 'B',    label: '背景色',   type: 'color',  from: n => n.background_color || '#ffffff' },
  { code: 'TC',   label: '文字色',   type: 'color',  from: n => n.text_color || '#000000' },
  { code: 'TS',   label: '文字大小', type: 'number', from: n => String(n.text_size || 0) },
  { code: 'VF',   label: '可见性',   type: 'visibility', from: n => n.visibility || 'V' },
  { code: 'LP',   label: '宽高',     type: 'box2',   from: n => `${(n.bounds?.right ?? 0) - (n.bounds?.left ?? 0)},${(n.bounds?.bottom ?? 0) - (n.bounds?.top ?? 0)}` },
  { code: 'TXY',  label: '位移',     type: 'box2',   from: () => '0,0' },
  { code: 'SCXY', label: '缩放',     type: 'box2',   from: () => '1,1' },
];

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
  props: ['node', 'device'],
  emits: ['edit-applied', 'error'],
  setup(props, { emit }) {
    const editValues = reactive({});

    watch(() => props.node, (n) => {
      for (const f of EDIT_FIELDS) editValues[f.code] = f.from(n);
    }, { immediate: true });

    const copy = (text) => navigator.clipboard.writeText(text).catch(() => {});

    async function applyEdit(code) {
      try {
        const url = '/api/edit' + (props.device ? `?device=${encodeURIComponent(props.device)}` : '');
        const r = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            view_addr: props.node.mem_addr,
            edit_type: code,
            value: editValues[code],
          }),
        });
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error(body.message || `HTTP ${r.status}`);
        }
        emit('edit-applied');
      } catch (e) {
        emit('error', `编辑失败: ${e.message}`);
      }
    }

    function exportViewPng() {
      const url = `/api/capture/${encodeURIComponent(props.node.mem_addr)}` +
        (props.device ? `?device=${encodeURIComponent(props.device)}` : '');
      window.open(url, '_blank');
    }

    return () => {
      const n = props.node;
      const b = n.bounds || {};
      const path = (n.class_name || '') + (n.id_str ? `#${n.id_str}` : '');
      return h('div', { class: 'p-3 text-sm space-y-3' }, [
        h('div', { class: 'space-y-1' }, [
          h('div', null, [h('b', null, 'class: '), n.class_name]),
          n.id_str ? h('div', null, [h('b', null, 'id: '), n.id_str]) : null,
          h('div', null, [h('b', null, 'bounds: '), `${b.left},${b.top} → ${b.right},${b.bottom} (${b.right - b.left}×${b.bottom - b.top})`]),
          n.text ? h('div', null, [h('b', null, 'text: '), n.text]) : null,
          n.mem_addr ? h('div', null, [h('b', null, 'mem_addr: '), n.mem_addr]) : null,
        ]),
        h('div', { class: 'flex gap-2 flex-wrap' }, [
          h('button', { class: 'bg-gray-200 px-2 py-1 rounded text-xs', onClick: () => copy(n.id_str || '') }, '📋 复制 id'),
          h('button', { class: 'bg-gray-200 px-2 py-1 rounded text-xs', onClick: () => copy(path) }, '📋 复制路径'),
          h('button', { class: 'bg-gray-200 px-2 py-1 rounded text-xs', onClick: () => copy(`${b.left},${b.top},${b.right},${b.bottom}`) }, '📋 复制坐标'),
        ]),
        h('hr'),
        h('div', { class: 'space-y-2' }, [
          h('div', { class: 'font-bold' }, '编辑属性'),
          ...EDIT_FIELDS.map(f => h('div', { class: 'flex items-center gap-2' }, [
            h('label', { class: 'w-16 text-xs text-gray-600' }, f.label),
            f.type === 'color'
              ? h('input', { type: 'color', value: editValues[f.code],
                  onInput: e => editValues[f.code] = e.target.value,
                  class: 'w-12 h-6' })
              : f.type === 'visibility'
              ? h('select', { value: editValues[f.code],
                  onChange: e => editValues[f.code] = e.target.value,
                  class: 'flex-1 border rounded px-1 text-xs' },
                  ['V','I','G'].map(o => h('option', { value: o }, o)))
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
            h('button', { class: 'bg-blue-600 text-white px-2 py-1 rounded text-xs',
                          onClick: () => applyEdit(f.code) }, '应用'),
          ])),
        ]),
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
    const hover = ref(null);
    const imageEl = ref(null);
    let scale = 1;

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
      try {
        const url = '/api/snapshot' + (device.value ? `?device=${encodeURIComponent(device.value)}` : '');
        snapshot.value = await fetchJson(url);
        selected.value = null;
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
      const img = new Image();
      img.onload = () => {
        const maxW = 480;
        scale = Math.min(1, maxW / img.naturalWidth);
        canvas.width = img.naturalWidth * scale;
        canvas.height = img.naturalHeight * scale;
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        imageEl.value = img;
        drawOverlays();
      };
      img.src = 'data:image/png;base64,' + snapshot.value.screenshot_png_b64;
    }

    function drawOverlays() {
      if (!canvasRef.value || !imageEl.value) return;
      const canvas = canvasRef.value;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(imageEl.value, 0, 0, canvas.width, canvas.height);
      // hover
      if (hover.value) drawBox(ctx, hover.value, 'rgba(220,38,38,0.9)', true);
      // selected
      if (selected.value) drawBox(ctx, selected.value, 'rgba(37,99,235,0.95)', false);
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
      schemaInput, canvasRef, hover, hasLayout,
      refresh, onCanvasMove, onCanvasLeave, onCanvasClick,
      onPickFromTree, sendSchema, exportLayoutJson,
    };
  },
}).mount('#app');
