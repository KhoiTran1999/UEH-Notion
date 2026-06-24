const API_BASE_URL = 'https://ueh-notion.onrender.com';

// DOM Elements
const views = {
    loading: document.getElementById('loading-view'),
    topics: document.getElementById('topics-view'),
    quiz: document.getElementById('quiz-view')
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
    refreshCandidatesBtn: document.getElementById('refresh-candidates-btn')
};

// State
let telegramData = { id: 123456789 }; // Mock for local testing
let allTopics = [];
let currentTopic = null;
let currentQuiz = [];
let currentQuestionIndex = 0;

// Initialize Telegram Web App
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
    if (tg.BackButton) {
        tg.BackButton.onClick(() => {
            showView('topics');
        });
    }
}

// Navigation
function showView(viewName) {
    Object.values(views).forEach(v => v.classList.add('hidden'));
    views[viewName].classList.remove('hidden');

    const tg = window.Telegram.WebApp;
    if (tg && tg.BackButton) {
        if (viewName === 'quiz') {
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
    showView('loading');
}

// API Calls
async function fetchTopics(forceRefresh = false) {
    showLoading('Đang tải danh sách chủ đề...');
    try {
        const res = await fetch(`${API_BASE_URL}/api/study/candidates?telegram_id=${telegramData.id}&force_refresh=${forceRefresh}`);
        if (!res.ok) throw new Error('Failed to fetch topics');
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
        if (!res.ok) throw new Error('Failed to fetch quick review');
        const data = await res.json();

        currentTopic = { id: 'quick_review', title: 'Ôn tập tổng hợp' };
        currentQuiz = data.questions || [];
        currentQuestionIndex = 0;

        document.getElementById('quiz-content').classList.remove('hidden');
        ui.quizResults.classList.add('hidden');
        ui.quizProgress.classList.remove('hidden');
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

async function startQuiz(topic, forceRefresh = false) {
    currentTopic = topic;
    showLoading(`Đang tạo câu hỏi cho "${topic.title}"...`);

    try {
        const res = await fetch(`${API_BASE_URL}/api/study/quiz`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic_id: topic.id,
                force_refresh: forceRefresh
            })
        });

        if (!res.ok) throw new Error('Failed to generate quiz');
        const data = await res.json();

        // Handle varying response formats. Assuming array of Q&A objects.
        // E.g. [{question: "...", answer: "..."}, ...]
        // The exact format depends on your AI backend, adjust as needed.
        let questions = [];
        if (Array.isArray(data)) {
            questions = data;
        } else if (data.questions) {
            questions = data.questions;
        } else if (data.quiz) {
            questions = data.quiz;
        } else {
            // Fallback parsing if it's just raw text
            questions = [{ question: "Không thể đọc cấu trúc câu hỏi.", answer: JSON.stringify(data) }];
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
        ui.forceRefreshBtn.classList.remove('hidden');
        ui.showResultsBtn.classList.add('hidden');
        ui.quizDoneBtn.classList.add('hidden');

        ui.quizTopicTitle.textContent = topic.title;
        renderQuestion();
        showView('quiz');

    } catch (error) {
        console.error(error);
        alert('Lỗi khi tạo bộ câu hỏi.');
        showView('topics');
    }
}

async function updateStatus(status) {
    showLoading('Saving status...');
    try {
        await fetch(`${API_BASE_URL}/api/study/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: telegramData.id,
                topic_id: currentTopic.id,
                status: status
            })
        });

        window.Telegram.WebApp.close();
    } catch (error) {
        console.error(error);
        alert('Failed to save status.');
        window.Telegram.WebApp.close();
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

        if (!res.ok) throw new Error('Failed to update status');

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
                metaHtml += `<span class="bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-[10px] font-semibold px-2 py-0.5 rounded border border-blue-100 dark:border-blue-900/50 truncate max-w-[150px]">🔹 ${topic.course}</span>`;
            }
            if (topic.chapter) {
                metaHtml += `<span class="bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-[10px] font-semibold px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700 truncate max-w-[200px]">📍 ${topic.chapter}</span>`;
            }
            metaHtml += `</div>`;
        }

        card.innerHTML = `
            <div class="topic-content cursor-pointer flex-1 flex flex-col space-y-2">
                <span class="font-semibold text-gray-800 dark:text-gray-100 text-sm md:text-base leading-tight">${topic.title}</span>
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

    const questionText = q.question || q.q || 'Question text missing';
    if (currentTopic.id === 'quick_review' && q.topic_title) {
        ui.questionText.innerHTML = `
            <div class="text-[10px] text-blue-500 font-bold uppercase tracking-wider mb-2">📌 Chủ đề: ${q.topic_title}</div>
            <div>${questionText}</div>
        `;
    } else {
        ui.questionText.textContent = questionText;
    }
    ui.optionsContainer.innerHTML = '';
    ui.explanationBox.classList.add('hidden');
    ui.quizProgress.textContent = `${currentQuestionIndex + 1}/${currentQuiz.length}`;

    const options = q.options || [];
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
                ui.explanationBox.textContent = q.explanation;
                ui.explanationBox.classList.remove('hidden');
            }

            if (currentQuestionIndex < currentQuiz.length - 1) {
                ui.nextBtn.classList.remove('hidden');
            } else {
                ui.showResultsBtn.classList.remove('hidden');
            }
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

    if (q.selected !== undefined && q.explanation) {
        ui.explanationBox.textContent = q.explanation;
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
    } else {
        ui.statusBtns.classList.remove('hidden');
        ui.quizDoneBtn.classList.add('hidden');
    }
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

ui.searchInput.addEventListener('input', filterAndRenderTopics);
ui.courseFilter.addEventListener('change', filterAndRenderTopics);
ui.quickReviewBtn.addEventListener('click', () => startQuickReview());
ui.quizDoneBtn.addEventListener('click', () => showView('topics'));
ui.refreshCandidatesBtn.addEventListener('click', () => fetchTopics(true));

// App Start
document.addEventListener('DOMContentLoaded', () => {
    initTelegram();
    fetchTopics();
});