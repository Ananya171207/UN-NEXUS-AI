// NOTE: UNUSED. The Research Assistant now answers through the backend (see services/researchService.js).
// This file is kept only as a reference for the old pre-written samples; nothing imports it.
// =====================================================================
// DEMONSTRATION CONTENT — NOT AI-GENERATED, NOT VERIFIED
// These answers were written by hand to show how the Research Assistant
// looks and behaves. They are deliberately qualitative and contain no
// statistics. The "sources" are suggested places to read more; this
// demo has not retrieved or checked them.
// A real AI backend will replace this file (see services/README.md).
// =====================================================================

const NOT_RETRIEVED = 'Suggested reading. Not retrieved or checked by this demonstration.';

const ref = (id, title, publisher, url) => ({
  id,
  title,
  publisher,
  url,
  provenance: 'external',
  note: NOT_RETRIEVED,
});

export const SUGGESTED_QUESTIONS = [
  { id: 'sdg13', category: 'Climate', icon: 'thermometer', question: 'What is the current global progress towards SDG 13?' },
  { id: 'india', category: 'Comparison', icon: 'globe', question: "Compare India's development indicators with global averages." },
  { id: 'food', category: 'Food security', icon: 'wheat', question: 'Which regions face the highest food insecurity?' },
  { id: 'education', category: 'Education', icon: 'graduation', question: 'What are the major challenges facing global education?' },
  { id: 'renewables', category: 'Energy', icon: 'zap', question: 'How has global renewable energy adoption changed?' },
];

const q = (id) => SUGGESTED_QUESTIONS.find((s) => s.id === id).question;
const related = (...ids) => ids.map((id) => ({ label: q(id), question: q(id) }));

const demoProvenance = 'demo';

