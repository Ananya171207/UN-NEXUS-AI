// The four kinds of content the Research Assistant can show.
// Every section of an answer carries one of these labels so the reader
// always knows where a statement came from.

export const PROVENANCE = {
  ai: {
    label: 'AI-generated analysis',
    short: 'AI analysis',
    description: 'Written by an AI model. It can contain mistakes, so check important points against the sources.',
  },
  verified: {
    label: 'Verified source information',
    short: 'Verified source',
    description: 'Taken directly from a named official dataset or publication that the platform has checked.',
  },
  external: {
    label: 'External reference',
    short: 'External reference',
    description: 'A link to a third-party website or publication. It opens another site and is not checked by this platform.',
  },
  demo: {
    label: 'Demonstration response',
    short: 'Demonstration',
    description: 'Pre-written sample content that shows how the interface works. It was not produced by an AI model and is not verified.',
  },
};

export const PROVENANCE_ORDER = ['ai', 'verified', 'external', 'demo'];
