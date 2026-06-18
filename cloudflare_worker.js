export default {
    async fetch(request, env, ctx) {
        if (request.method !== "POST") {
            return new Response("Method not allowed", { status: 405 });
        }

        try {
            const update = await request.json();
            if (!update.message || !update.message.text) return new Response("OK");

            const chatId = String(update.message.chat.id);
            const text = update.message.text.trim();

            // 1. Check User vs Notion
            const isValidUser = await checkNotionUser(env, chatId);
            if (!isValidUser) {
                await sendMessage(env, chatId, "⛔ Tài khoản của bạn chưa được kích hoạt.\nVui lòng liên hệ Admin để thêm vào hệ thống.");
                return new Response("Unauthorized", { status: 200 });
            }

            // 2. Handle Commands
            let mode = "";
            let targetRepo = ""; // Route to correct GitHub repo

            // === GARMIN BOT Commands ===
            if (text === "/daily" || text === "/report") {
                mode = "daily";
                targetRepo = "garmin";
                await sendMessage(env, chatId, "🚀 Đang lấy báo cáo ngày...");
            } else if (text === "/sleep") {
                mode = "sleep_analysis";
                targetRepo = "garmin";
                await sendMessage(env, chatId, "💤 Đang phân tích giấc ngủ...");
            } else if (text === "/workout") {
                mode = "workout";
                targetRepo = "garmin";
                await sendMessage(env, chatId, "🏃 Đang phân tích bài tập...");

            // === UEH NOTION Commands ===
            } else if (text === "/taskreport") {
                mode = "daily-report";
                targetRepo = "ueh";
                await sendMessage(env, chatId, "📊 Đang tạo báo cáo task...");
            } else if (text === "/study") {
                mode = "study-assistant";
                targetRepo = "ueh";
                await sendMessage(env, chatId, "🎓 Đang tạo bài ôn tập...");

            // === General ===
            } else if (text === "/start" || text === "/help") {
                await sendMessage(env, chatId,
                    "✅ Bot đã sẵn sàng!\n\n" +
                    "🏃 Garmin:\n" +
                    "/daily - Báo cáo ngày\n" +
                    "/sleep - Phân tích giấc ngủ\n" +
                    "/workout - Phân tích bài tập\n\n" +
                    "📚 UEH Notion:\n" +
                    "/taskreport - Báo cáo task\n" +
                    "/study - Ôn tập khắc sâu"
                );
                return new Response("OK");
            } else {
                return new Response("OK");
            }

            // 3. Trigger GitHub (route to correct repo)
            const success = await triggerGitHub(env, mode, chatId, targetRepo);
            if (!success) {
                await sendMessage(env, chatId, "⚠️ Lỗi hệ thống khi gọi Bot. Thử lại sau.");
            }

            return new Response("OK");

        } catch (e) {
            return new Response(`Error: ${e.message}`, { status: 500 });
        }
    },
};

async function checkNotionUser(env, telegramId) {
    const url = `https://api.notion.com/v1/databases/${env.NOTION_DATABASE_ID}/query`;
    const body = {
        filter: {
            property: "Telegram Chat ID",
            rich_text: {
                equals: telegramId
            }
        }
    };

    const resp = await fetch(url, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${env.NOTION_TOKEN}`,
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        },
        body: JSON.stringify(body)
    });

    if (!resp.ok) {
        console.log("Notion Error:", await resp.text());
        return false;
    }

    const data = await resp.json();
    return data.results.length > 0;
}

async function sendMessage(env, chatId, text) {
    const url = `https://api.telegram.org/bot${env.TG_BOT_TOKEN}/sendMessage`;
    await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, text: text })
    });
}

async function triggerGitHub(env, mode, chatId, targetRepo) {
    // Route to correct repo
    let owner, repo;
    if (targetRepo === "ueh") {
        owner = env.UEH_GITHUB_OWNER || env.GITHUB_OWNER;
        repo = env.UEH_GITHUB_REPO;
    } else {
        owner = env.GITHUB_OWNER;
        repo = env.GITHUB_REPO;
    }

    const url = `https://api.github.com/repos/${owner}/${repo}/dispatches`;
    const payload = {
        event_type: "telegram_command",
        client_payload: { mode: mode, user_id: chatId }
    };

    console.log(`[DEBUG] triggerGitHub: ${url}, mode=${mode}, target=${targetRepo}`);

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
        // Gửi debug info qua Telegram
        await sendMessage(env, chatId, `🔧 Debug: GitHub ${resp.status}\n${url}\n${errText}`);
    }

    return resp.status === 204;
}
