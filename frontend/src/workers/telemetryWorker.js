let ws = null;
let sharedBuffer = null;
let headerArray = null;
let dataArray0 = null;
let dataArray1 = null;

let nodeMap = new Map();
let nextIndex = 0;

self.onmessage = function(e) {
  if (e.data.type === 'init') {
    sharedBuffer = e.data.buffer;

    // Header: 1x Int32 (4 bytes)
    headerArray = new Int32Array(sharedBuffer, 0, 1);

    const floatsPerNode = 4;
    const maxNodes = e.data.maxNodes || 10000;
    const chunkFloats = maxNodes * floatsPerNode;

    dataArray0 = new Float32Array(sharedBuffer, 4, chunkFloats);
    dataArray1 = new Float32Array(sharedBuffer, 4 + chunkFloats * 4, chunkFloats);

    connect(e.data.wsUrl, e.data.token);
  } else if (e.data.type === 'set_nodes') {
    nodeMap.clear();
    e.data.nodes.forEach((id, i) => {
      nodeMap.set(id, i);
    });
    nextIndex = e.data.nodes.length;
  }
};

const decoder = new TextDecoder('utf-8');

function connect(wsUrl, token) {
  ws = new WebSocket(`${wsUrl}?token=${token}`);
  ws.binaryType = 'arraybuffer';

  ws.onmessage = function(event) {
    if (typeof event.data === 'string') return;

    const buffer = event.data;
    const view = new DataView(buffer);
    const numNodes = Math.floor(buffer.byteLength / 49);

    const activeIndex = Atomics.load(headerArray, 0);
    const writeIndex = activeIndex === 0 ? 1 : 0;
    const targetArray = writeIndex === 0 ? dataArray0 : dataArray1;
    const sourceArray = activeIndex === 0 ? dataArray0 : dataArray1;

    targetArray.set(sourceArray);

    let hasNewNodes = false;

    for (let i = 0; i < numNodes; i++) {
      const offset = i * 49;

      let uuidBytes = new Uint8Array(buffer, offset, 36);
      let end = 0;
      while (end < 36 && uuidBytes[end] !== 0) end++;
      let uuid = decoder.decode(uuidBytes.subarray(0, end));

      const x = view.getFloat32(offset + 36, false);
      const y = view.getFloat32(offset + 40, false);
      const z = view.getFloat32(offset + 44, false);
      const status = view.getUint8(offset + 48);

      let nodeIdx = nodeMap.get(uuid);
      if (nodeIdx === undefined) {
        nodeIdx = nextIndex++;
        nodeMap.set(uuid, nodeIdx);
        hasNewNodes = true;
      }

      const arrOffset = nodeIdx * 4;
      targetArray[arrOffset] = x;
      targetArray[arrOffset + 1] = y;
      targetArray[arrOffset + 2] = z;
      targetArray[arrOffset + 3] = status;
    }

    Atomics.store(headerArray, 0, writeIndex);

    if (hasNewNodes) {
      self.postMessage({ type: 'node_map', map: Array.from(nodeMap.entries()) });
    }
  };

  ws.onclose = () => {
    setTimeout(() => connect(wsUrl, token), 1000);
  };
}
