#!/usr/bin/env python3
"""
TNG Test Code Generator

This module generates TNG test code from a test specification file.

Usage:
    from tng_generator import TNGGenerator
    generator = TNGGenerator(spec_file, api_mappings_file)
    generator.generate(output_file)
"""

import os
import yaml
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class GeneratorConfig:
    """Configuration for code generation"""
    indent: str = "    "
    line_width: int = 120
    include_comments: bool = True


class TNGGenerator:
    """Generates TNG test code from specification"""
    
    def __init__(self, spec_file: str, mappings_file: str = None):
        """
        Initialize the generator.
        
        Args:
            spec_file: Path to the test specification YAML file
            mappings_file: Path to API mappings YAML file
        """
        self.spec_file = spec_file
        self.mappings_file = mappings_file or self._get_default_mappings()
        self.config = GeneratorConfig()
        
        # Load specification
        with open(spec_file, 'r') as f:
            self.spec = yaml.safe_load(f)
        
        # Load API mappings
        with open(self.mappings_file, 'r') as f:
            self.mappings = yaml.safe_load(f)
    
    def _get_default_mappings(self) -> str:
        """Get path to default API mappings file"""
        script_dir = Path(__file__).parent
        return str(script_dir / "api_mappings.yaml")
    
    def generate(self, output_file: str = None) -> str:
        """
        Generate TNG test code.
        
        Args:
            output_file: Optional path to write the generated code
            
        Returns:
            Generated code as string
        """
        code = self._generate_code()
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(code)
            print(f"Generated TNG test code: {output_file}")
        
        return code
    
    def _generate_code(self) -> str:
        """Generate the complete TNG test code"""
        parts = []
        
        # File header
        parts.append(self._generate_header())
        
        # Includes
        parts.append(self._generate_includes())
        
        # Anonymous namespace start
        parts.append("\nnamespace\n{")
        
        # Class definition
        parts.append(self._generate_class())
        
        # Test specification and registration
        parts.append(self._generate_registration())
        
        # Constructor
        parts.append(self._generate_constructor())
        
        # setUp method
        parts.append(self._generate_setup())
        
        # run method
        parts.append(self._generate_run())
        
        # Anonymous namespace end
        parts.append("\n}  // anonymous namespace")
        
        return "\n".join(parts)
    
    def _generate_header(self) -> str:
        """Generate file header comment"""
        class_name = self.spec.get('class_name', 'GeneratedTest')
        description = self.spec.get('suite_description', '')
        source_cpp = self.spec.get('source_cpp', '')
        
        return f'''/**
 * @file {self._to_snake_case(class_name)}_test.cpp
 * @brief {description}
 * @note Auto-generated from TServer test: {source_cpp}
 * @copyright Copyright © 2025 Advanced Micro Devices, Inc. All rights reserved.
 */
'''
    
    def _generate_includes(self) -> str:
        """Generate include statements"""
        includes = [
            "#include <test/cmn/basic_monolithic_test.h>",
            "#include <test/cmn/monolithic_support.h>",
            "#include <test/cmn/random.h>",
            "",
            "#include <hal/device.h>",
            "",
            "#include <cfg/config.h>",
            "",
            "#include <algorithm>",
            "#include <cstring>",
        ]
        
        # Add IP-specific includes based on detected API calls
        api_calls = self.spec.get('api_calls', [])
        ip_includes = set()
        
        for call in api_calls:
            context = call.get('context', '')
            if 'HalGpu' in context or 'RegRead' in context or 'RegWrite' in context:
                ip_includes.add("// TODO: Add IP-specific includes for register access")
            if 'palloc' in context:
                ip_includes.add("#include <ip/buffer_util.h>")
        
        if ip_includes:
            includes.append("")
            includes.extend(sorted(ip_includes))
        
        return "\n".join(includes)
    
    def _generate_class(self) -> str:
        """Generate the test class definition"""
        class_name = self.spec.get('class_name', 'GeneratedTest') + "TNG"
        description = self.spec.get('suite_description', '')
        feature = self.spec.get('feature', 'unknown')
        sub_characteristic = self.spec.get('sub_characteristic', 'unknown')
        
        # Generate parameter structs
        param_structs = self._generate_parameter_structs()
        param_list = self._generate_parameter_list()
        
        # Generate test case map
        test_cases = self._generate_test_case_map()
        
        # Generate member variables
        member_vars = self._generate_member_variables()
        
        return f'''
class {class_name} final : public tng::test::MonolithicTest
{{
private:
{param_structs}
    using Parameters = diag::type::IntrospectableStructure<{param_list}>;

public:
    static constexpr std::string_view k_Feature           = "{feature}";
    static constexpr std::string_view k_SubCharacteristic = "{sub_characteristic}";
    static constexpr size_t           k_Purpose           = 1; // TODO: Set appropriate purpose enum

    static constexpr std::string_view k_Description{{
        "{description}"}};

    static constexpr auto k_TestCaseMap = frozen::make_unordered_map<size_t, Parameters>({{
{test_cases}
    }});

    {class_name}(const tng::test::Parameters& parameters, tng::test::Environment& environment);

    tng::test::SetUpResult setUp(tng::test::ExecutionContext& context) final;
    tng::test::Monitor run(const tng::test::ExecutionContext& context) override;

private:
{member_vars}
}};
'''
    
    def _generate_parameter_structs(self) -> str:
        """Generate parameter struct definitions"""
        params = self.spec.get('parameters', [])
        if not params:
            return "    // No parameters"
        
        structs = []
        for param in params:
            name = param.get('name', 'unknown')
            ptype = self._map_type(param.get('type', 'int'))
            description = param.get('description', '')
            
            struct_name = self._to_pascal_case(name)
            structs.append(f'''    struct {struct_name} : public diag::value::ScalarValue<{ptype}>
    {{
        static constexpr std::string_view k_Name = "{name}";
    }};
''')
        
        return "\n".join(structs)
    
    def _generate_parameter_list(self) -> str:
        """Generate parameter list for IntrospectableStructure"""
        params = self.spec.get('parameters', [])
        if not params:
            return "/* no parameters */"
        
        names = [self._to_pascal_case(p.get('name', 'unknown')) for p in params]
        return ",\n                                                           ".join(names)
    
    def _generate_test_case_map(self) -> str:
        """Generate test case map entries"""
        variations = self.spec.get('variations', [])
        if not variations:
            return "        {1, {/* default parameters */}},"
        
        entries = []
        for var in variations:
            var_id = var.get('id', 1)
            description = var.get('description', '')
            func_name = var.get('function_name', '')
            
            # Generate parameter values (placeholders)
            params = self.spec.get('parameters', [])
            param_values = []
            for param in params:
                ptype = param.get('type', 'int')
                default = param.get('default')
                if default:
                    param_values.append(f"/*{param.get('name')}*/ {default}")
                elif ptype == 'bool':
                    param_values.append(f"/*{param.get('name')}*/ false")
                elif ptype in ['int', 'uint32_t', 'size_t', 'uintmax_t']:
                    param_values.append(f"/*{param.get('name')}*/ 0")
                else:
                    param_values.append(f"/*{param.get('name')}*/ {{}}")
            
            param_str = ", ".join(param_values) if param_values else "/* no params */"
            comment = f"  // {func_name}: {description}" if func_name else f"  // {description}"
            entries.append(f"        {{{var_id}, {{{param_str}}}}},{comment}")
        
        return "\n".join(entries)
    
    def _generate_member_variables(self) -> str:
        """Generate member variable declarations"""
        lines = [
            "    tng::test::ExclusiveReservation<tng::hal::Device> m_device;",
            "    const Parameters& m_parameters;",
        ]
        
        # Add original member variables with TNG equivalents
        member_vars = self.spec.get('member_variables', [])
        for var in member_vars:
            name = var.get('name', '')
            vtype = var.get('type', '')
            
            # Map TServer types to TNG
            tng_type = self._map_member_var_type(vtype)
            if tng_type:
                lines.append(f"    {tng_type} {name}; // Original: {vtype}")
        
        return "\n".join(lines)
    
    def _generate_registration(self) -> str:
        """Generate test registration code"""
        class_name = self.spec.get('class_name', 'GeneratedTest') + "TNG"
        
        return f'''
constexpr tng::test::impl::MonolithicTestSpecification<{class_name}> k_TestSpec;

const bool k_TestRegistered = tng::test::registerTest(k_TestSpec);
'''
    
    def _generate_constructor(self) -> str:
        """Generate constructor implementation"""
        class_name = self.spec.get('class_name', 'GeneratedTest') + "TNG"
        
        return f'''
{class_name}::{class_name}(const tng::test::Parameters& parameters, tng::test::Environment& environment) :
    MonolithicTest{{parameters, environment}},
    m_parameters{{diag::value::parameterCast<Parameters>(parameters)}}
{{
}}
'''
    
    def _generate_setup(self) -> str:
        """Generate setUp method"""
        class_name = self.spec.get('class_name', 'GeneratedTest') + "TNG"
        
        return f'''
tng::test::SetUpResult {class_name}::setUp(tng::test::ExecutionContext& /* context */)
{{
    // TODO: Add device reservation and setup code
    // Example:
    // m_device = environment.reserveDevice<tng::hal::Device>("GPU");
    // if (!m_device) {{
    //     m_log.warning("No device available!");
    //     return tng::test::SetUpResult::Skip;
    // }}
    
    return tng::test::SetUpResult::Ready;
}}
'''
    
    def _generate_run(self) -> str:
        """Generate run method with TODO comments for each variation"""
        class_name = self.spec.get('class_name', 'GeneratedTest') + "TNG"
        variations = self.spec.get('variations', [])
        
        # Generate variation handling code
        variation_code = []
        for var in variations:
            var_id = var.get('id', 1)
            func_name = var.get('function_name', '')
            description = var.get('description', '')
            
            variation_code.append(f'''
    // Variation {var_id}: {func_name}
    // Description: {description}
    // TODO: Implement variation logic
    // Original TServer function: {func_name}()
''')
        
        var_code_str = "\n".join(variation_code) if variation_code else "    // TODO: Implement test logic\n"
        
        # Generate API call translation hints
        api_hints = self._generate_api_hints()
        
        return f'''
tng::test::Monitor {class_name}::run(const tng::test::ExecutionContext& /* context */)
{{
    tng::test::Monitor monitor{{m_log}};
    
    // ============================================
    // API Translation Hints (from original TServer test):
{api_hints}
    // ============================================
    
    // Test implementation
{var_code_str}
    
    return monitor;
}}
'''
    
    def _generate_api_hints(self) -> str:
        """Generate API translation hints as comments"""
        api_calls = self.spec.get('api_calls', [])
        if not api_calls:
            return "    // No special API calls detected"
        
        hints = []
        seen = set()
        
        for call in api_calls:
            tserver_api = call.get('tserver_api', '')
            context = call.get('context', '')
            
            if context in seen:
                continue
            seen.add(context)
            
            # Look up mapping
            tng_api = self._lookup_mapping(context)
            if tng_api:
                hints.append(f"    // {context}:")
                hints.append(f"    //   TServer: {tserver_api[:60]}...")
                hints.append(f"    //   TNG: {tng_api}")
                hints.append("")
        
        return "\n".join(hints) if hints else "    // No special API calls detected"
    
    def _lookup_mapping(self, context: str) -> str:
        """Look up TNG equivalent for TServer API"""
        mapping_sections = ['device_access', 'memory', 'registers', 'logging', 'verification']
        
        for section in mapping_sections:
            section_mappings = self.mappings.get(section, {})
            for key, value in section_mappings.items():
                if context.lower() in key.lower():
                    return value.get('tng', '') if isinstance(value, dict) else str(value)
        
        return ""
    
    def _map_type(self, tserver_type: str) -> str:
        """Map TServer type to TNG type"""
        type_map = {
            'int': 'int32_t',
            'uint': 'uint32_t',
            'uintmax_t': 'uint64_t',
            'size_t': 'size_t',
            'bool': 'bool',
            'float': 'float',
            'double': 'double',
            'string': 'std::string',
        }
        return type_map.get(tserver_type, tserver_type)
    
    def _map_member_var_type(self, tserver_type: str) -> Optional[str]:
        """Map TServer member variable type to TNG"""
        # Skip logger types
        if 'Logger' in tserver_type:
            return None  # TNG has built-in logging
        
        # Map common types
        type_map = {
            'boost::optional': 'std::optional',
        }
        
        for old, new in type_map.items():
            if old in tserver_type:
                return tserver_type.replace(old, new)
        
        return tserver_type
    
    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _to_pascal_case(self, name: str) -> str:
        """Convert snake_case to PascalCase"""
        return ''.join(word.capitalize() for word in name.split('_'))


def main():
    """Main entry point for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate TNG test code from specification')
    parser.add_argument('spec_file', help='Path to test specification YAML file')
    parser.add_argument('--mappings', '-m', help='Path to API mappings YAML file')
    parser.add_argument('--output', '-o', help='Output .cpp file')
    
    args = parser.parse_args()
    
    generator = TNGGenerator(args.spec_file, args.mappings)
    
    output_file = args.output
    if not output_file:
        # Generate default output filename
        import os
        spec_name = os.path.splitext(os.path.basename(args.spec_file))[0]
        output_file = f"{spec_name}_tng_test.cpp"
    
    generator.generate(output_file)
    
    print(f"\n=== Generated TNG Test ===")
    print(f"Output: {output_file}")


if __name__ == '__main__':
    main()

