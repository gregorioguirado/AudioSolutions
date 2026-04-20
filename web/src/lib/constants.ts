// Legacy engine-brand IDs — the translation engine still understands only these.
export const CONSOLES = [
  { id: "yamaha_cl",        label: "Yamaha CL Series" },
  { id: "yamaha_cl_binary", label: "Yamaha CL/QL (binary)" },
  { id: "yamaha_ql",        label: "Yamaha QL Series" },
  { id: "yamaha_tf",        label: "Yamaha TF Series" },
  { id: "yamaha_dm7",       label: "Yamaha DM7" },
  { id: "yamaha_rivage",    label: "Yamaha RIVAGE PM" },
  { id: "digico_sd",        label: "DiGiCo SD/Quantum" },
] as const;

export type ConsoleId = (typeof CONSOLES)[number]["id"];

// New per-model catalogue used by the UI.
export type ConsoleModel = {
  id: string;          // stable slug, e.g. "yamaha-cl5"
  brand: string;       // human-readable brand, e.g. "Yamaha"
  brandId: ConsoleId;  // maps to the engine's brand-level ID
  series: string;      // e.g. "CL Series"
  model: string;       // e.g. "CL5"
  maxChannels: number;
  mixBuses: number;
  fileFormat: string;  // e.g. ".clf"
  supported: boolean;  // whether the engine currently supports it
};

export type ConsoleBrand = {
  name: string;
  models: ConsoleModel[];
};

export const CONSOLE_BRANDS: ConsoleBrand[] = [
  {
    name: "Yamaha",
    models: [
      { id: "yamaha-cl5",   brand: "Yamaha", brandId: "yamaha_cl", series: "CL Series", model: "CL5",         maxChannels: 72,  mixBuses: 24, fileFormat: ".clf", supported: true  },
      { id: "yamaha-cl3",   brand: "Yamaha", brandId: "yamaha_cl", series: "CL Series", model: "CL3",         maxChannels: 64,  mixBuses: 24, fileFormat: ".clf", supported: true  },
      { id: "yamaha-cl1",   brand: "Yamaha", brandId: "yamaha_cl", series: "CL Series", model: "CL1",         maxChannels: 48,  mixBuses: 24, fileFormat: ".clf", supported: true  },
      { id: "yamaha-ql5",   brand: "Yamaha", brandId: "yamaha_ql",     series: "QL Series", model: "QL5",         maxChannels: 64,  mixBuses: 16, fileFormat: ".cle", supported: true  },
      { id: "yamaha-ql1",   brand: "Yamaha", brandId: "yamaha_ql",     series: "QL Series", model: "QL1",         maxChannels: 32,  mixBuses: 16, fileFormat: ".cle", supported: true  },
      { id: "yamaha-tf5",   brand: "Yamaha", brandId: "yamaha_tf",     series: "TF Series", model: "TF5",         maxChannels: 32,  mixBuses: 20, fileFormat: ".tff", supported: true  },
      { id: "yamaha-tf3",   brand: "Yamaha", brandId: "yamaha_tf",     series: "TF Series", model: "TF3",         maxChannels: 32,  mixBuses: 20, fileFormat: ".tff", supported: true  },
      { id: "yamaha-tf1",   brand: "Yamaha", brandId: "yamaha_tf",     series: "TF Series", model: "TF1",         maxChannels: 32,  mixBuses: 20, fileFormat: ".tff", supported: true  },
      { id: "yamaha-dm7",   brand: "Yamaha", brandId: "yamaha_dm7",    series: "DM Series", model: "DM7",         maxChannels: 144, mixBuses: 72, fileFormat: ".dm7f", supported: true  },
      { id: "yamaha-rivage-pm10", brand: "Yamaha", brandId: "yamaha_rivage", series: "RIVAGE", model: "RIVAGE PM10", maxChannels: 216, mixBuses: 72, fileFormat: ".rivagepm", supported: true  },
    ],
  },
  {
    name: "DiGiCo",
    models: [
      { id: "digico-sd5",          brand: "DiGiCo", brandId: "digico_sd", series: "SD Series", model: "SD5",          maxChannels: 168, mixBuses: 56, fileFormat: ".show", supported: true  },
      { id: "digico-sd7",          brand: "DiGiCo", brandId: "digico_sd", series: "SD Series", model: "SD7",          maxChannels: 144, mixBuses: 56, fileFormat: ".show", supported: true  },
      { id: "digico-sd9",          brand: "DiGiCo", brandId: "digico_sd", series: "SD Series", model: "SD9",          maxChannels: 48,  mixBuses: 24, fileFormat: ".show", supported: true  },
      { id: "digico-sd10",         brand: "DiGiCo", brandId: "digico_sd", series: "SD Series", model: "SD10",         maxChannels: 56,  mixBuses: 24, fileFormat: ".show", supported: true  },
      { id: "digico-sd11",         brand: "DiGiCo", brandId: "digico_sd", series: "SD Series", model: "SD11",         maxChannels: 48,  mixBuses: 24, fileFormat: ".show", supported: true  },
      { id: "digico-sd12",         brand: "DiGiCo", brandId: "digico_sd", series: "SD Series", model: "SD12",         maxChannels: 96,  mixBuses: 48, fileFormat: ".show", supported: true  },
      { id: "digico-quantum-338",  brand: "DiGiCo", brandId: "digico_sd", series: "Quantum",   model: "Quantum 338",  maxChannels: 338, mixBuses: 96, fileFormat: ".show", supported: true  },
      { id: "digico-quantum-7",    brand: "DiGiCo", brandId: "digico_sd", series: "Quantum",   model: "Quantum 7",    maxChannels: 144, mixBuses: 48, fileFormat: ".show", supported: true  },
      { id: "digico-quantum-225",  brand: "DiGiCo", brandId: "digico_sd", series: "Quantum",   model: "Quantum 225",  maxChannels: 225, mixBuses: 64, fileFormat: ".show", supported: true  },
      { id: "digico-t-series",     brand: "DiGiCo", brandId: "digico_sd", series: "T-Series",  model: "T-Series",     maxChannels: 48,  mixBuses: 24, fileFormat: ".show", supported: true  },
    ],
  },
];

