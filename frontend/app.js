const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:'
    ? 'http://127.0.0.1:8000'
    : 'https://ueh-notion.onrender.com';


function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return text
        .toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// DOM Elements
const views = {
    loading: document.getElementById('loading-view'),
    topics: document.getElementById('topics-view'),
    quiz: document.getElementById('quiz-view'),
    timeline: document.getElementById('timeline-view')
};

const ui = {
    topicsList: document.getElementById('topics-list'),
    noTopics: document.getElementById('no-topics'),
    loadingText: document.getElementById('loading-text'),
    quizTopicTitle: document.getElementById('quiz-topic-title'),
    quizProgress: document.getElementById('quiz-progress'),
    questionText: document.getElementById('question-text'),
    optionsContainer: document.getElementById('options-container'),
    explanationBox: document.getElementById('explanation-box'),
    prevBtn: document.getElementById('prev-btn'),
    nextBtn: document.getElementById('next-btn'),
    statusBtns: document.getElementById('status-btns'),
    btnChua: document.getElementById('status-chua-btn'),
    btnNam: document.getElementById('status-nam-btn'),
    forceRefreshBtn: document.getElementById('force-refresh-btn'),
    closeQuizBtn: document.getElementById('close-quiz-btn'),
    showResultsBtn: document.getElementById('show-results-btn'),
    quizResults: document.getElementById('quiz-results'),
    resultsScore: document.getElementById('results-score'),
    resultsPercentage: document.getElementById('results-percentage'),
    resultsFeedback: document.getElementById('results-feedback'),
    resultsTime: document.getElementById('results-time'),
    resultsGrid: document.getElementById('results-grid'),
    reviewMistakesBtn: document.getElementById('review-mistakes-btn'),
    mistakesCount: document.getElementById('mistakes-count'),
    retakeMistakesBtn: document.getElementById('retake-mistakes-btn'),
    shareResultsBtn: document.getElementById('share-results-btn'),
    quizTimerText: document.getElementById('quiz-timer-text'),
    flagQuestionBtn: document.getElementById('flag-question-btn'),
    quizModeBtn: document.getElementById('quiz-mode-btn'),
    quizModeIcon: document.getElementById('quiz-mode-icon'),
    quizModeText: document.getElementById('quiz-mode-text'),
    searchInput: document.getElementById('search-input'),
    clearSearchBtn: document.getElementById('clear-search-btn'),
    courseFilter: document.getElementById('course-filter'),
    topicsSummaryText: document.getElementById('topics-summary-text'),
    resetFilterBtn: document.getElementById('reset-filter-btn'),
    noTopicsDesc: document.getElementById('no-topics-desc'),
    quickReviewBtn: document.getElementById('quick-review-btn'),
    quizDoneBtn: document.getElementById('quiz-done-btn'),
    refreshCandidatesBtn: document.getElementById('refresh-candidates-btn'),
    progressBar: document.getElementById('quiz-progress-bar'),
    progressContainer: document.getElementById('quiz-progress-container'),
    loadingProgressBar: document.getElementById('loading-progress-bar'),
    loadingPercentage: document.getElementById('loading-percentage'),
    cancelLoadingBtn: document.getElementById('cancel-loading-btn'),
    reviewAnswersBtn: document.getElementById('review-answers-btn'),
    dotContainer: document.getElementById('quiz-dot-container'),
    copyQuestionBtn: document.getElementById('copy-question-btn'),
    clearCacheBtn: document.getElementById('clear-cache-btn'),
    toggleTimelineBtn: document.getElementById('toggle-timeline-btn'),
    closeTimelineBtn: document.getElementById('close-timeline-btn'),
    timelineContainer: document.getElementById('timeline-container'),
    timelineCourseFilter: document.getElementById('timeline-course-filter'),
    timelineMonthFilter: document.getElementById('timeline-month-filter'),
    timelineDateFilter: document.getElementById('timeline-date-filter'),
    refreshTimelineBtn: document.getElementById('refresh-timeline-btn'),
    resumeBanner: document.getElementById('resume-quiz-banner'),
    resumeTitle: document.getElementById('resume-quiz-title'),
    resumeBadge: document.getElementById('resume-quiz-badge'),
    resumeBtn: document.getElementById('resume-quiz-btn'),
    discardResumeBtn: document.getElementById('discard-resume-btn'),
    quizConfigModal: document.getElementById('quiz-config-modal'),
    closeConfigModalBtn: document.getElementById('close-config-modal-btn'),
    modalTopicTitle: document.getElementById('modal-topic-title'),
    modalCancelBtn: document.getElementById('modal-cancel-btn'),
    modalStartQuizBtn: document.getElementById('modal-start-quiz-btn'),
    configNumQuestionsVal: document.getElementById('config-num-questions-val'),
    configNumQuestionsGroup: document.getElementById('config-num-questions-group'),
    configDifficultyGroup: document.getElementById('config-difficulty-group'),
    configTypeGroup: document.getElementById('config-type-group'),
    batchQuizBtn: document.getElementById('batch-quiz-btn'),
    batchQuizModal: document.getElementById('batch-quiz-modal'),
    closeBatchModalBtn: document.getElementById('close-batch-modal-btn'),
    batchModalCourseTitle: document.getElementById('batch-modal-course-title'),
    batchApplyAllBtn: document.getElementById('batch-apply-all-btn'),
    batchGlobalNum: document.getElementById('batch-global-num'),
    batchGlobalDiff: document.getElementById('batch-global-diff'),
    batchGlobalType: document.getElementById('batch-global-type'),
    batchTopicsList: document.getElementById('batch-topics-list'),
    batchProgressContainer: document.getElementById('batch-progress-container'),
    batchProgressText: document.getElementById('batch-progress-text'),
    batchProgressPercent: document.getElementById('batch-progress-percent'),
    batchProgressBar: document.getElementById('batch-progress-bar'),
    batchCurrentTopicStatus: document.getElementById('batch-current-topic-status'),
    batchCancelBtn: document.getElementById('batch-cancel-btn'),
    batchStartBtn: document.getElementById('batch-start-btn'),
    batchSelectAllCb: document.getElementById('batch-select-all-cb'),
    batchSelectedCount: document.getElementById('batch-selected-count'),
    batchTotalCount: document.getElementById('batch-total-count'),
};


// State
let telegramData = { id: 'web_guest' };
let allTopics = [];
let currentTopic = null;
let currentQuiz = [];
let currentQuestionIndex = 0;
let searchDebounceTimer = null;
let currentTimeline = [];

let savedProgressMap = {};
let isExamMode = localStorage.getItem('isExamMode') === 'true';
let singleQuizAbortController = null;
let batchQuizAbortController = null;

// Quiz Generation Configuration (Stored in localStorage)
let selectedTopicForConfig = null;
let quizConfig = {
    numQuestions: parseInt(localStorage.getItem('quizConfig_numQuestions'), 10) || 15,
    difficulty: localStorage.getItem('quizConfig_difficulty') || 'medium',
    questionType: localStorage.getItem('quizConfig_questionType') || 'balanced'
};

function saveQuizConfig() {
    try {
        localStorage.setItem('quizConfig_numQuestions', quizConfig.numQuestions);
        localStorage.setItem('quizConfig_difficulty', quizConfig.difficulty);
        localStorage.setItem('quizConfig_questionType', quizConfig.questionType);
    } catch (e) {}
}

function updateModalConfigUI() {
    if (ui.configNumQuestionsVal) {
        ui.configNumQuestionsVal.textContent = `${quizConfig.numQuestions} câu`;
    }

    // Number of questions
    if (ui.configNumQuestionsGroup) {
        ui.configNumQuestionsGroup.querySelectorAll('.config-btn').forEach(btn => {
            const val = parseInt(btn.getAttribute('data-val'), 10);
            if (val === quizConfig.numQuestions) {
                btn.className = 'config-btn active py-2 px-1 rounded-xl text-xs font-bold border border-blue-500 bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 shadow-xs transition';
            } else {
                btn.className = 'config-btn py-2 px-1 rounded-xl text-xs font-bold border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-blue-950 transition';
            }
        });
    }

    // Difficulty
    if (ui.configDifficultyGroup) {
        ui.configDifficultyGroup.querySelectorAll('.config-btn').forEach(btn => {
            const val = btn.getAttribute('data-val');
            if (val === quizConfig.difficulty) {
                btn.className = 'config-btn active py-2 px-1.5 rounded-xl text-xs font-bold border border-blue-500 bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 shadow-xs transition flex flex-col items-center gap-0.5';
            } else {
                btn.className = 'config-btn py-2 px-1.5 rounded-xl text-xs font-bold border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition flex flex-col items-center gap-0.5';
            }
        });
    }

    // Type
    if (ui.configTypeGroup) {
        ui.configTypeGroup.querySelectorAll('.config-btn').forEach(btn => {
            const val = btn.getAttribute('data-val');
            if (val === quizConfig.questionType) {
                btn.className = 'config-btn active py-2 px-1.5 rounded-xl text-xs font-bold border border-blue-500 bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 shadow-xs transition flex flex-col items-center gap-0.5';
            } else {
                btn.className = 'config-btn py-2 px-1.5 rounded-xl text-xs font-bold border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition flex flex-col items-center gap-0.5';
            }
        });
    }
}

function openQuizConfigModal(topic) {
    selectedTopicForConfig = topic;
    if (ui.modalTopicTitle) {
        ui.modalTopicTitle.textContent = topic.title || 'Chủ đề ôn tập';
    }
    updateModalConfigUI();
    if (ui.quizConfigModal) {
        ui.quizConfigModal.classList.remove('hidden');
    }
}

function closeQuizConfigModal() {
    if (ui.quizConfigModal) {
        ui.quizConfigModal.classList.add('hidden');
    }
    selectedTopicForConfig = null;
}

function updateQuizModeUI() {
    if (ui.quizModeIcon) ui.quizModeIcon.textContent = isExamMode ? '📝' : '📖';
    if (ui.quizModeText) ui.quizModeText.textContent = isExamMode ? 'Thi thử' : 'Luyện tập';
    if (ui.quizModeBtn) {
        if (isExamMode) {
            ui.quizModeBtn.classList.remove('bg-blue-50', 'text-blue-600', 'border-blue-200', 'dark:bg-blue-950/40', 'dark:text-blue-400', 'dark:border-blue-800');
            ui.quizModeBtn.classList.add('bg-purple-50', 'text-purple-600', 'border-purple-200', 'dark:bg-purple-950/40', 'dark:text-purple-400', 'dark:border-purple-800');
        } else {
            ui.quizModeBtn.classList.remove('bg-purple-50', 'text-purple-600', 'border-purple-200', 'dark:bg-purple-950/40', 'dark:text-purple-400', 'dark:border-purple-800');
            ui.quizModeBtn.classList.add('bg-blue-50', 'text-blue-600', 'border-blue-200', 'dark:bg-blue-950/40', 'dark:text-blue-400', 'dark:border-blue-800');
        }
    }
}

function shuffleQuestionOptions(q) {
    if (!q || !Array.isArray(q.options) || q.options.length <= 1 || q._shuffled) return q;
    const correctVal = q.options[q.correct];
    const opts = [...q.options];
    for (let i = opts.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [opts[i], opts[j]] = [opts[j], opts[i]];
    }
    q.options = opts;
    q.correct = opts.indexOf(correctVal);
    q._shuffled = true;
    return q;
}

// Quiz Timer State
let quizTimerInterval = null;
let quizElapsedSeconds = 0;