export const DEMO_ENTRIES = [
  {
    id: 'sdg13',
    keywords: ['sdg 13', 'sdg13', 'climate action', 'climate', 'warming', 'emissions'],
    response: {
      summary: {
        provenance: demoProvenance,
        text:
          'SDG 13 (Climate Action) asks countries to act urgently on climate change and its impacts. In this demonstration answer, overall progress is described as insufficient for the scale of the goal: emissions reduction, adaptation and climate finance are all widely reported as lagging behind what the targets require.',
      },
      keyFindings: {
        provenance: demoProvenance,
        items: [
          'Mitigation: global efforts to cut greenhouse-gas emissions are generally assessed as falling short of the pace needed to meet international temperature goals.',
          'Adaptation: many countries have national adaptation plans, but implementation and funding are often described as uneven, especially for the most vulnerable states.',
          'Finance: climate finance for developing countries remains a central point of negotiation, with debate about scale, accessibility and the balance between mitigation and adaptation.',
          'Data gaps: several SDG 13 indicators depend on national reporting that is incomplete or delayed, which limits precise tracking.',
        ],
      },
      analysis: {
        provenance: demoProvenance,
        paragraphs: [
          'SDG 13 is tracked through targets on resilience to climate hazards, integrating climate measures into national policy, education and awareness, and climate finance commitments. Assessment combines scientific reports with country submissions.',
          'A full analysis would compare countries and regions over time and show where progress is concentrated. That needs connected datasets, which this demonstration does not have.',
        ],
      },
      sources: [
        ref('s1', 'The Sustainable Development Goals Report', 'United Nations (UN DESA)', 'https://unstats.un.org/sdgs/'),
        ref('s2', 'Goal 13: Take urgent action to combat climate change', 'United Nations', 'https://sdgs.un.org/goals/goal13'),
        ref('s3', 'Assessment reports', 'Intergovernmental Panel on Climate Change (IPCC)', 'https://www.ipcc.ch/'),
      ],
      relatedTopics: related('renewables', 'india', 'food'),
    },
  },
  {
    id: 'india',
    keywords: ['india', 'indian'],
    response: {
      summary: {
        provenance: demoProvenance,
        text:
          "Comparing India with global averages means looking at income, health, education, energy and emissions together. In this demonstration answer the picture is described qualitatively: India is a very large and fast-growing economy whose income per person is below the world average, with commonly reported progress in areas such as electricity access and digital public services, alongside continuing challenges in health outcomes, learning quality and the quality of employment.",
      },
      keyFindings: {
        provenance: demoProvenance,
        items: [
          "Scale: India's population is among the largest in the world, so national averages hide large differences between states and between urban and rural areas.",
          'Income: GDP per person is below the world average, while total GDP is among the largest of any country.',
          'Energy and emissions: emissions per person are generally reported to be below the world average, while total emissions are large because of population size.',
          'Social indicators: gains in school enrolment and access to basic services are often reported next to gaps in learning outcomes, nutrition and health-system capacity.',
        ],
      },
      analysis: {
        provenance: demoProvenance,
        paragraphs: [
          'A rigorous comparison needs matching definitions and years across countries, for example from the World Bank or the UN SDG database, and should show where the gap is closing and where it is not.',
          'The India vs the World module (a later phase of this project) will present these comparisons with charts and tables. Until real datasets are connected, any figure there will be labelled as sample data.',
        ],
      },
      sources: [
        ref('s1', 'World Bank Open Data', 'World Bank', 'https://data.worldbank.org/'),
        ref('s2', 'SDG Global Database', 'United Nations Statistics Division', 'https://unstats.un.org/sdgs/dataportal'),
        ref('s3', 'Human Development Reports', 'UNDP', 'https://hdr.undp.org/'),
      ],
      relatedTopics: related('sdg13', 'education', 'renewables'),
    },
  },
  {
    id: 'food',
    keywords: ['food', 'hunger', 'insecurity', 'famine', 'nutrition', 'malnutrition'],
    response: {
      summary: {
        provenance: demoProvenance,
        text:
          'In this demonstration answer, food insecurity is described as most acute where conflict, climate extremes and economic shocks overlap. UN agencies have repeatedly highlighted parts of sub-Saharan Africa, parts of South Asia, and conflict-affected areas of Western Asia and elsewhere as facing the greatest challenges.',
      },
      keyFindings: {
        provenance: demoProvenance,
        items: [
          'Sub-Saharan Africa: many countries are reported to face high levels of hunger, driven by conflict, drought and flooding, and food prices that are high relative to incomes.',
          'South Asia: very large populations face food-security and nutrition challenges, including undernutrition among children.',
          'Conflict: protracted conflicts are consistently linked with the most severe food-insecurity situations, including risk of famine-like conditions.',
          'Affordability: the cost of a healthy diet is a major barrier even where enough calories are available.',
        ],
      },
      analysis: {
        provenance: demoProvenance,
        paragraphs: [
          'Food insecurity is usually measured with several indicators, such as prevalence of undernourishment, acute food-insecurity classifications and child nutrition measures. They answer different questions, so rankings of regions can change with the measure chosen.',
          'A real analysis would present these measures side by side for each region and year, with the source and date of every figure.',
        ],
      },
      sources: [
        ref('s1', 'Food and Agriculture Organization of the United Nations', 'FAO', 'https://www.fao.org/'),
        ref('s2', 'HungerMap', 'World Food Programme', 'https://hungermap.wfp.org/'),
        ref('s3', 'Integrated Food Security Phase Classification (IPC)', 'IPC Global Partnership', 'https://www.ipcinfo.org/'),
      ],
      relatedTopics: related('sdg13', 'education', 'india'),
    },
  },
  {
    id: 'education',
    keywords: ['education', 'school', 'schools', 'learning', 'teacher', 'teachers', 'literacy'],
    response: {
      summary: {
        provenance: demoProvenance,
        text:
          'Global education faces access, quality and funding challenges. In this demonstration answer the main themes are children and young people who remain out of school, weak learning outcomes among those who do attend, shortages of qualified teachers, disruption from conflict and crises, and unequal access to technology.',
      },
      keyFindings: {
        provenance: demoProvenance,
        items: [
          'Access: millions of children and adolescents remain out of school, concentrated in low-income and conflict-affected settings.',
          "Quality: many pupils do not acquire basic reading and numeracy skills, often described as a 'learning crisis'.",
          'Teachers: many low-income countries report shortages of trained teachers, especially in sub-Saharan Africa.',
          'Equity and funding: gender, disability, poverty and location all create gaps, and education budgets fall short of needs in many countries.',
        ],
      },
      analysis: {
        provenance: demoProvenance,
        paragraphs: [
          'SDG 4 covers early childhood through to adult learning, so a full picture combines enrolment, completion, learning-assessment and financing data from different sources.',
          'A real answer would show these indicators by region and over time, and flag where data are missing.',
        ],
      },
      sources: [
        ref('s1', 'UNESCO Institute for Statistics', 'UNESCO', 'https://uis.unesco.org/'),
        ref('s2', 'Global Education Monitoring Report', 'UNESCO', 'https://www.unesco.org/gem-report/en'),
        ref('s3', 'Education topic page', 'World Bank', 'https://www.worldbank.org/en/topic/education'),
      ],
      relatedTopics: related('india', 'food', 'sdg13'),
    },
  },
  {
    id: 'renewables',
    keywords: ['renewable', 'renewables', 'solar', 'wind', 'clean energy', 'energy transition'],
    response: {
      summary: {
        provenance: demoProvenance,
        text:
          'In this demonstration answer, renewable energy adoption is described as having accelerated over the past decade, led by solar and wind as technology costs have fallen. Even so, fossil fuels still supply a large share of total energy, and the benefits are unevenly spread between countries.',
      },
      keyFindings: {
        provenance: demoProvenance,
        items: [
          'Growth: solar and wind capacity additions have grown strongly, and renewables make up a large share of new power capacity in many markets.',
          'Cost: falling costs have made renewables competitive with fossil generation in many regions.',
          'Concentration: deployment is concentrated in a limited number of large economies, while many low-income countries attract much less investment.',
          'Integration: grid upgrades, storage and flexible demand are increasingly the limiting factors, not generation cost alone.',
        ],
      },
      analysis: {
        provenance: demoProvenance,
        paragraphs: [
          'Adoption can be measured as share of electricity, share of total energy or installed capacity. These give different pictures, because electricity is only part of total energy use.',
          'A real analysis would chart each measure by country and year, with the source of every series.',
        ],
      },
      sources: [
        ref('s1', 'Renewable energy statistics', 'International Renewable Energy Agency (IRENA)', 'https://www.irena.org/'),
        ref('s2', 'Energy data and analysis', 'International Energy Agency (IEA)', 'https://www.iea.org/'),
        ref('s3', 'Goal 7: Affordable and clean energy', 'United Nations', 'https://sdgs.un.org/goals/goal7'),
      ],
      relatedTopics: related('sdg13', 'india', 'education'),
    },
  },
];