// Other brands (Allen & Heath, Midas, SSL Live) are intentionally out of this list
// until the engine supports them. The data model (ConsoleBrand/ConsoleModel) is ready
// to accept them — just add a new entry and flip `supported: true`.

const MODEL_INDEX: Record<string, ConsoleModel> = {};
for (const brand of CONSOLE_BRANDS) {
  for (const m of brand.models) MODEL_INDEX[m.id] = m;
}

export function getModelById(id: string | null | undefined): ConsoleModel | undefined {
  if (!id) return undefined;
  return MODEL_INDEX[id];
}

export function brandIdForModel(modelId: string): ConsoleId | null {
  const model = getModelById(modelId);
  return model ? model.brandId : null;
}

// Pick a sensible default model for a given file extension.
// The engine only cares about the brand-level ID, so the specific model is a UX best-guess;
// the user can override in the selector.
const EXTENSION_DEFAULT_MODEL: Record<string, string> = {
  ".cle": "yamaha-cl5",
  ".clf": "yamaha-cl5",
  ".show": "digico-sd12",
  ".tff": "yamaha-tf5",
  ".dm7f": "yamaha-dm7",
  ".rivagepm": "yamaha-rivage-pm10",
};

export function detectModelFromFilename(filename: string): ConsoleModel | null {
  const dot = filename.lastIndexOf(".");
  if (dot === -1) return null;
  const ext = filename.slice(dot).toLowerCase();
  const id = EXTENSION_DEFAULT_MODEL[ext];
  return id ? (getModelById(id) ?? null) : null;
}

// ─── Legacy helpers kept for backward compatibility ─────────────────────────

const EXTENSION_MAP: Record<string, ConsoleId> = {
  ".cle": "yamaha_cl",
  ".clf": "yamaha_cl",
  ".show": "digico_sd",
};

export function detectConsole(filename: string): ConsoleId | null {
  const dot = filename.lastIndexOf(".");
  if (dot === -1) return null;
  const ext = filename.slice(dot).toLowerCase();
  return EXTENSION_MAP[ext] ?? null;
}

export function otherConsole(id: ConsoleId): ConsoleId {
  return id === "yamaha_cl" ? "digico_sd" : "yamaha_cl";
}

export function consoleLabel(id: string): string {
  return CONSOLES.find((c) => c.id === id)?.label ?? id;
}