function formatDuration(totalSeconds) {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function startQuizTimer(initialSeconds = 0) {
    stopQuizTimer();
    quizElapsedSeconds = initialSeconds;
    if (ui.quizTimerText) ui.quizTimerText.textContent = formatDuration(quizElapsedSeconds);
    quizTimerInterval = setInterval(() => {
        quizElapsedSeconds++;
        if (ui.quizTimerText) ui.quizTimerText.textContent = formatDuration(quizElapsedSeconds);
    }, 1000);
}

function stopQuizTimer() {
    if (quizTimerInterval) {
        clearInterval(quizTimerInterval);
        quizTimerInterval = null;
    }
}

// Helper: Quiz Progress Persistence via Redis Backend
async function saveQuizProgress() {
    if (typeof navigator !== 'undefined' && navigator.onLine === false) return;
    if (!currentTopic || !currentQuiz || currentQuiz.length === 0) return;

    const topicId = currentTopic.id;
    const data = {
        topic: currentTopic,
        quiz: currentQuiz,
        currentIndex: currentQuestionIndex,
        elapsedSeconds: quizElapsedSeconds,
        savedAt: Date.now()
    };
    savedProgressMap[topicId] = data;
    checkAndRenderResumeBanner();

    try {
        await fetch(`${API_BASE_URL}/api/study/progress`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: telegramData.id,
                topic_id: topicId,
                progress: data
            })
        });
    } catch (e) {
        console.warn('Cannot save quiz progress to Redis:', e);
    }
}

async function clearQuizProgress(topicId = null, refreshTopicsView = true) {
    const tid = topicId || (currentTopic ? currentTopic.id : null);
    if (tid) {
        delete savedProgressMap[tid];
    } else {
        savedProgressMap = {};
    }
    checkAndRenderResumeBanner();
    if (refreshTopicsView) {
        filterAndRenderTopics();
    }

    if (typeof navigator !== 'undefined' && navigator.onLine === false) return;
    try {
        const query = tid ? `?topic_id=${encodeURIComponent(tid)}` : '';
        await fetch(`${API_BASE_URL}/api/study/progress/${telegramData.id}${query}`, {
            method: 'DELETE'
        });
    } catch (e) {
        console.warn('Cannot clear quiz progress from Redis:', e);
    }
}

async function fetchSavedQuizProgress() {
    if (typeof navigator !== 'undefined' && navigator.onLine === false) return null;
    try {
        const res = await fetch(`${API_BASE_URL}/api/study/progress?telegram_id=${telegramData.id}`);
        if (!res.ok) return null;
        const data = await res.json();
        if (data && data.progress) {
            if (data.progress.topic && Array.isArray(data.progress.quiz)) {
                // Backwards compatibility for single progress object
                savedProgressMap = { [data.progress.topic.id]: data.progress };
            } else if (typeof data.progress === 'object') {
                savedProgressMap = data.progress;
            }
            return savedProgressMap;
        }
    } catch (e) {
        console.warn('Cannot fetch quiz progress from Redis:', e);
    }
    savedProgressMap = {};
    return null;
}

function getLatestSavedProgress() {
    const keys = Object.keys(savedProgressMap);
    if (keys.length === 0) return null;
    let latest = null;
    for (const key of keys) {
        const item = savedProgressMap[key];
        if (item && item.topic && Array.isArray(item.quiz) && item.quiz.length > 0) {
            if (!latest || (item.savedAt || 0) > (latest.savedAt || 0)) {
                latest = item;
            }
        }
    }
    return latest;
}

function checkAndRenderResumeBanner() {
    if (!ui.resumeBanner) return;
    const saved = getLatestSavedProgress();
    if (!saved) {
        ui.resumeBanner.classList.add('hidden');
        return;
    }
    const answeredCount = saved.quiz.filter(q => q.selected !== undefined).length;
    const total = saved.quiz.length;
    if (ui.resumeTitle) ui.resumeTitle.textContent = saved.topic.title || 'Chủ đề ôn tập';
    if (ui.resumeBadge) ui.resumeBadge.textContent = `Đã làm ${answeredCount}/${total} câu`;
    ui.resumeBanner.classList.remove('hidden');
}

function resumeSavedQuiz(savedData = null) {
    let saved = null;
    if (savedData && typeof savedData === 'object' && savedData.topic && Array.isArray(savedData.quiz)) {
        saved = savedData;
    } else {
        saved = getLatestSavedProgress();
    }
    if (!saved) return;
    currentTopic = saved.topic;
    currentQuiz = saved.quiz;
    currentQuestionIndex = (typeof saved.currentIndex === 'number' && saved.currentIndex >= 0 && saved.currentIndex < saved.quiz.length)
        ? saved.currentIndex
        : 0;

    startQuizTimer(saved.elapsedSeconds || 0);

    document.getElementById('quiz-content').classList.remove('hidden');
    ui.quizResults.classList.add('hidden');
    ui.quizProgress.classList.remove('hidden');
    if (ui.progressContainer) ui.progressContainer.classList.remove('hidden');

    if (currentTopic.id && currentTopic.id.startsWith('quick_review')) {
        ui.forceRefreshBtn.classList.remove('hidden');
        if (ui.clearCacheBtn) ui.clearCacheBtn.classList.add('hidden');
    } else {
        ui.forceRefreshBtn.classList.remove('hidden');
        if (ui.clearCacheBtn) ui.clearCacheBtn.classList.remove('hidden');
    }
    ui.showResultsBtn.classList.add('hidden');
    ui.quizDoneBtn.classList.add('hidden');

    ui.quizTopicTitle.textContent = currentTopic.title;
    renderQuestion();
    showView('quiz');
}


// Navigation
function showView(viewName) {
    Object.values(views).forEach(v => v.classList.add('hidden'));
    if (views[viewName]) {
        views[viewName].classList.remove('hidden');
        views[viewName].scrollTop = 0;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const isTimelineOnly = urlParams.get('view') === 'timeline';

    const tg = window.Telegram?.WebApp;
    if (tg && tg.BackButton && tg.isVersionAtLeast && tg.isVersionAtLeast('6.1')) {
        if (isTimelineOnly) {
            tg.BackButton.hide();
        } else if (viewName === 'quiz' || viewName === 'timeline') {
            tg.BackButton.show();
        } else {
            tg.BackButton.hide();
        }
    }
}


// Helper: Populate Course Dropdown
function populateCourseFilter() {
    const courses = [...new Set(allTopics.map(t => t.course).filter(Boolean))];
    ui.courseFilter.innerHTML = '<option value="">Tất cả môn học</option>';
    courses.forEach(course => {
        const opt = document.createElement('option');
        opt.value = course;
        opt.textContent = course;
        ui.courseFilter.appendChild(opt);
    });
}

// Helper: Filter & Render Topics
function filterAndRenderTopics() {
    const rawSearch = ui.searchInput.value;
    const searchQuery = rawSearch.toLowerCase().trim();
    const selectedCourse = ui.courseFilter.value;

    if (ui.clearSearchBtn) {
        if (rawSearch.length > 0) {
            ui.clearSearchBtn.classList.remove('hidden');
        } else {
            ui.clearSearchBtn.classList.add('hidden');
        }
    }

    const filtered = allTopics.filter(topic => {
        const matchesCourse = !selectedCourse || topic.course === selectedCourse;
        const matchesSearch = !searchQuery ||
            topic.title.toLowerCase().includes(searchQuery) ||
            (topic.chapter && topic.chapter.toLowerCase().includes(searchQuery)) ||
            (topic.course && topic.course.toLowerCase().includes(searchQuery));
        return matchesCourse && matchesSearch;
    });

    // Update Summary Header
    if (ui.topicsSummaryText) {
        const cachedCount = filtered.filter(t => t.has_cached_quiz).length;
        if (allTopics.length === 0) {
            ui.topicsSummaryText.textContent = 'Chưa có chủ đề nào';
        } else if (filtered.length === allTopics.length) {
            ui.topicsSummaryText.textContent = `${filtered.length} chủ đề • ${cachedCount} đã sẵn sàng`;
        } else {
            ui.topicsSummaryText.textContent = `Hiển thị ${filtered.length}/${allTopics.length} chủ đề • ${cachedCount} sẵn sàng`;
        }
    }

    // Dynamic Empty State description
    if (ui.noTopicsDesc) {
        if (searchQuery || selectedCourse) {
            ui.noTopicsDesc.textContent = 'Không có chủ đề nào khớp với từ khóa tìm kiếm hoặc môn học đã chọn.';
        } else {
            ui.noTopicsDesc.textContent = 'Tuyệt vời! Bạn đã hoàn thành ôn tập tất cả chủ đề.';
        }
    }

    renderTopics(filtered);
}

function showLoading(text, allowCancel = false) {
    ui.loadingText.textContent = text;
    if (ui.loadingProgressBar) ui.loadingProgressBar.style.width = '0%';
    if (ui.loadingPercentage) ui.loadingPercentage.textContent = '0%';
    if (ui.cancelLoadingBtn) {
        if (allowCancel) {
            ui.cancelLoadingBtn.classList.remove('hidden');
        } else {
            ui.cancelLoadingBtn.classList.add('hidden');
        }
    }
    showView('loading');
}

// API Calls
async function fetchTopics(forceRefresh = false) {
    showLoading('Đang tải danh sách chủ đề...');
    try {
        const res = await fetch(`${API_BASE_URL}/api/study/candidates?telegram_id=${telegramData.id}&force_refresh=${forceRefresh ? 'true' : 'false'}`);
        if (!res.ok) throw new Error('Lỗi tải danh sách chủ đề');
        const data = await res.json();
        allTopics = data.candidates || [];
        populateCourseFilter();
        filterAndRenderTopics();
    } catch (error) {
        console.error(error);
        alert('Lỗi tải chủ đề. Vui lòng kiểm tra kết nối.');
        allTopics = [];
        filterAndRenderTopics();
    }
}

async function startQuickReview(forceRefresh = false) {
    const selectedCourse = ui.courseFilter.value;
    const quickReviewId = selectedCourse ? `quick_review_${selectedCourse}` : 'quick_review';

    if (forceRefresh) {
        delete savedProgressMap[quickReviewId];
        clearQuizProgress(quickReviewId, false);
    } else {
        const saved = savedProgressMap[quickReviewId];
        if (saved && Array.isArray(saved.quiz) && saved.quiz.length > 0) {
            resumeSavedQuiz(saved);
            return;
        }
    }

    const courseParam = selectedCourse ? `?course=${encodeURIComponent(selectedCourse)}` : '';
    const loadingMsg = selectedCourse
        ? `Đang chuẩn bị toàn bộ câu hỏi cho "${selectedCourse}"...`
        : 'Đang chuẩn bị bộ câu hỏi tổng hợp...';

    showLoading(loadingMsg);
    try {
        const res = await fetch(`${API_BASE_URL}/api/study/quick-review${courseParam}`);
        if (!res.ok) throw new Error('Lỗi tải câu hỏi ôn tập nhanh');
        const data = await res.json();

        currentTopic = {
            id: data.id || quickReviewId,
            title: data.title || (selectedCourse ? `Ôn tập nhanh - ${selectedCourse}` : 'Ôn tập tổng hợp')
        };
        currentQuiz = (data.questions || []).map(shuffleQuestionOptions);
        currentQuestionIndex = 0;
        startQuizTimer(0);
        saveQuizProgress();

        document.getElementById('quiz-content').classList.remove('hidden');
        ui.quizResults.classList.add('hidden');
        ui.quizProgress.classList.remove('hidden');
        if (ui.progressContainer) {
            ui.progressContainer.classList.remove('hidden');
        }
        ui.forceRefreshBtn.classList.remove('hidden');
        ui.forceRefreshBtn.title = 'Tải lại bộ câu hỏi ôn tập nhanh';
        if (ui.clearCacheBtn) ui.clearCacheBtn.classList.add('hidden');
        ui.showResultsBtn.classList.add('hidden');
        ui.quizDoneBtn.classList.add('hidden');

        ui.quizTopicTitle.textContent = currentTopic.title;
        renderQuestion();
        showView('quiz');
    } catch (error) {
        console.error(error);
        alert('Lỗi tải câu hỏi ôn tập nhanh. Có thể không có chủ đề hoặc câu hỏi nào thuộc môn học đã chọn.');
        showView('topics');
    }
}

async function startQuiz(topic, forceRefresh = false, customConfig = null) {
    if (!forceRefresh && savedProgressMap[topic.id]) {
        const saved = savedProgressMap[topic.id];
        if (saved && Array.isArray(saved.quiz) && saved.quiz.length > 0) {
            resumeSavedQuiz(saved);
            return;
        }
    }

    currentTopic = topic;
    const cfg = customConfig || quizConfig;
    const nq = cfg.numQuestions || 15;
    const diff = cfg.difficulty || 'medium';
    const qType = cfg.questionType || 'balanced';

    const diffLabel = { 'easy': 'Cơ bản', 'medium': 'Chuẩn thi', 'hard': 'Nâng cao' }[diff] || 'Chuẩn thi';
    showLoading(`Đang tạo ${nq} câu hỏi [${diffLabel}] cho "${topic.title}"...`, true);

    if (singleQuizAbortController) {
        singleQuizAbortController.abort();
    }
    singleQuizAbortController = new AbortController();

    let aiTimer = null;
    let currentPercent = 0;

    function updateProgress(percentage, text) {
        currentPercent = percentage;
        if (ui.loadingProgressBar) ui.loadingProgressBar.style.width = `${percentage}%`;
        if (ui.loadingPercentage) ui.loadingPercentage.textContent = `${percentage}%`;
        if (ui.loadingText) ui.loadingText.textContent = text;
    }

    try {
        const res = await fetch(`${API_BASE_URL}/api/study/quiz`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: singleQuizAbortController.signal,
            body: JSON.stringify({
                topic_id: topic.id,
                force_refresh: forceRefresh,
                num_questions: nq,
                difficulty: diff,
                question_type: qType
            })
        });

        if (!res.ok) throw new Error('Lỗi tạo câu hỏi trắc nghiệm');

        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let quizData = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.trim()) continue;
                let event;
                try {
                    event = JSON.parse(line);
                } catch (parseError) {
                    console.warn('⚠️ Bỏ qua dòng JSON không hợp lệ từ server:', line, parseError);
                    continue;
                }
                if (event.type === 'progress') {
                    if (aiTimer) {
                        clearInterval(aiTimer);
                        aiTimer = null;
                    }
                    updateProgress(event.percentage || 0, event.details || '');
                } else if (event.type === 'result') {
                    quizData = event.data;
                } else if (event.type === 'error') {
                    throw new Error(event.message);
                }
            }
        }

        if (aiTimer) {
            clearInterval(aiTimer);
            aiTimer = null;
        }

        if (!quizData) {
            throw new Error('Không thể phân tích dữ liệu câu hỏi từ server');
        }

        // Handle varying response formats. Assuming array of Q&A objects.
        let questions = [];
        if (Array.isArray(quizData)) {
            questions = quizData;
        } else if (quizData.questions) {
            questions = quizData.questions;
        } else if (quizData.quiz) {
            questions = quizData.quiz;
        } else {
            questions = [{ question: "Không thể đọc cấu trúc câu hỏi.", answer: JSON.stringify(quizData) }];
        }

        if (questions.length === 0) {
            alert('Không có câu hỏi nào được tạo ra.');
            showView('topics');
            return;
        }

        currentQuiz = questions.map(shuffleQuestionOptions);
        currentQuestionIndex = 0;
        startQuizTimer(0);
        saveQuizProgress();

        if (currentTopic && currentTopic.id && !currentTopic.id.startsWith('quick_review')) {
            const t = allTopics.find(x => x.id === currentTopic.id);
            if (t) t.has_cached_quiz = true;
        }

        // Reset results UI to initial quiz state
        document.getElementById('quiz-content').classList.remove('hidden');
        ui.quizResults.classList.add('hidden');
        ui.quizProgress.classList.remove('hidden');
        if (ui.progressContainer) {
            ui.progressContainer.classList.remove('hidden');
        }
        ui.forceRefreshBtn.classList.remove('hidden');
        if (ui.clearCacheBtn) ui.clearCacheBtn.classList.remove('hidden');
        ui.showResultsBtn.classList.add('hidden');
        ui.quizDoneBtn.classList.add('hidden');

        ui.quizTopicTitle.textContent = topic.title;
        renderQuestion();
        showView('quiz');

    } catch (error) {
        if (aiTimer) {
            clearInterval(aiTimer);
            aiTimer = null;
        }
        if (error.name === 'AbortError') {
            console.log('Quiz generation cancelled by user.');
            showView('topics');
            return;
        }
        console.error(error);
        alert(error.message || 'Lỗi khi tạo bộ câu hỏi.');
        showView('topics');
    } finally {
        singleQuizAbortController = null;
    }
}

