export interface Citation {
  chunk_id: string;
  text: string;
  source_file: string;
  page: number | null;
  source_url: string | null;
  retrieved_date: string | null;
}

export interface AskResult {
  answer: string;
  citations: Citation[];
  sufficient_context: boolean;
  hallucinated_citations: string[];
  parse_failed: boolean;
  query_category: string | null;
  category_confidence: number | null;
  routing_action: string;
}

export type StreamEvent =
  | { type: "meta"; query_category: string | null; category_confidence: number | null; routing_action: string }
  | { type: "answer_delta"; text: string }
  | ({ type: "final" } & AskResult);

export interface DocumentSummary {
  doc_id: string;
  source_file: string;
  source_url: string | null;
  retrieved_date: string | null;
  chunk_count: number;
}

export interface EvalRunSummary {
  run_id: number;
  started_at: string;
  retrieval_hit_rate: number | null;
  mean_faithfulness: number | null;
  classifier_accuracy: Record<string, number> | null;
}

export interface EvalQuestionResult {
  question_id: string;
  query: string;
  category: string;
  retrieval_hit: boolean | null;
  faithfulness_score: number | null;
  faithfulness_rationale: string | null;
  classifier_predicted: string | null;
  classifier_correct: boolean | null;
  sufficient_context: boolean;
  routing_action: string;
  answer: string;
}

export interface EvalRunDetail {
  run: EvalRunSummary;
  questions: EvalQuestionResult[];
}
