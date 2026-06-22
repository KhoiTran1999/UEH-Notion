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
    flashcard: document.getElementById('flashcard'),
    questionText: document.getElementById('question-text'),
    answerText: document.getElementById('answer-text'),
    nextBtn: document.getElementById('next-btn'),
    statusBtns: document.getElementById('status-btns'),
    btnChua: document.getElementById('status-chua-btn'),
    btnNam: document.getElementById('status-nam-btn')
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

async function startQuiz(topic) {
    currentTopic = topic;
    showLoading(`Generating quiz for "${topic.title}"...`);

    try {
        const res = await fetch(`${API_BASE_URL}/api/study/quiz`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic_id: topic.id
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
    const q = currentQuiz[currentQuestionIndex];

    // Reset card state
    ui.flashcard.classList.remove('flipped');
    ui.nextBtn.classList.add('hidden');
    ui.statusBtns.classList.add('hidden');

    // Set content
    ui.questionText.textContent = q.question || q.q || 'Question text missing';
    ui.answerText.textContent = q.answer || q.a || 'Answer text missing';
    ui.quizProgress.textContent = `${currentQuestionIndex + 1}/${currentQuiz.length}`;
}

// Event Listeners
ui.flashcard.addEventListener('click', () => {
    // Only allow flip if we haven't reached the end or it's not already flipped
    if (!ui.flashcard.classList.contains('flipped')) {
        ui.flashcard.classList.add('flipped');

        // Show appropriate controls after flipping
        if (currentQuestionIndex < currentQuiz.length - 1) {
            ui.nextBtn.classList.remove('hidden');
        } else {
            ui.statusBtns.classList.remove('hidden');
        }
    }
});

ui.nextBtn.addEventListener('click', () => {
    currentQuestionIndex++;
    renderQuestion();
});

ui.btnChua.addEventListener('click', () => updateStatus('chua_nam_vung'));
ui.btnNam.addEventListener('click', () => updateStatus('da_nam_vung'));

// App Start
document.addEventListener('DOMContentLoaded', () => {
    initTelegram();
    fetchTopics();
});