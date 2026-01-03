#!/usr/bin/env python3
"""
Batch Processor for TServer to TNG Translation

This module provides batch processing capabilities for translating
multiple TServer tests to TNG format.

Usage:
    python batch_processor.py /path/to/suite/gpu --output /path/to/output
    python batch_processor.py --list /path/to/suite/gpu
"""

import os
import sys
import json
import glob
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from spec_extractor import TServerExtractor
from tng_generator import TNGGenerator
from ai_translator import AITranslator


@dataclass
class TestInfo:
    """Information about a discovered test"""
    cpp_file: str
    xml_file: Optional[str]
    suite_name: str
    test_name: str
    class_name: str
    num_variations: int
    num_parameters: int
    has_tcore: bool
    has_register_access: bool
    has_memory_ops: bool


@dataclass
class TranslationResult:
    """Result of a test translation"""
    cpp_file: str
    success: bool
    spec_file: Optional[str] = None
    tng_file: Optional[str] = None
    context_file: Optional[str] = None
    error: Optional[str] = None


class BatchProcessor:
    """Batch processor for TServer tests"""
    
    def __init__(self, output_dir: str = "tng_output"):
        """
        Initialize the batch processor.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def discover_tests(self, search_dir: str, pattern: str = "*.cpp") -> List[TestInfo]:
        """
        Discover TServer tests in a directory.
        
        Args:
            search_dir: Directory to search
            pattern: Glob pattern for test files
            
        Returns:
            List of TestInfo objects
        """
        tests = []
        
        # Find all cpp files
        search_path = Path(search_dir)
        cpp_files = list(search_path.rglob(pattern))
        
        for cpp_file in cpp_files:
            # Check if it's a TServer test
            if self._is_tserver_test(str(cpp_file)):
                test_info = self._analyze_test(str(cpp_file))
                if test_info:
                    tests.append(test_info)
        
        return tests
    
    def _is_tserver_test(self, cpp_file: str) -> bool:
        """Check if a file is a TServer test"""
        try:
            with open(cpp_file, 'r') as f:
                content = f.read()
                # Check for TServer markers
                return (
                    'ts::Test' in content or
                    'TServerTestInstance' in content or
                    'ts::TestFactory' in content
                )
        except Exception:
            return False
    
    def _analyze_test(self, cpp_file: str) -> Optional[TestInfo]:
        """Analyze a TServer test file"""
        try:
            # Find corresponding XML
            cpp_path = Path(cpp_file)
            xml_files = list(cpp_path.parent.glob("*.xml"))
            xml_file = str(xml_files[0]) if xml_files else None
            
            # Extract basic info
            extractor = TServerExtractor(cpp_file, xml_file)
            spec = extractor.extract()
            
            # Check for specific APIs
            with open(cpp_file, 'r') as f:
                content = f.read()
            
            has_tcore = 'TcoreInterface' in content or 'TCORE_NAME' in content
            has_register = 'RegRead' in content or 'RegWrite' in content
            has_memory = 'palloc' in content or 'pfree' in content
            
            return TestInfo(
                cpp_file=cpp_file,
                xml_file=xml_file,
                suite_name=spec.suite_id,
                test_name=spec.test_name or cpp_path.stem,
                class_name=spec.class_name,
                num_variations=len(spec.variations),
                num_parameters=len(spec.parameters),
                has_tcore=has_tcore,
                has_register_access=has_register,
                has_memory_ops=has_memory
            )
        except Exception as e:
            print(f"Warning: Could not analyze {cpp_file}: {e}")
            return None
    
    def translate_test(self, cpp_file: str, xml_file: str = None,
                       generate_context: bool = True) -> TranslationResult:
        """
        Translate a single TServer test to TNG.
        
        Args:
            cpp_file: Path to TServer .cpp file
            xml_file: Path to TServer .xml file (optional)
            generate_context: Whether to generate AI context file
            
        Returns:
            TranslationResult object
        """
        try:
            cpp_path = Path(cpp_file)
            base_name = cpp_path.stem
            
            # Create output subdirectory
            output_subdir = os.path.join(self.output_dir, base_name)
            os.makedirs(output_subdir, exist_ok=True)
            
            # Step 1: Extract specification
            extractor = TServerExtractor(cpp_file, xml_file)
            spec = extractor.extract()
            
            spec_file = os.path.join(output_subdir, f"{base_name}_spec.yaml")
            extractor.save_spec(spec_file)
            
            # Step 2: Generate TNG code
            generator = TNGGenerator(spec_file)
            tng_file = os.path.join(output_subdir, f"{base_name}_tng_test.cpp")
            generator.generate(tng_file)
            
            # Step 3: Generate AI context (optional)
            context_file = None
            if generate_context:
                translator = AITranslator(spec_file, cpp_file)
                context_file = os.path.join(output_subdir, f"{base_name}_ai_context.md")
                translator.generate_context_file(context_file)
            
            return TranslationResult(
                cpp_file=cpp_file,
                success=True,
                spec_file=spec_file,
                tng_file=tng_file,
                context_file=context_file
            )
            
        except Exception as e:
            return TranslationResult(
                cpp_file=cpp_file,
                success=False,
                error=str(e)
            )
    
    def translate_batch(self, tests: List[TestInfo], 
                        max_workers: int = 4,
                        generate_context: bool = True) -> List[TranslationResult]:
        """
        Translate multiple tests in parallel.
        
        Args:
            tests: List of TestInfo objects
            max_workers: Maximum parallel workers
            generate_context: Whether to generate AI context files
            
        Returns:
            List of TranslationResult objects
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.translate_test,
                    test.cpp_file,
                    test.xml_file,
                    generate_context
                ): test for test in tests
            }
            
            for future in as_completed(futures):
                test = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    status = "✓" if result.success else "✗"
                    print(f"  {status} {test.test_name}")
                except Exception as e:
                    results.append(TranslationResult(
                        cpp_file=test.cpp_file,
                        success=False,
                        error=str(e)
                    ))
                    print(f"  ✗ {test.test_name}: {e}")
        
        return results
    
    def generate_report(self, tests: List[TestInfo], 
                        results: List[TranslationResult],
                        output_file: str = None) -> str:
        """Generate a summary report"""
        output_file = output_file or os.path.join(self.output_dir, "translation_report.md")
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        report = []
        report.append("# TServer to TNG Translation Report\n")
        report.append(f"## Summary\n")
        report.append(f"- **Total Tests**: {len(tests)}")
        report.append(f"- **Successful**: {len(successful)}")
        report.append(f"- **Failed**: {len(failed)}")
        report.append(f"- **Output Directory**: `{self.output_dir}`\n")
        
        # Test breakdown by features
        report.append("## Test Analysis\n")
        report.append("| Test | Suite | Variations | TCore | RegAccess | Memory |")
        report.append("|------|-------|------------|-------|-----------|--------|")
        
        for test in tests:
            tcore = "✓" if test.has_tcore else ""
            reg = "✓" if test.has_register_access else ""
            mem = "✓" if test.has_memory_ops else ""
            report.append(f"| {test.test_name} | {test.suite_name} | {test.num_variations} | {tcore} | {reg} | {mem} |")
        
        report.append("\n## Translation Results\n")
        
        if successful:
            report.append("### Successful Translations\n")
            for result in successful:
                name = Path(result.cpp_file).stem
                report.append(f"- **{name}**")
                report.append(f"  - Spec: `{result.spec_file}`")
                report.append(f"  - TNG: `{result.tng_file}`")
                if result.context_file:
                    report.append(f"  - AI Context: `{result.context_file}`")
        
        if failed:
            report.append("\n### Failed Translations\n")
            for result in failed:
                name = Path(result.cpp_file).stem
                report.append(f"- **{name}**: {result.error}")
        
        report.append("\n## Next Steps\n")
        report.append("1. Review generated specifications (`.yaml` files)")
        report.append("2. Edit feature/sub_characteristic in specs")
        report.append("3. Use AI context files (`.md`) with Claude/GPT for implementation help")
        report.append("4. Implement TODO sections in generated TNG tests")
        report.append("5. Add tests to TNG CMakeLists.txt")
        
        report_text = "\n".join(report)
        
        with open(output_file, 'w') as f:
            f.write(report_text)
        
        print(f"\nReport saved: {output_file}")
        return report_text


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Batch process TServer tests for TNG translation'
    )
    parser.add_argument('input', nargs='?', help='Input directory or file')
    parser.add_argument('--output', '-o', default='tng_output', help='Output directory')
    parser.add_argument('--list', '-l', action='store_true', help='List discovered tests only')
    parser.add_argument('--pattern', '-p', default='*.cpp', help='File pattern to match')
    parser.add_argument('--no-context', action='store_true', help='Skip AI context generation')
    parser.add_argument('--workers', '-w', type=int, default=4, help='Parallel workers')
    parser.add_argument('--suite', '-s', help='Filter by suite name')
    
    args = parser.parse_args()
    
    if not args.input:
        parser.print_help()
        return
    
    processor = BatchProcessor(args.output)
    
    print(f"\n{'='*60}")
    print("TServer to TNG Batch Processor")
    print(f"{'='*60}")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    
    # Discover tests
    print(f"\nDiscovering tests...")
    
    if os.path.isfile(args.input):
        # Single file
        tests = []
        test_info = processor._analyze_test(args.input)
        if test_info:
            tests.append(test_info)
    else:
        # Directory
        tests = processor.discover_tests(args.input, args.pattern)
    
    # Filter by suite if specified
    if args.suite:
        tests = [t for t in tests if args.suite.lower() in t.suite_name.lower()]
    
    print(f"Found {len(tests)} TServer tests\n")
    
    if args.list:
        # List mode
        print("Discovered Tests:")
        print("-" * 80)
        print(f"{'Test Name':<30} {'Suite':<10} {'Vars':<6} {'Params':<8} {'Features'}")
        print("-" * 80)
        
        for test in tests:
            features = []
            if test.has_tcore:
                features.append("TCore")
            if test.has_register_access:
                features.append("Reg")
            if test.has_memory_ops:
                features.append("Mem")
            
            print(f"{test.test_name:<30} {test.suite_name:<10} {test.num_variations:<6} {test.num_parameters:<8} {', '.join(features)}")
        
        return
    
    # Translation mode
    print("Translating tests...")
    results = processor.translate_batch(
        tests,
        max_workers=args.workers,
        generate_context=not args.no_context
    )
    
    # Generate report
    processor.generate_report(tests, results)
    
    # Summary
    successful = sum(1 for r in results if r.success)
    print(f"\n{'='*60}")
    print(f"Completed: {successful}/{len(tests)} tests translated successfully")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()

