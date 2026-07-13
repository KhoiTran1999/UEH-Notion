const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
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
    searchInput: document.getElementById('search-input'),
    courseFilter: document.getElementById('course-filter'),
    quickReviewBtn: document.getElementById('quick-review-btn'),
    quizDoneBtn: document.getElementById('quiz-done-btn'),
    refreshCandidatesBtn: document.getElementById('refresh-candidates-btn'),
    progressBar: document.getElementById('quiz-progress-bar'),
    progressContainer: document.getElementById('quiz-progress-container'),
    loadingProgressBar: document.getElementById('loading-progress-bar'),
    loadingPercentage: document.getElementById('loading-percentage'),
    reviewAnswersBtn: document.getElementById('review-answers-btn'),
    dotContainer: document.getElementById('quiz-dot-container'),
    copyQuestionBtn: document.getElementById('copy-question-btn'),
    toggleTimelineBtn: document.getElementById('toggle-timeline-btn'),
    closeTimelineBtn: document.getElementById('close-timeline-btn'),
    timelineContainer: document.getElementById('timeline-container'),
    timelineCourseFilter: document.getElementById('timeline-course-filter'),
    timelineMonthFilter: document.getElementById('timeline-month-filter'),
    timelineDateFilter: document.getElementById('timeline-date-filter'),
    refreshTimelineBtn: document.getElementById('refresh-timeline-btn'),
};


// State
let telegramData = { id: 123456789 }; // Mock for local testing
let allTopics = [];
let currentTopic = null;
let currentQuiz = [];
let currentQuestionIndex = 0;
let searchDebounceTimer = null;
let currentTimeline = [];


// Navigation
function showView(viewName) {
    Object.values(views).forEach(v => v.classList.add('hidden'));
    views[viewName].classList.remove('hidden');

    const urlParams = new URLSearchParams(window.location.search);
    const isTimelineOnly = urlParams.get('view') === 'timeline';

    const tg = window.Telegram.WebApp;
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
    const searchQuery = ui.searchInput.value.toLowerCase().trim();
    const selectedCourse = ui.courseFilter.value;

    const filtered = allTopics.filter(topic => {
        const matchesCourse = !selectedCourse || topic.course === selectedCourse;
        const matchesSearch = !searchQuery ||
            topic.title.toLowerCase().includes(searchQuery) ||
            (topic.chapter && topic.chapter.toLowerCase().includes(searchQuery)) ||
            (topic.course && topic.course.toLowerCase().includes(searchQuery));
        return matchesCourse && matchesSearch;
    });

    renderTopics(filtered);
}

