"""Minimal Compound File Binary (OLE2 / [MS-CFB]) writer.

Only what a vbaProject.bin needs: version 3 (512-byte sectors), a mini
stream for parts under 4096 bytes, no DIFAT sectors.
"""
import struct

SECTOR_SIZE = 512
MINI_SECTOR_SIZE = 64
MINI_CUTOFF = 4096
FAT_PER_SECTOR = SECTOR_SIZE // 4

FREESECT = 0xFFFFFFFF
ENDOFCHAIN = 0xFFFFFFFE
FATSECT = 0xFFFFFFFD
NOSTREAM = 0xFFFFFFFF

TYPE_STORAGE = 1
TYPE_STREAM = 2
TYPE_ROOT = 5


class Entry:
    """One directory entry: the root, a storage, or a stream."""

    def __init__(self, name, obj_type, data=b"", clsid=b"\x00" * 16):
        if len(name.encode("utf-16-le")) + 2 > 64:
            raise ValueError("directory entry name too long: %r" % name)
        self.name = name
        self.obj_type = obj_type
        self.data = data
        self.clsid = clsid
        self.children = []
        self.eid = NOSTREAM
        self.child_id = NOSTREAM
        self.left_id = NOSTREAM
        self.right_id = NOSTREAM
        self.start = ENDOFCHAIN
        self.size = 0
        self._l = None
        self._r = None

    def add(self, entry):
        self.children.append(entry)
        return entry


def _sort_key(entry):
    """[MS-CFB] 2.6.4: shorter names first, then by upper-cased name."""
    upper = entry.name.upper()
    return (len(upper), [ord(ch) for ch in upper])


def _build_tree(nodes):
    """Balanced BST over the sorted siblings; returns the subtree root."""
    if not nodes:
        return None
    mid = len(nodes) // 2
    node = nodes[mid]
    node._l = _build_tree(nodes[:mid])
    node._r = _build_tree(nodes[mid + 1:])
    return node


