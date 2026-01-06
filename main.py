#!/usr/bin/env python3
"""
TServer to TNG Test Translator Tool

This tool helps translate TServer test cases to TNG format by:
1. Extracting a specification from TServer test files
2. Generating TNG test code from the specification
3. Generating AI-powered translation prompts
4. Batch processing multiple tests

Usage:
    # Extract specification only
    python main.py extract <tserver_cpp> [--xml <xml_file>] [-o output.yaml]
    
    # Generate TNG code from specification
    python main.py generate <spec.yaml> [-o output.cpp]
    
    # Full pipeline: extract and generate
    python main.py translate <tserver_cpp> [--xml <xml_file>] [-o output.cpp]
    
    # Generate AI context for a test
    python main.py ai-context <spec.yaml> <tserver_cpp> [-o context.md]
    
    # Batch process multiple tests
    python main.py batch <suite_dir> [-o output_dir]
    
    # List tests in a directory
    python main.py list <suite_dir>

Examples:
    # Extract spec from a TServer test
    python main.py extract /path/to/suite/gpu/fss/palloc_pfree_test.cpp
    
    # Generate TNG test from spec
    python main.py generate test_spec.yaml -o new_test.cpp
    
    # Full translation with AI context
    python main.py translate /path/to/test.cpp --ai-context
    
    # Batch translate entire suite
    python main.py batch /path/to/suite/gpu/fss -o tng_fss_tests
"""

import argparse
import os
import sys
import yaml
from pathlib import Path

from spec_extractor import TServerExtractor
from tng_generator import TNGGenerator
from ai_translator import AITranslator
from batch_processor import BatchProcessor


# Tool version
__version__ = "1.0.0"

# Default config file path
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


def cmd_extract(args):
    """Handle extract command"""
    print(f"\n{'='*60}")
    print("TServer Test Specification Extractor")
    print(f"{'='*60}")
    print(f"Input CPP: {args.cpp_file}")
    print(f"Input XML: {args.xml or 'Auto-detect'}")
    
    extractor = TServerExtractor(args.cpp_file, args.xml)
    spec = extractor.extract()
    
    output_file = args.output or "test_spec.yaml"
    extractor.save_spec(output_file)
    
    print(f"\n{'='*60}")
    print("Extraction Summary")
    print(f"{'='*60}")
    print(f"Test Name:       {spec.test_name}")
    print(f"Class Name:      {spec.class_name}")
    print(f"Suite ID:        {spec.suite_id}")
    print(f"Suite Desc:      {spec.suite_description[:50]}..." if spec.suite_description else "Suite Desc:      N/A")
    print(f"Parameters:      {len(spec.parameters)}")
    print(f"Variations:      {len(spec.variations)}")
    print(f"API Calls:       {len(spec.api_calls)}")
    print(f"Includes:        {len(spec.includes)}")
    print(f"Member Vars:     {len(spec.member_variables)}")
    print(f"\nOutput: {output_file}")
    
    # Print detected variations
    if spec.variations:
        print(f"\nDetected Variations:")
        for var in spec.variations[:10]:  # Show first 10
            print(f"  {var.id}: {var.name} - {var.function_name}")
        if len(spec.variations) > 10:
            print(f"  ... and {len(spec.variations) - 10} more")
    
    return output_file


def cmd_generate(args):
    """Handle generate command"""
    print(f"\n{'='*60}")
    print("TNG Test Code Generator")
    print(f"{'='*60}")
    print(f"Input Spec: {args.spec_file}")
    
    generator = TNGGenerator(args.spec_file, args.mappings)
    
    output_file = args.output
    if not output_file:
        spec_name = os.path.splitext(os.path.basename(args.spec_file))[0]
        output_file = f"{spec_name}_tng_test.cpp"
    
    code = generator.generate(output_file)
    
    print(f"\n{'='*60}")
    print("Generation Summary")
    print(f"{'='*60}")
    print(f"Output: {output_file}")
    print(f"Lines:  {len(code.splitlines())}")
    
    return output_file


