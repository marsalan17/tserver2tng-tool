# TServer to TNG Test Translator Tool

A tool for translating GPU diagnostic tests from **TServer** (`diag_gpu_ariel`) to **TNG** (`diag_tng_canis`).

**Version**: 1.0.0

## Quick Start

```bash
cd /data/armuhamm/workspace/tserver2tng_tool

# 1. Discover available IPs in YOUR TServer source (REQUIRED: provide your path)
/usr/bin/python3 main.py ips --tserver-path /your/path/diag_gpu_ariel

# 2. List tests for a specific IP
/usr/bin/python3 main.py ip display --list --tserver-path /your/path/diag_gpu_ariel

# 3. Translate all tests for your IP (provide TNG path for output location guidance)
/usr/bin/python3 main.py ip gfx --tserver-path /your/path/diag_gpu_ariel --tng-path /your/path/diag_tng_canis -o output_dir
```

## Required Paths

**You MUST provide your source paths when using this tool:**

| Path | Description | Example |
|------|-------------|---------|
| `--tserver-path` | Path to your TServer source code (`diag_gpu_ariel`) | `/data/user/workspace/diag_gpu_ariel` |
| `--tng-path` | Path to your TNG source code (`diag_tng_canis`) - for output guidance | `/data/user/workspace/diag_tng_canis` |

### Why Paths Are Required

- Each user has their source code in different locations
- The tool dynamically scans your source to discover available IPs
- The TNG path tells you where to place translated test files

## Supported IP Blocks

| IP | Feature | TServer Suites |
|----|---------|----------------|
| `gfx` | Graphics Core | gfxutil, stress3d, raytracing |
| `display` | Display/DCN | display, dpp, mpc, otg, dsc, dout, dmu, dwb |
| `vcn` | Video Codec | vcn |
| `memory` | Memory Controller | umc, hdp |
| `sdma` | SDMA Engine | sdma, nsdma |
| `pm` | Power Management | pm |
| `pcie` | PCIe | pcie |
| `iommu` | IOMMU | iommu, iohc |
| `security` | Security/PSP | asp, pspif |
| `df` | Data Fabric | df |
| `acp` | Audio | acp_az |
| `phy` | PHY | phy |
| `framework` | Framework | fss, tcore2 |

## Commands

### `ips` - Discover IPs from Your TServer Source
```bash
# Scan your TServer source to see what IP suites are available
/usr/bin/python3 main.py ips --tserver-path /path/to/diag_gpu_ariel
```

### `ip` - IP-Specific Operations
```bash
# List tests for an IP
/usr/bin/python3 main.py ip gfx --list --tserver-path /path/to/diag_gpu_ariel

# Translate all tests for an IP (with TNG path for guidance)
/usr/bin/python3 main.py ip vcn --tserver-path /path/to/diag_gpu_ariel --tng-path /path/to/diag_tng_canis -o vcn_output
```

### `translate` - Single Test
```bash
/usr/bin/python3 main.py translate /path/to/test.cpp --ai-context
```

### `batch` - Batch Process Directory
```bash
/usr/bin/python3 main.py batch /path/to/suite -o output_dir
```

### `list` - Discover Tests
```bash
/usr/bin/python3 main.py list /path/to/suite/gpu/fss
```

## Output Files

| File | Description |
|------|-------------|
| `*_spec.yaml` | Test specification (parameters, variations) |
| `*_tng_test.cpp` | Generated TNG test skeleton |
| `*_ai_context.md` | AI context for Claude/GPT assisted translation |
| `translation_report.md` | Batch processing summary |

## Using AI Context for Translation

1. Generate with: `--ai-context` flag
2. Open the generated `*_ai_context.md` file
3. Copy to Claude/GPT/Cursor
4. Ask: "Please translate variation 1 to TNG format"
5. Review and integrate the code

## Examples by IP

### GFX
```bash
/usr/bin/python3 main.py ip gfx --list --tserver-path /data/user/diag_gpu_ariel
/usr/bin/python3 main.py ip gfx --tserver-path /data/user/diag_gpu_ariel -o gfx_tng
```

### Display
```bash
/usr/bin/python3 main.py ip display --list --tserver-path /data/user/diag_gpu_ariel
/usr/bin/python3 main.py ip display --tserver-path /data/user/diag_gpu_ariel -o display_tng
```

### VCN
```bash
/usr/bin/python3 main.py ip vcn --list --tserver-path /data/user/diag_gpu_ariel
/usr/bin/python3 main.py ip vcn --tserver-path /data/user/diag_gpu_ariel -o vcn_tng
```

## File Structure

```
tserver2tng_tool/
├── main.py              # Main CLI
├── spec_extractor.py    # TServer parser
├── tng_generator.py     # TNG code generator
├── ai_translator.py     # AI context generator
├── batch_processor.py   # Batch processing
├── api_mappings.yaml    # API translation rules
├── config.yaml          # IP configurations (customize paths here)
├── requirements.txt     # Dependencies
└── README.md            # This file
```

## Adding a New IP

Edit `config.yaml` and add your IP under `ip_blocks`:

```yaml
ip_blocks:
  my_new_ip:
    tserver_suites:
      - "suite/gpu/my_suite"
    tng_output: "engine/my_ip/test"
    feature: "my_feature"
    sub_characteristics:
      - "sub1"
      - "sub2"
```

## Support

For issues or enhancements, contact the GPU Diagnostics team.
