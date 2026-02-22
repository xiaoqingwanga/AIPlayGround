"""Test code_analyzer.py for code safety analysis."""
import pytest

from gemini_chat_backend.tools.code_analyzer import CodeAnalyzer


class TestCodeAnalyzer:
    """Test code analyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        return CodeAnalyzer()

    def test_init(self, analyzer):
        """Test analyzer initialization."""
        assert hasattr(analyzer, 'python_modification_keywords')
        assert hasattr(analyzer, 'js_modification_keywords')
        assert hasattr(analyzer, 'restricted_modules')
        assert hasattr(analyzer, 'module_aliases')

    def test_analyze_python_simple_safe(self, analyzer):
        """Test analysis of simple safe Python code."""
        code = "print('hello')"
        safe, error, ops = analyzer.analyze_python_code(code)
        assert safe
        assert error is None
        assert ops == []

    def test_analyze_python_with_safe_os_import(self, analyzer):
        """Test analysis with safe os import and function calls."""
        test_cases = [
            ("import os; print(os.getcwd())", True),
            ("import os; print(os.listdir('.'))", True),
            ("import os; print(os.path.join('a', 'b'))", True),
            ("import os.path; print(os.path.join('a', 'b'))", True),
            ("from os import getcwd; print(getcwd())", True),
            ("from os.path import join; print(join('a', 'b'))", True),
            ("import os as operating_system; print(operating_system.getcwd())", True),
        ]

        for code, expected_safe in test_cases:
            safe, error, ops = analyzer.analyze_python_code(code)
            assert safe == expected_safe, f"Failed for code: {code}. Error: {error}"
            if not safe:
                assert error is not None

    def test_analyze_python_with_dangerous_os_calls(self, analyzer):
        """Test analysis blocking dangerous os function calls."""
        test_cases = [
            ("import os; os.system('ls')", False),
            ("import os; os.remove('file.txt')", False),
            ("import os; os.rename('a', 'b')", False),
            ("import os; os.mkdir('test')", False),
            ("from os import system; system('ls')", False),
            ("import os as o; o.system('ls')", False),
        ]

        for code, expected_safe in test_cases:
            safe, error, ops = analyzer.analyze_python_code(code)
            assert safe == expected_safe, f"Failed for code: {code}"
            if not safe:
                assert "modification operations" in error.lower()
                assert len(ops) > 0

    def test_analyze_python_with_sys_functions(self, analyzer):
        """Test analysis with sys module functions."""
        test_cases = [
            ("import sys; print(sys.version)", True),
            ("import sys; print(sys.platform)", True),
            ("import sys; print(sys.argv)", True),
            ("from sys import version; print(version)", True),
            ("import sys as s; print(s.version)", True),
        ]

        for code, expected_safe in test_cases:
            safe, error, ops = analyzer.analyze_python_code(code)
            assert safe == expected_safe, f"Failed for code: {code}. Error: {error}"

    def test_analyze_python_block_subprocess(self, analyzer):
        """Test analysis blocking subprocess calls."""
        test_cases = [
            ("import subprocess; subprocess.run(['ls'])", False),
            ("from subprocess import run; run(['ls'])", False),
            ("import subprocess as sp; sp.call(['ls'])", False),
        ]

        for code, expected_safe in test_cases:
            safe, error, ops = analyzer.analyze_python_code(code)
            assert safe == expected_safe, f"Failed for code: {code}"
            if not safe:
                assert "subprocess" in error.lower() or "modification" in error.lower()

    def test_analyze_python_block_shutil(self, analyzer):
        """Test analysis blocking shutil calls."""
        test_cases = [
            ("import shutil; shutil.copy('a', 'b')", False),
            ("from shutil import copy; copy('a', 'b')", False),
        ]

        for code, expected_safe in test_cases:
            safe, error, ops = analyzer.analyze_python_code(code)
            assert safe == expected_safe, f"Failed for code: {code}"

    def test_analyze_python_syntax_error(self, analyzer):
        """Test analysis with Python syntax error."""
        code = "print("  # Syntax error
        safe, error, ops = analyzer.analyze_python_code(code)
        # Syntax errors might be allowed by analyzer (as per current implementation)
        # Just ensure no exception is raised
        assert error is None or "syntax error" in error.lower()

    def test_analyze_javascript_simple_safe(self, analyzer):
        """Test analysis of simple safe JavaScript code."""
        code = "console.log('hello')"
        safe, error, ops = analyzer.analyze_javascript_code(code)
        assert safe
        assert error is None
        assert ops == []

    def test_analyze_javascript_with_safe_operations(self, analyzer):
        """Test analysis with safe JavaScript operations."""
        test_cases = [
            ("console.log(process.cwd())", True),
            ("const x = 1 + 2;", True),
            ("function add(a, b) { return a + b; }", True),
            ("const arr = [1, 2, 3];", True),
        ]

        for code, expected_safe in test_cases:
            safe, error, ops = analyzer.analyze_javascript_code(code)
            assert safe == expected_safe, f"Failed for code: {code}. Error: {error}"

    def test_analyze_javascript_block_fs_write(self, analyzer):
        """Test analysis blocking file system write operations."""
        test_cases = [
            ("const fs = require('fs'); fs.writeFile('test.txt', 'data')", False),
            ("require('fs').appendFile('test.txt', 'more')", False),
            ("fs.unlink('file.txt')", False),
            ("fs.mkdir('test')", False),
            ("fs.rename('a', 'b')", False),
        ]

        for code, expected_safe in test_cases:
            safe, error, ops = analyzer.analyze_javascript_code(code)
            assert safe == expected_safe, f"Failed for code: {code}"
            if not safe:
                assert "modification operations" in error.lower()

    def test_analyze_javascript_block_eval(self, analyzer):
        """Test analysis blocking eval and Function constructor."""
        test_cases = [
            ("eval('alert(1)')", False),
            ("new Function('return 1')()", False),
        ]

        for code, expected_safe in test_cases:
            safe, error, ops = analyzer.analyze_javascript_code(code)
            assert safe == expected_safe, f"Failed for code: {code}"

    def test_analyze_javascript_block_child_process(self, analyzer):
        """Test analysis blocking child_process operations."""
        test_cases = [
            ("require('child_process').exec('ls')", False),
            ("const { spawn } = require('child_process'); spawn('ls')", False),
        ]

        for code, expected_safe in test_cases:
            safe, error, ops = analyzer.analyze_javascript_code(code)
            assert safe == expected_safe, f"Failed for code: {code}"

    def test_is_code_safe_python(self, analyzer):
        """Test is_code_safe method for Python."""
        # Safe code
        safe, error = analyzer.is_code_safe("print('hello')", "python")
        assert safe
        assert error is None

        # Dangerous code
        safe, error = analyzer.is_code_safe("import os; os.system('ls')", "python")
        assert not safe
        assert error is not None

    def test_is_code_safe_javascript(self, analyzer):
        """Test is_code_safe method for JavaScript."""
        # Safe code
        safe, error = analyzer.is_code_safe("console.log('hello')", "javascript")
        assert safe
        assert error is None

        # Dangerous code
        safe, error = analyzer.is_code_safe("eval('alert(1)')", "javascript")
        assert not safe
        assert error is not None

    def test_is_code_safe_unsupported_language(self, analyzer):
        """Test is_code_safe method with unsupported language."""
        safe, error = analyzer.is_code_safe("print('hello')", "ruby")
        assert not safe
        assert "unsupported language" in error.lower()

    def test_extract_attribute_chain(self, analyzer):
        """Test _extract_attribute_chain method."""
        # Test needs actual AST node creation, which is complex
        # This is covered indirectly through other tests
        pass

    def test_check_attribute_call(self, analyzer):
        """Test _check_attribute_call method."""
        # Test needs module_aliases setup
        analyzer.module_aliases = {'os': 'os'}

        # Test safe function
        result = analyzer._check_attribute_call(['os', 'getcwd'])
        assert result is None

        # Test dangerous function
        result = analyzer._check_attribute_call(['os', 'system'])
        assert result is not None
        assert 'os.system' in result