async function clearQuizCache() {
    if (!currentTopic || currentTopic.id === 'quick_review') return;
    if (!confirm(`Bạn có chắc muốn xóa cache cho chủ đề "${currentTopic.title}"?`)) return;

    showLoading('Đang xóa cache Redis...');
    try {
        const res = await fetch(`${API_BASE_URL}/api/study/quiz/${currentTopic.id}`, {
            method: 'DELETE'
        });
        if (!res.ok) throw new Error('Lỗi xóa cache');
        delete savedProgressMap[currentTopic.id];
        checkAndRenderResumeBanner();
        const t = allTopics.find(x => x.id === currentTopic.id);
        if (t) t.has_cached_quiz = false;
        alert('Đã xóa cache thành công! Đang tải lại câu hỏi mới...');
        startQuiz(currentTopic, true);
    } catch (error) {
        console.error(error);
        alert('Lỗi xóa cache. Vui lòng thử lại.');
        showView('quiz');
    }
}

async function clearQuizCacheForTopic(topic) {
    if (!topic || !topic.id || topic.id.startsWith('quick_review')) return;
    if (!confirm(`Bạn có chắc muốn xóa cache cho chủ đề "${topic.title}"?`)) return;

    showLoading('Đang xóa cache Redis...');
    try {
        const res = await fetch(`${API_BASE_URL}/api/study/quiz/${topic.id}`, {
            method: 'DELETE'
        });
        if (!res.ok) throw new Error('Lỗi xóa cache');
        delete savedProgressMap[topic.id];
        checkAndRenderResumeBanner();
        const t = allTopics.find(x => x.id === topic.id);
        if (t) t.has_cached_quiz = false;
        alert('Đã xóa cache thành công!');
        filterAndRenderTopics();
        showView('topics');
    } catch (error) {
        console.error(error);
        alert('Lỗi xóa cache. Vui lòng thử lại.');
        showView('topics');
    }
}

async function updateStatus(status) {
    showLoading('Đang lưu kết quả...');
    try {
        const res = await fetch(`${API_BASE_URL}/api/study/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: telegramData.id,
                topic_id: currentTopic.id,
                status: status
            })
        });

        if (!res.ok) {
            throw new Error(`Server trả về lỗi ${res.status}`);
        }

        const responseText = await res.text();
        let responseJson = {};
        try {
            responseJson = JSON.parse(responseText);
        } catch (e) {
            console.warn("Could not parse response JSON, treating as empty object");
        }

        showView('topics');
    } catch (error) {
        console.error('Update status error:', error);
        alert('❌ Không thể lưu kết quả: ' + error.message);
        showView('topics');
    }
}

async function markTopicAsMastered(topicId, cardElement) {
    const masteredBtn = cardElement.querySelector('.mastered-btn');
    if (masteredBtn) {
        masteredBtn.disabled = true;
        masteredBtn.innerHTML = '<span>⏱</span><span>Đang lưu...</span>';
    }

    try {
        const res = await fetch(`${API_BASE_URL}/api/study/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: telegramData.id,
                topic_id: topicId,
                status: 'da_nam_vung'
            })
        });

        if (!res.ok) throw new Error('Lỗi cập nhật trạng thái');

        const tg = window.Telegram?.WebApp;
        if (tg?.HapticFeedback) {
            try {
                tg.HapticFeedback.notificationOccurred('success');
            } catch (e) {
                console.warn("Haptic feedback error:", e);
            }
        }

        allTopics = allTopics.filter(t => t.id !== topicId);
        // Clear cached quick review progress so newly mastered topics do not linger in quick review
        Object.keys(savedProgressMap).forEach(key => {
            if (key.startsWith('quick_review')) {
                delete savedProgressMap[key];
            }
        });

        cardElement.style.transition = 'all 0.3s ease-out';
        cardElement.style.opacity = '0';
        cardElement.style.transform = 'scale(0.95)';
        setTimeout(() => {
            cardElement.remove();
            if (ui.topicsList.children.length === 0) {
                ui.topicsList.classList.add('hidden');
                ui.noTopics.classList.remove('hidden');
            }
        }, 300);

    } catch (error) {
        console.error(error);
        alert('Lỗi khi cập nhật trạng thái.');
        if (masteredBtn) {
            masteredBtn.disabled = false;
            masteredBtn.innerHTML = `
                <svg class="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <span>Đã nắm vững</span>
            `;
        }
    }
}

