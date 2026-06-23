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
    forceRefreshBtn: document.getElementById('force-refresh-btn')
};

// State
let telegramData = { id: 123456789 }; // Mock for local testing
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
}

// Navigation
function showView(viewName) {
    Object.values(views).forEach(v => v.classList.add('hidden'));
    views[viewName].classList.remove('hidden');
}

function showLoading(text) {
    ui.loadingText.textContent = text;
    showView('loading');
}

// API Calls
async function fetchTopics() {
    showLoading('Loading topics...');
    try {
        const res = await fetch(`${API_BASE_URL}/api/study/candidates?telegram_id=${telegramData.id}`);
        if (!res.ok) throw new Error('Failed to fetch topics');
        const data = await res.json();
        renderTopics(data.candidates || []);
    } catch (error) {
        console.error(error);
        alert('Error loading topics. Ensure backend is running.');
        renderTopics([]); // Show empty state on error for now
    }
}

async function startQuiz(topic, forceRefresh = false) {
    currentTopic = topic;
    showLoading(`Generating quiz for "${topic.title}"...`);

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
            questions = [{ question: "Could not parse quiz format.", answer: JSON.stringify(data) }];
        }

        if (questions.length === 0) {
            alert('No questions generated.');
            showView('topics');
            return;
        }

        currentQuiz = questions;
        currentQuestionIndex = 0;

        ui.quizTopicTitle.textContent = topic.title;
        renderQuestion();
        showView('quiz');

    } catch (error) {
        console.error(error);
        alert('Error generating quiz.');
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
                page_id: currentTopic.id,
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
        const btn = document.createElement('button');
        btn.className = 'w-full text-left bg-white p-4 rounded-xl shadow-sm border border-gray-200 hover:border-blue-500 hover:shadow-md transition duration-200 flex flex-col';

        btn.innerHTML = `
            <span class="font-semibold text-gray-800">${topic.title}</span>
            <div class="flex justify-between items-center mt-2 text-xs text-gray-500">
                <span class="bg-gray-100 px-2 py-1 rounded">Score: ${Math.round(topic.score * 100) / 100 || 'N/A'}</span>
                <span>Tap to review &rarr;</span>
            </div>
        `;

        btn.onclick = () => startQuiz(topic);
        ui.topicsList.appendChild(btn);
    });

    showView('topics');
}

function renderQuestion() {
    const quizContent = document.getElementById('quiz-content');
    if (quizContent) {
        quizContent.classList.remove('fade-in');
        void quizContent.offsetWidth; // trigger reflow
        quizContent.classList.add('fade-in');
    }

    const q = currentQuiz[currentQuestionIndex];

    ui.questionText.textContent = q.question || q.q || 'Question text missing';
    ui.optionsContainer.innerHTML = '';
    ui.explanationBox.classList.add('hidden');
    ui.quizProgress.textContent = `${currentQuestionIndex + 1}/${currentQuiz.length}`;

    const options = q.options || [];
    options.forEach((opt, idx) => {
        const btn = document.createElement('button');
        const defaultClasses = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out active:scale-95 shadow-sm border-gray-200 bg-white hover:border-blue-400 hover:shadow-md text-gray-700';
        btn.className = defaultClasses;
        btn.textContent = opt;
        btn.onclick = () => {
            if (q.selected !== undefined) return;
            q.selected = idx;

            if (idx === q.correct) {
                btn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out shadow-sm border-green-500 bg-gradient-to-r from-green-50 to-green-100 text-green-800 font-bold';
                btn.textContent = '✅ ' + opt;
            } else {
                btn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out shadow-sm border-red-500 bg-gradient-to-r from-red-50 to-red-100 text-red-800 font-bold line-through';
                btn.textContent = '❌ ' + opt;

                const correctBtn = ui.optionsContainer.children[q.correct];
                if (correctBtn) {
                    correctBtn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out shadow-sm border-green-500 bg-green-50 text-green-800 font-bold';
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
                ui.statusBtns.classList.remove('hidden');
            }
        };

        if (q.selected !== undefined) {
            if (idx === q.correct) {
                btn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out shadow-sm border-green-500 bg-gradient-to-r from-green-50 to-green-100 text-green-800 font-bold';
                btn.textContent = '✅ ' + opt;
            } else if (idx === q.selected) {
                btn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out shadow-sm border-red-500 bg-gradient-to-r from-red-50 to-red-100 text-red-800 font-bold line-through';
                btn.textContent = '❌ ' + opt;
            } else {
                btn.className = 'w-full text-left p-4 rounded-xl border-2 font-medium transition-all duration-300 ease-out shadow-sm border-gray-200 bg-white text-gray-700 opacity-50';
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
            ui.statusBtns.classList.add('hidden');
        } else {
            ui.nextBtn.classList.add('hidden');
            ui.statusBtns.classList.remove('hidden');
        }
    } else {
        ui.nextBtn.classList.add('hidden');
        ui.statusBtns.classList.add('hidden');
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

// App Start
document.addEventListener('DOMContentLoaded', () => {
    initTelegram();
    fetchTopics();
});