function showLoading(text) {
    ui.loadingText.textContent = text;
    if (ui.loadingProgressBar) ui.loadingProgressBar.style.width = '0%';
    if (ui.loadingPercentage) ui.loadingPercentage.textContent = '0%';
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

async function startQuickReview() {
    showLoading('Đang chuẩn bị bộ câu hỏi tổng hợp...');
    try {
        const res = await fetch(`${API_BASE_URL}/api/study/quick-review`);
        if (!res.ok) throw new Error('Lỗi tải câu hỏi ôn tập nhanh');
        const data = await res.json();

        currentTopic = { id: 'quick_review', title: 'Ôn tập tổng hợp' };
        currentQuiz = data.questions || [];
        currentQuestionIndex = 0;

        document.getElementById('quiz-content').classList.remove('hidden');
        ui.quizResults.classList.add('hidden');
        ui.quizProgress.classList.remove('hidden');
        if (ui.progressContainer) {
            ui.progressContainer.classList.remove('hidden');
        }
        ui.forceRefreshBtn.classList.add('hidden');
        ui.showResultsBtn.classList.add('hidden');
        ui.quizDoneBtn.classList.add('hidden');

        ui.quizTopicTitle.textContent = 'Ôn tập tổng hợp';
        renderQuestion();
        showView('quiz');
    } catch (error) {
        console.error(error);
        alert('Lỗi tải câu hỏi ôn tập nhanh. Có thể danh sách chủ đề đang trống.');
        showView('topics');
    }
}

async function startQuiz(topic, forceRefresh = false, numQuestions) {
    currentTopic = topic;
    const nq = numQuestions || 10;
    showLoading(`Đang tạo ${nq} câu hỏi cho "${topic.title}"...`);

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
            body: JSON.stringify({
                topic_id: topic.id,
                force_refresh: forceRefresh,
                num_questions: nq
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
                    if (event.status === 'calling_ai') {
                        if (aiTimer) clearInterval(aiTimer);
                        let aiSeconds = 0;
                        updateProgress(event.percentage || 45, event.details || '🧠 Trợ lý AI đang kết nối...');
                        const aiProgressMessages = [
                            [0, '🧠 Trợ lý AI đang tiếp nhận nội dung...'],
                            [4, '🧠 Trợ lý AI đang đọc hiểu bài học...'],
                            [8, '🧠 Trợ lý AI đang biên soạn câu hỏi...'],
                            [13, '🧠 Trợ lý AI đang tối ưu hóa các đáp án nhiễu...'],
                            [19, '🧠 Trợ lý AI đang hoàn tất việc tạo đề...']
                        ];
                        aiTimer = setInterval(() => {
                            aiSeconds += 1;
                            if (currentPercent < 90) {
                                currentPercent += 2;
                                ui.loadingProgressBar && (ui.loadingProgressBar.style.width = `${currentPercent}%`);
                                ui.loadingPercentage && (ui.loadingPercentage.textContent = `${currentPercent}%`);
                            }
                            const msg = aiProgressMessages.filter(([t]) => aiSeconds >= t).pop();
                            if (msg && ui.loadingText) {
                                ui.loadingText.textContent = msg[1] + (aiSeconds >= 19 ? ` (giây thứ ${aiSeconds})` : '');
                            }
                        }, 1000);
                    } else {
                        if (aiTimer) { clearInterval(aiTimer); aiTimer = null; }
                        updateProgress(event.percentage || 0, event.details || '');
                    }
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

        currentQuiz = questions;
        currentQuestionIndex = 0;

        // Reset results UI to initial quiz state
        document.getElementById('quiz-content').classList.remove('hidden');
        ui.quizResults.classList.add('hidden');
        ui.quizProgress.classList.remove('hidden');
        if (ui.progressContainer) {
            ui.progressContainer.classList.remove('hidden');
        }
        ui.forceRefreshBtn.classList.remove('hidden');
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
        console.error(error);
        alert('Lỗi khi tạo bộ câu hỏi.');
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
        masteredBtn.innerHTML = '⏱ Đang lưu...';
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
            masteredBtn.innerHTML = '✅ Đã nắm vững';
        }
    }
}

// UI Rendering
function renderTopics(topics) {
    ui.topicsList.innerHTML = '';

    if (topics.length === 0) {
        ui.topicsList.classList.add('hidden');
        ui.noTopics.classList.remove('hidden');
        showView('topics');
        return;
    }

    ui.topicsList.classList.remove('hidden');
    ui.noTopics.classList.add('hidden');

    topics.forEach(topic => {
        const card = document.createElement('div');
        card.className = 'w-full bg-white dark:bg-gray-900 p-4 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 hover:shadow-md transition duration-200 flex flex-col space-y-3';

        let metaHtml = '';
        if (topic.course || topic.chapter) {
            metaHtml += `<div class="flex flex-wrap gap-1.5 w-full">`;
            if (topic.course) {
                metaHtml += `<span class="bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-[10px] font-semibold px-2 py-0.5 rounded border border-blue-100 dark:border-blue-900/50 truncate max-w-[150px]">🔹 ${escapeHtml(topic.course)}</span>`;
            }
            if (topic.chapter) {
                metaHtml += `<span class="bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-[10px] font-semibold px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700 truncate max-w-[200px]">📍 ${escapeHtml(topic.chapter)}</span>`;
            }
            metaHtml += `</div>`;
        }

        card.innerHTML = `
            <div class="topic-content cursor-pointer flex-1 flex flex-col space-y-2">
                <span class="font-semibold text-gray-800 dark:text-gray-100 text-sm md:text-base leading-tight">${escapeHtml(topic.title)}</span>
                ${metaHtml}
            </div>
            <div class="flex justify-between items-center pt-2 border-t border-gray-100 dark:border-gray-800 mt-1">
                <span class="text-[11px] text-blue-500 dark:text-blue-400 font-semibold cursor-pointer topic-link">Ôn tập &rarr;</span>
                <button class="mastered-btn bg-green-50 hover:bg-green-100 dark:bg-green-950/40 dark:hover:bg-green-950/60 text-green-700 dark:text-green-400 text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-green-200 dark:border-green-900/50 transition duration-150 flex items-center gap-1">
                    ✅ Đã nắm vững
                </button>
            </div>
        `;

        const openQuiz = () => startQuiz(topic);
        card.querySelector('.topic-content').onclick = openQuiz;
        card.querySelector('.topic-link').onclick = openQuiz;

        card.querySelector('.mastered-btn').onclick = (e) => {
            e.stopPropagation();
            markTopicAsMastered(topic.id, card);
        };

        ui.topicsList.appendChild(card);
    });

    showView('topics');
}

function renderQuestion() {
    ui.statusBtns.classList.add('hidden');

    const quizContent = document.getElementById('quiz-content');
    if (quizContent) {
        quizContent.classList.remove('fade-in');
        void quizContent.offsetWidth; // trigger reflow
        quizContent.classList.add('fade-in');
    }

    const q = currentQuiz[currentQuestionIndex];

    // Fallback cho câu hỏi bị lỗi dữ liệu
    const questionText = q.question || q.q || '⚠️ Nội dung câu hỏi bị thiếu';
    if (currentTopic.id === 'quick_review' && q.topic_title) {
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

    // Render dot progress indicator
    if (ui.dotContainer) {
        ui.dotContainer.innerHTML = '';
        currentQuiz.forEach((_, idx) => {
            const dot = document.createElement('span');
            const isActive = idx === currentQuestionIndex;
            const isAnswered = currentQuiz[idx].selected !== undefined;
            const isCorrect = currentQuiz[idx].selected === currentQuiz[idx].correct;
            let dotClass = 'w-2.5 h-2.5 rounded-full transition-all duration-300 ';
            if (isActive) {
                dotClass += 'bg-blue-500 scale-125 shadow-sm shadow-blue-300';
            } else if (isAnswered && isCorrect) {
                dotClass += 'bg-green-400';
            } else if (isAnswered && !isCorrect) {
                dotClass += 'bg-red-400';
            } else {
                dotClass += 'bg-gray-300 dark:bg-gray-600';
            }
            dot.className = dotClass;
            ui.dotContainer.appendChild(dot);
        });
    }

    const options = q.options || [];
    if (options.length === 0) {
        // Fallback khi không có đáp án nào
        const fallbackBtn = document.createElement('button');
        fallbackBtn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium border-red-300 bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 whitespace-normal break-words';
        fallbackBtn.textContent = '⚠️ Dữ liệu đáp án bị lỗi. Vui lòng tạo lại câu hỏi.';
        ui.optionsContainer.appendChild(fallbackBtn);
    } else {
        options.forEach((opt, idx) => {
            const btn = document.createElement('button');
            const defaultClasses = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out active:scale-95 shadow-sm border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-blue-400 dark:hover:border-blue-500 hover:shadow-md text-gray-700 dark:text-gray-300 whitespace-normal break-words';
            btn.className = defaultClasses;
            btn.textContent = opt;
            btn.onclick = () => {
                if (q.selected !== undefined) return;
                q.selected = idx;

                // Trigger Telegram Web App Haptic Feedback
                const tg = window.Telegram?.WebApp;
                if (tg?.HapticFeedback) {
                    try {
                        if (idx === q.correct) {
                            tg.HapticFeedback.notificationOccurred('success');
                        } else {
                            tg.HapticFeedback.notificationOccurred('error');
                        }
                    } catch (e) {
                        console.warn("Haptic feedback error:", e);
                    }
                }

                if (idx === q.correct) {
                    btn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out shadow-sm border-green-500 dark:border-green-600 bg-gradient-to-r from-green-50 to-green-100 dark:from-green-950/20 dark:to-green-950/40 text-green-800 dark:text-green-300 font-bold whitespace-normal break-words';
                    btn.textContent = '✅ ' + opt;
                } else {
                    btn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out shadow-sm border-red-500 dark:border-red-600 bg-gradient-to-r from-red-50 to-red-100 dark:from-red-950/20 dark:to-red-950/40 text-red-800 dark:text-red-300 font-bold line-through whitespace-normal break-words';
                    btn.textContent = '❌ ' + opt;

                    const correctBtn = ui.optionsContainer.children[q.correct];
                    if (correctBtn) {
                        correctBtn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out shadow-sm border-green-500 dark:border-green-600 bg-green-50 dark:bg-green-950/20 text-green-800 dark:text-green-300 font-bold whitespace-normal break-words';
                        correctBtn.textContent = '✅ ' + options[q.correct];
                    }

                }

                if (q.explanation) {
                    ui.explanationBox.innerHTML = `<div class="flex items-start gap-2.5">
                        <span class="text-xl select-none">💡</span>
                        <div>
                            <div class="font-bold text-blue-800 dark:text-blue-400 mb-0.5 text-xs uppercase tracking-wider">Giải thích chi tiết</div>
                            <div>${escapeHtml(q.explanation)}</div>
                        </div>
                    </div>`;
                    ui.explanationBox.classList.remove('hidden');
                }

                if (currentQuestionIndex < currentQuiz.length - 1) {
                    ui.nextBtn.classList.remove('hidden');
                } else {
                    ui.showResultsBtn.classList.remove('hidden');
                }

                renderMath();
            };

            if (q.selected !== undefined) {
                if (idx === q.correct) {
                    btn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out shadow-sm border-green-500 dark:border-green-600 bg-gradient-to-r from-green-50 to-green-100 dark:from-green-950/20 dark:to-green-950/40 text-green-800 dark:text-green-300 font-bold whitespace-normal break-words';
                    btn.textContent = '✅ ' + opt;
                } else if (idx === q.selected) {
                    btn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out shadow-sm border-red-500 dark:border-red-600 bg-gradient-to-r from-red-50 to-red-100 dark:from-red-950/20 dark:to-red-950/40 text-red-800 dark:text-red-300 font-bold line-through whitespace-normal break-words';
                    btn.textContent = '❌ ' + opt;
                } else {
                    btn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out shadow-sm border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-400 opacity-50 whitespace-normal break-words';
                }
            }
            ui.optionsContainer.appendChild(btn);
        });
    }

    if (q.selected !== undefined && q.explanation) {
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

    ui.resultsScore.textContent = `${correct} / ${total}`;
    ui.resultsPercentage.textContent = `${percentage}%`;

    let feedback = '';
    if (percentage === 100) {
        feedback = 'Xuất sắc! Bạn đã trả lời đúng tất cả các câu hỏi. Hãy tiếp tục phát huy!';
    } else if (percentage >= 80) {
        feedback = 'Rất tốt! Bạn nắm vững hầu hết các kiến thức trong chủ đề này.';
    } else if (percentage >= 50) {
        feedback = 'Khá tốt! Hãy cố gắng ôn tập thêm một chút để đạt điểm tối đa nhé.';
    } else {
        feedback = 'Cần cố gắng thêm! Hãy đọc kỹ phần giải thích của mỗi câu hỏi để nắm vững kiến thức.';
    }
    ui.resultsFeedback.textContent = feedback;

    if (currentTopic.id === 'quick_review') {
        ui.statusBtns.classList.add('hidden');
        ui.quizDoneBtn.classList.remove('hidden');
        ui.reviewAnswersBtn.classList.remove('hidden');
    } else {
        ui.statusBtns.classList.remove('hidden');
        ui.quizDoneBtn.classList.add('hidden');
        ui.reviewAnswersBtn.classList.add('hidden');
    }
}

function reviewAnswers() {
    currentQuestionIndex = 0;
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
        renderQuestion();
    }
});


ui.nextBtn.addEventListener('click', () => {
    currentQuestionIndex++;
    renderQuestion();
});

ui.btnChua.addEventListener('click', () => updateStatus('chua_nam_vung'));
ui.btnNam.addEventListener('click', () => updateStatus('da_nam_vung'));
ui.forceRefreshBtn.addEventListener('click', () => {
    if (currentTopic) {
        startQuiz(currentTopic, true);
    }
});
ui.closeQuizBtn.addEventListener('click', () => showView('topics'));
ui.showResultsBtn.addEventListener('click', showQuizResults);
ui.reviewAnswersBtn.addEventListener('click', reviewAnswers);
ui.copyQuestionBtn.addEventListener('click', copyCurrentQuestion);

ui.searchInput.addEventListener('input', () => {
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(filterAndRenderTopics, 250);
});
ui.courseFilter.addEventListener('change', filterAndRenderTopics);
ui.quickReviewBtn.addEventListener('click', () => startQuickReview());

ui.quizDoneBtn.addEventListener('click', () => showView('topics'));
ui.refreshCandidatesBtn.addEventListener('click', () => fetchTopics(true));

ui.toggleTimelineBtn.addEventListener('click', () => fetchTimeline());
ui.closeTimelineBtn.addEventListener('click', () => showView('topics'));
ui.refreshTimelineBtn.addEventListener('click', () => fetchTimeline(true));
ui.timelineCourseFilter.addEventListener('change', filterAndRenderTimeline);
ui.timelineMonthFilter.addEventListener('change', filterAndRenderTimeline);
ui.timelineDateFilter.addEventListener('change', filterAndRenderTimeline);

// Bind Telegram native BackButton for timeline too
function initTelegram() {
    const tg = window.Telegram.WebApp;
    tg.expand();

    // Get user ID from Telegram initData
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        telegramData = tg.initDataUnsafe.user;
    }

    // Apply dark mode theme if set in Telegram
    if (tg.colorScheme === 'dark') {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }

    // Listen to Telegram theme changes
    tg.onEvent('themeChanged', () => {
        if (tg.colorScheme === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    });

    // Bind Telegram native BackButton
    const urlParams = new URLSearchParams(window.location.search);
    const isTimelineOnly = urlParams.get('view') === 'timeline';
    if (tg.BackButton && tg.isVersionAtLeast && tg.isVersionAtLeast('6.1') && !isTimelineOnly) {
        tg.BackButton.onClick(() => {
            showView('topics');
        });
    }
}

// Helper: Render LaTeX math in element using KaTeX
function renderMath() {
    if (typeof renderMathInElement === 'function') {
        renderMathInElement(document.getElementById('quiz-view'), {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false}
            ],
            throwOnError: false
        });
    }
}



// App Start
document.addEventListener('DOMContentLoaded', () => {
    initTelegram();
    const urlParams = new URLSearchParams(window.location.search);
    const isTimelineOnly = urlParams.get('view') === 'timeline';

    if (isTimelineOnly) {
        // Hide close/back button in timeline view
        if (ui.closeTimelineBtn) {
            ui.closeTimelineBtn.classList.add('hidden');
        }
        fetchTimeline();
    } else {
        // Normal topics view
        fetchTopics();
    }

    // Hide the "Xem Deadline trên Web" button inside topics view by default or if not standalone,
    // actually, since they are separate pages, we hide it completely.
    if (ui.toggleTimelineBtn) {
        ui.toggleTimelineBtn.classList.add('hidden');
    }
});