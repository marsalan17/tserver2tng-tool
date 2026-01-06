#!/usr/bin/env python3
"""
AI-Powered TServer to TNG Translator

This module generates detailed prompts for AI-assisted code translation.
It extracts the original TServer function implementations and creates
structured prompts that can be used with Claude, GPT, or other LLMs.

Usage:
    from ai_translator import AITranslator
    translator = AITranslator(spec_file, original_cpp)
    prompt = translator.generate_prompt(variation_id=1)
"""

import os
import re
import yaml
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class AITranslator:
    """Generates AI prompts for TServer to TNG translation"""
    
    def __init__(self, spec_file: str, original_cpp: str, mappings_file: str = None, 
                 tng_path: str = None, tng_output_dir: str = None):
        """
        Initialize the AI translator.
        
        Args:
            spec_file: Path to the test specification YAML
            original_cpp: Path to the original TServer .cpp file
            mappings_file: Path to API mappings YAML
            tng_path: Path to TNG source code (diag_tng_canis)
            tng_output_dir: Relative path within TNG for output (e.g., engine/display/test)
        """
        self.spec_file = spec_file
        self.original_cpp = original_cpp
        self.tng_path = tng_path
        self.tng_output_dir = tng_output_dir
        
        # Load specification
        with open(spec_file, 'r') as f:
            self.spec = yaml.safe_load(f)
        
        # Load original C++ code
        with open(original_cpp, 'r') as f:
            self.cpp_content = f.read()
        
        # Load mappings
        mappings_file = mappings_file or str(Path(__file__).parent / "api_mappings.yaml")
        with open(mappings_file, 'r') as f:
            self.mappings = yaml.safe_load(f)
    
    def extract_function(self, func_name: str) -> Optional[str]:
        """Extract a function implementation from the C++ file"""
        if not func_name:
            return None
        
        # Pattern to find function definition
        # Handles: void ClassName::funcName() { ... }
        class_name = self.spec.get('class_name', '')
        
        # Try class method first
        pattern = rf'(?:void|bool|int|[\w:]+)\s+{class_name}::{func_name}\s*\([^)]*\)\s*\{{([^}}]*(?:\{{[^}}]*\}}[^}}]*)*)\}}'
        match = re.search(pattern, self.cpp_content, re.DOTALL)
        
        if match:
            return match.group(0)
        
        # Try standalone function
        pattern = rf'(?:void|bool|int|[\w:]+)\s+{func_name}\s*\([^)]*\)\s*\{{([^}}]*(?:\{{[^}}]*\}}[^}}]*)*)\}}'
        match = re.search(pattern, self.cpp_content, re.DOTALL)
        
        if match:
            return match.group(0)
        
        return None
    
    def get_api_mappings_text(self) -> str:
        """Generate human-readable API mappings"""
        lines = []
        
        for section, mappings in self.mappings.items():
            if section in ['test_structure']:
                continue
            
            lines.append(f"\n### {section.replace('_', ' ').title()}")
            
            if isinstance(mappings, dict):
                for name, value in mappings.items():
                    if isinstance(value, dict):
                        tserver = value.get('tserver', '')
                        tng = value.get('tng', '')
                        if tserver and tng:
                            lines.append(f"- `{tserver}` → `{tng}`")
        
        return "\n".join(lines)
    
    def generate_prompt(self, variation_id: int = None) -> str:
        """
        Generate an AI prompt for translating a specific variation or the whole test.
        
        Args:
            variation_id: Specific variation to translate, or None for overview
        """
        class_name = self.spec.get('class_name', 'UnknownTest')
        suite_desc = self.spec.get('suite_description', '')
        
        prompt_parts = []
        
        # System context
        prompt_parts.append(f"""# TServer to TNG Test Translation Task

## Context
You are translating a GPU diagnostic test from TServer (legacy framework) to TNG (new framework).

**Source Test**: {class_name}
**Suite**: {suite_desc}
**Original File**: {self.original_cpp}

## Framework Differences

### TServer (Old)
- Base class: `ts::Test`
- Entry point: `Result Main()` with `switch(GetId())`
- Parameters: `Parameter<T>("name", default)`
- Logging: `CORE_LOG_DEBUG(m_lg) << "message"`
- Memory: `env::System::palloc()` / `env::System::pfree()`
- Result: Return `Pass` or `Fail`

### TNG (New)
- Base class: `tng::test::MonolithicTest`
- Entry point: `tng::test::Monitor run()`
- Parameters: `diag::value::ScalarValue<T>` structs with `k_TestCaseMap`
- Logging: `m_log.debug("message {{}}", value)`
- Memory: RAII with `localNode.allocateBuffer()`
- Result: Return `tng::test::Monitor` object

## API Mappings
{self.get_api_mappings_text()}
""")
        
        # Add variation-specific context
        if variation_id is not None:
            variation = next(
                (v for v in self.spec.get('variations', []) if v.get('id') == variation_id),
                None
            )
            
            if variation:
                func_name = variation.get('function_name', '')
                description = variation.get('description', '')
                
                prompt_parts.append(f"""
## Target Variation
- **ID**: {variation_id}
- **Name**: {variation.get('name', '')}
- **Description**: {description}
- **Original Function**: `{func_name}()`
""")
                
                # Extract and add original function
                func_code = self.extract_function(func_name)
                if func_code:
                    prompt_parts.append(f"""
## Original TServer Implementation

```cpp
{func_code}
```
""")
                
                prompt_parts.append(f"""
## Task
Translate the `{func_name}()` function to TNG format. The translated code should:

1. Use TNG's `tng::test::Monitor` for result tracking
2. Replace `env::System::palloc/pfree` with TNG buffer allocation (RAII)
3. Convert `CORE_LOG_*` to `m_log.*` calls
4. Use `monitor.expectEqual()` / `monitor.expectTrue()` instead of throwing exceptions
5. Follow TNG naming conventions and code style

## Expected Output
Provide the translated C++ code that can be added to the `run()` method:

```cpp
// Variation {variation_id}: {description}
// Translated from: {func_name}()

// Your translated code here...
```
""")
        else:
            # Overview prompt for all variations
            prompt_parts.append("""
## All Variations
""")
            for var in self.spec.get('variations', []):
                func_name = var.get('function_name', '')
                prompt_parts.append(f"- **{var.get('id')}**: {var.get('description', '')} (`{func_name}`)")
            
            prompt_parts.append("""
## Task
Provide an overview of the translation strategy for this test, including:
1. Which variations can be directly translated
2. Which variations need significant rework
3. Any TServer APIs that have no direct TNG equivalent
4. Suggested TNG structure (separate test classes or single test with variations)
""")
        
        return "\n".join(prompt_parts)
    
    def generate_all_prompts(self, output_dir: str = None) -> List[str]:
        """Generate prompts for all variations"""
        output_dir = output_dir or "."
        prompts = []
        
        # Overview prompt
        overview = self.generate_prompt(variation_id=None)
        prompts.append(('overview', overview))
        
        # Per-variation prompts
        for var in self.spec.get('variations', []):
            var_id = var.get('id')
            if var.get('function_name'):  # Only for variations with implementations
                prompt = self.generate_prompt(variation_id=var_id)
                prompts.append((f"variation_{var_id}", prompt))
        
        # Save prompts
        os.makedirs(output_dir, exist_ok=True)
        for name, prompt in prompts:
            filepath = os.path.join(output_dir, f"prompt_{name}.md")
            with open(filepath, 'w') as f:
                f.write(prompt)
            print(f"Generated: {filepath}")
        
        return [p[1] for p in prompts]
    
    def generate_context_file(self, output_file: str = None) -> str:
        """
        Generate a comprehensive context file for AI translation.
        This can be used as a single prompt or reference document.
        """
        class_name = self.spec.get('class_name', 'UnknownTest')
        
        content = []
        
        # Add TNG output path information if available
        tng_location_info = ""
        if self.tng_path and self.tng_output_dir:
            full_tng_path = os.path.join(self.tng_path, self.tng_output_dir)
            tng_location_info = f"""
## TNG Output Location

**Your TNG Source Path**: `{self.tng_path}`
**Target Directory**: `{self.tng_output_dir}`
**Full Path**: `{full_tng_path}`

Place the translated test file in: `{full_tng_path}/`
"""
        elif self.tng_output_dir:
            tng_location_info = f"""
## TNG Output Location

**Target Directory**: `{self.tng_output_dir}`

> **Note**: TNG source path was not provided. To get the full path, run the tool with:
> `--tng-path /your/path/to/diag_tng_canis`
"""
        
        content.append(f"""# AI Translation Context: {class_name}
{tng_location_info}
## 1. Test Overview

**Test Name**: {self.spec.get('test_name', '')}
**Class Name**: {class_name}
**Suite**: {self.spec.get('suite_id', '')} - {self.spec.get('suite_description', '')}
**Original File**: `{self.original_cpp}`

### Parameters
""")
        
        for param in self.spec.get('parameters', []):
            content.append(f"- `{param.get('name')}` ({param.get('type')}): {param.get('description', 'No description')}")
        
        content.append("""
### Variations
""")
        
        for var in self.spec.get('variations', []):
            content.append(f"- **{var.get('id')}**: {var.get('name', '')} - {var.get('description', '')}")
            if var.get('function_name'):
                content.append(f"  - Function: `{var.get('function_name')}()`")
        
        content.append(f"""
## 2. Original TServer Code

```cpp
{self.cpp_content}
```

## 3. API Translation Reference
{self.get_api_mappings_text()}

## 4. TNG Test Template

```cpp
class {class_name}TNG final : public tng::test::MonolithicTest
{{
private:
    // Parameter definitions
    using Parameters = diag::type::IntrospectableStructure<...>;

public:
    static constexpr std::string_view k_Feature = "...";
    static constexpr std::string_view k_SubCharacteristic = "...";
    static constexpr auto k_TestCaseMap = frozen::make_unordered_map<size_t, Parameters>({{...}});

    {class_name}TNG(const tng::test::Parameters& parameters, tng::test::Environment& environment);
    tng::test::SetUpResult setUp(tng::test::ExecutionContext& context) final;
    tng::test::Monitor run(const tng::test::ExecutionContext& context) override;

private:
    tng::test::ExclusiveReservation<tng::hal::Device> m_device;
    const Parameters& m_parameters;
}};
```

## 5. Translation Instructions

For each TServer function, translate using these patterns:

### Memory Allocation
```cpp
// TServer
env::Resource* res = env::System::palloc(size);
// ... use res->ptr(), res->base() ...
env::System::pfree(res);

// TNG
auto& localNode = tng::hal::getHal().getLocalNode();
auto buffer = localNode.allocateBuffer(size, alignment);
auto binding = localNode.bindBufferToHost(buffer);
// ... use binding.getHostVirtualAddress(), buffer.getAddress() ...
// (automatic cleanup via RAII)
```

### Logging
```cpp
// TServer
CORE_LOG_DEBUG(m_lg) << "Value: " << value << std::endl;

// TNG
m_log.debug("Value: {{}}", value);
```

### Error Handling
```cpp
// TServer
if (error) throw std::runtime_error("message");
return Pass;

// TNG
if (error) monitor.fail("message");
// or
monitor.expectTrue(!error, "message");
return monitor;
```

### Register Access
```cpp
// TServer
HalGpu* gpu = proc->Get<HalGpu>();
uint32_t val = gpu->RegRead(offset);
gpu->RegWrite(offset, data);

// TNG
auto val = m_device->read32(offset);
m_device->write32(offset, data);
// Or use engine APIs for specific IP blocks
```
""")
        
        result = "\n".join(content)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(result)
            print(f"Context file saved: {output_file}")
        
        return result


def main():
    """Command-line interface for AI translator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate AI prompts for TServer to TNG translation')
    parser.add_argument('spec_file', help='Path to test specification YAML')
    parser.add_argument('cpp_file', help='Path to original TServer .cpp file')
    parser.add_argument('--variation', '-v', type=int, help='Generate prompt for specific variation')
    parser.add_argument('--all', '-a', action='store_true', help='Generate prompts for all variations')
    parser.add_argument('--context', '-c', help='Generate comprehensive context file')
    parser.add_argument('--output', '-o', default='.', help='Output directory for prompts')
    
    args = parser.parse_args()
    
    translator = AITranslator(args.spec_file, args.cpp_file)
    
    if args.context:
        translator.generate_context_file(args.context)
    elif args.all:
        translator.generate_all_prompts(args.output)
    elif args.variation:
        prompt = translator.generate_prompt(args.variation)
        print(prompt)
    else:
        prompt = translator.generate_prompt()
        print(prompt)


if __name__ == '__main__':
    main()

