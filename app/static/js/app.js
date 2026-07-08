// Mesh-Agent Panel Interactive Controller
document.addEventListener("DOMContentLoaded", () => {
    // Detect active tab based on body state or pathname
    const activeTab = document.body.dataset.activeTab;
    
    if (activeTab === "chat") {
        initChat();
    } else if (activeTab === "terminal") {
        initTerminal();
    } else if (activeTab === "workspace") {
        initWorkspace();
    } else if (activeTab === "config") {
        initConfig();
    }
});

// ==========================================
// 1. Chat Tab Interface
// ==========================================
function initChat() {
    const chatHistory = document.getElementById("chatHistory");
    const chatInput = document.getElementById("chatInput");
    const sendBtn = document.getElementById("sendBtn");
    
    // Load chat history from sessionStorage
    let messages = JSON.parse(sessionStorage.getItem("mesh_chat_history") || "[]");
    
    // Render stored messages
    messages.forEach(msg => appendMessage(msg.role, msg.content));
    scrollToBottom(chatHistory);

    // Send click trigger
    sendBtn.addEventListener("click", handleSend);
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });

    async function handleSend() {
        const text = chatInput.value.trim();
        if (!text) return;

        // Display user bubble
        appendMessage("user", text);
        chatInput.value = "";
        scrollToBottom(chatHistory);

        // Save user message to history
        messages.push({ role: "user", content: text });
        sessionStorage.setItem("mesh_chat_history", JSON.stringify(messages));

        // Show typing indicator
        const loader = appendTypingIndicator();
        scrollToBottom(chatHistory);

        try {
            // Post payload: send current message and historical logs
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    history: messages.slice(0, -1) // send history before this message
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Server error");
            }

            const data = await response.json();
            
            // Remove loader
            loader.remove();

            // Display assistant bubble
            appendMessage("assistant", data.reply);
            scrollToBottom(chatHistory);

            // Save assistant reply to history
            messages.push({ role: "assistant", content: data.reply });
            sessionStorage.setItem("mesh_chat_history", JSON.stringify(messages));

        } catch (err) {
            loader.remove();
            appendMessage("assistant", `⚠️ Error: ${err.message}`);
            scrollToBottom(chatHistory);
        }
    }

    function appendMessage(role, text) {
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${role}`;
        
        // Basic parser to render linebreaks and preformatted blocks nicely
        let parsedText = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\n/g, "<br>");
            
        // Check if there is XML tool tags in output, style them
        parsedText = parsedText.replace(/&lt;(write_file|read_file|list_files|delete_file)(.*?)&gt;/g, (match) => {
            return `<span style="color: var(--accent-cyan); font-family: var(--font-mono); font-weight: 600;">${match}</span>`;
        });
        parsedText = parsedText.replace(/&lt;\/(write_file|read_file|list_files|delete_file)&gt;/g, (match) => {
            return `<span style="color: var(--accent-cyan); font-family: var(--font-mono); font-weight: 600;">${match}</span>`;
        });

        bubble.innerHTML = `<p>${parsedText}</p>`;
        chatHistory.appendChild(bubble);
    }

    function appendTypingIndicator() {
        const bubble = document.createElement("div");
        bubble.className = "chat-bubble assistant";
        bubble.innerHTML = `
            <div class="typing-loader">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        chatHistory.appendChild(bubble);
        return bubble;
    }
}

