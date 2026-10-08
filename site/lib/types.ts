// Shape of site/data/leaderboard.json, produced by `bharatbench export`.
export type Stat = { n: number; mean: number; ci95: [number, number] };

export type ModelResult = {
  id: string;
  provider: string;
  model: string;
  label: string;
  overall: Stat | null;
  categories: Record<string, Stat>;
  languages: Record<string, Stat>;
  api_errors_excluded: number;
  unscored: number;
};

export type Category = { id: string; slug: string; title: string; description: string };

export type Example = {
  id: string;
  prompt: string;
  language: string;
  answer_type: string;
  difficulty: string;
  reference_answer: unknown;
  worked_solution?: string;
  source_url?: string;
};

export type JudgeInfo = {
  model: string;
  validation: { file: string; judge: string; n: number; exact_agreement: number; passed: boolean } | null;
} | null;

export type Leaderboard = {
  schema_version: number;
  run_id: string;
  last_updated: string;
  metric: string;
  bootstrap: { method: string; iterations: number; level: number; seed: number };
  run_notes: { note: string; repaired_replies: number; excluded_replies: number; total_replies: number };
  rubric_skipped: boolean;
  judge: JudgeInfo;
  totals: {
    dataset_tasks: number;
    verified_tasks: number;
    scored_tasks: number;
    models: number;
    scored_by_category: Record<string, number>;
    scored_by_language: Record<string, number>;
    scored_by_answer_type: Record<string, number>;
    dataset_by_answer_type: Record<string, number>;
  };
  params: {
    numeric_relative_tolerance: number;
    judge_agreement_threshold: number;
    rubric_scale: string;
    temperature: number;
  };
  verification: {
    statement: string;
    rows: { tasks: string; method: string }[];
    held_back: string;
  };
  language_labels: Record<string, string>;
  categories: Category[];
  models: ModelResult[];
  examples: Record<string, Example[]>;
};