// UI Rendering
function renderTopics(topics) {
    ui.topicsList.innerHTML = '';

    if (topics.length === 0) {
        ui.topicsList.classList.add('hidden');
        ui.noTopics.classList.remove('hidden');
        checkAndRenderResumeBanner();
        showView('topics');
        return;
    }

    ui.topicsList.classList.remove('hidden');
    ui.noTopics.classList.add('hidden');

    topics.forEach(topic => {
        const isCached = !!topic.has_cached_quiz;
        const card = document.createElement('div');
        const cardClasses = isCached
            ? 'w-full bg-indigo-50/50 dark:bg-indigo-950/30 p-4 rounded-xl shadow-sm border border-indigo-200 dark:border-indigo-800/80 hover:shadow-md transition duration-200 flex flex-col space-y-3'
            : 'w-full bg-gray-50/80 dark:bg-gray-900/60 p-4 rounded-xl shadow-xs border border-dashed border-gray-300 dark:border-gray-800 hover:shadow-sm opacity-85 transition duration-200 flex flex-col space-y-3';
        card.className = cardClasses;

        let chapterHtml = '';
        const chapterList = (Array.isArray(topic.chapters) && topic.chapters.length > 0)
            ? topic.chapters
            : (topic.chapter ? [topic.chapter] : []);
        if (chapterList.length > 0) {
            const badgeClass = isCached
                ? 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700/80'
                : 'bg-gray-200/60 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 border-gray-300/60 dark:border-gray-700/40';
            const badges = chapterList.map(ch => `<span class="${badgeClass} text-[10px] font-medium px-2 py-0.5 rounded border">📍 ${escapeHtml(ch)}</span>`).join('');
            chapterHtml = `<div class="flex flex-wrap items-center gap-1.5">${badges}</div>`;
        }

        let dateHtml = '';
        if (topic.updated_at) {
            let dateStr = topic.updated_at;
            try {
                const d = new Date(topic.updated_at);
                if (!isNaN(d.getTime())) {
                    const h = String(d.getHours()).padStart(2, '0');
                    const m = String(d.getMinutes()).padStart(2, '0');
                    dateStr = `${h}:${m} ${d.toLocaleDateString('vi-VN')}`;
                }
            } catch (e) {}
            dateHtml = `<span class="text-[10px] text-gray-400 dark:text-gray-500 font-normal shrink-0 select-none">${escapeHtml(dateStr)}</span>`;
        }

        const courseHtml = topic.course
            ? `<span class="text-[10px] font-bold uppercase tracking-wider ${isCached ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'} truncate max-w-[200px]">${escapeHtml(topic.course)}</span>`
            : '<span></span>';

        const titleClasses = isCached
            ? 'font-semibold text-gray-900 dark:text-gray-100 text-sm md:text-base leading-tight'
            : 'font-medium text-gray-500 dark:text-gray-400 text-sm md:text-base leading-tight';

        card.innerHTML = `
            <div class="topic-content cursor-pointer flex-1 flex flex-col space-y-1.5">
                <div class="flex justify-between items-center gap-2">
                    ${courseHtml}
                    ${dateHtml}
                </div>
                <span class="${titleClasses}">${escapeHtml(topic.title)}</span>
                ${chapterHtml}
            </div>
            <div class="flex justify-between items-center pt-2.5 border-t border-gray-100 dark:border-gray-800/80 mt-0.5 relative">
                <div class="relative">
                    <button class="topic-menu-btn w-8 h-8 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition flex items-center justify-center text-base" title="Tùy chọn khác">
                        ⋮
                    </button>
                    <div class="topic-menu-dropdown hidden absolute left-0 bottom-full mb-1 w-48 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-20 text-xs">
                        <button class="open-notion-btn w-full text-left px-3 py-2 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-750 flex items-center gap-2 transition">
                            <span>📖</span><span>Xem trên Notion</span>
                        </button>
                        <button class="config-quiz-btn w-full text-left px-3 py-2 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-750 flex items-center gap-2 transition">
                            <span>⚙️</span><span>Tùy chỉnh câu hỏi</span>
                        </button>
                        <button class="regenerate-quiz-btn w-full text-left px-3 py-2 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/30 flex items-center gap-2 transition">
                            <span>🔄</span><span>Tạo mới câu hỏi</span>
                        </button>
                        <button class="restart-quiz-btn w-full text-left px-3 py-2 text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30 flex items-center gap-2 transition ${savedProgressMap[topic.id] ? '' : 'hidden'}">
                            <span>⏱️</span><span>Làm lại từ đầu</span>
                        </button>
                        <button class="clear-cache-topic-btn w-full text-left px-3 py-2 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 flex items-center gap-2 transition border-t border-gray-100 dark:border-gray-700/60">
                            <span>🗑️</span><span>Xóa cache quiz</span>
                        </button>
                    </div>
                </div>
                <div>
                    <button class="mastered-btn bg-emerald-50/70 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:hover:bg-emerald-900/50 text-emerald-700 dark:text-emerald-400 text-xs font-semibold px-3 py-1 rounded-full border border-emerald-300/80 dark:border-emerald-700/60 hover:border-emerald-400 transition-all duration-150 flex items-center gap-1.5 active:scale-95 shadow-2xs">
                        <svg class="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                        <span>Đã nắm vững</span>
                    </button>
                </div>
            </div>
        `;

        const openQuiz = () => {
            if (!topic.has_cached_quiz && !savedProgressMap[topic.id]) {
                openQuizConfigModal(topic);
            } else {
                startQuiz(topic);
            }
        };
        card.querySelector('.topic-content').onclick = openQuiz;

        const menuBtn = card.querySelector('.topic-menu-btn');
        const menuDropdown = card.querySelector('.topic-menu-dropdown');

        menuBtn.onclick = (e) => {
            e.stopPropagation();
            // Đóng các menu khác trước khi mở menu này
            document.querySelectorAll('.topic-menu-dropdown').forEach(el => {
                if (el !== menuDropdown) el.classList.add('hidden');
            });

            const isOpening = menuDropdown.classList.contains('hidden');
            if (isOpening) {
                // Tự động căn vị trí dropdown hiển thị phía dưới nếu phía trên không đủ chỗ
                const btnRect = menuBtn.getBoundingClientRect();
                const listRect = ui.topicsList.getBoundingClientRect();
                const spaceAbove = btnRect.top - listRect.top;

                // Chiều cao ước tính menu là ~200px
                if (spaceAbove < 200) {
                    menuDropdown.classList.remove('bottom-full', 'mb-1');
                    menuDropdown.classList.add('top-full', 'mt-1');
                } else {
                    menuDropdown.classList.remove('top-full', 'mt-1');
                    menuDropdown.classList.add('bottom-full', 'mb-1');
                }
            }

            menuDropdown.classList.toggle('hidden');
        };

        const openNotionBtn = card.querySelector('.open-notion-btn');
        if (openNotionBtn) {
            openNotionBtn.onclick = (e) => {
                e.stopPropagation();
                menuDropdown.classList.add('hidden');
                const notionUrl = topic.url || `https://notion.so/${(topic.id || '').replace(/-/g, '')}`;
                openExternalLink(notionUrl);
            };
        }

        card.querySelector('.config-quiz-btn').onclick = (e) => {
            e.stopPropagation();
            menuDropdown.classList.add('hidden');
            openQuizConfigModal(topic);
        };

        const regenerateBtn = card.querySelector('.regenerate-quiz-btn');
        if (regenerateBtn) {
            regenerateBtn.onclick = (e) => {
                e.stopPropagation();
                menuDropdown.classList.add('hidden');
                if (confirm(`Bạn có chắc muốn tạo lại bộ câu hỏi mới cho "${topic.title}"?`)) {
                    startQuiz(topic, true);
                }
            };
        }

        const restartBtn = card.querySelector('.restart-quiz-btn');
        if (restartBtn) {
            restartBtn.onclick = async (e) => {
                e.stopPropagation();
                menuDropdown.classList.add('hidden');
                if (confirm(`Bạn có chắc muốn hủy phiên làm dở và làm lại từ câu 1 cho "${topic.title}"?`)) {
                    await clearQuizProgress(topic.id, false);
                    startQuiz(topic, false);
                }
            };
        }

        card.querySelector('.mastered-btn').onclick = (e) => {
            e.stopPropagation();
            menuDropdown.classList.add('hidden');
            if (confirm(`Đánh dấu "${topic.title}" là đã nắm vững?`)) {
                markTopicAsMastered(topic.id, card);
            }
        };

        card.querySelector('.clear-cache-topic-btn').onclick = (e) => {
            e.stopPropagation();
            menuDropdown.classList.add('hidden');
            clearQuizCacheForTopic(topic);
        };

        ui.topicsList.appendChild(card);
    });

    checkAndRenderResumeBanner();
    showView('topics');
}

function renderQuestion(animate = true) {
    ui.statusBtns.classList.add('hidden');

    const quizContent = document.getElementById('quiz-content');
    if (quizContent) {
        if (animate) {
            quizContent.classList.remove('fade-in');
            void quizContent.offsetWidth; // trigger reflow
            quizContent.classList.add('fade-in');
        } else {
            quizContent.classList.remove('fade-in');
        }
    }

    const q = currentQuiz[currentQuestionIndex];

    // Update Flag Button state
    if (ui.flagQuestionBtn) {
        if (q.flagged) {
            ui.flagQuestionBtn.classList.remove('text-gray-400', 'bg-white', 'dark:bg-gray-900');
            ui.flagQuestionBtn.classList.add('text-amber-500', 'bg-amber-50', 'dark:bg-amber-950/40', 'border-amber-300', 'dark:border-amber-700');
        } else {
            ui.flagQuestionBtn.classList.add('text-gray-400', 'bg-white', 'dark:bg-gray-900');
            ui.flagQuestionBtn.classList.remove('text-amber-500', 'bg-amber-50', 'dark:bg-amber-950/40', 'border-amber-300', 'dark:border-amber-700');
        }
    }

    // Fallback cho câu hỏi bị lỗi dữ liệu
    const questionText = q.question || q.q || '⚠️ Nội dung câu hỏi bị thiếu';
    if (currentTopic && currentTopic.id && currentTopic.id.startsWith('quick_review') && q.topic_title) {
        ui.questionText.innerHTML = `
            <div class="text-[10px] text-blue-500 font-bold uppercase tracking-wider mb-2">📌 Chủ đề: ${escapeHtml(q.topic_title)}</div>
            <div>${escapeHtml(questionText)}</div>
        `;
    } else {
        ui.questionText.textContent = questionText;
    }
    ui.optionsContainer.innerHTML = '';
    ui.explanationBox.classList.add('hidden');
    ui.quizProgress.textContent = `${currentQuestionIndex + 1}/${currentQuiz.length}`;

    // Update progress bar
    if (ui.progressBar && ui.progressContainer) {
        const progressPercent = ((currentQuestionIndex + 1) / currentQuiz.length) * 100;
        ui.progressBar.style.width = `${progressPercent}%`;
    }

    // Render interactive dot progress indicator
    if (ui.dotContainer) {
        ui.dotContainer.innerHTML = '';
        currentQuiz.forEach((item, idx) => {
            const dot = document.createElement('button');
            const isActive = idx === currentQuestionIndex;
            const isAnswered = item.selected !== undefined;
            const isCorrect = item.selected === item.correct;
            const isFlagged = !!item.flagged;

            let dotClasses = 'w-7 h-7 rounded-lg text-xs font-bold transition-all duration-200 flex items-center justify-center relative cursor-pointer active:scale-90 ';

            if (isActive) {
                dotClasses += 'bg-blue-500 text-white ring-2 ring-blue-300 dark:ring-blue-800 shadow-sm ';
            } else if (isAnswered) {
                if (isExamMode) {
                    dotClasses += 'bg-purple-100 dark:bg-purple-950/50 text-purple-700 dark:text-purple-400 border border-purple-300 dark:border-purple-800 ';
                } else if (isCorrect) {
                    dotClasses += 'bg-green-100 dark:bg-green-950/50 text-green-700 dark:text-green-400 border border-green-300 dark:border-green-800 ';
                } else {
                    dotClasses += 'bg-red-100 dark:bg-red-950/50 text-red-700 dark:text-red-400 border border-red-300 dark:border-red-800 ';
                }
            } else {
                dotClasses += 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 ';
            }

            dot.className = dotClasses;
            dot.textContent = idx + 1;
            dot.title = `Câu ${idx + 1}${isFlagged ? ' (Đã gắn cờ)' : ''}`;

            if (isFlagged) {
                const flagMarker = document.createElement('span');
                flagMarker.className = 'absolute -top-1 -right-1 text-[9px] select-none';
                flagMarker.textContent = '🚩';
                dot.appendChild(flagMarker);
            }

            dot.onclick = () => {
                currentQuestionIndex = idx;
                saveQuizProgress();
                renderQuestion();
            };

            ui.dotContainer.appendChild(dot);
        });
    }

    const options = q.options || [];
    const optionLabels = ['A', 'B', 'C', 'D', 'E', 'F'];

    if (options.length === 0) {
        // Fallback khi không có đáp án nào
        const fallbackBtn = document.createElement('button');
        fallbackBtn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium border-red-300 bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 whitespace-normal break-words';
        fallbackBtn.textContent = '⚠️ Dữ liệu đáp án bị lỗi. Vui lòng tạo lại câu hỏi.';
        ui.optionsContainer.appendChild(fallbackBtn);
    } else {
        options.forEach((opt, idx) => {
            const btn = document.createElement('button');
            const letter = optionLabels[idx] || (idx + 1);
            const isAnswered = q.selected !== undefined;

            let containerClasses = 'w-full text-left p-3.5 rounded-xl border-2 font-medium transition-all duration-200 ease-out active:scale-[0.99] shadow-sm flex items-start gap-3 whitespace-normal break-words ';
            let badgeClasses = 'w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 transition-colors ';

            if (isAnswered) {
                if (isExamMode) {
                    if (idx === q.selected) {
                        containerClasses += 'border-purple-500 dark:border-purple-600 bg-purple-50/80 dark:bg-purple-950/30 text-purple-900 dark:text-purple-200 font-bold';
                        badgeClasses += 'bg-purple-500 text-white';
                    } else {
                        containerClasses += 'border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400 opacity-50';
                        badgeClasses += 'bg-gray-100 dark:bg-gray-800 text-gray-500';
                    }
                } else {
                    if (idx === q.correct) {
                        containerClasses += 'border-green-500 dark:border-green-600 bg-green-50/80 dark:bg-green-950/30 text-green-900 dark:text-green-200 font-bold';
                        badgeClasses += 'bg-green-500 text-white';
                    } else if (idx === q.selected) {
                        containerClasses += 'border-red-500 dark:border-red-600 bg-red-50/80 dark:bg-red-950/30 text-red-900 dark:text-red-200 font-bold line-through';
                        badgeClasses += 'bg-red-500 text-white';
                    } else {
                        containerClasses += 'border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400 opacity-50';
                        badgeClasses += 'bg-gray-100 dark:bg-gray-800 text-gray-500';
                    }
                }
            } else {
                containerClasses += 'border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-blue-400 dark:hover:border-blue-500 hover:shadow-md text-gray-700 dark:text-gray-300';
                badgeClasses += 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 group-hover:bg-blue-100';
            }

            btn.className = containerClasses;
            btn.innerHTML = `
                <span class="${badgeClasses}">${letter}</span>
                <span class="flex-1 pt-0.5 leading-snug">${escapeHtml(opt)}</span>
            `;

            btn.onclick = () => {
                if (q.selected !== undefined) return;
                q.selected = idx;

                // Trigger Telegram Web App Haptic Feedback / Web Vibration
                const tg = window.Telegram?.WebApp;
                if (tg?.HapticFeedback) {
                    try {
                        if (isExamMode) {
                            tg.HapticFeedback.impactOccurred('medium');
                        } else if (idx === q.correct) {
                            tg.HapticFeedback.notificationOccurred('success');
                        } else {
                            tg.HapticFeedback.notificationOccurred('error');
                        }
                    } catch (e) {
                        console.warn("Haptic feedback error:", e);
                    }
                } else if (typeof navigator !== 'undefined' && navigator.vibrate) {
                    try {
                        navigator.vibrate(idx === q.correct ? 50 : [50, 50, 50]);
                    } catch (e) {}
                }

                saveQuizProgress();
                renderQuestion(false);

                if (currentQuestionIndex < currentQuiz.length - 1) {
                    ui.nextBtn.classList.remove('hidden');
                } else {
                    ui.showResultsBtn.classList.remove('hidden');
                }
            };

            ui.optionsContainer.appendChild(btn);
        });
    }

    if (q.selected !== undefined && q.explanation && !isExamMode) {
        ui.explanationBox.innerHTML = `<div class="flex items-start gap-2.5">
            <span class="text-xl select-none">💡</span>
            <div>
                <div class="font-bold text-blue-800 dark:text-blue-400 mb-0.5 text-xs uppercase tracking-wider">Giải thích chi tiết</div>
                <div>${escapeHtml(q.explanation)}</div>
            </div>
        </div>`;
        ui.explanationBox.classList.remove('hidden');
    }

    if (currentQuestionIndex > 0) {
        ui.prevBtn.classList.remove('hidden');
    } else {
        ui.prevBtn.classList.add('hidden');
    }

    if (q.selected !== undefined) {
        if (currentQuestionIndex < currentQuiz.length - 1) {
            ui.nextBtn.classList.remove('hidden');
            ui.showResultsBtn.classList.add('hidden');
        } else {
            ui.nextBtn.classList.add('hidden');
            ui.showResultsBtn.classList.remove('hidden');
        }
    } else {
        ui.nextBtn.classList.add('hidden');
        ui.showResultsBtn.classList.add('hidden');
    }

    renderMath();
}

