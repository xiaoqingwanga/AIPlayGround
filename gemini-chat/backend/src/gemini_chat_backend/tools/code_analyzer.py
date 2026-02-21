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
        # Python modification patterns
        self.python_modification_keywords = [
            'write', 'open', 'remove', 'delete', 'rename',
            'mkdir', 'makedirs', 'chmod', 'chown',
            'exec', 'eval', 'compile', 'system', 'popen',
            'subprocess', 'os.system', 'shutil'
        ]

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

            # Check for import statements
            for node in ast.walk(tree):
                # Check for imports of dangerous modules
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        if any(dangerous in module_name.lower() for dangerous in
                               ['os', 'sys', 'subprocess', 'shutil', 'tempfile']):
                            detected_ops.append(f"import {module_name}")

                # Check for calls to dangerous functions
                elif isinstance(node, ast.Call):
                    # Get function name if available
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr

                    if func_name.lower() in [kw.lower() for kw in self.python_modification_keywords]:
                        detected_ops.append(f"call to {func_name}")

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