def cmd_translate(args):
    """Handle full translate command"""
    print(f"\n{'='*60}")
    print("TServer to TNG Full Translation")
    print(f"{'='*60}")
    
    # Step 1: Extract
    extractor = TServerExtractor(args.cpp_file, args.xml)
    spec = extractor.extract()
    
    # Generate intermediate spec file name
    cpp_name = os.path.splitext(os.path.basename(args.cpp_file))[0]
    spec_file = f"{cpp_name}_spec.yaml"
    extractor.save_spec(spec_file)
    print(f"\n[Step 1/3] Specification extracted: {spec_file}")
    
    # Step 2: Generate
    generator = TNGGenerator(spec_file, args.mappings)
    
    output_file = args.output
    if not output_file:
        output_file = f"{cpp_name}_tng_test.cpp"
    
    generator.generate(output_file)
    print(f"[Step 2/3] TNG test generated: {output_file}")
    
    # Step 3: Generate AI context (optional)
    context_file = None
    if getattr(args, 'ai_context', False):
        tng_path = getattr(args, 'tng_path', None)
        translator = AITranslator(spec_file, args.cpp_file, tng_path=tng_path)
        context_file = f"{cpp_name}_ai_context.md"
        translator.generate_context_file(context_file)
        print(f"[Step 3/3] AI context generated: {context_file}")
    else:
        print(f"[Step 3/3] AI context skipped (use --ai-context to enable)")
    
    print(f"\n{'='*60}")
    print("Translation Complete!")
    print(f"{'='*60}")
    print(f"Specification: {spec_file}")
    print(f"TNG Test:      {output_file}")
    if context_file:
        print(f"AI Context:    {context_file}")
    print(f"\nNext Steps:")
    print(f"  1. Review the specification: {spec_file}")
    print(f"  2. Edit the generated test: {output_file}")
    if context_file:
        print(f"  3. Use AI context with Claude/GPT for implementation help")
        print(f"  4. Implement TODO sections")
        print(f"  5. Add to TNG build system")
    else:
        print(f"  3. Implement TODO sections")
        print(f"  4. Add to TNG build system")
    
    return output_file


def cmd_ai_context(args):
    """Handle AI context generation"""
    print(f"\n{'='*60}")
    print("AI Context Generator")
    print(f"{'='*60}")
    
    tng_path = getattr(args, 'tng_path', None)
    tng_output_dir = getattr(args, 'tng_output', None)
    
    translator = AITranslator(args.spec_file, args.cpp_file, args.mappings, 
                              tng_path=tng_path, tng_output_dir=tng_output_dir)
    
    output_file = args.output
    if not output_file:
        spec_name = os.path.splitext(os.path.basename(args.spec_file))[0]
        output_file = f"{spec_name}_ai_context.md"
    
    translator.generate_context_file(output_file)
    
    print(f"\nAI Context file: {output_file}")
    if tng_path:
        print(f"TNG Source Path: {tng_path}")
    print(f"\nUsage:")
    print(f"  1. Copy the content of {output_file}")
    print(f"  2. Paste into Claude, GPT, or your preferred AI assistant")
    print(f"  3. Ask for specific variation translations")
    
    return output_file


def cmd_batch(args):
    """Handle batch processing"""
    print(f"\n{'='*60}")
    print("Batch Processing TServer Tests")
    print(f"{'='*60}")
    
    processor = BatchProcessor(args.output)
    
    # Discover tests
    print(f"\nDiscovering tests in: {args.input_dir}")
    tests = processor.discover_tests(args.input_dir)
    
    if args.suite:
        tests = [t for t in tests if args.suite.lower() in t.suite_name.lower()]
    
    print(f"Found {len(tests)} TServer tests\n")
    
    if not tests:
        print("No tests found!")
        return
    
    # Translate
    print("Translating tests...")
    results = processor.translate_batch(
        tests,
        max_workers=args.workers,
        generate_context=not args.no_context
    )
    
    # Generate report
    processor.generate_report(tests, results)
    
    successful = sum(1 for r in results if r.success)
    print(f"\n{'='*60}")
    print(f"Completed: {successful}/{len(tests)} tests translated")
    print(f"{'='*60}")