function showQuizResults() {
    stopQuizTimer();

    const tg = window.Telegram?.WebApp;
    if (tg?.HapticFeedback) {
        try {
            tg.HapticFeedback.notificationOccurred('success');
        } catch (e) {
            console.warn("Haptic feedback error:", e);
        }
    }

    document.getElementById('quiz-content').classList.add('hidden');
    ui.quizResults.classList.remove('hidden');

    if (ui.progressContainer) {
        ui.progressContainer.classList.add('hidden');
    }

    ui.quizProgress.classList.add('hidden');
    ui.prevBtn.classList.add('hidden');
    ui.nextBtn.classList.add('hidden');
    ui.showResultsBtn.classList.add('hidden');
    ui.forceRefreshBtn.classList.add('hidden');

    const total = currentQuiz.length;
    const correct = currentQuiz.filter(q => q.selected === q.correct).length;
    const percentage = Math.round((correct / total) * 100);
    const mistakes = currentQuiz.map((q, idx) => ({ q, idx })).filter(item => item.q.selected !== item.q.correct);

    ui.resultsScore.textContent = `${correct} / ${total}`;
    ui.resultsPercentage.textContent = `${percentage}%`;
    if (ui.resultsTime) ui.resultsTime.textContent = formatDuration(quizElapsedSeconds);

    let feedback = '';
    if (percentage === 100) {
        feedback = '🌟 Xuất sắc! Bạn đã trả lời đúng tất cả các câu hỏi. Hãy tiếp tục phát huy!';
    } else if (percentage >= 80) {
        feedback = '🎉 Rất tốt! Bạn nắm vững hầu hết các kiến thức trong chủ đề này.';
    } else if (percentage >= 50) {
        feedback = '👍 Khá tốt! Hãy cố gắng ôn tập thêm một chút để đạt điểm tối đa nhé.';
    } else {
        feedback = '💪 Cần cố gắng thêm! Hãy đọc kỹ phần giải thích của mỗi câu hỏi để nắm vững kiến thức.';
    }
    ui.resultsFeedback.textContent = feedback;

    // Setup mistakes buttons
    if (ui.mistakesCount) ui.mistakesCount.textContent = mistakes.length;
    if (mistakes.length > 0) {
        if (ui.reviewMistakesBtn) ui.reviewMistakesBtn.classList.remove('hidden');
        if (ui.retakeMistakesBtn) ui.retakeMistakesBtn.classList.remove('hidden');
    } else {
        if (ui.reviewMistakesBtn) ui.reviewMistakesBtn.classList.add('hidden');
        if (ui.retakeMistakesBtn) ui.retakeMistakesBtn.classList.add('hidden');
    }

    // Render results grid matrix
    if (ui.resultsGrid) {
        ui.resultsGrid.innerHTML = '';
        currentQuiz.forEach((q, idx) => {
            const btn = document.createElement('button');
            const isCorrect = q.selected === q.correct;
            const isFlagged = !!q.flagged;

            let btnClasses = 'py-2 px-1 rounded-xl font-bold text-xs flex flex-col items-center justify-center gap-0.5 transition active:scale-95 border ';
            if (isCorrect) {
                btnClasses += 'bg-green-50 dark:bg-green-950/40 text-green-700 dark:text-green-400 border-green-300 dark:border-green-800 hover:bg-green-100';
            } else {
                btnClasses += 'bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-400 border-red-300 dark:border-red-800 hover:bg-red-100';
            }

            btn.className = btnClasses;
            btn.innerHTML = `
                <span class="text-[10px] opacity-75">Câu ${idx + 1}</span>
                <span>${isCorrect ? '✅' : '❌'}${isFlagged ? ' 🚩' : ''}</span>
            `;

            btn.onclick = () => {
                reviewAnswers(idx);
            };

            ui.resultsGrid.appendChild(btn);
        });
    }

    clearQuizProgress(null, false);

    ui.reviewAnswersBtn.classList.remove('hidden');

    if (currentTopic.id === 'quick_review') {
        ui.statusBtns.classList.add('hidden');
        ui.quizDoneBtn.classList.remove('hidden');
    } else {
        ui.statusBtns.classList.remove('hidden');
        ui.quizDoneBtn.classList.add('hidden');
    }
}

function reviewAnswers(targetIndex = 0) {
    currentQuestionIndex = typeof targetIndex === 'number' ? targetIndex : 0;
    document.getElementById('quiz-content').classList.remove('hidden');
    ui.quizResults.classList.add('hidden');
    ui.quizProgress.classList.remove('hidden');
    if (ui.progressContainer) {
        ui.progressContainer.classList.remove('hidden');
    }
    ui.showResultsBtn.classList.add('hidden');
    ui.reviewAnswersBtn.classList.add('hidden');
    ui.quizDoneBtn.classList.add('hidden');
    renderQuestion();
}

function reviewFirstMistake() {
    const firstMistakeIdx = currentQuiz.findIndex(q => q.selected !== q.correct);
    if (firstMistakeIdx !== -1) {
        reviewAnswers(firstMistakeIdx);
    } else {
        reviewAnswers(0);
    }
}

function retakeMistakes() {
    const mistakesOnly = currentQuiz
        .filter(q => q.selected !== q.correct)
        .map(q => {
            const copy = { ...q, selected: undefined, _shuffled: false };
            return shuffleQuestionOptions(copy);
        });

    if (mistakesOnly.length === 0) {
        alert('Bạn không có câu sai nào!');
        return;
    }

    currentQuiz = mistakesOnly;
    currentQuestionIndex = 0;
    startQuizTimer(0);
    saveQuizProgress();

    document.getElementById('quiz-content').classList.remove('hidden');
    ui.quizResults.classList.add('hidden');
    ui.quizProgress.classList.remove('hidden');
    if (ui.progressContainer) ui.progressContainer.classList.remove('hidden');
    ui.showResultsBtn.classList.add('hidden');
    ui.quizDoneBtn.classList.add('hidden');
    renderQuestion();
}

function shareQuizResults() {
    if (!currentTopic || !currentQuiz || currentQuiz.length === 0) return;
    const total = currentQuiz.length;
    const correct = currentQuiz.filter(q => q.selected === q.correct).length;
    const percentage = Math.round((correct / total) * 100);
    const timeStr = formatDuration(quizElapsedSeconds);

    const shareText = `📊 Kết quả ôn tập: ${currentTopic.title}\n🏆 Điểm số: ${correct}/${total} (${percentage}%)\n⏱️ Thời gian: ${timeStr}\n\n#UEHStudyAssistant #Quiz`;

    const triggerCopySuccess = () => {
        if (ui.shareResultsBtn) {
            const orig = ui.shareResultsBtn.innerHTML;
            ui.shareResultsBtn.innerHTML = '✅ Đã sao chép!';
            setTimeout(() => { ui.shareResultsBtn.innerHTML = orig; }, 1800);
        }
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(shareText).then(triggerCopySuccess).catch(() => {
            const ta = document.createElement('textarea');
            ta.value = shareText;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            triggerCopySuccess();
        });
    } else {
        const ta = document.createElement('textarea');
        ta.value = shareText;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        triggerCopySuccess();
    }
}

function toggleFlagCurrentQuestion() {
    const q = currentQuiz[currentQuestionIndex];
    if (!q) return;
    q.flagged = !q.flagged;
    saveQuizProgress();
    renderQuestion();
}

function copyCurrentQuestion() {
    const q = currentQuiz[currentQuestionIndex];
    if (!q) return;

    const questionText = q.question || q.q || '';
    const options = (q.options || []).map((opt, i) => opt).join('\n');
    const answerLabel = q.selected !== undefined
        ? `\n\n📌 Đáp án đúng: ${q.options[q.correct] || ''}`
        : '';
    const explanation = q.explanation
        ? `\n💡 Giải thích: ${q.explanation}`
        : '';

    const text = `📝 Câu ${currentQuestionIndex + 1}: ${questionText}\n\n${options}${answerLabel}${explanation}`;

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            const orig = ui.copyQuestionBtn.textContent;
            ui.copyQuestionBtn.textContent = '✅';
            setTimeout(() => { ui.copyQuestionBtn.textContent = orig; }, 1500);
        }).catch(() => {
            // Fallback
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            const orig = ui.copyQuestionBtn.textContent;
            ui.copyQuestionBtn.textContent = '✅';
            setTimeout(() => { ui.copyQuestionBtn.textContent = orig; }, 1500);
        });
    } else {
        // Fallback for older WebViews
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        const orig = ui.copyQuestionBtn.textContent;
        ui.copyQuestionBtn.textContent = '✅';
        setTimeout(() => { ui.copyQuestionBtn.textContent = orig; }, 1500);
    }
}

function getTimestamp(dateStr) {
    const { day, month, time } = parseDateParts(dateStr);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const mIdx = months.indexOf(month);
    const m = mIdx !== -1 ? mIdx : 0;
    const d = parseInt(day, 10) || 1;
    const [h, min] = time ? time.split(':').map(Number) : [0, 0];
    return new Date(2026, m, d, h, min).getTime();
}

