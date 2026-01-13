#!/usr/bin/env python3
"""
TServer to TNG Test Translator Tool (Simplified)

This tool helps translate TServer test cases to TNG format.

Usage:
    # 1. Discover available IPs in your TServer source
    python main.py ips --tserver-path /path/to/diag_gpu_ariel

    # 2. List tests for a specific IP
    python main.py ip display --list --tserver-path /path/to/diag_gpu_ariel

    # 3. Translate a specific test case
    python main.py translate /path/to/test.cpp --tng-path /path/to/diag_tng --ai-context

Examples:
    # Discover IPs
    python main.py ips --tserver-path /data/armuhamm/workspace/diag_gpu_ariel

    # List display tests
    python main.py ip display --list --tserver-path /data/armuhamm/workspace/diag_gpu_ariel

    # Translate a test (with TNG reference lookup)
    python main.py translate /data/armuhamm/workspace/diag_gpu_ariel/suite/gpu/mpc/mpcc_mode_test.cpp \\
        --tng-path /data/armuhamm/workspace/diag_tng.github \\
        --ai-context
"""

import argparse
import os
import sys
import yaml
import glob
from pathlib import Path

from spec_extractor import TServerExtractor
from tng_generator import TNGGenerator
from ai_translator import AITranslator
from batch_processor import BatchProcessor


__version__ = "2.0.0"

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.yaml")


