import { Tool } from '@/lib/types';
import { fileReadTool, fileWriteTool } from './file';
import { pythonExecTool, jsExecTool } from './exec';

export const tools: Tool[] = [
  fileReadTool,
  fileWriteTool,
  pythonExecTool,
  jsExecTool,
];

export function getTool(name: string): Tool | undefined {
  return tools.find(t => t.name === name);
}
