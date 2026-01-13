#!/usr/bin/env python3
"""
AI-Powered TServer to TNG Translator

This module generates detailed context files for AI-assisted code translation.
It extracts the original TServer function implementations and creates
structured context that can be used with Claude, GPT, or other LLMs.

Features:
- Extracts TServer test specifications
- Includes existing TNG reference test (if found)
- Provides API mapping hints
- Generates comprehensive translation context
"""

import os
import re
import yaml
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class AITranslator:
    """Generates AI context for TServer to TNG translation"""
    
    def __init__(self, spec_file: str, original_cpp: str, mappings_file: str = None, 
                 tng_path: str = None, tng_output_dir: str = None, tng_reference_file: str = None):
        """
        Initialize the AI translator.
        
        Args:
            spec_file: Path to the test specification YAML
            original_cpp: Path to the original TServer .cpp file
            mappings_file: Path to API mappings YAML
            tng_path: Path to TNG source code (diag_tng)
            tng_output_dir: Relative path within TNG for output
            tng_reference_file: Path to existing TNG test file (for reference)
        """
        self.spec_file = spec_file
        self.original_cpp = original_cpp
        self.tng_path = tng_path
        self.tng_output_dir = tng_output_dir
        self.tng_reference_file = tng_reference_file
        
        # Load specification
        with open(spec_file, 'r') as f:
            self.spec = yaml.safe_load(f)
        
        # Load original C++ code
        with open(original_cpp, 'r') as f:
            self.cpp_content = f.read()
        
        # Load TNG reference if provided
        self.tng_reference_content = None
        if tng_reference_file and os.path.exists(tng_reference_file):
            with open(tng_reference_file, 'r') as f:
                self.tng_reference_content = f.read()
        
        # Load mappings
        mappings_file = mappings_file or str(Path(__file__).parent / "api_mappings.yaml")
        if os.path.exists(mappings_file):
            with open(mappings_file, 'r') as f:
                self.mappings = yaml.safe_load(f)
        else:
            self.mappings = {}
    
    def extract_function(self, func_name: str) -> Optional[str]:
        """Extract a function implementation from the C++ file"""
        if not func_name:
            return None
        
        class_name = self.spec.get('class_name', '')
        
        # Try class method first
        pattern = rf'(?:void|bool|int|Result|[\w:]+)\s+{class_name}::{func_name}\s*\([^)]*\)\s*(?:override\s*)?\{{'
        match = re.search(pattern, self.cpp_content, re.DOTALL)
        
        if match:
            # Find matching closing brace
            start = match.start()
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i, char in enumerate(self.cpp_content[start:], start):
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"' and not in_string:
                    in_string = True
                elif char == '"' and in_string:
                    in_string = False
                elif not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return self.cpp_content[start:i+1]
        
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
        
        return "\n".join(lines) if lines else "No specific mappings defined."
    
    def generate_context_file(self, output_file: str = None) -> str:
        """
        Generate a comprehensive context file for AI translation.
        Includes TNG reference test if available.
        """
        test_name = self.spec.get('test_name', 'UnknownTest')
        class_name = self.spec.get('class_name', test_name)
        
        content = []
        
        # Header
        content.append(f"""# TServer to TNG Translation Context

## Test Information

| Field | Value |
|-------|-------|
| **Test Name** | {test_name} |
| **Class Name** | {class_name} |
| **Suite** | {self.spec.get('suite_id', '')} |
| **Description** | {self.spec.get('suite_description', '')} |
| **Source File** | `{self.original_cpp}` |
""")

        # TNG Reference Section (if found)
        if self.tng_reference_content:
            content.append(f"""
---

## ⭐ EXISTING TNG REFERENCE TEST

**IMPORTANT**: An existing TNG test was found that corresponds to this TServer test.
Use this as your PRIMARY reference for understanding TNG patterns and conventions.

**TNG Reference File**: `{self.tng_reference_file}`

```cpp
{self.tng_reference_content}
```

### Key Patterns to Follow from Reference:

1. **Test Class Structure**: Follow the same class hierarchy and inheritance
2. **Parameter Definitions**: Use the same `ScalarValue` pattern for parameters
3. **Test Case Map**: Follow the `k_TestCaseMap` pattern for variations
4. **Logging Style**: Use `m_log.debug/info/error` as shown
5. **Monitor Usage**: Follow the same error checking patterns
6. **Device Access**: Use the same HAL patterns for hardware access

---
""")
        else:
            content.append("""
---

## TNG Reference

> **Note**: No existing TNG reference test was found for this TServer test.
> The generated skeleton provides a starting template based on TNG conventions.
> Refer to other TNG tests in your codebase for specific patterns.

---
""")

        # Parameters
        content.append("""
## Parameters
""")
        
        params = self.spec.get('parameters', [])
        if params:
            content.append("| Name | Type | Default | Description |")
            content.append("|------|------|---------|-------------|")
            for param in params:
                default = param.get('default', 'N/A')
                desc = param.get('description', '')
                content.append(f"| `{param.get('name')}` | {param.get('type')} | {default} | {desc} |")
        else:
            content.append("No parameters detected.")

        # Variations
        content.append("""

## Test Variations
""")
        
        variations = self.spec.get('variations', [])
        if variations:
            content.append("| ID | Name | Description |")
            content.append("|----|------|-------------|")
            for var in variations:
                content.append(f"| {var.get('id')} | {var.get('name', '')} | {var.get('description', '')} |")
        else:
            content.append("No variations detected.")

        # Original TServer Code
        content.append(f"""

---

## Original TServer Test Code

```cpp
{self.cpp_content}
```
""")

        # API Mappings
        content.append(f"""

---

## API Translation Reference

### Framework Differences

| Aspect | TServer (Old) | TNG (New) |
|--------|---------------|-----------|
| **Base Class** | `ts::Test` | `tng::test::MonolithicTest` |
| **Entry Point** | `Result Main()` | `tng::test::Monitor run()` |
| **Parameters** | `Parameter<T>("name", default)` | `ScalarValue<T>` + `k_TestCaseMap` |
| **Logging** | `CORE_LOG_DEBUG(m_lg) << msg` | `m_log.debug("msg {{}}", val)` |
| **Memory Alloc** | `env::System::palloc()` | `localNode.allocateBuffer()` |
| **Memory Free** | `env::System::pfree()` | RAII (automatic) |
| **Result Pass** | `return Pass;` | `return monitor;` |
| **Result Fail** | `return Fail;` or `throw` | `monitor.fail("msg")` |

{self.get_api_mappings_text()}

---

## Translation Instructions

### 1. Memory Allocation Pattern

```cpp
// TServer (OLD)
env::Resource* res = env::System::palloc(size, minAddr, maxAddr, alignment, cacheType);
void* ptr = res->ptr();
uintmax_t phys = res->base();
// ... use memory ...
env::System::pfree(res);

// TNG (NEW)
auto& localNode = tng::hal::getHal().getLocalNode();
auto buffer = localNode.allocateBuffer(size, alignment);
auto binding = localNode.bindBufferToHost(buffer);
void* ptr = binding.getHostVirtualAddress();
uint64_t phys = buffer.getAddress();
// ... use memory ...
// (automatic cleanup - RAII)
```

### 2. Logging Pattern

```cpp
// TServer (OLD)
CORE_LOG_DEBUG(m_lg) << "Value: " << std::hex << value << std::endl;
CORE_LOG_INFO(m_lg) << "Status: " << status << std::endl;
CORE_LOG_ERROR(m_lg) << "Error: " << msg << std::endl;

// TNG (NEW)
m_log.debug("Value: {{:#x}}", value);
m_log.info("Status: {{}}", status);
m_log.error("Error: {{}}", msg);
```

### 3. Result/Error Handling Pattern

```cpp
// TServer (OLD)
if (error_condition) {{
    CORE_LOG_ERROR(m_lg) << "Something failed" << std::endl;
    return Fail;
}}
return Pass;

// TNG (NEW)
if (error_condition) {{
    monitor.fail("Something failed");
    return monitor;
}}
// Or use expectations:
monitor.expectTrue(!error_condition, "Something failed");
return monitor;
```

### 4. Parameter Access Pattern

```cpp
// TServer (OLD)
bool flag = Parameter<bool>("flag_name", false);
int count = Parameter<int>("count", 10);

// TNG (NEW) - In class definition:
struct FlagName : public diag::value::ScalarValue<bool> {{
    static constexpr std::string_view k_Name = "flag_name";
}};
struct Count : public diag::value::ScalarValue<int32_t> {{
    static constexpr std::string_view k_Name = "count";
}};
using Parameters = diag::type::IntrospectableStructure<FlagName, Count>;

// Access in run():
bool flag = m_parameters.get<FlagName>();
int count = m_parameters.get<Count>();
```

---

## How to Use This Context

1. **Copy this entire file** to Claude, GPT, or your AI assistant
2. **Ask specific questions** like:
   - "Translate the `Main()` function to TNG format"
   - "Convert variation 3 to use TNG patterns"
   - "How should I handle the memory allocation in `testFunction()`?"
3. **Review the generated code** and integrate it into your TNG test
4. **Test and iterate** - the AI provides a starting point, not final code

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
    
    parser = argparse.ArgumentParser(description='Generate AI context for TServer to TNG translation')
    parser.add_argument('spec_file', help='Path to test specification YAML')
    parser.add_argument('cpp_file', help='Path to original TServer .cpp file')
    parser.add_argument('--tng-reference', '-r', help='Path to existing TNG reference test')
    parser.add_argument('--output', '-o', help='Output context file')
    
    args = parser.parse_args()
    
    translator = AITranslator(
        args.spec_file, 
        args.cpp_file,
        tng_reference_file=args.tng_reference
    )
    
    output = args.output or args.spec_file.replace('.yaml', '_ai_context.md')
    translator.generate_context_file(output)


if __name__ == '__main__':
    main()