def load_config():
    """Load configuration from config.yaml"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    return {}


def get_ip_config(ip_name: str):
    """Get configuration for a specific IP block"""
    config = load_config()
    ips = config.get('ip_blocks', {})
    return ips.get(ip_name.lower())


def find_tng_reference(tserver_cpp: str, tng_base: str) -> str:
    """
    Find the corresponding TNG test file for a TServer test.
    
    Mapping strategy:
    - TServer: suite/gpu/mpc/mpcc_mode_test.cpp
    - TNG patterns to search:
      1. engine/display/test/stimulus/mpc/mpcc_mode_stimulus.cpp
      2. engine/*/test/stimulus/*/mpcc_mode*.cpp
      3. engine/*/test/*/mpcc_mode*.cpp
    """
    if not tng_base or not os.path.exists(tng_base):
        return None
    
    # Extract test name from TServer path
    tserver_name = os.path.basename(tserver_cpp)
    test_base_name = tserver_name.replace('_test.cpp', '').replace('.cpp', '')
    
    # Extract suite name (e.g., 'mpc' from suite/gpu/mpc/)
    tserver_dir = os.path.dirname(tserver_cpp)
    suite_name = os.path.basename(tserver_dir)
    
    # Search patterns (ordered by likelihood)
    search_patterns = [
        # Exact match in stimulus folder
        f"engine/*/test/stimulus/{suite_name}/{test_base_name}*.cpp",
        f"engine/*/test/stimulus/*/{test_base_name}*.cpp",
        # Direct test folder
        f"engine/*/test/{suite_name}/{test_base_name}*.cpp",
        f"engine/*/test/*/{test_base_name}*.cpp",
        # Any match with test name
        f"engine/**/test/**/{test_base_name}*.cpp",
        # Broader search
        f"**/{test_base_name}*.cpp",
    ]
    
    for pattern in search_patterns:
        full_pattern = os.path.join(tng_base, pattern)
        matches = glob.glob(full_pattern, recursive=True)
        
        # Filter out build directories and non-test files
        matches = [m for m in matches if '/build/' not in m and '/_build/' not in m]
        
        if matches:
            # Prefer stimulus files
            stimulus_matches = [m for m in matches if 'stimulus' in m]
            if stimulus_matches:
                return stimulus_matches[0]
            return matches[0]
    
    return None


def cmd_ips(args):
    """List all available IPs by scanning the TServer source directory"""
    tserver_path = args.tserver_path
    
    if not tserver_path:
        print("\n" + "="*60)
        print("ERROR: TServer source path is required!")
        print("="*60)
        print("\nUsage:")
        print("  python main.py ips --tserver-path /path/to/diag_gpu_ariel")
        return
    
    if not os.path.exists(tserver_path):
        print(f"\nError: TServer path does not exist: {tserver_path}")
        return
    
    print(f"\n{'='*60}")
    print("Discovering IP Blocks from TServer Source")
    print(f"{'='*60}")
    print(f"\nTServer Path: {tserver_path}")
    
    # Scan for suite directories
    suite_dirs = [
        os.path.join(tserver_path, "suite/gpu"),
        os.path.join(tserver_path, "suite/cpu"),
        os.path.join(tserver_path, "suite/nbridge"),
    ]
    
    discovered_ips = {}
    
    for suite_base in suite_dirs:
        if not os.path.exists(suite_base):
            continue
        
        category = os.path.basename(suite_base)
        
        for item in os.listdir(suite_base):
            item_path = os.path.join(suite_base, item)
            if os.path.isdir(item_path):
                cpp_files = []
                for root, dirs, files in os.walk(item_path):
                    cpp_files.extend([f for f in files if f.endswith('.cpp') and 'test' in f.lower()])
                
                if cpp_files or os.path.exists(os.path.join(item_path, "CMakeLists.txt")):
                    suite_key = f"suite/{category}/{item}"
                    discovered_ips[item] = {
                        'category': category,
                        'suite_path': suite_key,
                        'full_path': item_path,
                        'test_files': len(cpp_files),
                    }
    
    if not discovered_ips:
        print("\nNo IP suites found.")
        return
    
    print(f"\n{'IP Suite':<20} {'Category':<10} {'Tests':<8} {'Path'}")
    print("-" * 70)
    
    for ip_name in sorted(discovered_ips.keys()):
        info = discovered_ips[ip_name]
        print(f"{ip_name:<20} {info['category']:<10} {info['test_files']:<8} {info['suite_path']}")
    
    print(f"\n{'='*60}")
    print(f"Found {len(discovered_ips)} IP suites")
    print(f"{'='*60}")
    
    print(f"\nNext Steps:")
    print(f"  # List tests for a specific IP:")
    print(f"  python main.py ip <ip_name> --list --tserver-path {tserver_path}")
    print(f"\n  # Translate a specific test:")
    print(f"  python main.py translate <path/to/test.cpp> --tng-path <path/to/diag_tng>")


def cmd_ip(args):
    """Handle IP-based test listing"""
    config = load_config()
    ip_config = get_ip_config(args.ip_name)
    
    if not ip_config:
        print(f"\nError: Unknown IP '{args.ip_name}'")
        print("\nAvailable IPs in config:")
        for ip in config.get('ip_blocks', {}).keys():
            print(f"  - {ip}")
        print("\nTip: Run 'python main.py ips --tserver-path /your/path' to discover IPs")
        return
    
    tserver_base = args.tserver_path or config.get('paths', {}).get('tserver_base', '')
    
    if not tserver_base:
        print("\nError: TServer source path is REQUIRED!")
        print(f"\nUsage:")
        print(f"  python main.py ip {args.ip_name} --list --tserver-path /path/to/diag_gpu_ariel")
        return
    
    if not os.path.exists(tserver_base):
        print(f"\nError: TServer path does not exist: {tserver_base}")
        return
    
    print(f"\n{'='*60}")
    print(f"Tests for IP: {args.ip_name.upper()}")
    print(f"{'='*60}")
    print(f"\nTServer Path: {tserver_base}")
    
    suites = ip_config.get('tserver_suites', [])
    print(f"Suites: {', '.join(suites)}")
    
    # Discover tests
    processor = BatchProcessor()
    all_tests = []
    
    for suite in suites:
        suite_path = os.path.join(tserver_base, suite)
        if os.path.exists(suite_path):
            tests = processor.discover_tests(suite_path)
            all_tests.extend(tests)
    
    if not all_tests:
        print("\nNo tests found!")
        return
    
    print(f"\nFound {len(all_tests)} tests:\n")
    print(f"{'#':<4} {'Test Name':<40} {'File'}")
    print("-" * 80)
    
    for i, test in enumerate(all_tests, 1):
        print(f"{i:<4} {test.test_name:<40} {os.path.basename(test.cpp_file)}")
    
    print(f"\n{'='*60}")
    print("To translate a test:")
    print(f"  python main.py translate <path/to/test.cpp> --tng-path <path/to/diag_tng>")


def cmd_translate(args):
    """Handle test translation with TNG reference lookup"""
    cpp_file = args.cpp_file
    tng_path = args.tng_path
    output_dir = args.output or os.path.dirname(cpp_file) or "."
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(cpp_file):
        print(f"\nError: TServer test file not found: {cpp_file}")
        return
    
    print(f"\n{'='*60}")
    print("TServer to TNG Test Translation")
    print(f"{'='*60}")
    print(f"\nSource: {cpp_file}")
    
    # Find corresponding TNG reference
    tng_reference = None
    if tng_path:
        tng_reference = find_tng_reference(cpp_file, tng_path)
        if tng_reference:
            print(f"TNG Reference Found: {tng_reference}")
        else:
            print(f"TNG Reference: Not found (will generate from scratch)")
    
    # Step 1: Extract specification
    print(f"\n[Step 1/3] Extracting specification...")
    extractor = TServerExtractor(cpp_file)
    spec = extractor.extract()
    
    cpp_name = os.path.splitext(os.path.basename(cpp_file))[0]
    spec_file = os.path.join(output_dir, f"{cpp_name}_spec.yaml")
    extractor.save_spec(spec_file)
    print(f"  Specification: {spec_file}")
    print(f"  - Parameters: {len(spec.parameters)}")
    print(f"  - Variations: {len(spec.variations)}")
    
    # Step 2: Generate TNG skeleton
    print(f"\n[Step 2/3] Generating TNG test skeleton...")
    generator = TNGGenerator(spec_file)
    output_cpp = os.path.join(output_dir, f"{cpp_name}_tng.cpp")
    generator.generate(output_cpp)
    print(f"  TNG Skeleton: {output_cpp}")
    
    # Step 3: Generate AI context (with TNG reference)
    print(f"\n[Step 3/3] Generating AI translation context...")
    context_file = os.path.join(output_dir, f"{cpp_name}_ai_context.md")
    
    translator = AITranslator(
        spec_file, 
        cpp_file, 
        tng_path=tng_path,
        tng_reference_file=tng_reference
    )
    translator.generate_context_file(context_file)
    print(f"  AI Context: {context_file}")
    
    # Summary
    print(f"\n{'='*60}")
    print("Translation Complete!")
    print(f"{'='*60}")
    
    print(f"\nGenerated Files:")
    print(f"  1. {spec_file}")
    print(f"  2. {output_cpp}")
    print(f"  3. {context_file}")
    
    if tng_reference:
        print(f"\nTNG Reference Test:")
        print(f"  {tng_reference}")
        print(f"\n  The AI context includes this existing TNG test as a reference.")
        print(f"  Use it to understand the TNG patterns and conventions.")
    
    print(f"\nNext Steps:")
    print(f"  1. Open {context_file}")
    print(f"  2. Copy the content to Claude/GPT")
    print(f"  3. Ask: 'Please translate variation X to TNG format'")
    print(f"  4. Review and integrate the translated code into {output_cpp}")
    
    if tng_reference:
        tng_dir = os.path.dirname(tng_reference)
        print(f"\n  5. Place final test in: {tng_dir}/")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description=f'TServer to TNG Test Translator Tool v{__version__}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--version', '-V', action='version', version=f'%(prog)s {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # ips command - Discover IPs
    ips_parser = subparsers.add_parser('ips', help='Discover IP blocks from TServer source')
    ips_parser.add_argument('--tserver-path', '-t', required=False, 
                           help='Path to TServer source (diag_gpu_ariel)')
    
    # ip command - List tests for an IP
    ip_parser = subparsers.add_parser('ip', help='List tests for a specific IP block')
    ip_parser.add_argument('ip_name', help='IP block name (e.g., display, mpc, vcn)')
    ip_parser.add_argument('--list', '-l', dest='list_tests', action='store_true', 
                          required=True, help='List tests for this IP')
    ip_parser.add_argument('--tserver-path', '-t', 
                          help='Path to TServer source (diag_gpu_ariel)')
    
    # translate command - Translate a specific test
    trans_parser = subparsers.add_parser('translate', help='Translate a TServer test to TNG')
    trans_parser.add_argument('cpp_file', help='Path to TServer test .cpp file')
    trans_parser.add_argument('--tng-path', '-n', 
                             help='Path to TNG source (diag_tng) - for finding reference tests')
    trans_parser.add_argument('--output', '-o', 
                             help='Output directory (default: same as source)')
    trans_parser.add_argument('--ai-context', action='store_true', 
                             help='Generate AI context file (default: True)', default=True)
    
    args = parser.parse_args()
    
    if args.command == 'ips':
        cmd_ips(args)
    elif args.command == 'ip':
        cmd_ip(args)
    elif args.command == 'translate':
        cmd_translate(args)
    else:
        parser.print_help()
        print("\n" + "="*60)
        print("Quick Start")
        print("="*60)
        print("\n1. Discover available IPs:")
        print("   python main.py ips --tserver-path /path/to/diag_gpu_ariel")
        print("\n2. List tests for an IP:")
        print("   python main.py ip display --list --tserver-path /path/to/diag_gpu_ariel")
        print("\n3. Translate a specific test:")
        print("   python main.py translate /path/to/test.cpp --tng-path /path/to/diag_tng")


if __name__ == '__main__':
    main()
