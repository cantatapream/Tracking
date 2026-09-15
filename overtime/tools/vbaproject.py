"""Build a vbaProject.bin ([MS-OVBA]) holding one standard module plus the
document modules Excel expects (ThisWorkbook + one per worksheet)."""
import struct

import cfb
import ovba

CODEPAGE = 949            # Korean (the source contains Hangul literals)
ENC = "cp949"

LIBID_VBA = (r"*\G{000204EF-0000-0000-C000-000000000046}#4.2#9#"
             r"C:\PROGRA~2\COMMON~1\MICROS~1\VBA\VBA7.1\VBE7.DLL#Visual Basic For Applications")
LIBID_EXCEL = (r"*\G{00020813-0000-0000-C000-000000000046}#1.9#0#"
               r"C:\PROGRA~2\MICROS~1\Office16\EXCEL.EXE#Microsoft Excel 16.0 Object Library")
LIBID_STDOLE = (r"*\G{00020430-0000-0000-C000-000000000046}#2.0#0#"
                r"C:\Windows\SysWOW64\stdole2.tlb#OLE Automation")
LIBID_OFFICE = (r"*\G{2DF8D04C-5BFA-101B-BDE5-00AA0044DE52}#2.8#0#"
                r"C:\PROGRA~2\COMMON~1\MICROS~1\OFFICE16\MSO.DLL#Microsoft Office 16.0 Object Library")

BASE_WORKBOOK = "0{00020819-0000-0000-C000-000000000046}"
BASE_SHEET = "0{00020820-0000-0000-C000-000000000046}"


def _rec(rid, payload):
    return struct.pack("<HI", rid, len(payload)) + payload


def _pair(rid, text, rid_u):
    """A record carrying the MBCS text plus its UTF-16 twin."""
    mb = text.encode(ENC)
    uni = text.encode("utf-16-le")
    return (struct.pack("<HI", rid, len(mb)) + mb +
            struct.pack("<HI", rid_u, len(uni)) + uni)


def _reference(name, libid):
    out = _pair(0x0016, name, 0x003E)
    lib = libid.encode(ENC)
    inner = struct.pack("<I", len(lib)) + lib + struct.pack("<I", 0) + struct.pack("<H", 0)
    out += struct.pack("<HI", 0x000D, len(inner)) + inner
    return out


def _module_record(name, is_document):
    out = _pair(0x0019, name, 0x0047)            # MODULENAME (+ unicode)
    out += _pair(0x001A, name, 0x0032)           # MODULESTREAMNAME (+ unicode)
    out += _pair(0x001C, "", 0x0048)             # MODULEDOCSTRING (+ unicode)
    out += _rec(0x0031, struct.pack("<I", 0))    # MODULEOFFSET: no perf cache
    out += _rec(0x001E, struct.pack("<I", 0))    # MODULEHELPCONTEXT
    out += _rec(0x002C, struct.pack("<H", 0xFFFF))  # MODULECOOKIE
    out += _rec(0x0022 if is_document else 0x0021, b"")  # MODULETYPE
    out += _rec(0x002B, b"")                     # end of this module
    return out


def _dir_stream(project_name, modules):
    d = b""
    # --- PROJECTINFORMATION ---
    d += _rec(0x0001, struct.pack("<I", 1))          # SysKind: Win32
    d += _rec(0x0002, struct.pack("<I", 0x0409))     # Lcid
    d += _rec(0x0014, struct.pack("<I", 0x0409))     # LcidInvoke
    d += _rec(0x0003, struct.pack("<H", CODEPAGE))   # CodePage
    d += _rec(0x0004, project_name.encode(ENC))      # Name
    d += _pair(0x0005, "", 0x0040)                   # DocString
    d += _pair(0x0006, "", 0x003D)                   # HelpFilePath
    d += _rec(0x0007, struct.pack("<I", 0))          # HelpContext
    d += _rec(0x0008, struct.pack("<I", 0))          # LibFlags
    d += struct.pack("<HIIH", 0x0009, 4, 1, 1)       # Version
    d += _pair(0x000C, "", 0x003C)                   # Constants

    # --- PROJECTREFERENCES ---
    d += _reference("VBA", LIBID_VBA)
    d += _reference("Excel", LIBID_EXCEL)
    d += _reference("stdole", LIBID_STDOLE)
    d += _reference("Office", LIBID_OFFICE)

    # --- PROJECTMODULES ---
    d += _rec(0x000F, struct.pack("<H", len(modules)))
    d += _rec(0x0013, struct.pack("<H", 0xFFFF))     # PROJECTCOOKIE
    for name, _src, is_doc in modules:
        d += _module_record(name, is_doc)

    d += struct.pack("<HI", 0x0010, 0)               # Terminator
    return d


def _project_stream(project_name, modules):
    lines = ['ID="{5DD90D76-4B4A-44C1-94A1-2E0B7A2E9A31}"']
    for name, _src, is_doc in modules:
        if is_doc:
            lines.append("Document=%s/&H00000000" % name)
        else:
            lines.append("Module=%s" % name)
    lines += [
        'Name="%s"' % project_name,
        'HelpContextID="0"',
        'VersionCompatible32="393222000"',
        "",
        "[Host Extender Info]",
        "&H00000001={3832D640-CF90-11CF-8E43-00A0C911005A};VBE;&H00000000",
        "",
        "[Workspace]",
    ]
    for name, _src, _d in modules:
        lines.append("%s=0, 0, 0, 0, C" % name)
    return ("\r\n".join(lines) + "\r\n").encode(ENC)


def _projectwm_stream(modules):
    out = b""
    for name, _src, _d in modules:
        out += name.encode(ENC) + b"\x00" + name.encode("utf-16-le") + b"\x00\x00"
    return out + b"\x00\x00"


def document_module_source(name, is_workbook):
    base = BASE_WORKBOOK if is_workbook else BASE_SHEET
    return "\r\n".join([
        'Attribute VB_Name = "%s"' % name,
        'Attribute VB_Base = "%s"' % base,
        "Attribute VB_GlobalNameSpace = False",
        "Attribute VB_Creatable = False",
        "Attribute VB_PredeclaredId = True",
        "Attribute VB_Exposed = True",
        "Attribute VB_TemplateDerived = False",
        "Attribute VB_Customizable = True",
        "",
    ])


def build(project_name, modules):
    """modules: list of (name, source_text, is_document). Returns vbaProject.bin."""
    root = cfb.Entry("Root Entry", cfb.TYPE_ROOT)
    vba = root.add(cfb.Entry("VBA", cfb.TYPE_STORAGE))

    root.add(cfb.Entry("PROJECT", cfb.TYPE_STREAM,
                       _project_stream(project_name, modules)))
    root.add(cfb.Entry("PROJECTwm", cfb.TYPE_STREAM, _projectwm_stream(modules)))

    vba.add(cfb.Entry("_VBA_PROJECT", cfb.TYPE_STREAM,
                      b"\xcc\x61\xff\xff\x00\x00\x00"))
    vba.add(cfb.Entry("dir", cfb.TYPE_STREAM,
                      ovba.compress(_dir_stream(project_name, modules))))

    for name, src, _is_doc in modules:
        text = src.replace("\r\n", "\n").replace("\n", "\r\n")
        if not text.endswith("\r\n"):
            text += "\r\n"
        vba.add(cfb.Entry(name, cfb.TYPE_STREAM, ovba.compress(text.encode(ENC))))

    return cfb.CfbWriter(root).build()
