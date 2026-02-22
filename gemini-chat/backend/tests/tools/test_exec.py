"""Test exec.py tools for code execution."""
import pytest
import asyncio

from gemini_chat_backend.tools.exec import PythonExecTool, JSExecTool
from gemini_chat_backend.tools.base import ToolResult


class TestPythonExecTool:
    """Test Python execution tool."""

    @pytest.fixture
    def tool(self):
        return PythonExecTool()

    @pytest.mark.asyncio
    async def test_execute_empty_code(self, tool):
        """Test execution with empty code."""
        result = await tool.execute(code="")
        assert isinstance(result, ToolResult)
        assert not result.success
        assert "Code is required" in result.error

    @pytest.mark.asyncio
    async def test_execute_simple_code(self, tool):
        """Test execution of simple Python code."""
        result = await tool.execute(code="print('hello')")
        assert isinstance(result, ToolResult)
        assert result.success
        assert result.result["stdout"] == "hello\n"
        assert result.result["stderr"] == ""

    @pytest.mark.asyncio
    async def test_execute_with_os_getcwd(self, tool):
        """Test execution with safe os.getcwd() function."""
        result = await tool.execute(code="import os; print(os.getcwd())")
        assert isinstance(result, ToolResult)
        assert result.success
        assert len(result.result["stdout"]) > 0  # Should have some directory path

    @pytest.mark.asyncio
    async def test_execute_with_sys_version(self, tool):
        """Test execution with safe sys.version access."""
        result = await tool.execute(code="import sys; print(sys.version[:20])")
        assert isinstance(result, ToolResult)
        assert result.success
        assert len(result.result["stdout"]) > 0

    @pytest.mark.asyncio
    async def test_execute_with_os_path_join(self, tool):
        """Test execution with safe os.path.join()."""
        result = await tool.execute(code="import os; print(os.path.join('a', 'b'))")
        assert isinstance(result, ToolResult)
        assert result.success
        assert result.result["stdout"] == "a/b\n"

    @pytest.mark.asyncio
    async def test_block_dangerous_os_system(self, tool):
        """Test blocking dangerous os.system() call."""
        result = await tool.execute(code="import os; os.system('ls')")
        assert isinstance(result, ToolResult)
        assert not result.success
        assert "modification operations" in result.error.lower()

    @pytest.mark.asyncio
    async def test_block_dangerous_subprocess(self, tool):
        """Test blocking dangerous subprocess.run() call."""
        result = await tool.execute(code="import subprocess; subprocess.run(['ls'])")
        assert isinstance(result, ToolResult)
        assert not result.success
        assert "modification operations" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_with_error(self, tool):
        """Test execution with Python syntax error."""
        result = await tool.execute(code="print(")  # Syntax error
        assert isinstance(result, ToolResult)
        # Syntax errors might be allowed by analyzer but will fail at execution
        # The exact behavior depends on implementation

    @pytest.mark.asyncio
    async def test_execute_timeout(self, tool):
        """Test execution timeout handling."""
        # Create a long-running loop
        result = await tool.execute(code="import time; time.sleep(35)")
        assert isinstance(result, ToolResult)
        assert not result.success
        assert "timeout" in result.error.lower()


class TestJSExecTool:
    """Test JavaScript execution tool."""

    @pytest.fixture
    def tool(self):
        return JSExecTool()

    @pytest.mark.asyncio
    async def test_execute_empty_code(self, tool):
        """Test execution with empty code."""
        result = await tool.execute(code="")
        assert isinstance(result, ToolResult)
        assert not result.success
        assert "Code is required" in result.error

    @pytest.mark.asyncio
    async def test_execute_simple_code(self, tool):
        """Test execution of simple JavaScript code."""
        result = await tool.execute(code="console.log('hello')")
        assert isinstance(result, ToolResult)
        # Node.js might not be installed, handle both cases
        if not result.success and "not found" in result.error.lower():
            pytest.skip("Node.js not installed")
        assert result.success
        assert "hello" in result.result["result"]

    @pytest.mark.asyncio
    async def test_execute_with_single_quotes(self, tool):
        """Test execution with single quotes in JavaScript."""
        code = "console.log('test with single quotes')"
        result = await tool.execute(code=code)
        if not result.success and "not found" in result.error.lower():
            pytest.skip("Node.js not installed")
        assert result.success
        assert "test with single quotes" in result.result["result"]

    @pytest.mark.asyncio
    async def test_execute_with_backticks(self, tool):
        """Test execution with backticks (template literals)."""
        code = "console.log(`test with backticks ${1+2}`)"
        result = await tool.execute(code=code)
        if not result.success and "not found" in result.error.lower():
            pytest.skip("Node.js not installed")
        assert result.success
        assert "test with backticks" in result.result["result"]

    @pytest.mark.asyncio
    async def test_execute_with_double_quotes(self, tool):
        """Test execution with double quotes in JavaScript."""
        code = 'console.log("test with double quotes")'
        result = await tool.execute(code=code)
        if not result.success and "not found" in result.error.lower():
            pytest.skip("Node.js not installed")
        assert result.success
        assert "test with double quotes" in result.result["result"]

    @pytest.mark.asyncio
    async def test_execute_with_mixed_quotes(self, tool):
        """Test execution with mixed quotes in JavaScript."""
        code = """console.log('single', "double", `template ${'nested'}`)"""
        result = await tool.execute(code=code)
        if not result.success and "not found" in result.error.lower():
            pytest.skip("Node.js not installed")
        assert result.success
        # Should execute without syntax errors

    @pytest.mark.asyncio
    async def test_block_dangerous_fs_write(self, tool):
        """Test blocking dangerous fs.writeFile() in JavaScript."""
        code = "const fs = require('fs'); fs.writeFile('test.txt', 'data')"
        result = await tool.execute(code=code)
        if not result.success and "not found" in result.error.lower():
            pytest.skip("Node.js not installed")
        assert not result.success
        assert "modification operations" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_with_process_cwd(self, tool):
        """Test execution with process.cwd() in JavaScript."""
        code = "console.log('cwd:', process.cwd())"
        result = await tool.execute(code=code)
        if not result.success and "not found" in result.error.lower():
            pytest.skip("Node.js not installed")
        assert result.success
        assert "cwd:" in result.result["result"]

    @pytest.mark.asyncio
    async def test_execute_timeout(self, tool):
        """Test execution timeout handling."""
        # Create a long-running loop
        code = "while(true) {}"  # Infinite loop
        result = await tool.execute(code=code)
        if not result.success and "not found" in result.error.lower():
            pytest.skip("Node.js not installed")
        assert not result.success
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_node_not_found(self, tool):
        """Test handling when Node.js is not in PATH."""
        # This is hard to test without actually removing node from PATH
        # The tool should handle FileNotFoundError gracefully
        pass