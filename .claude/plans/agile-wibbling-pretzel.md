# Plan: Double-Check and Self-Correction for Quiz Generation

## Context
In the quiz generation feature, we want to ensure the AI-generated questions are of high quality, strictly accurate to the study notes, free of formatting issues (especially LaTeX formatting for KaTeX rendering), and contain exactly 10 questions. We will achieve this by introducing a second-pass "review and correction" AI step that evaluates and refines the initial raw quiz output.

## Recommended Approach
1. **Add `review_quiz` method in `AIService` (`src/services/ai.py`)**:
   - Fetches an optional review prompt from Notion database named `study_assistant_review` in project `UEH-Notion`.
   - Falls back to a robust, highly detailed Vietnamese prompt that instructs the AI to inspect, correct, and format the quiz questions (LaTeX formulas, question quality, JSON schema, and exactly 10 questions count).
   - Calls the custom OpenAI client to get the refined quiz JSON.

2. **Integrate the review step in `generate_quiz` (`src/services/study_logic.py`)**:
   - Insert a new stage between calling the quiz generator and parsing the JSON.
   - Trigger a new progress update via `progress_callback("reviewing_quiz", 75, "🔍 AI đang tự động đánh giá và chuẩn hóa câu hỏi...")`.
   - Call `ai.review_quiz(raw_content, full_content)` with a try-except block to gracefully fall back to the original `raw_content` if the review step fails.

3. **Ensure progress status support**:
   - The UI or frontend should handle any new progress status gracefully. Let's check `frontend/app.js` to ensure the new `reviewing_quiz` progress status is rendered properly.

## Critical Files to Modify
1. `src/services/ai.py`
   - Implement `review_quiz(self, raw_quiz, content)` with Notion prompt support and robust hardcoded fallback.
2. `src/services/study_logic.py`
   - Call `review_quiz` in `generate_quiz`.
   - Update progress callback percentages and status names.

## Reused Utilities
- `PromptService.get_prompt` in `src/services/prompt_service.py` to optionally load `study_assistant_review`.
- `clean_json_string` in `src/services/study_logic.py` to clean the reviewed output.

## Verification Plan
1. **Manual Testing**:
   - Start the backend and frontend servers (using `npm run dev` / `python -m src.api.main` or standard launch scripts).
   - Trigger quiz generation for a topic.
   - Observe the progress bar and logs to verify `reviewing_quiz` step works.
   - Inspect the final 10 questions to ensure high quality, correct LaTeX formulas, and correct formatting.
