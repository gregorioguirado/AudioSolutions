export const CONSOLES = [
  { id: "yamaha_cl", label: "Yamaha CL/QL" },
  { id: "digico_sd", label: "DiGiCo SD/Quantum" },
] as const;

export type ConsoleId = (typeof CONSOLES)[number]["id"];

const EXTENSION_MAP: Record<string, ConsoleId> = {
  ".cle": "yamaha_cl",
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
