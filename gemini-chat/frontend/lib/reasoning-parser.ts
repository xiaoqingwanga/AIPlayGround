import { ThinkingStep } from '@/lib/types';

/**
 * Simple hash function for strings to generate consistent IDs.
 * This creates a stable hash based on the content.
 */
function hashString(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(36);
}

/**
 * Parses raw reasoning content from DeepSeek into structured thinking steps.
 * Each step contains a title, content, and optional reflection.
 */
export function parseReasoningIntoSteps(reasoning: string): ThinkingStep[] {
  if (!reasoning || reasoning.trim().length === 0) {
    return [];
  }

  // Split reasoning into segments based on natural boundaries
  const segments = splitIntoSegments(reasoning);

  // Convert each segment into a structured step
  return segments.map((segment, index) => createStepFromSegment(segment, index));
}

/**
 * Split raw reasoning text into logical segments based on:
 * - Numbered steps ("1.", "2.", etc.)
 * - Transition keywords ("First", "Next", "Finally", etc.)
 * - Paragraph boundaries
 * - Bullet points
 */
function splitIntoSegments(reasoning: string): string[] {
  const segments: string[] = [];
  const lines = reasoning.split('\n');
  let currentSegment = '';

  // Keywords that typically indicate a new step
  const stepIndicators = [
    /^\d+[.):]\s/i,  // "1. ", "2) ", "3: "
    /^\s*[-•]\s/,     // "- ", "• "
    /^(first|second|third|fourth|fifth|finally|next|then|lastly|alternatively|moreover|furthermore|therefore|thus|consequently|as\s+a\s+result)\b/i,
  ];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    if (line.length === 0) {
      // Empty line - save current segment if substantial
      if (currentSegment.trim().length > 20) {
        segments.push(currentSegment.trim());
        currentSegment = '';
      }
      continue;
    }

    // Check if this line starts a new step
    const isNewStep = stepIndicators.some(pattern => pattern.test(line));

    if (isNewStep && currentSegment.trim().length > 0) {
      // Save current segment and start new one
      segments.push(currentSegment.trim());
      currentSegment = line;
    } else {
      // Continue current segment
      currentSegment += (currentSegment ? ' ' : '') + line;
    }
  }

  // Don't forget the last segment
  if (currentSegment.trim().length > 0) {
    segments.push(currentSegment.trim());
  }

  // If we ended up with no segments (very short input), treat entire text as one segment
  if (segments.length === 0 && reasoning.trim().length > 0) {
    segments.push(reasoning.trim());
  }

  return segments;
}

/**
 * Convert a text segment into a structured ThinkingStep.
 */
function createStepFromSegment(segment: string, index: number): ThinkingStep {
  // Extract a title from the segment
  const title = extractTitle(segment, index);

  // Clean up the content (remove the title part if it was part of the original text)
  const content = cleanContent(segment, title);

  // Generate a reflection based on the content
  const reflection = generateReflection(content, title);

  // Create a stable ID based on the segment content and index
  // This ensures the same logical step gets the same ID even when re-parsed
  const contentHash = hashString(segment);
  return {
    id: `step-${contentHash}-${index}`,
    type: 'reasoning',
    title,
    content,
    timestamp: Date.now(),
  };
}

/**
 * Extract a concise title from the segment content.
 */
function extractTitle(segment: string, index: number): string {
  // Common reasoning step patterns to recognize
  const patterns = [
    // Numbered items: "1. Analyze the problem" -> "Analyze the problem"
    { pattern: /^\d+[.):]\s*(.+?)(?:\.|$)/i, capture: 1 },

    // Transition words followed by content
    { pattern: /^(?:First|Second|Third|Fourth|Fifth),?\s*(.+?)(?:\.|$)/i, capture: 1 },

    // Action-oriented starters
    { pattern: /^(?:Let me|I need to|I should|I'll|I will|Now I|Next I)\s+(.+?)(?:\.|$)/i, capture: 1 },

    // Analysis starters
    { pattern: /^(?:Analyzing|Examining|Considering|Evaluating|Looking at|Reviewing)\s+(.+?)(?:\.|$)/i, capture: 1 },
  ];

  for (const { pattern, capture } of patterns) {
    const match = segment.match(pattern);
    if (match && match[capture]) {
      const extracted = match[capture].trim();
      // Limit title length
      if (extracted.length > 5 && extracted.length < 80) {
        return capitalizeFirst(extracted);
      }
    }
  }

  // Fallback: Use first sentence or first N characters
  const firstSentence = segment.split(/[.!?]/)[0].trim();
  if (firstSentence.length > 10 && firstSentence.length < 60) {
    return capitalizeFirst(firstSentence);
  }

  // Ultimate fallback: generic step name
  return `Step ${index + 1}`;
}

/**
 * Clean up the content by removing redundant title text if present.
 */
function cleanContent(segment: string, title: string): string {
  // If title is a generic "Step N", keep full content
  if (title.startsWith('Step ')) {
    return segment;
  }

  // Try to find where the title ends in the content and remove that portion
  const titleLower = title.toLowerCase();
  const segmentLower = segment.toLowerCase();

  // Check if title appears at the start
  if (segmentLower.startsWith(titleLower)) {
    // Find where title ends (might have punctuation or different casing)
    let endIndex = title.length;
    while (endIndex < segment.length && /[.!?:;\s]/.test(segment[endIndex])) {
      endIndex++;
    }
    return segment.slice(endIndex).trim() || title;
  }

  return segment;
}

/**
 * Generate a reflection based on the step content.
 * This creates a self-reflective thought about the reasoning step.
 */
function generateReflection(content: string, title: string): string | undefined {
  const contentLower = content.toLowerCase();
  const titleLower = title.toLowerCase();
  const combined = contentLower + ' ' + titleLower;

  // Reflection patterns based on content type
  const reflections: { pattern: RegExp; reflection: string }[] = [
    {
      pattern: /\b(analyz|understand|identify|clarify|interpret)\b/,
      reflection: 'Am I interpreting this correctly? What might I be missing?',
    },
    {
      pattern: /\b(compare|contrast|alternative|different|versus|or)\b/,
      reflection: 'Have I considered all viable alternatives fairly?',
    },
    {
      pattern: /\b(plan|step|next|then|proceed|approach|strategy)\b/,
      reflection: 'Is this the most efficient path forward?',
    },
    {
      pattern: /\b(verify|check|test|confirm|validate|ensure)\b/,
      reflection: 'What edge cases should I also verify?',
    },
    {
      pattern: /\b(assum|assume|premise|belief|likely|probably)\b/,
      reflection: 'Are my assumptions well-founded? What if they\'re wrong?',
    },
    {
      pattern: /\b(conclude|conclusion|result|therefore|thus|summary)\b/,
      reflection: 'Does this conclusion logically follow from the evidence?',
    },
    {
      pattern: /\b(uncertain|unclear|confused|puzzl|mystery|doubt)\b/,
      reflection: 'What information would help clarify this uncertainty?',
    },
  ];

  for (const { pattern, reflection } of reflections) {
    if (pattern.test(combined)) {
      return reflection;
    }
  }

  // Default reflections based on step position
  const defaults = [
    'Is this the right approach to begin with?',
    'Am I making progress toward the goal?',
    'Should I reconsider my strategy?',
    'What are the implications of this step?',
  ];

  return defaults[Math.floor(Math.random() * defaults.length)];
}

/**
 * Capitalize the first letter of a string.
 */
function capitalizeFirst(str: string): string {
  if (!str || str.length === 0) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}
