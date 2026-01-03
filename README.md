# TServer to TNG Test Translator Tool

A tool for translating GPU diagnostic tests from **TServer** (`diag_gpu_ariel`) to **TNG** (`diag_tng_canis`).

**Version**: 1.0.0

## Quick Start

```bash
cd /data/armuhamm/workspace/tserver2tng_tool

# 1. See all available IPs
/usr/bin/python3 main.py ips

# 2. List tests for your IP (specify your source path)
/usr/bin/python3 main.py ip gfx --list --tserver-path /your/path/diag_gpu_ariel

# 3. Translate all tests for your IP
/usr/bin/python3 main.py ip gfx --tserver-path /your/path/diag_gpu_ariel -o output_dir
```

## Setting Up Your Source Path

Each user has their source code in different locations. You can specify it in two ways:

### Option 1: Command Line (Recommended)
```bash
/usr/bin/python3 main.py ip display --tserver-path /home/myuser/workspace/diag_gpu_ariel
```

### Option 2: Edit config.yaml
```yaml
paths:
  tserver_base: "/your/workspace/diag_gpu_ariel"
```

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

### `ips` - List All IPs
```bash
/usr/bin/python3 main.py ips
```

### `ip` - IP-Specific Operations
```bash
# List tests for an IP
/usr/bin/python3 main.py ip gfx --list --tserver-path /path/to/diag_gpu_ariel

# Translate all tests for an IP
/usr/bin/python3 main.py ip vcn --tserver-path /path/to/diag_gpu_ariel -o vcn_output
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