def cmd_list(args):
    """Handle list command"""
    print(f"\n{'='*60}")
    print("TServer Test Discovery")
    print(f"{'='*60}")
    
    processor = BatchProcessor()
    tests = processor.discover_tests(args.input_dir)
    
    if args.suite:
        tests = [t for t in tests if args.suite.lower() in t.suite_name.lower()]
    
    print(f"\nFound {len(tests)} TServer tests:\n")
    print(f"{'Test Name':<35} {'Suite':<12} {'Vars':<6} {'Features'}")
    print("-" * 70)
    
    for test in tests:
        features = []
        if test.has_tcore:
            features.append("TCore")
        if test.has_register_access:
            features.append("Reg")
        if test.has_memory_ops:
            features.append("Mem")
        
        print(f"{test.test_name:<35} {test.suite_name:<12} {test.num_variations:<6} {', '.join(features)}")


def cmd_ip(args):
    """Handle IP-based translation"""
    config = load_config()
    ip_config = get_ip_config(args.ip_name)
    
    if not ip_config:
        print(f"\nError: Unknown IP '{args.ip_name}'")
        print("\nAvailable IPs:")
        for ip in config.get('ip_blocks', {}).keys():
            print(f"  - {ip}")
        print("\nTip: Run 'python main.py ips --tserver-path /your/path' to discover IPs from your source")
        return
    
    print(f"\n{'='*60}")
    print(f"TServer to TNG Translation - {args.ip_name.upper()}")
    print(f"{'='*60}")
    
    # Use user-provided path or default from config
    tserver_base = args.tserver_path or config.get('paths', {}).get('tserver_base', '')
    tng_base = getattr(args, 'tng_path', None) or config.get('paths', {}).get('tng_base', '')
    
    if not tserver_base:
        print("\nError: TServer source path is REQUIRED!")
        print("\nUsage:")
        print(f"  python main.py ip {args.ip_name} --tserver-path /path/to/diag_gpu_ariel")
        print("\nExample:")
        print(f"  python main.py ip {args.ip_name} --tserver-path /data/user/workspace/diag_gpu_ariel")
        return
    
    if not os.path.exists(tserver_base):
        print(f"\nError: TServer path does not exist: {tserver_base}")
        return
    
    print(f"\nConfiguration:")
    print(f"  TServer Path: {tserver_base}")
    if tng_base:
        print(f"  TNG Path:     {tng_base}")
        tng_output_path = os.path.join(tng_base, ip_config.get('tng_output', ''))
        print(f"  TNG Output:   {tng_output_path}")
    else:
        print(f"  TNG Path:     Not specified (use --tng-path for output location guidance)")
        print(f"  TNG Output:   {ip_config.get('tng_output', 'N/A')}")
    print(f"  Feature:      {ip_config.get('feature', 'N/A')}")
    
    suites = ip_config.get('tserver_suites', [])
    print(f"\nTServer Suites ({len(suites)}):")
    for suite in suites:
        print(f"  - {suite}")
    
    if args.list_only:
        # Just list tests
        print(f"\n{'='*60}")
        print("Discovering tests...")
        
        all_tests = []
        processor = BatchProcessor()
        
        for suite in suites:
            suite_path = os.path.join(tserver_base, suite)
            if os.path.exists(suite_path):
                tests = processor.discover_tests(suite_path)
                all_tests.extend(tests)
        
        print(f"\nFound {len(all_tests)} tests for {args.ip_name}:\n")
        print(f"{'Test Name':<35} {'Suite':<12} {'Vars':<6}")
        print("-" * 60)
        
        for test in all_tests:
            print(f"{test.test_name:<35} {test.suite_name:<12} {test.num_variations:<6}")
        return
    
    # Batch translate
    output_dir = args.output or f"tng_{args.ip_name}_output"
    processor = BatchProcessor(output_dir)
    
    all_tests = []
    for suite in suites:
        suite_path = os.path.join(tserver_base, suite)
        if os.path.exists(suite_path):
            tests = processor.discover_tests(suite_path)
            all_tests.extend(tests)
            print(f"  Found {len(tests)} tests in {suite}")
        else:
            print(f"  Warning: Suite not found: {suite_path}")
    
    if not all_tests:
        print("\nNo tests found!")
        return
    
    print(f"\nTranslating {len(all_tests)} tests...")
    results = processor.translate_batch(
        all_tests,
        max_workers=config.get('output', {}).get('batch_workers', 4),
        generate_context=config.get('output', {}).get('generate_ai_context', True)
    )
    
    processor.generate_report(all_tests, results)
    
    successful = sum(1 for r in results if r.success)
    print(f"\n{'='*60}")
    print(f"Completed: {successful}/{len(all_tests)} tests translated")
    print(f"Output: {output_dir}/")
    print(f"{'='*60}")


