import * as fs from 'fs/promises';
import * as path from 'path';
import { Tool } from '@/lib/types';

function getWorkingDir() {
  return process.env.TOOL_WORKING_DIRECTORY || process.cwd();
}

function resolveSafePath(filePath: string) {
  const workingDir = getWorkingDir();
  const resolved = path.resolve(workingDir, filePath);
  if (!resolved.startsWith(workingDir)) {
    throw new Error('Access denied: Path outside working directory');
  }
  return resolved;
}

export const fileReadTool: Tool = {
  name: 'file_read',
  description: 'Read a file from the filesystem',
  parameters: {
    type: 'object',
    properties: {
      path: {
        type: 'string',
        description: 'Path to the file (relative to working directory)',
      },
    },
    required: ['path'],
  },
  async execute({ path: filePath }) {
    const fullPath = resolveSafePath(filePath);
    const content = await fs.readFile(fullPath, 'utf-8');
    return { path: filePath, content };
  },
};

export const fileWriteTool: Tool = {
  name: 'file_write',
  description: 'Write content to a file',
  parameters: {
    type: 'object',
    properties: {
      path: {
        type: 'string',
        description: 'Path to the file (relative to working directory)',
      },
      content: {
        type: 'string',
        description: 'Content to write',
      },
    },
    required: ['path', 'content'],
  },
  async execute({ path: filePath, content }) {
    const fullPath = resolveSafePath(filePath);
    const dir = path.dirname(fullPath);
    await fs.mkdir(dir, { recursive: true });
    await fs.writeFile(fullPath, content, 'utf-8');
    return { path: filePath, success: true };
  },
};
