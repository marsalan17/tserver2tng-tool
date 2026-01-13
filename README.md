# TServer to TNG Test Translator Tool

A tool for translating GPU diagnostic tests from **TServer** (`diag_gpu_ariel`) to **TNG** (`diag_tng`).

**Version**: 2.0.0

---

## Quick Start

```bash
cd /data/armuhamm/workspace/tserver2tng_tool

# 1. Discover available IPs in your TServer source
python main.py ips --tserver-path /path/to/diag_gpu_ariel

# 2. List tests for a specific IP
python main.py ip display --list --tserver-path /path/to/diag_gpu_ariel

# 3. Translate a specific test
python main.py translate /path/to/test.cpp --tng-path /path/to/diag_tng
```

---

## Commands

### 1. `ips` - Discover Available IPs

Scans your TServer source to find all available IP test suites.

```bash
python main.py ips --tserver-path /data/armuhamm/workspace/diag_gpu_ariel
```

**Output:**
```
============================================================
Discovering IP Blocks from TServer Source
============================================================

TServer Path: /data/armuhamm/workspace/diag_gpu_ariel

IP Suite             Category   Tests    Path
------------------------------------------------------------------------
display              gpu        15       suite/gpu/display
mpc                  gpu        8        suite/gpu/mpc
vcn                  gpu        12       suite/gpu/vcn
...

Found 25 IP suites
```

---

### 2. `ip --list` - List Tests for an IP

Lists all test files for a specific IP block.

```bash
python main.py ip display --list --tserver-path /data/armuhamm/workspace/diag_gpu_ariel
python main.py ip mpc --list --tserver-path /data/armuhamm/workspace/diag_gpu_ariel
```

**Output:**
```
============================================================
Tests for IP: MPC
============================================================

TServer Path: /data/armuhamm/workspace/diag_gpu_ariel
Suites: suite/gpu/mpc

Found 8 tests:

#    Test Name                                File
--------------------------------------------------------------------------------
1    MpccModeTest                             mpcc_mode_test.cpp
2    MpccSrcDstMuxTest                        mpcc_src_dst_mux_test.cpp
...
```

---

### 3. `translate` - Translate a Test

Translates a specific TServer test file to TNG format.

```bash
python main.py translate /path/to/test.cpp --tng-path /path/to/diag_tng
```

**Example:**
```bash
python main.py translate \
    /data/armuhamm/workspace/diag_gpu_ariel/suite/gpu/mpc/mpcc_mode_test.cpp \
    --tng-path /data/armuhamm/workspace/diag_tng.github
```

**Output:**
```
============================================================
TServer to TNG Test Translation
============================================================

Source: /data/armuhamm/workspace/diag_gpu_ariel/suite/gpu/mpc/mpcc_mode_test.cpp
TNG Reference Found: /data/armuhamm/workspace/diag_tng.github/engine/display/test/stimulus/mpc/mpcc_mode_stimulus.cpp

[Step 1/3] Extracting specification...
  Specification: mpcc_mode_test_spec.yaml
  - Parameters: 8
  - Variations: 22

[Step 2/3] Generating TNG test skeleton...
  TNG Skeleton: mpcc_mode_test_tng.cpp

[Step 3/3] Generating AI translation context...
  AI Context: mpcc_mode_test_ai_context.md

============================================================
Translation Complete!
============================================================

Generated Files:
  1. mpcc_mode_test_spec.yaml
  2. mpcc_mode_test_tng.cpp
  3. mpcc_mode_test_ai_context.md

TNG Reference Test:
  /data/armuhamm/workspace/diag_tng.github/engine/display/test/stimulus/mpc/mpcc_mode_stimulus.cpp

  The AI context includes this existing TNG test as a reference.
  Use it to understand the TNG patterns and conventions.
```

---

## Output Files

| File | Description |
|------|-------------|
| `*_spec.yaml` | Extracted test specification (parameters, variations) |
| `*_tng.cpp` | Generated TNG test skeleton (starting template) |
| `*_ai_context.md` | AI context for Claude/GPT assisted translation |

---

## Using the AI Context

The `*_ai_context.md` file contains everything needed for AI-assisted translation:

1. **Open the file** in your editor
2. **Copy the entire content** to Claude, GPT, or Cursor
3. **Ask specific questions** like:
   - "Translate the Main() function to TNG format"
   - "Convert variation 3 using the TNG reference as a guide"
   - "How should I handle the memory allocation?"
4. **Review and integrate** the generated code

### If TNG Reference is Found

When the tool finds an existing TNG test that corresponds to your TServer test, it includes the full TNG code in the AI context. This is extremely helpful because:

- You can see exact patterns used in your codebase
- The AI can match the coding style
- API usage examples are real and tested

---

## TNG Reference Lookup

The tool automatically searches for corresponding TNG tests using these patterns:

| TServer Path | TNG Search Patterns |
|--------------|---------------------|
| `suite/gpu/mpc/mpcc_mode_test.cpp` | `engine/*/test/stimulus/mpc/mpcc_mode*.cpp` |
| | `engine/*/test/mpc/mpcc_mode*.cpp` |
| | `**/mpcc_mode*.cpp` |

---

## Supported IP Blocks

The tool recognizes these IP blocks (configured in `config.yaml`):

| IP | TServer Suites | TNG Location |
|----|----------------|--------------|
| `display` | display, dpp, mpc, otg, dsc, dout | engine/display/test |
| `gfx` | gfxutil, stress3d, raytracing | engine/gfx/test |
| `vcn` | vcn | engine/vcn/test |
| `memory` | umc, hdp | engine/memorysubsystem/test |
| `sdma` | sdma, nsdma | engine/gfx/sdma/test |
| `pm` | pm | engine/pmm/test |
| `pcie` | pcie | engine/pci/test |
| `iommu` | iommu, iohc | engine/iohub/test |
| `security` | asp, pspif | engine/securitylib/test |
| `df` | df | engine/support/test |

---

## File Structure

```
tserver2tng_tool/
├── main.py              # Main CLI (3 commands: ips, ip, translate)
├── spec_extractor.py    # TServer test parser
├── tng_generator.py     # TNG skeleton generator
├── ai_translator.py     # AI context generator
├── batch_processor.py   # Test discovery helper
├── api_mappings.yaml    # API translation rules
├── config.yaml          # IP block configurations
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## Requirements

- Python 3.8+
- PyYAML

```bash
pip install -r requirements.txt
```

---

## Support

For issues or enhancements, contact the GPU Diagnostics team.