def cmd_ips(args):
    """List all available IPs by scanning the TServer source directory"""
    tserver_path = args.tserver_path
    
    if not tserver_path:
        print("\n" + "="*60)
        print("ERROR: TServer source path is required!")
        print("="*60)
        print("\nUsage:")
        print("  python main.py ips --tserver-path /path/to/diag_gpu_ariel")
        print("\nExample:")
        print("  python main.py ips --tserver-path /data/user/workspace/diag_gpu_ariel")
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
        
        category = os.path.basename(suite_base)  # gpu, cpu, nbridge
        
        for item in os.listdir(suite_base):
            item_path = os.path.join(suite_base, item)
            if os.path.isdir(item_path):
                # Count test files
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
                        'has_cmake': os.path.exists(os.path.join(item_path, "CMakeLists.txt"))
                    }
    
    if not discovered_ips:
        print("\nNo IP suites found in the specified path.")
        print("Make sure the path points to the root of diag_gpu_ariel repository.")
        return
    
    # Group by category
    print(f"\n{'IP Suite':<20} {'Category':<10} {'Tests':<8} {'Path'}")
    print("-" * 80)
    
    for ip_name in sorted(discovered_ips.keys()):
        info = discovered_ips[ip_name]
        print(f"{ip_name:<20} {info['category']:<10} {info['test_files']:<8} {info['suite_path']}")
    
    print(f"\n{'='*60}")
    print(f"Found {len(discovered_ips)} IP suites in TServer source")
    print(f"{'='*60}")
    
    print(f"\nNext Steps:")
    print(f"  # List tests for a specific IP:")
    print(f"  python main.py ip <ip_name> --list --tserver-path {tserver_path}")
    print(f"\n  # Translate tests for an IP:")
    print(f"  python main.py ip <ip_name> --tserver-path {tserver_path} -o output_dir")
    print(f"\n  # Example:")
    print(f"  python main.py ip display --list --tserver-path {tserver_path}")