const LIMITATIONS = [
  'Demonstration response: pre-written sample text, not produced by an AI model.',
  'Contains no verified statistics. The listed sources were not retrieved or checked.',
];

const FALLBACK = {
  summary: {
    provenance: demoProvenance,
    text:
      'Demonstration mode holds pre-written sample answers for five example topics only. It cannot analyse this question, and no AI model is connected to produce a new answer. Try one of the related questions below.',
  },
  keyFindings: { provenance: demoProvenance, items: [] },
  analysis: null,
  sources: [],
  relatedTopics: SUGGESTED_QUESTIONS.map((s) => ({ label: s.question, question: s.question })),
};

function score(question, keywords) {
  const text = question.toLowerCase();
  let total = 0;
  for (const keyword of keywords) {
    const pattern = new RegExp(`(^|[^a-z0-9])${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}([^a-z0-9]|$)`);
    if (pattern.test(text)) total += keyword.includes(' ') ? 2 : 1;
  }
  return total;
}

// Picks the demonstration answer whose keywords best match the question.
export function findDemoResponse(question) {
  let best = null;
  let bestScore = 0;
  for (const entry of DEMO_ENTRIES) {
    const s = score(question, entry.keywords);
    if (s > bestScore) {
      best = entry;
      bestScore = s;
    }
  }
  const base = best ? best.response : FALLBACK;
  return { matched: Boolean(best), ...base, limitations: LIMITATIONS };
}