// ==========================================
// 2. Terminal Log Tab Interface
// ==========================================
function initTerminal() {
    const consoleDiv = document.getElementById("terminalConsole");
    const clearBtn = document.getElementById("clearLogsBtn");
    
    // Load logs immediately
    fetchLogs();
    
    // Poll logs every 2.5 seconds to watch agent operations live
    const intervalId = setInterval(fetchLogs, 2500);

    // Clear logs handler
    clearBtn.addEventListener("click", async () => {
        if (!confirm("Clear all execution logs?")) return;
        try {
            await fetch("/api/terminal/clear", { method: "POST" });
            consoleDiv.innerHTML = '<div class="terminal-line thought">> Console logs cleared. Ready.</div>';
        } catch (err) {
            console.error("Failed to clear logs", err);
        }
    });

    // Cleanup interval on page unload
    window.addEventListener("beforeunload", () => {
        clearInterval(intervalId);
    });

    async function fetchLogs() {
        try {
            const response = await fetch("/api/terminal/logs");
            if (!response.ok) return;
            const data = await response.json();
            renderLogs(data.logs);
        } catch (err) {
            console.error("Error fetching console logs:", err);
        }
    }

    function renderLogs(logs) {
        if (!logs || logs.length === 0) {
            consoleDiv.innerHTML = '<div class="terminal-line thought">> No active execution logs. Say something in Chat!</div>';
            return;
        }

        consoleDiv.innerHTML = "";
        logs.forEach(log => {
            const line = document.createElement("div");
            line.className = `terminal-line ${log.type}`;
            
            const timeStr = new Date(log.timestamp * 1000).toLocaleTimeString();
            let detailBlock = "";
            
            if (log.details) {
                detailBlock = `<pre style="font-size:12px; margin-top:4px; opacity:0.8; white-space:pre-wrap; word-break:break-all;">${escapeHtml(log.details)}</pre>`;
            }

            line.innerHTML = `[${timeStr}] <strong>${escapeHtml(log.summary)}</strong>${detailBlock}`;
            consoleDiv.appendChild(line);
        });
        scrollToBottom(consoleDiv);
    }
}