def cmd_interactive(args):
    """Interactive mode for exploring and translating tests"""
    print(f"\n{'='*60}")
    print("TServer to TNG Interactive Translator")
    print(f"{'='*60}")
    print("\nCommands:")
    print("  load <cpp_file>    - Load a TServer test file")
    print("  extract            - Extract specification")
    print("  show spec          - Show current specification")
    print("  show variations    - Show test variations")
    print("  show apis          - Show detected API calls")
    print("  generate           - Generate TNG test code")
    print("  save spec <file>   - Save specification to file")
    print("  help               - Show help")
    print("  quit               - Exit")
    
    extractor = None
    spec = None
    
    while True:
        try:
            cmd = input("\n> ").strip()
            if not cmd:
                continue
            
            parts = cmd.split()
            action = parts[0].lower()
            
            if action == 'quit' or action == 'exit':
                print("Goodbye!")
                break
            
            elif action == 'help':
                print("Commands: load, extract, show, generate, save, quit")
            
            elif action == 'load':
                if len(parts) < 2:
                    print("Usage: load <cpp_file>")
                    continue
                cpp_file = parts[1]
                if os.path.exists(cpp_file):
                    extractor = TServerExtractor(cpp_file)
                    print(f"Loaded: {cpp_file}")
                else:
                    print(f"File not found: {cpp_file}")
            
            elif action == 'extract':
                if not extractor:
                    print("No file loaded. Use 'load <cpp_file>' first.")
                    continue
                spec = extractor.extract()
                print(f"Extracted specification for: {spec.class_name}")
                print(f"  Parameters: {len(spec.parameters)}")
                print(f"  Variations: {len(spec.variations)}")
            
            elif action == 'show':
                if not spec:
                    print("No specification. Use 'extract' first.")
                    continue
                if len(parts) < 2:
                    print("Usage: show [spec|variations|apis|params]")
                    continue
                what = parts[1].lower()
                
                if what == 'spec':
                    print(f"\nTest: {spec.test_name}")
                    print(f"Class: {spec.class_name}")
                    print(f"Suite: {spec.suite_id}")
                    print(f"Description: {spec.suite_description}")
                
                elif what == 'variations':
                    print("\nVariations:")
                    for var in spec.variations:
                        print(f"  {var.id}: {var.name}")
                        print(f"      Function: {var.function_name}")
                        print(f"      Desc: {var.description}")
                
                elif what == 'apis':
                    print("\nDetected API Calls:")
                    seen = set()
                    for call in spec.api_calls:
                        key = call.context
                        if key not in seen:
                            seen.add(key)
                            print(f"  [{call.context}] {call.tserver_api[:60]}...")
                
                elif what == 'params':
                    print("\nParameters:")
                    for param in spec.parameters:
                        print(f"  {param.name}: {param.type}")
                        if param.description:
                            print(f"      {param.description}")
            
            elif action == 'generate':
                if not spec:
                    print("No specification. Use 'extract' first.")
                    continue
                
                # Save spec temporarily
                temp_spec = "/tmp/temp_spec.yaml"
                extractor.save_spec(temp_spec)
                
                # Generate
                generator = TNGGenerator(temp_spec)
                output = f"{spec.class_name.lower()}_tng_test.cpp"
                generator.generate(output)
                print(f"Generated: {output}")
            
            elif action == 'save':
                if not extractor:
                    print("No specification to save.")
                    continue
                if len(parts) < 3:
                    print("Usage: save spec <filename>")
                    continue
                filename = parts[2]
                extractor.save_spec(filename)
            
            else:
                print(f"Unknown command: {action}")
                print("Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit.")
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description=f'TServer to TNG Test Translator Tool v{__version__}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--version', '-V', action='version', version=f'%(prog)s {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # IPs command (list all IPs from source)
    ips_parser = subparsers.add_parser('ips', help='Discover IP blocks from TServer source')
    ips_parser.add_argument('--tserver-path', '-t', required=False, help='Path to TServer source (diag_gpu_ariel) - REQUIRED')
    
    # IP command (IP-specific operations)
    ip_parser = subparsers.add_parser('ip', help='Translate tests for a specific IP block')
    ip_parser.add_argument('ip_name', help='IP block name (e.g., gfx, display, vcn, memory)')
    ip_parser.add_argument('--list', '-l', dest='list_only', action='store_true', help='List tests only')
    ip_parser.add_argument('--output', '-o', help='Output directory')
    ip_parser.add_argument('--tserver-path', '-t', help='Path to TServer source (diag_gpu_ariel) - REQUIRED')
    ip_parser.add_argument('--tng-path', help='Path to TNG source (diag_tng_canis) - for output location guidance')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract specification from TServer test')
    extract_parser.add_argument('cpp_file', help='Path to TServer test .cpp file')
    extract_parser.add_argument('--xml', '-x', help='Path to TServer test .xml file')
    extract_parser.add_argument('--output', '-o', help='Output YAML file')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate TNG test from specification')
    gen_parser.add_argument('spec_file', help='Path to test specification YAML file')
    gen_parser.add_argument('--mappings', '-m', help='Path to API mappings YAML file')
    gen_parser.add_argument('--output', '-o', help='Output .cpp file')
    
    # Translate command (full pipeline)
    trans_parser = subparsers.add_parser('translate', help='Full translation from TServer to TNG')
    trans_parser.add_argument('cpp_file', help='Path to TServer test .cpp file')
    trans_parser.add_argument('--xml', '-x', help='Path to TServer test .xml file')
    trans_parser.add_argument('--mappings', '-m', help='Path to API mappings YAML file')
    trans_parser.add_argument('--output', '-o', help='Output .cpp file')
    trans_parser.add_argument('--ai-context', action='store_true', help='Generate AI context file')
    trans_parser.add_argument('--tng-path', help='Path to TNG source (diag_tng_canis) - for output location guidance')
    
    # AI Context command
    ai_parser = subparsers.add_parser('ai-context', help='Generate AI context for translation')
    ai_parser.add_argument('spec_file', help='Path to test specification YAML file')
    ai_parser.add_argument('cpp_file', help='Path to original TServer .cpp file')
    ai_parser.add_argument('--mappings', '-m', help='Path to API mappings YAML file')
    ai_parser.add_argument('--output', '-o', help='Output .md file')
    ai_parser.add_argument('--tng-path', help='Path to TNG source (diag_tng_canis) - for output location guidance')
    ai_parser.add_argument('--tng-output', help='Relative path within TNG for output (e.g., engine/display/test)')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Batch process multiple tests')
    batch_parser.add_argument('input_dir', help='Input directory containing TServer tests')
    batch_parser.add_argument('--output', '-o', default='tng_output', help='Output directory')
    batch_parser.add_argument('--suite', '-s', help='Filter by suite name')
    batch_parser.add_argument('--workers', '-w', type=int, default=4, help='Parallel workers')
    batch_parser.add_argument('--no-context', action='store_true', help='Skip AI context generation')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List TServer tests in a directory')
    list_parser.add_argument('input_dir', help='Directory to scan')
    list_parser.add_argument('--suite', '-s', help='Filter by suite name')
    
    # Interactive command
    inter_parser = subparsers.add_parser('interactive', help='Interactive exploration mode')
    
    args = parser.parse_args()
    
    if args.command == 'ips':
        cmd_ips(args)
    elif args.command == 'ip':
        cmd_ip(args)
    elif args.command == 'extract':
        cmd_extract(args)
    elif args.command == 'generate':
        cmd_generate(args)
    elif args.command == 'translate':
        cmd_translate(args)
    elif args.command == 'ai-context':
        cmd_ai_context(args)
    elif args.command == 'batch':
        cmd_batch(args)
    elif args.command == 'list':
        cmd_list(args)
    elif args.command == 'interactive':
        cmd_interactive(args)
    else:
        parser.print_help()
        print("\n" + "="*60)
        print("Quick Start")
        print("="*60)
        print("\n1. Discover available IPs in your TServer source:")
        print("   python main.py ips --tserver-path /path/to/diag_gpu_ariel")
        print("\n2. List tests for a specific IP:")
        print("   python main.py ip display --list --tserver-path /path/to/diag_gpu_ariel")
        print("   python main.py ip vcn --list --tserver-path /path/to/diag_gpu_ariel")
        print("\n3. Translate all tests for your IP:")
        print("   python main.py ip gfx --tserver-path /path/to/diag_gpu_ariel -o gfx_tng_tests")
        print("\n4. Translate a single test:")
        print("   python main.py translate /path/to/test.cpp --ai-context")
        print("\nIMPORTANT: Always provide --tserver-path with your source location!")
        print("\nFor more help on a specific command:")
        print("   python main.py <command> --help")


if __name__ == '__main__':
    main()