function populateTimelineFilters() {
    // 1. Populate courses
    const courses = [...new Set(currentTimeline.map(item => item.course).filter(Boolean))].sort();
    ui.timelineCourseFilter.innerHTML = '<option value="">Tất cả môn</option>';
    courses.forEach(course => {
        const option = document.createElement('option');
        option.value = course;
        option.textContent = course;
        ui.timelineCourseFilter.appendChild(option);
    });

    // 2. Populate months
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const localMonthNames = {
        'Jan': 'Tháng 01', 'Feb': 'Tháng 02', 'Mar': 'Tháng 03', 'Apr': 'Tháng 04',
        'May': 'Tháng 05', 'Jun': 'Tháng 06', 'Jul': 'Tháng 07', 'Aug': 'Tháng 08',
        'Sep': 'Tháng 09', 'Oct': 'Tháng 10', 'Nov': 'Tháng 11', 'Dec': 'Tháng 12'
    };
    const uniqueMonths = [...new Set(currentTimeline.map(item => parseDateParts(item.date).month).filter(Boolean))]
        .sort((a, b) => months.indexOf(a) - months.indexOf(b));

    ui.timelineMonthFilter.innerHTML = '<option value="">Tất cả tháng</option>';
    uniqueMonths.forEach(m => {
        const option = document.createElement('option');
        option.value = m;
        option.textContent = localMonthNames[m] || m;
        ui.timelineMonthFilter.appendChild(option);
    });

    // 3. Reset values to default
    ui.timelineCourseFilter.value = '';
    ui.timelineMonthFilter.value = '';
    ui.timelineDateFilter.value = '';
}

function filterAndRenderTimeline() {
    const selectedCourse = ui.timelineCourseFilter.value;
    const selectedMonth = ui.timelineMonthFilter.value;
    const selectedDateRange = ui.timelineDateFilter.value;

    let filtered = [...currentTimeline];

    // Filter by course
    if (selectedCourse) {
        filtered = filtered.filter(item => item.course === selectedCourse);
    }

    // Filter by month
    if (selectedMonth) {
        filtered = filtered.filter(item => parseDateParts(item.date).month === selectedMonth);
    }

    // Filter by date range (Today, Week, Month)
    if (selectedDateRange) {
        const now = new Date();
        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
        const todayEnd = todayStart + 24 * 3600 * 1000 - 1;
        const weekEnd = todayStart + 7 * 24 * 3600 * 1000;
        const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1).getTime();
        const thisMonthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 1).getTime() - 1;

        filtered = filtered.filter(item => {
            const ts = getTimestamp(item.date);
            if (selectedDateRange === 'today') {
                return ts >= todayStart && ts <= todayEnd;
            } else if (selectedDateRange === 'week') {
                return ts >= todayStart && ts <= weekEnd;
            } else if (selectedDateRange === 'month') {
                return ts >= thisMonthStart && ts <= thisMonthEnd;
            }
            return true;
        });
    }

    // Always sort chronologically by date
    filtered.sort((a, b) => getTimestamp(a.date) - getTimestamp(b.date));

    renderTimeline(filtered);
}

async function fetchTimeline(forceRefresh = false) {
    showLoading(forceRefresh ? 'Đang cập nhật từ Notion...' : 'Đang tải lịch deadline...');
    try {
        const res = await fetch(`${API_BASE_URL}/api/study/timeline?force_refresh=${forceRefresh}`);
        if (!res.ok) throw new Error('Lỗi tải timeline');
        const data = await res.json();
        currentTimeline = data.timeline || [];

        // Populate filters and reset selections
        populateTimelineFilters();
        filterAndRenderTimeline();
        showView('timeline');
    } catch (error) {
        console.error(error);
        alert('Lỗi tải timeline. Vui lòng thử lại.');
        showView('topics');
    }
}

function parseDateParts(dateStr) {
    if (!dateStr) return { day: '--', month: '--', time: '' };

    // Try ISO format: YYYY-MM-DD
    if (dateStr.includes('-')) {
        const parts = dateStr.split('T')[0].split('-');
        if (parts.length === 3) {
            const m = parts[1];
            const d = parts[2];
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const mIdx = parseInt(m, 10) - 1;
            const monthLabel = (mIdx >= 0 && mIdx < 12) ? months[mIdx] : m;
            const timePart = dateStr.includes('T') ? dateStr.split('T')[1].substring(0, 5) : '';
            return { day: d, month: monthLabel, time: timePart };
        }
    }

    // Standard dd/mm format, potentially with time: "15/07 09:00"
    const [datePart, timePart] = dateStr.split(' ');
    const parts = datePart.split('/');
    if (parts.length === 2) {
        const d = parts[0];
        const m = parts[1];
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const mIdx = parseInt(m, 10) - 1;
        const monthLabel = (mIdx >= 0 && mIdx < 12) ? months[mIdx] : m;
        return { day: d, month: monthLabel, time: timePart || '' };
    }

    return { day: dateStr, month: '', time: '' };
}

function openExternalLink(url) {
    if (window.Telegram && window.Telegram.WebApp && typeof window.Telegram.WebApp.openLink === 'function') {
        window.Telegram.WebApp.openLink(url);
    } else {
        window.open(url, '_blank');
    }
}

function renderTimeline(timelineItems) {
    ui.timelineContainer.innerHTML = '';
    if (timelineItems.length === 0) {
        ui.timelineContainer.innerHTML = '<p class="text-center text-gray-500 dark:text-gray-400 py-6">Không có deadline nào sắp tới.</p>';
        return;
    }

    timelineItems.forEach((item, index) => {
        const row = document.createElement('div');
        row.className = 'flex items-stretch gap-4 relative pb-6 fade-in';

        // Parse date components
        const { day, month, time } = parseDateParts(item.date);

        // Urgency badge styles
        let indicatorBg = 'bg-blue-500';
        let badgeBg = 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 border-blue-100 dark:border-blue-900/50';
        if (item.urgency === 'high') {
            indicatorBg = 'bg-red-500';
            badgeBg = 'bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-400 border-red-200 dark:border-red-900/50';
        } else if (item.urgency === 'low') {
            indicatorBg = 'bg-green-500';
            badgeBg = 'bg-green-50 dark:bg-green-950/40 text-green-700 dark:text-green-400 border-green-200 dark:border-green-900/50';
        }

        // Left date column (w-16, align text right/center)
        const dateCol = document.createElement('div');
        dateCol.className = 'w-16 shrink-0 flex flex-col items-end justify-start pt-1.5';
        dateCol.innerHTML = `
            <span class="text-xl font-extrabold text-gray-800 dark:text-gray-100 leading-none">${escapeHtml(day)}</span>
            <span class="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wider mt-0.5">${escapeHtml(month)}</span>
        `;

        // Dot centered on line at left-[72px] (from left edge of row, since dateCol is w-16 and gap is 16px, center of gap is 72px)
        const dot = document.createElement('div');
        dot.className = `absolute left-[65px] top-3.5 w-3.5 h-3.5 rounded-full border-2 border-white dark:border-gray-900 ${indicatorBg} z-10`;

        // Card content
        const card = document.createElement('div');
        card.className = 'flex-1 bg-gray-50 dark:bg-gray-850 p-4 rounded-xl border border-gray-150 dark:border-gray-800 hover:shadow-sm transition cursor-pointer active:scale-98 flex flex-col justify-between';

        let footerHtml = '';
        if (item.page_id) {
            const cleanPageId = item.page_id.replace(/-/g, '');
            const notionUrl = `https://notion.so/${cleanPageId}`;
            card.addEventListener('click', () => openExternalLink(notionUrl));
            footerHtml = `
                <div class="flex justify-end border-t border-gray-100 dark:border-gray-800/80 pt-2 mt-2">
                    <span class="text-[10px] font-bold text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1">
                        Xem chi tiết ↗
                    </span>
                </div>
            `;
        }

        card.innerHTML = `
            <div>
                <div class="flex items-center justify-between gap-2 mb-1.5">
                    <span class="text-xs font-bold text-gray-500 dark:text-gray-400 flex items-center gap-1">
                        📅 ${escapeHtml(item.weekday || '')} ${escapeHtml(time ? '• ' + time : '')}
                    </span>
                    <span class="text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${badgeBg}">
                        ${item.urgency === 'high' ? 'Gấp' : 'Bình thường'}
                    </span>
                </div>
                <h3 class="font-bold text-sm text-gray-800 dark:text-gray-100 leading-snug mb-1">
                    ${escapeHtml(item.course || '')}
                </h3>
                <p class="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
                    ${escapeHtml(item.content || '')}
                </p>
            </div>
            ${footerHtml}
        `;

        row.appendChild(dateCol);
        row.appendChild(dot);
        row.appendChild(card);
        ui.timelineContainer.appendChild(row);
    });
}

// Event Listeners
ui.prevBtn.addEventListener('click', () => {
    if (currentQuestionIndex > 0) {
        currentQuestionIndex--;
        saveQuizProgress();
        renderQuestion();
    }
});


ui.nextBtn.addEventListener('click', () => {
    currentQuestionIndex++;
    saveQuizProgress();
    renderQuestion();
});

if (ui.resumeBtn) ui.resumeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    resumeSavedQuiz();
});
if (ui.resumeBanner) ui.resumeBanner.addEventListener('click', () => resumeSavedQuiz());
if (ui.discardResumeBtn) ui.discardResumeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const latest = getLatestSavedProgress();
    if (latest && latest.topic && latest.topic.id) {
        clearQuizProgress(latest.topic.id);
    } else {
        clearQuizProgress();
    }
});

ui.btnChua.addEventListener('click', () => updateStatus('chua_nam_vung'));
ui.btnNam.addEventListener('click', () => {
    const title = currentTopic?.title ? `cho chủ đề "${currentTopic.title}"` : '';
    if (confirm(`Bạn có chắc chắn muốn đánh dấu đã nắm vững ${title}? Chủ đề sẽ được chuyển trạng thái trên Notion.`)) {
        updateStatus('da_nam_vung');
    }
});
ui.forceRefreshBtn.addEventListener('click', () => {
    if (currentTopic) {
        if (currentTopic.id && currentTopic.id.startsWith('quick_review')) {
            startQuickReview(true);
        } else {
            startQuiz(currentTopic, true);
        }
    }
});
ui.closeQuizBtn.addEventListener('click', () => {
    stopQuizTimer();
    showView('topics');
});
ui.showResultsBtn.addEventListener('click', showQuizResults);
ui.reviewAnswersBtn.addEventListener('click', () => reviewAnswers(0));
if (ui.reviewMistakesBtn) ui.reviewMistakesBtn.addEventListener('click', reviewFirstMistake);
if (ui.retakeMistakesBtn) ui.retakeMistakesBtn.addEventListener('click', retakeMistakes);
if (ui.shareResultsBtn) ui.shareResultsBtn.addEventListener('click', shareQuizResults);
if (ui.flagQuestionBtn) ui.flagQuestionBtn.addEventListener('click', toggleFlagCurrentQuestion);
if (ui.quizModeBtn) ui.quizModeBtn.addEventListener('click', () => {
    isExamMode = !isExamMode;
    try {
        localStorage.setItem('isExamMode', isExamMode);
    } catch (e) {}
    updateQuizModeUI();
    renderQuestion();
});
ui.copyQuestionBtn.addEventListener('click', copyCurrentQuestion);