// ==========================================
// 3. Workspace Dashboard Interface
// ==========================================
function initWorkspace() {
    const fileList = document.getElementById("fileList");
    const editorFileName = document.getElementById("editorFileName");
    const editorTextarea = document.getElementById("editorTextarea");
    const saveFileBtn = document.getElementById("saveFileBtn");
    const deleteFileBtn = document.getElementById("deleteFileBtn");
    const newFileBtn = document.getElementById("newFileBtn");
    
    let currentPath = ""; // empty means root
    let openedFile = null; // current file loaded

    // Load root directory contents
    loadDirectory("");

    // Save File Button
    saveFileBtn.addEventListener("click", async () => {
        if (!openedFile) return;
        const text = editorTextarea.value;
        try {
            const response = await fetch("/api/workspace/file", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: openedFile, content: text })
            });
            if (!response.ok) throw new Error("Could not save file");
            alert("File saved successfully!");
            loadDirectory(currentPath);
        } catch (err) {
            alert(`Error saving file: ${err.message}`);
        }
    });

    // Delete Button
    deleteFileBtn.addEventListener("click", async () => {
        const pathToDelete = openedFile || currentPath;
        if (!pathToDelete) {
            alert("Nothing selected to delete.");
            return;
        }
        if (!confirm(`Are you sure you want to delete '${pathToDelete}'?`)) return;
        
        try {
            const response = await fetch(`/api/workspace/file?path=${encodeURIComponent(pathToDelete)}`, {
                method: "DELETE"
            });
            if (!response.ok) throw new Error("Delete failed");
            alert("Deleted successfully!");
            openedFile = null;
            editorFileName.textContent = "No file open";
            editorTextarea.value = "";
            editorTextarea.disabled = true;
            loadDirectory(currentPath);
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    });

    // Create New File
    newFileBtn.addEventListener("click", async () => {
        const name = prompt("Enter path for new file (relative to workspace root):");
        if (!name) return;
        
        try {
            const response = await fetch("/api/workspace/file", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: name, content: "" })
            });
            if (!response.ok) throw new Error("Create failed");
            alert(`Created file '${name}'`);
            loadDirectory(currentPath);
            loadFile(name);
        } catch (err) {
            alert(`Error creating file: ${err.message}`);
        }
    });

    async function loadDirectory(path) {
        currentPath = path;
        try {
            const response = await fetch(`/api/workspace/files?path=${encodeURIComponent(path)}`);
            if (!response.ok) throw new Error("Failed to load folder contents");
            const data = await response.json();
            renderFilesList(data.files);
        } catch (err) {
            fileList.innerHTML = `<li class="error" style="color:var(--accent-red)">Failed to load: ${err.message}</li>`;
        }
    }

    function renderFilesList(files) {
        fileList.innerHTML = "";
        
        // Add back link if not at root
        if (currentPath !== "") {
            const backItem = document.createElement("li");
            backItem.className = "file-item dir";
            backItem.innerHTML = `
                <div class="file-info">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
                    <span>.. (parent directory)</span>
                </div>
            `;
            backItem.addEventListener("click", () => {
                // Navigate up
                const idx = currentPath.lastIndexOf("/");
                const parent = idx === -1 ? "" : currentPath.substring(0, idx);
                loadDirectory(parent);
            });
            fileList.appendChild(backItem);
        }

        if (files.length === 0) {
            fileList.innerHTML += `<li style="padding:12px; font-size:14px; color:var(--text-muted)">Directory is empty</li>`;
            return;
        }

        files.forEach(file => {
            const item = document.createElement("li");
            item.className = `file-item ${file.is_dir ? 'dir' : 'file'}`;
            if (openedFile === file.path) {
                item.classList.add("active");
            }
            
            const icon = file.is_dir 
                ? `<svg viewBox="0 0 24 24"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`
                : `<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
            
            const sizeStr = file.is_dir ? "" : `<span class="file-size">${formatBytes(file.size)}</span>`;

            item.innerHTML = `
                <div class="file-info">
                    ${icon}
                    <span>${escapeHtml(file.name)}</span>
                </div>
                ${sizeStr}
            `;

            item.addEventListener("click", () => {
                if (file.is_dir) {
                    loadDirectory(file.path);
                } else {
                    loadFile(file.path);
                    // Update active styling
                    document.querySelectorAll(".file-item").forEach(el => el.classList.remove("active"));
                    item.classList.add("active");
                }
            });
            fileList.appendChild(item);
        });
    }

    async function loadFile(path) {
        try {
            const response = await fetch(`/api/workspace/file?path=${encodeURIComponent(path)}`);
            if (!response.ok) throw new Error("Could not load file content");
            const data = await response.json();
            
            openedFile = path;
            editorFileName.textContent = path;
            editorTextarea.value = data.content;
            editorTextarea.disabled = false;
        } catch (err) {
            alert(`Failed to load file: ${err.message}`);
        }
    }
}

// ==========================================
// 4. Config Tab Interface
// ==========================================
function initConfig() {
    const providerSelect = document.getElementById("provider");
    const openaiFields = document.getElementById("openai_fields");
    const anthropicFields = document.getElementById("anthropic_fields");
    const geminiFields = document.getElementById("gemini_fields");
    const testBtn = document.getElementById("testConnectionBtn");
    const testResult = document.getElementById("testResult");

    // Toggle fields based on initial selection
    toggleFields(providerSelect.value);

    // Listen for select changes
    providerSelect.addEventListener("change", (e) => {
        toggleFields(e.target.value);
    });

    // Test Connection click
    testBtn.addEventListener("click", async () => {
        testResult.className = "alert-message";
        testResult.textContent = "Testing connectivity to LLM provider... please wait.";
        testResult.style.display = "block";
        
        try {
            const response = await fetch("/api/config/test", { method: "POST" });
            const data = await response.json();
            
            if (response.ok) {
                testResult.className = "alert-message success";
                testResult.textContent = data.message;
            } else {
                testResult.className = "alert-message error";
                testResult.textContent = data.message || "Failed connection.";
            }
        } catch (err) {
            testResult.className = "alert-message error";
            testResult.textContent = `Connection error: ${err.message}`;
        }
    });

    function toggleFields(provider) {
        if (provider === "openai") {
            openaiFields.style.display = "block";
            anthropicFields.style.display = "none";
            geminiFields.style.display = "none";
        } else if (provider === "anthropic") {
            openaiFields.style.display = "none";
            anthropicFields.style.display = "block";
            geminiFields.style.display = "none";
        } else if (provider === "gemini") {
            openaiFields.style.display = "none";
            anthropicFields.style.display = "none";
            geminiFields.style.display = "block";
        } else {
            openaiFields.style.display = "none";
            anthropicFields.style.display = "none";
            geminiFields.style.display = "none";
        }
    }
}

// ==========================================
// Helper Utilities
// ==========================================
function scrollToBottom(element) {
    if (element) {
        element.scrollTop = element.scrollHeight;
    }
}

function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
