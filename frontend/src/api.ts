export interface DemoConfig {
  project_id: string;
  agent_id: string;
  suite_id: string;
  versions: { vulnerable: string; hardened: string };
}
export interface Run {
  id: string;
  suite_id: string;
  agent_version_id: string;
  status: string;
  score: number | null;
  error: string | null;
  created_at: string;
}
export interface Result {
  id: string;
  run_id: string;
  test_case_id: string;
  category: string;
  name: string;
  status: string;
  score: number;
  output: string;
}
export interface Finding {
  id: string;
  result_id: string;
  category: string;
  severity: string;
  description: string;
}
export interface TraceEvent {
  sequence: number;
  event_type: string;
  detail: Record<string, unknown>;
  timestamp: string;
}
export interface Comparison {
  baseline_score: number;
  candidate_score: number;
  score_delta: number;
  fixed_test_case_ids: string[];
  regressed_test_case_ids: string[];
  compared_cases: number;
}

async function call<T>(route: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${route}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

const post = <T>(route: string, body: unknown): Promise<T> => call<T>(route, {
  method: 'POST', body: JSON.stringify(body),
});

export const api = {
  bootstrap: () => post<DemoConfig>('/demo/bootstrap', {}),
  runs: () => call<Run[]>('/test-runs'),
  run: (id: string) => call<Run>(`/test-runs/${id}`),
  results: (id: string) => call<Result[]>(`/test-runs/${id}/results`),
  findings: (id: string) => call<Finding[]>(`/test-runs/${id}/findings`),
  trace: (id: string) => call<TraceEvent[]>(`/test-results/${id}/trace`),
  start: (config: DemoConfig, profile: keyof DemoConfig['versions']) => post<Run>('/test-runs', {
    suite_id: config.suite_id, agent_version_id: config.versions[profile],
  }),
  compare: (baseline_run_id: string, candidate_run_id: string) => post<Comparison>('/comparisons', {
    baseline_run_id, candidate_run_id,
  }),
};
