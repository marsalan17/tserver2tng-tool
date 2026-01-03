#!/usr/bin/env python3
"""
TServer Test Specification Extractor

This module parses TServer test files (.cpp and .xml) and extracts
a structured specification that can be used to generate TNG tests.

Usage:
    from spec_extractor import TServerExtractor
    extractor = TServerExtractor(cpp_file, xml_file)
    spec = extractor.extract()
"""

import re
import os
import yaml
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from pathlib import Path


@dataclass
class Parameter:
    """Represents a test parameter"""
    name: str
    type: str
    description: str = ""
    default: Any = None
    pattern: str = ""


@dataclass
class Variation:
    """Represents a test variation"""
    id: int
    name: str
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    function_name: str = ""  # The function called in this variation


@dataclass
class ApiCall:
    """Represents an API call that needs to be mapped"""
    tserver_api: str
    context: str = ""  # Where it's used
    suggested_tng: str = ""


@dataclass
class TestSpecification:
    """Complete test specification"""
    # Source info
    source_cpp: str = ""
    source_xml: str = ""
    
    # Test metadata
    test_name: str = ""
    class_name: str = ""
    suite_id: str = ""
    suite_description: str = ""
    
    # TNG mapping suggestions
    feature: str = ""
    sub_characteristic: str = ""
    
    # Parameters and variations
    parameters: List[Parameter] = field(default_factory=list)
    variations: List[Variation] = field(default_factory=list)
    
    # API calls found
    api_calls: List[ApiCall] = field(default_factory=list)
    
    # Includes
    includes: List[str] = field(default_factory=list)
    
    # Private member variables
    member_variables: List[Dict[str, str]] = field(default_factory=list)
    
    # Functions in the class
    functions: List[Dict[str, str]] = field(default_factory=list)