// Keyboard Shortcuts Support for Desktop / Web
document.addEventListener('keydown', (e) => {
    if (views.quiz.classList.contains('hidden')) return;

    // Ignore shortcuts when typing in inputs/textareas
    const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
    if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select') return;

    const q = currentQuiz[currentQuestionIndex];
    if (!q) return;

    // Number keys 1-4 or letters A-D to select option
    if (q.selected === undefined && ui.optionsContainer && ui.optionsContainer.children) {
        let selectedIdx = null;
        if (['1', 'a', 'A'].includes(e.key)) selectedIdx = 0;
        else if (['2', 'b', 'B'].includes(e.key)) selectedIdx = 1;
        else if (['3', 'c', 'C'].includes(e.key)) selectedIdx = 2;
        else if (['4', 'd', 'D'].includes(e.key)) selectedIdx = 3;

        if (selectedIdx !== null && ui.optionsContainer.children[selectedIdx]) {
            ui.optionsContainer.children[selectedIdx].click();
            return;
        }
    }

    // Flag shortcut (F or f)
    if (e.key === 'f' || e.key === 'F') {
        toggleFlagCurrentQuestion();
        return;
    }

    // Next question: ArrowRight, Enter, Space (when answered)
    if ((e.key === 'ArrowRight' || (q.selected !== undefined && (e.key === 'Enter' || e.key === ' '))) && !ui.nextBtn.classList.contains('hidden')) {
        e.preventDefault();
        ui.nextBtn.click();
        return;
    }

    // Prev question: ArrowLeft
    if (e.key === 'ArrowLeft' && !ui.prevBtn.classList.contains('hidden')) {
        e.preventDefault();
        ui.prevBtn.click();
        return;
    }

    // Show Results: Enter / Space on last question
    if (q.selected !== undefined && (e.key === 'Enter' || e.key === ' ') && !ui.showResultsBtn.classList.contains('hidden')) {
        e.preventDefault();
        ui.showResultsBtn.click();
        return;
    }
});

ui.searchInput.addEventListener('input', () => {
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(filterAndRenderTopics, 250);
});
if (ui.clearSearchBtn) {
    ui.clearSearchBtn.addEventListener('click', () => {
        ui.searchInput.value = '';
        filterAndRenderTopics();
        ui.searchInput.focus();
    });
}
if (ui.resetFilterBtn) {
    ui.resetFilterBtn.addEventListener('click', () => {
        ui.searchInput.value = '';
        ui.courseFilter.value = '';
        fetchTopics(true);
    });
}
ui.courseFilter.addEventListener('change', filterAndRenderTopics);
ui.quickReviewBtn.addEventListener('click', () => startQuickReview());
if (ui.batchQuizBtn) {
    ui.batchQuizBtn.addEventListener('click', () => openBatchQuizModal());
}
if (ui.closeBatchModalBtn) {
    ui.closeBatchModalBtn.addEventListener('click', closeBatchQuizModal);
}
if (ui.batchCancelBtn) {
    ui.batchCancelBtn.addEventListener('click', closeBatchQuizModal);
}
if (ui.batchApplyAllBtn) {
    ui.batchApplyAllBtn.addEventListener('click', applyGlobalPresetToAllBatchTopics);
}
if (ui.batchStartBtn) {
    ui.batchStartBtn.addEventListener('click', startBatchQuizGeneration);
}

ui.quizDoneBtn.addEventListener('click', () => showView('topics'));
if (ui.cancelLoadingBtn) {
    ui.cancelLoadingBtn.addEventListener('click', () => {
        if (singleQuizAbortController) {
            singleQuizAbortController.abort();
            singleQuizAbortController = null;
        }
        showView('topics');
    });
}
ui.refreshCandidatesBtn.addEventListener('click', () => {
    fetchTopics(true);
});

ui.toggleTimelineBtn.addEventListener('click', () => fetchTimeline());
ui.closeTimelineBtn.addEventListener('click', () => showView('topics'));
ui.refreshTimelineBtn.addEventListener('click', () => fetchTimeline(true));
ui.timelineCourseFilter.addEventListener('change', filterAndRenderTimeline);
ui.timelineMonthFilter.addEventListener('change', filterAndRenderTimeline);
ui.timelineDateFilter.addEventListener('change', filterAndRenderTimeline);

// Quiz Config Modal Events
if (ui.closeConfigModalBtn) {
    ui.closeConfigModalBtn.addEventListener('click', closeQuizConfigModal);
}
if (ui.modalCancelBtn) {
    ui.modalCancelBtn.addEventListener('click', closeQuizConfigModal);
}
if (ui.quizConfigModal) {
    ui.quizConfigModal.addEventListener('click', (e) => {
        if (e.target === ui.quizConfigModal) {
            closeQuizConfigModal();
        }
    });
}
if (ui.batchQuizModal) {
    ui.batchQuizModal.addEventListener('click', (e) => {
        if (e.target === ui.batchQuizModal && !isBatchGenerating) {
            closeBatchQuizModal();
        }
    });
}
if (ui.batchSelectAllCb) {
    ui.batchSelectAllCb.addEventListener('change', toggleSelectAllBatchTopics);
}
if (ui.modalStartQuizBtn) {
    ui.modalStartQuizBtn.addEventListener('click', () => {
        if (selectedTopicForConfig) {
            const topicToStart = selectedTopicForConfig;
            closeQuizConfigModal();
            startQuiz(topicToStart, true, quizConfig);
        }
    });
}

// Config Button Groups
if (ui.configNumQuestionsGroup) {
    ui.configNumQuestionsGroup.addEventListener('click', (e) => {
        const btn = e.target.closest('.config-btn');
        if (!btn) return;
        const val = parseInt(btn.getAttribute('data-val'), 10);
        if (val) {
            quizConfig.numQuestions = val;
            saveQuizConfig();
            updateModalConfigUI();
        }
    });
}
if (ui.configDifficultyGroup) {
    ui.configDifficultyGroup.addEventListener('click', (e) => {
        const btn = e.target.closest('.config-btn');
        if (!btn) return;
        const val = btn.getAttribute('data-val');
        if (val) {
            quizConfig.difficulty = val;
            saveQuizConfig();
            updateModalConfigUI();
        }
    });
}
if (ui.configTypeGroup) {
    ui.configTypeGroup.addEventListener('click', (e) => {
        const btn = e.target.closest('.config-btn');
        if (!btn) return;
        const val = btn.getAttribute('data-val');
        if (val) {
            quizConfig.questionType = val;
            saveQuizConfig();
            updateModalConfigUI();
        }
    });
}

// Bind Telegram native BackButton for timeline too
function initTelegram() {
    const tg = window.Telegram?.WebApp;
    if (tg) {
        try {
            tg.expand();
        } catch (e) {}

        // Get user ID from Telegram initData
        if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
            telegramData = tg.initDataUnsafe.user;
        }

        // Apply dark mode theme if set in Telegram
        if (tg.colorScheme === 'dark') {
            document.documentElement.classList.add('dark');
        } else if (tg.colorScheme === 'light') {
            document.documentElement.classList.remove('dark');
        }

        // Listen to Telegram theme changes
        if (typeof tg.onEvent === 'function') {
            tg.onEvent('themeChanged', () => {
                if (tg.colorScheme === 'dark') {
                    document.documentElement.classList.add('dark');
                } else {
                    document.documentElement.classList.remove('dark');
                }
            });
        }

        // Bind Telegram native BackButton
        const urlParams = new URLSearchParams(window.location.search);
        const isTimelineOnly = urlParams.get('view') === 'timeline';
        if (tg.BackButton && tg.isVersionAtLeast && tg.isVersionAtLeast('6.1') && !isTimelineOnly) {
            tg.BackButton.onClick(() => {
                stopQuizTimer();
                showView('topics');
            });
        }
    }

    // Fallback ID when running outside Telegram (standard browser / Vercel web)
    if (!telegramData || !telegramData.id || telegramData.id === 'web_guest') {
        // Use a fixed ID for personal single-user deployment to sync across all browsers/devices
        telegramData = { id: 'default_user', first_name: 'Me' };
    }
}

// Batch Quiz Generation for Course
let batchTopicsData = [];
let isBatchGenerating = false;

function openBatchQuizModal() {
    if (!allTopics || allTopics.length === 0) {
        alert('Danh sách chủ đề đang được tải hoặc chưa có. Vui lòng thử lại sau giây lát.');
        return;
    }

    const selectedCourse = ui.courseFilter ? ui.courseFilter.value : '';
    let topicsInCourse = [];
    if (selectedCourse) {
        topicsInCourse = allTopics.filter(t => t.course === selectedCourse);
    } else {
        topicsInCourse = [...allTopics];
    }

    if (topicsInCourse.length === 0) {
        alert('Không có chủ đề nào trong môn học đã chọn để tạo quiz.');
        return;
    }

    if (ui.batchModalCourseTitle) {
        ui.batchModalCourseTitle.textContent = selectedCourse ? `Môn: ${selectedCourse} (${topicsInCourse.length} chủ đề)` : `Tất cả môn học (${topicsInCourse.length} chủ đề)`;
    }

    // Prepare default config for each topic
    batchTopicsData = topicsInCourse.map(t => ({
        topic_id: t.id,
        title: t.title,
        course: t.course,
        chapter: t.chapter,
        has_cached_quiz: t.has_cached_quiz,
        num_questions: quizConfig.numQuestions || 15,
        difficulty: quizConfig.difficulty || 'medium',
        question_type: quizConfig.questionType || 'balanced',
        force_refresh: true, // Batch generate generally wants fresh quizzes or regenerate
        status: 'pending', // pending | generating | done | error
        selected: true
    }));

    if (ui.batchSelectAllCb) ui.batchSelectAllCb.checked = true;
    updateBatchSelectionCount();
    renderBatchTopicsList();

    if (ui.batchProgressContainer) ui.batchProgressContainer.classList.add('hidden');
    if (ui.batchStartBtn) {
        ui.batchStartBtn.disabled = false;
        ui.batchStartBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        ui.batchStartBtn.innerHTML = `<span>⚡ Bắt đầu tạo (${batchTopicsData.length} chủ đề)</span>`;
    }
    if (ui.batchCancelBtn) ui.batchCancelBtn.disabled = false;

    if (ui.batchQuizModal) {
        ui.batchQuizModal.classList.remove('hidden');
    }
}

function closeBatchQuizModal() {
    if (isBatchGenerating) {
        if (!confirm('Quá trình tạo quiz đang diễn ra. Bạn có chắc muốn dừng lại?')) {
            return;
        }
        if (batchQuizAbortController) {
            batchQuizAbortController.abort();
            batchQuizAbortController = null;
        }
    }
    if (ui.batchQuizModal) {
        ui.batchQuizModal.classList.add('hidden');
    }
    batchTopicsData = [];
    isBatchGenerating = false;
}

function updateBatchSelectionCount() {
    const total = batchTopicsData.length;
    const selectedCount = batchTopicsData.filter(t => t.selected).length;

    if (ui.batchSelectedCount) ui.batchSelectedCount.textContent = selectedCount;
    if (ui.batchTotalCount) ui.batchTotalCount.textContent = total;

    if (ui.batchSelectAllCb) {
        ui.batchSelectAllCb.checked = selectedCount === total && total > 0;
        ui.batchSelectAllCb.indeterminate = selectedCount > 0 && selectedCount < total;
    }

    if (ui.batchStartBtn && !isBatchGenerating) {
        if (selectedCount === 0) {
            ui.batchStartBtn.disabled = true;
            ui.batchStartBtn.classList.add('opacity-50', 'cursor-not-allowed');
            ui.batchStartBtn.innerHTML = '<span>⚡ Chọn ít nhất 1 chủ đề</span>';
        } else {
            ui.batchStartBtn.disabled = false;
            ui.batchStartBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            ui.batchStartBtn.innerHTML = `<span>⚡ Bắt đầu tạo (${selectedCount} chủ đề)</span>`;
        }
    }
}

function toggleSelectAllBatchTopics() {
    const isChecked = ui.batchSelectAllCb ? ui.batchSelectAllCb.checked : true;
    batchTopicsData.forEach(item => {
        item.selected = isChecked;
    });
    renderBatchTopicsList();
    updateBatchSelectionCount();
}