class CfbWriter:
    def __init__(self, root):
        self.root = root
        self._sectors = []
        self._fat = []

    # -- sector allocation -------------------------------------------------
    def _alloc(self, data):
        if not data:
            return ENDOFCHAIN
        first = prev = None
        for off in range(0, len(data), SECTOR_SIZE):
            block = data[off:off + SECTOR_SIZE].ljust(SECTOR_SIZE, b"\x00")
            self._sectors.append(block)
            self._fat.append(FREESECT)
            idx = len(self._sectors) - 1
            if first is None:
                first = idx
            else:
                self._fat[prev] = idx
            prev = idx
        self._fat[prev] = ENDOFCHAIN
        return first

    # -- directory ---------------------------------------------------------
    def _order(self):
        """Assign entry ids and wire up the sibling trees."""
        flat = [self.root]
        queue = [self.root]
        while queue:
            node = queue.pop(0)
            kids = sorted(node.children, key=_sort_key)
            for kid in kids:
                flat.append(kid)
                queue.append(kid)
            node._sorted_kids = kids
        for i, node in enumerate(flat):
            node.eid = i
        for node in flat:
            top = _build_tree(node._sorted_kids)
            node.child_id = top.eid if top is not None else NOSTREAM
            for kid in node._sorted_kids:
                kid.left_id = kid._l.eid if kid._l is not None else NOSTREAM
                kid.right_id = kid._r.eid if kid._r is not None else NOSTREAM
        return flat

    def _dir_bytes(self, flat):
        out = bytearray()
        for node in flat:
            name = node.name.encode("utf-16-le") + b"\x00\x00"
            out += name.ljust(64, b"\x00")
            out += struct.pack("<H", len(name))
            out += struct.pack("<BB", node.obj_type, 1)  # 1 = black
            out += struct.pack("<III", node.left_id, node.right_id, node.child_id)
            out += node.clsid
            out += struct.pack("<I", 0)          # StateBits
            out += b"\x00" * 16                  # creation / modified time
            out += struct.pack("<I", node.start)
            out += struct.pack("<Q", node.size)
        # pad the last directory sector with unallocated entries
        while len(out) % SECTOR_SIZE:
            out += b"\x00" * 64
            out += struct.pack("<H", 0)
            out += struct.pack("<BB", 0, 1)
            out += struct.pack("<III", NOSTREAM, NOSTREAM, NOSTREAM)
            out += b"\x00" * 16
            out += struct.pack("<I", 0) + b"\x00" * 16
            out += struct.pack("<I", 0) + struct.pack("<Q", 0)
        return bytes(out)

    # -- main --------------------------------------------------------------
    def build(self):
        flat = self._order()

        streams = [e for e in flat if e.obj_type == TYPE_STREAM]
        big = [e for e in streams if len(e.data) >= MINI_CUTOFF]
        small = [e for e in streams if 0 < len(e.data) < MINI_CUTOFF]

        for e in big:
            e.size = len(e.data)
            e.start = self._alloc(e.data)
        for e in streams:
            if not e.data:
                e.size = 0
                e.start = ENDOFCHAIN

        # mini stream + MiniFAT
        mini = bytearray()
        minifat = []
        for e in small:
            e.size = len(e.data)
            e.start = len(mini) // MINI_SECTOR_SIZE
            padded = e.data.ljust(
                ((len(e.data) + MINI_SECTOR_SIZE - 1) // MINI_SECTOR_SIZE) * MINI_SECTOR_SIZE,
                b"\x00")
            mini += padded
            n = len(padded) // MINI_SECTOR_SIZE
            base = e.start
            for k in range(n):
                minifat.append(ENDOFCHAIN if k == n - 1 else base + k + 1)

        self.root.size = len(mini)
        self.root.start = self._alloc(bytes(mini))

        if minifat:
            mf = b"".join(struct.pack("<I", v) for v in minifat)
            pad = (-len(mf)) % SECTOR_SIZE
            mf += struct.pack("<I", FREESECT) * (pad // 4)
            first_minifat = self._alloc(mf)
            n_minifat = len(mf) // SECTOR_SIZE
        else:
            first_minifat = ENDOFCHAIN
            n_minifat = 0

        first_dir = self._alloc(self._dir_bytes(flat))

        # how many FAT sectors do we need, counting the FAT sectors themselves
        n_data = len(self._sectors)
        n_fat = 0
        while True:
            total = n_data + n_fat
            need = (total + FAT_PER_SECTOR - 1) // FAT_PER_SECTOR
            if need == n_fat:
                break
            n_fat = need
        if n_fat > 109:
            raise ValueError("file would need DIFAT sectors")

        fat_ids = []
        for _ in range(n_fat):
            self._sectors.append(b"\x00" * SECTOR_SIZE)
            self._fat.append(FATSECT)
            fat_ids.append(len(self._sectors) - 1)

        fat_entries = list(self._fat)
        while len(fat_entries) % FAT_PER_SECTOR:
            fat_entries.append(FREESECT)
        fat_raw = b"".join(struct.pack("<I", v) for v in fat_entries)
        for k, sid in enumerate(fat_ids):
            self._sectors[sid] = fat_raw[k * SECTOR_SIZE:(k + 1) * SECTOR_SIZE]

        header = bytearray()
        header += b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        header += b"\x00" * 16
        header += struct.pack("<HHH", 0x003E, 0x0003, 0xFFFE)
        header += struct.pack("<HH", 9, 6)
        header += b"\x00" * 6
        header += struct.pack("<I", 0)            # NumDirectorySectors (v3: 0)
        header += struct.pack("<I", n_fat)
        header += struct.pack("<I", first_dir)
        header += struct.pack("<I", 0)            # transaction signature
        header += struct.pack("<I", MINI_CUTOFF)
        header += struct.pack("<I", first_minifat)
        header += struct.pack("<I", n_minifat)
        header += struct.pack("<I", ENDOFCHAIN)   # first DIFAT sector
        header += struct.pack("<I", 0)            # number of DIFAT sectors
        difat = fat_ids + [FREESECT] * (109 - n_fat)
        header += b"".join(struct.pack("<I", v) for v in difat)
        assert len(header) == SECTOR_SIZE, len(header)

        return bytes(header) + b"".join(self._sectors)