class TServerExtractor:
    """Extracts test specification from TServer test files"""
    
    # Patterns for parsing C++ code
    PATTERNS = {
        'class_decl': r'class\s+(\w+)\s*:\s*public\s+ts::Test',
        'include': r'#include\s*[<"]([^>"]+)[>"]',
        'parameter': r'Parameter<(\w+)>\s*\(\s*"(\w+)"(?:\s*,\s*([^)]+))?\)',
        'parameter_opt': r'ParameterOpt<(\w+)>\s*\(\s*"(\w+)"\s*\)',
        'get_id': r'GetId\(\)\s*\)',
        'case_stmt': r'case\s+(\d+)\s*:',
        'function_call': r'(\w+)\s*\(\s*\)',
        'member_var': r'^\s*([\w:<>]+)\s+(\w+)\s*;',
        'function_def': r'(?:virtual\s+)?(?:[\w:]+)\s+(\w+)\s*\([^)]*\)\s*(?:override|final)?\s*(?:;|{)',
        'tserver_instance': r'TServerTestInstance\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)',
        
        # TServer API patterns
        'target_active': r'TargetActive\(\)',
        'get_component': r'GetComponent<(\w+)>',
        'palloc': r'env::System::palloc\s*\([^)]+\)',
        'pfree': r'env::System::pfree\s*\([^)]+\)',
        'tcore_process': r'GetTcoreProcess\(\)',
        'hal_gpu': r'Get<\s*(\w+)\s*>\s*\(\s*\)',
        'reg_read': r'RegRead\s*\([^)]+\)',
        'reg_write': r'RegWrite\s*\([^)]+\)',
        'core_log': r'CORE_LOG_(\w+)\s*\(',
    }
    
    def __init__(self, cpp_file: str, xml_file: str = None):
        """
        Initialize the extractor.
        
        Args:
            cpp_file: Path to the TServer test .cpp file
            xml_file: Path to the TServer test .xml file (optional, will try to find it)
        """
        self.cpp_file = cpp_file
        self.xml_file = xml_file or self._find_xml_file(cpp_file)
        self.spec = TestSpecification()
        
    def _find_xml_file(self, cpp_file: str) -> Optional[str]:
        """Try to find the corresponding XML file"""
        cpp_path = Path(cpp_file)
        suite_dir = cpp_path.parent
        
        # Look for XML files in the same directory
        for xml_file in suite_dir.glob("*.xml"):
            return str(xml_file)
        return None
    
    def extract(self) -> TestSpecification:
        """Extract the complete test specification"""
        self.spec.source_cpp = self.cpp_file
        self.spec.source_xml = self.xml_file or ""
        
        # Read and parse the C++ file
        with open(self.cpp_file, 'r') as f:
            cpp_content = f.read()
        
        self._extract_from_cpp(cpp_content)
        
        # Read and parse the XML file if available
        if self.xml_file and os.path.exists(self.xml_file):
            self._extract_from_xml()
        
        return self.spec
    
    def _extract_from_cpp(self, content: str):
        """Extract information from C++ file"""
        # Extract includes
        self.spec.includes = re.findall(self.PATTERNS['include'], content)
        
        # Extract class name
        class_match = re.search(self.PATTERNS['class_decl'], content)
        if class_match:
            self.spec.class_name = class_match.group(1)
        
        # Extract TServerTestInstance
        instance_match = re.search(self.PATTERNS['tserver_instance'], content)
        if instance_match:
            self.spec.test_name = instance_match.group(1)
        
        # Extract parameters
        self._extract_parameters(content)
        
        # Extract variations from switch/case
        self._extract_variations(content)
        
        # Extract API calls
        self._extract_api_calls(content)
        
        # Extract member variables
        self._extract_member_variables(content)
        
        # Extract functions
        self._extract_functions(content)
    
    def _extract_parameters(self, content: str):
        """Extract parameter declarations"""
        # Regular parameters
        for match in re.finditer(self.PATTERNS['parameter'], content):
            param_type, param_name, default = match.groups()
            self.spec.parameters.append(Parameter(
                name=param_name,
                type=param_type,
                default=default.strip() if default else None
            ))
        
        # Optional parameters
        for match in re.finditer(self.PATTERNS['parameter_opt'], content):
            param_type, param_name = match.groups()
            self.spec.parameters.append(Parameter(
                name=param_name,
                type=param_type,
                description="Optional parameter"
            ))
    
    def _extract_variations(self, content: str):
        """Extract test variations from switch/case statements"""
        # Find the Main() function
        main_match = re.search(r'Result\s+\w+::Main\(\)\s*{(.+?)^}', content, re.MULTILINE | re.DOTALL)
        if not main_match:
            return
        
        main_body = main_match.group(1)
        
        # Find switch on GetId()
        switch_match = re.search(r'switch\s*\(\s*(?:this->)?GetId\(\)\s*\)\s*{(.+?)}', main_body, re.DOTALL)
        if not switch_match:
            return
        
        switch_body = switch_match.group(1)
        
        # Extract case statements
        case_pattern = r'case\s+(\d+)\s*:\s*(?://[^\n]*)?\s*(\w+)\s*\(\s*\)\s*;'
        for match in re.finditer(case_pattern, switch_body):
            var_id = int(match.group(1))
            func_name = match.group(2)
            self.spec.variations.append(Variation(
                id=var_id,
                name=f"variation_{var_id}",
                function_name=func_name
            ))
    
    def _extract_api_calls(self, content: str):
        """Extract TServer API calls that need mapping"""
        api_patterns = [
            ('TargetActive', self.PATTERNS['target_active']),
            ('GetComponent', self.PATTERNS['get_component']),
            ('palloc', self.PATTERNS['palloc']),
            ('pfree', self.PATTERNS['pfree']),
            ('TcoreProcess', self.PATTERNS['tcore_process']),
            ('HalGpu', self.PATTERNS['hal_gpu']),
            ('RegRead', self.PATTERNS['reg_read']),
            ('RegWrite', self.PATTERNS['reg_write']),
            ('CORE_LOG', self.PATTERNS['core_log']),
        ]
        
        for api_name, pattern in api_patterns:
            for match in re.finditer(pattern, content):
                self.spec.api_calls.append(ApiCall(
                    tserver_api=match.group(0),
                    context=api_name
                ))
    
    def _extract_member_variables(self, content: str):
        """Extract private member variables"""
        # Find the class body
        class_match = re.search(r'class\s+\w+[^{]*{(.+?)};', content, re.DOTALL)
        if not class_match:
            return
        
        class_body = class_match.group(1)
        
        # Find private section
        private_match = re.search(r'private\s*:(.+?)(?:public|protected|$)', class_body, re.DOTALL)
        if private_match:
            private_section = private_match.group(1)
            for match in re.finditer(r'^\s*([\w:<>,\s]+)\s+(\w+)\s*;', private_section, re.MULTILINE):
                var_type = match.group(1).strip()
                var_name = match.group(2)
                if var_name.startswith('m_'):
                    self.spec.member_variables.append({
                        'type': var_type,
                        'name': var_name
                    })
    
    def _extract_functions(self, content: str):
        """Extract function declarations/definitions"""
        # Simple pattern to find function definitions
        func_pattern = r'(?:void|Result|bool|int|[\w:]+)\s+(\w+::)?(\w+)\s*\([^)]*\)'
        
        for match in re.finditer(func_pattern, content):
            func_name = match.group(2)
            if func_name not in ['if', 'while', 'for', 'switch', 'catch']:
                self.spec.functions.append({
                    'name': func_name,
                    'signature': match.group(0)
                })
    
    def _extract_from_xml(self):
        """Extract information from XML file"""
        try:
            tree = ET.parse(self.xml_file)
            root = tree.getroot()
            
            # Extract suite info
            self.spec.suite_id = root.get('id', '')
            self.spec.suite_description = root.get('description', '')
            
            # Extract UserParameters
            for param in root.findall('.//UserParameter'):
                name = param.get('name', '')
                pattern = param.get('pattern', '')
                description = param.get('description', '')
                
                # Check if we already have this parameter
                existing = next((p for p in self.spec.parameters if p.name == name), None)
                if existing:
                    existing.description = description
                    existing.pattern = pattern
                else:
                    self.spec.parameters.append(Parameter(
                        name=name,
                        type=self._pattern_to_type(pattern),
                        description=description,
                        pattern=pattern
                    ))
            
            # Extract Test variations from XML
            for test in root.findall('.//Test'):
                test_id = test.get('id', '')
                alt_name = test.get('alt', '')
                description = test.get('description', '')
                
                # Update existing variation or create new one
                try:
                    var_id = int(test_id)
                    existing = next((v for v in self.spec.variations if v.id == var_id), None)
                    if existing:
                        existing.name = alt_name
                        existing.description = description
                    else:
                        self.spec.variations.append(Variation(
                            id=var_id,
                            name=alt_name,
                            description=description
                        ))
                except ValueError:
                    pass
                
                # Extract variation-level parameters
                for variation in test.findall('.//Variation'):
                    var_id_str = variation.get('id', '')
                    var_desc = variation.get('description', '')
                    
                    # Extract parameters for this variation
                    var_params = {}
                    for param in variation.findall('.//Parameter'):
                        param_name = param.get('name', '')
                        param_value = param.text
                        var_params[param_name] = param_value
                    
        except ET.ParseError as e:
            print(f"Warning: Could not parse XML file: {e}")
    
    def _pattern_to_type(self, pattern: str) -> str:
        """Convert XML pattern to C++ type"""
        mapping = {
            'integer': 'int',
            'bool': 'bool',
            'hex': 'uint64_t',
            'string': 'std::string',
            'float': 'float',
        }
        return mapping.get(pattern, 'auto')
    
    def to_yaml(self) -> str:
        """Convert specification to YAML format"""
        spec_dict = asdict(self.spec)
        return yaml.dump(spec_dict, default_flow_style=False, sort_keys=False)
    
    def save_spec(self, output_file: str):
        """Save specification to a YAML file"""
        with open(output_file, 'w') as f:
            f.write(self.to_yaml())
        print(f"Specification saved to: {output_file}")


def main():
    """Main entry point for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract TServer test specification')
    parser.add_argument('cpp_file', help='Path to TServer test .cpp file')
    parser.add_argument('--xml', '-x', help='Path to TServer test .xml file')
    parser.add_argument('--output', '-o', help='Output YAML file', default='test_spec.yaml')
    
    args = parser.parse_args()
    
    extractor = TServerExtractor(args.cpp_file, args.xml)
    spec = extractor.extract()
    extractor.save_spec(args.output)
    
    print("\n=== Extracted Specification ===")
    print(f"Test Name: {spec.test_name}")
    print(f"Class Name: {spec.class_name}")
    print(f"Suite: {spec.suite_id} - {spec.suite_description}")
    print(f"Parameters: {len(spec.parameters)}")
    print(f"Variations: {len(spec.variations)}")
    print(f"API Calls: {len(spec.api_calls)}")
    

if __name__ == '__main__':
    main()