function renderBatchTopicsList() {
    if (!ui.batchTopicsList) return;
    ui.batchTopicsList.innerHTML = '';

    batchTopicsData.forEach((item, idx) => {
        const row = document.createElement('div');
        const isSel = item.selected !== false;
        row.className = `p-2.5 rounded-xl border transition ${isSel ? 'border-gray-200 dark:border-gray-800 bg-gray-50/60 dark:bg-gray-800/40' : 'border-dashed border-gray-200 dark:border-gray-800/60 bg-gray-100/40 dark:bg-gray-900/30 opacity-60'} space-y-2 text-xs`;
        row.id = `batch-topic-row-${item.topic_id}`;

        const isCached = item.has_cached_quiz;
        const cacheBadge = isCached
            ? `<span class="text-[9px] font-semibold px-1.5 py-0.2 rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/50 shrink-0" title="Đã có cache trong Redis">⚡ Có cache</span>`
            : `<span class="text-[9px] font-semibold px-1.5 py-0.2 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700 shrink-0" title="Chưa có cache trong Redis">Chưa cache</span>`;

        const statusBadge = `<span id="batch-status-badge-${item.topic_id}" class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 shrink-0">Chờ tạo</span>`;

        row.innerHTML = `
            <div class="flex items-center justify-between gap-2">
                <label class="flex items-center gap-2 cursor-pointer flex-1 min-w-0 select-none">
                    <input type="checkbox" data-idx="${idx}" class="batch-topic-cb w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 dark:border-gray-700 dark:bg-gray-800 cursor-pointer shrink-0" ${isSel ? 'checked' : ''}>
                    <span class="font-bold text-gray-800 dark:text-gray-100 truncate ${isSel ? '' : 'text-gray-400 dark:text-gray-500'}" title="${escapeHtml(item.title)}">
                        ${idx + 1}. ${escapeHtml(item.title)}
                    </span>
                    ${cacheBadge}
                </label>
                ${statusBadge}
            </div>
            <div class="grid grid-cols-3 gap-1.5 ${isSel ? '' : 'pointer-events-none opacity-40'}">
                <select data-idx="${idx}" data-field="num_questions" ${isSel ? '' : 'disabled'} class="batch-field text-[11px] font-bold p-1 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200">
                    <option value="5" ${item.num_questions === 5 ? 'selected' : ''}>5 câu</option>
                    <option value="10" ${item.num_questions === 10 ? 'selected' : ''}>10 câu</option>
                    <option value="15" ${item.num_questions === 15 ? 'selected' : ''}>15 câu</option>
                    <option value="20" ${item.num_questions === 20 ? 'selected' : ''}>20 câu</option>
                </select>
                <select data-idx="${idx}" data-field="difficulty" ${isSel ? '' : 'disabled'} class="batch-field text-[11px] font-bold p-1 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200">
                    <option value="easy" ${item.difficulty === 'easy' ? 'selected' : ''}>🌱 Cơ bản</option>
                    <option value="medium" ${item.difficulty === 'medium' ? 'selected' : ''}>⚡ Chuẩn thi</option>
                    <option value="hard" ${item.difficulty === 'hard' ? 'selected' : ''}>🔥 Nâng cao</option>
                </select>
                <select data-idx="${idx}" data-field="question_type" ${isSel ? '' : 'disabled'} class="batch-field text-[11px] font-bold p-1 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200">
                    <option value="theory" ${item.question_type === 'theory' ? 'selected' : ''}>📖 Lý thuyết</option>
                    <option value="balanced" ${item.question_type === 'balanced' ? 'selected' : ''}>⚖️ Cân bằng</option>
                    <option value="calculation" ${item.question_type === 'calculation' ? 'selected' : ''}>🧮 Tính toán</option>
                </select>
            </div>
        `;

        const cb = row.querySelector('.batch-topic-cb');
        if (cb) {
            cb.addEventListener('change', (e) => {
                const targetIdx = parseInt(e.target.getAttribute('data-idx'), 10);
                batchTopicsData[targetIdx].selected = e.target.checked;
                renderBatchTopicsList();
                updateBatchSelectionCount();
            });
        }

        row.querySelectorAll('.batch-field').forEach(sel => {
            sel.addEventListener('change', (e) => {
                const targetIdx = parseInt(e.target.getAttribute('data-idx'), 10);
                const field = e.target.getAttribute('data-field');
                let val = e.target.value;
                if (field === 'num_questions') val = parseInt(val, 10);
                batchTopicsData[targetIdx][field] = val;
            });
        });

        ui.batchTopicsList.appendChild(row);
    });
}

function applyGlobalPresetToAllBatchTopics() {
    const numQ = parseInt(ui.batchGlobalNum.value, 10);
    const diff = ui.batchGlobalDiff.value;
    const qType = ui.batchGlobalType.value;

    batchTopicsData.forEach(item => {
        item.num_questions = numQ;
        item.difficulty = diff;
        item.question_type = qType;
    });

    renderBatchTopicsList();

    const origText = ui.batchApplyAllBtn.textContent;
    ui.batchApplyAllBtn.textContent = '✓ Đã áp dụng!';
    setTimeout(() => { ui.batchApplyAllBtn.textContent = origText; }, 1200);
}

async function startBatchQuizGeneration() {
    const selectedTopics = batchTopicsData.filter(t => t.selected !== false);
    if (selectedTopics.length === 0) {
        alert('Vui lòng tick chọn ít nhất 1 chủ đề để tạo trắc nghiệm.');
        return;
    }
    if (isBatchGenerating) return;

    if (batchQuizAbortController) {
        batchQuizAbortController.abort();
    }
    batchQuizAbortController = new AbortController();

    isBatchGenerating = true;
    if (ui.batchStartBtn) {
        ui.batchStartBtn.disabled = true;
        ui.batchStartBtn.classList.add('opacity-50', 'cursor-not-allowed');
    }
    if (ui.batchCancelBtn) {
        ui.batchCancelBtn.innerHTML = '<span>✕ Hủy tiến trình</span>';
        ui.batchCancelBtn.className = 'flex-1 bg-red-100 hover:bg-red-200 dark:bg-red-950/50 dark:hover:bg-red-950/70 text-red-700 dark:text-red-300 font-bold py-2.5 px-3 rounded-xl text-xs transition cursor-pointer';
    }
    if (ui.batchProgressContainer) ui.batchProgressContainer.classList.remove('hidden');
    if (ui.batchProgressBar) ui.batchProgressBar.style.width = '0%';
    if (ui.batchProgressPercent) ui.batchProgressPercent.textContent = '0%';
    if (ui.batchProgressText) ui.batchProgressText.textContent = `🚀 Bắt đầu tạo ${selectedTopics.length} chủ đề...`;

    try {
        const payload = {
            course: ui.courseFilter.value || null,
            topics: selectedTopics.map(t => ({
                topic_id: t.topic_id,
                title: t.title,
                force_refresh: true,
                num_questions: t.num_questions,
                difficulty: t.difficulty,
                question_type: t.question_type
            }))
        };

        const res = await fetch(`${API_BASE_URL}/api/study/batch-quiz`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: batchQuizAbortController.signal,
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error(`Lỗi từ máy chủ: ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.trim()) continue;
                let event;
                try {
                    event = JSON.parse(line);
                } catch (pe) {
                    console.warn('Batch stream JSON parse warning:', pe);
                    continue;
                }

                if (event.type === 'batch_started') {
                    if (ui.batchProgressText) ui.batchProgressText.textContent = event.message || 'Đang tạo câu hỏi...';
                } else if (event.type === 'topic_progress') {
                    const badge = document.getElementById(`batch-status-badge-${event.topic_id}`);
                    if (badge) {
                        badge.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 animate-pulse';
                        badge.textContent = `${event.percentage}%`;
                    }
                    if (ui.batchCurrentTopicStatus) {
                        ui.batchCurrentTopicStatus.textContent = `⚡ [${event.percentage}%] ${event.details || ''}`;
                    }
                } else if (event.type === 'topic_completed') {
                    if (event.success) {
                        const t = allTopics.find(x => x.id === event.topic_id);
                        if (t) t.has_cached_quiz = true;
                    }
                    const badge = document.getElementById(`batch-status-badge-${event.topic_id}`);
                    if (badge) {
                        if (event.success) {
                            badge.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300';
                            badge.textContent = `✓ ${event.num_questions} câu`;
                        } else {
                            badge.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300';
                            badge.textContent = '✕ Lỗi';
                        }
                    }
                    if (ui.batchProgressBar) ui.batchProgressBar.style.width = `${event.percentage}%`;
                    if (ui.batchProgressPercent) ui.batchProgressPercent.textContent = `${event.percentage}%`;
                    if (ui.batchProgressText) ui.batchProgressText.textContent = `Đã hoàn thành ${event.completed_count}/${event.total_count} chủ đề`;
                } else if (event.type === 'batch_finished') {
                    if (ui.batchProgressBar) ui.batchProgressBar.style.width = '100%';
                    if (ui.batchProgressPercent) ui.batchProgressPercent.textContent = '100%';
                    if (ui.batchProgressText) {
                        ui.batchProgressText.textContent = `🎉 Hoàn tất! Tạo thành công ${event.successful_topics}/${event.total_topics} chủ đề`;
                    }
                    if (ui.batchCurrentTopicStatus) {
                        ui.batchCurrentTopicStatus.textContent = 'Toàn bộ câu hỏi đã sẵn sàng trong bộ nhớ đệm.';
                    }

                    const tg = window.Telegram?.WebApp;
                    if (tg?.HapticFeedback) {
                        try {
                            tg.HapticFeedback.notificationOccurred('success');
                        } catch (e) {}
                    }
                } else if (event.type === 'error') {
                    throw new Error(event.message);
                }
            }
        }
    } catch (err) {
        if (err.name === 'AbortError') {
            console.log('Batch quiz generation aborted.');
            if (ui.batchProgressText) ui.batchProgressText.textContent = '⏹️ Đã dừng tạo trắc nghiệm.';
            return;
        }
        console.error('Batch quiz error:', err);
        alert('Lỗi tạo hàng loạt: ' + (err.message || 'Không xác định'));
        if (ui.batchProgressText) ui.batchProgressText.textContent = '❌ Quá trình tạo gặp sự cố';
    } finally {
        isBatchGenerating = false;
        batchQuizAbortController = null;
        if (ui.batchCancelBtn) {
            ui.batchCancelBtn.innerHTML = '<span>Đóng</span>';
            ui.batchCancelBtn.className = 'flex-1 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-bold py-2.5 px-3 rounded-xl text-xs transition cursor-pointer';
        }
        if (ui.batchStartBtn) {
            ui.batchStartBtn.disabled = false;
            ui.batchStartBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            ui.batchStartBtn.innerHTML = '<span>🔄 Tạo lại các chủ đề đã chọn</span>';
        }
    }
}
function renderMath() {
    if (typeof renderMathInElement === 'function') {
        renderMathInElement(document.getElementById('quiz-view'), {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false},
                {left: '\\(', right: '\\)', display: false},
                {left: '\\[', right: '\\]', display: true}
            ],
            ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code", "option"],
            throwOnError: false,
            errorColor: '#ef4444'
        });
    }
}



// App Start
document.addEventListener('DOMContentLoaded', async () => {
    initTelegram();
    updateQuizModeUI();
    const urlParams = new URLSearchParams(window.location.search);
    const isTimelineOnly = urlParams.get('view') === 'timeline';

    if (isTimelineOnly) {
        // Hide close/back button in timeline view
        if (ui.closeTimelineBtn) {
            ui.closeTimelineBtn.classList.add('hidden');
        }
        fetchTimeline();
    } else {
        // Normal topics view: load saved progress first to ensure cards and banner have correct state
        await fetchSavedQuizProgress();
        checkAndRenderResumeBanner();
        await fetchTopics();
    }

    // Global click listener: Đóng dropdown menu 3 chấm khi click ra ngoài
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.topic-menu-btn') && !e.target.closest('.topic-menu-dropdown')) {
            document.querySelectorAll('.topic-menu-dropdown').forEach(el => el.classList.add('hidden'));
        }
    });

    // Hide the "Xem Deadline trên Web" button inside topics view by default or if not standalone,
    // actually, since they are separate pages, we hide it completely.
    if (ui.toggleTimelineBtn) {
        ui.toggleTimelineBtn.classList.add('hidden');
    }
});