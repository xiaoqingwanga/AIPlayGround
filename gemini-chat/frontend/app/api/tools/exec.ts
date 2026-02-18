import { exec } from 'child_process';
import { promisify } from 'util';
import * as vm from 'vm';
import { Tool } from '@/lib/types';

const execAsync = promisify(exec);

export const pythonExecTool: Tool = {
  name: 'python_exec',
  description: 'Execute Python code (timeout: 30s)',
  parameters: {
    type: 'object',
    properties: {
      code: {
        type: 'string',
        description: 'Python code to execute',
      },
    },
    required: ['code'],
  },
  async execute({ code }) {
    try {
      const { stdout, stderr } = await execAsync(`python3 -c "${code.replace(/"/g, '\\"')}"`, {
        timeout: 30000,
      });
      return { stdout, stderr };
    } catch (error: any) {
      return {
        stdout: error.stdout || '',
        stderr: error.stderr || error.message,
      };
    }
  },
};

export const jsExecTool: Tool = {
  name: 'js_exec',
  description: 'Execute JavaScript code in a sandbox',
  parameters: {
    type: 'object',
    properties: {
      code: {
        type: 'string',
        description: 'JavaScript code to execute',
      },
    },
    required: ['code'],
  },
  async execute({ code }) {
    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        resolve({ error: 'Execution timeout (5s)' });
      }, 5000);

      try {
        const context = vm.createContext({});
        const result = vm.runInContext(code, context, { timeout: 5000 });
        clearTimeout(timeout);
        resolve({ result });
      } catch (error: any) {
        clearTimeout(timeout);
        resolve({ error: error.message });
      }
    });
  },
};
