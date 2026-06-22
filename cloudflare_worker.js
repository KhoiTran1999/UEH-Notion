export default {
    async fetch(request, env, ctx) {
        if (request.method !== "POST") {
            return new Response("Method not allowed", { status: 405 });
        }

        try {
            const update = await request.json();

            // Handle Inline Keyboard Callback Queries
            if (update.callback_query) {
                const chatId = String(update.callback_query.message.chat.id);
                const text = update.callback_query.data;
                const callbackQueryId = update.callback_query.id;

                // Answer callback query to remove loading state on button
                await fetch(`https://api.telegram.org/bot${env.TG_BOT_TOKEN}/answerCallbackQuery`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ callback_query_id: callbackQueryId })
                });

                return await processCommand(env, chatId, text);
            }

            if (!update.message || !update.message.text) return new Response("OK");

            const chatId = String(update.message.chat.id);
            const text = update.message.text.trim();

            return await processCommand(env, chatId, text);

        } catch (e) {
            return new Response(`Error: ${e.message}`, { status: 500 });
        }
    },
};

async function processCommand(env, chatId, text) {
    let mode = "";
    let topicId = null;

    if (text === "/taskreport") {
        mode = "daily-report";
        await sendMessage(env, chatId, "🚀 Đã nhận lệnh! Bắt đầu tạo báo cáo ngày cho bạn...");
    } else if (text === "/study") {
        mode = "study-assistant";
        await sendMessage(env, chatId, "📚 Mở góc ôn tập bằng Web App bên dưới nhé:", {
            inline_keyboard: [
                [{ text: "Mở Góc Ôn Tập", web_app: { url: env.WEBAPP_URL || "https://example.com" } }]
            ]
        });
        return new Response("OK");
    } else if (text.startsWith("/study_")) {
        mode = "study-assistant";
        topicId = text.replace("/study_", "");

        // Convert to standard UUID format with hyphens (Notion requires this sometimes, though API often accepts without)
        if (topicId.length === 32 && !topicId.includes("-")) {
            topicId = `${topicId.substr(0, 8)}-${topicId.substr(8, 4)}-${topicId.substr(12, 4)}-${topicId.substr(16, 4)}-${topicId.substr(20)}`;
        }

        await sendMessage(env, chatId, "🎯 Đã chọn bài! Bắt đầu quá trình tạo trắc nghiệm...");
    } else if (text.startsWith("/mastered_")) {
        mode = "mark-mastered";
        topicId = text.replace("/mastered_", "");
        if (topicId.length === 32 && !topicId.includes("-")) {
            topicId = `${topicId.substr(0, 8)}-${topicId.substr(8, 4)}-${topicId.substr(12, 4)}-${topicId.substr(16, 4)}-${topicId.substr(20)}`;
        }
        await sendMessage(env, chatId, "⏳ Đang cập nhật trạng thái...");
    } else if (text.startsWith("/review_")) {
        mode = "mark-review";
        topicId = text.replace("/review_", "");
        if (topicId.length === 32 && !topicId.includes("-")) {
            topicId = `${topicId.substr(0, 8)}-${topicId.substr(8, 4)}-${topicId.substr(12, 4)}-${topicId.substr(16, 4)}-${topicId.substr(20)}`;
        }
        await sendMessage(env, chatId, "⏳ Đang cập nhật trạng thái...");
    } else if (text === "/start" || text === "/help") {
        await sendMessage(env, chatId,
            "✅ Bot đã sẵn sàng!\nChọn chức năng bên dưới hoặc gõ lệnh tương ứng:",
            {
                inline_keyboard: [
                    [{ text: "📊 Báo cáo Task", callback_data: "/taskreport" }],
                    [{ text: "🎓 Ôn tập khắc sâu", callback_data: "/study" }]
                ]
            }
        );
        return new Response("OK");
    } else {
        return new Response("OK");
    }

    // We no longer trigger GitHub action for mode = study-assistant as it's now a Web App.
    // If you need legacy support, keep it, but we can return early here.
    if (mode === "study-assistant") {
        return new Response("OK");
    }

    if (mode !== "") {
        const success = await triggerGitHub(env, mode, chatId, topicId);
        if (!success) {
            await sendMessage(env, chatId, "⚠️ Lỗi hệ thống khi gọi GitHub Actions. Thử lại sau.");
        }
    }

    return new Response("OK");
}

async function sendMessage(env, chatId, text, replyMarkup = null) {
    const url = `https://api.telegram.org/bot${env.TG_BOT_TOKEN}/sendMessage`;
    const body = { chat_id: chatId, text: text };
    if (replyMarkup) {
        body.reply_markup = replyMarkup;
    }
    await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });
}

async function triggerGitHub(env, mode, chatId, topicId = null) {
    const owner = env.GITHUB_OWNER;
    const repo = env.GITHUB_REPO;

    const url = `https://api.github.com/repos/${owner}/${repo}/dispatches`;

    let client_payload = { mode: mode, user_id: chatId };
    if (topicId) {
        client_payload.topic_id = topicId;
    }

    const payload = {
        event_type: "telegram_command",
        client_payload: client_payload
    };

    console.log(`[DEBUG] triggerGitHub: ${url}, mode=${mode}`);

    const resp = await fetch(url, {
        method: "POST",
        headers: {
            "Authorization": `token ${env.GITHUB_TOKEN}`,
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Cloudflare-Worker"
        },
        body: JSON.stringify(payload)
    });

    if (resp.status !== 204) {
        const errText = await resp.text();
        console.log(`[ERROR] GitHub API ${resp.status}: ${errText}`);
        await sendMessage(env, chatId, `🔧 Debug: GitHub ${resp.status}\n${url}\n${errText}`);
    }

    return resp.status === 204;
}