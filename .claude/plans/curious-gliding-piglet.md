# Plan - Redesign Quiz Force-Refresh Button

## Context
The "Tạo đề mới (Bỏ qua lưu cache)" button is currently a large underlined text link at the bottom of the Quiz View. It is distracting, contains technical jargon ("cache"), and is prone to accidental clicks when users try to navigate questions. We will change it to a clean, standard refresh icon button in the header next to the progress indicator.

## Proposed Changes

### Frontend HTML (`frontend/index.html`)
1. Remove the old `#force-refresh-btn` at the bottom of the quiz view.
2. In the Quiz View header, wrap the `#quiz-progress` span in a flex container and insert the `#force-refresh-btn` next to it as a small icon button (using the same standard refresh SVG icon).

### Frontend Javascript (`frontend/app.js`)
- Keep the `ui.forceRefreshBtn` mapping since the ID remains the same.
- In `startQuickReview()` and `showQuizResults()` where `ui.forceRefreshBtn` is hidden or shown, ensure it matches the new header icon styling. Since the button is in the header, we can hide it for `quick_review` quizzes (as quick reviews don't support cached database refreshes easily).

## Verification Plan
1. Start local servers.
2. Load a topic quiz and verify the bottom text link is gone.
3. Verify the new refresh icon button is visible in the top-right header next to the progress indicator.
4. Verify clicking the refresh icon successfully regenerates a new set of quiz questions.
5. Verify the refresh icon is hidden when viewing quick reviews or when on the results screen.
