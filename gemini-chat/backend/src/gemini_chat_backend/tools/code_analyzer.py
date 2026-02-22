"""
Code analysis utilities for detecting modification operations.
"""
import ast
import re
from typing import List, Tuple, Optional

# Try to import logger, but fall back to a simple logger if dependencies not available
try:
    from gemini_chat_backend.utils.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """Analyzes code for modification operations."""

    def __init__(self):
        # Python modification patterns (for direct function calls not from restricted modules)
        self.python_modification_keywords = [
            'write', 'open', 'remove', 'delete', 'rename',
            'mkdir', 'makedirs', 'chmod', 'chown',
            'exec', 'eval', 'compile', 'system', 'popen',
        ]

        # Define safe vs dangerous functions for restricted modules
        # Start with minimal safe set - can be expanded based on user feedback
        self.restricted_modules = {
            'os': {
                'safe': {'getcwd', 'listdir', 'path', 'name', 'environ', 'getenv', 'sep',
                        'linesep', 'curdir', 'pardir', 'pathsep', 'defpath', 'altsep',
                        'extsep', 'devnull'},
                'dangerous': {'system', 'popen', 'remove', 'rename', 'mkdir', 'makedirs',
                             'chmod', 'chown', 'unlink', 'rmdir', 'exec', 'spawn',
                             'kill', 'fork', 'pipe', 'dup', 'dup2', 'close', 'fdopen',
                             'open', 'write', 'read', 'lseek', 'fstat', 'stat', 'lstat',
                             'access', 'chmod', 'chown', 'link', 'symlink', 'readlink',
                             'listxattr', 'removexattr', 'setxattr'}
            },
            'sys': {
                'safe': {'version', 'platform', 'argv', 'path', 'modules', 'exit',
                        'executable', 'prefix', 'base_prefix', 'byteorder',
                        'maxsize', 'maxunicode', 'copyright', 'api_version',
                        'version_info', 'hexversion', 'dont_write_bytecode',
                        'stdin', 'stdout', 'stderr', 'exc_info', 'last_type',
                        'last_value', 'last_traceback', 'tracebacklimit'},
                'dangerous': {'setprofile', 'settrace', 'setrecursionlimit',
                             'setcheckinterval', 'setswitchinterval'}
            },
            'subprocess': {
                'safe': set(),
                'dangerous': {'run', 'call', 'check_call', 'check_output', 'Popen',
                             'getoutput', 'getstatusoutput'}
            },
            'shutil': {
                'safe': set(),
                'dangerous': {'copy', 'copy2', 'copytree', 'rmtree', 'move', 'chown',
                             'which', 'disk_usage', 'unpack_archive', 'make_archive'}
            },
            'tempfile': {
                'safe': set(),
                'dangerous': {'mkstemp', 'mkdtemp', 'mktemp', 'NamedTemporaryFile',
                             'TemporaryFile', 'SpooledTemporaryFile'}
            }
        }

        # For modules imported with aliases (e.g., import os as operating_system)
        self.module_aliases = {}

        # JavaScript modification patterns
        self.js_modification_keywords = [
            'writeFile', 'appendFile', 'unlink', 'rmdir',
            'mkdir', 'rename', 'chmod', 'chown',
            'eval', 'Function', 'exec', 'spawn',
            'fs.write', 'fs.append', 'fs.unlink',
            'child_process', 'process.exit'
        ]

    def analyze_python_code(self, code: str) -> Tuple[bool, Optional[str], List[str]]:
        """Analyze Python code for modification operations.

        Args:
            code: Python code to analyze

        Returns:
            Tuple of (is_safe, error_message, detected_operations)
        """
        try:
            tree = ast.parse(code)
            detected_ops = []
            self.module_aliases = {}  # Reset for each analysis

            # First pass: collect imports and their aliases
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        alias_name = alias.asname or module_name
                        # Store mapping from alias to actual module
                        self.module_aliases[alias_name] = module_name

                elif isinstance(node, ast.ImportFrom):
                    # Handle 'from module import name'
                    module_name = node.module or ''
                    for alias in node.names:
                        imported_name = alias.name
                        alias_name = alias.asname or imported_name
                        # Store as module.function for later analysis
                        self.module_aliases[alias_name] = f"{module_name}.{imported_name}"

            # Second pass: analyze function calls and operations
            for node in ast.walk(tree):
                # Check for calls to dangerous functions
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        # Check if this is a direct call to a dangerous function
                        if func_name.lower() in [kw.lower() for kw in self.python_modification_keywords]:
                            detected_ops.append(f"call to {func_name}")

                    elif isinstance(node.func, ast.Attribute):
                        # Handle calls like os.getcwd(), sys.version, etc.
                        attr_chain = self._extract_attribute_chain(node.func)
                        result = self._check_attribute_call(attr_chain)
                        if result:
                            detected_ops.append(result)

                # Check for assignments to system variables
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.startswith('__'):
                            detected_ops.append(f"assignment to {target.id}")

            if detected_ops:
                return False, f"Code contains modification operations: {', '.join(detected_ops)}", detected_ops

            return True, None, []

        except SyntaxError as e:
            logger.warning(f"Syntax error in Python code analysis: {e}")
            # Allow syntax errors - they'll fail at execution anyway
            return True, None, []
        except Exception as e:
            logger.error(f"Error analyzing Python code: {e}")
            return False, f"Code analysis failed: {str(e)}", []

    def analyze_javascript_code(self, code: str) -> Tuple[bool, Optional[str], List[str]]:
        """Analyze JavaScript code for modification operations.

        Args:
            code: JavaScript code to analyze

        Returns:
            Tuple of (is_safe, error_message, detected_operations)
        """
        detected_ops = []

        # Convert to lowercase for case-insensitive matching
        code_lower = code.lower()

        # Check for dangerous patterns
        for pattern in self.js_modification_keywords:
            # Simple pattern matching - could be enhanced
            if re.search(rf'\b{pattern.lower()}\b', code_lower):
                detected_ops.append(pattern)

        # Check for eval and Function constructors
        if re.search(r'\beval\s*\(', code_lower):
            detected_ops.append('eval')
        if re.search(r'\bnew\s+Function\s*\(', code_lower):
            detected_ops.append('Function constructor')

        # Check for file system operations
        if re.search(r'\bfs\.\w+', code_lower):
            # Check if it's a write operation
            if re.search(r'\bfs\.(write|append|unlink|rmdir|mkdir|rename|chmod|chown)', code_lower):
                detected_ops.append('fs operation')

        if detected_ops:
            return False, f"Code contains modification operations: {', '.join(detected_ops)}", detected_ops

        return True, None, []

    def _extract_attribute_chain(self, node: ast.Attribute) -> List[str]:
        """Extract attribute chain from AST node (e.g., 'os.path.join' -> ['os', 'path', 'join'])."""
        chain = []
        current = node

        while isinstance(current, ast.Attribute):
            chain.insert(0, current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            chain.insert(0, current.id)

        return chain

    def _check_attribute_call(self, attr_chain: List[str]) -> Optional[str]:
        """Check if an attribute-based function call is safe.

        Args:
            attr_chain: List of attribute names (e.g., ['os', 'getcwd'])

        Returns:
            Error message if dangerous, None if safe
        """
        if len(attr_chain) < 2:
            return None  # Not a module.function call

        # Check if first element is a known module or alias
        module_name = attr_chain[0]
        actual_module = self.module_aliases.get(module_name, module_name)

        # Split actual_module if it's in module.function format (from import)
        if '.' in actual_module:
            actual_module, imported_func = actual_module.split('.', 1)
            # Check if the imported function is from a restricted module
            if actual_module in self.restricted_modules:
                # The imported function is being called directly
                func_name = imported_func
                module_info = self.restricted_modules[actual_module]
                if func_name in module_info['dangerous']:
                    return f"call to {actual_module}.{func_name}"
                # If it's in safe or not listed, allow it
                return None

        # Check if it's a restricted module
        if actual_module in self.restricted_modules:
            module_info = self.restricted_modules[actual_module]

            # For calls like os.getcwd(), func_name is getcwd
            func_name = attr_chain[1]

            # Check os.path.* calls
            if actual_module == 'os' and func_name == 'path' and len(attr_chain) > 2:
                # os.path.join() etc. - all os.path functions are read-only
                return None

            if func_name in module_info['dangerous']:
                return f"call to {actual_module}.{func_name}"

            # If function is in safe list or not explicitly dangerous, allow it
            # This allows read-only functions by default while blocking dangerous ones
            return None

        return None

    def is_code_safe(self, code: str, language: str = 'python') -> Tuple[bool, Optional[str]]:
        """Check if code is safe to execute (read-only).

        Args:
            code: Code to check
            language: 'python' or 'javascript'

        Returns:
            Tuple of (is_safe, error_message)
        """
        if language.lower() == 'python':
            safe, error, _ = self.analyze_python_code(code)
            return safe, error
        elif language.lower() == 'javascript':
            safe, error, _ = self.analyze_javascript_code(code)
            return safe, error
        else:
            return False, f"Unsupported language: {language}"
